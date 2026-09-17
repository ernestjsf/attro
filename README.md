# Attro

An opinionated distribution of Pi: a source-built Pi core, customized plugins,
and an isolated release manager. Use **`attro`** as the everyday launcher; it forwards standard Pi flags and prompts to the active release. Use
`attro` management subcommands to prepare, activate, update, and roll back
pinned releases. Customizations live in plugins and the distribution profile;
Pi core is built from the maintained `attro-core` fork, not edited in place.

**Preview release:** Attro **0.2.0** is a source-built distribution, not a
certified stable release. There is no automatic stable update feed. See
[verification evidence](docs/verification.md) for tested platforms and remaining
limits, and [publication gates](docs/publication.md) for history sanitization.

## Install

Requires **Git, Python 3.10+, Node 22.19.0+, and npm** on PATH, plus `curl`
for the command below. Supported environments are **macOS, Linux, and Windows
through WSL2**. Native Windows/PowerShell installation is not supported.
Install prerequisites using your preferred package/version manager first; the
installer does not use `sudo` or install system dependencies.

Once the `v0.2.0-preview.1` tag is published:

```sh
curl -fsSL https://raw.githubusercontent.com/ernestjsf/attro/v0.2.0-preview.1/install.sh | sh
```

The script clones the tagged source and pinned forks into `~/.local/share/attro`
and runs the existing installer. Keep that source directory: the launcher uses
it. It refuses an existing source directory rather than overwriting your files.
Downloads and local builds can take several minutes and require network access.
Like any source installer, this executes downloaded code with your user
permissions; inspect `install.sh` and the tagged sources before running it.

On Windows, install WSL2 (for example `wsl --install` from an administrator
PowerShell), finish Linux setup, then run the prerequisites and install command
**inside the WSL terminal**. Use a directory in the Linux filesystem rather than
`/mnt/c` for the checkout and managed state. WSL2 uses the Linux implementation;
Linux CI is not a separate verification of Windows/WSL integration.

### Install from a trusted checkout

Alternatively, start with a clean, **recursive** clone. Review its sources before
executing dependency installation or builds.

```sh
git clone --recurse-submodules https://github.com/ernestjsf/attro.git
cd attro
./install
```

The clone above follows the development branch. For a reproducible preview,
clone with `--branch v0.2.0-preview.1` after that tag is published.

`./install` runs `attro doctor`, prepares a pinned release from this checkout,
activates it, and symlinks **`attro`** into `~/.local/bin` (or `--bin-dir`).
The installer **refuses existing foreign launchers** in the target bin directory
and **does not edit PATH or shell startup files**. It prints the
`export PATH=...` line to add yourself. The installed launcher points at this
checkout's `bin/attro`; **keep the checkout at its current path**. Repository
`bin/pi` and `bin/piattro` compatibility wrappers remain for development but
are **not installed** by `./install`.

Run **`attro`** with no arguments to launch the active Pi app. Standard Pi
flags and prompts are forwarded (`attro -p hello`, `attro --model …`, etc.).
Management commands are explicit subcommands: `doctor`, `update`, `setup`,
`activate`, `rollback`, `try`, `exec`, and `status`. Use `attro -- doctor` to
pass `doctor` to Pi chat instead of the manager.

Provider authentication is **not copied** from `~/.pi/agent`. After install,
run `attro`, then `/login` for the providers you use. Attro seeds the shared
profile once on first activation with **UI and package defaults only**
from `profile/settings.json` and the prepared release config. It **never copies
live login, session history, OAuth tokens, trust state, agent definitions,
model routing, skills, prompts, or other personal configuration** from
`~/.pi/agent`. Later activations, updates, and rollbacks preserve whatever you
establish under the shared profile. See [managed state](profile/MANAGED.md).

If you prefer manual steps or are developing the manager itself, see
[setup](docs/setup.md).

## What Attro ships

Attro **0.2.0** ships the maintained distribution recipe, not a maintainer's
personal Pi setup:

- **Pi core** built from the pinned `plugins/attro-core` source tree
- **Seven customized plugin forks** (Zentui, CC extensions, web access, Lens,
  rpiv todo, ask-user, subagents)
- **Three descriptor npm packages** (`pi-caffeinate`, `pi-btw`, `pi-cursor-sdk`)
- **Shared display defaults** in `config/` (Zentui, CC style, rpiv todo)

**Not bundled:** Quattro custom themes, personal instructions, agent definitions, model/provider and
reasoning preferences, skills, prompt templates, standalone user extensions,
and personal plugin preferences. Those belong in your own `~/.attro/agent`
directory (or other Pi discovery paths you configure). Individual plugins may
ship their own skills and documentation under their source trees; that is
separate from any personal copies you maintain locally.

## Shared profile and releases

Attro **0.2.0** uses one canonical user profile at `~/.attro/agent`
(override with `ATTRO_HOME`; legacy `~/.piattro` is reused when `~/.attro` is
absent). It is initialized **once** on first activation from reviewed UI and
package defaults in `profile/settings.json` plus the prepared release config
(plugin wiring and the three shared UI config files under `config/`). Theme
selection uses upstream Pi defaults on fresh profiles; copy personal theme files
into `~/.attro/agent` or choose a theme interactively. The root checkout still
exports `themes/quattro-*.json` through `package.json` for originalPi use, but
new Attro releases do not copy them or pass `--theme` flags.
Later activations, updates, and rollbacks **preserve** your preferences and
ordinary session history in that directory. Pi still loads personal config/skills
and trusted-project `AGENTS.md` / `.pi` resources at runtime according to
upstream rules.

