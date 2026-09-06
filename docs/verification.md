# Local milestone verification

Evidence from Attro implementation work on macOS. This is **not** a public
release certification or evidence of Linux/Windows/second-machine compatibility.
**Attro 0.2.0** shared-profile, `./install`, everyday `attro` launcher,
source-core build, and subagent resource-inheritance gates are **partially
verified locally**, not certified for publication.

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

Warnings about unavailable models and Cursor discovery were expected before `/login`. The auth store remained empty, and seeded `openai-codex/gpt-6-astra` and Quattro Green preferences were preserved. Authenticated turns, actual model-driven child tasks, cross-version real rollback, and fresh-machine/anonymous clone tests remain unverified.

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

That 119-test suite included installer, profile inventory, runtime-lock
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
have not yet been scanned and approved**. Do not mark publication gates complete
from this document alone. See [publication](publication.md).
