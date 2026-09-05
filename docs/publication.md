# Public release preparation

Piattro's original code is MIT, as selected by its owner. See `LICENSE` and
`THIRD_PARTY_NOTICES.md`. That does not make the existing private workbench or
fork histories automatically safe to publish.

## Current source topology

The root checkout is `pi-customizations`, with a `quattro` branch and GitHub
remote `ernestjsf/pi-customizations`. Its seven submodule URLs point to the
maintainer's fork mirrors. Setup documentation currently requires private GitHub
authentication. This implementation does not rename repositories, change
visibility, push branches, or certify anonymous retrieval.

A public launch must choose canonical public URLs. Either audit and publish the
existing histories with explicit approval, or create sanitized public repositories
while preserving upstream licenses and provenance. For each migrated fork,
update the gitlink, `.gitmodules`, and `sources.lock.json` together, then adapt
any private-origin verification rules deliberately. In particular, the existing
source verifier explicitly disallows replacing the subagents mirror with the
older public `ernestjsf/pi-subagents` repository: do not silently bypass that rule.

## What the source manifest does not capture

The seven-fork manifest is not a full backup of the maintainer's live environment.
The audit also found:

| Live resource | Distribution treatment |
| --- | --- |
| `pi-caffeinate`, `pi-btw`, `pi-goal`, `pi-cursor-sdk` | Include only as exact npm pins in `piattro.json`; never rely on an existing global install. |
| `auto-session-name.ts`, `turn-status.ts` | Standalone personal extensions; not automatically copied. Audit and package separately if selected for the public profile. |
| `safety-guard.ts`, `pi-automode` | Personal behavior/policy extensions; do not silently transplant policy into public defaults. |
| Herdr extensions and externally installed skills | Host integrations; not part of the core portable profile. |
| Agent definitions, personal `AGENTS.md`, custom skills/prompts | Personal orchestration and provider assumptions; keep local until explicitly sanitized for sharing. |
| Models, provider login, trust and safety state | Machine/user-local. Never publish credentials or granted trust. |
| Sessions, histories, caches, backups | Excluded from distribution source. |

Inspect the actual descriptor/profile for the current inclusion list; this table
is a migration inventory, not a claim that every component is already supported.
The portable profile is intentionally not an exact clone of the maintainer's
personal behavior.

## Required evidence before publication

1. Run a maintained secret scanner over **all intended public history**, and
   review findings without printing credentials into CI logs or issue reports.
   No full-history secret scan has been completed by this implementation.
2. Inspect fork-specific changes, copied assets, attribution, and any generated
   artifacts. The initial source license audit is not a complete dependency SBOM.
3. In a credential-free environment, clone the candidate recursively and verify
   every pinned commit is available. Validate the source manifest.
4. Run clean preparation and combined runtime checks on each supported platform.
   Offline fixture tests do not demonstrate successful real dependency downloads
   or interactive TUI compatibility.
5. Review a candidate release on another machine, including login, long-running
   sessions, configuration preservation, and rollback.
6. Publish reviewed source references before publishing a root release that
   points at them. Never publish a release with inaccessible gitlinks.

Keep the stable consumer update feed disabled until these gates are satisfied.
