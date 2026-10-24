import errno
import fcntl
import os
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from pathlib import Path

from termux_viet.input import InputProcessor
from termux_viet.terminal import child_settings, write_all


class TerminalTests(unittest.TestCase):
    def test_canonical_erase_removes_utf8_character(self):
        master, slave = pty.openpty()
        try:
            attrs = termios.tcgetattr(slave)
            attrs[0] |= 0x4000
            attrs[6][termios.VERASE] = b'\x7f'
            termios.tcsetattr(slave, termios.TCSANOW, attrs)
            bypass, erase = child_settings(master)
            self.assertFalse(bypass)
            with InputProcessor() as processor:
                write_all(master, processor.feed(b'ass asf\r', erase=erase))
            self.assertTrue(select.select([slave], [], [], 2)[0])
            self.assertEqual(os.read(slave, 1024), 'as à\n'.encode())
        finally:
            os.close(master)
            os.close(slave)

    def test_password_bypass_is_canonical_without_echo(self):
        master, slave = pty.openpty()
        try:
            attrs = termios.tcgetattr(slave)
            attrs[3] &= ~termios.ECHO
            termios.tcsetattr(slave, termios.TCSANOW, attrs)
            self.assertTrue(child_settings(master)[0])
            attrs[3] &= ~termios.ICANON
            termios.tcsetattr(slave, termios.TCSANOW, attrs)
            self.assertFalse(child_settings(master)[0])
        finally:
            os.close(master)
            os.close(slave)


class Relay:
    def __init__(self, program, environment=None):
        self.master, self.slave = pty.openpty()
        self.before = termios.tcgetattr(self.slave)
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'),
                   TERMUX_VIET_MODE_KEY='0')
        if environment:
            env.update(environment)
        code = 'import sys; from termux_viet.terminal import run; sys.exit(run(sys.argv[1:]))'
        self.process = subprocess.Popen(
            [sys.executable, '-c', code, *program],
            stdin=self.slave, stdout=self.slave, stderr=self.slave, env=env,
        )
        self.output = bytearray()

    def until(self, marker, timeout=5):
        deadline = time.monotonic() + timeout
        while marker not in self.output and time.monotonic() < deadline:
            if select.select([self.master], [], [], 0.05)[0]:
                try:
                    data = os.read(self.master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not data:
                    break
                self.output.extend(data)
        if marker not in self.output:
            raise AssertionError(f'Missing {marker!r}; received {len(self.output)} bytes, '
                                 f'prefix={bytes(self.output[:200])!r}')

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)
        os.close(self.master)
        os.close(self.slave)


