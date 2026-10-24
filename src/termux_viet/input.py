"""Streaming terminal input; paste and opaque control strings stay literal."""

from .engine import Engine

ESC = 27
PASTE_END = b'\x1b[201~'
MAX_SEQUENCE = 4096


def _string_end(data, *, bell=False, start=0):
    end = data.find(b'\x1b\\', start)
    candidates = [end + 2] if end >= 0 else []
    if bell:
        end = data.find(b'\x07', start)
        if end >= 0:
            candidates.append(end + 1)
    return min(candidates) if candidates else None


def _escape_end(data):
    if len(data) < 2:
        return None
    second = data[1]
    if second == ord(' '):
        return 2
    if second in (ord('['), ord('O')):
        for index in range(2, len(data)):
            if 0x40 <= data[index] <= 0x7e:
                end = index + 1
                if data[:end] == b'\x1b[M':
                    return end + 3 if len(data) >= end + 3 else None
                return end
        return None
    if second in b']PX^_':
        return _string_end(data, bell=second == ord(']'), start=2)
    if 0x20 <= second <= 0x2f:
        for index in range(2, len(data)):
            if 0x30 <= data[index] <= 0x7e:
                return index + 1
        return None
    if second >= 128:
        width = _utf8_width(second)
        return 1 + width if len(data) >= 1 + width else None
    return 2


def _utf8_width(first):
    if 0xc2 <= first <= 0xdf:
        return 2
    if 0xe0 <= first <= 0xef:
        return 3
    if 0xf0 <= first <= 0xf4:
        return 4
    return 1


class InputProcessor:
    def __init__(self, *, vi=True, modern=False, spell_check=True, bypass=False,
                 on_mode=None, paste_markers=True):
        self.engine = Engine(modern=modern, spell_check=spell_check)
        self.vi = vi
        self._bypass = bypass
        self.on_mode = on_mode
        self.pending = bytearray()
        self.paste = False
        self.paste_markers = paste_markers
        self._current_paste_markers = True
        self._opaque = False
        self._opaque_bel = False
        self._literal_word = False
        self._composing = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.engine.close()

    def reset(self):
        self.engine.reset()
        self._literal_word = False
        self._composing = False

    @property
    def bypass(self):
        return self._bypass

    @bypass.setter
    def bypass(self, value):
        if value != self._bypass:
            self.reset()
        self._bypass = value

    def set_mode(self, vi):
        self.reset()
        if vi != self.vi:
            self.vi = vi
            if self.on_mode:
                self.on_mode('VI' if vi else 'EN')

    def flush_pending(self):
        output = bytes(self.pending)
        self.pending.clear()
        self.reset()
        return output

    @property
    def escape_pending(self):
        return bool(self.pending and self.pending[0] == ESC and not self.paste
                    and not self._opaque)

    def feed(self, data, *, erase=b'\x7f'):
        self.pending.extend(data)
        output = bytearray()
        while self.pending:
            if self.paste:
                end = self.pending.find(PASTE_END)
                if end >= 0:
                    output.extend(self.pending[:end])
                    if self._current_paste_markers:
                        output.extend(PASTE_END)
                    del self.pending[:end + len(PASTE_END)]
                    self.paste = False
                    self.reset()
                    continue
                keep = 0
                for length in range(1, min(len(self.pending), len(PASTE_END) - 1) + 1):
                    if self.pending[-length:] == PASTE_END[:length]:
                        keep = length
                count = len(self.pending) - keep
                output.extend(self.pending[:count])
                del self.pending[:count]
                break
            if self._opaque:
                end = _string_end(self.pending, bell=self._opaque_bel)
                if end is not None:
                    output.extend(self.pending[:end])
                    del self.pending[:end]
                    self._opaque = False
                    continue
                count = len(self.pending) - (self.pending[-1] == ESC)
                output.extend(self.pending[:count])
                del self.pending[:count]
                break

            first = self.pending[0]
            if first == ESC:
                if len(self.pending) >= 2 and self.pending[1] == ESC:
                    output.append(ESC)
                    del self.pending[0]
                    self.reset()
                    continue
                end = _escape_end(self.pending)
                if end is None:
                    if len(self.pending) > MAX_SEQUENCE:
                        self._opaque = len(self.pending) > 1 and self.pending[1] in b']PX^_'
                        self._opaque_bel = self.pending[1] == ord(']')
                        keep = self._opaque and self.pending[-1] == ESC
                        count = len(self.pending) - keep
                        output.extend(self.pending[:count])
                        del self.pending[:count]
                        self.reset()
                    break
                sequence = bytes(self.pending[:end])
                del self.pending[:end]
                self.reset()
                if sequence == b'\x1b[200~':
                    self.paste = True
                    self._current_paste_markers = self.paste_markers
                    if self._current_paste_markers:
                        output.extend(sequence)
                elif sequence == b'\x1b[1;5E':
                    self.set_mode(False)
                elif sequence == b'\x1b[1;5V':
                    self.set_mode(True)
                elif sequence in (b'\x1b ', b'\x1b\\'):
                    self.set_mode(not self.vi)
                else:
                    output.extend(sequence)
                continue

            if first >= 128:
                width = _utf8_width(first)
                available = min(width, len(self.pending))
                invalid = next((i for i in range(1, available)
                                if not 0x80 <= self.pending[i] <= 0xbf), None)
                if invalid is not None:
                    width = invalid
                elif len(self.pending) < width:
                    break
                output.extend(self.pending[:width])
                del self.pending[:width]
                self.reset()
                self._literal_word = width > 1 and invalid is None
                continue

            del self.pending[0]
            if first == 0:
                self.set_mode(not self.vi)
            elif first in (8, 127):
                if self.vi and not self.bypass and self._composing:
                    edit = self.engine.backspace()
                    output.extend(erase * edit.erase + edit.text.encode())
                else:
                    self.reset()
                    output.append(first)
            elif (65 <= first <= 90 or 97 <= first <= 122):
                if self.vi and not self.bypass and not self._literal_word:
                    edit = self.engine.key(chr(first))
                    output.extend(erase * edit.erase + edit.text.encode())
                    self._composing = True
                else:
                    output.append(first)
            else:
                self.reset()
                output.append(first)
        return bytes(output)


