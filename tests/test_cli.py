import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cli(*args, text=None, env=None):
    environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
    if env:
        environment.update(env)
    return subprocess.run([sys.executable, '-m', 'termux_viet', *args],
                          input=text, capture_output=True, text=True, env=environment)


class CliTests(unittest.TestCase):
    def test_convert_argument(self):
        result = cli('convert', 'tieengs Vieetj')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'tiếng Việt\n')

    def test_convert_pipe_preserves_newlines(self):
        result = cli('convert', text='tieengs Vieetj\nass')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'tiếng Việt\nas')

    def test_modern_style(self):
        self.assertEqual(cli('convert', '--modern', 'hoaf').stdout, 'hoà\n')

    def test_interactive_without_tty_reports_actionable_error(self):
        result = cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn('convert', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_version_and_doctor(self):
        self.assertEqual(cli('--version').stdout, 'termux-viet 0.1.0\n')
        result = cli('doctor')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('UniKey: OK', result.stdout)

    def test_missing_command_argument_is_usage_error(self):
        self.assertEqual(cli('-c').returncode, 2)
