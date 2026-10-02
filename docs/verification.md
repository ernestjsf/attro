# Local milestone verification

Evidence from Attro implementation work on macOS. This is **not** a public
release certification or evidence of Linux/Windows/second-machine compatibility.
**Attro 0.2.0** shared-profile, `./install`, everyday `attro` launcher,
source-core build, and subagent resource-inheritance gates are **partially
verified locally**, not certified for publication.

## Pi 1.0 native candidate source verification (2026-10-03)

Source pins: core `f9d1dd5b`, Lens `fb827854`, subagents `c17a2e93`, unchanged
RPIV `1a1d7818`. The candidate is maintained in an isolated checkout; the
original checkout's unrelated edits were preserved. Local commits only; this
is not a public release or cross-platform certification.

- Core Pi 1.0 integration passed `npm run check`, `npm run build:offline`,
  isolated `./test.sh` (coding-agent **2,955 passed / 50 skipped**, AI **1,259
  passed / 859 skipped**, remaining package suites passed), and **241** focused
  UI/profile/RPC tests. Network-denied terminal checks at 100 and 40 columns
  retained Attro's composer, branding, settings, and native MCP menu.
- Subsequent native MCP storage/approval changes passed focused store, refresh,
  command, and session tests, required checks/hooks, and offline builds. A real
  macOS keychain probe used only a synthetic service/account and local OAuth
  fixture; **38 operations** passed and the synthetic credential was removed.
  No adapter credentials were imported or inspected.
- Independent sensitive review found brief storage-lock contention and stale
  lease takeover risks. The correction uses non-expiring owner-marked mutexes
  for managed storage and refresh, with bounded contention waits and explicit
  offline crash recovery. **118** focused tests passed, including independent
  processes, token rotation, SIGSTOP/SIGCONT, crashed holders, cancellation,
  and replacement-owner protection. Scoped Astra re-review cleared both
  findings. Pending-confirmation config replacement and mixed protected /
  unprotected resource enumeration also have direct behavioral coverage.
- Lens native deferred discovery passed build, strict lint, distribution and
  packaging checks, **310** focused tests, and the release suite: **8,860
  passed / 47 skipped**. The existing BOM drift fixture follows Pi 1.0's helper
  location; the six situational tools no longer use a custom activation tool.
- Combined subagents passed **524** checks plus **30** concurrency checks.
  This includes native capability snapshots/RPC and the independently reviewed
  Agents overview change (source `50f3d6f`, integrated as `9ffb1030`). Its real
  PTY probe at 100/40 columns retained the latest visible progress while
  reducing 40 progressing updates to five terminal frames in the recorded run.
- Pi 1.0 review also found that nesting `check_subagents` could retain the
  caller's concurrency permit and lose persisted delivery acknowledgement.
  Native `model-only` exposure fixes both without changing scheduler/delivery
  storage. A public registration regression failed before the fix and passed
  afterward; scoped sensitive re-review confirmed native callable exclusion.
- Root shell forwarding now preserves `mcp` as the first core argument rather
  than prepending session resource flags. Three invocation subcases failed
  before the correction. The full root suite passed: **241 run / one skipped**;
  primary LSP found no errors in the affected root/subagent files.

Environment: macOS arm64, Node **26.7.0**, npm **11.19.0**, Python **3.14.6**.
Component evidence is retained in local integration/security handoff logs.
Source-pin validation and prepared-artifact smoke tests must use the final
recipe and record its manifest/release identity before activation. Source tests
are not evidence that a later prepared artifact has been tested.

Known limits: native MCP needs fresh user sign-in, retains per-call approval,
and has no MCP app windows. Provider routes and effort-profile choices remain
unchanged. Keychain crash recovery requires all relevant processes to be
verified stopped; prolonged post-rotation unavailability can require sign-in.
Linux keychains, standalone Bun, and authenticated remote MCP workflows are not
certified by these checks. `npm audit` reports three high-severity package
findings in unchanged Gondolin `0.12.0`, node-forge `1.4.0`, and brace-expansion
`5.0.9`; those exact versions also occur in the original Pi 0.87.1 fork lock.
They were identified, not remediated as part of the native MCP dependency change.

## Pi 1.0 root recipe preparation (2026-10-03)

Tested root baseline `2a0623eb702ba5846b688939c03c156595f39f5d` plus the
Pi 1.0 recipe/schema/profile diff on macOS arm64, Python **3.14.6**, Node
**26.7.0**, npm **11.19.0**. This is preparation-layer evidence, not final
Attro fork/plugin integration or live activation.

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **241 run,
  one skipped**, with process-local `GIT_AUTHOR_NAME=Fixture`,
  `GIT_AUTHOR_EMAIL=fixture@example.invalid`, `GIT_COMMITTER_NAME=Fixture`, and
  `GIT_COMMITTER_EMAIL=fixture@example.invalid`. Without that fixture identity,
  the first run failed only the merge-check test because the host has no Git
  committer identity. No Git configuration was changed.