class RelayTests(unittest.TestCase):
    def test_mode_button_updates_without_changing_child_input(self):
        from termux_viet.extra_keys import install_keys, parse_layout
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            properties = root / '.termux/termux.properties'
            properties.parent.mkdir()
            properties.write_text(install_keys(''))
            bindir = root / 'bin'
            bindir.mkdir()
            reload_script = bindir / 'termux-reload-settings'
            reload_script.write_text(f'#!{sys.executable}\n')
            reload_script.chmod(0o755)
            relay = Relay([sys.executable, '-c',
                           "import os; print('READY',flush=True); "
                           "print('RESULT='+os.read(0,1024).hex(),flush=True); os.read(0,1024)"],
                          {'HOME': str(root), 'XDG_STATE_HOME': str(root / 'state'),
                           'PATH': str(bindir) + os.pathsep + os.environ['PATH'],
                           'TERMUX_VIET_MODE_KEY': '1'})
            try:
                relay.until(b'READY')
                write_all(relay.master, b'\x00ass\r')
                relay.until(b'RESULT=6173730a')
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    if parse_layout(properties.read_text())[0][0]['display'] == 'VI':
                        break
                    time.sleep(.01)
                self.assertEqual(parse_layout(properties.read_text())[0][0]['display'], 'VI')
                self.assertEqual(parse_layout(properties.read_text())[1][3:6],
                                 ['LEFT', 'DOWN', 'RIGHT'])
                write_all(relay.master, b'\r')
                self.assertEqual(relay.process.wait(timeout=5), 0)
            finally:
                relay.close()

    def relay(self, code):
        relay = Relay([sys.executable, '-c', code])
        self.addCleanup(relay.close)
        return relay

    def test_exit_status_and_terminal_restoration(self):
        relay = self.relay('print("READY", flush=True); raise SystemExit(7)')
        relay.until(b'READY')
        self.assertEqual(relay.process.wait(timeout=5), 7)
        self.assertEqual(termios.tcgetattr(relay.slave), relay.before)

    def test_bash_and_zsh_receive_live_telex(self):
        for shell, flags in [('bash', ['--noprofile', '--norc', '-i']), ('zsh', ['-f', '-i'])]:
            executable = shutil.which(shell)
            if not executable:
                continue
            with self.subTest(shell=shell):
                relay = Relay([executable, *flags])
                try:
                    write_all(relay.master, b"printf '<READY>\\n'\r")
                    relay.until(b'<READY>\r\n')
                    write_all(relay.master, b"printf '<OK>%s</OK>\\n' 'tieengs Vieetj'\r")
                    relay.until('<OK>tiếng Việt</OK>\r\n'.encode())
                    write_all(relay.master, b'\x00exit 7\r')
                    self.assertEqual(relay.process.wait(timeout=5), 7)
                finally:
                    relay.close()

    def test_output_is_byte_exact(self):
        relay = self.relay("import os,time; os.write(1,b'\\xe1'); time.sleep(.05); "
                           "os.write(1,b'\\xbb\\x87\\xffEND')")
        relay.until(b'END')
        self.assertIn(b'\xe1\xbb\x87\xffEND', relay.output)
        self.assertEqual(relay.process.wait(timeout=5), 0)

    def test_slow_screen_keeps_all_output_after_child_exit(self):
        relay = self.relay(
            "import os,time; print('READY',flush=True); time.sleep(.05); "
            "os.write(1,b'x'*100000+b'END')"
        )
        relay.until(b'READY')
        time.sleep(.7)
        relay.until(b'END')
        self.assertEqual(relay.output.count(b'x'), 100000)
        self.assertEqual(relay.process.wait(timeout=5), 0)

    def test_canonical_child_receives_composed_line(self):
        relay = self.relay("import os; print('READY',flush=True); "
                           "line=os.read(0,1024); print('RESULT='+line.hex(),flush=True)")
        relay.until(b'READY')
        write_all(relay.master, b'vieetj\x7fn\r')
        relay.until(('RESULT=' + 'viện\n'.encode().hex()).encode())
        self.assertEqual(relay.process.wait(timeout=5), 0)

    def test_password_is_literal(self):
        relay = self.relay(
            "import os,termios; a=termios.tcgetattr(0); a[3]&=~termios.ECHO; "
            "termios.tcsetattr(0,termios.TCSANOW,a); print('READY',flush=True); "
            "print('RESULT='+os.read(0,1024).hex(),flush=True)"
        )
        relay.until(b'READY')
        write_all(relay.master, b'passwords\r')
        relay.until(b'RESULT=70617373776f7264730a')

    def test_paste_to_unaware_child_has_literal_payload_without_markers(self):
        relay = self.relay("import os; print('READY',flush=True); "
                           "print('RESULT='+os.read(0,1024).hex(),flush=True)")
        relay.until(b'READY')
        self.assertIn(b'\x1b[?2004h', relay.output)
        write_all(relay.master, b'\x1b[200~ass passwords\x1b[201~\r')
        relay.until(('RESULT=' + b'ass passwords\n'.hex()).encode())

    def test_alternate_screen_bypasses_telex(self):
        relay = self.relay(
            "import os; print('\\x1b[?1049hREADY',flush=True); "
            "print('RESULT='+os.read(0,1024).hex(),flush=True)"
        )
        relay.until(b'READY')
        write_all(relay.master, b'ass\r')
        relay.until(b'RESULT=6173730a')

    def test_sigterm_restores_terminal(self):
        relay = self.relay("import time; print('READY',flush=True); time.sleep(60)")
        relay.until(b'READY')
        relay.process.send_signal(signal.SIGTERM)
        self.assertEqual(relay.process.wait(timeout=5), 128 + signal.SIGTERM)
        self.assertEqual(termios.tcgetattr(relay.slave), relay.before)

    def test_resize_reaches_child(self):
        relay = self.relay(
            "import os; print('READY',flush=True); os.read(0,1024); "
            "s=os.get_terminal_size(); print(f'SIZE={s.lines},{s.columns}',flush=True)"
        )
        relay.until(b'READY')
        fcntl.ioctl(relay.slave, termios.TIOCSWINSZ, struct.pack('HHHH', 31, 91, 0, 0))
        relay.process.send_signal(signal.SIGWINCH)
        write_all(relay.master, b'\r')
        relay.until(b'SIZE=31,91')

    def test_missing_command_returns_127(self):
        relay = Relay(['termux-viet-command-does-not-exist'])
        self.addCleanup(relay.close)
        self.assertEqual(relay.process.wait(timeout=5), 127)

    def test_child_exit_does_not_wait_for_nohup_descendant(self):
        relay = self.relay(
            "import subprocess,signal; subprocess.Popen(['sleep','3'], "
            "preexec_fn=lambda:signal.signal(signal.SIGHUP,signal.SIG_IGN)); "
            "print('READY',flush=True); raise SystemExit(7)"
        )
        relay.until(b'READY')
        self.assertEqual(relay.process.wait(timeout=1.5), 7)

    def test_sigterm_works_with_child_input_backpressure(self):
        relay = self.relay(
            "import tty,time; tty.setraw(0); print('READY',flush=True); time.sleep(30)"
        )
        relay.until(b'READY')
        os.set_blocking(relay.master, False)
        deadline = time.monotonic() + .5
        while time.monotonic() < deadline:
            try:
                os.write(relay.master, b'x' * 4096)
            except BlockingIOError:
                time.sleep(.005)
        relay.process.terminate()
        try:
            self.assertEqual(relay.process.wait(timeout=2), 143)
            self.assertEqual(termios.tcgetattr(relay.slave), relay.before)
        finally:
            if relay.process.poll() is None:
                relay.process.kill()
                relay.process.wait()

    def test_sigterm_works_with_screen_output_backpressure(self):
        relay = self.relay(
            "import os,time; print('READY',flush=True); "
            "os.write(1,b'x'*2000000); time.sleep(30)"
        )
        relay.until(b'READY')
        time.sleep(.1)
        relay.process.terminate()
        try:
            self.assertEqual(relay.process.wait(timeout=2), 143)
            self.assertEqual(termios.tcgetattr(relay.slave), relay.before)
        finally:
            if relay.process.poll() is None:
                relay.process.kill()
                relay.process.wait()
