# Local milestone verification

Evidence from Piattro implementation work on macOS. This is **not** a public
release certification or evidence of Linux/Windows/second-machine compatibility.
**Piattro 0.2.0** shared-profile, `./install`, and subagent resource-inheritance
gates are **partially verified locally**, not certified for publication.

## Current v0.2 local checkpoint

After comment cleanup:

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **119 passed**.
- `npm exec --offline --yes --package pyright@1.1.408 -- pyright --project pyrightconfig.json`: **0 errors, 0 warnings**.
- `node plugins/pi-subagents/subagents.test.cjs` on Node 26.7.0: **ALL PASS**.
- `python3 -m py_compile install` and `git diff --check`: passed.
- An isolated public-spawn probe failed against subagent baseline `0682f10` and passed against the current code for resource inheritance, missing-envelope rejection, and out-of-release binary rejection. No credentials or model prompts were used.
- A private snapshot of 107 root source files passed Gitleaks 8.30.1 with zero findings. This is not a final all-ref publication scan.
- Independent Fable review found **no blocking defects** in shared state, installer failure handling, or child resource/core pinning. It independently reran all 119 Python tests. A pre-set `PI_SUBAGENT_COMMAND` or `PI_SUBAGENT_EXECUTABLE` remains an explicit test-hook override; production shells should leave these unset.

The remaining work is a real clean v0.2 installation and combined loader/TUI check, followed by final publication verification. No publication is part of this local checkpoint.

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

The current 119-test suite includes installer, profile inventory, runtime-lock
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
- launcher symlink creation with conflict refusal
- partial rollback on activation failure
- bin-directory install lock (O_NOFOLLOW, flock)
- custom `PIATTRO_HOME` handling

**16 installer tests passed** in the latest local run documented in the
continuation checkpoint. This does not prove anonymous clone, combined TUI, or
production PATH adoption.

## Real clean-checkout preparation (v0.1-era)

A temporary clone of root commit `172bb3484921638b73bb8bd5f3cad7a823aeb75d`
was populated with exact committed submodule pins. It does **not** prove public
or anonymous source accessibility and predates shared-v1 layout and `./install`.

With `WORK` identifying that temporary directory and `RELEASE_ID` the ID printed
by setup, these commands passed:

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
  plugins, and upstream Pi **0.85.0**.
- Both launch paths printed **0.85.0**. Doctor reported healthy.
- Retained core launched after renaming the source checkout away.

Shared-v1 preparation uses committed `runtime/core` and `runtime/npm` lock
inputs and a canonical `~/.piattro/agent` profile. **Repeat fresh-install
verification** with `./install` and shared-profile continuity before claiming
v0.2 readiness.

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

- Combined interactive TUI and provider login on a fresh `./install`
- Shared-profile continuity across update and rollback on a real install
- Real nested subagent loader startup (the isolated spawn seam is verified)
- Linux execution, GitHub-hosted workflow execution, second physical machine
- Public source/history safety and anonymous recursive clone
- Stable release delivery and consumer update feed
- Full transitive dependency/SBOM clearance of installed artifacts

RPIV environment isolation received independent confirmation in a controlled
ambient-root test run (263 files, 5185 tests pass; sentinel files unchanged).
That validates RPIV config routing, not full Piattro publication readiness.

No public repositories, tags, or artifacts were pushed. No live Pi registration,
PATH, global package, or `~/.pi/agent` migration was performed as part of these
checks.

## Publication audit status

Preliminary secret scans and fixture classification exist from earlier audit
work; the **final committed publication candidate and full branch/tag histories
have not yet been scanned and approved**. Do not mark publication gates complete
from this document alone. See [publication](publication.md).
