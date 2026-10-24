#!/usr/bin/env python3
"""Measure engine/parser throughput on the current device."""

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from termux_viet.engine import Engine  # noqa: E402
from termux_viet.input import InputProcessor  # noqa: E402


def main():
    raw = 'Tooi ddang gox tieengs Vieetj treen Termux. '
    samples = []
    with Engine() as engine:
        for _ in range(5):
            start = time.perf_counter_ns()
            for _ in range(500):
                engine.reset()
                for char in raw:
                    engine.key(char)
            samples.append((time.perf_counter_ns() - start) / (500 * len(raw)) / 1000)
    with InputProcessor() as processor:
        start = time.perf_counter()
        for _ in range(500):
            processor.feed(raw.encode())
        elapsed = time.perf_counter() - start
    print(f'Engine median: {statistics.median(samples):.2f} us/key')
    print(f'Parser: {500 * len(raw) / elapsed:.0f} keys/second')
    status = Path('/proc/self/status')
    if status.exists():
        for line in status.read_text().splitlines():
            if line.startswith('VmRSS:'):
                print(f'Current RSS: {line.split(":", 1)[1].strip()} (Linux)')
    print(f'Native: {(ROOT / "src/termux_viet/libtermux_viet.so").stat().st_size} bytes')


if __name__ == '__main__':
    main()
