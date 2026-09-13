# User-defined effort profiles — implementation plan

## Status and authorization

Planning handoff only. No implementation, personal configuration changes, commits,
installation, activation, or provider requests were performed or authorized by this
planning task. The next agent should implement when instructed, not treat this
file as permission to deploy or rewrite personal configuration.

Repository: `/Users/example/projects/pi-customizations`.
Discovery baseline: root `202375c`, `plugins/attro-core` `a641985`.
Recheck current source and worktree status before starting; these are observations,
not pins to restore. Read applicable `AGENTS.md` files and full relevant SDK/TUI
docs before implementation. Paths below are relative to the repository root.

## Agreed product direction

- A configurable shortcut, initially Ctrl+S, cycles effort profiles.
- Profiles select the main session's model/thinking and the defaults used by
  participating agents. Roles, instructions, permissions, and required reviews
  remain independent of profiles.
- Low, Balanced, High, and Ultra are editable starter presets, not special runtime
  tiers. Users can create, duplicate, edit, select, and reorder their own profiles.
- Custom agents can participate through explicit per-agent mappings or a category,
  or remain fixed. Unconfigured agents retain existing behavior.
- Explicit task overrides beat profile defaults; profile defaults beat agent defaults.
- Show the active profile and inspect resolved model/thinking for all discovered
  agents, including why each value was selected.
- **Explicit user decision:** switching is session-local. Definitions are durable;
  selecting a profile does not change the startup default. Saving a startup default
  is a separate explicit action. Other running sessions are unaffected.

The concrete schema and lifecycle rules below are recommended implementation
contracts, not claims that corresponding APIs already exist. Keep changes bounded;
raise a material conflict rather than silently expanding scope.

## First increment and exclusions

Deliver manual profiles end-to-end: configuration, authoring/selection commands,
shortcut, current-session application, agent resolution, child inheritance,
inspection, restoration, and real terminal verification.

Do not add automatic escalation, task-scoped boosts, model benchmarking, budget
accounting, automatic fallback providers, profile inheritance graphs, or new
workflow/review/delegation modes. Ultra must not automatically create more agents.
Do not turn arbitrary profile names (such as `local-only`) into implied security
policies. A name alone does not enforce network isolation or spending limits.

Recommend global user-owned definitions only for v1. Trusted project agents still
participate; project profile files/overrides can follow separately. Do not add a
second project-trust mechanism or load untrusted project profile configuration.

## Existing seams and constraints

### Core

Within `plugins/attro-core/packages/coding-agent/`:

- `src/core/agent-session.ts`: `setModel`, `setThinkingLevel`, `cycleModel`,
  `cycleThinkingLevel`, `_emitModelSelect`, and SDK/extension action wiring.
  Ordinary switches are already session-local unless `persist: true`.
  `setModel` checks auth, appends a model change, chooses a model-specific/default
  thinking level, and emits events. `setThinkingLevel` clamps unsupported levels.
  A naive `setModel` then `setThinkingLevel` profile switch exposes intermediate
  state to observers; do not declare success or publish profile state too early.
- `src/core/settings-manager.ts`: existing startup defaults and per-model effort.
- `src/core/session-manager.ts`: append-only session entries, custom entries, branch
  reconstruction, resume/fork. Profile restoration must follow the selected branch,
  not the last physical line in the file.
- `src/core/keybindings.ts`, `src/modes/interactive/interactive-mode.ts`: configurable
  action registration and native editor handlers. Do not hardcode key matching.
- `src/core/footer-data-provider.ts` and
  `src/modes/interactive/components/footer.ts`: native status presentation.
- `src/core/extensions/types.ts`, SDK exports, CLI startup and RPC seams: inspect
  before defining the small cross-package profile-state contract.

Ctrl+S already means save in model/thinking/scoped-model selectors and sort in the
session selector. Keep those contextual actions. The profile action belongs to
normal composer focus, not a global handler that steals modal/list input.

Read `docs/keybindings.md`, `docs/settings.md`, relevant sections' linked docs, and
`examples/extensions/model-status.ts`. The installed Pi documentation is a useful
foundation but source Attro behavior is authoritative.

### Subagents

Within `plugins/pi-subagents/`:

