# Zentui recipe retirement (Phase 2)

Attro **0.2.0** no longer ships `pi-zentui` as a submodule or profile package.
Native Attro core owns the former Zentui surfaces (minimalist editor chrome,
user-message labeled frame, selector borders, footer/status integration). CC
extensions continue to own work-first tool rows, thinking disclosure, and
related assistant rendering.

## Historical display defaults

Before retirement, managed releases copied reviewed Zentui defaults from
`config/zentui.json` into each prepared release and seeded `zentui.json` on
first activation only. That seed path is **removed** for new releases:
existing `~/.attro/agent/zentui.json` files are **never deleted** by Attro
updates or rollbacks.

The last reviewed recipe defaults are archived at
[docs/archive/zentui-display-defaults-retired.json](archive/zentui-display-defaults-retired.json)
(SHA-256 `7ef5d08bda4d072a0a912c45b9c8966e7c31b7a9e8df8c646019af01f866f1a7`
when copied from the former `config/zentui.json` pin).

Notable archived choices retained in core parity planning:

- Editor style **minimalist** with compact path display and context gauge.
- Experimental thinking renderer **disabled** (CC owns assistant thinking UI).
- Turn summary and working-line thought preview **disabled** when core owns
  primary activity (`nativeEditor.activityOwner: "core"`).
- Selector borders enabled with Zentui color source (migrating to core-native).

## Retained manifests

Release manifests snapshot `sources.provenance` from preparation time. Older
releases may still list `config/zentui.json` and `plugins/pi-zentui`; Attro
continues to validate those embedded records structurally without requiring the
current shipped recipe to include them.

## License / notices

Upstream `pi-zentui` is MIT-licensed (copyright Luka). Attro ships the adapted
surfaces in attro-core only; each port carries a full MIT header:

- `plugins/attro-core/packages/coding-agent/src/core/native-git-status.ts`
- `plugins/attro-core/packages/coding-agent/src/modes/interactive/components/labeled-user-message-render.ts`
- `plugins/attro-core/packages/coding-agent/src/modes/interactive/components/user-message-osc.ts`

See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