Each prepared release retains immutable code and managed resource paths
(`releases/<id>/`). Managed plugins are passed to Pi through upstream
CLI resource flags (`-e`, etc.) from the release's prepared settings.
Release-specific environment routing sets `PI_CODING_AGENT_DIR`,
`RPIV_CONFIG_HOME`, and `PI_LENS_CONFIG_PATH`. Releases prepared before the
personal-bundle boundary may still expose `ATTRO_RESOURCE_DIR` pointing at a
retained `profile/resources/` tree; new recipe releases do not ship personal
resource bundles. Update personal configs that still reference the old bundled
path. Attro does not edit files under `~/.attro/agent` when the repository
recipe changes.

**Release contents are not rewritten in place.** Preparing and activating a new
release applies the new recipe. Superseded release code is automatically pruned
when idle; Attro does not delete, re-seed, or rewrite the shared user profile.

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
attro rollback   # only while the previous release is still retained
```

`update` prepares the **explicit checkout's recipe**, not the latest upstream
versions. Attro keeps the active release and one staged update candidate.
Preparing another candidate supersedes the earlier candidate; activation
supersedes other releases. Idle superseded code is automatically deleted.
There is **no guaranteed offline rollback copy**. If the previous release is
still retained, rollback switches binaries while **keeping the shared profile**;
otherwise, prepare the desired recipe again. Rollback does not undo shared plugin
data changes, external side effects, or modifications made by an agent.

Running managed sessions hold release leases. A detached cleanup process retries
pending deletion after sessions exit, without replacing or supervising the Pi
process. It exits when cleanup is finished. Process inspection also conservatively
protects older unleased sessions and detached children; inspection failure retains
code rather than assuming it is unused. This is not a guarantee for arbitrary
processes that hide or discard their release identity. Directly launching retained
binaries bypasses the managed launch/cleanup locking protocol.

Cleanup never sweeps arbitrary directories or deletes `~/.attro/agent`. Legacy
releases with per-release user state are preserved for manual handling. Interrupted
cleanup is retried; a later preparation, activation, or real launch also resumes
pending cleanup if the cleanup process was stopped. Never manually delete releases
while sessions still use them.

[Update automation](docs/automation.md) explains scheduled candidate discovery,
optional disposable fork-merge assessment, and the remaining release-PR lane.
Discovery reports are **not** an automatic consumer release feed.

### Cursor attribution

New releases disable Cursor SDK's default commit and PR attribution through the
versioned `sdkPatches` entry in `attro.json`. Preparation patches only staged
`@cursor/sdk@1.0.27` bundles, checks their original and resulting SHA-256 hashes,
and records patch provenance that is verified when the release is used. An
unrecognized SDK version or bundle fails preparation rather than being patched
blindly; SDK upgrades require a reviewed patch specification.

This changes attribution defaults, not explicit overrides or admin controls.
It does not rewrite existing commits, change original Pi, or modify retained
releases. Prepare and activate a new release to adopt it, then start a fresh
session. Cursor Cloud attribution is not covered.

## Structure

```text
bin/                    attro launcher (everyday + management); pi/piattro compat wrappers (not installed)
install.sh              tagged-source bootstrap for macOS/Linux/WSL2
install                 prepare/activate/attro launcher install
attro/                preparation, validation, activation, and launch code
attro.json            distribution recipe (v0.2.0; source-core install method)
runtime/                committed npm package-lock inputs for descriptor npmPackages
sources.lock.json       canonical eight-submodule pins and copied config hashes
plugins/                eight Git submodules (attro-core + seven customized plugin forks)
profile/                portable UI/package defaults and managed-state guidance
config/                 reviewed shared display defaults copied into releases
themes/                 Quattro theme sources for originalPi; not bundled in new Attro releases
scripts/                source verification and upstream update discovery
tests/                  isolated runtime, installer, and discovery regression tests
.github/workflows/      macOS/Linux tests, real install smoke checks, and update reports
docs/                   setup, maintenance, design, and publication gates
```

The legacy root npm manifest remains private and exports themes only. Install the
whole environment with the manager or `./install`, not `pi install` on that
theme-only package. Original Attro code is [MIT](LICENSE); upstream notices
remain authoritative ([third-party inventory](THIRD_PARTY_NOTICES.md)).

Legacy upstream npm releases of `@earendil-works/pi-coding-agent` remain
readable for comparison; Attro **0.2.0** builds core from the pinned
`plugins/attro-core` source tree instead of installing that npm package directly.

## Developer checks

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/verify.py
python3 scripts/verify.py --runtime
git diff --check
```

The source verifier requires clean, pinned submodules. `--runtime` additionally
checks listed generated-file presence after the documented Lens and attro-core
preparation; it does not certify dependency compatibility, source-core build
success, or the combined interactive UI. Unit tests use isolated fixtures and
do not install or alter the live Pi setup. See [verification evidence](docs/verification.md)
for exact local results and remaining validation gates.
