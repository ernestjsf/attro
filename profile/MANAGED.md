# Attro managed mode

Attro **0.2.0** (`agentMode: shared-v1`) uses one canonical user profile and
immutable per-release code/resources. Prepare only from an **explicitly trusted,
clean local checkout**:

```sh
./install                                      # prepare, activate, install attro launcher
bin/attro setup --repo /path/to/checkout       # manual prepare
bin/attro update --repo /path/to/checkout
bin/attro activate RELEASE_ID
bin/attro rollback
bin/attro status
bin/attro doctor
bin/attro try -- --version
bin/attro exec -- --version
```

**Everyday launch:** run `bin/attro` with no arguments to start the active Pi
app. Standard Pi flags and prompts are forwarded. Repository `bin/pi` and
`bin/piattro` compatibility wrappers remain for development; `./install` symlinks
only `attro` into the target bin directory.

The installed launcher resolves to this checkout's `bin/attro`; keep the checkout
available. Prepared Pi releases do not need their original source checkout to
launch or roll back. `doctor --repo PATH` additionally checks source inputs;
plain `doctor` only checks retained releases and host Node compatibility.
Use `attro -- doctor` to pass `doctor` to Pi chat instead of the manager.

Global `--state-root PATH` (or `ATTRO_HOME` / legacy `PIATTRO_HOME`) selects the managed directory,
defaulting to `~/.attro` (reusing existing `~/.piattro` when `~/.attro` is absent). Export the same value in every shell that runs `attro`. Attro refuses
managed roots overlapping live `~/.pi`, its manager checkout, the setup source
checkout, or a Git working tree. This is a refusal guard, not an OS security
boundary.

Global `--json` emits one JSON document for manager commands, including failures.
For `try` and `exec`, it is available only with `--dry-run`; actual Pi output is
passed through. Put Pi flags after `--` when using these subcommands or when
escaping a reserved management word (for example `attro -- doctor`).

## Shared profile (`~/.attro/agent`)

On first activation of a shared-profile release, Attro initializes
`~/.attro/agent` once from reviewed **UI and package defaults** in
`profile/settings.json` and the prepared release config (plugin wiring and the
shared UI files copied from `config/`). Theme selection uses upstream Pi defaults
on fresh profiles until you add personal theme files. Subsequent activations, updates,
and rollbacks **preserve** preferences, provider login, session history, and
ordinary per-working-directory sessions in that directory.

Attro **never copies or symlinks** live OAuth tokens, auth files, sessions,
trust decisions, agent definitions, model routing, skills, prompts, or history
from `~/.pi/agent`. Authenticate separately with `/login` after install. OAuth
must be authenticated in the shared profile: Pi 0.85.0's per-path OAuth locks
make sharing aliased token files unsafe. Agent file symlinks and hardlinks are
refused. At runtime Pi may still load personal config/skills and trusted-project
`AGENTS.md` / `.pi` resources according to upstream discovery rules. Attro does
not edit `~/.attro/agent` when the repository recipe changes.

Environment routing for exec and try (except trial override):

| Variable | Purpose |
| --- | --- |
| `PI_CODING_AGENT_DIR` | Shared writable agent directory |
| `RPIV_CONFIG_HOME` | `<agent>/rpiv-config` |
| `PI_LENS_CONFIG_PATH` | `<agent>/lens-config.json` |
| `ATTRO_RESOURCE_DIR` (alias: `PIATTRO_RESOURCE_DIR`) | Legacy release path; see below |

Provider API keys and other ambient provider configuration from the environment
are intentionally inherited. Attro does not override `HOME` or change
billing/provider routing. It clears inherited Pi session-directory/session
markers and package/server path overrides. Pi startup network checks are disabled
with `PI_OFFLINE=1` and `PI_SKIP_VERSION_CHECK=1`; this does not disable
provider requests or plugin networking.

### Legacy `ATTRO_RESOURCE_DIR`

Older releases prepared with personal resource bundles set
`ATTRO_RESOURCE_DIR` to `<release>/profile/resources`. Current recipe releases
do not ship personal skills, prompts, or extensions in that tree. If your own
configuration or extensions still reference the bundled path, move those assets
into `~/.attro/agent` (or another Pi discovery location you control) and update
the references yourself. Attro does not rewrite personal files for you.

## Retained release layout (shared-v1)

Each `releases/<id>/` contains:

