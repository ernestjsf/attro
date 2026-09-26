# Security policy

## Reporting privately

Do not disclose vulnerabilities, exploit details, credentials, or sensitive
logs in public issues, pull requests, or discussions.

Use [GitHub private vulnerability reporting](https://github.com/ernestjsf/attro/security/advisories/new)
for this repository. Reporting is enabled; sign in to GitHub to submit a private
report rather than opening a public issue. If that channel is unavailable,
request a private contact channel without posting vulnerability details.

Include the affected Attro revision or managed release ID, impact, minimal
reproduction, and relevant environment. Use
synthetic data and redact secrets. If a credential has been exposed, revoke or
rotate it with its issuer; deleting an issue or Git history does not invalidate it.

## Scope and support

Attro **0.2.0 is a source-built preview**, not a stable security-supported release.
Reports should identify the exact source pin; version numbers alone do not
identify every prepared build. There is no published Attro release or tag yet,
no guaranteed response/remediation time, and no promised backport or long-term
support window for older previews.

This policy covers original Attro code and its integration changes. Upstream
Pi, maintained forks, npm dependencies, and user-installed extensions retain
their own licenses and reporting policies; see [third-party notices](THIRD_PARTY_NOTICES.md).
Do not assume an upstream fix is present until the Attro recipe pins it. If the
owner of a suspected flaw is unclear, request a private Attro channel first.

## Execution is not sandboxed

- Agent tools, extensions, language servers, and child processes run with the
  normal permissions of the user who launched Attro. They can read, modify,
  delete, and execute files outside the working directory when that user can.
- Launches inherit the environment, including available provider credentials,
  aside from specific manager overrides. Providers and plugins can make network
  requests. Offline startup flags do not disable tool or provider networking.
- `attro try` isolates temporary agent state, **not host access**. Project trust,
  managed release paths, and mutation guards are not OS security boundaries.
- Untrusted repository content, instructions, tool output, and model responses
  can influence actions through prompt injection. Review executable dependencies
  and extensions before loading them; do not assume every tool call needs approval.
- Installation downloads dependencies and builds source with your permissions.
  Code immutability is a manager convention, not protection against your account.
  Rollback switches retained code; it does not reverse file edits, external side
  effects, or shared-profile changes.

Use a separately configured container, VM, or other OS isolation when needed,
with minimal file mounts, restricted networking, and narrowly scoped credentials.
Keep backups and review changes before applying them elsewhere. Treat session
logs and exported transcripts as sensitive. See [managed-state details](profile/MANAGED.md)
and [verification limits](docs/verification.md).