- Schema-6 acceptance was observed failing before the extractor change.
  Coverage retains schema 3, rejects unknown/malformed schemas and incorrect
  archive/per-file hashes, and exercises schema-6 traversal, links, duplicates,
  nested entries, and expansion/per-file limits without writing a target.
- After extending existing profile assertions,
  `python3 -m unittest discover -s tests -p 'test_profile_boundary.py' -v`:
  **12 passed**. Fresh seeding keeps additive native tools in `on` mode;
  subsequent initialization preserves personal tools, codemode mode, and theme.
- A disposable copy of the verified **upstream** 1.0.0 archive passed the root
  workspace/lock validator, `npm ci --ignore-scripts --no-audit --no-fund`, the
  updated `apply_model_snapshot`, `node packages/ai/scripts/check-model-data.ts`,
  and `npm run build:offline`. Build HOME and npm config were isolated; install
  scripts were disabled. The committed lock bytes did not change. The build
  used the local hash-verified archive, not live catalog hydration; dependency
  installation used the network. The build was not OS-network-sandboxed.
- Post-build workspace/symlink and runtime validation passed (**3,654 hashed
  source/runtime files**); the compiled CLI returned **1.0.0**. A credential-free
  `CodemodeSandbox` probe using the emitted bundled codemode worker and locked
  QuickJS WASM completed a synthetic tool call and returned **42**.
- `git diff --check`: passed. `python3 scripts/verify.py` remains **pending**:
  the parallel core/Lens migration was not yet pinned and clean at this check.

The unchanged source-build recipe accommodates the new workspaces and worker
paths. Final fork pins, independent review, clean managed preparation, native
MCP/tool discovery, full plugin/UI smoke checks, and actual activation remain
separate gates. No live settings, launchers, original checkout, or release state
were changed by these checks. An old manager can read the unchanged schema-1
release manifest, but its schema-3-only extractor cannot prepare this new recipe.

## First-four performance candidate (2026-09-26)

Tested source **`e2d71639a950bb35e093fc140b9bf032083d1faa`**, with core
`cd81d9ad`, Lens `fbf7aa3e`, subagents `f2d78013`, and unchanged RPIV `1a1d7818`.
A clean local-object clone prepared **`attro-0.2.0-35cda96e2569`** in disposable
HOME/state on macOS arm64, Node **26.7.0**, Python **3.14.6**. Neither the live
release nor personal configuration was activated or rewritten; commits remain
local. This record does not certify publication or authenticated provider use.