class TerminalModes:
    """Observe DEC mode changes without interpreting text inside OSC/DCS."""

    def __init__(self):
        self.alternate = False
        self.bracketed_paste = False
        self.paste_generation = 0
        self._state = 'text'
        self._csi = bytearray()
        self._string_esc = False
        self._string_bel = False

    def feed(self, data):
        for byte in data:
            if self._state == 'string':
                if (self._string_bel and byte == 7) or (self._string_esc and byte == ord('\\')):
                    self._state = 'text'
                self._string_esc = byte == ESC
            elif self._state == 'csi':
                if 0x40 <= byte <= 0x7e:
                    self._mode(bytes(self._csi), byte)
                    self._state = 'text'
                    self._csi.clear()
                elif len(self._csi) < 256:
                    self._csi.append(byte)
                else:
                    self._state = 'text'
                    self._csi.clear()
            elif self._state == 'esc':
                if byte == ord('['):
                    self._state = 'csi'
                elif byte in b']PX^_':
                    self._state = 'string'
                    self._string_esc = False
                    self._string_bel = byte == ord(']')
                else:
                    self._state = 'esc' if byte == ESC else 'text'
            elif byte == ESC:
                self._state = 'esc'

    def _mode(self, parameters, final):
        if not parameters.startswith(b'?') or final not in b'hl':
            return
        enabled = final == ord('h')
        for code in parameters[1:].split(b';'):
            if code in (b'47', b'1047', b'1049'):
                self.alternate = enabled
            elif code == b'2004':
                self.bracketed_paste = enabled
                self.paste_generation += 1
