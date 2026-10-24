#!/usr/bin/env sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python_bin=${PYTHON:-python3}
if ! command -v "$python_bin" >/dev/null 2>&1; then
    printf '%s\n' 'Python 3.10+ is required. On Termux: pkg install python clang git' >&2
    exit 1
fi
if ! command -v "${CXX:-c++}" >/dev/null 2>&1; then
    printf '%s\n' 'A C++ compiler is required. On Termux: pkg install clang' >&2
    exit 1
fi
"$python_bin" "$project_dir/scripts/build.py"
"$python_bin" "$project_dir/scripts/install.py" "$@"
