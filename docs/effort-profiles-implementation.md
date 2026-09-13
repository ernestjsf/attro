# Effort profiles — implementation and verification

Implemented in the working tree; not committed, built, installed, or activated.
Personal configuration and agent definitions were not changed. No live provider
requests or real credentials were used for verification.

## Behavior

- Global, user-owned `effort-profiles.json`; missing configuration leaves routing
  unchanged and `/profile create` or `/profile presets` can bootstrap definitions.
- Session-local selection/cycling, explicit startup-default saves, create/edit/copy,
  category/agent mappings, fixed agents, configurable cycle order and shortcuts.
- Omitted lead fields use the pre-profile session baseline, including restoration
  and detach/reselect. Explicit task fields retain per-field precedence.
- Core-owned resolution and session/branch snapshots; immutable child inheritance
  survives parent switches and catalog deletion. Inactive parents send explicit
  null inheritance to suppress child startup defaults.
- Native status and Attro editor metadata include the profile; inspector exposes
  availability, requested/effective thinking, participation and provenance.

User documentation: [Effort profiles](../plugins/attro-core/packages/coding-agent/docs/effort-profiles.md).

## Changed paths

Under `plugins/attro-core/packages/coding-agent/`:

- New `src/core/effort-profiles.ts` and `effort-profile-session.ts`.
- Core integration in `agent-session.ts`, `agent-session-services.ts`, `sdk.ts`,
  `session-manager.ts`, `keybindings.ts`, and `extensions/{types,loader,runner,index}.ts`.
- Public exports/startup in `src/index.ts` and `src/main.ts`.
- Interactive command/presentation changes in `src/modes/interactive/interactive-mode.ts`,
  `effort-profile-ui-port.ts`, and `components/{profile-editor,profile-selector,attro-editor,index}.ts`.
- New effort-profile/UI/editor tests; existing keybindings and trigger-compact
  extension fixtures updated. Documentation index/keybindings and effort-profile guide.

Under `plugins/pi-subagents/`: `agents.ts`, `index.ts`, `spawn-agent.ts`, `types.ts`,
`effort-profile-spawn.ts`, `pi-coding-agent-effort-profiles.ts`, `fake-pi.cjs`,
`subagents.test.cjs`, test-only `quattro-pi-package-entry.ts`, and `README.md`.

Under `plugins/pi-zentui/`: `extensions/zentui/{index,minimalist-editor,native-editor}.ts`
and `test/minimalist-editor.test.ts`.

Root documentation records the baseline clarification and this evidence report.
No installer, dependency, lockfile, or personal-policy changes were needed.

## Tested revisions

All checks used uncommitted task changes over these revisions:

| Repository | Revision |
| --- | --- |
| Root | `28b139d` |
| Core | `f8ae9815a5fec4f217fc2b24a4d8fbb9f8d2a4c5` |
| Subagents | `428b3f2` |
| Zentui | `f4c0412` |

Core execution used Node `v26.7.0`, npm `11.19.0`; offline fixtures and isolated
configuration were used for behavioral/terminal checks. No executable changes
followed the final checks. This report is prose-only.

## Checks

From `plugins/attro-core`:

```sh
PATH=/opt/homebrew/bin:/usr/bin:/bin npm run check
```

Passed, including formatting, pinned dependencies, import/entry graphs,
shrinkwrap/install-lock verification, TypeScript and browser smoke. No formatter
changes in the final run. Full output:
`/private/tmp/attro-effort-check.1SmOib/core-final-check.log`.

From `plugins/attro-core/packages/coding-agent`:

```sh
env PI_OFFLINE=1 node ../../node_modules/vitest/dist/cli.js --run \
  test/effort-profiles.test.ts test/session-manager \
  test/agent-session-runtime-events.test.ts \
  test/agent-session-branching.test.ts test/agent-session-tree-navigation.test.ts

node ../../node_modules/vitest/dist/cli.js --run \
  test/effort-profile-ui.test.ts test/attro-editor-profile.test.ts \
  test/keybindings.test.ts test/model-selector.test.ts test/thinking-selector.test.ts \
  test/footer-width.test.ts test/footer-data-provider.test.ts
```

