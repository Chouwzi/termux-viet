"""Per-instance UniKey composition with Unicode edits."""

import ctypes
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True, slots=True)
class Edit:
    erase: int
    text: str

    def apply(self, text):
        return (text[:-self.erase] if self.erase else text) + self.text


def _load_library():
    path = Path(__file__).with_name('libtermux_viet.so')
    if not path.is_file():
        raise RuntimeError('Native engine missing. Run: python scripts/build.py')
    lib = ctypes.CDLL(str(path))
    lib.tv_create.argtypes = [ctypes.c_int]
    lib.tv_create.restype = ctypes.c_void_p
    lib.tv_destroy.argtypes = [ctypes.c_void_p]
    lib.tv_destroy.restype = None
    lib.tv_reset.argtypes = [ctypes.c_void_p]
    lib.tv_reset.restype = None
    lib.tv_edit.argtypes = [ctypes.c_void_p, ctypes.c_int,
                           ctypes.POINTER(ctypes.c_int), ctypes.c_void_p, ctypes.c_int]
    lib.tv_edit.restype = ctypes.c_int
    return lib


class Engine:
    def __init__(self, *, modern=False):
        self._lib = _load_library()
        self._handle = self._lib.tv_create(modern)
        if not self._handle:
            raise MemoryError('Unable to initialize UniKey')
        self._output = ctypes.create_string_buffer(1024)
        self._backs = ctypes.c_int()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self._handle:
            self._lib.tv_destroy(self._handle)
            self._handle = None

    def reset(self):
        if not self._handle:
            raise RuntimeError('Engine is closed')
        self._lib.tv_reset(self._handle)

    def _edit(self, key):
        if not self._handle:
            raise RuntimeError('Engine is closed')
        size = self._lib.tv_edit(self._handle, key, ctypes.byref(self._backs),
                                 self._output, len(self._output))
        if size < 0 or size > len(self._output):
            raise RuntimeError('UniKey could not process input')
        return Edit(self._backs.value, self._output.raw[:size].decode('utf-8'))

    def key(self, char):
        if len(char) != 1:
            raise ValueError('Expected one character')
        if not char.isascii() or ord(char) < 32 or ord(char) == 127:
            self.reset()
            return Edit(0, char)
        return self._edit(ord(char))

    def backspace(self):
        return self._edit(-1)


def convert(text, *, modern=False):
    with Engine(modern=modern) as engine:
        def word(match):
            raw = match.group()
            if not raw.isascii():
                return raw
            engine.reset()
            output = []
            for char in raw:
                edit = engine.key(char)
                if edit.erase:
                    del output[-edit.erase:]
                output.extend(edit.text)
            return ''.join(output)

        return re.sub(r'[^\W\d_]+', word, text)