- Clean-clone `python3 scripts/verify.py` and `git diff --check`: **passed**.
  `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **239 run, one skipped**.
  The original checkout retains the unrelated pre-existing core changelog edit;
  that edit was excluded from commits and the clean verification clone.
- Core required `npm run check` and **75 focused RPC/session tests** passed.
  Faux-provider wire captures reproduced both oversized lifecycle aggregates;
  opt-in child projection reduced the observed `turn_end` / `agent_end` records
  from about 1.2 MB each to **19 / 38 bytes**, without truncating tool results.
- Subagents: **483 assertions and 30 concurrency checks passed**. Independent
  sensitive reviews cleared transport settlement, retained process ownership,
  cancellation, and warm-retirement protections. Concurrency remains four;
  the warm-idle default is now 30 seconds, with explicit overrides preserved.
- Lens build, strict lint, offline distribution build, changelog checks, and
  **five compiled MCP smoke tests** passed. The full suite passed **8,872 tests,
  49 skipped** across **727 passing / 11 skipped files**. Baseline platform,
  mock-asset, state-count and async-fixture failures were repaired separately.
  Red-first and mutation checks cover cold-index publication races; independent
  sensitive review cleared the optimistic source/snapshot publication fence.
- RPIV: **380 focused tests across 29 files**, type and non-writing format
  checks passed. The packaged todo/config/i18n files match their pinned source;
  the external closure is locked `typebox@1.3.6`. Artifact mutation/symlink
  checks and the new preparation branch regression passed; provenance/path
  review found no blockers.
- Actual candidate preparation and post-startup `doctor` passed. The updated
  manager also validated the retained Cursor-bearing control release. New
  releases omit Cursor, but historical manifests and personal data remain intact.
- Compiled CLI **100×30 PTY** startup and `/quit` exited **0** without forced
  cleanup. All seven managed plugins loaded. Synthetic-provider RPC checks
  exercised todo dependencies/state transitions, saved-session replay, German
  localization, default/compact event shapes, and real managed children.
  Final Node-26.7 probes completed **one and four children**, retaining the pinned
  binary, resource envelope, child markers and restricted tool lists. A real
  requested TypeScript `documentSymbol` returned `greet`; the initial empty
  result was traced to the fixture's missing discoverable TypeScript install.
  The earlier todo/replay/two-child probes used Node **26.5.0** and are separate
  evidence. All fixture-owned parent/child PIDs were gone after cleanup.

Five interleaved, credential-free control/candidate pairs per mode used the same
Node 26.7 runtime. The control was prepared from `c8ccf8c` and the candidate from
`e2d7163`. Network-denied direct-CLI `--help` medians were **2.452 → 1.937 s**;
RPC `get_state` readiness was **2.543 → 1.886 s**. Help peak RSS medians were
**468.4 → 449.9 MiB**. These are not model first-token or full managed-launch
measurements. Read-only manager validation separately became **0.200 → 0.367 s**
(median of five pairs), reflecting the added 1,420-file RPIV integrity inventory.
That cost is not hidden in the direct-CLI improvement claim.

Allocated release size after the probes was **2,288,796 → 1,462,344 KiB**
(about **2.18 → 1.39 GiB**); RPIV alone was **792,256 → 6,572 KiB**. Allocation
is not compressed download size or uniquely reclaimable physical space.
Five faux-child retention comparisons at simulated 31-second idle age retired
four children under the new window versus none under 120 seconds, trading
roughly **210 ms median cold continuation overhead** for lower residency in that
fixture. These figures are not live-provider or full-tree RAM guarantees.

The semantic probe's first exploratory run unexpectedly made an npm registry
request. The final positive LSP run disabled installs and used npm offline mode;
its npm logs show no HTTP fetch, but it did not have an OS network firewall.
Only the startup benchmarks and PTY probes claim OS-level network denial.
No live provider API calls or credential copies were part of these probes.
Linux/WSL2, another machine, authenticated tasks, and live activation remain
unverified. The candidate is prepared and locally verified, not installed as
this user's active release or published.

## Public-readiness baseline (2026-09-26)

Historical sections below describe their recorded revisions, not current
publication status. This checkpoint supersedes earlier claims that no clean
local source install or subagent resource-inheritance check has been performed;
it does **not** establish anonymous installation or cross-platform readiness.

Tested root **`c9c44b53df65074c295d236b2325ea2bfe17e1b8`**, core
**`4415a11b053a614f8918be58b56cba5b92779ffb`**, on macOS **26.3.1(a) arm64**,
Python **3.14.6**, Node **26.7.0**, npm **11.19.0**. A clean recursive checkout
used local Git objects for private pins. Every build/launch used a disposable
HOME, managed root, working directory, and an explicit `env -i` environment.
No personal credentials, model prompts, or live activation were involved.

- Pyright language-server diagnostics for the installer and 18 manager modules:
  **zero findings** before installation.
- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **237 run, one
  skipped** (the opt-in real Cursor SDK smoke). Separately, the same suite passed
  from a root-only archive without submodules, validating the revised offline
  CI checkout topology. Test processes do not inherit an explicit `ATTRO_HOME`;
  fixtures choose their own isolated managed roots.
- `python3 scripts/verify.py` and `git diff --check`: **passed**.
- Real `./install --bin-dir <temporary-bin>`: **passed**, including locked
  downloads, core/Lens builds, model-data hydration, SDK patching, activation,
  and creation of only the `attro` launcher. Core `--version` returned **0.87.1**;
  manager/core help and `attro --json doctor --repo <clean-source>` passed,
  with no doctor issues or warnings.
- Real **100×30 PTY** startup: explicitly continued without an unavailable
  authenticated effort profile, reached the UI, and `/quit` exited **0** without
  forced cleanup. Auth/model stores remained `{}`. The session had no user or
  assistant messages; shipped settings gained only normal changelog metadata.
- `node plugins/pi-subagents/subagents.test.cjs`, using the newly built pinned
  core via the suite's `PI_ROOT`/`ATTRO_CORE` host overrides: **456 checks, ALL
  PASS**. Includes managed resource-envelope rejection, pinned child binaries,
  recursive resource inheritance, and synthetic real-RPC readiness. This is not
  a model-driven nested provider task.
- Official Node **22.22.3** downloaded into the disposable directory and checked
  against its published SHA-256: retained core version/help and doctor **passed**.
  This is runtime evidence for the Node-26-built release, not a Node-22 rebuild
  or an exact **22.19.0** minimum-floor test. The host's unrelated Homebrew
  Node22 had a missing shared library; it was not repaired or used as evidence.

The baseline exposed misleading missing-profile-file guidance and an upstream
`pi` exit-resume hint in managed mode; subsequent fixes require their own focused
verification. No provider authentication or routing behavior was changed during
this baseline run.

Readiness documentation and issue forms passed local-link, YAML/structure,
whitespace, and LSP checks. The new tagged-bootstrap workflow passed YAML,
`bash -n`, ShellCheck, invalid-tag rejection, and independent read-only review.
Its pinned setup-node v4 has dependency caching explicitly disabled; an analyzer
cache-poisoning warning was independently confirmed as a false positive against
the exact action source. The workflow has **not** executed on GitHub.

**Remaining:** authenticated turns, a model-driven nested task, real multi-version
profile continuity/rollback, Linux/WSL2, another machine, anonymous recursive
retrieval, tagged bootstrap delivery, and publication/privacy/license gates.
The root is already public; required forks remain private and retained root
objects remain accessible. See [publication status](publication.md). Private
vulnerability reporting was enabled and confirmed through GitHub's API. No source
push, tag, release, fork visibility change, or website deployment was performed.

## First-run guidance correction

Core **`63067e54c9500c1dd1172474d0836c7e2bf7e960`** changes only presentation:
the unavailable-profile dialog now explains `/login`, `/model`, and `/profile`,
and only conditionally advises correcting an invalid profile file. Managed
session exit hints use `attro`; standalone Pi retains its existing name.
Authentication, explicit continuation, model selection, and profile persistence
control flow are unchanged.

On Node **26.7.0**, with an isolated HOME/agent directory and no credentials:

- Existing resume-command regression coverage failed before the fix, then
  passed for canonical/legacy managed markers, precedence, and unmanaged use.
- `node ../../node_modules/vitest/dist/cli.js --run
  test/format-resume-command.test.ts test/effort-profiles.test.ts
  test/interactive-mode-startup-input.test.ts` from the coding-agent package:
  **51 passed**.
- TypeScript server syntactic/semantic diagnostics: **zero findings**.
- Required root `npm run check`: **passed**, including formatting, dependency,
  import, entry, shrinkwrap, installation-lock, type, and browser checks; no
  automatic fixes were made.
- Real source CLI **100×30 PTY**: updated guidance rendered, explicit Continue
  retained, `/quit` exited **0**, and the resume hint used `attro --session`.
  No provider prompt was sent and no effort-profile file was created.

These results cover the committed source correction, not a published installer.

### Updated managed release on Node 22

A clean recursive **local-object** clone of root
**`0a1575c185cf417da4f6dd871368efdede3e63a0`**, including core `63067e5`, passed
`python3 scripts/verify.py`. Its source remained clean after testing. On the same
macOS arm64 host, the official checksummed **Node 22.22.3 / npm 10.9.8** runtime
prepared release **`attro-0.2.0-ac2feafc4f20`** through the actual manager's
`update --repo <clean-source>` command. The prepared provenance confirms those
build versions and root revision. This closes the local Node-22 build gap for
that version, not the exact 22.19.0 minimum floor.

In an explicit credential-free environment and disposable managed root:

1. Started a real PTY session on baseline release `attro-0.2.0-cdff6862ba8d` and
   explicitly continued without a profile; kept it running during preparation.
2. Prepared and activated the updated release. The old running session's code
   remained registered; candidate `doctor --repo <clean-source>` was healthy
   with no issues or warnings.
3. Started the updated release in another **100×30 PTY**. Verified the rendered
   login/model/profile guidance and `attro --session` exit hint; `/quit` exited
   **0**. No extension module-load errors were found.
4. Verified settings, empty auth, and a synthetic profile continuity marker
   remained byte-identical across activation. `rollback` returned to the retained
   baseline release while its session was still running, and those bytes remained
   unchanged. The baseline session then also exited **0**, without forced cleanup.
5. Audited the disposable profile: auth remained `{}` and session files contained
   **zero conversation messages**. No provider prompt or live activation occurred.

These are real local build, activation, concurrent-session retention, and
retained-code rollback checks—not a guarantee of rollback after pruning, a data
migration test, a provider login, or anonymous delivery. No production storage
or concurrency implementation changed. Public macOS/Linux bootstrap, Linux/WSL2,
authenticated/model-driven tasks, and publication clearance remain unverified.

## Pi 0.87.1 local candidate

Tested on macOS arm64: root baseline
`79e4c6676ee48d0b428e907e8344736719fb7ed5`, core baseline
`e7c1886b8b0831629699e7f10337f8380ac65a8d`, plus the 0.87.1 integration,
Cursor adapter update, and model-refresh launcher fix. The tested core is now
committed as `65885dbf60293ae5b2982bb12f8bbc1e78c125ea`; committing did not
change its tested contents. The subsequently approved effort-profile defaults
are committed in final core pin `cce2c9d6fe2b7b9e3e58f7cef77e2aa73b5c6e27`.
`npm run check` (Node 22.23.2) and full isolated `./test.sh` (Node 26.7.0) passed
again for that pin. The new built-in Light/Balanced/Deep presets use GPT-6 via
Codex; existing personal catalogs are neither overwritten nor migrated.
Source archive identity and recipe pins are recorded in
[core provenance](core-provenance.md#pi-0871-integration).

- Core `npm ci --ignore-scripts --no-audit --no-fund`: passed on Node **22.23.2**.
  No dependency lifecycle scripts ran. Upstream's example-only Gondolin Node
  requirement and eval-only autoevals package-manager requirement emitted engine
  warnings. Undici **8.10.2** release notes were reviewed; proxy/HTTP tests passed.
- Core `npm run check`: passed, including formatting, dependency declarations,
  pinned versions, import/entry graphs, shrinkwrap/install-lock checks, types,
  and browser smoke.
- Core `npm run build:offline`: passed on Node **22.23.2** with an isolated HOME
  and no provider credentials. Generated provider data validated against the
  verified 0.87.1 archive. Built CLI `--version` returned **0.87.1**.
- Core `./test.sh`: passed on Node **26.7.0**. The runner removes credentials and
  isolates HOME, config, and temporary files; live-provider suites were skipped.
  Coding-agent reported **2,703 passed / 50 skipped**. TUI separately passed
  **994 / one skipped** on Node 22.23.2.
- Node **22.23.2** full-suite limitation: Chord's 100,000-argument append test
  exceeds its call stack. The same test failed in pristine 0.85.0 source with
  the current test dependencies, and passed on Node 26.5.0 and 26.7.0. Imported
  Chord code was not changed to hide this pre-existing runtime limit.
- Root `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **237 run,
  one skipped**. The launcher exception accepts only exact `update --models`;
  mixed core/package flags remain refused. Guard and child-argv regressions were
  observed red before the fix and green afterward.
