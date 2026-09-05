# Setup and manual migration

For the isolated Piattro manager, start with the [main README](../README.md).
This page covers consumer install, developer source preparation, and the legacy
workbench live-migration reference. Managed setup builds its own copies; do not
perform the live migration below merely to try a managed release.

This repository is a reviewed, private source manifest. Preparation is separate
from activation: setup commands below do not edit Pi settings, install/remove live
packages, or bypass guarded settings writes.

## Consumer install (Piattro 0.2.0)

After prerequisites (Python 3.10+, Git, npm, Node 22.19.0+) and private GitHub
authentication for the recursive clone:

```sh
git clone --recurse-submodules https://github.com/ernestjsf/pi-customizations.git \
  ~/projects/pi-customizations
cd ~/projects/pi-customizations
./install
```

`./install`:

1. Runs `piattro doctor --repo` on this checkout.
2. Prepares a pinned release (`piattro setup --repo`).
3. Activates it.
4. Symlinks `pi` and `piattro` into `~/.local/bin` (override with `--bin-dir`).

The installer refuses conflicting existing launchers (non-matching symlinks or
regular files) and does not modify PATH or shell startup files. Add the printed
`export PATH=...` line yourself. Launchers resolve to this checkout's
`bin/pi` and `bin/piattro`; keep the checkout at its current path.

If you set `PIATTRO_HOME` during install, export the same value whenever you run
`pi` or `piattro` later.

After install, run `pi`, then `/login` for the providers you use. Piattro does
not copy credentials or session history from `~/.pi/agent`. The shared profile at
`~/.piattro/agent` is seeded once on first activation; updates and rollback
preserve it.

Dry-run without writing state or links:

```sh
./install --dry-run
```

Manual equivalent:

```sh
./bin/piattro doctor --repo "$PWD"
./bin/piattro setup --repo "$PWD" --activate
export PATH="$HOME/.local/bin:$PATH"   # after symlinking launchers yourself
pi /login
```

## Developer fresh checkout

Authenticate to the private GitHub repositories with the GitHub credential
helper/PAT or SSH, then clone the root with its canonical submodules:

```sh
git clone --recurse-submodules https://github.com/ernestjsf/pi-customizations.git \
  ~/projects/pi-customizations
cd ~/projects/pi-customizations
```

If an existing clone was not recursive, use `git submodule update --init --recursive`.
The seven submodule origins are the private Quattro mirrors; the subagents origin is
specifically `pi-subagents-quattro`, never public `ernestjsf/pi-subagents`.

Submodule remotes are local clone configuration and are not versioned. To add the
provenance remotes to a fresh clone:

```sh
git -C plugins/pi-zentui remote add upstream https://github.com/lmilojevicc/pi-zentui.git
git -C plugins/pi-cc-extensions remote add upstream https://github.com/minuque/pi-cc-extensions.git
git -C plugins/pi-web-access remote add upstream https://github.com/nicobailon/pi-web-access.git
git -C plugins/pi-lens remote add upstream https://github.com/apmantza/pi-lens.git
git -C plugins/rpiv-mono remote add upstream https://github.com/juicesharp/rpiv-mono.git
git -C plugins/pi-ask-user remote add upstream https://github.com/edlsh/pi-ask-user.git
git -C plugins/pi-subagents remote add upstream https://github.com/williamcr01/pi-subagents.git
```

Install each lockfile-bearing source independently, without lifecycle scripts:

```sh
for p in plugins/pi-zentui plugins/pi-cc-extensions plugins/pi-web-access \
  plugins/pi-lens plugins/rpiv-mono plugins/pi-ask-user; do
  (cd "$p" && npm ci --ignore-scripts --no-audit --no-fund)
done
```

`pi-subagents` has no dependency lockfile because it has no external runtime
dependencies: it uses host-provided Pi APIs/peer facilities. No `npm ci` is needed
for that submodule. The root package has no runtime dependency installation.

## Lens preparation

Lens is the one generated-runtime preparation step. From `plugins/pi-lens`, run
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

Other runtimes are direct TypeScript entrypoints as declared in `sources.lock.json`.
The rpiv runtime package is only `plugins/rpiv-mono/packages/rpiv-todo`; inspect each
source package's own entry paths before using another package.

After preparation, the optional runtime-file presence check is explicit and still
read-only:

```sh
python3 scripts/verify.py --runtime
```

This checks only that the manifest's listed runtime files exist. It does not prove
runtime readiness, dependency installation, or host compatibility; `npm run
check:grammars` is the separate Lens grammar provenance check.

## Active installation and migration reference

The live global settings now use the seven local paths below. This table remains
the migration reference for a fresh machine: replace only matching package entries;
it is not a replacement full settings JSON. **Piattro managed install does not
perform this migration** and does not copy live credentials or history:

| Existing package identity | Replacement local path |
| --- | --- |
| `pi-zentui` | `~/projects/pi-customizations/plugins/pi-zentui` |
| `pi-cc-extensions` | `~/projects/pi-customizations/plugins/pi-cc-extensions` |
| `pi-web-access` | `~/projects/pi-customizations/plugins/pi-web-access` |
| `pi-lens` | `~/projects/pi-customizations/plugins/pi-lens` |
| `@juicesharp/rpiv-todo` | `~/projects/pi-customizations/plugins/rpiv-mono/packages/rpiv-todo` |
| `pi-ask-user` | `~/projects/pi-customizations/plugins/pi-ask-user` |
| `@williamcr01/pi-subagents` | `~/projects/pi-customizations/plugins/pi-subagents` |

Preserve every unrelated package, filter, and safety setting. Never keep both an
old source and its replacement; never paste a fragment over the global settings
document; and never run `pi remove`, because it would remove the original dirty
repository registration.

The root package may be added only for themes if desired. The current machine
loads Quattro Green from `~/.pi/agent/themes/`; its tracked copy is in `themes/`.
These setup commands do not auto-edit settings or install/remove live packages.
Old npm copies may remain on disk without being active; do not delete them as
part of UI cleanup. Do not bypass guarded settings writes.

See [transcript UI](transcript-ui.md) for the active display ownership and reload
instructions. Changes inside a registered local source tree require `/reload`
(or a restart) to load; theme file edits hot-reload separately.
