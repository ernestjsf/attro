"""Latest-only release retention without supervising the foreground Pi process."""

from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import stat
import subprocess
import sys
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from attro.lock import OperationBusy, operation_lock
from attro.paths import release_dir, repo_root, safe_child, validate_state_root
from attro.profile import session_archive_days, shared_agent_dir, validate_shared_agent
from attro.validate import ValidationError

LEASE_NAME = ".attro-lease"
REAPER_LOCK_NAME = ".retention-reaper.lock"
PENDING_NAME = ".retention-pending"
ARCHIVE_STAMP_NAME = ".sessions-archived"
ARCHIVE_DIR_NAME = "sessions-archive"
ARCHIVE_INTERVAL = 24 * 3600
REAPER_INTERVAL = 7.0
_reapers: list[subprocess.Popen] = []


class LeaseBusy(Exception):
    pass


@dataclass
class ReleaseLease:
    fd: int


@dataclass
class CleanupResult:
    warnings: list[str] = field(default_factory=list)
    retryable: bool = False


def _open_lock(path: Path) -> int:
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        os.close(fd)
        raise ValidationError(f"lock must be an unaliased regular file: {path}")
    return fd


@contextmanager
def release_lease(release_path: Path, *, exclusive: bool = False, inheritable: bool = False) -> Iterator[ReleaseLease]:
    if release_path.is_symlink() or not release_path.is_dir():
        raise ValidationError(f"release missing or symlinked: {release_path}")
    fd = _open_lock(safe_child(release_path, LEASE_NAME))
    try:
        mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        try:
            fcntl.flock(fd, mode | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LeaseBusy(str(release_path)) from exc
        os.set_inheritable(fd, inheritable)
        yield ReleaseLease(fd)
    finally:
        # Explicit LOCK_UN would also unlock a descriptor inherited by Pi.
        os.close(fd)


def _path_mentioned(text: str, release_root: str) -> bool:
    position = text.find(release_root)
    while position >= 0:
        end = position + len(release_root)
        if end == len(text) or text[end] in "/\x00\t\n\r \"'":
            return True
        position = text.find(release_root, position + 1)
    return False


def _inspection_env(releases: Path) -> dict[str, str]:
    # A helper must not keep the caller's old release alive through inherited env.
    return {key: value for key, value in os.environ.items() if str(releases) + os.sep not in value}


def scan_processes(release_root: Path) -> tuple[bool, bool]:
    """Best-effort protection for same-user unleased sessions and detached children."""
    if sys.platform not in {"darwin", "linux"}:
        return True, False
    command = ["/bin/ps", "eww", "-axo", "pid=,uid=,command="] if sys.platform == "darwin" else ["/bin/ps", "-ww", "-axo", "pid=,uid=,args="]
    try:
        listing = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10, env=_inspection_env(release_root.parent))
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        return True, False
    if listing.returncode != 0 or not listing.stdout.strip():
        return True, False
    root = str(release_root)
    for line in listing.stdout.splitlines():
        fields = line.split(None, 2)
        try:
            pid, uid = int(fields[0]), int(fields[1])
        except (IndexError, ValueError):
            return True, False
        if pid == os.getpid() or uid != os.getuid():
            continue
        if len(fields) != 3:
            return True, False
        if _path_mentioned(fields[2], root):
            return True, True
        if sys.platform == "linux":
            process = Path("/proc") / str(pid)
            try:
                environment = (process / "environ").read_bytes().decode(errors="replace")
            except FileNotFoundError:
                continue
            except OSError:
                return True, False
            if _path_mentioned(environment, root):
                return True, True
    return False, True


def _remove_record(state_root: Path, release_id: str, checkpoint: dict) -> None:
    """Finalize only our absent, inactive checkpoint; caller holds operation_lock."""
    from attro.state import load_state, save_state

    state = load_state(state_root)
    if (state["active"] == release_id or state["releases"].get(release_id) != checkpoint
            or not checkpoint.get("deleting") or release_dir(release_id, state_root).exists()):
        return
    del state["releases"][release_id]
    if state["previous"] == release_id:
        state["previous"] = None
    save_state(state_root, state)


def _directory_identity(path: Path) -> list[int]:
    metadata = path.lstat()
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValidationError(f"release missing or symlinked: {path}")
    return [metadata.st_dev, metadata.st_ino]


