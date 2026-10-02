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
release from an explicit trusted checkout. A separate `activate` command (or
explicit `update --activate`) switches the active pointer. The
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

## Migrating an existing profile to Pi 1.0

Attro retains its composer, dock, compact transcript, effort profiles, Lens,
Todos, and subagents while adopting Pi's native MCP, codemode, and tool search.
Preparing a new release does **not** rewrite an existing personal profile.
Review and back up the following scoped changes before applying them:

- Remove the `pi-mcp-adapter` package registration when switching to native MCP.
  Keeping it loaded replaces native session `/mcp`; do not run both integrations
  unintentionally. Its `mcp` proxy and `mcpScript` tool are replaced by native
  `tool_search` and `codemode`.
- Add `+codemode` and `+tool_search` to `defaultTools` without discarding existing
  tool choices. Keep `codemode.mode: "on"` to retain ordinary direct tools.
- Native MCP reads `<agent-dir>/mcp.json` and trusted-project `.pi/mcp.json`, not
  the adapter's shared `.mcp.json` discovery paths. Convert only authorized
  entries. Remove adapter-only `auth: "oauth"` and lifecycle options; native
  HTTP servers discover OAuth automatically and enabled servers connect in the
  background. Preserve URLs, arguments, scopes, and approval requirements.
- Managed Attro keeps native MCP credentials in the OS keychain rather than
  silently moving them into `mcp-auth.json`. Existing adapter credentials are
  left untouched, not imported. Use `/mcp login <server>` (or
  `attro mcp login <server>`) for a fresh native sign-in. Browser/workspace
  consent remains a user action. See [native MCP](../plugins/attro-core/packages/coding-agent/docs/mcp.md)
  for credential-store failure and recovery behavior.
- Preserve `approveTools: true` on servers requiring per-call approval.
  Native direct, nested, and resource calls honor it; calls without UI fail
  closed. A same-name project entry replaces the global entry, but an omitted
  approval policy inherits the global policy. Explicit project policies remain
  authoritative in trusted projects.
- Native MCP does not render MCP app windows. Servers such as tldraw can retain
  tool access without the adapter's interactive app UI; confirm this capability
  change before removing an adapter on behalf of another user.
- Lens's `pi_lens_activate_tools` is retired. Use native discovery for its
  deferred tools. Call `check_subagents` directly: its `model-only` exposure
  prevents nested waiting and result-delivery errors.

Do not substitute the new OpenAI ChatGPT login route, model defaults, virtual
routing, or profile mappings for existing provider choices during migration.
Update adapter-specific personal skills through their managed sources where
applicable. Old running sessions keep their leased release; start a new Attro
session after activation instead of reloading them into mixed resources.

Code rollback does not restore these profile edits or OAuth state. Retain a
separate recoverable copy of the previous recipe/code and reviewed config
backups; do not depend on automatic release retention.

## Review and update workflow (maintainers)

1. Start from a clean root and clean submodules; make a backup before any
   migration work. Existing `~/...ui-backups` are retained.
2. Fetch an `upstream` remote inside the relevant submodule.
3. Review the upstream range and merge the intended changes into that submodule's
   `main` branch. Keep its canonical `origin` URL. Publication requires the
   [history and privacy gates](publication.md), not merely a successful merge.
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
7. Push reviewed source branches to their approved mirrors first, then update
   the public root only after verifying every intended public pin is accessible.
   Do not expose private fork history before its publication clearance. Never
   force-push or reset dirty submodules.

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
