"""Regression tests for automatic release retention."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from attro.cli import main
from attro.lock import OperationBusy, operation_lock
from attro.retention import LeaseBusy, _reaper_main, _reapers, reconcile_releases, release_lease, start_reaper
from attro.state import activate_release, load_state, register_release, save_state
from attro.validate import ValidationError
from test_attro_activation import _write_release


class RetentionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.state = self.base / "managed"
        self.state.mkdir()
        self.addCleanup(self._stop_reapers)

    def _stop_reapers(self) -> None:
        for process in list(_reapers):
            if isinstance(process.args, list) and str(self.state) in process.args:
                self._stop_process(process)
                _reapers.remove(process)

    def _stop_process(self, process: subprocess.Popen) -> None:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def _wait_removed(self, release: Path) -> None:
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if not release.exists() and release.name not in load_state(self.state)["releases"]:
                return
            time.sleep(0.1)
        self.fail(f"automatic cleanup did not finish for {release.name}")

    def _prunable(self, release_id: str, marker: str) -> Path:
        release = _write_release(self.state, release_id, marker=marker)
        agent = release / "agent"
        if agent.exists():
            shutil.rmtree(agent)
        return release

    def cli(self, *args: str, success: bool = True) -> tuple[str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(["--state-root", str(self.state), *args])
        if success:
            self.assertEqual(result, 0, stderr.getvalue())
        else:
            self.assertNotEqual(result, 0, stdout.getvalue())
        return stdout.getvalue(), stderr.getvalue()

    def _sleep_cli(self) -> Path:
        script = self.base / "sleep-cli.py"
        script.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys, time\n"
            "print('ready', flush=True)\n"
            "time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 60)\n"
        )
        script.chmod(0o755)
        return script

    def test_activate_prunes_idle_retired_and_preserves_shared_agent(self) -> None:
        a = self._prunable("attro-0.1.0-aaaaaaaaaaaa", "a")
        b = self._prunable("attro-0.1.0-bbbbbbbbbbbb", "b")
        register_release(self.state, a.name, a)
        register_release(self.state, b.name, b)
        activate_release(self.state, a.name)
        agent = self.state / "agent"
        sentinel = agent / "settings.json"
        before_agent = sentinel.read_bytes()
        self.cli("activate", b.name)
        state = load_state(self.state)
        self.assertEqual(state["active"], b.name)
        self.assertNotIn(a.name, state["releases"])
        self.assertFalse(a.exists())
        self.assertEqual(sentinel.read_bytes(), before_agent)

    def test_register_idempotent_and_one_staged_candidate(self) -> None:
        a = self._prunable("attro-0.1.0-aaaaaaaaaaaa", "a")
        b = self._prunable("attro-0.1.0-bbbbbbbbbbbb", "b")
        c = self._prunable("attro-0.1.0-cccccccccccc", "c")
        register_release(self.state, a.name, a)
        activate_release(self.state, a.name)
        register_release(self.state, b.name, b)
        register_release(self.state, b.name, b)
        state = load_state(self.state)
        self.assertEqual(state["releases"][b.name]["retention"], "candidate")
        register_release(self.state, c.name, c)
        state = load_state(self.state)
        self.assertEqual(state["releases"][b.name]["retention"], "retired")
        self.assertEqual(state["releases"][c.name]["retention"], "candidate")

    def test_rollback_refused_when_previous_pruned(self) -> None:
        a = self._prunable("attro-0.1.0-aaaaaaaaaaaa", "a")
        b = self._prunable("attro-0.1.0-bbbbbbbbbbbb", "b")
        register_release(self.state, a.name, a)
        register_release(self.state, b.name, b)
        activate_release(self.state, a.name)
        self.cli("activate", b.name)
        _, error = self.cli("rollback", success=False)
        self.assertIn("no previous release", error)
        state = load_state(self.state)
        self.assertEqual(state["active"], b.name)
        self.assertIsNone(state["previous"])

    def test_dry_run_exec_has_no_retention_side_effects(self) -> None:
        release = self._prunable("attro-0.1.0-dryrun000000", "dry")
        register_release(self.state, release.name, release)
        activate_release(self.state, release.name)
        before = {p.relative_to(self.state): p.read_bytes() for p in self.state.rglob("*") if p.is_file()}
        with mock.patch("attro.retention.start_reaper", side_effect=AssertionError("dry-run must not start reaper")):
            self.cli("--json", "exec", "--dry-run", "--", "--version")
        after = {p.relative_to(self.state): p.read_bytes() for p in self.state.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertFalse((release / ".attro-lease").exists())

    def test_launch_refuses_deleting_release(self) -> None:
        retired = self._prunable("attro-0.1.0-deleting0000", "del")
        active = self._prunable("attro-0.1.0-active000001", "live")
        register_release(self.state, retired.name, retired)
        register_release(self.state, active.name, active)
        activate_release(self.state, active.name)
        metadata = retired.stat()
        state = load_state(self.state)
        state["releases"][retired.name].update(
            retention="retired",
            deleting=True,
            deletionIdentity=[metadata.st_dev, metadata.st_ino],
        )
        save_state(self.state, state)
        _, error = self.cli("try", "--release-id", retired.name, "--dry-run", success=False)
        self.assertIn("marked deleting", error)

    def test_legacy_and_per_release_agent_preserved(self) -> None:
        legacy = _write_release(self.state, "piattro-0.1.0-legacy0000", marker="legacy", legacy=True)
        (legacy / "agent/auth.json").write_text('{"preserve":true}')
        register_release(self.state, legacy.name, legacy)
        shared = self._prunable("attro-0.1.0-shared000000", "shared")
        register_release(self.state, shared.name, shared)
        activate_release(self.state, shared.name)
        with operation_lock(self.state):
            result = reconcile_releases(self.state)
        self.assertTrue(legacy.exists())
        joined = " ".join(result.warnings)
        self.assertIn("per-release user data requires manual handling", joined)
        self.assertEqual((legacy / "agent/auth.json").read_text(), '{"preserve":true}')

    def test_process_scan_failure_is_fail_safe(self) -> None:
        retired = self._prunable("attro-0.1.0-retired00000", "old")
        active = self._prunable("attro-0.1.0-active000000", "new")
        register_release(self.state, retired.name, retired)
        register_release(self.state, active.name, active)
        activate_release(self.state, active.name)
        with mock.patch("attro.retention.scan_processes", return_value=(True, False)):
            with operation_lock(self.state):
                result = reconcile_releases(self.state)
        self.assertTrue(retired.exists())
        self.assertTrue(result.retryable)
        self.assertTrue(any("process inspection unavailable" in warning for warning in result.warnings))

    def test_interrupted_delete_marker_retries_without_manifest(self) -> None:
        retired = self._prunable("attro-0.1.0-partial00000", "part")
        active = self._prunable("attro-0.1.0-active000002", "live")
        register_release(self.state, retired.name, retired)
        register_release(self.state, active.name, active)
        activate_release(self.state, active.name)
        calls = {"count": 0}

        def fail_first_rmtree(path: Path, *args: object, **kwargs: object) -> None:
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError("interrupted cleanup")

        with mock.patch("attro.retention.shutil.rmtree", side_effect=fail_first_rmtree):
            with operation_lock(self.state):
                first = reconcile_releases(self.state)
        state = load_state(self.state)
        entry = state["releases"][retired.name]
        self.assertTrue(entry.get("deleting"))
        self.assertEqual(len(entry.get("deletionIdentity", [])), 2)
        self.assertTrue(retired.exists())
        self.assertTrue(first.retryable)
        (retired / "manifest.json").unlink(missing_ok=True)
        shutil.rmtree(retired / "pi", ignore_errors=True)
        with operation_lock(self.state):
            second = reconcile_releases(self.state)
        self.assertEqual(second.warnings, [])
        self.assertFalse(retired.exists())
        self.assertNotIn(retired.name, load_state(self.state)["releases"])

    def test_child_with_release_env_blocks_then_allows_prune(self) -> None:
        retired = self._prunable("attro-0.1.0-child0000000", "child")
        active = self._prunable("attro-0.1.0-holder0000000", "hold")
        register_release(self.state, retired.name, retired)
        register_release(self.state, active.name, active)
        activate_release(self.state, active.name)
        env = {**os.environ, "ATTRO_RELEASE_ROOT": str(retired), "PIATTRO_RELEASE_ROOT": str(retired)}
        child = subprocess.Popen(
            [sys.executable, str(self._sleep_cli()), "20"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        self.addCleanup(self._stop_process, child)
        assert child.stdout is not None
        self.assertEqual(child.stdout.readline().strip(), "ready")
        _, warning = self.cli("activate", active.name)
        self.assertTrue(retired.exists())
        self.assertIn("still used by a process", warning)
        self._stop_process(child)
        self._wait_removed(retired)

    def _exercise_launch(self, mode: str) -> None:
        a = self._prunable("attro-0.1.0-held00000000", "held")
        b = self._prunable("attro-0.1.0-next00000000", "next")
        register_release(self.state, a.name, a)
        activate_release(self.state, a.name)
        pi_bin = a / "pi/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
        pi_bin.write_text("#!/usr/bin/env python3\nimport sys\nprint('ready', flush=True)\nsys.stdin.readline()\nsys.exit(23)\n", encoding="utf-8")
        pi_bin.chmod(0o755)
        holder = subprocess.Popen(
            [sys.executable, "-m", "attro.cli", "--state-root", str(self.state), mode],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self._stop_process, holder)
        assert holder.stdout is not None
        self.assertEqual(holder.stdout.readline().strip(), "ready")
        with self.assertRaises(LeaseBusy):
            with release_lease(a, exclusive=True):
                pass
        with operation_lock(self.state):
            register_release(self.state, b.name, b)
        self.cli("activate", b.name)
        self.assertEqual(load_state(self.state)["active"], b.name)
        self.assertTrue(a.exists())
        self.assertIsNone(holder.poll())
        holder.communicate(input="exit\n", timeout=5)
        self.assertEqual(holder.returncode, 23)
        self._wait_removed(a)

    def test_exec_lease_and_exit_cleanup(self) -> None:
        self._exercise_launch("exec")

    def test_try_lease_and_exit_cleanup(self) -> None:
        self._exercise_launch("try")

    def test_start_reaper_uses_detached_stdio(self) -> None:
        with mock.patch("attro.retention.subprocess.Popen") as popen, mock.patch("attro.retention._reapers", []):
            popen.return_value = mock.Mock()
            self.assertTrue(start_reaper(self.state))
            kwargs = popen.call_args.kwargs
            self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
            self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
            self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
            self.assertTrue(kwargs["close_fds"])
            self.assertTrue(kwargs["start_new_session"])

    def test_reaper_cleans_retired_release(self) -> None:
        retired = self._prunable("attro-0.1.0-reaper000000", "reap")
        register_release(self.state, retired.name, retired)
        state = load_state(self.state)
        state["releases"][retired.name]["retention"] = "retired"
        save_state(self.state, state)
        process = subprocess.Popen(
            [sys.executable, "-m", "attro.retention", "--reaper", str(self.state)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.addCleanup(self._stop_process, process)
        output, error = process.communicate(timeout=20)
        self.assertEqual(process.returncode, 0, error)
        self.assertEqual(output, b"")
        self.assertFalse(retired.exists())
        self.assertNotIn(retired.name, load_state(self.state)["releases"])

    def _retired_pair(self) -> tuple[Path, Path]:
        old = self._prunable("attro-0.1.0-old000000000", "old")
        active = self._prunable("attro-0.1.0-live00000000", "active")
        register_release(self.state, old.name, old)
        activate_release(self.state, old.name)
        register_release(self.state, active.name, active)
        activate_release(self.state, active.name)
        return old, active

    def test_checkpoint_failure_keeps_code_and_successful_activation(self) -> None:
        old, active = self._retired_pair()
        original_save = save_state

        def fail_checkpoint(root, state):
            if any(entry.get("deleting") for entry in state["releases"].values()):
                raise OSError("checkpoint unavailable")
            original_save(root, state)

        with mock.patch("attro.state.save_state", side_effect=fail_checkpoint), mock.patch("attro.retention.start_reaper", return_value=False):
            output, _ = self.cli("--json", "activate", active.name)
        self.assertEqual(json.loads(output)["active"], active.name)
        self.assertIn("warnings", json.loads(output))
        self.assertTrue(old.exists())
        self.assertFalse(load_state(self.state)["releases"][old.name].get("deleting"))

    def test_process_decoding_failure_keeps_successful_activation(self) -> None:
        old, active = self._retired_pair()
        error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid process environment")
        with mock.patch("attro.retention.subprocess.run", side_effect=error), mock.patch("attro.retention.start_reaper", return_value=True):
            output, _ = self.cli("--json", "activate", active.name)
        result = json.loads(output)
        self.assertEqual(result["active"], active.name)
        self.assertIn("process inspection unavailable", " ".join(result["warnings"]))
        self.assertTrue(old.exists())
        self.assertFalse(load_state(self.state)["releases"][old.name].get("deleting"))

    def test_registry_failure_after_removal_is_retryable(self) -> None:
        old, _ = self._retired_pair()
        original_save = save_state

        def fail_final_save(root, state):
            if old.name not in state["releases"]:
                raise OSError("registry unavailable")
            original_save(root, state)

        with mock.patch("attro.state.save_state", side_effect=fail_final_save):
            with operation_lock(self.state):
                result = reconcile_releases(self.state)
        self.assertTrue(result.retryable)
        self.assertFalse(old.exists())
        self.assertTrue(load_state(self.state)["releases"][old.name]["deleting"])
        with operation_lock(self.state):
            self.assertEqual(reconcile_releases(self.state).warnings, [])
        self.assertNotIn(old.name, load_state(self.state)["releases"])

    def test_symlinked_release_is_refused_and_nested_link_is_not_followed(self) -> None:
        old, _ = self._retired_pair()
        outside = self.base / "outside"
        outside.mkdir()
        sentinel = outside / "preserve"
        sentinel.write_text("personal data")
        preserved = self.base / "preserved-release"
        old.rename(preserved)
        old.symlink_to(outside, target_is_directory=True)
        with operation_lock(self.state):
            with self.assertRaises(ValidationError):
                reconcile_releases(self.state)
        self.assertEqual(sentinel.read_text(), "personal data")
        old.unlink()
        preserved.rename(old)
        (old / "external-link").symlink_to(outside, target_is_directory=True)
        with operation_lock(self.state):
            self.assertEqual(reconcile_releases(self.state).warnings, [])
        self.assertFalse(old.exists())
        self.assertEqual(sentinel.read_text(), "personal data")

    def test_deleting_directory_replacement_is_preserved(self) -> None:
        old, _ = self._retired_pair()
        with mock.patch("attro.retention.shutil.rmtree", side_effect=OSError("interrupted")):
            with operation_lock(self.state):
                reconcile_releases(self.state)
        old.rename(self.base / "interrupted-release")
        old.mkdir()
        sentinel = old / "preserve"
        sentinel.write_text("replacement data")
        with operation_lock(self.state):
            result = reconcile_releases(self.state)
        self.assertIn("directory identity changed", " ".join(result.warnings))
        self.assertEqual(sentinel.read_text(), "replacement data")
        self.assertFalse(result.retryable)

    def test_reaper_retries_operation_contention(self) -> None:
        old, _ = self._retired_pair()
        calls = 0

        def contend_once(root):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OperationBusy("another Attro operation is already running")
            return operation_lock(root)

        with mock.patch("attro.retention.operation_lock", side_effect=contend_once), mock.patch("attro.retention.time.sleep"):
            self.assertEqual(_reaper_main(self.state), 0)
        self.assertEqual(calls, 2)
        self.assertFalse(old.exists())


if __name__ == "__main__":
    unittest.main()
