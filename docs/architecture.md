# Architecture

`keyboard bytes → InputProcessor → UniKey edits → child PTY → application`

`native/bridge.cpp` owns one `UkSharedMem` and `UkEngine` per opaque handle.
The ABI returns a count of Unicode characters to erase and UTF-8 replacement
bytes. C++ exceptions terminate at the ABI boundary. The 1,024-byte output buffer
and upstream engine history are bounded. Use engines from one thread; the
upstream conversion tables are shared.

`engine.py` manages handles explicitly with context managers. The offline
converter changes ASCII letter tokens and preserves existing Unicode tokens.
Default options: Telex, free marking, traditional tone placement, spell checking
on, macros off, automatic word restoration off. No dictionary, network or
third-party Python runtime packages are loaded.

`input.py` handles byte framing separately from composition. Bracketed paste
is opaque, including controls and mode hotkeys inside it. UTF-8 input boundaries
reset composition; Unicode words remain literal. Navigation and control keys
invalidate the current composition. ESC alone uses a 35 ms timeout; incomplete
escape sequences use 250 ms and their bytes are forwarded on expiry. Overlong
control strings and CSI sequences stream through with bounded retained state.

`terminal.py` runs a child under a controlling PTY. The child inherits a UTF-8
canonical erase configuration; raw readline receives DEL for edit operations.
Output remains bytes. DEC alternate-screen and paste modes are observed without
interpreting text inside OSC/DCS. Bracketed paste is enabled on the outer terminal
and markers are adapted to the child. Canonical no-echo input bypasses conversion.

Both PTY and display writes are nonblocking and use queues. Each read source is
paused at 1 MiB queued; a single read may temporarily exceed that threshold.
Signals wake the blocking selector through a pipe, so idle operation does not
poll. The direct child is reaped independently of descendant PTY lifetime. After
child exit, an inherited PTY gets a 250 ms idle drain window and at most another
1 MiB of output. Already queued display output is flushed without a deadline,
so a slow screen cannot silently truncate it. Signal handling remains responsive
throughout. Termination restores termios and descriptor flags before bounded
child cleanup. Mode files are private and scoped to the wrapper PID.

`install.py` stages content-addressed runtime releases and atomically changes
the current symlink. Launchers use the install prefix; configuration files are
backed up before writes and existing permissions/symlink targets are preserved.
Only marked hooks and recognized legacy blocks are changed. Backups stay local;
they can contain personal shell settings and must never be committed.

`extra_keys.py` safely decodes literal Termux layouts without evaluating code.
The marked Ctrl+Space toggle displays the current mode and precedes ESC; legacy arrow replacements are repaired.
Unrelated buttons and nested popup dictionaries survive layout updates.
`indicator.py` coalesces mode changes on a condition-driven worker started only
after the PTY fork. A changed label triggers a bounded settings reload outside
the input loop. No thread is started for an unmanaged layout and no idle polling
is used. Termux shares one toolbar configuration across sessions; a label reflects
the last session to refresh it, while the toggle always affects the active input
session. Runtime refresh can be disabled with `TERMUX_VIET_MODE_KEY=0`.

The PTY interface has no reliable surrounding-text API. Reopening a previous
word, distinguishing arbitrary raw password forms, or detecting Vim's Insert
mode through tmux requires deeper application integration. EN is the explicit
literal-input mode for those cases.