- Isolated built-SDK resource loading registered all **eight external extensions**
  and the Cursor provider without errors. This verifies loading, not authenticated
  provider turns or nested-agent execution. The two installed Cursor SDK bundle
  hashes still match the existing **1.0.27** attribution-off patch's input hashes.
- Native managed-style TUI startup rendered in isolated tmux at **100 and 40
  columns**; keyboard opening/closing of `/settings` and `/quit` worked. No
  provider prompt was sent. An initial temporary profile fixture omitted its
  required `cycle` field; the expected fail-closed dialog appeared, and the
  fixture was corrected without changing profile validation.
- Independent Astra review found cache warming surviving cancellation until
  settlement. The correction cancels scheduled and in-flight warming immediately,
  ignores late completions, and allows deliberate later requests to restart it.
  Both new public-session regressions failed before the fix; **32 focused tests**
  then passed. Narrow re-review cleared the finding with no new blockers.
- Root and core `git diff --check`: passed. No commits, pushes, live profile
  changes, or activation were performed.

The user subsequently authorized local commits, installation, and activation.
The recipe now advances its core pin and matching archive fields together to
0.87.1. The checks above precede managed preparation/activation and do not alone
certify a retained release. Authenticated turns, full managed-plugin session
lifecycle, Linux/Windows, and fresh-machine installation remain unverified.

