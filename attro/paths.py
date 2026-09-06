"""Path resolution and refusal guards (not a filesystem sandbox)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

LEGACY_HOME_ENV = "PIATTRO_HOME"
CANONICAL_HOME_ENV = "ATTRO_HOME"
DEFAULT_HOME_NAME = ".attro"
LEGACY_HOME_NAME = ".piattro"


def home() -> Path:
    explicit = os.environ.get(CANONICAL_HOME_ENV) or os.environ.get(LEGACY_HOME_ENV)
    if explicit:
        return Path(explicit).expanduser()
    attro_default = Path.home() / DEFAULT_HOME_NAME
    legacy_default = Path.home() / LEGACY_HOME_NAME
    if attro_default.exists():
        return attro_default
    if legacy_default.exists():
        return legacy_default
    return attro_default


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_state_root(root: Path, checkout: Path | None = None) -> Path:
    from attro.validate import ValidationError

    root = root.expanduser().absolute()
    if root.is_symlink():
        raise ValidationError(f"managed root cannot be a symlink: {root}")
    root = root.resolve()
    protected = [(Path.home() / ".pi").resolve(), repo_root().resolve()]
    if checkout is not None:
        protected.append(checkout.resolve())
    if root == Path.home().resolve() or root == Path(root.anchor):
        raise ValidationError(f"unsafe managed root: {root}")
    for path in protected:
        if root == path or root in path.parents or path in root.parents:
            raise ValidationError(f"managed root overlaps protected path: {path}")
    for ancestor in (root, *root.parents):
        if (ancestor / ".git").exists():
            raise ValidationError(f"managed root cannot be inside a Git checkout: {root}")
    for name in ("releases", "staging", "state.json", ".operations.lock", "agent"):
        safe_child(root, name)
    return root


def safe_child(base: Path, *parts: str) -> Path:
    from attro.validate import ValidationError

    if base.is_symlink():
        raise ValidationError(f"refusing symlink: {base}")
    base = base.resolve()
    target = base
    for part in parts:
        if not isinstance(part, str) or not part or "\\" in part or "\x00" in part:
            raise ValidationError(f"invalid relative path: {part!r}")
        rel = Path(part)
        if rel.is_absolute() or any(p in {"..", "."} for p in part.split("/")):
            raise ValidationError(f"invalid relative path: {part!r}")
        for component in rel.parts:
            target /= component
            if target.is_symlink():
                raise ValidationError(f"refusing symlink: {target}")
    if target == base or base not in target.parents:
        raise ValidationError(f"path escapes root: {target}")
    return target


def releases_dir(state_root: Path | None = None) -> Path:
    return safe_child(validate_state_root(state_root or home()), "releases")


def staging_dir(state_root: Path | None = None) -> Path:
    return safe_child(validate_state_root(state_root or home()), "staging")


def state_path(state_root: Path | None = None) -> Path:
    return safe_child(validate_state_root(state_root or home()), "state.json")


def lock_path(state_root: Path | None = None) -> Path:
    return safe_child(validate_state_root(state_root or home()), ".operations.lock")


def release_dir(release_id: str, state_root: Path | None = None) -> Path:
    from attro.validate import validate_release_id

    validate_release_id(release_id)
    return safe_child(releases_dir(state_root), release_id)


def platform_supported() -> bool:
    return sys.platform in {"darwin", "linux"}
