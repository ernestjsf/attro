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
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from attro.lock import OperationBusy, operation_lock
from attro.paths import release_dir, repo_root, safe_child, validate_state_root
from attro.validate import ValidationError

LEASE_NAME = ".attro-lease"
REAPER_LOCK_NAME = ".retention-reaper.lock"
REAPER_INTERVAL = 7.0
_ROUTINE_IN_USE_RETENTION_MARKERS = (
    ": running session holds its lease",
    ": still used by a process",
)
_reapers: list[subprocess.Popen] = []


def filter_launch_retention_warnings(warnings: list[str]) -> list[str]:
    """Drop expected in-use retention notices during ordinary managed launch."""
    filtered: list[str] = []
    for warning in warnings:
        if warning.startswith("retaining ") and any(marker in warning for marker in _ROUTINE_IN_USE_RETENTION_MARKERS):
            continue
        filtered.append(warning)
    return filtered


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


def _remove_record(state_root: Path, release_id: str) -> None:
    from attro.state import load_state, save_state

    state = load_state(state_root)
    del state["releases"][release_id]
    if state["previous"] == release_id:
        state["previous"] = None
    save_state(state_root, state)


def _delete_one(state_root: Path, release_id: str) -> tuple[str | None, bool]:
    from attro.state import load_state, prepared_manifest, save_state

    state = load_state(state_root)
    if release_id == state["active"]:
        return None, False
    entry = state["releases"][release_id]
    path = release_dir(release_id, state_root)
    if entry.get("deleting") and not path.exists():
        _remove_record(state_root, release_id)
        return None, False
    if safe_child(path, "agent").exists():
        return f"retaining {release_id}: per-release user data requires manual handling", False
    try:
        with release_lease(path, exclusive=True):
            metadata = path.stat()
            identity = [metadata.st_dev, metadata.st_ino]
            if entry.get("deleting"):
                if entry["deletionIdentity"] != identity:
                    return f"retaining {release_id}: directory identity changed during cleanup", False
            else:
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
            if not entry.get("deleting"):
                entry.update(deleting=True, retention="retired", deletionIdentity=identity)
                if state["previous"] == release_id:
                    state["previous"] = None
                save_state(state_root, state)
            shutil.rmtree(path)
            _remove_record(state_root, release_id)
    except LeaseBusy:
        return f"retaining {release_id}: running session holds its lease", True
    return None, False


def reconcile_releases(state_root: Path) -> CleanupResult:
    """Caller holds operation_lock, including throughout deletion and registry saves."""
    from attro.state import load_state

    state = load_state(state_root)
    result = CleanupResult()
    for rid, entry in state["releases"].items():
        if rid == state["active"] or entry.get("retention") != "retired":
            continue
        try:
            warning, retryable = _delete_one(state_root, rid)
        except ValidationError as exc:
            warning, retryable = f"retaining {rid}: {exc}", False
        except OSError as exc:
            warning, retryable = f"retaining {rid}: cleanup deferred ({exc})", True
        if warning:
            result.warnings.append(warning)
        result.retryable |= retryable
    return result


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
        if result.retryable and not start_reaper(state_root):
            result.warnings.append("cleanup process could not start; a later operation will retry")
        return result.warnings
    except (OSError, ValidationError) as exc:
        return [f"release cleanup deferred: {exc}"]


def _reaper_main(state_root: Path) -> int:
    root = validate_state_root(state_root)
    fd = _open_lock(safe_child(root, REAPER_LOCK_NAME))
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        while root.is_dir():
            try:
                with operation_lock(root):
                    result = reconcile_releases(root)
                    if not result.retryable:
                        # Release the singleton before another operation can add work.
                        os.close(fd)
                        fd = -1
                        return 0
            except OperationBusy:
                pass
            except (OSError, ValidationError):
                return 1
            time.sleep(REAPER_INTERVAL)
        return 0
    finally:
        if fd >= 0:
            os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reaper", type=Path, required=True)
    args = parser.parse_args(argv)
    return _reaper_main(args.reaper)


if __name__ == "__main__":
    raise SystemExit(main())
