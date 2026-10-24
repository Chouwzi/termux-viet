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


def _write_pending(fd, queue):
    try:
        count = os.write(fd, queue)
    except (BlockingIOError, InterruptedError):
        return
    if count == 0:
        raise OSError(errno.EIO, 'Terminal write returned zero')
    del queue[:count]


def _relay(pid, master, processor, wake_read, stopped):
    modes = TerminalModes()
    to_child = bytearray()
    to_screen = bytearray(b'\x1b[?2004h')
    escape_since = None
    child_status = None
    drain_deadline = None
    eof = False
    limit = 1024 * 1024
    while not stopped():
        if child_status is None:
            result, status = os.waitpid(pid, os.WNOHANG)
            if result:
                child_status = status
                drain_deadline = time.monotonic() + .25
                to_child.clear()
        if (eof and not to_screen) or (
                drain_deadline is not None and time.monotonic() >= drain_deadline):
            break
        readers = [wake_read]
        if not eof and len(to_screen) < limit:
            readers.append(master)
        if child_status is None and not eof and len(to_child) < limit:
            readers.append(0)
        writers = ([master] if to_child and not eof else []) + ([1] if to_screen else [])
        timeout = None
        if escape_since is not None:
            delay = .035 if len(processor.pending) == 1 else .25
            timeout = max(0, escape_since + delay - time.monotonic())
        if drain_deadline is not None:
            remaining = max(0, drain_deadline - time.monotonic())
            timeout = remaining if timeout is None else min(timeout, remaining)
        readable, writable, _ = select.select(readers, writers, [], timeout)
        if wake_read in readable:
            os.read(wake_read, 65536)
        if stopped():
            break
        if 1 in writable:
            _write_pending(1, to_screen)
        if master in writable:
            try:
                _write_pending(master, to_child)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                to_child.clear()
        if master in readable:
            try:
                data = os.read(master, 65536)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                data = b''
            if not data:
                eof = True
            else:
                alternate = modes.alternate
                generation = modes.paste_generation
                modes.feed(data)
                if alternate != modes.alternate:
                    processor.reset()
                to_screen.extend(data)
                if modes.paste_generation != generation and not modes.bracketed_paste:
                    to_screen.extend(b'\x1b[?2004h')
        if 0 in readable:
            data = os.read(0, 4096)
            if not data:
                break
            password, erase = child_settings(master)
            processor.bypass = password or modes.alternate
            processor.paste_markers = modes.bracketed_paste
            to_child.extend(processor.feed(data, erase=erase))
        if processor.escape_pending:
            now = time.monotonic()
            if 0 in readable or escape_since is None:
                escape_since = now
            delay = .035 if len(processor.pending) == 1 else .25
            if now - escape_since >= delay:
                to_child.extend(processor.flush_pending())
                escape_since = None
        else:
            escape_since = None
    return child_status


def run(command, *, vi=True, modern=False, spell_check=True):
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

    with InputProcessor(vi=vi, modern=modern, spell_check=spell_check,
                        on_mode=update_mode) as processor:
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
        child_status = None
        screen_flags = fcntl.fcntl(1, fcntl.F_GETFL)
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
            os.set_blocking(master, False)
            os.set_blocking(1, False)
            update_mode('VI' if vi else 'EN')
            child_status = _relay(pid, master, processor, wake_read, lambda: stopped)
        finally:
            try:
                termios.tcsetattr(0, termios.TCSANOW, old)
                os.write(1, b'\x1b[?2004l')
            except OSError:
                pass
            fcntl.fcntl(1, fcntl.F_SETFL, screen_flags)
            if stopped:
                _signal_child(pid, master, stopped)
            if child_status is None:
                status = _reap(pid, master)
            else:
                status = os.waitstatus_to_exitcode(child_status)
                status = status if status >= 0 else 128 - status
            os.close(master)
            mode_file.unlink(missing_ok=True)
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
            signal.set_wakeup_fd(previous_wakeup)
            os.close(wake_read)
            os.close(wake_write)
        return 128 + stopped if stopped else status
