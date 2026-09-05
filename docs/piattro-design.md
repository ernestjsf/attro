# Piattro design and release gates

Piattro is an opinionated distribution of upstream Pi, not a fork of Pi core.
Its release is a recipe: an exact Pi version, the seven source pins already in
`sources.lock.json`, and a portable profile. `pi` is the coding command;
`piattro` manages the installation. The existing private workbench remains the
source of the first candidate, not an already-public product.

## Boundaries

- Do not modify the existing global Pi installation or `~/.pi/agent` during
  development or setup. PATH adoption must be explicit.
- Prepare each release independently. Failed preparation must leave the active
  release intact. Keep old installations for offline rollback.
- Keep user credentials, sessions, provider selections, and project trust out of
  source control. Never copy a live configuration directory wholesale.
- Treat local checkouts and their dependencies as executable, trusted source.
  Disabling npm lifecycle scripts does not sandbox an extension or build.
- A separate Pi agent directory isolates Pi configuration, not the operating
  system. Plugins may use HOME, XDG directories, network services, and tools.
- Do not claim code rollback reverses shared-state migrations or external side
  effects. Block incompatible managed state formats until recovery is designed.
- Existing sessions must continue using their resolved release after activation.
  Keep old release directories; do not prune automatically.

## Release records

`sources.lock.json` remains the canonical fork inventory. `piattro.json` adds
the distribution version, Pi pin, profile, and compatibility requirements.
Installed metadata records source identity and preparation information.
Top-level versions alone do not prove full dependency reproducibility: the Pi
runtime dependency graph must eventually be locked and verified for public
release builds, not merely resolved independently on each machine.

The legacy npm package remains private and theme-only. That flag prevents
accidental npm publication; it is not a statement about the future project's
license or GitHub visibility.

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
- [ ] Audit third-party licenses, notices, assets, and redistribution rights.
- [ ] Audit public candidate files AND all history intended for publication.
- [ ] Resolve private source URLs without exposing private history by accident.
- [ ] Prove every pinned source is retrievable without maintainer credentials.
- [ ] Include or explicitly exclude standalone extensions and npm plugins from
      the personal setup; the seven forks alone are not an exact reproduction.
- [ ] Commit the reproducible runtime dependency inputs and artifact provenance.
- [ ] Test real fresh preparation on macOS and Linux before advertising support.
- [ ] Smoke-test the combined interactive UI and provider login experience.
- [ ] Verify interrupted preparation/activation, concurrent operations, and
      retained-release rollback, including state compatibility.
- [ ] Review storage/activation and release-automation permission boundaries independently.
- [ ] Test on a second machine before replacing the maintainer's daily launcher.
- [ ] Publish a reviewed tag and document recovery/uninstall.

No checkbox is satisfied merely by writing the corresponding implementation.
Record actual evidence before marking a gate complete.
