# Contributing to Attro

Attro is a source-built **0.2.0 preview**, currently based on Pi **1.0.0**.
The root repository is public, but its four pinned source forks are currently
private. A public clone alone cannot complete recursive setup or installation.
There is no published Attro tag or release yet. See [publication status](docs/publication.md)
and [verification evidence](docs/verification.md) before assuming a build or
platform has been validated.

## Questions, bugs, and proposals

Use [Attro issues](https://github.com/ernestjsf/attro/issues) for Attro setup
questions, reproducible bugs, and focused feature proposals. Search existing
issues first; for a larger change, discuss its scope before implementation.
Identify the source revision or managed release ID, platform, and exact commands;
share a small reproduction rather than full session logs. Remove credentials,
private code, personal paths, and provider/account details.

**Security concerns belong in the [security process](SECURITY.md), not public
bug reports or pull requests.** Support and review are best effort; there is no
promised response time or acceptance guarantee.

Upstream Pi's new-contributor auto-close/approval gate is **not an Attro
contribution requirement**. If submitting a separate upstream contribution,
follow that repository's policies.

## Where changes belong

| Area | Owning repository / source |
| --- | --- |
| Launcher, installer, release manager, recipe, profile defaults, distribution docs | This repository |
| Pi core, native Attro UI, effort profiles | `ernestjsf/attro-core` (`plugins/attro-core`) |
| Lens | `ernestjsf/attro-lens` (`plugins/pi-lens`) |
| Todo runtime | `ernestjsf/attro-rpiv` (`plugins/rpiv-mono/packages/rpiv-todo`) |
| Subagent runtime | `ernestjsf/attro-subagents` (`plugins/pi-subagents`) |
| Descriptor npm packages | Upstream packages pinned by `attro.json` and `runtime/npm` |

Fork changes belong in the owning fork, followed by a root change updating the
gitlink and `sources.lock.json` together. While forks are private, discuss the
proposal in a root issue without assuming access will be granted. Do not replace
canonical fork URLs or edit generated installed releases to submit a fix.

Read the relevant fork's `AGENTS.md`, contributor guidance, and package scripts
before changing it; package checks, lockfile rules, and changelog conventions
are not interchangeable. Retain upstream licenses and attribution; the root
[MIT license](LICENSE) does not replace [third-party notices](THIRD_PARTY_NOTICES.md).

## Local setup and checks

Use [developer setup](docs/setup.md) for prerequisites and source preparation.
Access to all pinned forks is required. Attro builds core from source: neither
installing upstream Pi from npm nor running `pi install` on this root's legacy
theme-only npm package installs the Attro distribution. Review source before
running dependency installation or builds; use a disposable environment without
provider credentials for install testing.

For root executable changes, run from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/verify.py
git diff --check
```

The source verifier requires clean submodules at the recorded pins. After the
core and Lens preparation documented in setup, the optional generated-file
presence check is `python3 scripts/verify.py --runtime`; it is not a runtime or
interactive compatibility test. Follow each affected fork's own required checks
as well. For prose-only changes, check links, formatting, and the diff; no local
build is needed. Required CI checks still apply.

## Pull requests

Target the root `main` branch with a focused change. Explain the problem,
observable behavior, and relevant risks; reference an issue when one exists.
Include exact verification commands, outcomes, revision/environment, and any
checks not run with reasons. Extend existing behavioral coverage for regressions
when practical, and document user-visible changes or limitations.

Do not include auth files, session exports, personal configuration, generated
release trees, or unrelated formatting. Review your diff, including any
AI-assisted changes, before submission. Do not claim a published release,
platform certification, or successful check without evidence.
