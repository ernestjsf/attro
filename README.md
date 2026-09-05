# pi-customizations

Private Quattro workbench manifest for seven reviewed Pi sources. The sources are
standard Git submodules pinned by the root gitlinks and `sources.lock.json`; this
repository does not patch or bespoke-install submodule checkouts.

## Checkout and preparation

Use private GitHub authentication and recurse into the pinned sources:

```sh
git clone --recurse-submodules https://github.com/ernestjsf/pi-customizations.git ~/projects/pi-customizations
cd ~/projects/pi-customizations
python3 scripts/verify.py
```

The verifier is read-only. Its default check covers gitlinks, checked-out HEADs,
clean submodules, approved private origins, source entry files, and copied config
hashes. It deliberately does **not** claim runtime readiness: Lens `dist/` and
core grammars are generated preparation artifacts. Run the documented build and
then `python3 scripts/verify.py --runtime` to check that the listed runtime files
are present. That optional check does not prove dependency or host compatibility.

Install dependencies only from the lockfiles, without lifecycle scripts:

```sh
for p in plugins/pi-zentui plugins/pi-cc-extensions plugins/pi-web-access \
  plugins/pi-lens plugins/rpiv-mono plugins/pi-ask-user; do
  (cd "$p" && npm ci --ignore-scripts --no-audit --no-fund)
done
```

`pi-subagents` has no lockfile or external runtime dependencies; it uses host-provided
Pi APIs, so no npm install is needed for that submodule. Lens must be prepared
explicitly; see [setup](docs/setup.md). Do not install all seven dependencies just
to run the root source checker.

## Manifest and configs

The root `package.json` is private `0.1.0` and declares the Quattro Amber and
Quattro Green themes only. It does not auto-activate extensions. The five copied
files in `themes/` and `config/` are the explicit allowlist; no auth, session,
safety-policy, or full global settings files are captured. The existing Zentui safety
footer-label placement is unchanged because that setting is display-only, not a
policy change.

The live global settings now select all seven local package paths in `plugins/`;
old npm copies are not registered alongside them. Quattro Green is the active
live theme. See [transcript UI](docs/transcript-ui.md) for display ownership,
configuration, verification, and rollback. The gitlinks and source manifest pin
the reviewed local commits. No commits were pushed by the UI cleanup.

## Validation evidence

The pinned source `QUATTRO.md` reports: Zentui 1,383 passed/1 skipped; CC 181;
web 633; rpiv-todo 232; ask-user 82; subagents full suite passed; Lens 75 targeted
plus lint/build/import and 12 core + 1 vendored grammar checks. Lens was not a full
suite or live combined-TUI run.

See [setup](docs/setup.md) for non-activating preparation and [updating](docs/updating.md)
for the fetch/review/merge workflow.
