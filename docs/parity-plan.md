# Live-profile parity and continuity

This phase targets the maintainer's existing Pi experience, not a generic or
provider-neutral alternative. Its acceptance criterion is: a fresh authorized
clone, one preparation/activation workflow, and initial authentication reproduce
the selected live resources and defaults. Credentials, granted trust, session
history, caches, and machine binaries are not distributed through Git.

## Approved continuity decision

The owner selected a **separate canonical `~/.attro/agent` profile**, initialized
once, rather than reusing or copying the live `~/.pi/agent` authentication store.

- Authenticate once when adopting Attro; all subsequent managed releases use
  the same canonical user-profile path.
- Preserve user preferences, login state, and ordinary per-working-directory
  sessions across updates and rollback.
- Keep release code and managed resource paths version-specific. Pass those
  paths through upstream Pi's supported CLI resource arguments so a running A
  session does not reload B's plugins after activation changes.
- Keep normal user/project resource discovery and project trust behavior. Do not
  use broad `--no-*` discovery flags to hide duplicate managed registrations.
- Seed defaults only when initializing the shared profile. Activation, update,
  and rollback must not rewrite user preferences with new defaults.
- A trial uses isolated temporary state, not the canonical user's credentials
  or sessions. It is not an operating-system sandbox.

Pi 0.85.0 supports repeatable `-e`, `--skill`, `--prompt-template`, and `--theme`
resource arguments. An `-e` package directory includes its declared resources,
not just extension files. This avoids an auth-storage patch or a replacement
Pi CLI. There is no generic read-only settings-default overlay in upstream Pi;
this design intentionally uses one-time initialization instead.

Sharing an OAuth file through different symlink paths is not equivalent to a
canonical profile: Pi's per-path auth locking can treat aliases as different
locks. Do not copy refresh tokens or symlink auth files between releases.

## Profile boundaries

`profile/resources/` is the versioned resource package: standalone extensions,
skills, prompt templates, and any additional redistributable themes.
`profile/agent/` contains explicitly reviewed initial user-state defaults, such
as agent definitions, keybindings, model metadata, and plugin preferences.
`profile/settings.json` records selected initial settings and ordered managed
resource references. The preparation/launch code resolves portable paths.

Provider/model choices are part of the requested opinionated configuration.
Do not silently replace them with different providers, paid API routes, or
weaker permission defaults. Availability still depends on the user's accounts
and host integrations. Copying credentials or granted project trust is excluded.

The live optional safety-guard preference is disabled. If included in the exact
profile, document that fact rather than presenting this preference as a security
sandbox. The existing prompt/approval behavior must not be bypassed by setup.

## Existing panel work

The owner confirmed the uncommitted `pi-subagents` panel/test changes are finished
and authorized incorporating them. Review found the new model/effort labels
lost meaningful text in the fixed-width dashboard column. Fix and test that
regression before committing the fork and advancing its root pin. Preserve the
original feature intent and keep this separate from profile/runtime commits.

## Publication gate

The first historical scan covered the old committed root and fork sources,
not forthcoming profile files or the new panel commit. It reported 26 apparent
fixture findings that require explicit content/context review. Record exact
fingerprints, not blanket exceptions for all test directories.

Before public visibility, scan all intended branch/tag histories including any
remote-only refs, review private GitHub metadata surfaces, and scan the final
publication candidate. Push reviewed fork commits before a root release points
to them. Then verify anonymous retrieval of every pinned source. No visibility
change is implied merely by writing this plan.