Passed: respectively **135 tests, 13 skipped** and **44 tests across seven files**.
Logs: `/tmp/core-finish-persistence-green.log` and
`/tmp/ui-corrections-final-tests.log`. Custom-model activation and competing-writer
partial-checkpoint regressions were demonstrated red-to-green.

From `plugins/pi-subagents`:

```sh
env -i HOME="$HOME" PATH=/opt/homebrew/bin:/usr/bin:/bin \
  /opt/homebrew/bin/node subagents.test.cjs
```

`ALL PASS`, including real core resolver/fake-child coverage for precedence,
queued descendants, explicit overrides, catalog-independent inheritance and root-off
null propagation. The harness uses its sandbox for agent/profile fixtures.

From `plugins/pi-zentui`, with `/opt/homebrew/bin` first in `PATH`:

```sh
npm run fmt
npm run verify
npm run pack:check
```

Passed: **46 test files, 1,389 tests passed, one skipped**; 44 package files checked.
No formatting changes. Later corrections touched only core, not Zentui.

Proactive primary LSP: seven core backend files, seven UI files and three Zentui
files clean. `lens_diagnostics mode=all` reported no blocking errors; subagents
had 120 non-authoritative inferred-project warnings (missing tsconfig/module/Node
resolution). These were not suppressed or presented as a successful plugin typecheck.
`git diff --check` passed for root and all three changed repositories.

## Terminal evidence

Source CLI in real tmux terminals, isolated HOME/config, `PI_OFFLINE=1`, inert
custom models at `127.0.0.1:1`, no real keys. Compared no-extension native UI with
actual CC, Subagents and Zentui source extensions plus repository display config;
managed-style invocation used `ATTRO_MANAGED=1`. No installed release was mutated.

Verified at **100×32, 52×18 and 36×12**:

- Profile label remains visible and two-line drafts survive cycling/resizing.
- Created `terminal-profile` using available-model/thinking choices; label text
  `Terminal 123 c` accepted; explicit save inserted it at cycle position 2.
- Inspector lists fixed/mapped/unmapped agents, unresolved portable mappings,
  selected-profile details, availability and lead/profile provenance.
- Starter preset flow reached Ultra/model/thinking/editor preview; cancellation
  left the catalog SHA-1 unchanged (`c2bf178d5e64ffe34fbe164591cc8d0997f9f53e`).
- Contextual model-selector Ctrl+S saved the fixture model default instead of
  cycling the profile; the draft survived and manual deviation showed custom state.
- Remapped forward/backward to Alt+S/Alt+B: Ctrl+S no longer cycled; both remapped
  actions worked without losing the draft. Other running sessions were unchanged.

Harness: `/private/tmp/attro-effort-check.1SmOib/run.sh`.
Captures: `/private/tmp/attro-effort-check.1SmOib/captures/` (native/Attro wide,
narrow, short; authoring, preset preview and remapping). Temporary evidence paths
are local and may be cleaned by the operating system.

## Independent review and limits

Astra independently reviewed concrete configuration-loss, persistence, route/scope
and child-isolation risks. Corrected all nine reported findings: destructive
checkpoint rollback, duplicate-ID overwrites, mutable-catalog routing dependency,
root-off inheritance, editor construction/focus, synchronous-save handling,
text-consuming shortcuts, and missing bootstrap/authoring actions. Scoped
re-review of corrections found **no unresolved material findings**.

Existing-session checkpoint failures now preserve bytes and publish no successful
switch. An uncertain write permanently blocks that SessionManager's mutations;
stop and inspect/recover the file before reopening. No automatic truncation,
retry, or repair is attempted, and unchanged on-disk history is not guaranteed.

**Known baseline test failure:** `test/agent-session-concurrent.test.ts:291`
expects abort to deliver queued extension steering. It fails identically with
unchanged baseline `f8ae9815` AgentSession source, reproduced using
`/tmp/verify-effort-baseline.sh`. A broader backend selection reported 202 passed,
18 skipped and this one failure (`/tmp/core-finish-regressions.log`). It was not
changed as part of profiles; a fully green no-profile regression gate is therefore
not claimed.

No full core suite/build, installer gate, live provider routing, paid model use,
or installed-release verification was performed. Existing explicit model overrides
and personal model-specific instructions can still take precedence over profiles;
no personal policy was rewritten.