- `agents.ts`: `AgentDefinition`, strict allowed frontmatter fields,
  `loadAgentDefinitions`, `resolveSpawnInput`. Global definitions load first;
  trusted project definitions override by name. Definition bodies supply prompts.
- Today `resolveSpawnInput` folds definition defaults into input, explicit fields
  winning. After folding, definition model/thinking looks like an explicit input.
  Preserve original input/provenance before inserting profile resolution.
- `spawn-agent.ts`: `startSubagent`, `resolveChildModel`, `scopedModelArgs`, spawn
  environment/CLI construction. Effective model currently resolves from explicit
  input > named definition > subagent default > parent model. Thinking follows
  the corresponding chain, finally `off`.
- `index.ts`: tool handler builds `SpawnContext`, currently passing parent model,
  thinking, tools, scoped models, recursion limits, and managed-resource context.
- `types.ts`: spawn context/input and `AgentRecord`.
- `config.ts`: existing defaults and thinking validation.
- `subagents.test.cjs`: existing public-spawn/fake-child harness, definition,
  override, model-scope, and nested propagation coverage.

Preserve scoped-model restrictions, tool narrowing, recursion/concurrency limits,
managed-release resource inheritance, and explicit spawn override behavior. An
empty model scope currently defers model validation to core; profiles should use
core model resolution rather than introduce a competing fuzzy resolver.

### Actual Attro presentation and configuration

- `plugins/pi-zentui/extensions/zentui/`: existing footer/editor metadata and
  thinking-status rendering. Inspect its entrypoint and applicable instructions;
  verify the indicator with the real installed-style plugin stack, not native
  footer alone. Prefer an existing status channel if it renders correctly.
- `profile/MANAGED.md`: user state belongs in the resolved agent directory, normally
  `~/.attro/agent`; release code is immutable. Do not hardcode the home directory.
- `attro/profile.py` and existing root profile-boundary tests govern managed user
  configuration, not this new effort-profile concept. Avoid confusing the names.
- Personal model routing and agent definitions are deliberately not installer-seeded.
  Do not add Ernest's models, roles, or prompts to the public managed defaults.
- Some historical managed-resource verification prose is stale; consult source and
  current regression tests instead of treating an old pending gate as current fact.

## Suggested configuration contract

Use existing JSON conventions, with `effort-profiles.json` in the resolved agent
configuration directory. Reuse existing safe configuration persistence where
appropriate rather than introducing a configuration framework. Missing file means
profiles are disabled and existing behavior remains unchanged.

Illustrative schema (model values are placeholders, not usable defaults):

```json
{
  "version": 1,
  "defaultProfile": "balanced",
  "cycle": ["low", "balanced", "deep-work"],
  "profiles": {
    "balanced": {
      "label": "Balanced",
      "lead": { "model": "provider/model-id", "thinking": "medium" },
      "categories": {
        "worker": { "model": "provider/worker-id", "thinking": "high" }
      },
      "agents": {
        "researcher": { "thinking": "high" }
      }
    },
    "low": {
      "label": "Low",
      "lead": { "model": "provider/fast-id", "thinking": "low" }
    },
    "deep-work": {
      "label": "Deep work",
      "lead": { "model": "provider/strong-id", "thinking": "high" }
    }
  }
}
```

Use `thinking`, not a second `effort` field, to match current APIs. Model selectors
written by the UI must be canonical provider-qualified IDs, including deliberate
provider-specific variants such as Composer speed aliases. Do not silently
normalize subscription routes into API routes or strip meaningful suffixes.

IDs are stable, unique, bounded strings; labels are display-only. Reject unknown
schema versions, malformed mappings, invalid thinking names, duplicate/unknown
cycle references, and invalid defaults with actionable file/field errors. Profiles
outside `cycle` remain selectable. An empty cycle disables cycling; a one-entry
cycle is a harmless no-op unless reapplying a modified profile. No implicit sort by
perceived power and no conditional logic on `low`/`ultra` names.

Mappings may omit model or thinking independently; omission falls through to the
next source. **Implementation clarification agreed with the user:** omitted lead
fields fall back to the session's pre-profile model/thinking baseline, not current
values left by another profile or manual override. Preserve that baseline through
session restoration. No null/delete semantics or multi-level category inheritance in v1.
Distinguish malformed config from a well-formed profile whose models are currently
unavailable. Never overwrite a malformed user file to repair it automatically.

