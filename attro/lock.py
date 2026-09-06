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


@contextmanager
def operation_lock(state_root: Path, *, fault_after_acquire: bool = False) -> Iterator[None]:
    """Acquire an exclusive operations lock under state_root."""
    path = lock_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(fd).st_nlink != 1:
            raise ValidationError("operations lock must not be hardlinked")
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValidationError("another Attro operation is already running") from exc
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