```
pi/          source-built Pi monorepo from pinned plugins/attro-core (see below)
plugins/     committed plugin trees, with dependencies/build artifacts
config/      allowlisted plugin configs and pristine managed settings
profile/     empty placeholder directories for legacy layout compatibility
npm/         descriptor npmPackages installs from committed runtime lock inputs
```

There is **no per-release `agent/` directory** in shared-v1. User state lives
only under `~/.attro/agent`.

**Source core (`pi/`):** preparation exports the pinned `plugins/attro-core`
commit, runs `npm ci` against its committed lock, applies the hash-pinned
upstream **0.85.0** model-data archive, and runs the offline monorepo build.
The retained CLI is `pi/packages/coding-agent/dist/bundle/cli.js`. Core and TUI
packages are built together from the same monorepo tree. Preparation requires
network access for locked dependencies and the pinned model-data download;
retained releases are larger than npm-only core installs. Provenance is recorded
in `pi/core.json`.

Plugin paths retain their source layout, including
`plugins/rpiv-mono/packages/rpiv-todo`. Allowlisted plugin configs from
`config/` are flattened by basename into release `config/`. New Attro releases
do not copy Quattro theme files from `themes/` or pass `--theme` flags; upstream
Pi built-in themes and personal theme files under `~/.attro/agent` remain
available at runtime. Managed resource paths in prepared `config/settings.json`
are absolute paths inside the release; launch prepends them as Pi CLI flags (`-e`).

Git exports use the validated committed root and pinned submodule commits, not
mutable working-tree contents. Ignored build artifacts are not copied. Symlinked
source files are rejected. Dependency installs and the reviewed Lens/attro-core
builds run only in staging. Failed preparation cannot replace or delete an
existing release. The operation lock serializes cooperating manager processes.
Activation changes only the atomically replaced, fsynced `state.json`
active/previous pointers; retained settings and binaries are not rewritten.

Descriptor npm packages use **committed lock inputs** under `runtime/npm`
(`npm ci`). Plugin `npm ci` uses each plugin's committed dependency lock.
Host Node must satisfy the recorded minimum at preparation and launch.

Release paths are absolute and physical. Do not move retained directories.
Code/config immutability is a management convention, not filesystem protection
from your user account or extensions. No release deletion/pruning command is
provided.

## Managed resources and subagents

Exec and try prepend managed resource argv derived from the active release's
prepared settings. The manager also exports a validated JSON envelope in
`ATTRO_MANAGED_RESOURCE_ARGV` (alias: `PIATTRO_MANAGED_RESOURCE_ARGV`) for downstream consumers.

**Verification gate (pending):** subagent child processes must inherit the same
pinned parent-release managed resource argv so children launched while release A
is active do not silently lose managed plugins or custom tools after release B
is activated. The intended design pins parent-release resource args at spawn
time and validates paths against the parent release root. This boundary is
**not yet fully implemented or verified**; treat subagent resource parity as
pending until the spawn seam fix and its regression tests pass.

## Legacy v0.1 releases

Older prepared releases used per-release `agent/` directories with separate
logins and histories per release. Activating or launching them requires the
legacy layout. Attro refuses shared-v1 operations on v0.1 manifests and
reports that legacy credentials and history are **preserved, not migrated**.
Prepare a new release from a current source revision before switching to
shared-v1.

Releases prepared before the personal-bundle boundary may still retain a
populated `profile/resources/` tree. Those directories are immutable with their
release. Preparing a new release from the current recipe does not delete or
re-seed your shared profile.

## Try versus exec

`attro try` uses a temporary agent directory seeded only from the release's
pristine config. It does not copy the shared profile's OAuth credentials,
settings edits, trust decisions, or history. Session/provider/model/trust
defaults are removed from trial settings. It runs Pi as a child process and
removes the temporary agent directory on normal exit; trial logins/history are
disposable. `exec` replaces the wrapper process with the physical release-local
Pi executable and uses the shared profile.

Neither mode is a sandbox. Project-local resources may load when Pi project trust
allows them. Plugins and tools run with your normal user permissions and may
read or write arbitrary home-directory files. Explicit Pi flags can also
redirect sessions or load additional extensions.

## Native mutation guard

The wrapper refuses leading `update`, `install`, `remove`, `uninstall`,
`upgrade`, and `package install|remove|uninstall|update|upgrade` commands. Use
`attro update --repo PATH` and `attro activate RELEASE_ID` instead. This is
an accidental-mutation guard, not a comprehensive restriction on interactive Pi
commands, flags, extensions, or direct execution of the underlying binary.
