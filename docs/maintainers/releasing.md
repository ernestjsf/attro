# Releasing an Attro preview

This is a maintainer checklist, not an automatic release feed. A passing local
build does not clear private history for publication. Do not publish a tag or
advertise an install command until the applicable gates below pass.

## 1. Freeze and clear the source candidate

- Use a clean root checkout and clean submodules. Record root HEAD, all four
  gitlinks, `attro.json`, and `sources.lock.json` together.
- Finish the [publication audit](publication.md): intended public refs, history,
  commit messages, retained GitHub PR/cache material, Actions logs/artifacts,
  and dependency notices. Existing sanitized archives are private audit
  material, not release assets. Rotate genuine credentials if any are found.
- Resolve any retained-data removal requirement with GitHub Support before
  exposing affected private repositories. A public root repository does not
  waive clearance for its forks or prove that old root objects are inaccessible.
- Review the current `THIRD_PARTY_NOTICES.md` against the actual source recipe.
  Prebuilt bundles need a separate contents/dependency-license audit; this
  checklist initially covers a source-built release.
- Publish cleared fork commits before the root that references them. Verify
  each pin through anonymous HTTPS access, without local object alternates,
  Git credential helpers, or a GitHub token.

Do not rewrite, delete, or change visibility merely to make CI pass. Preserve
unrelated branches and work. Private mirrors that are no longer release inputs
need not be published for the current four-fork recipe.

## 2. Verify the candidate

Run the documented root checks on the exact candidate:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/verify.py
git diff --check
```

Require successful macOS and Linux jobs in `.github/workflows/ci.yml`. A skipped
job or checkout failure is not a pass. Review the required checks in each
changed fork's own contribution instructions too.

In a fresh, credential-free environment, anonymously clone the candidate
recursively and run `./install`. Do not satisfy missing public pins from local
Git objects. Confirm `attro --version`, `attro exec -- --version`,
`attro exec -- --help`, and `attro doctor`, then exercise:

- Interactive startup with no provider: an actionable login/model path, not an
  unrecoverable unavailable-default-profile error.
- A user-authorized provider login and a small real task, followed by exit and
  resume. Never copy maintainer tokens into a release or CI.
- Read/write/edit tools and one nested subagent task with the managed plugins.
- Preparation and activation of another reviewed recipe while preserving the
  shared profile. Check rollback while the previous release is retained and
  its documented refusal after pruning; do not promise an offline rollback copy.
- PATH instructions, diagnostics, and manual uninstall guidance on another
  machine.

WSL2 needs its own check; Linux CI alone does not establish WSL compatibility.
List unverified platforms explicitly instead of promoting them to supported.
Keep synthetic-provider evidence distinct from authenticated provider evidence.

## 3. Publish a versioned preview

- Finalize release notes with known limitations, prerequisite versions, tested
  platforms, exact candidate revisions, and verification commands/results.
- Check `install.sh`'s `ATTRO_RELEASE_TAG` matches the proposed tag. The initial
  planned tag is `v0.2.0-preview.1`; it is not available until actually published.
- Publish the reviewed root commit and an immutable annotated preview tag. Use
  a GitHub **prerelease**, not a stable/latest release. Do not move an existing
  release tag; fix a broken release with a new preview version.
- Do not upload a developer checkout, `node_modules`, live profile, or private
  audit archive as an asset. GitHub's source archive alone omits submodule
  contents; the documented installer uses a recursive Git clone.

## 4. Verify delivery before announcing

Run the **actual tagged** `install.sh` from its public URL in a fresh home on
macOS and Linux. Verify the installed root/fork pins match the release. Fetching
HTTP 200 or running fixture bootstrap tests is not an installation proof.

Only then replace pending-install wording in the README and website. Publish
accurate release notes and update the site's source-status snapshot. Deploy the
site through an explicitly configured hosting project; do not guess a hosting
account or introduce billing to complete a launch.

The consumer update path remains explicit reviewed checkouts, preparation, and
activation. Scheduled upstream discovery is not a consumer update service.

## Evidence to retain

For each release, record the root and fork SHAs, clean/dirty state, OS and
architecture, Python/Node versions, exact commands and exit status, CI run URLs,
public tag/bootstrap checks, and unresolved limits. Keep sensitive scanner
reports private; public evidence should contain counts and conclusions, not
secret values, private paths, or provider transcripts.

A new commit invalidates only evidence affected by that change, except required
current-head CI/release gates. Reuse valid fork check results rather than
rebuilding unchanged code without a reason. Record what changed since the run.