## Fork maintenance cutover (local)

Tested recipe **`8c10f9240a11780c9c656289548e36fe5f4b79c9`**, core
**`e7c1886b8b0831629699e7f10337f8380ac65a8d`**, on macOS. This evidence
precedes this documentation-only record; executable inputs are unchanged.
The recipe has four submodules (core, Lens, rpiv, subagents) and five pinned
npm packages. Web-access and ask-user use upstream npm; selected Zentui and CC
surfaces are first-party core code.

- Clean pinned source verification and `git submodule status`: passed. Local Git
  objects supplied unpublished commits; anonymous remote retrieval was not tested.
- Root `python3 -m unittest discover -s tests -p 'test_*.py'`: **221 run, one
  skipped**. The final run used Python **3.11.15**, with Python **3.14.6** first
  on PATH for bootstrap subprocesses. An earlier PATH preferring macOS Python
  3.9 correctly failed the bootstrap's Python 3.10+ prerequisite; correcting PATH
  passed without changing source.
- Core `npm run check`: passed on Node **22.23.2**, including typechecking,
  dependency/import checks, entry budgets, lock checks, and browser smoke.
  **20 focused suites / 199 tests passed** after formatting. The preceding native
  composer cutover passed 103 focused tests. Primary LSP checks confirmed clean
  results on the changed runtime and root validation seams.
- Independent reviews cleared corrections to narrow OSC framing, asynchronous
  Git invalidation, custom renderer ownership/exclusions, write metadata, and
  referenced-session loading/context ordering. Reference reads do not repair or
  migrate files on disk; orphaned references are omitted from provider context
  after compaction. Delimiters are guidance, not an injection sandbox.
- Actual `attro setup --repo <clean-source>` in a disposable home/state root
  installed locked dependencies, built core and Lens, hydrated pinned model data,
  and applied the pinned Cursor SDK patch. Candidate
  **`attro-0.2.0-552ea05bdede`** records build Node **26.5.0**; runtime checks used
  Node **22.23.2**. `try --release-id <candidate> -- --version` returned **0.85.0**;
  `doctor --repo <clean-source>` reported **OK**. The disposable state remained
  **`active: null`** throughout.
- Full managed-plugin interactive startup/restored transcripts were rendered at
  40 and 80 columns. `/context`, `/model`, `/reload`, and tool expansion worked
  without loader errors. Native-only synthetic captures additionally exercised
  streaming thinking, rich diffs, and mouse/global thinking expansion.
