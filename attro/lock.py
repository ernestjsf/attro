"""Cross-process operation locking."""

from __future__ import annotations

import json
import os
import stat
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from attro.paths import lock_path
from attro.validate import ValidationError


class OperationBusy(ValidationError):
    pass


LAUNCH_LOCK_WAIT_SECONDS = 5.0
_LOCK_POLL_INTERVAL = 0.05
_OPERATIONS = frozenset({"operation", "setup", "update", "activate", "rollback", "launch", "try", "exec", "cleanup"})


def _busy_message(fd: int) -> str:
    message = "another Attro operation is already running"
    try:
        owner = json.loads(os.pread(fd, 1024, 0))
        if not isinstance(owner, dict):
            return message
        details = []
        operation = owner.get("operation")
        if isinstance(operation, str) and operation in _OPERATIONS:
            details.append(operation)
        pid = owner.get("pid")
        if type(pid) is int and 0 < pid <= 2**31 - 1:
            details.append(f"PID {pid}")
        if details:
            message += " (recorded owner: " + ", ".join(details) + ")"
    except (OSError, ValueError):
        pass
    return message


@contextmanager
def operation_lock(
    state_root: Path,
    *,
    fault_after_acquire: bool = False,
    wait_timeout: float = 0,
    operation: str = "operation",
) -> Iterator[None]:
    """Acquire an exclusive operations lock under state_root."""
    path = lock_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValidationError("operations lock must be an unaliased regular file")
        import fcntl

        deadline = time.monotonic() + wait_timeout if wait_timeout > 0 else None
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if deadline is None or time.monotonic() >= deadline:
                    raise OperationBusy(_busy_message(fd)) from exc
                time.sleep(_LOCK_POLL_INTERVAL)
        payload = {
            "pid": os.getpid(),
            "operation": operation if operation in _OPERATIONS else "operation",
            "startedAt": time.time(),
        }
        os.ftruncate(fd, 0)
        os.write(fd, json.dumps(payload).encode())
        os.fsync(fd)
        if fault_after_acquire:
            raise ValidationError("fault injection: interrupted after lock acquire")
        yield
    finally:
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(fd)
