# Native bottom dock implementation plan

## Approved direction

Attro core owns one bottom dock. Preserve the native editor and its editing,
completion, paste, history, and focus behavior. Place compact task and agent
sections below the composer; expanded lists share a height budget and full
content remains available through existing detail interfaces. Background updates
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
This is a committed source candidate, not an activated release or a claim that
all historical release gates have passed.
