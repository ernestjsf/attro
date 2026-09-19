"""Cross-process operation locking."""

from __future__ import annotations

import json
import os
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


@contextmanager
def operation_lock(
    state_root: Path,
    *,
    fault_after_acquire: bool = False,
    wait_timeout: float = 0,
) -> Iterator[None]:
    """Acquire an exclusive operations lock under state_root."""
    path = lock_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(fd).st_nlink != 1:
            raise ValidationError("operations lock must not be hardlinked")
        import fcntl

        deadline = time.monotonic() + wait_timeout if wait_timeout > 0 else None
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if deadline is None or time.monotonic() >= deadline:
                    raise OperationBusy("another Attro operation is already running") from exc
                time.sleep(_LOCK_POLL_INTERVAL)
        payload = {
            "pid": os.getpid(),
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
