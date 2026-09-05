# Third-party notices

The root MIT license applies to original Piattro code and documentation. It does
not replace third-party licenses. Preserve the license files, copyright headers,
and attribution files in each source tree and installed dependency.

## Fork sources

The seven current fork trees each carry an MIT license. Their exact upstream
URLs and reviewed commits are recorded in `sources.lock.json`.

| Source | Authoritative license |
| --- | --- |
| Zentui | `plugins/pi-zentui/LICENSE` |
| CC extensions | `plugins/pi-cc-extensions/LICENSE` |
| Web access | `plugins/pi-web-access/LICENSE` |
| Lens | `plugins/pi-lens/LICENSE` |
| rpiv mono / selected todo package | `plugins/rpiv-mono/LICENSE` |
| Ask user | `plugins/pi-ask-user/LICENSE` |
| Subagents | `plugins/pi-subagents/LICENSE` |

Additional upstream notices inside those trees remain authoritative:

- CC diff rendering: `plugins/pi-cc-extensions/extensions/renderer/tool/diff/ATTRIBUTION.md`
  (MIT, pi-tool-display / MasuRii and contributors).
- Zentui experimental thinking: notices in
  `plugins/pi-zentui/extensions/zentui/thinking-experimental.ts`
  (MIT, Zach Yuen and Marc Mironescu / FluxGear).
- Zentui spinners: notices in
  `plugins/pi-zentui/extensions/zentui/working-line-spinners.ts`
  (MIT, Marko Nakic and FammasMaz / pi-cc-tools contributors).
- Lens coderabbit rules:
  `plugins/pi-lens/rules/ast-grep-rules/coderabbit/LICENSE` (Apache-2.0).
- Zentui's README credits a Mohammad Alizade / Unsplash showcase image under
  the **Unsplash License**, not MIT. Do not treat that image as Piattro artwork
  or imply that all repository assets use the source-code license.

## Bundled profile resources (Piattro 0.2.0)

Piattro ships selected redistributable skills and extensions in
`profile/resources/`. Provenance is recorded in `profile/inventory.json`.

| Component | License | Notice / license file |
| --- | --- | --- |
| bb-cli skill | MIT ([get-bb/bb](https://github.com/get-bb/bb)) | `profile/resources/skills/bb-cli/NOTICE.md`, `profile/resources/licenses/get-bb-bb-MIT` |
| Herdr skill | Apache-2.0 ([herdrdev/herdr](https://github.com/herdrdev/herdr)) | `profile/resources/skills/herdr/NOTICE.md`, `profile/resources/licenses/herdrdev-herdr-Apache-2.0` |
| Herdr pi integration extensions | Apache-2.0 (upstream `@ 5eab32da`) | `profile/resources/extensions/herdr-agent-state.NOTICE.md` |

The bundled **bb-cli** and **Herdr** skills document optional host integrations.
The **`bb` CLI/server** and **`herdr` binary** are **not** bundled; users install
those host tools separately if needed.

## Runtime and dependency notices

Upstream Pi and the inspected optional npm plugins (`pi-caffeinate`, `pi-btw`,
`pi-goal`, and `pi-cursor-sdk`) declare MIT. Installed dependency license files
must still be retained. Notable other licenses in the selected package graph:

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
