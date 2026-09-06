"""Public-seam subprocess tests for the attro everyday launcher."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATTRO = ROOT / "bin" / "attro"

sys.path.insert(0, str(ROOT))

from attro.state import activate_release, register_release  # noqa: E402
from test_attro_activation import _write_release  # noqa: E402


class AttroLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "managed"
        self.state.mkdir()
        release_id = "attro-0.1.0-launcher"
        release = _write_release(self.state, release_id, marker="launcher")
        pi_bin = release / "pi/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
        pi_bin.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "print('fixture pi', ' '.join(sys.argv[1:]), sep=':')\n",
            encoding="utf-8",
        )
        pi_bin.chmod(0o755)
        register_release(self.state, release_id, release)
        activate_release(self.state, release_id)
        self.env = {
            **os.environ,
            "ATTRO_HOME": str(self.state),
            "PIATTRO_HOME": str(self.state),
            "PI_SKIP_VERSION_CHECK": "1",
        }

    def run_attro(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ATTRO), *args],
            env=self.env,
            capture_output=True,
            text=True,
        )

    def test_no_args_launches_active_pi(self) -> None:
        result = self.run_attro()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fixture pi:", result.stdout)

    def test_pi_flags_and_prompt_forwarding(self) -> None:
        version = self.run_attro("--version")
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn("attro 0.2.0", version.stdout)

        for args in (("-p", "hello"), ("--", "--version"), ("--model", "explicit", "-c")):
            result = self.run_attro(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.startswith("fixture pi:"), result.stdout)
            for token in args:
                if token == "--":
                    continue
                self.assertIn(token, result.stdout)

    def test_management_commands_still_work(self) -> None:
        status = self.run_attro("--json", "status")
        self.assertEqual(status.returncode, 0, status.stderr)
        payload = json.loads(status.stdout)
        self.assertEqual(payload["active"], "attro-0.1.0-launcher")

        doctor = self.run_attro("doctor")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertIn("Attro doctor: OK", doctor.stdout)

        dry_run = self.run_attro("--json", "exec", "--dry-run", "--", "--version")
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        launch = json.loads(dry_run.stdout)
        self.assertIn("--version", launch["argv"])

    def test_reserved_word_escape_routes_to_pi_chat(self) -> None:
        result = self.run_attro("--", "doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("fixture pi:"), result.stdout)
        self.assertIn(" doctor", result.stdout)

        management = self.run_attro("doctor")
        self.assertEqual(management.returncode, 0, management.stderr)
        self.assertIn("Attro doctor: OK", management.stdout)

    def test_help_works_before_installing_an_active_release(self) -> None:
        empty = Path(self.tmp.name) / "uninitialized"
        self.env["ATTRO_HOME"] = str(empty)
        result = self.run_attro("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: attro", result.stdout)
        self.assertFalse(empty.exists())

    def test_equals_form_state_root_routes_management(self) -> None:
        self.env["ATTRO_HOME"] = str(Path(self.tmp.name) / "uninitialized")
        result = self.run_attro("--json", f"--state-root={self.state}", "status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["active"], "attro-0.1.0-launcher")

    def test_option_values_are_not_treated_as_commands(self) -> None:
        result = self.run_attro("-p", "setup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("fixture pi:"), result.stdout)
        self.assertIn("-p", result.stdout)
        self.assertIn("setup", result.stdout)


if __name__ == "__main__":
    unittest.main()
