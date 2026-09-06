#!/usr/bin/env python3
"""Public CLI compatibility: legacy state untouched, Attro naming works."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from attro.cli import main  # noqa: E402
from attro.paths import home  # noqa: E402
from attro.state import release_env  # noqa: E402
from test_attro_activation import _write_release  # noqa: E402


class HomeResolutionTests(unittest.TestCase):
    def test_prefers_attro_home_over_legacy_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            attro = Path(tmp) / "attro"
            legacy = Path(tmp) / "legacy"
            attro.mkdir()
            legacy.mkdir()
            with mock.patch.dict(os.environ, {"ATTRO_HOME": str(attro), "PIATTRO_HOME": str(legacy)}, clear=False):
                self.assertEqual(home(), attro)

    def test_reuses_legacy_root_when_new_default_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp)
            legacy = fake_home / ".piattro"
            legacy.mkdir()
            attro = fake_home / ".attro"
            with mock.patch.dict(os.environ, {"HOME": str(fake_home)}, clear=False):
                os.environ.pop("ATTRO_HOME", None)
                os.environ.pop("PIATTRO_HOME", None)
                self.assertFalse(attro.exists())
                self.assertEqual(home(), legacy)

    def test_defaults_to_attro_when_neither_root_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp)
            with mock.patch.dict(os.environ, {"HOME": str(fake_home)}, clear=False):
                os.environ.pop("ATTRO_HOME", None)
                os.environ.pop("PIATTRO_HOME", None)
                self.assertEqual(home(), fake_home / ".attro")


class ReleaseEnvAliasTests(unittest.TestCase):
    def test_release_env_exports_canonical_and_legacy_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            release = _write_release(state_root, "attro-0.2.0-compat", marker="compat")
            agent = state_root / "agent"
            agent.mkdir()
            (agent / ".attro-profile.json").write_text(
                json.dumps({"schemaVersion": 1, "agentMode": "shared-v1", "agentDir": str(agent)}) + "\n"
            )
            env = release_env(release, agent_dir=agent)
            self.assertEqual(env["ATTRO_RESOURCE_DIR"], env["PIATTRO_RESOURCE_DIR"])
            self.assertEqual(env["ATTRO_RELEASE_ID"], env["PIATTRO_RELEASE_ID"])
            self.assertEqual(env["ATTRO_RELEASE_ROOT"], env["PIATTRO_RELEASE_ROOT"])
            self.assertEqual(env["ATTRO_PI_BIN"], env["PIATTRO_PI_BIN"])
            self.assertEqual(env["ATTRO_MANAGED"], env["PIATTRO_MANAGED"])


class LegacyStatePreservationTests(unittest.TestCase):
    def test_status_against_legacy_root_does_not_create_attro_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            fake_home.mkdir()
            legacy = fake_home / ".piattro"
            legacy.mkdir()
            (legacy / "state.json").write_text(json.dumps({"schemaVersion": 1, "active": None, "previous": None, "releases": {}}) + "\n")
            attro_default = fake_home / ".attro"
            with mock.patch.dict(os.environ, {"HOME": str(fake_home)}, clear=False):
                os.environ.pop("ATTRO_HOME", None)
                os.environ.pop("PIATTRO_HOME", None)
                code = main(["status"])
            self.assertEqual(code, 0)
            self.assertTrue(legacy.exists())
            self.assertFalse(attro_default.exists())


class LauncherCompatibilityTests(unittest.TestCase):
    def test_piattro_wrapper_delegates_to_attro_cli(self) -> None:
        wrapper = ROOT / "bin" / "piattro"
        result = subprocess.run([sys.executable, str(wrapper), "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("attro 0.2.0", result.stdout)


if __name__ == "__main__":
    unittest.main()
