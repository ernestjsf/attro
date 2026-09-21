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
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from attro.cli import main
from attro.lock import OperationBusy, operation_lock
from attro.retention import (
    LeaseBusy,
    _reaper_main,
    _reapers,
    PENDING_NAME,
    REAPER_LOCK_NAME,
    request_cleanup,
    reconcile_releases,
    release_lease,
    start_reaper,
)
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
        with mock.patch("attro.retention.scan_processes", return_value=(True, False)), mock.patch("attro.retention.start_reaper", return_value=True):
            result = reconcile_releases(self.state)
        self.assertTrue(retired.exists())
        self.assertTrue(result.retryable)
        self.assertTrue(any("process inspection unavailable" in warning for warning in result.warnings))

    def test_postcheckpoint_scan_failure_keeps_checkpoint_for_retry(self) -> None:
        old, _ = self._retired_pair()
        with mock.patch("attro.retention.scan_processes", side_effect=[(False, True), (True, False)]), mock.patch(
            "attro.retention.start_reaper", return_value=True
        ):
            result = reconcile_releases(self.state)
        self.assertTrue(old.exists())
        self.assertTrue(result.retryable)
        self.assertIn("process inspection unavailable", " ".join(result.warnings))
        checkpoint = load_state(self.state)["releases"][old.name]
        self.assertTrue(checkpoint["deleting"])
        self.assertEqual(checkpoint["deletionIdentity"], [old.stat().st_dev, old.stat().st_ino])
        self.assertEqual(reconcile_releases(self.state).warnings, [])
        self.assertFalse(old.exists())

    def test_trial_child_started_after_initial_scan_keeps_release(self) -> None:
        old, _ = self._retired_pair()
        from attro.retention import scan_processes

        run = subprocess.run
        children: list[subprocess.Popen] = []
        scans = 0

        def trial_or_scan(command, **kwargs):
            if command[0] == "/bin/ps":
                return run(command, **kwargs)
            # Model a trial that leaves an env-pinned child but closes its lease.
            child = subprocess.Popen(
                [sys.executable, str(self._sleep_cli()), "20"],
                env=kwargs["env"], close_fds=True, start_new_session=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            children.append(child)
            self.addCleanup(self._stop_process, child)
            assert child.stdout is not None
            self.assertEqual(child.stdout.readline().strip(), "ready")
            return subprocess.CompletedProcess(command, 0)

        def inspect(path):
            nonlocal scans
            scans += 1
            with operation_lock(self.state):
                pass
            if scans == 1:
                result = scan_processes(path)
                self.assertEqual(result, (False, True))
                self.cli("try", "--release-id", old.name)
                with release_lease(old, exclusive=True):
                    pass
                return result
            self.assertTrue(load_state(self.state)["releases"][old.name]["deleting"])
            with self.assertRaises(LeaseBusy):
                with release_lease(old):
                    pass
            return scan_processes(path)

        with mock.patch("attro.retention.scan_processes", side_effect=inspect), mock.patch(
            "attro.cli.subprocess.run", side_effect=trial_or_scan
        ), mock.patch("attro.retention.start_reaper", return_value=True):
            result = reconcile_releases(self.state)
        self.assertTrue(old.exists())
        self.assertEqual(scans, 2)
        self.assertTrue(result.retryable)
        self.assertIn("still used by a process", " ".join(result.warnings))
        self._stop_process(children[0])
        self.assertEqual(reconcile_releases(self.state).warnings, [])
        self.assertFalse(old.exists())

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

        with mock.patch("attro.retention.shutil.rmtree", side_effect=fail_first_rmtree), mock.patch("attro.retention.start_reaper", return_value=True):
            first = reconcile_releases(self.state)
        state = load_state(self.state)
        entry = state["releases"][retired.name]
        self.assertTrue(entry.get("deleting"))
        self.assertEqual(len(entry.get("deletionIdentity", [])), 2)
        self.assertTrue(retired.exists())
        self.assertTrue(first.retryable)
        (retired / "manifest.json").unlink(missing_ok=True)
        shutil.rmtree(retired / "pi", ignore_errors=True)
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

    def _launch_during_cleanup(self, phase: str) -> None:
        old, active = self._retired_pair()
        entered, resume = threading.Event(), threading.Event()
        failures: list[BaseException] = []
        from attro import state as state_module
        from attro import retention

        original = {
            "validation": state_module.prepared_manifest,
            "scan": retention.scan_processes,
            "deletion": shutil.rmtree,
        }[phase]

        def pause(path, *args, **kwargs):
            if path == old:
                entered.set()
                if not resume.wait(5):
                    raise AssertionError("cleanup barrier timed out")
            return original(path, *args, **kwargs)

        def clean() -> None:
            try:
                main(["--state-root", str(self.state), "activate", active.name])
            except BaseException as exc:
                failures.append(exc)

        target = {
            "validation": "attro.state.prepared_manifest",
            "scan": "attro.retention.scan_processes",
            "deletion": "attro.retention.shutil.rmtree",
        }[phase]
        with mock.patch(target, side_effect=pause), mock.patch("attro.retention.start_reaper", return_value=True), mock.patch(
            "attro.cli.exec_pi", return_value=None
        ) as execute, mock.patch("attro.cli.LAUNCH_LOCK_WAIT_SECONDS", 0.15), mock.patch("attro.cli.emit"):
            thread = threading.Thread(target=clean)
            thread.start()
            try:
                self.assertTrue(entered.wait(3), "cleanup never reached barrier")
                self.cli("exec", "--", "--version")
                execute.assert_called_once()
                self.assertTrue(thread.is_alive(), "launch waited for cleanup to finish")
            finally:
                resume.set()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        self.assertFalse(old.exists())

    def test_launch_during_retired_validation(self) -> None:
        self._launch_during_cleanup("validation")

    def test_launch_during_process_scan(self) -> None:
        self._launch_during_cleanup("scan")

    def test_launch_during_deletion(self) -> None:
        self._launch_during_cleanup("deletion")

    def _change_retired_during_inspection(self, action: str) -> None:
        old, _ = self._retired_pair()

        def inspect(path):
            if path == old:
                with operation_lock(self.state):
                    if action == "activate":
                        activate_release(self.state, old.name)
                    else:
                        register_release(self.state, old.name, old)
                    with release_lease(old):
                        pass
            return False, True

        with mock.patch("attro.retention.scan_processes", side_effect=inspect):
            self.assertEqual(reconcile_releases(self.state).warnings, [])
        self.assertTrue(old.exists())
        entry = load_state(self.state)["releases"][old.name]
        self.assertEqual(entry["retention"], "active" if action == "activate" else "candidate")
        self.assertFalse(entry.get("deleting"))

    def test_reactivation_during_inspection_is_preserved(self) -> None:
        self._change_retired_during_inspection("activate")

    def test_reregistration_during_inspection_is_preserved(self) -> None:
        self._change_retired_during_inspection("register")

    def test_replacement_during_inspection_is_preserved(self) -> None:
        old, _ = self._retired_pair()

        def inspect(path):
            old.rename(self.base / "inspected-release")
            old.mkdir()
            (old / "preserve").write_text("replacement")
            return False, True

        with mock.patch("attro.retention.scan_processes", side_effect=inspect):
            result = reconcile_releases(self.state)
        self.assertIn("directory identity changed", " ".join(result.warnings))
        self.assertEqual((old / "preserve").read_text(), "replacement")
        self.assertFalse(load_state(self.state)["releases"][old.name].get("deleting"))

    def test_user_data_added_during_inspection_is_preserved(self) -> None:
        old, _ = self._retired_pair()

        def inspect(path):
            (old / "agent").mkdir()
            (old / "agent/auth.json").write_text("preserve")
            return False, True

        with mock.patch("attro.retention.scan_processes", side_effect=inspect):
            result = reconcile_releases(self.state)
        self.assertIn("per-release user data", " ".join(result.warnings))
        self.assertEqual((old / "agent/auth.json").read_text(), "preserve")

    def test_deleted_lease_path_does_not_admit_second_cleaner_and_finalization_is_fresh(self) -> None:
        old, _ = self._retired_pair()
        candidate = self._prunable("attro-0.1.0-candidate000", "candidate")
        original = shutil.rmtree

        def remove(path, *args, **kwargs):
            if path == old:
                (old / ".attro-lease").unlink()
                with mock.patch("attro.retention.scan_processes", side_effect=AssertionError("second cleaner entered")):
                    reconcile_releases(self.state)
                    self.assertEqual(_reaper_main(self.state), 0)
                with operation_lock(self.state):
                    register_release(self.state, candidate.name, candidate)
            original(path, *args, **kwargs)

        with mock.patch("attro.retention.shutil.rmtree", side_effect=remove), mock.patch("attro.retention.start_reaper", return_value=True):
            result = reconcile_releases(self.state)
        self.assertEqual(result.warnings, [])
        self.assertFalse(old.exists())
        self.assertEqual(load_state(self.state)["releases"][candidate.name]["retention"], "candidate")

    def _request_during_pass(self, background: bool) -> None:
        old, active = self._retired_pair()
        later = self._prunable("attro-0.1.0-later0000000", "later")
        original = shutil.rmtree

        def remove(path, *args, **kwargs):
            original(path, *args, **kwargs)
            if path == old:
                with operation_lock(self.state):
                    register_release(self.state, later.name, later)
                    activate_release(self.state, active.name)
                    self.assertEqual(request_cleanup(self.state), [])
                # The request's child loses the singleton; the owner must notice it.
                self.assertEqual(_reaper_main(self.state), 0)

        with mock.patch("attro.retention.shutil.rmtree", side_effect=remove), mock.patch("attro.retention.start_reaper", return_value=True) as spawn:
            if background:
                self.assertEqual(_reaper_main(self.state), 0)
                self.assertEqual(spawn.call_count, 1)
            else:
                reconcile_releases(self.state)
                self.assertEqual(spawn.call_count, 2, "sync owner must spawn a successor after releasing its mutex")
                self.assertTrue(later.exists())
                self.assertEqual(_reaper_main(self.state), 0)
        self.assertFalse(later.exists())
        self.assertFalse((self.state / PENDING_NAME).exists())

    def test_background_owner_consumes_request_during_pass(self) -> None:
        self._request_during_pass(True)

    def test_synchronous_owner_hands_off_request_during_pass(self) -> None:
        self._request_during_pass(False)

    def test_contending_manager_retries_cleanup_handoff_after_operation_contention(self) -> None:
        old, active = self._retired_pair()
        later = self._prunable("attro-0.1.0-later0000000", "later")
        with operation_lock(self.state):
            register_release(self.state, later.name, later)
        removing, finish_owner = threading.Event(), threading.Event()
        manager_locked, finish_manager, manager_released = threading.Event(), threading.Event(), threading.Event()
        failures: list[BaseException] = []
        original_remove = shutil.rmtree
        from attro.retention import reconcile_and_maybe_reap

        def remove(path, *args, **kwargs):
            if path == old:
                removing.set()
                if not finish_owner.wait(5):
                    raise AssertionError("owner barrier timed out")
            original_remove(path, *args, **kwargs)

        def owner():
            try:
                reconcile_releases(self.state)
            except BaseException as exc:
                failures.append(exc)

        def manager():
            try:
                with operation_lock(self.state, operation="setup"):
                    manager_locked.set()
                    if not finish_manager.wait(5):
                        raise AssertionError("manager barrier timed out")
            except BaseException as exc:
                failures.append(exc)
            finally:
                manager_released.set()

        def handoff(root):
            manager_thread = threading.Thread(target=manager)
            manager_thread.start()
            try:
                self.assertTrue(manager_locked.wait(3))
                return reconcile_and_maybe_reap(root)
            finally:
                finish_manager.set()
                manager_thread.join(5)

        def retry(_interval):
            finish_manager.set()
            self.assertTrue(manager_released.wait(3))

        with mock.patch("attro.retention.shutil.rmtree", side_effect=remove), mock.patch(
            "attro.retention.start_reaper", return_value=True
        ) as spawn, mock.patch("attro.cli.reconcile_and_maybe_reap", side_effect=handoff), mock.patch(
            "attro.retention.time.sleep", side_effect=retry
        ) as sleep:
            cleaner = threading.Thread(target=owner)
            cleaner.start()
            try:
                self.assertTrue(removing.wait(3))
                _, warning = self.cli("activate", later.name)
                self.assertEqual(warning, "")
                sleep.assert_called()
                self.assertTrue((self.state / PENDING_NAME).exists())
            finally:
                finish_owner.set()
                cleaner.join(5)
            self.assertFalse(cleaner.is_alive())
            self.assertEqual(spawn.call_count, 2, "contender requests work and owner spawns successor")
        self.assertEqual(failures, [])
        self.assertTrue(active.exists())
        self.assertEqual(_reaper_main(self.state), 0)
        self.assertFalse(active.exists())
        self.assertTrue(later.exists())
        self.assertFalse((self.state / PENDING_NAME).exists())

    def test_request_at_owner_exit_starts_successor(self) -> None:
        old, active = self._retired_pair()
        later = self._prunable("attro-0.1.0-later0000000", "later")
        exiting, resume = threading.Event(), threading.Event()
        original_close = os.close
        failures: list[BaseException] = []

        def close(fd):
            metadata = os.fstat(fd)
            mutex = self.state / REAPER_LOCK_NAME
            if mutex.exists() and metadata.st_ino == mutex.stat().st_ino and not exiting.is_set():
                exiting.set()
                if not resume.wait(5):
                    raise AssertionError("exit barrier timed out")
            original_close(fd)

        def owner():
            try:
                self.assertEqual(_reaper_main(self.state), 0)
            except BaseException as exc:
                failures.append(exc)

        def request():
            try:
                with operation_lock(self.state, wait_timeout=3):
                    register_release(self.state, later.name, later)
                    activate_release(self.state, active.name)
                    self.assertEqual(request_cleanup(self.state), [])
            except BaseException as exc:
                failures.append(exc)

        with mock.patch("attro.retention.os.close", side_effect=close), mock.patch("attro.retention.start_reaper", return_value=True) as spawn:
            cleaner = threading.Thread(target=owner)
            cleaner.start()
            try:
                self.assertTrue(exiting.wait(3))
                with self.assertRaises(OperationBusy):
                    with operation_lock(self.state):
                        pass
                requester = threading.Thread(target=request)
                requester.start()
            finally:
                resume.set()
                cleaner.join(5)
            requester.join(5)
            self.assertFalse(cleaner.is_alive())
            self.assertFalse(requester.is_alive())
            spawn.assert_called_once_with(self.state)
        self.assertEqual(failures, [])
        self.assertFalse(old.exists())
        self.assertTrue((self.state / PENDING_NAME).exists())
        self.assertEqual(_reaper_main(self.state), 0)
        self.assertFalse(later.exists())

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

        with mock.patch("attro.state.save_state", side_effect=fail_final_save), mock.patch("attro.retention.start_reaper", return_value=True):
            result = reconcile_releases(self.state)
        self.assertTrue(result.retryable)
        self.assertFalse(old.exists())
        self.assertTrue(load_state(self.state)["releases"][old.name]["deleting"])
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
        with self.assertRaises(ValidationError):
            reconcile_releases(self.state)
        self.assertEqual(sentinel.read_text(), "personal data")
        old.unlink()
        preserved.rename(old)
        (old / "external-link").symlink_to(outside, target_is_directory=True)
        self.assertEqual(reconcile_releases(self.state).warnings, [])
        self.assertFalse(old.exists())
        self.assertEqual(sentinel.read_text(), "personal data")

    def test_deleting_directory_replacement_is_preserved(self) -> None:
        old, _ = self._retired_pair()
        with mock.patch("attro.retention.shutil.rmtree", side_effect=OSError("interrupted")), mock.patch("attro.retention.start_reaper", return_value=True):
            reconcile_releases(self.state)
        old.rename(self.base / "interrupted-release")
        old.mkdir()
        sentinel = old / "preserve"
        sentinel.write_text("replacement data")
        result = reconcile_releases(self.state)
        self.assertIn("directory identity changed", " ".join(result.warnings))
        self.assertEqual(sentinel.read_text(), "replacement data")
        self.assertFalse(result.retryable)

    def test_reaper_retries_operation_contention(self) -> None:
        old, _ = self._retired_pair()
        calls = 0

        def contend_once(root, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OperationBusy("another Attro operation is already running")
            return operation_lock(root, **kwargs)

        with mock.patch("attro.retention.operation_lock", side_effect=contend_once), mock.patch("attro.retention.time.sleep"):
            self.assertEqual(_reaper_main(self.state), 0)
        self.assertGreaterEqual(calls, 2)
        self.assertFalse(old.exists())

    def test_operation_lock_wait_timeout(self) -> None:
        with operation_lock(self.state, operation="cleanup"):
            start = time.monotonic()
            with self.assertRaises(OperationBusy) as error:
                with operation_lock(self.state, wait_timeout=0.15):
                    pass
            self.assertGreaterEqual(time.monotonic() - start, 0.1)
            self.assertIn(f"recorded owner: cleanup, PID {os.getpid()}", str(error.exception))

    def test_operation_busy_metadata_is_bounded_and_sanitized(self) -> None:
        with operation_lock(self.state):
            path = self.state / ".operations.lock"
            for payload in ({"pid": 123, "operation": "setup\\nunsafe"}, {"pid": True, "operation": []}, {"pid": 123, "operation": "x" * 2000}):
                path.write_text(json.dumps(payload))
                with self.assertRaises(OperationBusy) as error:
                    with operation_lock(self.state):
                        pass
                message = str(error.exception)
                self.assertLess(len(message), 150)
                self.assertNotIn("unsafe", message)
                self.assertNotIn("True", message)
            path.write_text('{"pid": 123}')
            with self.assertRaisesRegex(OperationBusy, "PID 123"):
                with operation_lock(self.state):
                    pass

    def test_operation_lock_bounded_wait_acquires(self) -> None:
        acquired = threading.Event()

        def holder() -> None:
            with operation_lock(self.state):
                acquired.set()
                time.sleep(0.3)

        thread = threading.Thread(target=holder)
        thread.start()
        self.addCleanup(thread.join)
        self.assertTrue(acquired.wait(timeout=2))
        start = time.monotonic()
        with operation_lock(self.state, wait_timeout=2.0):
            elapsed = time.monotonic() - start
        self.assertGreaterEqual(elapsed, 0.05)
        self.assertLess(elapsed, 1.5)

    def test_launch_only_schedules_cleanup_and_reports_spawn_failure(self) -> None:
        release = self._prunable("attro-0.1.0-launch00000", "launch")
        register_release(self.state, release.name, release)
        activate_release(self.state, release.name)
        pi_bin = release / "pi/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
        pi_bin.parent.mkdir(parents=True, exist_ok=True)
        pi_bin.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n", encoding="utf-8")
        pi_bin.chmod(0o755)
        old = self._prunable("attro-0.1.0-old000000000", "old")
        register_release(self.state, old.name, old)
        activate_release(self.state, release.name)
        with mock.patch("attro.cli.reconcile_and_maybe_reap", side_effect=AssertionError("launch must not clean inline")), mock.patch(
            "attro.retention.scan_processes", side_effect=AssertionError("launch must not scan")
        ), mock.patch("attro.retention.start_reaper", return_value=False) as spawn, mock.patch("attro.cli.exec_pi", return_value=None):
            _, stderr = self.cli("exec", "--", "--version")
        spawn.assert_called_once_with(self.state)
        self.assertIn("cleanup process could not start", stderr)
        self.assertTrue(old.exists())
        self.assertTrue((self.state / PENDING_NAME).exists())


if __name__ == "__main__":
    unittest.main()