### Custom agent participation

Suggested new optional frontmatter:

```yaml
profileCategory: worker
```

or:

```yaml
profileMode: fixed
```

- An explicit `profiles.<id>.agents.<agentName>` entry is user opt-in for that agent.
- `profileCategory` opts into that category's defaults; category names are arbitrary.
- `profileMode: fixed` excludes all profile model/thinking mappings for this agent.
  It does not revoke the existing ability to supply an explicit task override.
- With neither a mapping nor a category, resolve exactly as today.
- An explicit agent mapping overlays its category per field.
- Unknown categories simply supply no values; report that fact in inspection.
- An agent-level map naming an undiscovered agent is retained and marked unresolved,
  allowing portable configs and agents that exist only in particular projects.

Add fields to the strict parser deliberately; do not make it accept arbitrary
frontmatter. No prompt/tool/cwd/timeout edits from profile mappings.

## Resolution and state rules

### Per-field child resolution

For each of model and thinking, choose the first supplied value:

1. Original explicit spawn input.
2. Active snapshot's mapping for the agent, unless fixed.
3. Active snapshot's category mapping, unless fixed.
4. Named definition default.
5. Existing subagent configuration/environment default.
6. Immediate parent's active model/thinking; final thinking fallback remains `off`.

Resolve before flattening provenance. Record the source of each winning field for
inspection. Anonymous spawns retain current behavior; do not silently classify
all unnamed children as workers. An explicit model override does not implicitly
wipe an independently configured thinking value; validate the resolved pair and
report any existing capability clamp transparently.

Do not relax sensitive-review instructions or required checks. These are currently
primarily role/prompt policy, not a universal machine-enforced policy engine. Do
not claim profiles add such enforcement. Existing explicit sensitive-review model
overrides still win. If a preset conflicts with required policy, resolve that
conflict explicitly rather than lowering the requirement.

### Applying a profile

1. Load and validate a candidate configuration/profile without mutating live state.
2. Resolve the lead target and participating discovered agents through the same
   resolver used for preview/spawn. Validate model existence, current capabilities,
   auth availability, and applicable scopes without making provider requests.
   Block activation for unusable explicit mappings of participating discovered
   agents; retain unresolved mappings for agents not discovered here.
3. Present requested/effective thinking where core clamps capabilities. Preserve
   provider semantics: Composer `thinking: off` is not a guarantee that Composer
   does no internal reasoning. Reject unknown levels; never silently change model
   or provider to obtain a higher level.
4. Apply only while the lead session is idle, including prompt preflight,
   compaction/retry and other session operations. For v1, a busy switch returns
   an actionable notice instead of aborting work or installing a hidden queue.
   Already-running children do not prevent an idle lead from switching.
5. Coordinate lead model/thinking and active snapshot publication so a reentrant
   observer/spawn cannot receive a mixed old/new profile. Prevent overlapping
   switch requests; recheck idle/state after asynchronous validation. Reuse core
   mutation plumbing with the smallest necessary coherent apply seam.
6. Emit the profile-state event/indicator and persist session metadata only after
   successful application. Failures must not report a successful switch or alter
   startup defaults. Specify and test event/history behavior if persistence fails;
   do not paper over partially applied state with a misleading label.

Selecting a different profile replaces prior lead manual overrides. Ordinary
`/model`, model cycling, `/thinking`, and thinking cycling remain available and
mark the profile `custom` when actual lead values differ. Reapply the active
profile to reset those deviations. Explicit one-child overrides do not mark the
whole parent profile custom.

### Startup, resume, branches, and children

- Fresh session: saved default profile if configured, otherwise existing startup
  behavior. Explicit CLI/SDK lead model/thinking options win per field and show
  `custom` when different. A bad/unavailable startup profile must not silently
  pick another provider: report it; noninteractive invocation fails clearly, while
  interactive startup offers correction or explicit no-profile continuation.
- Resume/fork/tree: restore the selected branch's effective profile snapshot and
  actual lead model/thinking, not today's edited default. Do not overwrite resumed
  lead state with a fresh default. Old sessions without metadata work normally.
