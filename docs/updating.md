# Updating pinned sources

This page is the manual maintainer workflow for source pins. For automated
candidate discovery see [automation](automation.md); for preparing and switching
managed Attro releases see the [README](../README.md). A consumer update does
not merge upstream branches into these workbench sources.

The root branch is `main`. Submodule gitlinks and `sources.lock.json` are the
canonical pins. Do not rewrite a source pin, force-reset, or discard dirty
submodule work. The existing `~/projects/pi-forks` directories are preparation
copies; future work should use these parent-repository submodules to avoid
divergence.

## Consumer update (shared profile)

After `./install` or an equivalent manual setup, updating Attro prepares a new
release from an explicit trusted checkout and switches the active pointer. The
shared profile at `~/.attro/agent` **persists** across update and rollback:

```sh
attro update --repo /path/to/reviewed-clean-checkout
attro activate <new-release-id>
attro rollback   # only if previous code is still retained; shared profile unchanged
```

`update` does not fetch the latest upstream plugin versions automatically; it
builds the recipe pinned in the checkout you pass. Retention keeps the active
release and one staged candidate. Preparing a replacement candidate or activating
a release supersedes older code, which is automatically pruned when idle. Running
sessions keep their release; pending cleanup retries after they exit. There is no
guaranteed offline rollback copy: prepare the desired recipe again if its code
has already been pruned. Legacy per-release user data is preserved. See the
[retention behavior and limitations](../README.md#update-and-rollback).

## Review and update workflow (maintainers)

1. Start from a clean root and clean submodules; make a backup before any
   migration work. Existing `~/...ui-backups` are retained.
2. Fetch an `upstream` remote inside the relevant submodule.
3. Review the upstream range and merge the intended changes into that submodule's
   `main` branch. Keep the private `origin` URL and do not publish source from
   this root.
4. Run the source package's locked checks. Use `npm ci --ignore-scripts` first
   when dependencies are absent. For Lens, run `npm run build:dist`, download core
   grammars, and run `npm run check:grammars`; development tests require `npm run
   build` before tests. For attro-core, run `npm ci` and `npm run build:offline`
   after applying the pinned model-data archive; preparation does this automatically
   during release setup.
5. Update only the submodule gitlink and the corresponding exact `pin`, package
   version/base, lockfile, entry paths, and provenance in `sources.lock.json`.
   When attro-core changes, also review `attro.json` core source metadata and the
   pinned model-data archive URL/sha256 if upstream requires it.
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

Managed Attro does not migrate live `~/.pi/agent` credentials or history into
`~/.attro/agent`. Users authenticate once in the shared profile after install.

Legacy upstream npm releases of `@earendil-works/pi-coding-agent` remain
readable for comparison. Attro **0.2.0** uses explicit source-core preparation
from `plugins/attro-core` instead of bumping that npm package directly.
