"""Public-seam tests for the root install script."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL = REPO_ROOT / "install"

FAKE_ATTRO = '''#!/usr/bin/env python3
import fcntl
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
state_root = Path(os.environ.get("ATTRO_HOME") or os.environ["PIATTRO_HOME"])
state_path = state_root / "state.json"


def emit(data):
    print(json.dumps(data, indent=2, sort_keys=True))


def fail(message):
    emit({"error": message})
    raise SystemExit(1)


args = sys.argv[1:]
if not args:
    fail("missing subcommand")

if args[0] == "--json":
    if len(args) < 2:
        fail("missing subcommand")
    args = args[1:]

if args[0] == "doctor":
    if os.environ.get("FIXTURE_DOCTOR_FAIL") == "1":
        emit({"healthy": False, "issues": ["fixture doctor failed"], "warnings": []})
        raise SystemExit(1)
    repo = Path(args[args.index("--repo") + 1]).resolve()
    if repo != root:
        fail(f"unexpected repo: {repo}")
    emit({"healthy": True, "issues": [], "warnings": []})
    raise SystemExit(0)

if args[0] == "setup":
    repo = Path(args[args.index("--repo") + 1]).resolve()
    if repo != root:
        fail(f"unexpected repo: {repo}")
    if os.environ.get("FIXTURE_SETUP_FAIL") == "1":
        fail("fixture setup failed")
    state_root.mkdir(parents=True, exist_ok=True)
    release_id = os.environ.get("FIXTURE_RELEASE_ID", "attro-0.1.0-fixture")
    state = json.loads(state_path.read_text()) if state_path.is_file() else {"active": None, "previous": None, "releases": {}}
    state["releases"][release_id] = {"path": "releases/" + release_id}
    state_path.write_text(json.dumps(state) + "\\n")
    (state_root / "releases").mkdir(exist_ok=True)
    emit({"releaseId": release_id})
    raise SystemExit(0)

if args[0] == "activate":
    if os.environ.get("FIXTURE_EXPECT_BIN_LOCK"):
        with open(os.environ["FIXTURE_EXPECT_BIN_LOCK"], "a+") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                fail("launcher lock was released before activation")
    if os.environ.get("FIXTURE_ACTIVATE_FAIL") == "1":
        fail("fixture activation failed")
    release_id = args[1]
    state_root.mkdir(parents=True, exist_ok=True)
    state = json.loads(state_path.read_text()) if state_path.is_file() else {"active": None, "previous": None, "releases": {}}
    state["previous"] = state.get("active")
    state["active"] = release_id
    state_path.write_text(json.dumps(state) + "\\n")
    emit({"active": release_id})
    raise SystemExit(0)

fail("unknown command")
'''


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.managed = self.base / "managed"
        self.bin_dir = self.base / "launchers"
        self.repo = self.base / "checkout with spaces"
        self.repo.mkdir()
        self.env = {
            "HOME": str(self.home),
            "ATTRO_HOME": str(self.managed), "PIATTRO_HOME": str(self.managed),
            "PATH": os.environ.get("PATH", ""),
        }
        shutil.copy2(INSTALL, self.repo / "install")
        (self.repo / "install").chmod(0o755)
        bin_root = self.repo / "bin"
        bin_root.mkdir()
        (bin_root / "pi").write_text("#!/bin/sh\necho fixture-pi\n")
        (bin_root / "pi").chmod(0o755)
        (bin_root / "attro").write_text(FAKE_ATTRO)
        (bin_root / "attro").chmod(0o755)
        (bin_root / "piattro").write_text(FAKE_ATTRO)
        (bin_root / "piattro").chmod(0o755)

    def run_install(self, *args: str, extra_env: dict[str, str] | None = None, success: bool = True) -> subprocess.CompletedProcess[str]:
        env = {**self.env, **(extra_env or {})}
        result = subprocess.run(
            [sys.executable, str(self.repo / "install"), "--bin-dir", str(self.bin_dir), *args],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def launcher_targets(self) -> dict[str, Path]:
        return {name: (self.repo / "bin" / name).resolve() for name in ("pi", "attro", "piattro")}

    def test_success_creates_links_and_activates(self):
        result = self.run_install()
        for name, target in self.launcher_targets().items():
            link = self.bin_dir / name
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), target)
        state = json.loads((self.managed / "state.json").read_text())
        self.assertEqual(state["active"], "attro-0.1.0-fixture")
        self.assertIn("export PATH=", result.stdout)
        self.assertIn(str(self.bin_dir), result.stdout)

    def test_preflight_failure_writes_no_state_or_links(self):
        result = self.run_install(extra_env={"FIXTURE_DOCTOR_FAIL": "1"}, success=False)
        self.assertIn("fixture doctor failed", result.stderr)
        self.assertFalse(self.managed.exists())
        self.assertFalse(self.bin_dir.exists())

    def test_setup_failure_leaves_active_unchanged_and_no_links(self):
        self.managed.mkdir()
        (self.managed / "state.json").write_text('{"active":"existing","previous":null,"releases":{}}')
        result = self.run_install(extra_env={"FIXTURE_SETUP_FAIL": "1"}, success=False)
        self.assertIn("fixture setup failed", result.stderr)
        self.assertEqual(json.loads((self.managed / "state.json").read_text())["active"], "existing")
        self.assertFalse(self.bin_dir.exists())

    def test_identity_matching_rerun_is_idempotent(self):
        self.run_install()
        before = {name: (self.bin_dir / name).readlink() for name in ("pi", "attro", "piattro")}
        self.run_install(extra_env={"FIXTURE_RELEASE_ID": "attro-0.2.0-fixture"})
        after = {name: (self.bin_dir / name).readlink() for name in ("pi", "attro", "piattro")}
        self.assertEqual(before, after)
        self.assertEqual(json.loads((self.managed / "state.json").read_text())["active"], "attro-0.2.0-fixture")

    def test_activation_failure_cleans_created_links(self):
        result = self.run_install(extra_env={"FIXTURE_ACTIVATE_FAIL": "1"}, success=False)
        self.assertIn("fixture activation failed", result.stderr)
        self.assertFalse((self.bin_dir / "pi").exists())
        self.assertFalse((self.bin_dir / "attro").exists())
        self.assertFalse((self.bin_dir / "piattro").exists())

    def test_partial_link_failure_removes_first_created_link(self):
        script = self.repo / "install"
        code = f'''import runpy
from pathlib import Path
ns = runpy.run_path({str(script)!r}, run_name="install_probe")
original = Path.symlink_to
def create_link(self, *args, **kwargs):
    if self.name == "attro":
        raise PermissionError("fixture second link failed")
    return original(self, *args, **kwargs)
Path.symlink_to = create_link
raise SystemExit(ns["main"](["--bin-dir", {str(self.bin_dir)!r}]))
'''
        result = subprocess.run([sys.executable, "-c", code], cwd=self.repo, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture second link failed", result.stderr)
        self.assertFalse((self.bin_dir / "pi").is_symlink())
        self.assertFalse((self.bin_dir / "piattro").is_symlink())
        self.assertIsNone(json.loads((self.managed / "state.json").read_text())["active"])

    def test_launcher_lock_covers_activation(self):
        self.run_install(extra_env={"FIXTURE_EXPECT_BIN_LOCK": str(self.bin_dir / ".attro-install.lock")})

    def test_symlinked_launcher_lock_is_rejected(self):
        self.bin_dir.mkdir()
        sentinel = self.base / "unrelated-file"
        sentinel.write_text("preserve")
        (self.bin_dir / ".attro-install.lock").symlink_to(sentinel)
        self.run_install(success=False)
        self.assertEqual(sentinel.read_text(), "preserve")
        self.assertFalse((self.bin_dir / "pi").is_symlink())

    def test_printed_environment_exports_preserve_literal_paths(self):
        self.bin_dir = self.base / "launchers $unexpanded"
        self.managed = self.base / "profile with spaces"
        self.env["ATTRO_HOME"] = str(self.managed)
        self.env.pop("PIATTRO_HOME", None)
        result = self.run_install()
        exports = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("export ")]
        command = "\n".join(exports) + '\nprintf "%s\\n" "$ATTRO_HOME" "$PIATTRO_HOME" "$PATH"'
        shell = subprocess.run(["/bin/sh", "-c", command], env={"PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
        self.assertEqual(shell.returncode, 0, shell.stderr)
        home, legacy_home, path = shell.stdout.splitlines()
        self.assertEqual(home, str(self.managed))
        self.assertEqual(legacy_home, str(self.managed))
        self.assertEqual(path, str(self.bin_dir) + ":/usr/bin:/bin")

    def test_failed_activation_preserves_existing_links_and_active_release(self):
        self.run_install()
        self.run_install(extra_env={"FIXTURE_ACTIVATE_FAIL": "1", "FIXTURE_RELEASE_ID": "attro-0.2.0-fixture"}, success=False)
        self.assertEqual(json.loads((self.managed / "state.json").read_text())["active"], "attro-0.1.0-fixture")
        for name in ("pi", "attro", "piattro"):
            self.assertTrue((self.bin_dir / name).is_symlink())

    def test_existing_native_pi_conflict_is_rejected(self):
        self.bin_dir.mkdir(parents=True)
        (self.bin_dir / "pi").write_text("#!/bin/sh\necho native\n")
        result = self.run_install(success=False)
        self.assertIn("conflicting launcher file", result.stderr)
        self.assertFalse((self.bin_dir / "piattro").exists())
        self.assertFalse(self.managed.exists())

    def test_bin_dir_overlap_with_checkout_is_rejected(self):
        nested = self.repo / "local" / "bin"
        nested.mkdir(parents=True)
        result = self.run_install("--bin-dir", str(nested), success=False)
        self.assertIn("overlaps protected path", result.stderr)

    def test_bin_dir_overlap_with_managed_root_is_rejected(self):
        nested = self.managed / "bin"
        nested.mkdir(parents=True)
        result = self.run_install("--bin-dir", str(nested), success=False)
        self.assertIn("overlaps protected path", result.stderr)

    def test_dry_run_writes_nothing(self):
        result = self.run_install("--dry-run")
        self.assertIn("would install launchers", result.stdout)
        self.assertFalse(self.managed.exists())
        self.assertFalse(self.bin_dir.exists())

    def test_unsupported_platform_is_rejected(self):
        script = self.repo / "install"
        code = f"""import sys
sys.platform = "win32"
ns = {{}}
with open({str(script)!r}) as fh:
    exec(compile(fh.read(), {str(script)!r}, "exec"), ns)
raise SystemExit(ns["main"]([]))
"""
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsupported platform", result.stderr)

    def test_symlink_bin_dir_works(self):
        real_bin = self.base / "real launchers"
        real_bin.mkdir()
        link_bin = self.base / "linked launchers"
        link_bin.symlink_to(real_bin, target_is_directory=True)
        result = subprocess.run(
            [sys.executable, str(self.repo / "install"), "--bin-dir", str(link_bin)],
            cwd=self.repo,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((real_bin / "pi").is_symlink())
        self.assertEqual((real_bin / "pi").resolve(), (self.repo / "bin" / "pi").resolve())


if __name__ == "__main__":
    unittest.main()
