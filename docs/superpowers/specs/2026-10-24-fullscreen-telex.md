# Fullscreen Telex correction

The original alternate-screen bypass disabled VI in TUI prompts and editors
while the language button continued to report VI. Alternate-screen selection
describes display storage, not whether an application accepts text.

Continue converting in VI on both screens. Keep composition resets on screen
transitions and canonical no-echo password bypass. Keep EN as the manual choice
for literal commands, modal editor navigation and unobservable raw password forms.
No application detection, background polling or editor configuration is needed.

Validate alternate-screen canonical and raw input, mode toggles, password bypass,
and actual nvim/nano file contents after live composition, deletion and EN input.
Editor tests skip when their optional executable is unavailable. Smoke-test the
installed harness prompt widgets with unsent text; do not make model requests.

This supersedes the alternate-screen bypass in the original design and plan.
