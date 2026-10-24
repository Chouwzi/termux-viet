import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from termux_viet.extra_keys import parse_layout

ROOT = Path(__file__).resolve().parents[1]
LEGACY = '''# old keyboard
if [ -z "$TIVI" ] && [ -t 0 ] && [ -x "$HOME/.local/bin/tivi" ] \\
   && [ ! -f "$HOME/.config/tivi/off" ]; then
    TIVI=1 "$HOME/.local/bin/tivi" "${SHELL:-/bin/bash}"
fi
'''


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='termux-viet-test-')
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.environment = dict(os.environ, HOME=str(self.home),
                                XDG_CONFIG_HOME=str(self.home / '.config'),
                                XDG_STATE_HOME=str(self.home / '.local/state'))
        self.environment.pop('PYTHONPATH', None)
        self.launcher = self.home / '.local/bin/termux-viet'

    def install(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'), *args],
                              capture_output=True, text=True, env=self.environment)

    def test_install_into_home_with_spaces_and_convert(self):
        self.home = self.home / 'space in home'
        self.home.mkdir()
        self.environment['HOME'] = str(self.home)
        self.launcher = self.home / '.local/bin/termux-viet'
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([str(self.launcher), 'convert', 'nuwar'],
                                capture_output=True, text=True, env=self.environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'nửa\n')
        self.assertFalse((self.home / '.bashrc').exists())

    def test_migration_is_backed_up_and_reinstall_is_idempotent(self):
        original = 'export MY_CUSTOM_VALUE=kept\n' + LEGACY
        bashrc = self.home / '.bashrc'
        bashrc.write_text(original)
        for _ in range(2):
            result = self.install('--auto-start', '--migrate')
            self.assertEqual(result.returncode, 0, result.stderr)
        content = bashrc.read_text()
        self.assertEqual(content.count('# >>> termux-viet >>>'), 1)
        self.assertIn('MY_CUSTOM_VALUE=kept', content)
        self.assertNotIn('TIVI=1 "$HOME/.local/bin/tivi"', content)
        backups = list((self.home / '.local/state/termux-viet/backups').glob('*/.bashrc'))
        self.assertTrue(any(path.read_text() == original for path in backups))
        result = subprocess.run([str(self.launcher), 'uninstall'],
                                capture_output=True, text=True, env=self.environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.launcher.exists())
        self.assertEqual(bashrc.read_text(), 'export MY_CUSTOM_VALUE=kept\n# old keyboard\n')
        self.assertTrue(backups[0].exists())

    def test_termux_keys_preserve_unrelated_settings(self):
        directory = self.home / '.termux'
        directory.mkdir()
        properties = directory / 'termux.properties'
        original = "bell-character=ignore\nextra-keys = [['ESC'], \\\n ['LEFT']]\nterminal-margin-horizontal=4\n"
        properties.write_text(original)
        result = self.install('--termux-keys')
        self.assertEqual(result.returncode, 0, result.stderr)
        content = properties.read_text()
        self.assertIn('bell-character=ignore', content)
        self.assertIn('terminal-margin-horizontal=4', content)
        self.assertEqual(content.count('extra-keys ='), 1)
        button = parse_layout(content)[0][0]
        self.assertEqual(button['display'], 'VI')
        self.assertEqual(button['macro'], 'CTRL SPACE')
        properties.write_text(content + 'new-setting=keep\n')
        result = subprocess.run([str(self.launcher), 'uninstall'], capture_output=True,
                                text=True, env=self.environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(properties.read_text(), original + 'new-setting=keep\n')

    def test_custom_prefix_uninstall_finds_own_installation(self):
        prefix = self.home / 'custom prefix'
        result = self.install('--prefix', str(prefix))
        self.assertEqual(result.returncode, 0, result.stderr)
        launcher = prefix / 'bin/termux-viet'
        result = subprocess.run([str(launcher), 'uninstall'], capture_output=True,
                                text=True, env=self.environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(launcher.exists())
        self.assertFalse((prefix / 'share/termux-viet').exists())

    def test_unrelated_legacy_reference_is_not_removed(self):
        original = 'alias old_keyboard="tivi"\nif true; then\n  echo tivi\nfi\n'
        bashrc = self.home / '.bashrc'
        bashrc.write_text(original)
        result = self.install('--migrate')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(bashrc.read_text(), original)
