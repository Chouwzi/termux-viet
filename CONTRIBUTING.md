# Contributing

Use Python 3.10+ and a C++17 compiler. There are no runtime pip dependencies.
Build with `python scripts/build.py`, then run
`PYTHONPATH=src python -m unittest discover -v`. If installed, run
`ruff check src scripts tests` for Python linting.

For input bugs include raw Telex keys, expected text, actual text, VI/EN mode,
shell/application and whether the input was typed or pasted. Do not attach
typed-text logs, tokens, passwords, shell history or personal configuration.

GitFlow:

- `main`: released versions, tagged `vMAJOR.MINOR.PATCH`.
- `develop`: integration for the next release.
- `feature/<name>`: start from develop, add regression tests before fixes,
  merge back with a merge commit.
- `release/<version>`: branch from develop, finish validation and changelog,
  merge into main, tag, then merge back into develop.
- `hotfix/<name>`: start from main, merge into main and develop after tests.

Use conventional commit subjects. New code should keep comments short and
explain constraints rather than repeat the code. Preserve vendor copyright
and license notices. Keep native source changes isolated from upstream files;
an upstream update must record the new commit and rerun reference tests.

Before publishing, review tracked files and history for credentials, personal
paths/configuration, build artifacts and missing license attribution. Never
commit local installer backups or interactive diagnostics containing input.
