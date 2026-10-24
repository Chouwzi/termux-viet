"""PTY lifecycle and byte-preserving relay."""

import errno
import fcntl
import os
import pty
import select
import signal
import struct
import termios
import time
import tty
from pathlib import Path

from .input import InputProcessor, TerminalModes

IUTF8 = getattr(termios, 'IUTF8', 0x4000)


def write_all(fd, data):
    view = memoryview(data)
    while view:
        try:
            count = os.write(fd, view)
        except InterruptedError:
            continue
        if count == 0:
            raise OSError(errno.EIO, 'Terminal write returned zero')
        view = view[count:]


def child_settings(fd):
    attrs = termios.tcgetattr(fd)
    canonical = bool(attrs[3] & termios.ICANON)
    password = canonical and not (attrs[3] & termios.ECHO)
    erase = attrs[6][termios.VERASE] if canonical else b'\x7f'
    if isinstance(erase, int):
        erase = bytes([erase])
    return password, erase


def _resize(master):
    try:
        size = fcntl.ioctl(0, termios.TIOCGWINSZ, b'\x00' * 8)
        rows, cols, _, _ = struct.unpack('HHHH', size)
        if rows and cols:
            fcntl.ioctl(master, termios.TIOCSWINSZ, size)
    except OSError:
        pass


def _signal_child(pid, master, signum):
    groups = {pid}
    try:
        groups.add(os.tcgetpgrp(master))
    except OSError:
        pass
    for group in groups:
        if group > 0 and group != os.getpgrp():
            try:
                os.killpg(group, signum)
            except ProcessLookupError:
                pass


def _reap(pid, master):
    for signum in (None, signal.SIGHUP, signal.SIGTERM, signal.SIGKILL):
        if signum is not None:
            _signal_child(pid, master, signum)
        deadline = time.monotonic() + 0.25
        while time.monotonic() < deadline:
            try:
                result, status = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                return 0
            if result:
                code = os.waitstatus_to_exitcode(status)
                return code if code >= 0 else 128 - code
            time.sleep(0.01)
    _, status = os.waitpid(pid, 0)
    code = os.waitstatus_to_exitcode(status)
    return code if code >= 0 else 128 - code


def _mode_file():
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state'))
    return state / 'termux-viet' / f'{os.getpid()}.mode'


def run(command, *, vi=True, modern=False):
    if not command:
        raise ValueError('A child command is required')
    if not os.isatty(0):
        raise ValueError('Interactive mode requires a terminal; use convert for piped text')
    old = termios.tcgetattr(0)
    mode_file = _mode_file()

    def update_mode(mode):
        try:
            mode_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            mode_file.write_text(mode + '\n', encoding='ascii')
            mode_file.chmod(0o600)
        except OSError:
            pass

    with InputProcessor(vi=vi, modern=modern, on_mode=update_mode) as processor:
        pid, master = pty.fork()
        if pid == 0:
            try:
                attrs = termios.tcgetattr(0)
                attrs[0] |= IUTF8
                termios.tcsetattr(0, termios.TCSANOW, attrs)
                os.environ['TERMUX_VIET'] = '1'
                os.environ['TIVI'] = '1'
                os.environ['TERMUX_VIET_MODE_FILE'] = str(mode_file)
                os.execvp(command[0], command)
            except OSError as error:
                write_all(2, f'termux-viet: {error.strerror}: {command[0]}\r\n'.encode())
            os._exit(127)

        stopped = 0
        previous_handlers = {}
        modes = TerminalModes()
        escape_since = None
        wake_read, wake_write = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        previous_wakeup = signal.set_wakeup_fd(wake_write)

        def terminate(signum, _frame):
            nonlocal stopped
            stopped = signum

        try:
            for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT,
                           signal.SIGWINCH, signal.SIGCHLD):
                previous_handlers[signum] = signal.getsignal(signum)
                handler = (lambda *_: _resize(master)) if signum == signal.SIGWINCH else terminate
                signal.signal(signum, (lambda *_: None) if signum == signal.SIGCHLD else handler)
            _resize(master)
            tty.setraw(0, termios.TCSANOW)
            update_mode('VI' if vi else 'EN')
            while not stopped:
                timeout = None
                if escape_since is not None:
                    delay = 0.035 if len(processor.pending) == 1 else 0.25
                    timeout = max(0, escape_since + delay - time.monotonic())
                readable, _, _ = select.select([master, 0, wake_read], [], [], timeout)
                if wake_read in readable:
                    os.read(wake_read, 65536)
                if stopped:
                    break
                if master in readable:
                    try:
                        data = os.read(master, 65536)
                    except OSError as error:
                        if error.errno == errno.EIO:
                            break
                        raise
                    if not data:
                        break
                    alternate = modes.alternate
                    modes.feed(data)
                    if alternate != modes.alternate:
                        processor.reset()
                    write_all(1, data)
                if 0 in readable:
                    data = os.read(0, 4096)
                    if not data:
                        break
                    password, erase = child_settings(master)
                    processor.bypass = password or modes.alternate
                    write_all(master, processor.feed(data, erase=erase))
                if processor.pending and processor.pending[0] == 27 and not processor.paste:
                    now = time.monotonic()
                    if 0 in readable or escape_since is None:
                        escape_since = now
                    timeout = 0.035 if len(processor.pending) == 1 else 0.25
                    if now - escape_since >= timeout:
                        write_all(master, processor.flush_pending())
                        escape_since = None
                else:
                    escape_since = None
        finally:
            termios.tcsetattr(0, termios.TCSANOW, old)
            if stopped:
                _signal_child(pid, master, stopped)
            status = _reap(pid, master)
            os.close(master)
            mode_file.unlink(missing_ok=True)
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
            signal.set_wakeup_fd(previous_wakeup)
            os.close(wake_read)
            os.close(wake_write)
        return 128 + stopped if stopped else status
