"""Export committed regular files, never a mutable working-tree copy."""

from __future__ import annotations

import io
import shutil
import subprocess
import tarfile
from pathlib import Path

from piattro.paths import safe_child
from piattro.validate import ValidationError, assert_copy_allowed, git


def export_tracked_tree(repo_root: Path, dst_root: Path, revision: str = "HEAD") -> None:
    repo_root = repo_root.resolve()
    if dst_root.exists() or dst_root.is_symlink():
        raise ValidationError(f"export target already exists: {dst_root}")
    commit = git("rev-parse", "--verify", f"{revision}^{{commit}}", cwd=repo_root)
    try:
        result = subprocess.run(["git", "archive", "--format=tar", commit], cwd=repo_root, check=False, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValidationError(f"git export failed: {exc}") from exc
    if result.returncode:
        raise ValidationError(f"git archive failed in {repo_root}: {result.stderr.decode(errors='replace')}")
    dst_root.mkdir(parents=True)
    exported = 0
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
        for member in archive:
            rel = member.name.rstrip("/")
            target = safe_child(dst_root, rel)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ValidationError(f"refusing non-regular tracked file: {rel}")
            assert_copy_allowed(rel)
            source = archive.extractfile(member)
            if source is None:
                raise ValidationError(f"cannot export {rel}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with source, target.open("xb") as stream:
                shutil.copyfileobj(source, stream)
            target.chmod(0o755 if member.mode & 0o111 else 0o644)
            exported += 1
    if not exported:
        raise ValidationError(f"no tracked files exported from {repo_root}")
