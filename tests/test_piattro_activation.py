#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from piattro.constants import MANIFEST_FILE, PREPARED_MARKER  # noqa: E402
from piattro.state import activate_release, register_release, release_env  # noqa: E402
from piattro.validate import sha256_file


def _write_release(root: Path, release_id: str, *, marker: str, legacy: bool = False) -> Path:
    release_path = root.resolve() / "releases" / release_id
    agent_dir = release_path / "agent"
    agent_dir.mkdir(parents=True)
    for name in ("config", "plugins", "npm"):
        (release_path / name).mkdir()
    (release_path / "plugins/pi-lens").mkdir()
    (release_path / "profile/agent").mkdir(parents=True)
    (release_path / "profile/resources").mkdir()
    settings = {
        "theme": "quattro-green",
        "packages": [str(release_path / "plugins/pi-lens")],
        "marker": marker,
    }
    (release_path / "config/settings.json").write_text(json.dumps(settings))
    (agent_dir / "settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    pi_bin = release_path / "pi" / "node_modules" / "@earendil-works" / "pi-coding-agent" / "dist" / "bundle" / "cli.js"
    pi_bin.parent.mkdir(parents=True, exist_ok=True)
    pi_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    pi_bin.chmod(0o755)
    package = pi_bin.parents[2]
    (package / "package.json").write_text(json.dumps({"name": "@earendil-works/pi-coding-agent", "version": "0.85.0"}))
    lock = release_path / "pi/package-lock.json"
    lock.write_text('{}\n')
    manifest = {
        "schemaVersion": 1,
        "releaseId": release_id,
        "preparedAt": "2026-01-01T00:00:00+00:00",
        "checkoutRoot": "/tmp/checkout",
        "distribution": "piattro",
        "descriptorVersion": "0.1.0",
        "layout": {name: str(release_path / name) for name in ("pi", "plugins", "config", "agent", "npm")},
        "provenance": {
            "checkoutHead": "a" * 40,
            "sources": {"schemaVersion": 1, "branch": "quattro", "submodules": [], "configs": []},
            "npmPackages": [],
            "core": {
                "package": "@earendil-works/pi-coding-agent",
                "expectedVersion": "0.85.0", "installedVersion": "0.85.0",
                "installMethod": "npm", "nodeMinimum": ">=22.19.0",
                "installRoot": str(package),
                "piBinary": str(pi_bin.resolve()),
                "lockFile": str(lock), "lockSha256": sha256_file(lock),
            }
        },
    }
    if not legacy:
        manifest.update({"agentMode": "shared-v1", "profileFiles": {}, "settingsSha256": sha256_file(release_path / "config/settings.json")})
        manifest["layout"].pop("agent")
        manifest["layout"]["profile"] = str(release_path / "profile")
    (release_path / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (release_path / PREPARED_MARKER).write_text("prepared\n", encoding="utf-8")
    return release_path


class ActivationIsolationTests(unittest.TestCase):
    def test_activation_does_not_rewrite_retained_release_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            release_a = _write_release(state_root, "piattro-0.1.0-aaaaaaaaaaaa", marker="release-a")
            release_b = _write_release(state_root, "piattro-0.1.0-bbbbbbbbbbbb", marker="release-b")
            register_release(state_root, "piattro-0.1.0-aaaaaaaaaaaa", release_a)
            register_release(state_root, "piattro-0.1.0-bbbbbbbbbbbb", release_b)
            activate_release(state_root, "piattro-0.1.0-aaaaaaaaaaaa")
            before = (release_a / "agent" / "settings.json").read_text(encoding="utf-8")
            activate_release(state_root, "piattro-0.1.0-bbbbbbbbbbbb")
            after = (release_a / "agent" / "settings.json").read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertIn("release-a", after)

    def test_release_a_launch_paths_unchanged_after_b_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            release_a = _write_release(state_root, "piattro-0.1.0-aaaaaaaaaaaa", marker="release-a")
            release_b = _write_release(state_root, "piattro-0.1.0-bbbbbbbbbbbb", marker="release-b")
            register_release(state_root, "piattro-0.1.0-aaaaaaaaaaaa", release_a)
            register_release(state_root, "piattro-0.1.0-bbbbbbbbbbbb", release_b)
            activate_release(state_root, "piattro-0.1.0-aaaaaaaaaaaa")
            env_a_before = release_env(release_a)
            activate_release(state_root, "piattro-0.1.0-bbbbbbbbbbbb")
            env_a_after = release_env(release_a)
            self.assertEqual(env_a_before["PI_CODING_AGENT_DIR"], env_a_after["PI_CODING_AGENT_DIR"])
            self.assertEqual(env_a_before["PIATTRO_PI_BIN"], env_a_after["PIATTRO_PI_BIN"])
            self.assertTrue(env_a_after["PI_CODING_AGENT_DIR"].endswith("/agent"))
            self.assertNotIn("/checkout/", env_a_after["PI_CODING_AGENT_DIR"])


if __name__ == "__main__":
    unittest.main()
