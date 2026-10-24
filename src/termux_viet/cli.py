"""Command-line entry points."""

import argparse
import os
import shutil
import sys

from . import __version__
from .engine import convert


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog='termux-viet', description='Vietnamese Telex input for Termux terminals',
        epilog='Use an English keyboard layout to avoid double composition. '
               'Ctrl+Space or Alt+Space switches VI/EN.',
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    if args and args[0] == 'convert':
        parser.add_argument('action')
        parser.add_argument('--modern', action='store_true', help='use hoà/thuỷ style')
        parser.add_argument('text', nargs='*')
        options = parser.parse_args(args)
        text = ' '.join(options.text) if options.text else sys.stdin.read()
        try:
            sys.stdout.write(convert(text, modern=options.modern))
            if options.text:
                sys.stdout.write('\n')
            return 0
        except (RuntimeError, OSError) as error:
            parser.exit(1, f'termux-viet: {error}\n')
    if args and args[0] == 'doctor':
        parser.add_argument('action')
        parser.parse_args(args)
        print(f'termux-viet {__version__}; Python {sys.version.split()[0]}')
        try:
            if convert('tieengs Vieetj') != 'tiếng Việt':
                raise RuntimeError('engine self-check failed')
        except (RuntimeError, OSError) as error:
            print(f'UniKey: ERROR ({error})')
            return 1
        print('UniKey: OK')
        print(f'Terminal: {"TTY" if sys.stdin.isatty() else "non-interactive"}')
        print('Hotkeys: Ctrl+Space / Alt+Space; Termux EN/VI macros supported')
        return 0
    if args and args[0] == 'uninstall':
        from .install import uninstall
        parser.add_argument('action')
        parser.add_argument('--prefix', help='installation prefix (default: ~/.local)')
        options = parser.parse_args(args)
        uninstall(options.prefix)
        return 0

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--en', action='store_true', help='start in English mode')
    mode.add_argument('--vi', action='store_true', help='start in Vietnamese mode (default)')
    parser.add_argument('--modern', action='store_true', help='use hoà/thuỷ tone placement')
    parser.add_argument('-c', metavar='COMMAND', help='run a shell command')
    parser.add_argument('command', nargs=argparse.REMAINDER, help='child program and arguments')
    options = parser.parse_args(args)
    shell = os.environ.get('SHELL') or shutil.which('bash') or '/bin/sh'
    command = options.command
    if command[:1] == ['--']:
        command = command[1:]
    if options.c is not None:
        if command:
            parser.error('-c cannot be combined with a child program')
        command = [shell, '-c', options.c]
    if not command:
        command = [shell]
    try:
        from .terminal import run
        return run(command, vi=not options.en, modern=options.modern)
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(2, f'termux-viet: {error}\n')
