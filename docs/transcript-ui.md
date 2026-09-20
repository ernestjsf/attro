# Transcript UI

## Shipped display defaults

Attro ships the maintained plugin forks, shared UI config files, and display
defaults — not through personal extensions or skills in the distribution profile.

| Surface | Owner |
| --- | --- |
| Native minimalist editor in managed Attro | Attro core |
| User-message labeled frame, selector borders | Attro core (formerly Zentui plugin) |
| Work-first tool rows, output previews, expandable details, edit/write diffs, per-message thinking | Attro core (selected CC behavior) |
| Primary progress (phase, current tool, elapsed time) | Attro core |
| Dock layout, disclosure state, height budget and inline navigation | Attro core |
| Diagnostic, task and subagent content/actions | Lens, rpiv todo, and subagent packages |

Optional widgets such as turn-status are **not bundled** in the distribution
recipe. Users who want them install or copy standalone extensions into their own
`~/.attro/agent` directory (or another Pi discovery path).

Thinking starts folded on fresh profiles (`hideThinkingBlock: true` in
`profile/settings.json`), with per-message disclosure; Ctrl+T reveals it. Existing
profiles retain their visibility preference. Compact mode keeps assistant
commentary in chronological order rather than collecting tools into Activity
cards. Native transcript components own this presentation; neither the Zentui
nor CC renderer package is loaded by the managed recipe. Core alone publishes
primary activity. These changes remove duplicate UI, not model reasoning or tool
content.

## Native input editor

Managed Attro uses the same native minimalist editor from its first frame through
session initialization. Project trust still gates drafting, and submission stays
disabled until initialization finishes. Loading and metadata updates do not
replace the editor or transfer its draft, cursor, or undo state.

The composer uses the active theme, unboxed separator lines, model/thinking
labels, context gauge, session name, and activity. Working, retry and compaction
share the composer activity location. A utility row below the sections shows the
compact directory and Git status. Core's footer data provider supplies cached
Git status without replacing the input. Completed tools and user shell commands
invalidate outstanding Git snapshots; routine streaming redraws do not. Other
extensions can still explicitly replace the editor.

This removes Attro's startup editor handoff, not synchronous plugin-loading
stalls. These changes require a new prepared release; retained releases are not
modified in place.

## Progress ownership

Core owns the primary activity location and elapsed clock. Its labels follow
actual lifecycle and tool events: waiting for the model, generating a response,
executing tools, retrying, compacting, waiting for input, stopping, and settled
outcomes. Blocking states take priority over ordinary streaming updates. Tool
labels identify the operation and relevant target; they do not infer successful
checks, invent percentages, or display reasoning excerpts.

A completed main response is not a claim that background agents finished. Todos
remain the task plan, Agents own child activity, and Diagnostics own check results.
Detailed tool output stays in the transcript. The steering queue remains a separate
user-instruction surface above the input, not a second execution indicator.

Extensions should check `ctx.ui.nativeEditor?.activityOwner === "core"` before
publishing a competing primary indicator. The capability, rather than the managed
environment flag alone, preserves fallback behavior on older releases. Personal
completion extensions can yield their waiting/settled widget while retaining
independent final-answer headings. Final-answer headings are not bundled by Attro.

## Shared bottom dock

Managed Attro places Todos and Agents below the native composer. Both start
collapsed; live updates preserve the chosen disclosure state and typing focus.
Core measures the draft and other dock content before allocating expanded rows.
Clicking a section header always expands/collapses its list in place, including
in short terminals. Expanded sections reserve actual item rows; overflow scrolls
inside the list rather than opening a popup. Row clicks select without opening
details, and the two headers remain separately identifiable when space permits.

- `Alt+T` / `Alt+A`: focus Todos / Agents, opening the chosen list if collapsed.
  Press that same shortcut again to return to the input without collapsing the list.
- `Alt+Shift+T` / `Alt+Shift+A`: expand/collapse without switching lists;
  collapsing the focused list returns to the draft.
- Only the focus shortcuts enter a list. Down, row clicks, scrolling and
  background updates do not take keyboard focus from the editor.
- While focused: Up/Down select and stop at the list boundaries; Up never returns
  to the input. Enter/Right inspect the selected agent, `x` stops it,
  and Escape/Left return to the unchanged draft. Alt+J/K also navigate only while
  the list is focused. Core bindings are configurable; managed Todo no longer
  intercepts them with its legacy `collapseKey` setting.
