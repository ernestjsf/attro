#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from piattro.validate import ValidationError, render_profile, validate_descriptor  # noqa: E402


class DescriptorValidationTests(unittest.TestCase):
    def test_accepts_repo_descriptor(self) -> None:
        data = validate_descriptor(ROOT / "piattro.json")
        self.assertEqual(data["distribution"], "piattro")
        self.assertEqual(data["core"]["version"], "0.85.0")
        self.assertEqual(data["core"]["engines"]["node"], ">=22.19.0")

    def test_rejects_missing_core_version(self) -> None:
        payload = {
            "schemaVersion": 1,
            "distribution": "piattro",
            "version": "0.1.0",
            "profile": "profile/settings.json",
            "sourcesLock": "sources.lock.json",
            "core": {"package": "@earendil-works/pi-coding-agent"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "piattro.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValidationError):
                validate_descriptor(path)


class RenderProfileTests(unittest.TestCase):
    def test_uses_final_release_root_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_root = Path(tmp) / "releases" / "piattro-0.1.0-deadbeef"
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
