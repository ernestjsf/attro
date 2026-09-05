# Updating pinned sources

The root branch is `quattro`. Submodule gitlinks and `sources.lock.json` are the
canonical pins. Do not rewrite a source pin, force-reset, or discard dirty
submodule work. The existing `~/projects/pi-forks` directories are preparation
copies; future work should use these parent-repository submodules to avoid
divergence.

## Review and update workflow

1. Start from a clean root and clean submodules; make a backup before any
   migration work. Existing `~/...ui-backups` are retained.
2. Fetch an `upstream` remote inside the relevant submodule.
3. Review the upstream range and merge the intended changes into that submodule's
   `quattro` branch. Keep the private `origin` URL and do not publish source from
   this root.
4. Run the source package's locked checks. Use `npm ci --ignore-scripts` first
   when dependencies are absent. For Lens, run `npm run build:dist`, download core
   grammars, and run `npm run check:grammars`; development tests require `npm run
   build` before tests.
5. Update only the submodule gitlink and the corresponding exact `pin`, package
   version/base, lockfile, entry paths, and provenance in `sources.lock.json`.
6. Run `python3 scripts/verify.py` (and `--runtime` after generated preparation
   for file-presence only), inspect `git diff --check`, and commit the root change with a logical
   conventional message.
7. Push the reviewed source branches to their approved private mirrors as needed,
   then push the root private fork only after Lead review. Never force-push or
   reset dirty submodules.

A fresh clone should add upstream remotes using the commands in setup.md; those
remotes are clone-local and intentionally not represented in `.gitmodules`.

## Scope and safety

Do not copy live auth/session/safety/global settings into this repository. Do not
activate packages or alter settings as part of an update. Manual migration must
replace matching entries with local paths while preserving unrelated packages and
filters, without retaining duplicate old/new sources and without `pi remove`.
