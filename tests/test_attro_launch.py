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

from attro.constants import PREPARED_MARKER  # noqa: E402
from attro.launch import (  # noqa: E402
    MANAGED_RESOURCE_ARGV_ENV,
    build_exec_env,
    build_try_env,
    managed_resource_args,
    managed_resource_argv_envelope,
    normalize_pi_command,
    populate_try_agent,
    refuse_managed_mutation,
    validate_managed_resource_argv,
)
from attro.validate import ValidationError  # noqa: E402
from test_attro_activation import _write_release


def _fake_release(tmp: Path, release_id: str) -> Path:
    release_path = _write_release(tmp, release_id, marker="launch")
    config = release_path / "config"
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
            release_path = _fake_release(Path(tmp), "attro-0.1.0-test")
            isolated = Path(tmp) / "sandbox" / "agent"
            populate_try_agent(release_path, isolated)
            self.assertTrue((isolated / "settings.json").is_file())
            self.assertFalse((isolated / "zentui.json").exists())
            self.assertTrue((isolated / "claude-code-style.json").is_file())
            self.assertFalse((isolated / "auth.json").exists())

    def test_build_try_env_clears_session_overrides_from_os_environ(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_path = _fake_release(Path(tmp), "attro-0.1.0-test")
            isolated = Path(tmp) / "sandbox" / "agent"
            populate_try_agent(release_path, isolated)
            with mock.patch.dict(
                "os.environ",
                {
                    "PI_CODING_AGENT_SESSION_DIR": "/tmp/live-session",
                    "PI_SESSION_FILE": "/tmp/session.json",
                    "PI_SESSION_ID": "abc",
                    "RPIV_CONFIG_HOME": "/tmp/live-rpiv-config",
                    "PI_LENS_CONFIG_PATH": "/tmp/live-lens-config.json",
                },
                clear=False,
            ):
                env = build_try_env(release_path, isolated)
            for key in ("PI_CODING_AGENT_SESSION_DIR", "PI_SESSION_FILE", "PI_SESSION_ID"):
                self.assertNotIn(key, env)
            self.assertEqual(env["PI_CODING_AGENT_DIR"], str(isolated.resolve()))
            self.assertEqual(env["RPIV_CONFIG_HOME"], str(isolated.resolve() / "rpiv-config"))
            self.assertEqual(env["PI_LENS_CONFIG_PATH"], str(isolated.resolve() / "lens-config.json"))

    def test_build_exec_env_exports_managed_resource_argv_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_path = _fake_release(Path(tmp), "attro-0.1.0-test")
            agent = Path(tmp) / "agent"
            agent.mkdir()
            envelope = json.loads(managed_resource_argv_envelope(release_path))
            self.assertEqual(envelope, ["-e", str((release_path / "plugins/pi-lens").resolve())])
            env = build_exec_env(release_path, agent_dir=agent)
            self.assertEqual(json.loads(env[MANAGED_RESOURCE_ARGV_ENV]), envelope)
            self.assertEqual(env[MANAGED_RESOURCE_ARGV_ENV], managed_resource_argv_envelope(release_path))

    def test_build_try_env_exports_managed_resource_argv_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_path = _fake_release(Path(tmp), "attro-0.1.0-test")
            isolated = Path(tmp) / "sandbox" / "agent"
            populate_try_agent(release_path, isolated)
            env = build_try_env(release_path, isolated)
            self.assertEqual(env[MANAGED_RESOURCE_ARGV_ENV], managed_resource_argv_envelope(release_path))

    def test_validate_managed_resource_argv_rejects_malformed_and_escaping_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_path = _fake_release(Path(tmp), "attro-0.1.0-test")
            root = release_path.resolve()
            inside = root / "plugins/pi-lens"
            inside.mkdir(parents=True, exist_ok=True)
            outside = Path(tmp) / "outside"
            outside.mkdir()
            with self.assertRaises(ValidationError):
                validate_managed_resource_argv(["-e"], root)
            with self.assertRaises(ValidationError):
                validate_managed_resource_argv(["--evil", str(inside)], root)
            with self.assertRaises(ValidationError):
                validate_managed_resource_argv(["-e", "relative/path"], root)
            with self.assertRaises(ValidationError):
                validate_managed_resource_argv(["-e", str(outside)], root)
            validated = validate_managed_resource_argv(managed_resource_args(release_path), root)
            self.assertEqual(validated, ["-e", str(inside.resolve())])

    def test_managed_resource_paths_preserve_trailing_whitespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_path = _fake_release(Path(tmp), "attro-0.1.0-test")
            root = release_path.resolve()
            nested = root / "plugins/pi-lens"
            nested.mkdir(parents=True, exist_ok=True)
            self.assertEqual(validate_managed_resource_argv(["-e", str(nested)], root), ["-e", str(nested.resolve())])
            trailing_root = Path(tmp) / "release "
            trailing_root.mkdir()
            trailing_path = trailing_root / "plugins/pi-lens"
            trailing_path.mkdir(parents=True)
            self.assertEqual(
                validate_managed_resource_argv(["-e", str(trailing_path)], trailing_root.resolve()),
                ["-e", str(trailing_path.resolve())],
            )


if __name__ == "__main__":
    unittest.main()
