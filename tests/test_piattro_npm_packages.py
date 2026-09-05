#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from piattro.npm_packages import (  # noqa: E402
    normalize_npm_packages,
    npm_package_install_dir,
    parse_npm_spec,
    validate_package_name,
    validate_version,
)
from piattro.validate import ValidationError, render_profile, validate_descriptor  # noqa: E402


class ParseNpmSpecTests(unittest.TestCase):
    def test_parses_scoped_and_unscoped_specs(self) -> None:
        self.assertEqual(parse_npm_spec("@narumitw/pi-caffeinate@0.49.4"), ("@narumitw/pi-caffeinate", "0.49.4"))
        self.assertEqual(parse_npm_spec("pi-btw@0.4.1"), ("pi-btw", "0.4.1"))

    def test_rejects_bare_package_name(self) -> None:
        with self.assertRaises(ValidationError):
            parse_npm_spec("pi-btw")


class NormalizeNpmPackagesTests(unittest.TestCase):
    def test_accepts_descriptor_entries(self) -> None:
        entries = normalize_npm_packages(
            [
                {"package": "pi-btw", "version": "0.4.1"},
                {"package": "@narumitw/pi-goal", "version": "0.54.4"},
            ]
        )
        self.assertEqual(entries[0]["package"], "pi-btw")
        self.assertEqual(entries[1]["version"], "0.54.4")

    def test_rejects_duplicate_packages(self) -> None:
        payload = [
            {"package": "pi-btw", "version": "0.4.1"},
            {"package": "pi-btw", "version": "0.4.2"},
        ]
        with self.assertRaises(ValidationError):
            normalize_npm_packages(payload)

    def test_validates_package_and_version_fields(self) -> None:
        self.assertEqual(validate_package_name("@narumitw/pi-goal"), "@narumitw/pi-goal")
        self.assertEqual(validate_version("0.4.1"), "0.4.1")
        with self.assertRaises(ValidationError):
            validate_package_name("")
        with self.assertRaises(ValidationError):
            validate_version("latest")


class RenderProfileNpmTests(unittest.TestCase):
    def test_appends_release_local_npm_paths(self) -> None:
        release_root = Path("/tmp/piatro/releases/piatro-0.1.0-abc")
        descriptor = {
            "npmPackages": [
                {"package": "pi-btw", "version": "0.4.1"},
            ]
        }
        rendered = render_profile('{"packages":["/plugins/pi-lens"]}', release_root, Path("/checkout"), descriptor)
        payload = json.loads(rendered)
        expected = str(npm_package_install_dir(release_root, "pi-btw").resolve())
        self.assertEqual(payload["packages"], ["/plugins/pi-lens", expected])


class DescriptorNpmTests(unittest.TestCase):
    def test_repo_descriptor_includes_four_live_packages(self) -> None:
        data = validate_descriptor(ROOT / "piattro.json")
        packages = [(entry["package"], entry["version"]) for entry in data["npmPackages"]]
        self.assertEqual(
            packages,
            [
                ("@narumitw/pi-caffeinate", "0.49.4"),
                ("pi-btw", "0.4.1"),
                ("@narumitw/pi-goal", "0.54.4"),
                ("pi-cursor-sdk", "0.3.6"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
