# Piattro managed mode

Piattro currently prepares only an **explicitly trusted, clean local checkout**:

```sh
bin/piattro setup --repo /absolute/path/to/pi-customizations --activate
bin/piattro update --repo /absolute/path/to/pi-customizations
bin/piattro activate RELEASE_ID
bin/piattro rollback
bin/piattro status
bin/piattro doctor
bin/piattro try -- --version
bin/pi --version
```

Put this checkout's `bin/` on `PATH`, or symlink its wrappers. The wrappers resolve their physical location; keep the manager checkout available. Prepared Pi releases do not need their original source checkout to launch or roll back. `doctor --repo PATH` additionally checks source inputs; plain `doctor` only checks retained releases and host Node compatibility.

Global `--state-root PATH` (or `PIATTRO_HOME`) selects a separate managed directory, defaulting to `~/.piattro`. Piattro refuses managed roots overlapping live `~/.pi`, its manager checkout, the setup source checkout, or a Git working tree. This is a refusal guard, not an OS security boundary.

Global `--json` emits one JSON document for manager commands, including failures. For `try` and `exec`, it is available only with `--dry-run`; actual Pi output is passed through. Put Pi flags after `--` when using these subcommands. `bin/pi` inserts this separator automatically.

## Retained release layout

Each `releases/<id>/` contains:

```
pi/          exact pinned core npm install and generated dependency lock
plugins/     committed plugin trees, with dependencies/build artifacts
config/      allowlisted themes, plugin configs, pristine managed settings
agent/       writable settings, separate login credentials and session history
npm/         descriptor npmPackages installs and generated dependency lock
```

Plugin paths retain their source layout, including `plugins/rpiv-mono/packages/rpiv-todo`. Themes from `themes/` and allowlisted plugin configs from `config/` are flattened by basename into release `config/`. `agent/` initially receives settings plus `zentui.json` and `claude-code-style.json`; copying the rpiv config into `config/` does not redirect plugins that use their own home-directory paths.

Git exports use the validated committed root and pinned submodule commits, not mutable working-tree contents. Ignored build artifacts are not copied. Symlinked source files are rejected. Dependency installs and the reviewed Lens build run only in staging. Failed preparation cannot replace or delete an existing release. The operation lock serializes cooperating manager processes. Activation changes only the atomically replaced, fsynced `state.json` active/previous pointers; retained settings and binaries are not rewritten.

Core and the descriptor's canonical `npmPackages: [{package, version}]` entries use exact top-level versions. Plugin `npm ci` uses committed dependency locks. **Core/npm dependency locks are newly resolved during preparation**, retained with their hashes for provenance, and do not imply globally reproducible transitive dependency resolution. The four npm packages are appended in descriptor order after the seven plugin entries in profile order. Host Node must satisfy the recorded minimum at preparation and launch.

Release paths are absolute and physical. Do not move retained directories. Code/config immutability is a management convention, not filesystem protection from your user account or extensions. No release deletion/pruning command is provided.

## Credentials, settings, and histories

`exec` uses the selected release's writable `agent/` directly via `PI_CODING_AGENT_DIR`. Piattro never copies or symlinks live OAuth tokens, auth files, sessions, trust decisions, provider settings, or model defaults. OAuth must be authenticated **separately in each release**: Pi 0.85.0's per-path OAuth locks make sharing aliased token files unsafe. Agent file symlinks and hardlinks are refused.

Separate release logins and histories are a deliberate initial limitation, **not seamless user-state migration**. Provider/model selections and settings changes made in one release do not automatically carry into a new release. Rollback returns to the previous release's own settings and history.

Provider API keys and other ambient provider configuration from the environment are intentionally inherited. Piattro does not override `HOME` or change billing/provider routing. It clears inherited Pi session-directory/session markers and package/server path overrides. Pi startup network checks are disabled with `PI_OFFLINE=1` and `PI_SKIP_VERSION_CHECK=1`; this does not disable provider requests or plugin networking.

## Try versus exec

`piattro try` uses a temporary agent directory seeded only from the release's pristine `config/settings.json`, `zentui.json`, and `claude-code-style.json`. It does not copy the writable agent's OAuth credentials, settings edits, trust decisions, or history. Session/provider/model/trust defaults are removed from trial settings. It runs Pi as a child process and removes the temporary agent directory on normal exit; trial logins/history are disposable. `exec` replaces the wrapper process with the physical release-local Pi executable.

Neither mode is a sandbox. Project-local resources may load when Pi project trust allows them. Plugins and tools run with your normal user permissions and may read or write arbitrary home-directory files. Explicit Pi flags can also redirect sessions or load additional extensions.

## Native mutation guard

The wrapper refuses leading `update`, `install`, `remove`, `uninstall`, `upgrade`, and `package install|remove|uninstall|update|upgrade` commands. Use `piattro update --repo PATH` and `piattro activate RELEASE_ID` instead. This is an accidental-mutation guard, not a comprehensive restriction on interactive Pi commands, flags, extensions, or direct execution of the underlying binary.
