import os
import select
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from termux_viet.terminal import write_all

from .test_terminal import Relay


class EditorTests(unittest.TestCase):
    def check_editor(self, editor):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'vietnamese.txt'
            if editor == 'nvim':
                command = [editor, '-u', 'NONE', '-i', 'NONE', '-n', '-c', 'startinsert', str(path)]
                ready, finish = b'INSERT', b'\x1c\x0e\x00:wq\r'
            else:
                command = [editor, '-I', '-t', str(path)]
                ready, finish = b'^X', b'\x18'
            relay = Relay(command, {'TERM': 'xterm-256color', 'LC_ALL': 'C.UTF-8'})
            try:
                relay.until(ready)
                write_all(relay.master, b'tieengs Vieetj nuwar nuwax vieetj\x7fn '
                          b'\x00passwords\x00')
                write_all(relay.master, finish)
                deadline = time.monotonic() + 5
                while relay.process.poll() is None and time.monotonic() < deadline:
                    if select.select([relay.master], [], [], .05)[0]:
                        try:
                            os.read(relay.master, 65536)
                        except OSError:
                            break
                self.assertEqual(relay.process.wait(timeout=2), 0)
                self.assertEqual(path.read_text(), 'tiếng Việt nửa nữa viện passwords\n')
            finally:
                relay.close()

    @unittest.skipUnless(shutil.which('nvim'), 'nvim is not installed')
    def test_neovim_insert_mode_saves_live_telex_and_literal_english(self):
        self.check_editor('nvim')

    @unittest.skipUnless(shutil.which('nano'), 'nano is not installed')
    def test_nano_saves_live_telex_and_literal_english(self):
        self.check_editor('nano')
