# Update automation

Piattro separates maintainer update discovery from consumer release activation.
Updating a source pin is not the same as publishing a new stable distribution.
A weekly discovery report is **not** an automatic consumer release feed.

## Implemented discovery

```sh
python3 scripts/check_updates.py --report /tmp/piattro-updates.json
python3 scripts/check_updates.py --assess-merges --report /tmp/piattro-merges.json
```

The first command reads `sources.lock.json` and `piattro.json`, queries the
upstream default-branch HEADs and npm `latest` versions, and writes a JSON
report. It does not change pins, checkout branches, install packages, or change
your live environment. A different npm `latest` is a candidate to review, not
proof that an upgrade is compatible (or a version-ordering decision).

`--assess-merges` additionally clones each changed fork into a disposable
directory, fetches the exact fork pin and current upstream revision, and
attempts a non-committing merge there. It preserves Git history for the merge
base and disables hooks/signing during checkout/merge. It does **not** run the
merged code, retain or publish a merge commit, or establish runtime compatibility.
Unavailable fork repositories are reported as errors. This is not an OS sandbox
or a substitute for reviewing trusted Git configuration on the machine.

Exit codes:

- `0`: discovery completed, including when candidates exist.
- `1`: discovery failed or inputs were invalid; inspect the report's errors.
- `2`: candidates exist and `--fail-on-updates` was requested.

The report includes upstream refs, installed recipe pins, candidate versions,
merge assessment results when requested, and explicit errors. Discovery does
not describe a failed lookup as "up to date".

## GitHub workflows

- `.github/workflows/check-updates.yml` runs discovery weekly or manually and
  uploads the report for review. It uses read-only repository permissions and
  does not need fork checkout credentials for the default upstream-only check.
- `.github/workflows/ci.yml` runs offline lifecycle/discovery tests on macOS and
  Linux. It does not require private submodules and does not certify real plugin
  installation, `./install`, or combined TUI readiness.

Both workflows use pinned action commits. No privileged `pull_request_target`
job executes contributor code. No deployment or cross-repository write token is
configured by these files.

## Next automation lane: reviewed release PRs

The current implementation deliberately stops before automatic PRs, fork pushes,
and stable publication. Those require the public source topology and automation
identity to be established first. The intended next lane is:

1. Prepare candidate fork merges in disposable repositories.
2. Build/test each component and the combined distribution.
3. Open reviewable fork PRs; preserve customizations and surface conflicts.
4. After approval, publish the fork commits, then update root gitlinks and recipe
   pins together in a root PR.
5. Run fresh `./install` and rollback checks for the candidate release.
6. Approve and publish a Piattro tag; only then advertise it to consumers.

Grant any future GitHub App only the specific repositories and permissions it
needs. Keep release credentials out of untrusted PR jobs. Do not auto-promote
an update merely because it merges cleanly or its unit tests pass.

Until a public stable feed exists, `piattro update --repo /trusted/checkout`
prepares that explicit local recipe; it does not fetch the newest upstream
versions. Shared-profile state at `~/.piattro/agent` persists across consumer
updates. See [publication gates](publication.md) and [design](piattro-design.md).
