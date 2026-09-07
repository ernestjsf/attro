# Transcript UI

## Shipped display defaults

Attro ships the maintained plugin forks, shared UI config files, and display
defaults — not through personal extensions or skills in the distribution profile.

| Surface | Owner |
| --- | --- |
| User-message labeled frame, minimalist editor, selector borders | Zentui |
| Work-first tool rows, output previews, expandable details, edit/write diffs, per-message thinking | CC extensions |
| Live working line, current tool, elapsed time and token count | Zentui |
| Diagnostic, task and subagent panels | Lens, rpiv todo, and subagent packages |

Optional widgets such as turn-status are **not bundled** in the distribution
recipe. Users who want them install or copy standalone extensions into their own
`~/.attro/agent` directory (or another Pi discovery path).

Zentui's experimental thinking renderer is disabled in the shipped
`config/zentui.json` to avoid overlapping CC's assistant renderer. Thinking starts folded on fresh profiles (`hideThinkingBlock: true` in
`profile/settings.json`), with a per-message disclosure; Ctrl+T reveals it. Existing
profiles retain their visibility preference. Compact mode keeps assistant commentary in chronological order and no longer collects tools into Activity cards.
CC's own working message and agent summary remain disabled. Zentui's turn summary and working-line thought
preview are disabled; the working message is the literal `Working…`. These
changes remove duplicate UI, not model reasoning or tool content.

## Visual hierarchy

Compact mode prioritizes evidence over tool plumbing: file and symbol reads show
up to three source lines with line numbers when the returned location is known,
beneath their path/range or symbol header. Omitted content stays expandable.
Read-limit/truncation notices and partial-symbol notices remain visible separately
from the preview's own omitted-line count. Image classification uses actual image
attachments or the core read tool's `details.isImage` marker, never literal source
phrases. This also keeps text-only image-processing failures unnumbered.
Commands and searches expose bounded output previews; edits use
rich diffs; new writes show eight preview lines in the shipped defaults. Failed
tools expose error text even while collapsed. Restored writes without a known
baseline use a neutral content preview, not an all-add diff. Ordinary rows are unboxed and use
the active theme's title/status tokens, with state glyphs rather than color alone.
Fuller input/output remains accessible through tool expansion. A tool updates in
place as it runs and settles; tool rows are not moved into expanded Activity cards.

Assistant commentary remains ordinary Markdown between actions, without repeated
Assistant labels. In compact interactive mode, a short appended prompt guideline
asks for meaningful findings, decisions, uncertainty, and blockers—not narration
of each tool call or raw internal reasoning. This is guidance, not a guarantee of
model behavior. Formatting guidance uses inline code for paths, commands, and
identifiers, and headings only where useful. Stored messages and tool results
are not rewritten.

Response colors belong to the selected theme: `mdHeading` controls headings,
`mdCode` inline code, `mdLink` links, and `mdListBullet` list markers. Normal prose
keeps `text`; status colors remain reserved for actual tool states. A personal
theme can map `mdHeading` to its `accent` without changing the renderer or other
themes. No keyword-matching colorizer or fixed response palette is installed.

Fresh profiles use the upstream theme default; personal Quattro themes remain
optional. Standalone final-answer/status extensions are not bundled or required.

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
- `themes/quattro-green.json` and `themes/quattro-amber.json` remain in the
  checkout for originalPi compatibility; new Attro releases do not copy them or
  pass `--theme` flags. Green includes optional `dockBg` color `#0e1713`.
- `sources.lock.json` records copied display-file hashes and last committed
  source pins. Uncommitted fork edits are live working-tree changes, not new pins.

The root checkout exports Quattro themes through `package.json` for originalPi
use only. Do not copy full global settings,
credentials, sessions, or safety policy into this repository. Provider, model,
permission, and unrelated plugin configurations are user-owned.

## Applying changes

For distribution changes, prepare and activate a new release, then restart
Attro. `/reload` alone keeps using the running process's pinned release.
Existing profiles retain their settings: select thinking-hidden with Ctrl+T and
set `writeDiffCollapsedLines: 8` in the shared CC config to adopt those new defaults.
Personal extension changes can use `/reload`; personal theme files retain
upstream's hot-reload behavior. Restarting also gives a fresh transcript
component tree.

Use Ctrl+O for tool expansion and Ctrl+T for thinking visibility. These are Pi's default bindings and are not remapped by the
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
and narrow-width component rendering. Thinking remains attached to its original
message and separately expandable. Compact tool rows preserve their action at
narrow widths; overflow remains accessible through expansion.
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

### Work-first verification (2026-09-07)

- `npm run typecheck`, `npm run lint`, `npm run format:check`, and `npm test`
  passed in the CC fork on Homebrew Node 26.5.0 (192 tests).
- `python3 -m unittest discover -s tests -p 'test_*.py' -v` passed
  (178 tests run, one skipped).
- The Bash-tail, unknown-write-baseline, and duplicate-stop regressions failed
  against an isolated pre-fix source snapshot, then passed against the fixes.
- The installed Attro CLI with checkout CC and Zentui extensions rendered a
  synthetic restored session in an isolated tmux terminal at 100 and 40 columns.
  Captures confirmed actual output beyond 16 KB, neutral restored-write previews,
  folded thinking, visible errors, and Ctrl+O/Ctrl+T toggles. No credentials or
  model requests were used. Live provider streaming and the full plugin set were
  not exercised; partial output is covered by component tests.
- Source/release verification remains blocked by the uncommitted CC submodule;
  `--runtime` also reports the checkout's missing core build artifact. No source
  pins were fabricated, and no installed release or shared user profile was changed.

### Numbered read previews and response emphasis (2026-09-07)

The CC refinement passed `npm run typecheck`, `npm run lint`,
`npm run format:check`, and `npm test` (211 tests). The root Python suite passed
178 tests run with one skipped. Nineteen new preview/guidance assertions failed
against the prior CC commit and passed with the refinement. An isolated installed
CLI with Lens, checkout CC, and Zentui rendered restored file/symbol reads at
40 and 100 columns; Ctrl+O exposed the complete results without reordering them.
Theme-loader and rendered ANSI checks confirmed that a personal `mdHeading` →
`accent` mapping and existing inline-code colors work at both widths. No personal
theme was added to the distribution, and no model requests were made by these checks.
The optional core image-result marker passed `npm run check` and both complete
read/image test files (84 tests). Three continuation/image-classification
regressions failed against the pre-fix renderer snapshot and passed with the fixes.

Historical maintainer backups of pre-change live files may exist under
`~/.pi/agent/ui-backups/` on development machines. Those paths are personal and
are not part of the Attro distribution recipe.