- Save a bounded, credential-free selected profile snapshot and ID/label in session
  metadata using existing session mechanisms; no full user catalog or prompts.
  Config edits/deletion do not retroactively change that snapshot. Inspector marks
  it changed/missing on disk; explicit selection/reapply adopts current definitions.
- New descendants inherit the snapshot captured when their parent was spawned,
  not a mutable process-global profile ID or a later reread of global config.
  A lead switch cannot change an existing child's future grandchildren.
- Child startup must not apply the snapshot's `lead` mapping over the resolved
  child model/thinking. Carry inheritance context separately from startup lead
  selection. Preserve the current managed-resource envelope and scope narrowing.
- Capture a run's profile provenance at spawn acceptance, including while queued.
  It remains fixed for that run. Do not extend agent lifecycle or queue behavior.
- No profile state in global `process.env` that can couple independent SDK sessions.
  A validated, size-bounded per-child launch envelope is acceptable; inspect current
  launch mechanisms first. No credentials or paths to mutable personal snapshots.

## Ownership and implementation sequence

Prefer core-owned session state/resolution utilities plus a thin subagent adapter,
not a UI extension with an unrelated second resolver. Core should not import the
subagents plugin. Provide a small read-only context/API for active snapshot and
resolved model capabilities; the plugin retains definition discovery and spawning.
Avoid a general plugin registry unless existing APIs make it necessary. Agree the
exact shared contract before parallel work; one writer per shared file.

### 1. Configuration and pure resolution

Define validated types, loading, per-field provenance, and shared resolution.
Integrate opt-in frontmatter without changing tools/prompts. Extend existing
behavioral tests for explicit override vs profile vs definition fallback, category,
fixed and unconfigured agents. Test invalid files with no mutation.

### 2. Session application and restoration

Implement idle-only coherent application, effective/custom state, snapshot history,
startup default handling, branch restoration, and read-only SDK/extension exposure.
Cover failures and independent SDK sessions before UI wiring. Inspect extension
model/thinking events for intermediate-state and feedback-loop hazards.

### 3. Subagent integration

Resolve at the original request seam; pass immutable inheritance context and record
provenance. Verify nested fake-child behavior, queued-run snapshots, explicit
sensitive-review overrides, model scopes and managed resource inheritance. Do not
copy the lead mapping onto worker startup.

### 4. Commands and presentation

- `/profile`: selector/inspector, active and saved-default indicators, availability
  and custom state. Display every discovered agent's resolved model, thinking,
  participation and provenance; do not hide fixed/unmapped agents.
- `/profile <id>`: select; `/profile off`: detach while retaining current lead
  model/thinking and reverting future spawns to ordinary defaults.
- `/profile create`: guided name and model/thinking selection; allow copying an
  existing profile. `/profile edit <id>`: reuse the same editor for lead/category/
  agent assignments, labels and cycle membership/order. A compact existing dialog
  flow is sufficient; no new dashboard framework. Cancellation writes nothing.
- Expose explicit reapply and save/clear startup-default actions in the inspector.
  Handle command-word/ID collisions via parser rules or reserved-ID validation.
- Profile creation/edits persist only after validation and explicit save. Do not
  overwrite concurrent edits: reuse existing safe locked/read-modify-write storage,
  or detect a changed file and ask the user to reload. Review before implementing
  a new locking mechanism. Do not silently replace chezmoi-managed sources.
- Provide an explicit starter-preset creation flow using user-selected available
  models and supported thinking levels. All starter mappings become ordinary user
  data. Do not preseed personal providers, routes or agent definitions at install.
- Add `app.profile.cycleForward` with Ctrl+S default and a configurable reverse
  action (no default needed). Preserve selector save/sort, remapping, draft,
  focus, history and fullscreen search. No raw key checks.
- Show compact profile status in native and actual Attro footer/editor metadata.
  Use theme tokens, bounded widths, and accessible textual unavailable/custom state.

### 5. Documentation, integration review, and verification

Update user-facing profile/keybinding/agent-definition docs and relevant changelogs
according to each repository's rules. Explain persistence, precedence, fixed
semantics, custom state, busy behavior, provider routes and startup failure.

