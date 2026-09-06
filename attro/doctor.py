"""Read-only checks of source inputs and retained release artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from attro.paths import home, platform_supported, release_dir, state_path
from attro.state import load_state, prepared_manifest
from attro.validate import ValidationError, check_node, validate_checkout, validate_descriptor


def run_doctor(*, repo: Path | None = None, state_root: Path | None = None) -> dict[str, Any]:
    root = state_root or home()
    report: dict[str, Any] = {"platformSupported": platform_supported(), "stateRoot": str(root), "issues": [], "warnings": []}
    if not platform_supported():
        report["issues"].append("unsupported platform")
    if repo is not None:
        try:
            descriptor = validate_descriptor(repo / "attro.json")
            validate_checkout(repo, descriptor)
            check_node(descriptor["core"]["engines"]["node"])
            report["descriptorValid"] = True
        except (ValidationError, OSError) as exc:
            report["descriptorValid"] = False
            report["issues"].append(str(exc))
    try:
        report["statePresent"] = state_path(root).exists()
        state = load_state(root)
        report["active"], report["previous"] = state["active"], state["previous"]
        if not report["statePresent"]:
            report["warnings"].append("no managed state yet; run setup --repo PATH")
        for rid in state["releases"]:
            try:
                manifest = prepared_manifest(release_dir(rid, root), rid)
                check_node(manifest["provenance"]["core"]["nodeMinimum"])
            except (ValidationError, OSError) as exc:
                report["issues"].append(f"{rid}: {exc}")
    except (ValidationError, OSError) as exc:
        report["issues"].append(f"state invalid: {exc}")
    report["healthy"] = not report["issues"]
    return report
