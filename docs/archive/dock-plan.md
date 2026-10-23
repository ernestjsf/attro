# Native bottom dock implementation plan

## Approved direction

Attro core owns one bottom dock. Preserve the native editor and its editing,
completion, paste, history, and focus behavior. Place compact task and agent
sections directly below the composer; expanded lists share a height budget and
long lists are browsable inline, without popup list navigation. Explicit detail
commands remain available separately. Background updates
must not reopen sections or steal the draft's focus.

Plugins continue to own task, agent, and diagnostic functionality. Integrate
presentation at a small shared seam rather than duplicating their state or
introducing a dashboard framework. Ordinary extension widgets retain a fallback.
Use the active theme and configurable keybindings; do not copy browser shortcuts.

## Checkpoints

1. Map core layout/editor ownership and plugin contribution points. Agree on the
   concrete contribution contract before parallel implementation.
2. Implement the native dock and bounded section rendering. Preserve the editor
   instance, exceptional activity/cancellation, and regular-mode operation.
   Run core-required checks and commit the verified core increment locally.
3. Adapt task and agent presentation to the shared dock without changing tools,
   execution, delivery, or persistence. Preserve existing detail actions and
   expose attention even when collapsed. Check and commit the plugin increments.
4. Review the integrated task diff independently. Verify real terminal rendering
   at wide/narrow and short sizes, draft/focus retention, and detail navigation.
   Correct concrete findings, document evidence and limits, then commit release
   source pins and documentation.

## Interaction priorities

- Input remains primary. Growing drafts take space before expanded lists.
- Empty sections take no rows; completed work remains inspectable.
- Waiting and failed agents remain discoverable, including alongside queued input.
- Steering and follow-up retain their actual semantics and configured shortcuts.
- Keyboard paths work without a mouse or overriding editor completion keys.
- Fullscreen mouse handling must not break transcript selection or scrolling.
- Resizing can shorten a list without changing the user's expansion preference.
- Details return to the untouched draft; plugin reload removes stale UI state.

## Scope and verification boundary

No new dependencies, live profile changes, installed-release modifications,
activation, publication, or push. Local commits are authorized. Release input
pins must refer to actual committed source; do not conceal failing checks by
weakening verification. Use isolated terminals and synthetic/local data instead
of paid provider calls. Record any interaction not exercised rather than treating
the HTML prototype as native-rendering evidence.

The reference prototype is currently `/private/tmp/attro-dock-preview/index.html`.
It is design evidence only, not production code or a durable release artifact.

## Implemented checkpoint (2026-09-09)

- Native unboxed composer with shared working/retry/compaction activity and a
  separate directory/Git utility row.
- Core-owned, independently collapsible task/agent sections; measured height
  allocation, short-terminal detail access, and a configurable details chooser.
- Live legacy-widget fallback with a full-content viewer; zero-row infrastructure
  remains mounted. Mouse coordinates in scrolled detail content are translated
  into the full content space.
- Task, subagent, and optional Lens adapters with ordinary-host fallbacks and
  separate detail overlays. No execution or persistence changes.
- Independent reviews covered core and plugin diffs. Findings on focus, sizing,
  stale contexts/status, empty-to-live updates, error propagation, and native
  keyboard conflicts were corrected with focused regression coverage.

### Verification evidence

Environment: Homebrew Node 26.5.0, `PATH=/opt/homebrew/bin:/usr/bin:/bin`.
Commands below run from their respective plugin roots unless stated otherwise.

- Core: `npm run check` passed after the final mouse correction. From
  `packages/coding-agent`, the focused Vitest files are `dock-sections`,
  `chat-viewport`, `attro-editor`, `interactive-mode-status`, `status-indicator`,
  `custom-editor-history-keybindings`, and
  `suite/regressions/5943-session-start-notify`. The final committed core passed
  all 83 tests, including the paged-widget mouse regression.
- Todo: `npm run check` exited successfully; `vitest run packages/rpiv-todo/`
  passed 244 tests. Biome reports one pre-existing informational `useTemplate`
  finding in `rpiv-pi/extensions/rpiv-core/built-in-workflows.test.ts`, outside
  this change.
- Subagents: `env -i HOME="$HOME" PATH=/opt/homebrew/bin:/usr/bin:/bin
  /opt/homebrew/bin/node subagents.test.cjs` passed 309 checks.
- Lens: `npm run build`, `npm run lint`, and the four Vitest files
  `tests/lens-toggle-command.test.ts`, `tests/index-mode-awareness.test.ts`,
  `tests/clients/widget-state.test.ts`, and `tests/host-sdk-type-only.test.ts`
  passed (93 tests). Six pre-existing safety-comment diagnostics on unchanged
  casts in `index.ts` were explicitly deferred, not suppressed in source.
