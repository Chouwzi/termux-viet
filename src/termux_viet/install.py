"""User-local installation, backed-up config edits and managed shell hooks."""

import hashlib
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
import time
from pathlib import Path

BEGIN = '# >>> termux-viet >>>'
END = '# <<< termux-viet <<<'
HOOK = re.compile(r'(?m)^# >>> termux-viet >>>\n.*?^# <<< termux-viet <<<\n?', re.S)
LEGACY = re.compile(r'(?m)^if \[ -z "\$TIVI" \].*?^fi\n?', re.S)
KEYS = ("extra-keys = [['ESC','/','-','HOME','UP','END','PGUP'],"
        "['TAB','CTRL','ALT',{macro: 'ALT [ 1 ; 5 E', display: 'EN'},'DOWN',"
        "{macro: 'ALT [ 1 ; 5 V', display: 'VI'},'PGDN']]\n")


def _prefix(prefix=None):
    if prefix:
        return Path(prefix).expanduser().resolve()
    executable = Path(sys.argv[0]).resolve()
    if executable.name == 'termux-viet' and executable.parent.name == 'bin':
        return executable.parents[1]
    return Path.home() / '.local'


def _state():
    return Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'termux-viet'


def _atomic_write(path, text, *, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode is None:
        mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _edit_config(path, transform, backup):
    target = path.resolve()
    original = target.read_text(encoding='utf-8') if target.exists() else ''
    result = transform(original)
    if result == original:
        return
    if target.exists():
        backup.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(target, backup / path.name)
    _atomic_write(target, result)


def _remove_legacy(text):
    def remove(match):
        block = match.group()
        if '$HOME/.local/bin/tivi' in block and '$HOME/.config/tivi/off' in block:
            return ''
        return block
    return LEGACY.sub(remove, text)


def _hook(prefix):
    executable = shlex.quote(str(prefix / 'bin/termux-viet'))
    bindir = shlex.quote(str(prefix / 'bin'))
    return (
        f'{BEGIN}\n'
        f'case ":$PATH:" in *:{bindir}:*) ;; *) export PATH={bindir}:"$PATH" ;; esac\n'
        'case $- in\n'
        '  *i*)\n'
        '    if [ -t 0 ] && [ -z "${TERMUX_VIET:-}${TIVI:-}" ] &&\n'
        '       [ ! -f "${XDG_CONFIG_HOME:-$HOME/.config}/termux-viet/off" ]; then\n'
        f'      [ ! -x {executable} ] || exec {executable} "${{SHELL:-sh}}"\n'
        '    fi\n'
        '    ;;\n'
        'esac\n'
        f'{END}\n'
    )


def _keys(text):
    lines = text.splitlines(keepends=True)
    output = []
    replaced = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.match(r'^\s*extra-keys\s*=', line):
            while line.rstrip().endswith('\\') and index + 1 < len(lines):
                index += 1
                line = lines[index]
            if not replaced:
                output.append(KEYS)
                replaced = True
        else:
            output.append(line)
        index += 1
    if not replaced:
        if output and not output[-1].endswith('\n'):
            output.append('\n')
        output.append(KEYS)
    return ''.join(output)


def install(root, *, prefix=None, auto_start=False, migrate=False, termux_keys=False):
    prefix = _prefix(prefix)
    source = Path(root) / 'src/termux_viet'
    library = source / 'libtermux_viet.so'
    if not library.is_file():
        raise RuntimeError('Build the native engine first: python scripts/build.py')
    digest = hashlib.sha256()
    files = sorted([*source.glob('*.py'), library])
    for path in files:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    base = prefix / 'share/termux-viet'
    release = base / 'releases' / digest.hexdigest()[:16]
    if not release.exists():
        release.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.install-', dir=release.parent))
        try:
            package = staging / 'termux_viet'
            package.mkdir()
            for path in files:
                shutil.copy2(path, package / path.name)
            shutil.copy2(Path(root) / 'LICENSE', staging / 'LICENSE')
            shutil.copytree(Path(root) / 'LICENSES', staging / 'LICENSES')
            staging.rename(release)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    link = base / f'.current-{os.getpid()}'
    try:
        link.symlink_to(release.relative_to(base), target_is_directory=True)
        link.replace(base / 'current')
    finally:
        link.unlink(missing_ok=True)
    launcher = prefix / 'bin/termux-viet'
    script = (
        f'#!{sys.executable}\n'
        'import sys\nfrom pathlib import Path\n'
        'sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '
        '"share/termux-viet/current"))\n'
        'from termux_viet.cli import main\nraise SystemExit(main())\n'
    )
    _atomic_write(launcher, script, mode=0o755)
    backup = _state() / 'backups' / f'{time.time_ns()}'
    if auto_start or migrate:
        def transform(text):
            text = HOOK.sub('', text)
            if migrate:
                text = _remove_legacy(text)
            if auto_start:
                if text and not text.endswith('\n'):
                    text += '\n'
                text += _hook(prefix)
            return text
        for filename in ('.bashrc', '.zshrc'):
            path = Path.home() / filename
            if path.exists() or auto_start:
                _edit_config(path, transform, backup)
    if termux_keys:
        properties = Path.home() / '.termux/termux.properties'
        manifest = base / 'install.json'
        metadata = json.loads(manifest.read_text()) if manifest.exists() else {}
        if 'extra_keys_before' not in metadata:
            original = properties.read_text() if properties.exists() else ''
            match = re.search(r'(?m)^[ \t]*extra-keys[ \t]*=(?:[^\n]*\\\n)*[^\n]*(?:\n|$)',
                              original)
            metadata['extra_keys_before'] = match.group() if match else ''
            _atomic_write(manifest, json.dumps(metadata))
        _edit_config(properties, _keys, backup)
    print(f'Installed: {launcher}')
    if backup.exists():
        print(f'Config backup: {backup}')
    print('Run: termux-viet doctor')
    return launcher


def uninstall(prefix=None):
    prefix = _prefix(prefix)
    backup = _state() / 'backups' / f'uninstall-{time.time_ns()}'
    for filename in ('.bashrc', '.zshrc'):
        path = Path.home() / filename
        if path.exists():
            _edit_config(path, lambda text: HOOK.sub('', text), backup)
    (prefix / 'bin/termux-viet').unlink(missing_ok=True)
    base = prefix / 'share/termux-viet'
    manifest = base / 'install.json'
    if manifest.exists():
        metadata = json.loads(manifest.read_text())
        properties = Path.home() / '.termux/termux.properties'
        if 'extra_keys_before' in metadata and properties.exists():
            _edit_config(properties, lambda text: text.replace(
                KEYS, metadata['extra_keys_before'], 1), backup)
    if base.is_dir():
        shutil.rmtree(base)
    print('Removed termux-viet and its shell hooks. Config backups are preserved.')