- Full managed registry snapshots contained **35 unique tools / 38 unique
  commands**, including each web/ask tool, the selected first-party commands,
  Lens, todo, and subagent tools. Runtime prompt discovery included **ask-user
  exactly once**. Counts remained stable after `/reload`; `cc-dark` and `cc-light`
  resolved through the theme API. No retired UI plugin paths were loaded.
- Credential-free synthetic providers completed both print and interactive turns
  with the full managed plugin set. Persisted tool results showed successful
  **read → write → edit**, and the expected final file mutation was checked.
  A deliberately empty effort-profile catalog was written only to disposable
  test profiles. Without it, the unauthenticated default profile correctly refused
  startup. Product authentication/profile policy was not relaxed.
- Tests launched under `env -i` to avoid inheriting a verification subagent's
  incarnation metadata. No live credentials were copied, no real provider or web
  query was made, and no live release was activated or published.

Linux/WSL, authenticated provider turns (including Cursor), real model-driven
nested agents, binary archive execution, and public publication remain outside
this local evidence. Existing personal extensions were not rewritten. The
unrelated dirty subagents worktree was excluded by verifying its committed pin
in a clean clone.

## Private publication candidate (2026-09-17)

Candidate `2f771c92462ddc43e5abe90f622bdf971fd22421`, before subsequent
CI-only/documentation corrections, was checked on macOS with Node **26.7.0** and
Python **3.14.6**:

- `python3 scripts/verify.py`: passed against clean, rewritten submodule pins.
- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **209 run,
  one skipped** (208 passed).
- `python3 -m unittest tests.test_install -v`: **33 passed**. Bootstrap regressions
  for relative paths with `CDPATH`, tilde/space handling, and unsafe resume advice
  were observed RED before correction and GREEN afterward.
- Primary diagnostics for the bootstrap, installer tests, source verifier, and
  CI workflow: no findings. Shell syntax and `git diff --check`: passed.
- A real `./install --bin-dir ...` under `env -i` with isolated `HOME` and
  `ATTRO_HOME` downloaded dependencies, built core/plugins, and activated a release.
  No live user configuration or credentials were supplied.
- `attro exec -- --version`: **0.85.0**; `attro doctor --repo ...`: **OK**.
- Interactive PTY startup reached the authentication-dependent effort-profile
  prompt. Explicitly continuing without a profile reached the UI; `/quit` exited
  **0**. Startup created an empty `auth.json` object, not credentials. A prior
  bounded attempt stopped at that prompt and required forced cleanup.

The existing histories were sanitized in isolated copies: **137 of 14,268**
commits changed; **3,162** unchanged signed commits retained their original
identities. Historical source pins were mapped, with five pre-existing lock/gitlink
mismatches in three old root commits preserved rather than silently repaired.
The current candidate's pins are consistent. All **35** historical secret-scanner
findings were independently classified as synthetic fixtures, public OAuth client
constants, or other non-credential literals; they were not changed to silence
the scanner. The candidate root history and added files had no scanner findings.

**Publication remains blocked:** repositories stay private pending GitHub-retained
commit/PR-cache cleanup and the old CI-log audit/removal decision. Linux, WSL2,
anonymous recursive retrieval, the actual tagged bootstrap, authenticated provider
use, and another-machine validation are not verified by these local checks.
See [publication gates](publication.md). No public tag or stable feed is implied.

## Automatic release retention (2026-09-07)

After comment review, the retention change passed these local checks:

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **197 tests run,
  one skipped** (196 passed).
- `npm exec --offline --yes --package pyright@1.1.408 -- pyright --project pyrightconfig.json`:
  **0 errors, 0 warnings**.
- `python3 scripts/verify.py` and `python3 scripts/verify.py --runtime`: passed.
- `python3 -m py_compile install` and `git diff --check`: passed.

The same isolated public activation probe failed against the pre-change manager
because the old release remained, then passed with automatic retention. Nineteen
focused retention tests cover idle pruning, rollback refusal, staged candidates,
real exec/try lease inheritance and cleanup after exit, a detached env-pinned
process, process-inspection/decoding failure, interrupted deletion/registry saves,
directory-identity changes, symlink confinement, and shared/legacy data protection.
A review-found decoding failure was also reproduced with an actual non-UTF-8
process environment on macOS; the correction retains code with an inspection
warning rather than failing a committed activation. Independent Astra review
confirmed the correction; no other concrete destructive-deletion findings were
reported in the scoped review.
Fixtures use temporary managed roots and synthetic executables; no provider calls
or live release activation are part of these checks.

Linux process inspection and a real interactive PTY session were not exercised
locally. The foreground launch still uses `execvpe`; process scanning for unleased
sessions remains conservative best-effort protection, not a guarantee for arbitrary
processes that hide their release identity.

## Maintained-core verification

The current tree passes **154 Python tests**, the full subagent suite on Node 26, pinned Pyright (**0 errors, 0 warnings**), installer compilation, and whitespace checks. Launcher regressions for help before initialization and `--state-root=PATH` were observed RED before correction and GREEN afterward.

