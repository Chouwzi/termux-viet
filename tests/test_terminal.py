import errno
import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import sys
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
    def __init__(self, program):
        self.master, self.slave = pty.openpty()
        self.before = termios.tcgetattr(self.slave)
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
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
            raise AssertionError(f'Missing {marker!r} in {bytes(self.output)!r}')

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)
        os.close(self.master)
        os.close(self.slave)


class RelayTests(unittest.TestCase):
    def relay(self, code):
        relay = Relay([sys.executable, '-c', code])
        self.addCleanup(relay.close)
        return relay

    def test_exit_status_and_terminal_restoration(self):
        relay = self.relay('print("READY", flush=True); raise SystemExit(7)')
        relay.until(b'READY')
        self.assertEqual(relay.process.wait(timeout=5), 7)
        self.assertEqual(termios.tcgetattr(relay.slave), relay.before)

    def test_output_is_byte_exact(self):
        relay = self.relay("import os,time; os.write(1,b'\\xe1'); time.sleep(.05); "
                           "os.write(1,b'\\xbb\\x87\\xffEND')")
        relay.until(b'END')
        self.assertIn(b'\xe1\xbb\x87\xffEND', relay.output)
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