- Mouse wheel over an expanded section: browse that list in place.
- The dock's Extensions entry and Alt+O chooser have been removed.
- `Alt+D`: retains native forward-word deletion; `Ctrl+O` remains tool expansion.

The input has a faint, muted border and no active cursor while a list is focused;
its normal appearance is restored when focus returns. Draft text and cursor
position are preserved.

Agents reuse the full responsive dashboard: names/roles/activity, model and
thinking level, context, cost, tokens and age where width permits. Selection
tracks the run ID through updates/reordering. `/subagents` shows history inline,
including dismissed records, without opening a popup or acquiring keyboard focus.
Explicit per-agent inspection retains transcript viewing and steering.

Enabled Lens widgets contribute a diagnostic summary with a separate details
overlay. Hidden Lens widgets remain hidden. Legacy widgets share a bounded,
scrollable inline area; zero-row infrastructure stays live. No Extensions menu
is needed to access overflow. Unsupported hosts retain their original UI.
Routine LSP footer status yields to a registered Diagnostics dock; failed-server
alerts remain visible. Subagent completion notifications are retained because
an expanded dock does not prove a particular result row is visible.

The `setDockSection`, `toggleDockSection`, `navigateDockSection`, and
`isDockSectionExpanded` contract is
in `plugins/attro-core/packages/coding-agent/docs/tui.md`. The implementation plan
and verification boundary are in [dock-plan.md](dock-plan.md).

Autocomplete retains its native behavior. Queued steering and follow-ups appear
above the input in a matching frame. Progress ownership does not change their
delivery or cancellation semantics.

## Visual hierarchy

Compact mode prioritizes evidence over tool plumbing: default-rendered file and
symbol reads show up to three source lines with line numbers when the returned location is known,
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
Explicit plugin `renderCall` / `renderResult` slots and self-rendered shells retain
their ownership rather than being replaced by name-based styling.

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

- `plugins/attro-core/packages/coding-agent/src/modes/interactive/` owns native
  transcript components. Selected commands and Markdown transformations live in
  `packages/coding-agent/src/attro-features/` within that core tree.
- Historical Zentui display defaults are archived in
  `docs/archive/zentui-display-defaults-retired.json`; see
  [zentui-native-parity.md](zentui-native-parity.md).
- `config/claude-code-style.json` remains the reviewed native transcript default;
  keeping the legacy filename avoids rewriting existing user preferences.
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

## Native transcript preferences and commands

The native implementation reads supported fields from
`~/.attro/agent/claude-code-style.json`. The recipe continues to seed this file
only for new profiles. `/reload` re-reads preferences; updates do not overwrite
existing files. `previewLines` controls folded thinking, not the independent
three-line compact tool preview. The original `cc-dark` and `cc-light` theme
assets remain available in managed Attro, without changing the selected theme.
Diff highlighting uses core's syntax highlighter instead of the former optional
Shiki CLI; token colors can differ, while diff contents and layout remain native.

Selected `/clear`, `/exit`, `/context`, session references, Markdown enhancements,
and compact response guidance are retained as first-party features. The former
`/ccstyle` configuration panel and unused CC feature collection are not bundled;
edit supported preferences in the same JSON file instead. Avoid loading the
retired CC renderer alongside native rendering. Personal prototype patches such
as a final-answer heading extension are user-owned and were not rewritten.

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

Use a supported Node version (22.19.0 or newer) and build TUI dependencies
before tests that import their compiled entrypoints. From `plugins/attro-core`,
run `npm run check` and the affected focused non-e2e tests following its
`AGENTS.md`. Exercise the actual CLI in an isolated profile at normal and narrow
terminal widths, without the retired renderer packages.

Exercise collapsed/expanded, pending/error, multiline arguments, restored messages
and narrow-width component rendering. Thinking remains attached to its original
message and separately expandable. Compact tool rows preserve their action at
narrow widths; overflow remains accessible through expansion.
Validate JSON and compare tracked config/theme files against their prepared
release copies. No new dependencies or additional UI plugin are needed.

`python3 scripts/verify.py --runtime` checks source pins, clean submodules, private
origins, runtime-file presence, and copied config hashes. It intentionally fails
when source submodules have uncommitted edits; do not weaken this check or
fabricate a pin to hide them. Commit reviewed submodule changes and update the gitlink/pin
only as part of the normal source-publication workflow. This check does not
inspect activation or certify live combined-TUI compatibility.

The dated evidence below describes the retired fork, not verification of the
native cutover. Current candidate verification must record its exact core and
recipe pins, supported Node version, focused checks, and actual combined render.

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