An isolated export of core commit `36b02b695383ad89bc3a22b73633be3fa27be3c1` was augmented only with the hash-pinned v0.85.0 model snapshot. The model-data validator passed, and the dependency lock stayed unchanged through installation and build:

```sh
node packages/ai/scripts/check-model-data.ts
npm ci --ignore-scripts --no-audit --no-fund
npm run build:offline
# From packages/tui:
node --test test/stack-background.test.ts
# From packages/coding-agent:
node ../../node_modules/vitest/vitest.mjs --run test/chat-viewport.test.ts test/scrollbar-theme.test.ts
```

The build and tests ran with macOS sandbox network access denied; downloading the pinned snapshot and installing locked dependencies were separate network-enabled steps. **4 stack tests and 14 viewport/theme tests passed.** The compiled CLI returned `0.85.0` and displayed help from outside the source checkout. The actual Quattro Green theme resolved `dockBg` to `#0e1713` in that build. No credentials or model prompts were used.

### Integrated local installation and startup

A clean local checkout at `1ee0a12a7948c806c48e9fc4e77a7ece263fc7a6` passed the real `./install --bin-dir <temporary-bin>` flow with a temporary HOME and ATTRO_HOME, no inherited credentials, and no global installation. The retained source core recorded Node **26.5.0** and npm **11.17.0**. Preparation and activation took about 131 seconds.

The installed `attro --json doctor` reported healthy; `attro -- --version` returned `0.85.0`; source provenance matched core commit `36b02b6`. Existing `pi` and `piattro` sentinel files in the target bin directory stayed byte-identical. A real `attro try -- --version` also passed while shared settings, auth, and profile-marker bytes stayed unchanged.

The installed app started in a 100-column, 30-row pseudo-terminal and rendered the configured `#0e1713` dock background. Node outbound connections were blocked and no prompt was sent. No extension-loader or subagent process-identity error was present. An earlier OS-sandbox startup probe blocked macOS `/bin/ps`, so the final startup probe used Node network blocking instead; the production process-identity guard was not weakened.

Warnings about unavailable models and Cursor discovery were expected before `/login`. The auth store remained empty, and Quattro Green UI preferences from the prepared release config were preserved. That run predated the personal-bundle boundary; it is not evidence that personal model routing is shipped or seeded today. Authenticated turns, actual model-driven child tasks, cross-version real rollback, and fresh-machine/anonymous clone tests remain unverified.

## Attro rename verification

After comment cleanup, the renamed tree passed all **125 Python tests**, the full Node 26 subagent suite, pinned Pyright (**0 errors, 0 warnings**), installer compilation, and whitespace checks. `bin/attro --help` and the legacy `bin/piattro --help` produce identical output. The canonical-only `ATTRO_HOME` installer export case was observed failing before correction and passes now. New child-namespace tests were also observed RED before implementation and GREEN afterward.

Independent Fable review found no blocking state-compatibility or child-namespace defects. A private source snapshot passed Gitleaks 8.30.1 with zero findings. The original eight GitHub repositories were renamed with stable repository IDs and private visibility; the user's `ernestjsf/attro-core` was subsequently added as a ninth private source repository. For the rename, local checkout paths, upstream identities, and branch history were preserved. This does not close the fresh-install, source-core build, or publication gates below.

## Everyday launcher verification (partial)

New public-seam tests in `tests/test_attro_launcher.py` cover:

- `attro` with no args launches the active Pi binary
- standard Pi flag and prompt forwarding
- management subcommands (`status`, `doctor`, `exec --dry-run`) still work
- `attro -- doctor` routes to Pi chat instead of the manager
- option values such as `-p setup` are not treated as management commands

The latest local suite size reported for this launcher work is **131 Python tests**
(before the later source-core and launcher regression additions). That count is historical to the launcher
milestone; later source-core build and unauthenticated UI startup evidence is
recorded above. Authenticated and fresh-machine checks are still pending.

## Pre-rename v0.2 local checkpoint

After comment cleanup:

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **119 passed**.
- `npm exec --offline --yes --package pyright@1.1.408 -- pyright --project pyrightconfig.json`: **0 errors, 0 warnings**.
- `node plugins/pi-subagents/subagents.test.cjs` on Node 26.7.0: **ALL PASS**.
- `python3 -m py_compile install` and `git diff --check`: passed.
- An isolated public-spawn probe failed against subagent baseline `0682f10` and passed against the current code for resource inheritance, missing-envelope rejection, and out-of-release binary rejection. No credentials or model prompts were used.
- A private snapshot of 107 root source files passed Gitleaks 8.30.1 with zero findings. This is not a final all-ref publication scan.
- Independent Fable review found **no blocking defects** in shared state, installer failure handling, or child resource/core pinning. It independently reran all 119 Python tests. A pre-set `PI_SUBAGENT_COMMAND` or `PI_SUBAGENT_EXECUTABLE` remains an explicit test-hook override; production shells should leave these unset.

At that checkpoint, clean v0.2 installation, source-core build, combined UI,
and publication checks remained. Subsequent local evidence is recorded above;
publication is still outside the verified checkpoint.

