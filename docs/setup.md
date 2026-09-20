# Setup and manual migration

For the isolated Attro manager, start with the [main README](../README.md).
This page covers consumer install, developer source preparation, and the legacy
workbench live-migration reference. Managed setup builds its own copies; do not
perform the live migration below merely to try a managed release.

This repository contains the source manifest. Preparation is separate from
activation: setup commands below do not edit Pi settings, install/remove live
packages, or bypass guarded settings writes.

## Consumer install (Attro 0.2.0)

Requires Python 3.10+, Git, npm, and Node 22.19.0+ on macOS, Linux, or
Windows through WSL2. Native Windows is not supported. For the tagged one-command
bootstrap and WSL instructions, see [Install](../README.md#install).
The manual equivalent is:

```sh
git clone --recurse-submodules https://github.com/ernestjsf/attro.git \
  ~/projects/pi-customizations
cd ~/projects/pi-customizations
./install
```

`./install`:

1. Runs `attro doctor --repo` on this checkout.
2. Prepares a pinned release (`attro setup --repo`).
3. Activates it.
4. Symlinks **`attro`** into `~/.local/bin` (override with `--bin-dir`).

The installer refuses conflicting existing launchers (non-matching symlinks or
regular files) and does not modify PATH or shell startup files. Add the printed
`export PATH=...` line yourself. The installed launcher resolves to this
checkout's `bin/attro`; keep the checkout at its current path. Repository
`bin/pi` and `bin/piattro` wrappers remain for development but are **not**
installed.

If you set `ATTRO_HOME` during install, export the same value whenever you run
`attro` later.

After install, run **`attro`**, then `/login` for the providers you use. Attro
does not copy credentials, OAuth tokens, session history, agent definitions,
model routing, skills, or prompts from `~/.pi/agent`. The shared profile at
`~/.attro/agent` is initialized once on first activation from reviewed UI,
package, and UI defaults plus the prepared release config; updates and
rollback preserve whatever you establish there. Personal configuration remains
your responsibility under `~/.attro/agent` or other Pi discovery paths.

Dry-run without writing state or links:

```sh
./install --dry-run
```

Manual equivalent:

```sh
./bin/attro doctor --repo "$PWD"
./bin/attro setup --repo "$PWD" --activate
export PATH="$HOME/.local/bin:$PATH"   # after symlinking the attro launcher yourself
attro
/login
```

## Developer fresh checkout

Clone the root with its canonical submodules. After publication, these HTTPS
URLs require no GitHub account or token:

```sh
git clone --recurse-submodules https://github.com/ernestjsf/attro.git \
  ~/projects/pi-customizations
cd ~/projects/pi-customizations
```

If an existing clone was not recursive, use `git submodule update --init --recursive`.
The four submodule origins are the maintained Attro mirrors (three plugin forks
plus `plugins/attro-core`); `pi-web-access` and `pi-ask-user` are pinned from
public npm instead. Zentui is native in attro-core (see
[zentui-native-parity](zentui-native-parity.md)). The subagents origin is specifically
`ernestjsf/attro-subagents`, not the unrelated `ernestjsf/pi-subagents`.

Submodule remotes are local clone configuration and are not versioned. To add the
provenance remotes to a fresh clone:

```sh
git -C plugins/attro-core remote add upstream https://github.com/earendil-works/pi-mono.git
git -C plugins/pi-lens remote add upstream https://github.com/apmantza/pi-lens.git
git -C plugins/rpiv-mono remote add upstream https://github.com/juicesharp/rpiv-mono.git
git -C plugins/pi-subagents remote add upstream https://github.com/williamcr01/pi-subagents.git
```

Install each lockfile-bearing source independently, without lifecycle scripts:

```sh
for p in plugins/pi-lens plugins/rpiv-mono; do
  (cd "$p" && npm ci --ignore-scripts --no-audit --no-fund)
done
```

`pi-subagents` has no dependency lockfile because it has no external runtime
dependencies: it uses host-provided Pi APIs/peer facilities. No `npm ci` is needed
for that submodule. Descriptor npm packages (`pi-web-access`, `pi-ask-user`, and
the other pins in `attro.json`) install from committed `runtime/npm` during
release preparation, not from submodule paths.

### Retired visual forks (`pi-web-access`, `pi-ask-user`)

Attro **0.2.0** pins **`pi-web-access@0.27.0`** and **`pi-ask-user@0.14.0`**
from public npm instead of the former Attro submodule forks. Tools, bundled
`pi-ask-user` skills, and relative profile package order are unchanged. The old
forks are no longer submodules or release inputs.

Behavioral differences from the retired Quattro visual forks (reviewed and
accepted for stock upstream):

| Area | Stock npm | Retired fork |
| --- | --- | --- |
| **Web curator UI** | Upstream styling; opening the curator page in a browser loads **Google Fonts** from `fonts.googleapis.com` and `fonts.gstatic.com` (Outfit, Instrument Serif). | Local Quattro monospace/amber styling without those remote font requests in `curator-page.ts`. |
| **Ask-user UI** | Upstream `index.ts` theme API. | Extra `theme.bg` fallback for hosts/tests that omit background helpers. |

`pi-web-access` search/fetch tools still perform their normal outbound requests
when invoked; npm preparation uses the public registry only (`runtime/npm` lock
validation). The `pi.video` metadata URL in the package manifest is unchanged
from upstream and is not fetched at install time.

### Retired Zentui submodule (Phase 2)

Attro no longer ships `pi-zentui` as a recipe submodule or profile package.
Native attro-core owns the former Zentui surfaces. New releases do **not**
seed `zentui.json`; existing `~/.attro/agent/zentui.json` files are preserved.
See [zentui-native-parity](zentui-native-parity.md).

### Retired CC submodule

Selected compact transcript rendering, `/clear`, `/exit`, `/context`, session
references, and Markdown enhancements are first-party Attro code. The legacy
`claude-code-style.json` filename remains the read-only preference input; edit
supported settings and use `/reload`. The former `/ccstyle` configuration panel
is not bundled. Existing user files and sessions are not migrated or rewritten.
Do not additionally load the retired CC package in managed Attro: its prototype
patches can compete with native rendering. See [transcript UI](transcript-ui.md).

## attro-core and Lens preparation

Attro **0.2.0** builds Pi core from the pinned `plugins/attro-core` monorepo
instead of installing `@earendil-works/pi-coding-agent` from npm. Preparation
exports the pinned commit, runs `npm ci`, downloads the hash-pinned upstream
**0.85.0** model-data archive, and runs the offline build. Network access is
required for locked dependencies and the model-data asset. The built CLI is
`packages/coding-agent/dist/bundle/cli.js`. Core and TUI are built together from
the same tree. Retained releases under `releases/<id>/pi/` are larger than
legacy npm-core installs.

For local development verification of attro-core generated outputs before
`python3 scripts/verify.py --runtime`, from `plugins/attro-core`:

```sh
npm ci --ignore-scripts --no-audit --no-fund
# model-data archive URL and sha256 are pinned in attro.json; preparation applies them automatically
npm run build:offline
```

Lens is the other generated-runtime preparation step. From `plugins/pi-lens`, run
these commands in this order:

```sh
npm run build:dist
node scripts/download-grammars.js --core --dest grammars
npm run check:grammars
```

`dist/` and `grammars/` are ignored generated artifacts and are legitimately absent
from a pristine source-pin checkout. Development Lens tests additionally require
an in-place build before tests:

```sh
npm run build
npm test -- tests/tools/render-compact.test.ts tests/clients/widget-state.test.ts
```

Other plugin runtimes are direct TypeScript entrypoints as declared in
`sources.lock.json`. The rpiv runtime package is only
`plugins/rpiv-mono/packages/rpiv-todo`; inspect each source package's own entry
paths before using another package.

After preparation, the optional runtime-file presence check is explicit and still
read-only:

```sh
python3 scripts/verify.py --runtime
```

This checks only that the manifest's listed runtime files exist. It does not prove
runtime readiness, attro-core build success, dependency installation, or host
compatibility; `npm run check:grammars` is the separate Lens grammar provenance
check.

## Optional manual Pi migration (non-managed)

Attro managed install does **not** perform manual Pi settings migration and does
not copy live credentials or history. If you maintain a separate global Pi
installation and want to point matching package entries at this checkout's plugin
paths, replace only the matching package identities below. This table is not a
replacement full settings JSON:

| Existing package identity | Replacement local path |
| --- | --- |
| `pi-zentui` | native attro-core (no separate recipe package) |
| `pi-cc-extensions` | selected features native in managed Attro; no separate recipe package |
| `pi-lens` | `~/projects/pi-customizations/plugins/pi-lens` |
| `@juicesharp/rpiv-todo` | `~/projects/pi-customizations/plugins/rpiv-mono/packages/rpiv-todo` |
| `pi-web-access` | npm pin `pi-web-access@0.27.0` (see `runtime/npm`) |
| `pi-ask-user` | npm pin `pi-ask-user@0.14.0` (see `runtime/npm`) |
| `@williamcr01/pi-subagents` | `~/projects/pi-customizations/plugins/pi-subagents` |

Pi core itself is **not** migrated through this table; Attro builds it from
`plugins/attro-core` during release preparation.

Preserve every unrelated package, filter, and safety setting. Never keep both an
old source and its replacement; never paste a fragment over the global settings
document; and never run `pi remove`, because it would remove the original dirty
repository registration.

The root checkout exports Quattro themes through `package.json` for originalPi
use. Those source files remain in `themes/` (Green includes optional `dockBg`
color `#0e1713`), but new Attro releases do not copy them into release
`config/` or pass `--theme` flags. Fresh Attro profiles use upstream Pi theme
defaults until you add personal theme files under `~/.attro/agent`.

See [transcript UI](transcript-ui.md) for the active display ownership and reload
instructions. Changes inside a registered local source tree require `/reload`
(or a restart) to load; theme file edits hot-reload separately.