- Isolated source-CLI tmux checks exercised core contributions and real todo/agent
  adapters at 100×32, 52×18, and 36×12: disclosure/details, preserved multiline
  drafts using bracketed paste, return from dialogs, and native Alt+D word
  deletion. Real task and agent detail overlays were inspected at 100×32.
  Harness/captures are temporary at `/private/tmp/attro-native-dock-smoke`.
  No paid provider requests or installed-profile changes were made. These
  keyboard/layout captures predate only the isolated fallback mouse correction;
  that correction has behavioral coverage.

- Root: `python3 -m unittest discover -s tests -p 'test_*.py' -v` passed
  (197 tests run, one skipped). `git diff --check` and JSON validation passed.

### Remaining limits

Autocomplete placement and queued-message presentation remain native; the
prototype's floating suggestions and unified queue row are not implemented.
No live-provider streaming, real IME, or full installed-release/plugin-stack
certification was performed. Lens detail rendering was not exercised in tmux.
The initial checkpoint was subsequently installed at the user's request. It does
not imply that all historical release gates have passed.

## Inline-list correction (2026-09-09)

The user's follow-up rejects popup list browsing. Header clicks and Alt+T/Alt+A
now always toggle Todos/Agents inline. Expanded lists contain actual items even
at 36×12; they no longer substitute a popup link or aggregate details entry.
Alt+J/Alt+K and the mouse wheel browse overflow in place, and native Down
navigates the inline Agents list. Row clicks select instead of opening popups.
Optional explicit detail actions and `/subagents` remain available; unrelated
question/diagnostic dialogs and the legacy-widget viewer are unchanged.

Verification for this correction:

- Core `npm run check` passed on Node 26.7.0; the existing `dock-sections`,
  `chat-viewport`, and `attro-editor` Vitest files passed 41 tests after formatting.
- Subagents' isolated Node 26.5.0 harness passed 311 checks, including inline
  native Down and preservation of explicit `/subagents` review.
- Lead primary LSP checks passed for the three changed core implementation files.
- `bash /private/tmp/attro-inline-dock-check.sh` exercised the real source CLI at
  100×32, 52×18, and 36×12. At every size, both expanded lists showed items;
  keyboard navigation reached item 12, header mouse clicks collapsed/reopened
  Todos, and the draft stayed unchanged. Popup callbacks were instrumented and
  none fired. Captures: `/private/tmp/attro-inline-dock-captures`.

The follow-up is delivered through a new prepared release, never by replacing
files inside a running release or rewriting personal configuration.

## Rich agent controls and direct interaction verification (2026-09-09)

The user clarified that the dock's Extensions entry/chooser should be removed,
not Ctrl+O tool-output expansion. The chooser and its Alt+O binding are removed.
Legacy widgets share an inline ScrollView instead, including in very short
terminals; their component lifecycle and zero-row infrastructure stay intact.

Agents now reuse the existing responsive dashboard renderer rather than the
name/activity-only projection. Inline rows include role, model/thinking,
context, cost, tokens and age where width permits. Down-at-editor-end or a row
click focuses the list; arrows select by stable run ID, Enter inspects that
agent, x stops it, and Escape returns to the untouched draft. `/subagents`
shows dismissed/history records inline, not in a popup list. Queued states
retain attention styling. Explicit per-agent detail/steering remains available.

Verification:

- Final core `npm run check` passed with Homebrew Node 26.5.0 and no formatter
  changes. The existing dock-sections/chat-viewport/attro-editor Vitest files
  passed 42 tests; three primary LSP checks were clean.
- `env -i HOME="$HOME" PATH=/opt/homebrew/bin:/usr/bin:/bin
  /opt/homebrew/bin/node subagents.test.cjs` passed 321 checks on final source.
- Independent review found popup history, extreme-height legacy-widget access,
  and queued-attention issues. All three were corrected and covered by the
  focused checks; lead directly confirmed inline history after correction.
- Lead ran the source CLI with real CC, Zentui, todo, and subagent code in
  isolated state. Valid registry fixtures exercised rich metadata and overflow;
  no replacement agent-section callbacks were used. Twelve records were
  verified through the production registry reader before UI testing.
- The production spawn-agent tool was captured at registration and invoked with
  the real UI context, launching the repository's local fake RPC child. Enter
  opened that selected child's real detail view; typed steering was recorded by
  the child as an RPC steering message; x cancelled that same child. The draft
  remained intact. This exercises real plugin/process/control wiring, not a
  paid provider. Automatic parent continuation after cancellation reported the
  expected missing-key error in the deliberately unauthenticated test profile.