Host reference: Python 3.14.6, Node 26.7.0, npm 11.19.0.

## Automated checks (v0.1-era baseline)

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
npm exec --yes --package pyright@1.1.408 -- pyright --project pyrightconfig.json
git diff --check
```

Historical results (2026-09-05, pre–shared-profile milestone):

- **67 unit tests passed** after comment cleanup and final preparation-branch
  coverage changes.
- Fresh Pyright: **0 errors, 0 warnings** on the then-current tree.
- Whitespace checks passed.

That 119-test suite included installer, profile-boundary checks, runtime-lock
validation, and shared-profile lifecycle coverage. The compact-JSON lock
regression was observed failing before correction and passes now.

Coverage in the v0.1-era suite included committed snapshot export, dirty-root
refusal, final paths, scoped npm pins, package-lock preservation/mutation, Lens
generated artifacts, failed preparation, interrupted pointer replacement,
cross-process lock contention, retained-release rollback without source
availability, state/path escapes, credential aliases, trial configuration
isolation, and wrapper flag forwarding/symlinks. Fixtures do not call model
providers.

## Installer checks (v0.2, local)

The `./install` script and `tests/test_install.py` cover:

- doctor/setup/activate orchestration
- **attro-only** launcher symlink creation with conflict refusal
- partial rollback on activation failure
- bin-directory install lock (O_NOFOLLOW, flock)
- custom `ATTRO_HOME` handling

**17 installer tests passed** in the latest local run documented in the
continuation checkpoint. This does not prove anonymous clone, source-core build,
combined TUI, or production PATH adoption.

## Real clean-checkout preparation (v0.1-era)

A temporary clone of root commit `172bb3484921638b73bb8bd5f3cad7a823aeb75d`
was populated with exact committed submodule pins. It does **not** prove public
or anonymous source accessibility and predates shared-v1 layout, source-core
build, and `./install`.

With `WORK` identifying that temporary directory and `RELEASE_ID` the ID printed
by setup, these commands passed. Historical command names are preserved because
that immutable commit predates the Attro rename:

```sh
(cd "$WORK/source" && python3 scripts/verify.py)
"$WORK/source/bin/piattro" --json --state-root "$WORK/state" setup --repo "$WORK/source"
"$WORK/source/bin/piattro" --state-root "$WORK/state" activate "$RELEASE_ID"
PIATTRO_HOME="$WORK/state" "$WORK/source/bin/pi" --version
"$WORK/source/bin/piattro" --state-root "$WORK/state" try -- --version
"$WORK/source/bin/piattro" --json --state-root "$WORK/state" doctor
```

Results:

- Source verifier passed before preparation; Lens generated artifacts were
  correctly absent from the pristine source checkout.
- Real dependency installation completed for locked source trees, pinned npm
  plugins, and upstream Pi **0.85.0** (legacy npm-core path on that commit).
- Both launch paths printed **0.85.0**. Doctor reported healthy.
- Retained core launched after renaming the source checkout away.

Shared-v1 preparation now builds core from pinned `plugins/attro-core` and uses
a canonical `~/.attro/agent` profile. **Repeat fresh-install verification**
with `./install`, source-core build, and shared-profile continuity before
claiming v0.2 readiness.

## Ast-grep runtime warning

The prepared Lens `node_modules/.bin/ast-grep` may warn that postinstall was
skipped and a runtime binary fallback is used. This is expected under
`--ignore-scripts`. This checks raw CLI output, not every Lens tool consumer.

## Independent review and remaining gates

A read-only Fable review found **no blocking safety defects** in activation,
path containment, snapshotting, and credential isolation for the v0.1 scope.
Its non-blocking whitespace-range issue was fixed and missing npm-ci/Lens fixture
coverage was added.

**Not verified (including v0.2 gaps):**

- Source-core build and launch from a clean recursive clone
- Provider login and authenticated model turns in the installed interactive app
- Shared-profile continuity across update and rollback on a real install
- Real nested subagent loader startup (the isolated spawn seam is verified)
- Linux execution, GitHub-hosted workflow execution, second physical machine
- Public source/history safety and anonymous recursive clone
- Stable release delivery and consumer update feed
- Full transitive dependency/SBOM clearance of installed artifacts

RPIV environment isolation received independent confirmation in a controlled
ambient-root test run (263 files, 5185 tests pass; sentinel files unchanged).
That validates RPIV config routing, not full Attro publication readiness.

No public repositories, tags, or artifacts were pushed. No live Pi registration,
PATH, global package, or `~/.pi/agent` migration was performed as part of these
checks.

## Publication audit status

Preliminary secret scans and fixture classification exist from earlier audit
work; the **final committed publication candidate and full branch/tag histories
have not yet been scanned and approved**. Earlier commits may still contain
personal bundles removed from the current tree. Do not mark publication gates
complete or claim old branches are safe to publish from this document alone.
See [publication](publication.md).
