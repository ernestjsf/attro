"""Launch helpers for managed Pi exec and try."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from piattro.constants import TRY_AGENT_COPY_ALLOWLIST
from piattro.guard import MANAGED_REFUSAL, blocked_pi_command
from piattro.paths import safe_child
from piattro.state import prepared_manifest, release_env
from piattro.validate import ValidationError, check_node, load_json, write_json_atomic


def normalize_pi_command(command: list[str]) -> list[str]:
    if command and command[0] == "--":
        return command[1:]
    return command


def refuse_managed_mutation(command: list[str]) -> None:
    blocked = blocked_pi_command(command)
    if blocked is not None:
        raise ValidationError(f"refusing managed pi command {' '.join(blocked)}: {MANAGED_REFUSAL}")


def resolve_pi_binary(release_path: Path) -> str:
    manifest = prepared_manifest(release_path)
    core = manifest["provenance"]["core"]
    check_node(core["nodeMinimum"])
    return core["piBinary"]


def build_exec_env(release_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(release_env(release_path))
    env["PI_SKIP_VERSION_CHECK"] = "1"
    for key in (
        "PI_CODING_AGENT_SESSION_DIR",
        "PI_SESSION_FILE",
        "PI_SESSION_ID",
        "PI_PACKAGE_DIR",
        "PI_SERVER_DIR",
        "PI_SERVER_ID",
        "PIATTRO_TRY",
    ):
        env.pop(key, None)
    return env


def build_try_env(release_path: Path, isolated_agent: Path) -> dict[str, str]:
    env = build_exec_env(release_path)
    env["PI_CODING_AGENT_DIR"] = str(isolated_agent.resolve())
    env["PIATTRO_TRY"] = "1"
    return env


def populate_try_agent(release_path: Path, isolated_agent: Path) -> None:
    prepared_manifest(release_path)
    if isolated_agent.exists() or isolated_agent.is_symlink():
        raise ValidationError("try agent target already exists")
    isolated_agent.mkdir(parents=True)
    for name in TRY_AGENT_COPY_ALLOWLIST:
        src = safe_child(release_path, "config", name)
        if src.is_file():
            shutil.copyfile(src, isolated_agent / name)
    settings = load_json(isolated_agent / "settings.json")
    for key in ("sessionDir", "defaultProvider", "defaultModel", "defaultThinkingLevel", "modelThinkingLevels", "defaultProjectTrust"):
        settings.pop(key, None)
    write_json_atomic(isolated_agent / "settings.json", settings)


def exec_pi(pi_bin: str, command: list[str], env: dict[str, str]) -> None:
    argv = [pi_bin, *command]
    os.execvpe(pi_bin, argv, env)
