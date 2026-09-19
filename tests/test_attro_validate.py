#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from attro.constants import CORE_SOURCE_SUBMODULE  # noqa: E402
from attro.validate import (  # noqa: E402
    ValidationError,
    render_profile,
    validate_core_source_archive_alignment,
    validate_core_sources_lock_entry,
    validate_descriptor,
    validate_shipped_sources_lock,
    validate_sources_lock,
)

LEGACY_CORE_BASE_COMMIT = "36b02b695383ad89bc3a22b73633be3fa27be3c1"
LEGACY_CORE_BASE_VERSION = "0.0.3"
LEGACY_CORE_PROVENANCE = "QUATTRO.md"


def legacy_retained_sources_lock_manifest() -> dict:
    """Pre–Phase-1A core entry shape for retained-release manifest regression."""
    manifest = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    manifest = copy.deepcopy(manifest)
    for entry in manifest["submodules"]:
        if entry["path"] == CORE_SOURCE_SUBMODULE:
            entry["baseCommit"] = LEGACY_CORE_BASE_COMMIT
            entry["baseVersion"] = LEGACY_CORE_BASE_VERSION
            entry["provenance"] = LEGACY_CORE_PROVENANCE
            entry.pop("forkRootCommit", None)
            entry.pop("sourceArchive", None)
            entry.pop("forkComparison", None)
            break
    return manifest


class DescriptorValidationTests(unittest.TestCase):
    def test_accepts_repo_descriptor(self) -> None:
        data = validate_descriptor(ROOT / "attro.json")
        self.assertEqual(data["distribution"], "attro")
        self.assertEqual(data["core"]["version"], "0.85.0")
        self.assertEqual(data["core"]["engines"]["node"], ">=22.19.0")

    def test_rejects_missing_core_version(self) -> None:
        payload = {
            "schemaVersion": 1,
            "distribution": "attro",
            "version": "0.1.0",
            "profile": "profile/settings.json",
            "sourcesLock": "sources.lock.json",
            "core": {"package": "@earendil-works/pi-coding-agent"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "attro.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValidationError):
                validate_descriptor(path)


class SourcesLockValidationTests(unittest.TestCase):
    def test_accepts_shipped_and_legacy_branches(self) -> None:
        manifest = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
        validate_shipped_sources_lock(manifest)
        validate_shipped_sources_lock({**manifest, "branch": "quattro"})

    def test_rejects_unsupported_branch(self) -> None:
        manifest = {"schemaVersion": 1, "branch": "feature", "submodules": [], "configs": []}
        with self.assertRaisesRegex(ValidationError, "branch must"):
            validate_sources_lock(manifest)

    def test_accepts_shipped_npm_provenance_entries(self) -> None:
        manifest = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
        npm = manifest.get("npmPackages")
        self.assertIsInstance(npm, list)
        self.assertEqual(len(npm), 2)
        validate_sources_lock(manifest)

    def test_shipped_core_provenance_matches_descriptor(self) -> None:
        manifest = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
        descriptor = validate_descriptor(ROOT / "attro.json")
        core = next(entry for entry in manifest["submodules"] if entry["path"] == CORE_SOURCE_SUBMODULE)
        self.assertEqual(core["baseCommit"], "107d79f11072bbc8a3a757ed7fd69596bee7d68c")
        self.assertEqual(core["forkRootCommit"], "36b02b695383ad89bc3a22b73633be3fa27be3c1")
        self.assertEqual(core["provenance"], "docs/core-provenance.md")
        comparison = core["forkComparison"]
        self.assertEqual(comparison["commonPathCount"], 1658)
        self.assertEqual(comparison["identicalPathCount"], 1588)
        self.assertEqual(comparison["forkTreePathCount"], 1688)
        self.assertEqual(comparison["differentPathCount"], 70)
        self.assertEqual(comparison["forkOnlyPathCount"], 30)
        self.assertEqual(comparison["archiveOnlyPathCount"], 40)
        validate_shipped_sources_lock(manifest)
        validate_core_source_archive_alignment(core, descriptor)
        self.assertTrue((ROOT / "docs/core-provenance.md").is_file())

    def test_fork_comparison_pin_may_differ_from_submodule_pin(self) -> None:
        manifest = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
        core = next(entry for entry in manifest["submodules"] if entry["path"] == CORE_SOURCE_SUBMODULE)
        core = {**core, "forkComparison": {**core["forkComparison"], "pin": "0" * 40}}
        validate_core_sources_lock_entry(core)

    def test_retained_manifest_sources_lock_accepts_baseline_core_shape(self) -> None:
        legacy = legacy_retained_sources_lock_manifest()
        validate_sources_lock(legacy)
        with self.assertRaises(ValidationError):
            validate_shipped_sources_lock(legacy)

    def test_retained_manifest_sources_lock_accepts_zentui_config_record(self) -> None:
        manifest = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
        manifest = copy.deepcopy(manifest)
        manifest["configs"].append(
            {
                "path": "config/zentui.json",
                "source": "~/.pi/agent/zentui.json",
                "sha256": "7ef5d08bda4d072a0a912c45b9c8966e7c31b7a9e8df8c646019af01f866f1a7",
                "provenance": "Historical Zentui display defaults (retired from shipped recipe).",
            }
        )
        validate_sources_lock(manifest)
        with self.assertRaises(ValidationError):
            validate_shipped_sources_lock(manifest)


class RenderProfileTests(unittest.TestCase):
    def test_uses_final_release_root_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_root = Path(tmp) / "releases" / "attro-0.1.0-deadbeef"
            release_root.mkdir(parents=True)
            (release_root / "plugins").mkdir()
            (release_root / "config").mkdir()
            checkout = Path(tmp) / "checkout"
            checkout.mkdir()
            profile = '{"packages":["{{PLUGIN_PI_LENS}}"],"themes":["{{THEME_QUATTRO_GREEN}}"]}'
            rendered = render_profile(profile, release_root, checkout, descriptor={"npmPackages": []})
            payload = json.loads(rendered)
            self.assertTrue(payload["packages"][0].startswith(str(release_root.resolve())))
            self.assertIn("/plugins/pi-lens", payload["packages"][0])
            self.assertIn("/config/quattro-green.json", payload["themes"][0])


if __name__ == "__main__":
    unittest.main()
