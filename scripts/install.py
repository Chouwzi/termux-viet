#!/usr/bin/env python3
"""Install from a local checkout."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from termux_viet.install import install  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix')
    parser.add_argument('--auto-start', action='store_true')
    parser.add_argument('--migrate', action='store_true', help='replace recognized legacy tivi hooks')
    parser.add_argument('--termux-keys', action='store_true', help='install EN/VI extra keys')
    options = parser.parse_args()
    try:
        install(ROOT, **vars(options))
    except (RuntimeError, OSError) as error:
        parser.exit(1, f'termux-viet: {error}\n')


if __name__ == '__main__':
    main()
