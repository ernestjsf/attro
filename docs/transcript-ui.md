# Transcript UI

## Shipped display defaults

Attro ships the Quattro transcript/display stack through the maintained plugin
forks, shared UI config files, and themes — not through personal extensions or
skills in the distribution profile.

| Surface | Owner |
| --- | --- |
| User-message labeled frame, minimalist editor, selector borders | Zentui |
| Compact tool rows, expandable details, edit/write diffs, folded thinking/activity | CC extensions |
| Live working line, current tool, elapsed time and token count | Zentui |
| Diagnostic, task and subagent panels | Lens, rpiv todo, and subagent packages |

Optional widgets such as turn-status are **not bundled** in the distribution
recipe. Users who want them install or copy standalone extensions into their own
`~/.attro/agent` directory (or another Pi discovery path).

Zentui's experimental thinking renderer is disabled in the shipped
`config/zentui.json` to avoid overlapping CC's assistant renderer. Thinking is
not globally hidden by default (`hideThinkingBlock: false` in
`profile/settings.json`); CC's compact folding is a separate display behavior.
CC's own working message and agent summary remain disabled. Zentui's turn summary and working-line thought
preview are disabled; the working message is the literal `Working…`. These
changes remove duplicate UI, not model reasoning or tool content.

## Visual hierarchy

Quattro Green is the default theme. User text uses cream; tool titles use jade;
success uses green; pending tools use a subtle amber surface; errors retain
their red surface. Completed tools use a separate blue-green surface, not the
user-message background. Labels and state glyphs provide distinctions without
relying only on color.

The confirmed final-answer separator uses `borderAccent` and a bold `mdHeading`
label when a matching completion marker is present. Old messages are not guessed
to be final, and streaming/failed answers do not acquire that label. No
model-facing messages or tool results are rewritten by these display changes.

## Related UI work in plugin forks

The scroll button uses Pi's floating transcript indicator instead of reserving a
dock row; its click area follows viewport clipping, and renderer-local ownership
survives layout recomposition and repeated cleanup. The subagent panel adapts
its columns to available width and uses labeled detail metadata and a context-usage
bar. Spawn, delivery, and execution behavior are unchanged.

## Source and configuration

- `plugins/pi-cc-extensions/` is the active tool-rendering source tree.
- `config/zentui.json` is the reviewed Zentui display default.
- `config/claude-code-style.json` is the reviewed CC display default.
- `config/rpiv-todo.json` is the reviewed rpiv todo display default.
- `themes/quattro-green.json` and `themes/quattro-amber.json` are the shipped
  Quattro themes; Green includes optional `dockBg` color `#0e1713`.
- `sources.lock.json` records copied display-file hashes and last committed
  source pins. Uncommitted fork edits are live working-tree changes, not new pins.

The root package exports themes only. Do not copy full global settings,
credentials, sessions, or safety policy into this repository. Provider, model,
permission, and unrelated plugin configurations are user-owned.

## Applying changes

For distribution changes, prepare and activate a new release, then restart
Attro. `/reload` alone keeps using the running process's pinned release.
Personal extension changes can use `/reload`; personal theme files retain
upstream's hot-reload behavior. Restarting also gives a fresh transcript
component tree.

Use Ctrl+O for tool expansion and Ctrl+T for thinking visibility (subject to CC's
compact grouping). These are Pi's default bindings and are not remapped by the
shipped profile defaults. Fullscreen clicking/selection remains owned by Pi and
the existing renderer interaction layer.

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
Validate JSON and compare tracked config/theme files against their prepared
release copies. No new dependencies or additional UI plugin are needed.

`python3 scripts/verify.py --runtime` checks source pins, clean submodules, private
origins, runtime-file presence, and copied config hashes. It intentionally fails
while the CC fork has uncommitted edits; do not weaken this check or fabricate a
pin to hide them. Commit reviewed submodule changes and update the gitlink/pin
only as part of the normal source-publication workflow. This check does not
inspect activation or certify live combined-TUI compatibility.

Verification used real installed-Pi transcript components at 40/80 columns,
final-heading/status components at narrow and normal widths, the CC test suite,
and the subagent test harness. This is component/automated evidence, not a
screenshot or manual interaction test of the entire live combined terminal.

Historical maintainer backups of pre-change live files may exist under
`~/.pi/agent/ui-backups/` on development machines. Those paths are personal and
are not part of the Attro distribution recipe.
