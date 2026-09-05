# Piattro

An opinionated distribution of Pi: a pinned Pi runtime, customized plugins,
Quattro themes, and an isolated release manager. Use `pi` to work and `piattro`
to manage prepared releases. Pi core remains upstream; customizations live in
plugins and the distribution profile.

**Development status:** local-checkout installation and update discovery are the
first milestone. This repository still references the existing fork mirrors;
it is **not yet a publicly installable, fully validated stable distribution**.
No remote stable feed, automatic release PRs, or public artifacts are published
by the current workflows. See [publication gates](docs/publication.md).

## Try the local manager

Requires Python 3.10+, Git, npm, and a Node version satisfying the pinned Pi
engine (currently Node 22.19.0+). macOS and Linux are the target platforms;
real fresh-install and combined-UI validation are required before support is
advertised. Windows is not supported by this first implementation.

Start with a trusted, clean, recursive checkout whose pinned forks you can
access. Review its sources before executing dependency installation or builds.
The current workbench checkout instructions are in [source setup](docs/setup.md).

```sh
./bin/piattro --help
./bin/piattro doctor
./bin/piattro setup --repo "$PWD"
./bin/piattro status
```

`setup` installs/builds a **separate managed release**; it does not replace your
existing global Pi or activate the candidate by default. It can download npm
packages and Lens grammars and execute the reviewed build steps. Disabled npm
lifecycle scripts do not sandbox those builds or the resulting extensions.

Use the release ID printed by setup:

```sh
./bin/piattro try --release-id <release-id>
./bin/piattro activate <release-id>
./bin/pi
```

Only after validating the candidate, put this checkout's `bin/` directory before
your existing Pi on PATH. This is an explicit shell choice; the installer does
not edit shell startup files or overwrite an existing `pi` command. Keep the
manager checkout available.

```sh
export PATH="/absolute/path/to/piattro/bin:$PATH"
command -v pi
pi
```

Provider authentication and personal settings are not copied from `~/.pi/agent`.
A trial uses temporary Pi state and discards it on exit; it is not a sandbox and
can still access environment credentials, project resources, and host tools.
See [managed state](profile/MANAGED.md) before adopting the setup for daily work.

## Update and rollback

```sh
piattro update --repo /path/to/reviewed-clean-checkout
piattro try --release-id <new-release-id>
piattro activate <new-release-id>
piattro rollback
```

`update` currently prepares the **explicit checkout's recipe**, not the latest
upstream versions. Old prepared code is retained locally; rollback switches the
active pointer. It does not undo shared plugin data changes, external side
effects, or modifications made by an agent. Never delete old releases while
sessions still use them.

[Update automation](docs/automation.md) explains scheduled candidate discovery,
optional disposable fork-merge assessment, and the remaining release-PR lane.

## Structure

```text
bin/                    piattro manager and pi launcher
piattro/                preparation, validation, activation, and launch code
piattro.json            distribution/core/npm version recipe
sources.lock.json       canonical seven-fork pins and copied config hashes
plugins/                seven Git submodules (customized upstream plugins)
profile/                portable defaults and managed-state guidance
config/ + themes/       reviewed display configuration and Quattro themes
scripts/                source verification and upstream update discovery
tests/                  isolated runtime and discovery regression tests
.github/workflows/      macOS/Linux tests and weekly update reports
docs/                   setup, maintenance, design, and publication gates
```

The legacy root npm manifest remains private and exports themes only. Install the
whole environment with the manager, not `pi install` on that theme-only package.
Original Piattro code is [MIT](LICENSE); upstream notices remain authoritative
([third-party inventory](THIRD_PARTY_NOTICES.md)).

## Developer checks

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/verify.py
python3 scripts/verify.py --runtime
git diff --check
```

The source verifier requires clean, pinned submodules. `--runtime` additionally
checks listed generated-file presence after the documented Lens preparation;
it does not certify dependency compatibility or the combined interactive UI.
Unit tests use isolated fixtures and do not install or alter the live Pi setup.
