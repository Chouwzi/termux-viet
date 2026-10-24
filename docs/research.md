# Research notes

Reviewed on 2026-10-24 using primary sources and the installed Python implementation.

| Source | What informed the implementation |
| --- | --- |
| [UniKey manual](https://www.unikey.org/support/ukmanual.html) | Tone keys, free marking, replacing/removing tones and case handling |
| [fcitx5-unikey pinned engine](https://github.com/fcitx/fcitx5-unikey/tree/ed9170c35c1a6275d105e03d7f9bc4f674c1469c/unikey) | Incremental composition, repeated-key cancellation, display-character backspace and tone relocation |
| [Upstream tests](https://github.com/fcitx/fcitx5-unikey/blob/ed9170c35c1a6275d105e03d7f9bc4f674c1469c/test/testunikey.cpp) | 1,307 active literal reference pairs, tested with upstream's disabled-spell-check setting |
| [Termux TerminalView](https://github.com/termux/termux-app/blob/master/terminal-view/src/main/java/com/termux/view/TerminalView.java) | Android commitText/deleteSurroundingText are separate from terminal byte input |
| [Termux TerminalEmulator](https://github.com/termux/termux-app/blob/master/terminal-emulator/src/main/java/com/termux/terminal/TerminalEmulator.java) | DECSET 2004 paste framing and input delivery |
| [Xterm controls](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html) | CSI, OSC/DCS, string terminators, alternate screen and bracketed paste |

The installed legacy engine gave 2,077 exact round trips out of 2,100 corpus
entries. Seventeen differences were tone-position conventions; six were actual
semantic/vowel errors. Round trips alone did not exercise incremental editing
or terminal behavior. Reproduced failures included `nuwar` → `nữa`, `aaa` → `â`,
`ass` → `á`, malformed `oeo` vowels, converted paste, stale composition after
Ctrl+A, and BS sent to a canonical PTY configured for DEL.

The new implementation reuses the original engine rather than reimplementing
Vietnamese spelling rules. It does not copy the old Funput-derived tables,
corpus or spelling overrides. License provenance is recorded in `vendor/` and
`tests/fixtures/`.

Independent review reproduced input/output backpressure blocking termination,
child exit waiting on a nohup descendant, and overlong CSI framing depending
on read boundaries. Dedicated regression tests cover those conditions.
