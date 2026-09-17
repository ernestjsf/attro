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
INSTALL_SH = REPO_ROOT / "install.sh"

FAKE_GIT = """#!/bin/sh
set -eu
log=${FAKE_GIT_LOG:?}
printf '%s\\n' "$*" >> "$log"
if [ "$1" = "clone" ]; then
  shift
  dest=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --recurse-submodules) shift ;;
      --branch) shift 2 ;;
      --*) shift ;;
      *)
        dest="$1"
        shift
        ;;
    esac
  done
  if [ -z "$dest" ] || [ -z "${FAKE_CLONE_TEMPLATE:-}" ]; then
    echo "fake git: missing dest or template" >&2
    exit 1
  fi
  mkdir -p "$dest"
  cp -R "$FAKE_CLONE_TEMPLATE/." "$dest/"
  mkdir -p "$dest/.git"
  exit 0
fi
exit 1
"""

FAKE_NPM = "#!/bin/sh\nexit 0\n"

FAKE_NODE = """#!/bin/sh
if [ "$1" = "-e" ]; then
  if [ "${FAKE_NODE_FAIL_VERSION:-0}" = "1" ]; then
    exit 1
  fi
  exit 0
fi
if [ "$1" = "-v" ] || [ "$1" = "--version" ]; then
  echo "${FAKE_NODE_VERSION:-v22.19.0}"
  exit 0
fi
echo "unsupported fake node invocation: $*" >&2
exit 1
"""

FAKE_ATTRO = '''#!/usr/bin/env python3
import fcntl
import json
import os
import signal
import sys
import time
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

if os.environ.get("FIXTURE_INTERRUPT_AT") == args[0]:
    os.kill(os.getppid(), signal.SIGINT)
    time.sleep(5)
    raise SystemExit(130)

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

    def launcher_target(self) -> Path:
        return (self.repo / "bin" / "attro").resolve()

    def test_success_creates_attro_link_and_activates(self):
        result = self.run_install()
        link = self.bin_dir / "attro"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), self.launcher_target())
        self.assertFalse((self.bin_dir / "pi").exists())
        self.assertFalse((self.bin_dir / "piattro").exists())
        state = json.loads((self.managed / "state.json").read_text())
        self.assertEqual(state["active"], "attro-0.1.0-fixture")
        self.assertIn("export PATH=", result.stdout)
        self.assertIn(str(self.bin_dir), result.stdout)
        self.assertIn("Installed attro launcher", result.stdout)

    def test_reports_installation_phases(self):
        result = self.run_install()
        phases = ("[1/3]", "[2/3]", "[3/3]")
        positions = [result.stderr.index(phase) for phase in phases]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("minutes", result.stderr)

    def test_interrupted_activation_keeps_prepared_release(self):
        result = self.run_install(extra_env={"FIXTURE_INTERRUPT_AT": "activate"}, success=False)
        self.assertEqual(result.returncode, 130, result.stderr)
        self.assertIn("Installation interrupted", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        state = json.loads((self.managed / "state.json").read_text())
        self.assertIsNone(state["active"])
        self.assertIn("attro-0.1.0-fixture", state["releases"])
        self.assertFalse((self.bin_dir / "attro").is_symlink())

    def test_interruption_preserves_existing_launcher_and_activation(self):
        self.run_install()
        before = (self.bin_dir / "attro").readlink()
        result = self.run_install(extra_env={"FIXTURE_INTERRUPT_AT": "activate"}, success=False)
        self.assertEqual(result.returncode, 130, result.stderr)
        self.assertEqual((self.bin_dir / "attro").readlink(), before)
        self.assertEqual(json.loads((self.managed / "state.json").read_text())["active"], "attro-0.1.0-fixture")

    def test_interrupted_preparation_creates_no_launcher(self):
        result = self.run_install(extra_env={"FIXTURE_INTERRUPT_AT": "setup"}, success=False)
        self.assertEqual(result.returncode, 130, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.bin_dir / "attro").is_symlink())

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
        before = (self.bin_dir / "attro").readlink()
        self.run_install(extra_env={"FIXTURE_RELEASE_ID": "attro-0.2.0-fixture"})
        after = (self.bin_dir / "attro").readlink()
        self.assertEqual(before, after)
        self.assertEqual(json.loads((self.managed / "state.json").read_text())["active"], "attro-0.2.0-fixture")

    def test_activation_failure_cleans_created_attro_link(self):
        result = self.run_install(extra_env={"FIXTURE_ACTIVATE_FAIL": "1"}, success=False)
        self.assertIn("fixture activation failed", result.stderr)
        self.assertFalse((self.bin_dir / "attro").exists())

    def test_attro_link_failure_leaves_bin_dir_empty(self):
        script = self.repo / "install"
        code = f'''import runpy
