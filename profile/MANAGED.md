# Attro managed mode

Attro **0.2.0** (`agentMode: shared-v1`) uses one canonical user profile and
immutable per-release code/resources. Prepare only from an **explicitly trusted,
clean local checkout**:

```sh
./install                                    # prepare, activate, install launchers
bin/attro setup --repo /path/to/checkout   # manual prepare
bin/attro update --repo /path/to/checkout
bin/attro activate RELEASE_ID
bin/attro rollback
bin/attro status
bin/attro doctor
bin/attro try -- --version
bin/pi --version
```

Launchers symlink this checkout's `bin/pi`, `bin/attro`, and `bin/piattro`; keep the checkout
available. Prepared Pi releases do not need their original source checkout to
launch or roll back. `doctor --repo PATH` additionally checks source inputs;
plain `doctor` only checks retained releases and host Node compatibility.

Global `--state-root PATH` (or `ATTRO_HOME` / legacy `PIATTRO_HOME`) selects the managed directory,
defaulting to `~/.attro` (reusing existing `~/.piattro` when `~/.attro` is absent). Export the same value in every shell that runs `pi`, `attro`, or `piattro`. Attro refuses
managed roots overlapping live `~/.pi`, its manager checkout, the setup source
checkout, or a Git working tree. This is a refusal guard, not an OS security
boundary.

Global `--json` emits one JSON document for manager commands, including failures.
For `try` and `exec`, it is available only with `--dry-run`; actual Pi output is
passed through. Put Pi flags after `--` when using these subcommands. `bin/pi`
inserts this separator automatically.

## Shared profile (`~/.attro/agent`)

On first activation of a shared-profile release, Attro seeds
`~/.attro/agent` once from reviewed defaults in `profile/agent/` and pristine
release config. Subsequent activations, updates, and rollbacks **preserve**
preferences, provider login, session history, and ordinary per-working-directory
sessions in that directory.

Attro **never copies or symlinks** live OAuth tokens, auth files, sessions,
trust decisions, or history from `~/.pi/agent`. Authenticate separately with
`/login` after install. OAuth must be authenticated in the shared profile:
Pi 0.85.0's per-path OAuth locks make sharing aliased token files unsafe. Agent
file symlinks and hardlinks are refused.

Environment routing for exec and try (except trial override):

| Variable | Purpose |
| --- | --- |
| `PI_CODING_AGENT_DIR` | Shared writable agent directory |
| `RPIV_CONFIG_HOME` | `<agent>/rpiv-config` |
| `PI_LENS_CONFIG_PATH` | `<agent>/lens-config.json` |
| `ATTRO_RESOURCE_DIR` (alias: `PIATTRO_RESOURCE_DIR`) | `<release>/profile/resources` |

Provider API keys and other ambient provider configuration from the environment
are intentionally inherited. Attro does not override `HOME` or change
billing/provider routing. It clears inherited Pi session-directory/session
markers and package/server path overrides. Pi startup network checks are disabled
with `PI_OFFLINE=1` and `PI_SKIP_VERSION_CHECK=1`; this does not disable
provider requests or plugin networking.

## Retained release layout (shared-v1)

Each `releases/<id>/` contains:

```
pi/          exact pinned core npm install from committed runtime lock inputs
plugins/     committed plugin trees, with dependencies/build artifacts
config/      allowlisted themes, plugin configs, pristine managed settings
profile/     immutable seed defaults (profile/agent) and resource bundle (profile/resources)
npm/         descriptor npmPackages installs from committed runtime lock inputs
```

There is **no per-release `agent/` directory** in shared-v1. User state lives
only under `~/.attro/agent`.

Plugin paths retain their source layout, including
`plugins/rpiv-mono/packages/rpiv-todo`. Themes from `themes/` and allowlisted
plugin configs from `config/` are flattened by basename into release `config/`.
Managed resource paths in prepared `config/settings.json` are absolute paths
inside the release; launch prepends them as Pi CLI flags (`-e`, `--skill`,
`--prompt-template`, `--theme`).

Git exports use the validated committed root and pinned submodule commits, not
mutable working-tree contents. Ignored build artifacts are not copied. Symlinked
source files are rejected. Dependency installs and the reviewed Lens build run
only in staging. Failed preparation cannot replace or delete an existing
release. The operation lock serializes cooperating manager processes.
Activation changes only the atomically replaced, fsynced `state.json`
active/previous pointers; retained settings and binaries are not rewritten.

Core and npm packages use **committed lock inputs** under `runtime/core` and
`runtime/npm` (`npm ci`). Plugin `npm ci` uses each plugin's committed
dependency lock. Host Node must satisfy the recorded minimum at preparation and
launch.

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

## Try versus exec

`attro try` uses a temporary agent directory seeded only from the release's
pristine config and `profile/agent` defaults. It does not copy the shared
profile's OAuth credentials, settings edits, trust decisions, or history.
Session/provider/model/trust defaults are removed from trial settings. It runs
Pi as a child process and removes the temporary agent directory on normal exit;
trial logins/history are disposable. `exec` replaces the wrapper process with the
physical release-local Pi executable and uses the shared profile.

Neither mode is a sandbox. Project-local resources may load when Pi project trust
allows them. Plugins and tools run with your normal user permissions and may
read or write arbitrary home-directory files. Explicit Pi flags can also
redirect sessions or load additional extensions.

Bundled **bb-cli** and **Herdr** skills document optional host tools; the `bb`
and `herdr` binaries themselves are **not** bundled and must be installed
separately if you use those integrations.

## Native mutation guard

The wrapper refuses leading `update`, `install`, `remove`, `uninstall`,
`upgrade`, and `package install|remove|uninstall|update|upgrade` commands. Use
`attro update --repo PATH` and `attro activate RELEASE_ID` instead. This is
an accidental-mutation guard, not a comprehensive restriction on interactive Pi
commands, flags, extensions, or direct execution of the underlying binary.
