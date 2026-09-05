# Transcript UI

## Active ownership

The live `~/.pi/agent/settings.json` registers all seven local fork packages under
`~/projects/pi-customizations/plugins/`. It does not register their old npm/git
copies alongside them. Those older copies and UI backups are deliberately retained;
being present on disk does not make a package active.

| Surface | Owner |
| --- | --- |
| User-message labeled frame, minimalist editor, selector borders | Zentui |
| Compact tool rows, expandable details, edit/write diffs, folded thinking/activity | CC extensions |
| Live working line, current tool, elapsed time and token count | Zentui |
| Waiting/settled status and confirmed final-answer heading | `~/.pi/agent/extensions/turn-status.ts` |
| Diagnostic, task and subagent panels | Their respective Lens, todo and subagent packages |

Zentui's experimental thinking renderer is disabled: it overlapped CC's private
assistant renderer and yielded to the host's hidden-thinking setting anyway.
Thinking remains hidden by default (`hideThinkingBlock: true`). CC's own working
message and agent summary remain disabled. Zentui's turn summary and working-line
thought preview are disabled; the working message is the literal `Working…`.
The turn-status widget is hidden during ordinary work, but remains visible when
waiting for input and after settling. These changes remove duplicate UI, not
model reasoning or tool content.

## Visual hierarchy

Quattro Green remains the active theme. User text uses cream; tool titles use
jade; success uses green; pending tools use a subtle amber surface; errors retain
their red surface. Completed tools use a separate blue-green surface, not the
user-message background. Labels and state glyphs provide distinctions without
relying only on color.

The confirmed final-answer separator uses `borderAccent` and a bold `mdHeading`
label. It still requires a saved, matching completion marker: old messages are
not guessed to be final, and streaming/failed answers do not acquire that label.
No model-facing messages or tool results are rewritten by these display changes.

## Related UI cleanup

The stopped session's fullscreen scroll-button and subagent-panel work was
finished separately. The scroll button uses Pi's floating transcript indicator
instead of reserving a dock row; its click area follows viewport clipping, and
renderer-local ownership survives layout recomposition and repeated cleanup.
The subagent panel adapts its columns to available width and uses labeled detail
metadata and a context-usage bar. Spawn, delivery and execution behavior are
unchanged.

## Source and configuration

- `plugins/pi-cc-extensions/` is the active tool-rendering source tree.
- `config/zentui.json` mirrors `~/.pi/agent/zentui.json`.
- `config/claude-code-style.json` mirrors `~/.pi/agent/claude-code-style.json`.
- `themes/quattro-green.json` mirrors `~/.pi/agent/themes/quattro-green.json`.
- `turn-status.ts` remains a standalone global extension; it is not separately
  registered by this root package or duplicated in a fork.
- `sources.lock.json` records copied display-file hashes and last committed
  source pins. Uncommitted fork edits are live working-tree changes, not new pins.

The root package exports themes only. Do not copy full global settings,
credentials, sessions or safety policy into this repository. Provider, model,
permission and unrelated plugin configurations are unchanged.

## Applying changes

After the current turn finishes, run `/reload`. For a fully fresh transcript
component tree, restart Pi and resume the session. The active custom theme file
hot-reloads independently; source and extension configuration changes need reload.

Use Ctrl+O for tool expansion and Ctrl+T for thinking visibility (subject to CC's
compact grouping). These are Pi's default bindings and are not remapped by the
current global keybindings. Fullscreen clicking/selection remains owned by Pi
and the existing renderer interaction layer.

## Verification and rollback

Use the same Homebrew Node as the live Pi wrapper (verified with Node 26.5.0),
not the older nvm Node that may come first on the shell PATH:

```sh
cd ~/projects/pi-customizations/plugins/pi-cc-extensions
export PATH=/opt/homebrew/bin:$PATH
npm run typecheck
npm run lint
npm test
```

Exercise collapsed/expanded, pending/error, multiline arguments, restored messages
and narrow-width component rendering. Activity remains expandable after a turn
finishes, so folded thinking is not lost. Compact tool rows preserve the tool
name at narrow widths; verbose expansion hints are omitted below 60 columns.
Validate JSON and compare live files against their tracked copies. No new
dependencies or additional UI plugin are needed.

`python3 scripts/verify.py --runtime` checks source pins, clean submodules, private
origins, runtime-file presence and copied config hashes. It intentionally fails
while the CC fork has uncommitted edits; do not weaken this check or fabricate a
pin to hide them. Commit reviewed submodule changes and update the gitlink/pin
only as part of the normal source-publication workflow. This check does not
inspect activation or certify live combined-TUI compatibility.

Verification used real installed-Pi transcript components at 40/80 columns,
final-heading/status components at narrow and normal widths, the CC test suite,
and the subagent test harness. This is component/automated evidence, not a
screenshot or manual interaction test of the entire live combined terminal.

The pre-change live files are backed up at:

```text
~/.pi/agent/ui-backups/transcript-hierarchy-20260905-142656/
```

That folder contains `zentui.json`, `quattro-green.json`, and `turn-status.ts`.
To roll back, restore each to its corresponding live path, restore the tracked
config/theme copies and their hashes, and revert only this transcript change in
the CC fork. Preserve any subsequent unrelated work. Reload or restart afterward.
