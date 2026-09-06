# Public release preparation

Attro's original code is MIT, as selected by its owner. See `LICENSE` and
`THIRD_PARTY_NOTICES.md`. That does not make the existing private workbench or
fork histories automatically safe to publish.

**Current status:** the root repository `ernestjsf/attro` remains
**private**. No visibility change, public tag, or consumer release feed has been
published. Audits of the final committed candidate and full intended histories
are **pending**.

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

## What the source manifest does not capture

The eight-submodule manifest is not a full backup of the maintainer's live environment.
The audit also found:

| Live resource | Distribution treatment |
| --- | --- |
| `pi-caffeinate`, `pi-btw`, `pi-goal`, `pi-cursor-sdk` | Exact npm pins in `attro.json`; never rely on an existing global install. |
| `auto-session-name.ts`, `turn-status.ts` | Standalone personal extensions; not automatically copied. Audit and package separately if selected for the public profile. |
| `safety-guard.ts`, `pi-automode` | Personal behavior/policy extensions; seed config may ship without implementation; do not silently transplant policy into public defaults. |
| Herdr extensions and externally installed skills | Herdr **skill and pi integration assets** are bundled in `profile/resources` under Apache-2.0 with notices; the **Herdr binary** is a host tool and is **not** bundled. |
| bb-cli skill | Bundled in `profile/resources/skills/bb-cli` under MIT with notices; the **bb** CLI/server is a host tool and is **not** bundled. |
| Agent definitions, personal `AGENTS.md`, custom skills/prompts | Reviewed subsets seed `profile/agent/` and `profile/resources/`; Pi may also load trusted-project resources at runtime. Not an exact live clone. |
| Models, provider login, trust and safety state | Machine/user-local. Never publish credentials or granted trust. |
| Sessions, histories, caches, backups | Excluded from distribution source. |

Inspect `profile/inventory.json` and the actual descriptor/profile for the current
inclusion list. The portable profile is intentionally not an exact clone of the
maintainer's personal behavior. Opinionated model routes (including Sol high for
the reviewer agent) are user-config metadata in the seed profile; availability
depends on the installer's own provider accounts.

Attro **0.2.0** uses a separate canonical `~/.attro/agent` profile. Publication
docs must not imply credential migration from live `~/.pi/agent`. Login and
session history are never copied from live `~/.pi/agent` during seeding.

## Required evidence before publication

1. Run a maintained secret scanner over **all intended public history**, and
   review findings without printing credentials into CI logs or issue reports.
   Preliminary scans found fixture-like patterns requiring explicit
   content/context review; **no final committed-candidate scan is complete**.
2. Inspect fork-specific changes, copied assets, attribution, bundled
   `profile/resources` (bb, Herdr, and other vendored files), attro-core monorepo
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