Personal `AGENTS.md` currently describes specific lead/role defaults. Warn that
an instruction demanding one model or always supplying explicit spawn overrides
can defeat profiles. Do not rewrite it or agent definitions without authorization;
if adapting personal policy is needed, propose that separately and preserve its
sensitive-review requirements. Managed dotfile changes must use chezmoi source
and targeted apply, never overwrite templates with rendered contents.

Request an independent review before completion. Persistence and cross-session /
child snapshot isolation warrant focused review of data loss and concurrency
failure paths; use Astra for concrete configuration-loss, auth-route or scope
boundary risks, not merely because the feature mentions models. Review actual
changes once and re-review corrections, not a repeated broad architecture audit.

## Acceptance and verification gates

Use existing behavioral tests/public seams and add only coverage distinguishing
these requirements. This plan explicitly calls for the necessary regression tests.
No paid providers, real credentials, live profile edits, or installed release
mutation during verification.

Required scenarios:

1. Arbitrary custom profiles cycle in configured order and are selectable outside
   the cycle; empty/one-entry cycles, remapping and contextual Ctrl+S work.
2. Per-field precedence, category, explicit map, fixed and unmapped agents work;
   explicit task overrides and existing policy/tool/scope boundaries survive.
3. Invalid/unavailable configuration and auth/scope failures cause no misleading
   applied state, partial default writes or fallback provider requests.
4. Busy and overlapping switches do not race prompts or yield mixed snapshots.
5. Switching A to B leaves another SDK session, running/queued children and their
   future descendants on A; newly spawned children use B.
6. Resume/fork/branch restore uses branch-local snapshots despite config edits;
   missing metadata and missing/deleted profiles have defined behavior.
7. Manual lead overrides show custom; reapply resets them; startup save is explicit;
   selection/reload never rewrites model defaults or agent definition files.
8. Create/edit/cancel and conflicting external config edits preserve user data.
9. Real terminal inspection with native and Attro plugin presentation at wide,
   narrow and short sizes; preserved multiline draft/focus and selector shortcuts.
10. No-profile operation passes existing model/thinking/subagent regression tests.

Commands/gates to select from after checking current instructions:

- Proactive LSP diagnostics for changed source before builds/checks.
- Core root: `npm run check` after code changes; preserve full output.
- From `plugins/attro-core/packages/coding-agent`, run focused Vitest files via
  `node ../../node_modules/vitest/dist/cli.js --run test/<affected>.test.ts`.
  Existing candidates include `keybindings.test.ts`, `model-selector.test.ts`,
  `thinking-selector.test.ts`, `footer-width.test.ts`, `footer-data-provider.test.ts`,
  relevant `agent-session-*` and session-manager tests; choose by actual diff.
- Subagent root: `node --test subagents.test.cjs`, preferably isolated environment
  as existing harness docs recommend. Extend its real fake-RPC-child seam.
- Zentui: read its `AGENTS.md` and scripts; run required checks and affected tests
  if changed. A core-only footer test is not enough for Attro acceptance.
- Root Python/installer gates only if managed config/launcher boundaries change;
  avoid expanding into installer work just to seed model presets.
- `git diff --check`; `lens_diagnostics` mode `all` for edited code before done.
- Do not run core build or full tests without the authorization required by core
  instructions. Use focused suites and an existing source-CLI terminal harness;
  request a build if rendered verification actually requires it.

Final implementation report: changed paths, exact commands/results, revision plus
uncommitted diff tested, review findings/corrections, actual terminal evidence,
and unverified limits. Do not claim a release is installed or profile routing is
verified with live providers based on synthetic tests.

## Handoff checklist

- [ ] Validate current source, instructions and shared API seams.
- [ ] Configuration/resolver and agent opt-in semantics.
- [ ] Session-local coherent application and restoration.
- [ ] Child snapshot propagation and scoped-model preservation.
- [ ] User-created presets, commands, shortcut and real Attro indicator.
- [ ] Focused failure-path coverage and rendered inspection.
- [ ] Independent scoped review, docs, checks and evidence report.

Planning evidence: read-only core/source discovery and a subagent-focused scout;
no executable behavior was tested for this unimplemented feature. The only intended
repository change from this planning task is this document.
