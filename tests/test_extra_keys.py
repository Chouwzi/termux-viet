import json
import tempfile
import unittest
from pathlib import Path

from termux_viet.extra_keys import apply_mode, install_keys, parse_layout, uninstall_keys

DEFAULT = "extra-keys = [['ESC','/','-','HOME','UP','END','PGUP']," \
          "['TAB','CTRL','ALT','LEFT','DOWN','RIGHT','PGDN']]\n"
LEGACY = "extra-keys = [['ESC','/','-','HOME','UP','END','PGUP']," \
         "['TAB','CTRL','ALT',{macro:'ALT [ 1 ; 5 E',display:'EN'},'DOWN'," \
         "{macro:'ALT [ 1 ; 5 V',display:'VI'},'PGDN']]\n"


class ExtraKeyTests(unittest.TestCase):
    def test_toggle_precedes_escape_and_preserves_default_keys(self):
        original = parse_layout(DEFAULT)
        installed = parse_layout(install_keys(DEFAULT))
        button = installed[0].pop(0)
        self.assertEqual(button['macro'], 'CTRL SPACE')
        self.assertEqual(button['display'], 'VI')
        self.assertEqual(installed, original)

    def test_legacy_arrow_replacements_are_repaired(self):
        installed = parse_layout(install_keys(LEGACY))
        self.assertEqual(installed[1], ['TAB', 'CTRL', 'ALT', 'LEFT', 'DOWN', 'RIGHT', 'PGDN'])
        self.assertEqual(installed[0][1], 'ESC')

    def test_custom_popups_and_settings_survive_repeated_install(self):
        custom = "bell-character=ignore\nextra-keys=[[{key:'ESC',popup:{macro:'CTRL c'," \
                 "display:'key: example'}},'F1'],['LEFT','RIGHT']]\nmargin=2\n"
        once = install_keys(custom)
        self.assertEqual(install_keys(once), once)
        layout = parse_layout(once)
        self.assertEqual(layout[0][1]['popup']['display'], 'key: example')
        self.assertEqual(layout[1], ['LEFT', 'RIGHT'])
        self.assertIn('bell-character=ignore\n', once)
        self.assertIn('margin=2\n', once)

    def test_malformed_or_executable_configuration_is_never_evaluated(self):
        for text in ['extra-keys=__import__("os").getcwd()\n', 'extra-keys=[broken\n']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                install_keys(text)

    def test_java_property_escaping_keeps_backslash_and_quote_buttons(self):
        text = r'''extra-keys = [["ESC","\\\\",{key:"QUOTE",display:"a\\"b"}],["LEFT","RIGHT"]]'''
        expected = [['ESC', '\\', {'key': 'QUOTE', 'display': 'a"b'}], ['LEFT', 'RIGHT']]
        self.assertEqual(parse_layout(text), expected)
        installed = parse_layout(install_keys(text))
        installed[0].pop(0)
        self.assertEqual(installed, expected)

    def test_property_continuation_discards_leading_indentation(self):
        text = "extra-keys=[[{key:'ESC',display:'a\\\n    b'},'LEFT','RIGHT']]\n"
        self.assertEqual(parse_layout(text)[0][0]['display'], 'ab')
        self.assertEqual(parse_layout(install_keys(text))[0][1]['display'], 'ab')

    def test_mode_updates_only_owned_button_and_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'termux.properties'
            path.write_text('bell-character=ignore\n' + install_keys(DEFAULT))
            self.assertTrue(apply_mode(path, 'EN'))
            layout = parse_layout(path.read_text())
            self.assertEqual(layout[0][0]['display'], 'EN')
            self.assertFalse(apply_mode(path, 'EN'))
            self.assertTrue(apply_mode(path, 'VI'))
            self.assertEqual(parse_layout(path.read_text())[0][0]['display'], 'VI')
            self.assertIn('bell-character=ignore\n', path.read_text())
            path.write_text(DEFAULT)
            self.assertFalse(apply_mode(path, 'EN'))
            self.assertEqual(path.read_text(), DEFAULT)

    def test_uninstall_restores_previous_keys_after_dynamic_label_update(self):
        installed = install_keys(DEFAULT)
        changed = json.loads(json.dumps(parse_layout(installed)))
        changed[0][0]['display'] = 'EN'
        text = 'extra-keys=' + json.dumps(changed) + '\nnew-setting=keep\n'
        self.assertEqual(uninstall_keys(text, DEFAULT, installed), DEFAULT + 'new-setting=keep\n')

    def test_uninstall_keeps_new_user_buttons(self):
        installed = install_keys(DEFAULT)
        layout = parse_layout(installed)
        layout[1].append('F2')
        text = 'extra-keys=' + json.dumps(layout) + '\n'
        result = parse_layout(uninstall_keys(text, DEFAULT, installed))
        self.assertEqual(result[0][0], 'ESC')
        self.assertEqual(result[1][-1], 'F2')
