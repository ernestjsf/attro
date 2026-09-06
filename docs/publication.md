# Public release preparation

Attro's original code is MIT, as selected by its owner. See `LICENSE` and
`THIRD_PARTY_NOTICES.md`. That does not make the existing private workbench or
fork histories automatically safe to publish.

**Current status:** the root repository `ernestjsf/attro` remains
**private**. No visibility change, public tag, or consumer release feed has been
published. Audits of the final committed candidate and full intended histories
are **pending**. **No history rewrite is authorized now.** A separate decision
is required before any push or visibility change that would expose prior commits
containing personal configuration, bundled skills, or other removed material.

## Current source topology

The root checkout is `pi-customizations`, with a `quattro` branch and GitHub
remote `https://github.com/ernestjsf/attro.git`. Its **eight submodule**
URLs point to the maintainer's private fork mirrors (attro-core plus seven
plugin forks). Setup documentation currently requires private GitHub
authentication. This implementation does not rename repositories, change
visibility, push branches, or certify anonymous retrieval.

A public launch must choose canonical public URLs. Either audit and publish the
existing histories with explicit approval, or create sanitized public repositories
while preserving upstream licenses and provenance. For each migrated fork,
update the gitlink, `.gitmodules`, and `sources.lock.json` together, then adapt
any private-origin verification rules deliberately. In particular, the existing
source verifier explicitly disallows replacing the subagents mirror with the
older public `ernestjsf/pi-subagents` repository: do not silently bypass that rule.

Attro **0.2.0** builds Pi core from the private `ernestjsf/attro-core` fork
(pinned in `sources.lock.json`) rather than relying on public npm publication of
that core package. Legacy upstream npm releases remain readable for comparison.

## What the distribution ships

Attro ships the maintained core recipe, not a maintainer's personal Pi setup:

| Shipped in the recipe | Not bundled in the recipe |
| --- | --- |
| Source-built Pi core from `plugins/attro-core` | Personal instructions and agent definitions |
| Seven customized plugin forks | Model/provider routing and reasoning preferences |
| Three descriptor npm packages (`pi-caffeinate`, `pi-btw`, `pi-cursor-sdk`) | Personal skills, prompts, and standalone user extensions |
| Shared display defaults in `config/` | Quattro custom themes, personal plugin preferences, and policy extensions |
| UI/package defaults in `profile/settings.json` | OAuth tokens, sessions, trust state, or live `~/.pi/agent` copies |

Model **providers remain available through the shipped plugins and npm packages**.
Only personal routing defaults were removed from the distribution profile. Do not
claim that upstream built-in agents, provider integrations, or plugin-shipped
skills are gone from the maintained forks.

Users keep personal copies under `~/.attro/agent` (or other Pi discovery paths).
Pi still loads personal/global and trusted-project `.pi` resources at runtime.
Plugin repositories may ship their own skills and docs normally. Existing
installed releases retain whatever they were prepared with until a new release is
prepared and activated; Attro does not automatically delete or re-seed personal
state when the recipe changes.

## What the source manifest does not capture

The eight-submodule manifest is not a full backup of any maintainer's live
environment. Additional live-only resources require separate review if ever
selected for a public profile:

| Live resource | Distribution treatment |
| --- | --- |
| `pi-caffeinate`, `pi-btw`, `pi-cursor-sdk` | Exact npm pins in `attro.json`; never rely on an existing global install. |
| Standalone personal extensions (for example turn-status, auto-session-name, safety-guard, pi-automode) | Not bundled; users install or copy into their own agent directory. |
| Optional host tools (`bb`, `herdr`) and externally installed skills | Not bundled; users install separately and retain their own notices. |
| Agent definitions, personal `AGENTS.md`, custom skills/prompts | User-owned under `~/.attro/agent` or trusted-project paths; not seeded from the repository recipe. |
| Models, provider login, trust and safety state | Machine/user-local. Never publish credentials or granted trust. |
| Sessions, histories, caches, backups | Excluded from distribution source. |

Inspect `attro.json`, `profile/settings.json`, and the actual prepared release
for the current inclusion list. The portable profile is intentionally not an
exact clone of any maintainer's personal behavior.

Attro **0.2.0** uses a separate canonical `~/.attro/agent` profile. Publication
docs must not imply credential migration from live `~/.pi/agent`. Login and
session history are never copied from live `~/.pi/agent` during initialization.

Releases prepared before the personal-bundle boundary may still contain
`profile/resources/` trees on disk. Those retained releases are immutable. New
recipe releases do not reproduce that content. Users with configs referencing
`ATTRO_RESOURCE_DIR` or bundled resource paths must update their personal files
themselves; Attro does not edit `~/.attro/agent` during recipe cleanup.

## Required evidence before publication

1. Run a maintained secret scanner over **all intended public history**, and
   review findings without printing credentials into CI logs or issue reports.
   Preliminary scans found fixture-like patterns requiring explicit
   content/context review; **no final committed-candidate scan is complete**.
   Treat earlier commits that contained personal bundles as **still present in
   Git history** until a sanitized publication path is explicitly approved.
2. Inspect fork-specific changes, copied assets, attribution, attro-core monorepo
   notices, and any generated artifacts. The initial source license audit is not a
   complete dependency SBOM.
3. In a credential-free environment, clone the candidate recursively and verify
   every pinned commit is available. Validate the source manifest. Prove
   `./install` end-to-end, including source-core build.
4. Run clean preparation and combined runtime checks on each supported platform.
   Offline fixture tests do not demonstrate successful real dependency downloads,
   model-data archive retrieval, or interactive TUI compatibility.
5. Review a candidate release on another machine, including login, long-running
   sessions, shared-profile continuity across update/rollback, and rollback.
6. Verify subagent managed-resource inheritance before claiming portable
   subagent parity.
7. Publish reviewed source references before publishing a root release that
   points at them. Never publish a release with inaccessible gitlinks.

Keep the stable consumer update feed disabled until these gates are satisfied.
Scheduled update **discovery** (see [automation](automation.md)) is not an
automatic consumer release feed.

## Fork URL identities (Attro mirrors)

These GitHub repository names are Attro mirror identities; plugin directory names in this checkout are unchanged:

| Legacy fork URL | Attro fork URL |
|---|---|
| `ernestjsf/pi-zentui` | `ernestjsf/attro-zentui` |
| `ernestjsf/pi-cc-extensions` | `ernestjsf/attro-cc-extensions` |
| `ernestjsf/pi-web-access` | `ernestjsf/attro-web-access` |
| `ernestjsf/pi-lens` | `ernestjsf/attro-lens` |
| `ernestjsf/rpiv-mono` | `ernestjsf/attro-rpiv` |
| `ernestjsf/pi-ask-user` | `ernestjsf/attro-ask-user` |
| `ernestjsf/pi-subagents-quattro` | `ernestjsf/attro-subagents` |
| _(new private fork)_ | `ernestjsf/attro-core` |

The attro-core fork tracks upstream `earendil-works/pi-mono` at Pi **0.85.0**
for source-built core preparation.
