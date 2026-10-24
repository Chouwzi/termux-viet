# Changelog

## 0.2.2 — 2026-10-24

- Keep Telex enabled in alternate-screen TUI inputs instead of silently bypassing VI.
- Preserve canonical password bypass and reset composition on screen changes.
- Add raw fullscreen/mode-toggle/password regressions and optional real nvim/nano save tests.
- Verify unsent Vietnamese input in installed Codex, OpenCode and agy TUIs on Termux.

## 0.2.1 — 2026-10-24

- Show the current mode on the language button: VI for Vietnamese, EN for English.
- Keep Ctrl+Space toggle behavior and the preserved arrow keys.

## 0.2.0 — 2026-10-24

- Restore LEFT/RIGHT replaced by the legacy language buttons.
- Add one Ctrl+Space language toggle before ESC while preserving default/custom keys and popups.
- Display the target language: EN when VI is selected, VI when EN is selected.
- Refresh the marked button asynchronously on mode changes; document Termux's global layout scope.
- Preserve unrelated properties and custom additions during install, refresh and uninstall.
- Add layout, indicator and real PTY regressions; isolate malformed config from engine startup.

## 0.1.1 — 2026-10-24

- Fix converter option parsing on Python 3.10 and allow options between text arguments.
- Add a CLI regression for mixed positional/options; retain the original 0.1.0 tag.

## 0.1.0 — 2026-10-24

- Native UniKey Telex with traditional/modern tone placement and optional spell checking.
- Incremental edits, repeated-key cancellation and displayed-character Backspace.
- Literal Unicode/paste, streaming escape framing and explicit VI/EN hotkeys.
- Nonblocking PTY relay with password/alternate-screen bypass, resize, exit status and signal cleanup.
- Local installer, optional Bash/Zsh autostart, EN/VI keys, legacy migration and config backups.
- UniKey reference fixtures, real PTY/installer regressions and Linux CI.

VNI, word prediction and surrounding-text editing are not included in this release.
