#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from piattro.constants import PREPARED_MARKER  # noqa: E402
from piattro.launch import (  # noqa: E402
    build_try_env,
    normalize_pi_command,
    populate_try_agent,
    refuse_managed_mutation,
)
from piattro.validate import ValidationError  # noqa: E402
from test_piattro_activation import _write_release


def _fake_release(tmp: Path, release_id: str) -> Path:
    release_path = _write_release(tmp, release_id, marker="launch")
    config = release_path / "config"
    (config / "zentui.json").write_text("{}\n", encoding="utf-8")
    (config / "claude-code-style.json").write_text("{}\n", encoding="utf-8")
    (release_path / "agent/auth.json").write_text("{}\n", encoding="utf-8")
    return release_path


class LaunchHelperTests(unittest.TestCase):
    def test_normalize_pi_command_strips_double_dash(self) -> None:
        self.assertEqual(normalize_pi_command(["--", "--version"]), ["--version"])
        self.assertEqual(normalize_pi_command(["--version"]), ["--version"])

    def test_refuse_managed_mutation_blocks_update(self) -> None:
        with self.assertRaises(ValidationError):
            refuse_managed_mutation(["update"])

    def test_populate_try_agent_copies_allowlist_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_path = _fake_release(Path(tmp), "piattro-0.1.0-test")
            isolated = Path(tmp) / "sandbox" / "agent"
            populate_try_agent(release_path, isolated)
            self.assertTrue((isolated / "settings.json").is_file())
            self.assertTrue((isolated / "zentui.json").is_file())
            self.assertTrue((isolated / "claude-code-style.json").is_file())
            self.assertFalse((isolated / "auth.json").exists())

    def test_build_try_env_clears_session_overrides_from_os_environ(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_path = _fake_release(Path(tmp), "piattro-0.1.0-test")
            isolated = Path(tmp) / "sandbox" / "agent"
            populate_try_agent(release_path, isolated)
            with mock.patch.dict(
                "os.environ",
                {
                    "PI_CODING_AGENT_SESSION_DIR": "/tmp/live-session",
                    "PI_SESSION_FILE": "/tmp/session.json",
                    "PI_SESSION_ID": "abc",
                },
                clear=False,
            ):
                env = build_try_env(release_path, isolated)
            for key in ("PI_CODING_AGENT_SESSION_DIR", "PI_SESSION_FILE", "PI_SESSION_ID"):
                self.assertNotIn(key, env)
            self.assertEqual(env["PI_CODING_AGENT_DIR"], str(isolated.resolve()))


if __name__ == "__main__":
    unittest.main()