from pathlib import Path
ns = runpy.run_path({str(script)!r}, run_name="install_probe")
original = Path.symlink_to
def create_link(self, *args, **kwargs):
    raise PermissionError("fixture link failed")
Path.symlink_to = create_link
raise SystemExit(ns["main"](["--bin-dir", {str(self.bin_dir)!r}]))
'''
        result = subprocess.run([sys.executable, "-c", code], cwd=self.repo, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture link failed", result.stderr)
        self.assertFalse((self.bin_dir / "attro").is_symlink())
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
        self.assertFalse((self.bin_dir / "attro").is_symlink())

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

    def test_failed_activation_preserves_existing_attro_link_and_active_release(self):
        self.run_install()
        self.run_install(extra_env={"FIXTURE_ACTIVATE_FAIL": "1", "FIXTURE_RELEASE_ID": "attro-0.2.0-fixture"}, success=False)
        self.assertEqual(json.loads((self.managed / "state.json").read_text())["active"], "attro-0.1.0-fixture")
        self.assertTrue((self.bin_dir / "attro").is_symlink())

    def test_existing_native_pi_is_left_untouched(self):
        self.bin_dir.mkdir(parents=True)
        native = self.bin_dir / "pi"
        native.write_text("#!/bin/sh\necho native\n")
        native.chmod(0o755)
        before = native.read_text()
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(native.read_text(), before)
        self.assertFalse(native.is_symlink())
        self.assertTrue((self.bin_dir / "attro").is_symlink())

    def test_existing_legacy_links_are_not_removed(self):
        self.bin_dir.mkdir(parents=True)
        legacy_pi = self.bin_dir / "pi"
        legacy_piattro = self.bin_dir / "piattro"
        legacy_pi.symlink_to(self.repo / "bin" / "pi")
        legacy_piattro.symlink_to(self.repo / "bin" / "piattro")
        self.run_install()
        self.assertTrue(legacy_pi.is_symlink())
        self.assertTrue(legacy_piattro.is_symlink())
        self.assertEqual(legacy_pi.resolve(), (self.repo / "bin" / "pi").resolve())
        self.assertEqual(legacy_piattro.resolve(), (self.repo / "bin" / "piattro").resolve())
        self.assertTrue((self.bin_dir / "attro").is_symlink())

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
        self.assertTrue((real_bin / "attro").is_symlink())
        self.assertEqual((real_bin / "attro").resolve(), (self.repo / "bin" / "attro").resolve())


class BootstrapInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.managed = self.base / "managed"
        self.bin_dir = self.base / "launchers"
        self.source_dir = self.home / ".local" / "share" / "attro"
        self.fake_bin = self.base / "fake-bin"
        self.fake_bin.mkdir()
        self.git_log = self.base / "git.log"
        self.clone_template = self.base / "clone-template"
        self.clone_template.mkdir()
        shutil.copy2(INSTALL, self.clone_template / "install")
        (self.clone_template / "install").chmod(0o755)
        bin_root = self.clone_template / "bin"
        bin_root.mkdir()
        (bin_root / "attro").write_text(FAKE_ATTRO)
        (bin_root / "attro").chmod(0o755)
        for name, body in (("git", FAKE_GIT), ("npm", FAKE_NPM), ("node", FAKE_NODE)):
            path = self.fake_bin / name
            path.write_text(body)
            path.chmod(0o755)
        for helper in ("python3", "uname"):
            resolved = shutil.which(helper)
            if resolved:
                (self.fake_bin / helper).symlink_to(resolved)
        self.env = {
            "HOME": str(self.home),
            "ATTRO_HOME": str(self.managed),
            "PIATTRO_HOME": str(self.managed),
            "ATTRO_BIN_DIR": str(self.bin_dir),
            "PATH": f"{self.fake_bin}:/usr/bin:/bin",
            "FAKE_GIT_LOG": str(self.git_log),
            "FAKE_CLONE_TEMPLATE": str(self.clone_template),
        }

    def run_bootstrap(self, *extra_env: str | tuple[str, str], success: bool = True, pipe: bool = False) -> subprocess.CompletedProcess[str]:
        env = dict(self.env)
        for item in extra_env:
            if isinstance(item, tuple):
                key, value = item
                env[key] = value
        script = INSTALL_SH.read_text()
        if pipe:
            result = subprocess.run(
                ["/bin/sh"],
                input=script,
                env=env,
                cwd=self.base,
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                ["/bin/sh", str(INSTALL_SH)],
                env=env,
                cwd=self.base,
                capture_output=True,
                text=True,
            )
        if success:
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def test_install_sh_passes_shell_syntax_check(self):
        result = subprocess.run(["/bin/sh", "-n", str(INSTALL_SH)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bootstrap_clones_tag_and_runs_install(self):
        result = self.run_bootstrap()
        log = self.git_log.read_text()
        self.assertIn("--recurse-submodules", log)
        self.assertIn("--branch v0.2.0-preview.1", log)
        self.assertIn("https://github.com/ernestjsf/attro.git", log)
        self.assertIn(str(self.source_dir), log)
        link = self.bin_dir / "attro"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (self.source_dir / "bin" / "attro").resolve())
        self.assertIn("Installed attro launcher", result.stdout)

    def test_bootstrap_forwards_attro_bin_dir(self):
        self.run_bootstrap(("ATTRO_BIN_DIR", str(self.bin_dir)))
        self.assertTrue((self.bin_dir / "attro").is_symlink())

    def test_bootstrap_honors_attro_source_dir(self):
        custom = self.home / "src" / "attro"
        self.run_bootstrap(("ATTRO_SOURCE_DIR", str(custom)))
        self.assertTrue(custom.is_dir())
        self.assertTrue((custom / "install").is_file())
        self.assertFalse(self.source_dir.exists())

    def test_bootstrap_refuses_untrusted_existing_directory(self):
        self.source_dir.mkdir(parents=True)
        sentinel = self.source_dir / "keep-me.txt"
        sentinel.write_text("preserve")
        result = self.run_bootstrap(success=False)
        self.assertIn("refusing to use existing path", result.stderr)
        self.assertEqual(sentinel.read_text(), "preserve")
        self.assertFalse(self.git_log.exists())

    def test_bootstrap_refuses_symlink_target(self):
        real = self.home / "real-checkout"
        real.mkdir()
        self.source_dir.parent.mkdir(parents=True)
        self.source_dir.symlink_to(real)
        result = self.run_bootstrap(success=False)
        self.assertIn("refusing to use symlink path", result.stderr)
        self.assertFalse(self.git_log.exists())

    def test_bootstrap_existing_checkout_does_not_recommend_execution(self):
        self.source_dir.mkdir(parents=True)
        shutil.copy2(INSTALL, self.source_dir / "install")
        (self.source_dir / "install").chmod(0o755)
        (self.source_dir / ".git").mkdir()
        result = self.run_bootstrap(success=False)
        self.assertIn("refusing to use existing path", result.stderr)
        self.assertNotIn("&& ./install", result.stderr)
        self.assertFalse(self.git_log.exists())

    def test_bootstrap_expands_tilde_and_accepts_spaces(self):
        self.run_bootstrap(("ATTRO_SOURCE_DIR", "~/source with spaces/attro"),
                           ("ATTRO_BIN_DIR", "~/bin with spaces"))
        source = self.home / "source with spaces/attro"
        self.assertTrue((source / "install").is_file())
        self.assertEqual((self.home / "bin with spaces/attro").resolve(),
                         source / "bin/attro")

    def test_bootstrap_relative_destination_ignores_cdpath(self):
        foreign = self.base / "foreign"
        (foreign / "source").mkdir(parents=True)
        installer = foreign / "source/install"
        installer.write_text("#!/bin/sh\necho wrong-installer >&2\nexit 41\n")
        installer.chmod(0o755)
        self.run_bootstrap(("ATTRO_SOURCE_DIR", "source"), ("CDPATH", str(foreign)))
        self.assertEqual((self.bin_dir / "attro").resolve(), self.base / "source/bin/attro")

    def test_bootstrap_missing_git_fails_before_clone(self):
        minimal = self.base / "minimal-path"
        minimal.mkdir()
        for helper in ("python3", "uname", "node", "npm"):
            source = self.fake_bin / helper
            if source.exists():
                (minimal / helper).symlink_to(source.resolve())
        result = self.run_bootstrap(("PATH", str(minimal)), success=False)
        self.assertIn("required command not found: git", result.stderr)
        self.assertFalse(self.source_dir.exists())

    def test_bootstrap_old_node_fails_before_clone(self):
        result = self.run_bootstrap(("FAKE_NODE_FAIL_VERSION", "1"), success=False)
        self.assertIn("Node 22.19.0+ required", result.stderr)
        self.assertFalse(self.source_dir.exists())

    def test_bootstrap_piped_invocation_succeeds(self):
        self.run_bootstrap(pipe=True)


if __name__ == "__main__":
    unittest.main()
