# UniKey reference cases

`unikey-telex.json` contains the 1,307 uncommented literal input/output pairs
from `test/testunikey.cpp` in fcitx5-unikey commit
`ed9170c35c1a6275d105e03d7f9bc4f674c1469c`.

SPDX-FileCopyrightText: 2021-2021 CSSlayer <wengxt@gmail.com>

SPDX-License-Identifier: GPL-2.0-or-later

Source: https://github.com/fcitx/fcitx5-unikey/blob/ed9170c35c1a6275d105e03d7f9bc4f674c1469c/test/testunikey.cpp

Conversion to JSON on 2026-10-24 changes only representation. Commented-out
cases are excluded. Upstream runs these cases with spell checking disabled;
the corresponding termux-viet test uses the same setting. Default spell
checking and terminal behavior have separate regression tests.
