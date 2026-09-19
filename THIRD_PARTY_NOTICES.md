# Third-party notices

The root MIT license applies to original Attro code and documentation. It does
not replace third-party licenses. Preserve the license files, copyright headers,
and attribution files in each source tree and installed dependency.

## Fork sources

The five current fork trees each carry upstream licenses. Upstream npm packages
`pi-web-access@0.27.0` and `pi-ask-user@0.14.0` are pinned via `runtime/npm`.
Exact origin URLs and reviewed commits are recorded in `sources.lock.json`.

| Source | Authoritative license |
| --- | --- |
| attro-core (Pi monorepo) | `plugins/attro-core/LICENSE` and per-package notices under `plugins/attro-core/packages/` |
| CC extensions | `plugins/pi-cc-extensions/LICENSE` |
| Lens | `plugins/pi-lens/LICENSE` |
| rpiv mono / selected todo package | `plugins/rpiv-mono/LICENSE` |
| Web access (npm) | upstream `pi-web-access@0.27.0` package LICENSE |
| Ask user (npm) | upstream `pi-ask-user@0.14.0` package LICENSE |
| Subagents | `plugins/pi-subagents/LICENSE` |

Attro **0.2.0** builds Pi core from the pinned `plugins/attro-core` source tree
(`ernestjsf/attro-core`, upstream `earendil-works/pi-mono` at **0.85.0**) rather
than installing `@earendil-works/pi-coding-agent` from npm during preparation.
Legacy upstream npm releases of that package remain readable for comparison.

Additional upstream notices inside those trees remain authoritative:

- CC diff rendering: `plugins/pi-cc-extensions/extensions/renderer/tool/diff/ATTRIBUTION.md`
  (MIT, pi-tool-display / MasuRii and contributors).
- **Zentui (native in attro-core):** portions adapted from upstream `pi-zentui`
  (MIT; copyright Luka). Authoritative notices are the full MIT headers in:
  `plugins/attro-core/packages/coding-agent/src/core/native-git-status.ts`,
  `plugins/attro-core/packages/coding-agent/src/modes/interactive/components/labeled-user-message-render.ts`,
  `plugins/attro-core/packages/coding-agent/src/modes/interactive/components/user-message-osc.ts`.
  Attro does not ship a separate `pi-zentui` recipe package. Archived former
  recipe defaults: `docs/archive/zentui-display-defaults-retired.json`.
- Lens coderabbit rules:
  `plugins/pi-lens/rules/ast-grep-rules/coderabbit/LICENSE` (Apache-2.0).
Source-core preparation downloads the hash-pinned upstream **0.85.0** model-data
archive declared in `attro.json`; that asset carries its own upstream provenance
and must be retained in audit material for prebuilt releases.

Individual plugins may ship their own skills, examples, and documentation under
their source trees. Those notices remain in the plugin repositories. Attro does
**not** redistribute personal skills, prompts, or standalone user extensions from
the distribution recipe. Users who install optional host tools (for example `bb`
or `herdr`) or third-party skills in `~/.attro/agent` are responsible for
retaining the applicable licenses and notices in their own environment.

## Runtime and dependency notices

The attro-core monorepo and the inspected optional npm plugins (`pi-caffeinate`,
`pi-btw`, `pi-web-access`, `pi-ask-user`, and `pi-cursor-sdk`) declare MIT in
their respective package metadata. Installed dependency license files must still
be retained.

**`pi-web-access@0.27.0` curator UI:** when a user opens the stock upstream
curator page in a browser, the page loads web fonts from Google (`fonts.googleapis.com`
/ `fonts.gstatic.com`). That is expected stock behavior and was explicitly accepted
for Attro managed releases; it is separate from npm install-time fetches and from
tool-driven search/fetch traffic. See [setup](docs/setup.md#retired-visual-forks-pi-web-access-pi-ask-user).

Notable other licenses in the selected package graph:

| Dependency | Declared license |
| --- | --- |
| `grok-mermaid` | Apache-2.0 |
| `@mozilla/readability` | Apache-2.0 |
| `linkedom` | ISC |
| `minimatch` | BlueOak-1.0.0 |

The rpiv site (not the selected todo runtime) uses JetBrains Mono under OFL-1.1.
Build/transitive dependencies have additional licenses. This document is an
initial source inventory, **not a complete SBOM, legal opinion, or a clearance
of redistributable compiled artifacts**. Before publishing prebuilt bundles,
audit their actual contents and ship all required license/notice/source offers.

## Publication is separate

A permissive source license does not establish that private fork histories are
safe to expose. Audit the intended public files and history, verify anonymous
access to every pinned source, and obtain approval before changing visibility
or pushing a public release. No repository visibility is changed by this file.
The root repository remains **private** as of the latest documentation refresh.

**History gate:** files removed from the current tree may still exist in earlier
local Git commits and in releases prepared before the personal-bundle boundary.
Do not treat the current checkout as proof that older branches or retained
releases are safe to publish without a separate sanitized-history decision.
See [publication gates](docs/publication.md).
