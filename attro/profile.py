"""Immutable profile inputs and one-time, private shared user-state initialization."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from attro.constants import AGENT_SEED_CONFIGS
from attro.paths import safe_child, validate_state_root
from attro.validate import ValidationError, assert_copy_allowed, fsync_dir, load_json, relative_path, write_json_atomic

RESOURCE_FLAGS = {"packages": "-e", "extensions": "-e", "skills": "--skill", "prompts": "--prompt-template", "themes": "--theme"}
PROFILE_MARKER = ".attro-profile.json"
LEGACY_PROFILE_MARKER = ".piattro-profile.json"
SEED_FILES = frozenset({
    "AGENTS.md", "CLAUDE.md", "SYSTEM.md", "APPEND_SYSTEM.md", "models.json", "keybindings.json",
    "subagents.json", "rpiv-todo.json", "claude-plugins.json", "cursor-sdk.json", "cursor-sdk-context-windows.json",
    "pi-caffeinate.json", "safety-guard.json", "web-search.json", "lens-config.json", "extensions/pi-automode/config.json",
    "rpiv-config/rpiv-todo/config.json", *AGENT_SEED_CONFIGS,
})


def validate_profile_tree(root: Path, *, seed: bool = False) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValidationError(f"profile directory missing or symlinked: {root}")
    files = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        relative_path(rel, "profile path")
        assert_copy_allowed(rel)
        if any(part.lower() in {"sessions", "cache", "trust", "credentials", "node_modules", ".git"} for part in path.relative_to(root).parts):
            raise ValidationError(f"forbidden profile path: {rel}")
        if path.is_symlink() or (not path.is_dir() and (not path.is_file() or path.stat().st_nlink != 1)):
            raise ValidationError(f"profile files must not alias external state: {rel}")
        if path.is_dir():
            continue
        if seed:
            parts = path.relative_to(root).parts
            allowed = rel in SEED_FILES or (len(parts) == 2 and ((parts[0] == "agents" and path.suffix == ".md") or (parts[0] == "pluginprefs" and path.suffix == ".json")))
            if not allowed:
                raise ValidationError(f"profile seed file is not approved: {rel}")
            if path.suffix == ".json":
                load_json(path)
        files.append(path)
    return files


def validate_resource_package(root: Path) -> None:
    package = load_json(safe_child(root, "package.json"))
    manifest = package.get("pi")
    if not isinstance(manifest, dict):
        raise ValidationError("profile resource package requires a pi manifest")
    for key in ("extensions", "skills", "prompts", "themes"):
        entries = manifest.get(key, [])
        if not isinstance(entries, list):
            raise ValidationError(f"profile package pi.{key} must be an array")
        for entry in entries:
            value = entry[2:] if isinstance(entry, str) and entry.startswith("./") else entry
            relative_path(value, f"pi.{key}")
            if not safe_child(root, value).exists():
                raise ValidationError(f"profile package resource missing: {entry}")


def shared_agent_dir(state_root: Path) -> Path:
    return safe_child(validate_state_root(state_root), "agent")


def _profile_marker_payload(agent: Path) -> dict[str, Any]:
    return {"schemaVersion": 1, "agentMode": "shared-v1", "agentDir": str(agent)}


def _read_profile_marker(agent: Path) -> dict[str, Any] | None:
    for name in (PROFILE_MARKER, LEGACY_PROFILE_MARKER):
        marker = safe_child(agent, name)
        if marker.is_file():
            return load_json(marker)
    return None


def validate_shared_agent(state_root: Path, *, required: bool = True) -> Path:
    agent = shared_agent_dir(state_root)
    if not agent.exists():
        if required:
            raise ValidationError("shared profile is not initialized; activate a shared-profile release first")
        return agent
    if not agent.is_dir():
        raise ValidationError(f"shared agent path is not a directory: {agent}")
    for name in (PROFILE_MARKER, LEGACY_PROFILE_MARKER, "auth.json", "settings.json", "trust.json", "models.json", "keybindings.json", "sessions"):
        path = safe_child(agent, name)
        if path.is_file() and path.stat().st_nlink != 1:
            raise ValidationError(f"shared agent sensitive file must not be hardlinked: {path}")
        if path.exists() and name not in {PROFILE_MARKER, LEGACY_PROFILE_MARKER, "sessions"} and not path.is_file():
            raise ValidationError(f"shared agent sensitive path must be a file: {path}")
    sessions = safe_child(agent, "sessions")
    if sessions.exists() and not sessions.is_dir():
        raise ValidationError("shared sessions path must be a directory")
    for path in sessions.rglob("*"):
        if path.is_symlink() or (path.is_file() and path.stat().st_nlink != 1):
            raise ValidationError(f"shared sessions must not alias external state: {path}")
    marker = _read_profile_marker(agent)
    if marker != _profile_marker_payload(agent):
        raise ValidationError(f"refusing existing unmanaged shared agent directory: {agent}; preserve it and choose an empty managed root")
    return agent


def seed_agent(release_path: Path, target: Path, *, agent_path: Path | None = None) -> None:
    target.mkdir(parents=True, mode=0o700)
    settings = load_json(safe_child(release_path, "config/settings.json"))
    for key in (*RESOURCE_FLAGS, "sessionDir", "defaultProjectTrust"):
        settings.pop(key, None)
    write_json_atomic(target / "settings.json", settings)
    for name in AGENT_SEED_CONFIGS:
        src = safe_child(release_path, "config", name)
        if src.is_file():
            dst = target / ("rpiv-config/rpiv-todo/config.json" if name == "rpiv-todo.json" else name)
            dst.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(src, dst)
    source = safe_child(release_path, "profile/agent")
    if source.exists():
        for src in validate_profile_tree(source, seed=True):
            dst = target / src.relative_to(source)
            dst.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            text = src.read_text()
            resolved = str(agent_path or target.resolve())
            for token in ("{{ATTRO_AGENT_DIR}}", "{{PIATTRO_AGENT_DIR}}"):
                text = text.replace(token, resolved)
            dst.write_text(text)
    for path in target.rglob("*"):
        path.chmod(0o700 if path.is_dir() else 0o600)
        if path.is_file():
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
        else:
            fsync_dir(path)
    fsync_dir(target)


def initialize_shared_agent(state_root: Path, release_path: Path) -> Path:
    agent = validate_shared_agent(state_root, required=False)
    if agent.exists():
        return agent
    with tempfile.TemporaryDirectory(prefix=".agent-init-", dir=state_root) as tmp:
        stage = Path(tmp) / "agent"
        seed_agent(release_path, stage, agent_path=agent)
        write_json_atomic(stage / PROFILE_MARKER, _profile_marker_payload(agent))
        if agent.exists() or agent.is_symlink():
            raise ValidationError(f"shared agent target already exists: {agent}")
        stage.rename(agent)
        fsync_dir(state_root)
    return agent


def require_shared_release(manifest: dict[str, Any]) -> None:
    if manifest.get("agentMode") != "shared-v1":
        raise ValidationError("legacy v0.1 release uses per-release user state; prepare a new release from a new source revision/version with this manager before activating or launching. Legacy credentials and history are preserved, not migrated")
