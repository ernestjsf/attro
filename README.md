# Attro

An opinionated distribution of Pi: a pinned Pi runtime, customized plugins,
Quattro themes, and an isolated release manager. Use `pi` to work and `attro`
to manage prepared releases. Pi core remains upstream; customizations live in
plugins and the distribution profile.

**Development status:** Attro **0.2.0** implements a shared-profile portable
distribution with a one-command installer for trusted local checkouts. This
repository is still **private**, **not yet publicly installable**, and **not
fully verified** as a stable release. No remote stable feed, automatic release
PRs, or public artifacts are published by the current workflows. See
[publication gates](docs/publication.md).

## Install from a trusted checkout

Requires Python 3.10+, Git, npm, and Node satisfying the pinned Pi engine
(currently Node **22.19.0+**). macOS and Linux are the target platforms;
real fresh-install and combined-UI validation are required before support is
advertised. Windows is not supported by this first implementation.

Start with a trusted, clean, **recursive** clone whose pinned forks you can
access. Review its sources before executing dependency installation or builds.

```sh
git clone --recurse-submodules https://github.com/ernestjsf/attro.git
cd pi-customizations
./install
```

`./install` runs `attro doctor`, prepares a pinned release from this checkout,
activates it, and symlinks `pi` and `attro` into `~/.local/bin` (or
`--bin-dir`). The installer **refuses existing foreign launchers** in the target
bin directory and **does not edit PATH or shell startup files**. It prints the
`export PATH=...` line to add yourself. Launchers point at this checkout's
`bin/pi` and `bin/attro`; **keep the checkout at its current path**.

Provider authentication is **not copied** from `~/.pi/agent`. After install,
run `pi`, then `/login` for the providers you use. Updates and rollback keep
the same shared profile (preferences, login, and session history). See
[managed state](profile/MANAGED.md).

If you prefer manual steps or are developing the manager itself, see
[setup](docs/setup.md).

## Shared profile and releases

Attro **0.2.0** uses one canonical user profile at `~/.attro/agent`
(override with `ATTRO_HOME`). It is seeded **once** on first activation from
reviewed defaults in the release; later activations, updates, and rollbacks
**preserve** your preferences, provider login, and ordinary session history.

Each prepared release retains immutable code and managed resource paths
(`releases/<id>/`). Managed plugins, skills, prompt templates, and themes are
passed to Pi through upstream CLI resource flags (`-e`, `--skill`, etc.) from
the release's prepared settings. Release-specific environment routing sets
`PI_CODING_AGENT_DIR`, `RPIV_CONFIG_HOME`, `PI_LENS_CONFIG_PATH`, and
`ATTRO_RESOURCE_DIR`.

A trial uses temporary Pi state and discards it on exit; it is not a sandbox and
can still access environment credentials, project resources, and host tools.

Legacy **v0.1** releases used per-release agent directories; they are not
migrated automatically. Prepare a new release from current sources before
activating or launching.

## Update and rollback

After `./install`, put `~/.local/bin` (or your `--bin-dir`) on PATH, then:

```sh
attro update --repo /path/to/reviewed-clean-checkout
attro activate <new-release-id>
attro rollback
```

`update` prepares the **explicit checkout's recipe**, not the latest upstream
versions. Old prepared code is retained locally; rollback switches the active
pointer and returns to the previous release's binaries while **keeping the
shared profile**. It does not undo shared plugin data changes, external side
effects, or modifications made by an agent. Never delete old releases while
sessions still use them.

[Update automation](docs/automation.md) explains scheduled candidate discovery,
optional disposable fork-merge assessment, and the remaining release-PR lane.
Discovery reports are **not** an automatic consumer release feed.

## Structure

```text
bin/                    attro manager and pi launcher wrappers
install                 one-command prepare/activate/launcher install
attro/                preparation, validation, activation, and launch code
attro.json            distribution recipe (v0.2.0, runtime lock inputs)
runtime/                committed core/npm package-lock inputs for npm ci
sources.lock.json       canonical seven-fork pins and copied config hashes
plugins/                seven Git submodules (customized upstream plugins)
profile/                portable defaults, resource bundle, and managed-state guidance
config/ + themes/       reviewed display configuration and Quattro themes
scripts/                source verification and upstream update discovery
tests/                  isolated runtime, installer, and discovery regression tests
.github/workflows/      macOS/Linux tests and weekly update reports
docs/                   setup, maintenance, design, and publication gates
```

The legacy root npm manifest remains private and exports themes only. Install the
whole environment with the manager or `./install`, not `pi install` on that
theme-only package. Original Attro code is [MIT](LICENSE); upstream notices
remain authoritative ([third-party inventory](THIRD_PARTY_NOTICES.md)).

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
See [verification evidence](docs/verification.md) for exact local results and
remaining validation gates.
