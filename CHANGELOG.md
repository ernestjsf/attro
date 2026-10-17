# Changelog

Distribution-level changes are recorded here. Core and plugin repositories keep
their own package histories; this is not an upstream Pi release log.

## Unreleased — 0.2.0 preview

This describes the current source recipe, **not a published release**. No Attro
tag or release is available yet.

### Added and changed

- Source-built Pi **0.87.1** core from the pinned Attro fork, with native
  composer, activity/dock, and selected transcript features.
- The everyday `attro` launcher and explicit preparation, activation, trial,
  update, status, and rollback commands. Preparation uses a reviewed local
  checkout rather than an automatic consumer update feed.
- Immutable per-release code with a shared user profile seeded once from
  UI/package defaults. Existing personal credentials, history, skills, and
  routing are not copied from the original Pi profile.
- Four pinned source forks (core, Lens, rpiv todo, subagents), four descriptor
  npm packages, committed dependency locks, and source/provenance verification.
- Todo-only RPIV runtime packaging retains configuration and localization support
  without installing unrelated workspaces or development dependencies.
- Light child sessions defer Lens indexing and startup scans until requested.
  Subagents use targeted registry reads and a 30-second warm-idle default;
  explicit retention overrides and active concurrency are unchanged.
- Managed resource routing for sessions and subagents; lease-aware cleanup of
  idle superseded releases. The active release and one staged candidate are kept.
- New releases omit Cursor SDK support and attribution patching. Retained
  Cursor-bearing releases remain validated; personal provider data is preserved.
  Native UI replaces the former standalone Zentui/CC recipe inputs.

### Fixed

- Managed session exit hints use the installed `attro` launcher instead of `pi`.
- Child markers activate Lens's lightweight mode. Compact child RPC lifecycle
  events avoid repeating oversized aggregates, with bounded failure reporting.
- Cold symbol-index publication rejects intervening source and snapshot changes
  rather than exposing a superseded build as ready.

### Removed

- Effort-profile selection, editing, cycling, suggestions, and routing overrides.
  Use ordinary model/thinking defaults and agent definitions instead. Legacy
  sessions remain readable without restoring profile routing. Personal settings
  and catalogs are not automatically migrated or deleted.

### Known limits

- The root is public, but all four required source forks remain private.
  Anonymous recursive installation is blocked. No tagged bootstrap, npm Attro
  distribution, prebuilt release, or stable update feed is being advertised.
- macOS and Linux/WSL2 are the intended environments; native Windows is not
  supported. Local macOS evidence does not certify Linux/WSL2, fresh-machine
  installs, authenticated providers, or full model-driven nested-agent behavior.
- A rollback copy is not guaranteed after cleanup. Rollback preserves shared
  profile state and does not undo agent actions or external side effects.
- Trial state isolation is not a sandbox. Personal configuration and legacy
  per-release state are not automatically migrated.
- Full publication, runtime, and dependency-audit gates remain distinct from
  source checks and offline fixture tests.

See [verification evidence](docs/verification.md), [publication status](docs/publication.md),
[managed state](profile/MANAGED.md), and the [security policy](SECURITY.md).
