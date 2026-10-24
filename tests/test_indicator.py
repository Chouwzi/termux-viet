import sys
import tempfile
import time
import unittest
from pathlib import Path

from termux_viet.extra_keys import install_keys, parse_layout
from termux_viet.indicator import ModeKeyIndicator


class IndicatorTests(unittest.TestCase):
    def test_label_changes_and_reload_runs_outside_input_callback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            properties = root / 'termux.properties'
            properties.write_text(install_keys(''))
            completed = root / 'reloaded'
            reload_command = [sys.executable, '-c',
                              'import pathlib,sys,time; time.sleep(.05); '
                              'pathlib.Path(sys.argv[1]).write_text("done")', str(completed)]
            indicator = ModeKeyIndicator(properties, reload_command=reload_command)
            try:
                indicator.update('EN')
                deadline = time.monotonic() + 3
                while not completed.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(completed.exists())
                self.assertEqual(parse_layout(properties.read_text())[0][0]['display'], 'EN')
                completed.unlink()
                indicator.update('VI')
                while not completed.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(completed.exists())
                self.assertEqual(parse_layout(properties.read_text())[0][0]['display'], 'VI')
            finally:
                indicator.close()

    def test_unmanaged_configuration_is_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'termux.properties'
            original = 'extra-keys=[["ESC","LEFT","RIGHT"]]\n'
            path.write_text(original)
            indicator = ModeKeyIndicator(path, reload_command=[])
            indicator.update('EN')
            indicator.close()
            self.assertEqual(path.read_text(), original)

    def test_invalid_configuration_cannot_break_mode_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'termux.properties'
            original = 'extra-keys = [broken termux-viet\n'
            path.write_text(original)
            indicator = ModeKeyIndicator(path, reload_command=[])
            indicator.update('EN')
            indicator.close()
            self.assertEqual(path.read_text(), original)

    def test_non_utf8_configuration_does_not_break_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'termux.properties'
            path.write_bytes(b'\xfftermux-viet')
            indicator = ModeKeyIndicator(path, reload_command=[])
            indicator.update('EN')
            indicator.close()
            self.assertEqual(path.read_bytes(), b'\xfftermux-viet')
