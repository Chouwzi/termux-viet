import unittest

from termux_viet.input import InputProcessor, TerminalModes


def display(data):
    text = ''
    for char in data.decode():
        text = text[:-1] if char == '\x7f' else text + char
    return text


class InputTests(unittest.TestCase):
    def process(self, chunks, **kwargs):
        with InputProcessor(**kwargs) as processor:
            output = b''.join(processor.feed(chunk) for chunk in chunks)
            return output + processor.flush_pending(), processor.vi

    def test_live_composition_and_backspace(self):
        output, _ = self.process([b'vieetj\x7fn '])
        self.assertEqual(display(output), 'viện ')

    def test_all_utf8_split_points_preserve_bytes(self):
        raw = 'đã có tiếng Việt 🙂 ass'.encode()
        for point in range(len(raw) + 1):
            with self.subTest(point=point):
                output, _ = self.process([raw[:point], raw[point:]])
                self.assertEqual(display(output), 'đã có tiếng Việt 🙂 as')

    def test_paste_preserves_controls_and_does_not_toggle(self):
        raw = b'\x1b[200~passwords\x00\x1b[1;5E\xff\x1b[201~'
        for point in range(len(raw) + 1):
            with self.subTest(point=point):
                output, vi = self.process([raw[:point], raw[point:]])
                self.assertEqual(output, raw)
                self.assertTrue(vi)

    def test_escape_sequences_preserved_at_every_split(self):
        for raw in [b'\x1b[A', b'\x1b[1;5D', b'\x1bOP', b'\x1b]x\x07',
                    b'\x1bPtest\x1b\\', b'\x1bA', b'\x1b(B', b'\x1b[Mabc']:
            for point in range(len(raw) + 1):
                with self.subTest(raw=raw, point=point):
                    output, vi = self.process([raw[:point], raw[point:]])
                    self.assertEqual(output, raw)
                    self.assertTrue(vi)

    def test_timeout_never_drops_incomplete_escape_or_utf8(self):
        for raw in [b'\x1b', b'\x1b[1;', b'\x1b]incomplete', b'\xe1\xbb']:
            output, _ = self.process([raw])
            self.assertEqual(output, raw)

    def test_controls_reset_composition(self):
        for control in [b'\x01', b'\x05', b'\x02', b'\x17', b'\x03', b'\t', b'\r']:
            with self.subTest(control=control):
                output, _ = self.process([b'as', control, b'f'])
                self.assertTrue(output.endswith(control + b'f'))

    def test_mode_hotkeys_and_legacy_termux_buttons(self):
        for toggle in [b'\x00', b'\x1b ', b'\x1b\\']:
            output, vi = self.process([toggle, b'ass', toggle, b'ass'])
            self.assertEqual(display(output), 'assas')
            self.assertTrue(vi)
        output, vi = self.process([b'\x1b[1;5Eass\x1b[1;5Vass'])
        self.assertEqual(display(output), 'assas')
        self.assertTrue(vi)

    def test_en_and_bypass_are_literal(self):
        for options in [{'vi': False}, {'bypass': True}]:
            raw = b'ass\x7f\x01\xff'
            output, _ = self.process([raw], **options)
            self.assertEqual(output, raw)

    def test_unicode_word_cannot_be_rewritten_by_ascii_suffix(self):
        output, _ = self.process(['đass '.encode(), b'ass'])
        self.assertEqual(display(output), 'đass as')

    def test_long_control_string_uses_bounded_memory(self):
        raw = b'\x1b]' + b'a' * 50000 + b'\x07'
        output, _ = self.process([raw])
        self.assertEqual(output, raw)

    def test_incomplete_utf8_then_ascii_does_not_swallow_ascii(self):
        output, _ = self.process([b'\xe1', b'ass'])
        self.assertEqual(output, b'\xe1a\x7f\xc3\xa1\x7fas')


class TerminalModeTests(unittest.TestCase):
    def test_alternate_screen_is_observed_across_chunks(self):
        for code in (b'47', b'1047', b'1049'):
            raw = b'\x1b[?' + code + b'h'
            for point in range(len(raw) + 1):
                modes = TerminalModes()
                modes.feed(raw[:point])
                modes.feed(raw[point:])
                self.assertTrue(modes.alternate)
                modes.feed(b'\x1b[?' + code + b'l')
                self.assertFalse(modes.alternate)

    def test_osc_content_does_not_change_screen_mode(self):
        modes = TerminalModes()
        modes.feed(b'\x1b]0;title \x1b[?1049h\x07')
        self.assertFalse(modes.alternate)

    def test_bracketed_paste_mode_is_observed(self):
        modes = TerminalModes()
        modes.feed(b'\x1b[?2004h')
        self.assertTrue(modes.bracketed_paste)
        modes.feed(b'\x1b[?2004l')
        self.assertFalse(modes.bracketed_paste)
