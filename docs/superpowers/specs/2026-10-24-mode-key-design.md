# Mode key correction

User-defined behavior: restore LEFT/RIGHT and preserve all default keys; add one
toggle before ESC; selected VI displays VI and selected EN displays EN.
The label shows the current mode; pressing it switches to the other mode.
Keep the Telex engine and existing hotkeys unchanged.

The installer preserves custom layouts/popups and tags its own button. Legacy
E/V macros replacing arrows become LEFT/RIGHT. The button sends Ctrl+Space so
its action remains correct even if a label is stale.

Termux exposes static toolbar configuration rather than a per-session label API.
Update the marked label through an asynchronous, coalesced settings reload;
ordinary input and idle operation do not trigger reloads. Document the global
toolbar limitation; do not imply independently accurate labels across sessions.

Verify default/custom/legacy layouts, install idempotence, uninstall after label
changes, malformed configuration, and real PTY input during a mode change.