def _delete_one(state_root: Path, release_id: str, entry: dict) -> tuple[str | None, bool]:
    from attro.state import load_state, prepared_manifest, save_state

    with operation_lock(state_root, operation="cleanup"):
        state = load_state(state_root)
        if state["active"] == release_id or state["releases"].get(release_id) != entry:
            return None, False
        path = release_dir(release_id, state_root)
        if entry.get("deleting") and not path.exists():
            _remove_record(state_root, release_id, entry)
            return None, False
        identity = _directory_identity(path)
        if entry.get("deleting") and entry["deletionIdentity"] != identity:
            return f"retaining {release_id}: directory identity changed during cleanup", False
        if safe_child(path, "agent").exists():
            return f"retaining {release_id}: per-release user data requires manual handling", False

    if not entry.get("deleting"):
        manifest = prepared_manifest(path, release_id)
        if manifest.get("agentMode") != "shared-v1":
            return f"retaining {release_id}: legacy user state requires manual handling", False
    protected, succeeded = scan_processes(path)
    if not succeeded:
        return f"retaining {release_id}: process inspection unavailable; cleanup deferred", True
    if protected:
        return f"retaining {release_id}: still used by a process", True
    if not getattr(shutil.rmtree, "avoids_symlink_attacks", False):
        return f"retaining {release_id}: symlink-resistant deletion unavailable", False

    try:
        with ExitStack() as leases:
            with operation_lock(state_root, operation="cleanup"):
                state = load_state(state_root)
                current = state["releases"].get(release_id)
                if state["active"] == release_id or current != entry:
                    return None, False
                path = release_dir(release_id, state_root)
                if _directory_identity(path) != identity:
                    return f"retaining {release_id}: directory identity changed during cleanup", False
                if safe_child(path, "agent").exists():
                    return f"retaining {release_id}: per-release user data requires manual handling", False
                # Do not exclude reactivation or trial launches during slow inspection.
                leases.enter_context(release_lease(path, exclusive=True))
                checkpoint = {**entry, "deleting": True, "retention": "retired", "deletionIdentity": identity}
                state["releases"][release_id] = checkpoint
                if state["previous"] == release_id:
                    state["previous"] = None
                save_state(state_root, state)
            # A completed trial may have left an unleased child after the first scan.
            # The checkpoint now excludes new managed launches; inspect off-lock.
            protected, succeeded = scan_processes(path)
            if not succeeded:
                return f"retaining {release_id}: process inspection unavailable; cleanup deferred", True
            if protected:
                return f"retaining {release_id}: still used by a process", True
            # The permanent cleaner mutex survives removal of the release lease inode.
            path = release_dir(release_id, state_root)
            if _directory_identity(path) != identity:
                return f"retaining {release_id}: directory identity changed during cleanup", False
            if safe_child(path, "agent").exists():
                return f"retaining {release_id}: per-release user data requires manual handling", False
            shutil.rmtree(path)
            with operation_lock(state_root, operation="cleanup"):
                _remove_record(state_root, release_id, checkpoint)
    except LeaseBusy:
        return f"retaining {release_id}: running session holds its lease", True
    return None, False


def _cleanup_pass(state_root: Path) -> CleanupResult:
    from attro.state import load_state

    with operation_lock(state_root, operation="cleanup"):
        state = load_state(state_root)
        safe_child(state_root, PENDING_NAME).unlink(missing_ok=True)
    result = CleanupResult()
    for rid, entry in state["releases"].items():
        if rid == state["active"] or entry.get("retention") != "retired":
            continue
        try:
            warning, retryable = _delete_one(state_root, rid, entry)
        except (OperationBusy, OSError) as exc:
            warning, retryable = f"retaining {rid}: cleanup deferred ({exc})", True
        except ValidationError as exc:
            warning, retryable = f"retaining {rid}: {exc}", False
        if warning:
            result.warnings.append(warning)
        result.retryable |= retryable
    return result


def _archive_due(state_root: Path) -> bool:
    agent = shared_agent_dir(state_root)
    if session_archive_days(agent) == 0 or not (agent / "sessions").is_dir():
        return False
    try:
        return time.time() - safe_child(state_root, ARCHIVE_STAMP_NAME).stat().st_mtime > ARCHIVE_INTERVAL
    except FileNotFoundError:
        return True


