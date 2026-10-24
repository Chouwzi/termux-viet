"""Preserve Termux layouts and manage the current-mode language key."""

import ast
import fcntl
import json
import os
import re
import tempfile
from pathlib import Path

DEFINITION = re.compile(r'(?m)^[ \t]*extra-keys[ \t]*=(?:[^\n]*\\\r?\n)*[^\n]*(?:\n|$)')
MARKER = 'termux-viet'
DEFAULT = [['ESC', '/', '-', 'HOME', 'UP', 'END', 'PGUP'],
           ['TAB', 'CTRL', 'ALT', 'LEFT', 'DOWN', 'RIGHT', 'PGDN']]


def definition(text):
    matches = list(DEFINITION.finditer(text))
    return matches[-1].group() if matches else ''


def _literal(node, *, key=False):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, type(None))):
        return node.value
    if isinstance(node, ast.Name):
        if key:
            return node.id
        if node.id in ('true', 'false', 'null'):
            return {'true': True, 'false': False, 'null': None}[node.id]
    if isinstance(node, ast.List):
        return [_literal(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {_literal(k, key=True): _literal(v) for k, v in zip(node.keys, node.values)}
    raise ValueError('Unsupported extra-keys expression; existing layout was preserved')


def _property_value(value):
    value = re.sub(
        r'(\\+)\r?\n[ \t\f]*',
        lambda match: match[1][:-1] if len(match[1]) % 2 else match[0],
        value,
    )
    output = []
    index = 0
    while index < len(value):
        char = value[index]
        index += 1
        if char == '\\':
            if index == len(value):
                raise ValueError('Incomplete property escape')
            char = value[index]
            index += 1
            if char == 'u':
                code = value[index:index + 4]
                if len(code) != 4 or not all(c in '0123456789abcdefABCDEF' for c in code):
                    raise ValueError('Invalid Unicode property escape')
                char = chr(int(code, 16))
                index += 4
            else:
                char = {'t': '\t', 'n': '\n', 'r': '\r', 'f': '\f'}.get(char, char)
        output.append(char)
    return ''.join(output).encode('utf-16-le', 'surrogatepass').decode('utf-16-le')


def parse_layout(text):
    value = definition(text)
    if not value:
        return [row.copy() for row in DEFAULT]
    value = _property_value(value.split('=', 1)[1]).strip()
    try:
        layout = _literal(ast.parse(value, mode='eval').body)
    except (SyntaxError, TypeError, RecursionError) as error:
        raise ValueError('Invalid extra-keys configuration; existing layout was preserved') from error
    if (not isinstance(layout, list) or not layout or
            any(not isinstance(row, list) or not row for row in layout) or
            any(not isinstance(button, (str, dict)) for row in layout for button in row)):
        raise ValueError('extra-keys must contain rows of buttons')
    return layout


def _owned(button):
    return isinstance(button, dict) and button.get(MARKER) == 'toggle'


def _replace(text, layout):
    value = json.dumps(layout, ensure_ascii=False, separators=(',', ':')).replace('\\', '\\\\')
    new = 'extra-keys = ' + value + '\n'
    if not DEFINITION.search(text):
        return text + ('' if not text or text.endswith('\n') else '\n') + new
    first = True

    def replace(_match):
        nonlocal first
        if first:
            first = False
            return new
        return ''
    return DEFINITION.sub(replace, text)


def install_keys(text, mode='VI'):
    layout = parse_layout(text)
    for index, row in enumerate(layout):
        repaired = []
        for button in row:
            if _owned(button):
                continue
            if isinstance(button, dict):
                legacy = (button.get('macro'), button.get('display'))
                if legacy == ('ALT [ 1 ; 5 E', 'EN'):
                    button = 'LEFT'
                elif legacy == ('ALT [ 1 ; 5 V', 'VI'):
                    button = 'RIGHT'
            repaired.append(button)
        layout[index] = repaired
    toggle = {'macro': 'CTRL SPACE', 'display': mode, MARKER: 'toggle'}
    for row in layout:
        for index, button in enumerate(row):
            if button == 'ESC' or isinstance(button, dict) and button.get('key') == 'ESC':
                row.insert(index, toggle)
                return _replace(text, layout)
    layout[0].insert(0, toggle)
    return _replace(text, layout)


def _without_toggle(layout):
    return [[button for button in row if not _owned(button)] for row in layout]


def uninstall_keys(text, previous, installed):
    current = parse_layout(text)
    if not any(_owned(button) for row in current for button in row):
        return text
    if installed and _without_toggle(current) == _without_toggle(parse_layout(installed)):
        return DEFINITION.sub(lambda _: previous, text, count=1)
    return _replace(text, _without_toggle(current))


def apply_mode(path, mode):
    if mode not in ('VI', 'EN'):
        raise ValueError('Mode must be VI or EN')
    path = Path(path).resolve()
    if not path.exists():
        return False
    with path.with_name('.termux-viet-keys.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        original = path.read_text(encoding='utf-8')
        if len(original) > 65536:
            return False
        layout = parse_layout(original)
        target = mode
        changed = False
        for row in layout:
            for button in row:
                if _owned(button) and button.get('display') != target:
                    button['display'] = target
                    changed = True
        if not changed:
            return False
        descriptor, temporary = tempfile.mkstemp(prefix='.termux-viet-', dir=path.parent)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                stream.write(_replace(original, layout))
            os.chmod(temporary, path.stat().st_mode & 0o777)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return True
