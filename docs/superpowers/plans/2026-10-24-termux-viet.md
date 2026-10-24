# termux-viet implementation plan

> Execution: inline with superpowers:executing-plans. User approved implementation and publication on 2026-10-24.

Goal: a lightweight Vietnamese terminal input method for Termux with UniKey Telex and a portable installer.

Architecture: a small C ABI exposes per-instance UniKey edits to Python ctypes. A streaming byte parser applies edits to a child PTY. Installation uses only the Python standard library and a C++ compiler.

Spec: ../specs/2026-10-24-termux-viet-design.md

## Global constraints

- Name: termux-viet; Python package: termux_viet. Telex first; VNI deferred.
- No runtime pip dependencies, network access or typed-text logging.
- Vendor pinned source with original notices and complete corresponding licenses.
- Public repository must exclude personal config, history, credentials and build artifacts.
- Main/develop/feature/release GitFlow; separate conventional commits.
- Isolated new repository; no modification of original engine files.

## Review focus

- Split UTF-8/CSI/paste markers at every boundary must preserve behavior.
- Password input and alternate screens must bypass conversion.
- Canonical erase must remove UTF-8 characters correctly; raw readline must receive DEL.
- Signals, child exit and startup errors must restore terminal settings.
- Reinstall/uninstall must preserve user config, maintain backups and avoid duplicate hooks.

## Tasks

### 1. Engine and distribution

- [x] Write regression tests with literal expected strings for repeated marks, case, qu/gi, uo, free marks, backspace and independent instances; run RED.
- [x] Vendor eight dependency-free UniKey translation units and required headers with upstream commit/license metadata.
- [x] Implement opaque native handles and bounded UTF-8 edits; compile with hidden symbols.
- [x] Implement Python resource ownership, edit application, convert and traditional/modern tone options.
- [x] Verify engine tests and compiler warnings; commit.

### 2. Input and terminal

- [x] Write parser tests for controls, hotkeys, UTF-8, escape and bracketed paste with arbitrary chunking; run RED.
- [x] Implement bounded streaming parser, literal Unicode boundaries, session mode and output-mode observation.
- [x] Write real PTY tests for canonical/raw erase, password bypass, byte output, resize, child exit and signal cleanup; run RED.
- [x] Implement PTY relay with complete writes, terminal restoration and signal/exit propagation.
- [x] Run whole suite; commit.

### 3. CLI, installation and migration

- [x] Write subprocess tests for conversion, CLI errors and temporary-HOME install/reinstall/uninstall; run RED.
- [x] Implement CLI, no-dependency local installer, shell hooks, backups and explicit legacy migration.
- [x] Check Bash/Zsh hooks and existing EN/VI key compatibility; run suite; commit.

### 4. Release

- [x] Add Vietnamese README, architecture/research notes, contribution/GitFlow guide, changelog and CI.
- [x] Benchmark engine/parser and document measured scope without commercial-equivalence claims.
- [x] Fresh-context review, fix material issues with regressions, rerun all checks.
- [x] Audit tracked files and history for secrets, license and machine paths.
- [x] Merge feature to develop, release/0.1.0 to main, tag v0.1.0, merge back.
- [x] Create public GitHub repository and push reviewed refs; verify visibility, tree and remote heads.
- [x] Install on current Termux with backed-up legacy hooks and verify local executable.
