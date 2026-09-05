# Piattro design and release gates

Piattro is an opinionated distribution of upstream Pi, not a fork of Pi core.
Its release is a recipe: an exact Pi version, the seven source pins in
`sources.lock.json`, a portable profile, and committed runtime lock inputs.
`pi` is the coding command; `piattro` manages the installation. The existing
private workbench remains the source of the first candidate, not an
already-public product.

**Piattro 0.2.0** (`shared-v1`) separates immutable release code/resources from
one canonical user profile at `~/.piattro/agent`. See [parity plan](parity-plan.md)
for the approved continuity decision.

## Boundaries

- Do not modify the existing global Pi installation or `~/.pi/agent` during
  development or setup. PATH adoption must be explicit; `./install` does not edit
  shell startup files.
- Prepare each release independently. Failed preparation must leave the active
  release intact. Keep old installations for offline rollback.
- Keep user credentials, sessions, provider selections, and project trust out of
  source control. Never copy a live configuration directory wholesale.
- Seed the shared profile once on first activation. Activation, update, and
  rollback must not rewrite user preferences with new defaults.
- Treat local checkouts and their dependencies as executable, trusted source.
  Disabling npm lifecycle scripts does not sandbox an extension or build.
- A separate Pi agent directory isolates Pi configuration, not the operating
  system. Plugins may use HOME, XDG directories, network services, and tools.
- Do not claim code rollback reverses shared-state migrations or external side
  effects. Block incompatible managed state formats until recovery is designed.
- Existing sessions must continue using their resolved release after activation.
  Keep old release directories; do not prune automatically.
- Pass managed resource paths through upstream Pi CLI flags so a running release
  A session does not reload release B's plugins after activation changes.

## Release records

`sources.lock.json` remains the canonical fork inventory. `piattro.json` adds
the distribution version (**0.2.0**), Pi pin, profile paths, and compatibility
requirements. Installed metadata records source identity, `agentMode: shared-v1`,
and preparation information.

**Runtime lock inputs:** `runtime/core` and `runtime/npm` hold committed
`package.json` and `package-lock.json` files. Preparation runs `npm ci` against
these inputs for core and descriptor npm packages. Plugin trees use their own
committed locks. This improves reproducibility over v0.1's per-preparation lock
resolution but does not by itself certify full transitive SBOM clearance.

**Profile layout:**

- `profile/settings.json` — initial settings and ordered managed resource references
- `profile/agent/` — reviewed one-time seed defaults (agents, keybindings, models, plugin prefs)
- `profile/resources/` — versioned resource package (extensions, skills, prompts, bundled themes)
- `profile/inventory.json` — provenance record for seeded and bundled files

Legacy v0.1 releases used per-release `agent/` directories. They remain on disk
if prepared earlier but are not migrated; prepare a new shared-v1 release to adopt
the portable model.

The legacy npm package remains private and theme-only. That flag prevents
accidental npm publication; it is not a statement about the future project's
license or GitHub visibility.

## Managed launch and subagent continuity

Exec and try prepend managed resource argv from prepared `config/settings.json`
and set `PI_CODING_AGENT_DIR`, `RPIV_CONFIG_HOME`, `PI_LENS_CONFIG_PATH`, and
`PIATTRO_RESOURCE_DIR`. The manager exports a validated JSON envelope in
`PIATTRO_MANAGED_RESOURCE_ARGV`.

**Pending verification gate:** subagent child processes must inherit pinned
parent-release managed resource argv at spawn time so grandchildren do not lose
managed plugins or custom tools when the active pointer changes. The intended
design validates only known resource flags and absolute paths contained in the
parent release root. Implementation and regression tests at the spawn seam are
**in progress**; do not treat subagent resource parity as verified yet.

## Update lanes

Consumer updates adopt a reviewed Piattro release. They do not merge upstream
plugins on the consumer's computer.

Maintainer automation discovers new upstream revisions and versions. The next
lane prepares merge candidates in disposable checkouts, runs component and
combined checks, opens reviewable PRs, and publishes only with approval. A
scheduled discovery report alone is not that full release pipeline.

A remote stable feed requires an agreed public repository, immutable release
identities, artifact provenance checks, and a release publisher. Until those
exist, an explicit trusted local checkout is the candidate source; there is no
implicit fetch-and-execute from an unreviewed remote.

## Public release checklist

- [x] Choose and apply a license for original Piattro code with the owner's approval
      (MIT, explicitly selected by the owner; see `LICENSE`).
- [ ] Audit third-party licenses, notices, assets, and redistribution rights
      (bb-cli MIT and Herdr Apache-2.0 bundled in `profile/resources`; host
      `bb`/`herdr` binaries not bundled).
- [ ] Audit public candidate files AND all history intended for publication.
- [ ] Resolve private source URLs without exposing private history by accident.
- [ ] Prove every pinned source is retrievable without maintainer credentials.
- [ ] Include or explicitly exclude standalone extensions and npm plugins from
      the personal setup; the seven forks alone are not an exact reproduction.
- [x] Commit reproducible runtime dependency inputs (`runtime/core`, `runtime/npm`)
      for v0.2.0 preparation.
- [ ] Test real fresh `./install` on macOS and Linux before advertising support.
- [ ] Smoke-test the combined interactive UI and provider login experience.
- [x] Verify failed preparation/interrupted pointer replacement, concurrent
      operations, and retained-release rollback/schema refusal in isolated
      lifecycle tests (see [evidence](verification.md); v0.1-era evidence;
      shared-v1 and installer gates partially pending).
- [x] Review storage/activation and release-automation permission boundaries
      independently (Fable review found no blocking safety defects in v0.1 scope).
- [ ] Verify subagent managed-resource inheritance at the spawn seam.
- [ ] Test on a second machine before replacing the maintainer's daily launcher.
- [ ] Publish a reviewed tag and document recovery/uninstall.

No checkbox is satisfied merely by writing the corresponding implementation.
Record actual evidence before marking a gate complete.
