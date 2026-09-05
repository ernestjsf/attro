# Local milestone verification

Evidence from the initial Piattro implementation on macOS, 2026-09-05.
Host: Python 3.14.6, Node 26.7.0, npm 11.19.0. This is not a public release
certification or evidence of Linux/Windows/second-machine compatibility.

## Automated checks

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
npm exec --yes --package pyright@1.1.408 -- pyright --project pyrightconfig.json
git diff --check
git diff --check b0160f6 HEAD
```

- **67 tests passed** after comment cleanup and the final preparation-branch
  coverage changes.
- Fresh Pyright: **0 errors, 0 warnings**. The long-running editor LSP retained
  stale unresolved-import diagnostics for three newly created modules; those
  were marked false-positive based on this fresh scan, successful runtime
  imports, and the real preparation/launch below. No inline suppressions added.
- Whitespace checks passed. CI now checks the actual event base/head range,
  rather than a clean worktree with no diff.
- The initial hardened lifecycle suite was observed failing (1 failure and 9
  errors) before the runtime fixes, then passing. The Lens build-failure test
  was also observed failing before correcting its stage-specific failure
  injection; it now tests build failure rather than an earlier npm-ci failure.

Coverage includes committed snapshot export, dirty-root refusal, final paths,
scoped npm pins, package-lock preservation/mutation, Lens generated artifacts,
failed preparation, interrupted pointer replacement, cross-process lock
contention, retained-release rollback without source availability, state/path
escapes, credential aliases, trial configuration isolation, and actual wrapper
flag forwarding/symlinks. Fixtures do not call model providers.

## Real clean-checkout preparation

A temporary clone of root commit `172bb3484921638b73bb8bd5f3cad7a823aeb75d`
was populated with the exact committed submodule pins from local object stores.
Only the temporary clones' origin configuration was set to the canonical source
manifest URLs. This exercises real submodule gitfiles without incorporating the
maintainer's concurrent uncommitted subagent edits. It does **not** prove public
or anonymous source accessibility.

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
- Real dependency installation completed for all six locked source trees,
  all four pinned npm plugins, and upstream Pi **0.85.0**.
- Lens `build:dist`, core grammar download, and grammar checks completed in
  staging. The manager checked listed runtime resources and recorded lock hashes.
- Both launch paths printed **0.85.0**. Doctor reported healthy with no issues
  or warnings. The temporary source checkout remained clean.
- Renaming the preparation source checkout out of the way still allowed the
  retained core to launch via the main manager and pass doctor. No reinstall was
  invoked. Two-version rollback itself is covered by isolated lifecycle tests,
  not a second real network installation.

The live workbench source verifier remains blocked by concurrent, unrelated
changes in `plugins/pi-subagents/panel.ts` and `subagents.test.cjs`. Those files
and their gitlink were not modified or committed by this implementation.

## Ast-grep runtime warning

The prepared Lens `node_modules/.bin/ast-grep` was invoked against a temporary
TypeScript file with:

```sh
ast-grep run --pattern 'const $A = $B' --lang typescript --json=compact sample.ts
```

It exited **0** and returned valid JSON containing one match. Its stderr warns
that postinstall was skipped and a runtime binary fallback is used. This is
expected under `--ignore-scripts`; lifecycle execution was not enabled to hide
the warning. This checks raw CLI output, not every Lens tool consumer.

## Independent review and remaining gates

A read-only Fable review found **no blocking safety defects** in activation,
path containment, snapshotting, credential isolation, or CI permissions. Its
non-blocking whitespace-range issue was fixed and missing npm-ci/Lens fixture
coverage was added. The ast-grep warning and documented agent-symlink/state
limitations remain explicit.

Not verified: the combined interactive TUI, provider login, model calls, Linux
execution, GitHub-hosted workflow execution, a second physical machine, public
source/history safety, or stable release delivery. Core/npm transitive locks
are still resolved per preparation. Credentials/history/settings remain
release-specific; no seamless user-state migration is claimed.

No public repositories, tags, or artifacts were pushed. No live Pi registration,
PATH, global package, or `~/.pi/agent` migration was performed. The real installed
candidate exists only in temporary managed state, not as the user's daily Pi.