def archive_sessions(state_root: Path, *, now: float | None = None) -> int:
    """Move session files idle for sessionArchiveDays to <state>/sessions-archive/<same relative path>."""
    agent = validate_shared_agent(state_root, required=False)
    days = session_archive_days(agent)
    if days == 0:
        return 0
    stamp = safe_child(state_root, ARCHIVE_STAMP_NAME)
    os.close(_open_lock(stamp))
    os.utime(stamp)
    sessions = agent / "sessions"
    if not sessions.is_dir():
        return 0
    cutoff = (time.time() if now is None else now) - days * 86400
    archive = safe_child(state_root, ARCHIVE_DIR_NAME)
    moved = 0
    for source in sessions.rglob("*.jsonl"):
        try:
            metadata = source.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_mtime >= cutoff:
                continue
            target = safe_child(archive, *source.relative_to(sessions).parts)
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.rename(source, target)
            moved += 1
        except (OSError, ValidationError):
            continue
    return moved


def request_cleanup(state_root: Path) -> list[str]:
    """Request background work only. Caller holds operation_lock through spawning."""
    from attro.state import load_state

    try:
        state = load_state(state_root)
        if not any(rid != state["active"] and entry.get("retention") == "retired"
                   for rid, entry in state["releases"].items()) and not _archive_due(state_root):
            return []
        os.close(_open_lock(safe_child(state_root, PENDING_NAME)))
        if not start_reaper(state_root):
            return ["cleanup process could not start; a later operation will retry"]
        return []
    except (OSError, ValidationError) as exc:
        return [f"release cleanup deferred: {exc}"]


def _run_cleanup(state_root: Path, *, background: bool = False) -> CleanupResult:
    # All cleaners share the old reaper's permanent mutex, never a deleted inode.
    fd = _open_lock(safe_child(state_root, REAPER_LOCK_NAME))
    result = CleanupResult()
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if not background:
                while True:
                    try:
                        with operation_lock(state_root, operation="cleanup"):
                            result.warnings = request_cleanup(state_root)
                        break
                    except OperationBusy:
                        time.sleep(REAPER_INTERVAL)
            return result
        try:
            while True:
                try:
                    result = _cleanup_pass(state_root)
                except OperationBusy:
                    time.sleep(REAPER_INTERVAL)
                    continue
                if not background:
                    return result
                while True:
                    try:
                        with operation_lock(state_root, operation="cleanup"):
                            pending = safe_child(state_root, PENDING_NAME).exists()
                            if not pending and not result.retryable:
                                os.close(fd)
                                fd = -1
                                return result
                        break
                    except OperationBusy:
                        time.sleep(REAPER_INTERVAL)
                if not pending:
                    time.sleep(REAPER_INTERVAL)
        finally:
            # Requests and singleton release are ordered by the operations lock.
            # A losing requester either leaves pending work or spawns the next owner.
            while fd >= 0:
                try:
                    with operation_lock(state_root, operation="cleanup"):
                        pending = safe_child(state_root, PENDING_NAME).exists()
                        os.close(fd)
                        fd = -1
                        if pending or result.retryable:
                            result.warnings.extend(request_cleanup(state_root))
                    break
                except OperationBusy:
                    time.sleep(REAPER_INTERVAL)
    finally:
        if fd >= 0:
            os.close(fd)


def reconcile_releases(state_root: Path) -> CleanupResult:
    """Run one serialized cleanup pass without an outer operation_lock."""
    return _run_cleanup(state_root)


def start_reaper(state_root: Path) -> bool:
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "attro.retention", "--reaper", str(state_root)],
            cwd=repo_root(),
            env=_inspection_env(state_root / "releases"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
    except OSError:
        return False
    _reapers[:] = [child for child in _reapers if child.poll() is None]
    _reapers.append(process)
    return True


def reconcile_and_maybe_reap(state_root: Path) -> list[str]:
    # Retention must not turn an already committed activation into a failed install.
    try:
        result = reconcile_releases(state_root)
        return result.warnings
    except (OSError, ValidationError) as exc:
        return [f"release cleanup deferred: {exc}"]


def _reaper_main(state_root: Path) -> int:
    try:
        root = validate_state_root(state_root)
        try:
            archive_sessions(root)
        except (OSError, ValidationError):
            pass  # archiving is best effort and must not block release cleanup
        _run_cleanup(root, background=True)
        return 0
    except (OSError, ValidationError):
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reaper", type=Path, required=True)
    args = parser.parse_args(argv)
    return _reaper_main(args.reaper)


if __name__ == "__main__":
    raise SystemExit(main())
