# Attro design and release gates

Attro is an opinionated distribution of upstream Pi, not a fork of Pi core in
this repository. Its release is a recipe: Pi **0.85.0** built from the pinned
`plugins/attro-core` source tree, the seven plugin source pins in
`sources.lock.json`, UI/package/theme defaults, and committed runtime lock inputs
for descriptor npm packages. **`attro`** is the everyday launcher and release
manager; it forwards standard Pi flags/prompts and exposes explicit management
subcommands. The existing private workbench remains the source of the first
candidate, not an already-public product.

**Attro 0.2.0** (`shared-v1`) separates immutable release code/resources from
one canonical user profile at `~/.attro/agent`. First activation seeds UI,
package, and theme defaults only. Personal agent definitions, model routing,
skills, prompts, and extensions remain user-owned. Updates and rollbacks preserve
the shared profile; they do not rewrite it with new repository defaults.

## Boundaries

- Do not modify the existing global Pi installation or `~/.pi/agent` during
  development or setup. PATH adoption must be explicit; `./install` does not edit
  shell startup files.
- Prepare each release independently. Failed preparation must leave the active
  release intact. Keep old installations for offline rollback.
- Keep user credentials, sessions, provider selections, and project trust out of
  source control. Never copy a live configuration directory wholesale.
- Seed the shared profile once on first activation from reviewed UI and package
  defaults. Activation, update, and rollback must not rewrite user preferences
  with new defaults.
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

`sources.lock.json` remains the canonical fork inventory (attro-core plus seven
plugin forks). `attro.json` adds the distribution version (**0.2.0**), core
install method (**source**), profile path, and compatibility requirements.
Installed metadata records source identity, `agentMode: shared-v1`, and
preparation information.

**Source core:** preparation exports the pinned `plugins/attro-core` commit,
runs `npm ci` against its committed lock, applies the hash-pinned upstream
**0.85.0** model-data archive, and runs the offline monorepo build. The
retained CLI is `packages/coding-agent/dist/bundle/cli.js`. Core and TUI packages
are built together. Network access is required during preparation. Retained
`releases/<id>/pi/` trees are larger than legacy npm-core installs. Provenance
is recorded in `pi/core.json`. There is no live catalog hydration or package
publication step in this mode.

**Runtime lock inputs:** `runtime/npm` holds committed `package.json` and
`package-lock.json` for descriptor npm packages. Preparation runs `npm ci`
against these inputs. Plugin trees use their own committed locks. Legacy
`runtime/core` npm lock inputs remain in the repository for historical reference
but are **not** used when `core.installMethod` is `source`.

**Profile layout:**

- `profile/settings.json` — initial UI, package, and theme defaults (no personal model routing)
- `config/` — shared display defaults copied into each prepared release (`zentui.json`, `claude-code-style.json`, `rpiv-todo.json`)
- `themes/` — Quattro theme files referenced by the profile

On first activation Attro initializes `~/.attro/agent` once from those defaults
plus the prepared release config. Pi may additionally load personal
config/skills and trusted-project `AGENTS.md` / `.pi` resources at runtime.
Live login, OAuth tokens, and session history from `~/.pi/agent` are never
copied. Attro does not edit `~/.attro/agent` when the repository recipe changes.

Legacy v0.1 releases used per-release `agent/` directories. They remain on disk
if prepared earlier but are not migrated; prepare a new shared-v1 release to adopt
the portable model. Releases prepared before the personal-bundle boundary may
still retain populated `profile/resources/` trees until replaced by a newly
prepared release.

The legacy npm package remains private and theme-only. That flag prevents
accidental npm publication; it is not a statement about the future project's
license or GitHub visibility.

## Managed launch and subagent continuity

Everyday `attro` (no args) and explicit `attro exec`/`try` prepend managed
resource argv from prepared `config/settings.json` and set
`PI_CODING_AGENT_DIR`, `RPIV_CONFIG_HOME`, and `PI_LENS_CONFIG_PATH`. Legacy
releases may also export `ATTRO_RESOURCE_DIR`. The manager exports a validated
JSON envelope in `ATTRO_MANAGED_RESOURCE_ARGV`. Reserved management words such
as `doctor` route to Pi when escaped with `--` (`attro -- doctor`).

**Pending verification gate:** subagent child processes must inherit pinned
parent-release managed resource argv at spawn time so grandchildren do not lose
managed plugins or custom tools when the active pointer changes. The intended
design validates only known resource flags and absolute paths contained in the
parent release root. Implementation and regression tests at the spawn seam are
**in progress**; do not treat subagent resource parity as verified yet.

**Pending verification gate:** source-core build success and combined interactive
TUI behavior on a fresh `./install` are not yet certified.

## Update lanes

Consumer updates adopt a reviewed Attro release. They do not merge upstream
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

- [x] Choose and apply a license for original Attro code with the owner's approval
      (MIT, explicitly selected by the owner; see `LICENSE`).
- [ ] Audit third-party licenses, notices, assets, and redistribution rights
      (attro-core monorepo upstream notices; plugin-shipped skills/docs in fork trees).
- [ ] Audit public candidate files AND all history intended for publication,
      including commits that previously contained personal bundles.
- [ ] Record an explicit sanitized-history decision before any public push or
      visibility change (no history rewrite authorized now).
- [ ] Resolve private source URLs without exposing private history by accident.
- [ ] Prove every pinned source is retrievable without maintainer credentials.
- [ ] Confirm the recipe excludes personal agent/model/skill/prompt bundles while
      retaining maintained core, plugins, npm packages, and display defaults.
- [x] Commit reproducible runtime dependency inputs (`runtime/npm`) for v0.2.0
      descriptor npm preparation.
- [ ] Test real fresh `./install` on macOS and Linux before advertising support.
- [ ] Smoke-test the combined interactive UI and provider login experience.
- [ ] Verify source-core build and retained-release launch on a clean checkout.
- [x] Verify failed preparation/interrupted pointer replacement, concurrent
      operations, and retained-release rollback/schema refusal in isolated
      lifecycle tests (see [evidence](verification.md); v0.1-era evidence;
      shared-v1, installer, and launcher gates partially pending).
- [x] Review storage/activation and release-automation permission boundaries
      independently (Fable review found no blocking safety defects in v0.1 scope).
- [ ] Verify subagent managed-resource inheritance at the spawn seam.
- [ ] Test on a second machine before replacing the maintainer's daily launcher.
- [ ] Publish a reviewed tag and document recovery/uninstall.

No checkbox is satisfied merely by writing the corresponding implementation.
Record actual evidence before marking a gate complete.
