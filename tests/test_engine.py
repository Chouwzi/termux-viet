import unittest

from termux_viet.engine import Engine, convert


class EngineTests(unittest.TestCase):
    def test_telex_regressions(self):
        cases = {
            'nuwar': 'nửa', 'nuawr': 'nửa', 'nuwax': 'nữa',
            'aaa': 'aa', 'ddd': 'dd', 'ass': 'as', 'dd': 'đ',
            'khoeo': 'khoeo', 'khoeof': 'khoèo', 'ngoeoj': 'ngoẹo',
            'tieengs Vieetj': 'tiếng Việt', 'Tooi': 'Tôi',
            'TOOI': 'TÔI', 'Vieetj': 'Việt', 'DDUOWNGF': 'ĐƯỜNG',
            'dduowcj': 'được', 'dduwowngf': 'đường',
            'nguowif': 'người', 'quas': 'quá', 'gif': 'gì',
            'giar': 'giả', 'quyeefn': 'quyền', 'nghieeng': 'nghiêng',
            'toanfs': 'toán', 'toansz': 'toan', 'vayaj': 'vậy',
            'vieet': 'viêt', 'dduocj': 'đuọc',
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(convert(raw), expected)

    def test_tone_style(self):
        self.assertEqual(convert('hoaf thuyr khoer'), 'hòa thủy khỏe')
        self.assertEqual(convert('hoaf thuyr khoer', modern=True), 'hoà thuỷ khoẻ')

    def test_backspace_deletes_displayed_character(self):
        with Engine() as engine:
            text = ''
            for key in 'vieetj':
                text = engine.key(key).apply(text)
            self.assertEqual(text, 'việt')
            text = engine.backspace().apply(text)
            self.assertEqual(text, 'việ')
            self.assertEqual(engine.key('n').apply(text), 'viện')

    def test_instances_are_independent(self):
        with Engine() as first, Engine() as second:
            self.assertEqual(first.key('a').text, 'a')
            self.assertEqual(second.key('d').text, 'd')
            self.assertEqual(first.key('s').apply('a'), 'á')
            self.assertEqual(second.key('d').apply('d'), 'đ')
            first.reset()
            self.assertEqual(first.key('s').text, 's')

    def test_unicode_is_preserved_and_ends_composition(self):
        self.assertEqual(convert('đã có tiếng Việt 🙂 ass'), 'đã có tiếng Việt 🙂 as')

    def test_long_input_has_bounded_engine_state(self):
        self.assertEqual(convert('b' * 20000), 'b' * 20000)


if __name__ == '__main__':
    unittest.main()
