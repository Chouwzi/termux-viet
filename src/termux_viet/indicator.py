"""Coalesce language-key refreshes away from the input path."""

import shutil
import subprocess
import threading
from pathlib import Path

from .extra_keys import MARKER, apply_mode


class ModeKeyIndicator:
    def __init__(self, properties=None, *, reload_command=None, enabled=True):
        self.path = Path(properties) if properties else Path.home() / '.termux/termux.properties'
        try:
            self.enabled = enabled and MARKER in self.path.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            self.enabled = False
        command = shutil.which('termux-reload-settings')
        self.command = ([command] if command else []) if reload_command is None else reload_command
        self._condition = threading.Condition()
        self._pending = None
        self._closed = False
        self._thread = None

    def update(self, mode):
        if not self.enabled:
            return
        with self._condition:
            if self._closed:
                return
            self._pending = mode
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, daemon=True,
                                                name='termux-viet-mode-key')
                self._thread.start()
            self._condition.notify()

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closed or self._pending is not None)
                if self._closed:
                    return
                mode, self._pending = self._pending, None
            try:
                changed = apply_mode(self.path, mode)
                if changed and self.command:
                    subprocess.run(self.command, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=.75, check=False)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                continue

    def close(self):
        with self._condition:
            self._closed = True
            self._pending = None
            self._condition.notify()
        if self._thread is not None:
            self._thread.join(timeout=1)
