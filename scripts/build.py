#!/usr/bin/env python3
"""Build the bundled UniKey bridge without package downloads."""

import os
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    destination = ROOT / 'src/termux_viet/libtermux_viet.so'
    temporary = destination.with_suffix('.tmp.so')
    compiler = shlex.split(os.environ.get('CXX', 'c++'))
    sources = sorted((ROOT / 'vendor/unikey').glob('*.cpp'))
    command = compiler + [
        '-std=c++17', '-O2', '-DNDEBUG', '-fPIC', '-fvisibility=hidden',
        '-shared', '-pthread', '-Wall', '-Wextra', '-Wl,-z,relro,-z,now',
        '-I', str(ROOT / 'vendor/unikey'), str(ROOT / 'native/bridge.cpp'),
        *map(str, sources), '-o', str(temporary),
    ]
    try:
        subprocess.run(command, check=True)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(destination.relative_to(ROOT))


if __name__ == '__main__':
    build()