- Captures during selection/detail/steering/cancellation, narrow resizing, and
  selection after reordering are under
  `/private/tmp/attro-real-agent-ui-repro/captures/`. Final control captures use
  `final-controls-*`; earlier valid source captures use `corrected-*`.
  `/subagents` was separately checked with a dismissed fixture visible inline.

The earlier helper's baseline captures are not acceptance evidence: its seed
omitted the required task field and its refresh replaced production callbacks.
The lead replaced that helper with `extensions/real-plugin-check.ts` and
`try-source.sh` in the same temporary harness directory. No credentials or
personal profile contents were copied; display defaults alone were used.

## Shortcut-only focus and performance (2026-09-09)

The user confirmed Alt+A/Alt+T for focus and the same shortcuts plus Shift for
collapse/expand. Focus opens a collapsed list and is idempotent. Toggling another
list does not steal focus; collapsing the focused list returns to the draft.
Down, mouse clicks/wheel, background updates, and `/subagents` no longer acquire
managed dock focus. Ordinary Pi retains its legacy behavior; managed Todo leaves
shortcut ownership to core so the shipped `collapseKey: alt+t` cannot shadow
core remaps. The capability guard no longer requires the obsolete optional
navigation method to recognize a native dock host.

Direct terminal testing caught tmux's Shift+Alt encoding (`ESC[27;3;65~`), where
Shift is implicit in the uppercase code point. Decoder coverage now includes
that form, explicit modifiers, CSI-u and legacy ESC+uppercase, while retaining
ESC+B/F word navigation. The coding-agent Vitest config now aliases the canonical
TUI package to workspace source rather than testing stale generated output.

Verification on Homebrew Node 26.5.0:

- Core `npm run check` and five focused Vitest files passed (52 tests).
- TUI `node --test test/keys.test.ts test/keybindings.test.ts` passed 69 tests.
- Subagents' clean-environment harness passed 325 checks, including a native host
  without the optional navigation method remaining shortcut-only.
- Todo `npm run check` and its package tests passed (247 tests); the previously
  documented unrelated Biome informational finding remains.
- Real Todo/Agents factories and tool hooks were exercised together with CC and
  Zentui in `/private/tmp/attro-shortcut-acceptance.sh`: default focus shortcuts,
  shifted toggles, idempotent refocus, switching between lists, and continued
  typing after Down, mouse clicks/wheel, and history commands all passed.
- `/private/tmp/attro-shortcut-remap-check.sh` repeated the interaction checks
  with custom core bindings, confirming the old Alt+A/T defaults did not retain
  hidden plugin handlers. No personal configuration was changed.

Performance changes are bounded to presentation: precompute last siblings rather
than repeatedly filtering the tree; resolve row allocations once per render; pass
one registry snapshot through a changed-agent poll refresh instead of reading it
up to three times. No cross-frame content cache, polling interval, storage, or lock
semantics changed.

An isolated benchmark compared the archived prior plugin pin `562747b` with the
working correction, invoking real production renderers (five warmups, up to 200
samples). At 1,000 records/120 columns, an eight-visible-row refresh measured
p50/p95 **4.5655/5.0455 ms → 0.1909/0.2174 ms**. At 120 records, full DockSections
render measured **0.7866/1.1292 ms → 0.2495/0.3020 ms**. These are in-memory renderer
measurements, not an end-to-end UI speedup claim. Artifacts and reproducible
before/after scripts are under `/private/tmp/attro-dock-perf`.

Synthetic registry IO at about 500 files/5.8 MiB still took tens of milliseconds
per snapshot. IO remains the next bottleneck for large histories; this change
avoids redundant reads but does not cache or alter durable state. The harness's
static sibling-work estimate describes the old algorithm, not current tracing.

## Focus return and inactive input appearance (2026-09-09)

The follow-up changes repeated Option/Alt+A or T from idempotent focus to a
return-to-input action when its own list is already focused. The other shortcut
still switches lists. Up/previous-row now clamps at the first row rather than
returning to the editor. Shift variants retain their disclosure-only behavior.

The native editor hides its fake cursor and uses a faint, muted frame while
unfocused, restoring the original appearance on return. Faint styling keeps the
states distinguishable even when a theme maps the active border to borderMuted;
activity/error colors and draft/cursor state remain intact. No timers or polling
were added.

Existing behavioral tests demonstrated both navigation failures and the inactive
border failure before the fixes. `npm run check` and all 52 focused core tests
then passed on Node 26.5.0. The real-plugin terminal acceptance script verified
repeated Up on both lists, same-shortcut return, cross-list switching and typing
retention. ANSI captures independently confirmed cursor hiding, a distinct faint
border, and exact active-border restoration using
`/private/tmp/attro-check-editor-focus-style.py`.
