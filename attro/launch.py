"""Launch helpers for managed Pi exec and try."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from attro.guard import MANAGED_REFUSAL, blocked_pi_command
from attro.paths import safe_child
from attro.profile import RESOURCE_FLAGS, require_shared_release, seed_agent
from attro.state import _with_legacy_env_aliases, prepared_manifest, release_env
from attro.validate import ValidationError, check_node, load_json

MANAGED_RESOURCE_ARGV_ENV = "ATTRO_MANAGED_RESOURCE_ARGV"
KNOWN_RESOURCE_FLAGS = frozenset(RESOURCE_FLAGS.values())


def normalize_pi_command(command: list[str]) -> list[str]:
    if command and command[0] == "--":
        return command[1:]
    return command


def refuse_managed_mutation(command: list[str]) -> None:
    blocked = blocked_pi_command(command)
    if blocked is not None:
        raise ValidationError(f"refusing managed pi command {' '.join(blocked)}: {MANAGED_REFUSAL}")


def resolve_pi_binary(release_path: Path, *, manifest: dict[str, Any] | None = None) -> str:
    manifest = manifest or prepared_manifest(release_path)
    core = manifest["provenance"]["core"]
    check_node(core["nodeMinimum"])
    return core["piBinary"]


def validate_managed_resource_argv(argv: list[str], release_root: Path) -> list[str]:
    if len(argv) % 2:
        raise ValidationError("managed resource argv must be flag/path pairs")
    root = release_root.resolve()
    validated: list[str] = []
    for index in range(0, len(argv), 2):
        flag = argv[index]
        path_value = argv[index + 1]
        if flag not in KNOWN_RESOURCE_FLAGS:
            raise ValidationError(f"unknown managed resource flag: {flag!r}")
        if not isinstance(path_value, str) or not path_value:
            raise ValidationError("managed resource path must be a non-empty string")
        path = Path(path_value)
        if not path.is_absolute():
            raise ValidationError(f"managed resource path must be absolute: {path_value!r}")
        try:
            canonical = path.resolve(strict=True)
        except OSError as exc:
            raise ValidationError(f"managed resource path missing: {path_value!r}") from exc
        if not canonical.is_relative_to(root):
            raise ValidationError(f"managed resource path escapes release root: {path_value!r}")
        validated.extend([flag, str(canonical)])
    return validated


def managed_resource_argv_envelope(release_path: Path, *, manifest: dict[str, Any] | None = None) -> str:
    argv = managed_resource_args(release_path, manifest=manifest)
    return json.dumps(validate_managed_resource_argv(argv, release_path.resolve()))


def build_exec_env(release_path: Path, *, agent_dir: Path | None = None, manifest: dict[str, Any] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.update(release_env(release_path, agent_dir=agent_dir, manifest=manifest))
    env[MANAGED_RESOURCE_ARGV_ENV] = managed_resource_argv_envelope(release_path, manifest=manifest)
    env = _with_legacy_env_aliases(env)
    env["PI_SKIP_VERSION_CHECK"] = "1"
    for key in (
        "PI_CODING_AGENT_SESSION_DIR",
        "PI_SESSION_FILE",
        "PI_SESSION_ID",
        "PI_PACKAGE_DIR",
        "PI_SERVER_DIR",
        "PI_SERVER_ID",
        "ATTRO_TRY",
        "PIATTRO_TRY",
    ):
        env.pop(key, None)
    return env


def build_try_env(release_path: Path, isolated_agent: Path, *, manifest: dict[str, Any] | None = None) -> dict[str, str]:
    env = build_exec_env(release_path, agent_dir=isolated_agent.resolve(), manifest=manifest)
    env["ATTRO_TRY"] = "1"
    return _with_legacy_env_aliases(env)


def populate_try_agent(release_path: Path, isolated_agent: Path, *, manifest: dict[str, Any] | None = None) -> None:
    require_shared_release(manifest or prepared_manifest(release_path))
    if isolated_agent.exists() or isolated_agent.is_symlink():
        raise ValidationError("try agent target already exists")
    seed_agent(release_path, isolated_agent)


def managed_resource_args(release_path: Path, *, manifest: dict[str, Any] | None = None) -> list[str]:
    require_shared_release(manifest or prepared_manifest(release_path))
    settings = load_json(safe_child(release_path, "config/settings.json"))
    return [arg for key, flag in RESOURCE_FLAGS.items() for value in settings.get(key, []) for arg in (flag, value)]


def exec_pi(pi_bin: str, command: list[str], env: dict[str, str]) -> None:
    argv = [pi_bin, *command]
    os.execvpe(pi_bin, argv, env)
