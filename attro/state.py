"""Atomic active/previous pointers to confined retained releases."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attro.constants import CORE_CLI_REL, CORE_SOURCE_SUBMODULE, MANIFEST_FILE, PREPARED_MARKER
from attro.core_source import validate_installed_workspace_links, validate_source_core_layout
from attro.paths import release_dir, safe_child, state_path
from attro.profile import initialize_shared_agent, require_shared_release, validate_profile_tree, validate_shared_agent
from attro.validate import ValidationError, load_json, sha256_file, validate_manifest, validate_release_id, validate_sources_lock, validate_state, write_json_atomic


def empty_state() -> dict[str, Any]:
    return {"schemaVersion": 1, "active": None, "previous": None, "releases": {}}


def load_state(state_root: Path) -> dict[str, Any]:
    path = state_path(state_root)
    if not path.exists():
        return empty_state()
    data = load_json(path)
    validate_state(data)
    for rid, entry in data["releases"].items():
        expected = release_dir(rid, state_root)
        if entry["path"] != str(expected):
            raise ValidationError(f"release registry path is not canonical: {rid}")
    return data


def save_state(state_root: Path, data: dict[str, Any]) -> None:
    validate_state(data)
    for rid, entry in data["releases"].items():
        if entry["path"] != str(release_dir(rid, state_root)):
            raise ValidationError(f"release registry path is not canonical: {rid}")
    write_json_atomic(state_path(state_root), data)


def prepared_manifest(path: Path, release_id: str | None = None, *, final_root: Path | None = None) -> dict[str, Any]:
    if path.is_symlink() or not path.is_dir():
        raise ValidationError(f"release missing or symlinked: {path}")
    path = path.resolve()
    final = final_root or path
    manifest = load_json(safe_child(path, MANIFEST_FILE))
    validate_manifest(manifest)
    if manifest["releaseId"] != (release_id or path.name):
        raise ValidationError("manifest release identity mismatch")
    if not safe_child(path, PREPARED_MARKER).is_file():
        raise ValidationError(f"release not prepared: {path}")
    shared = manifest.get("agentMode") == "shared-v1"
    for name in ("pi", "plugins", "config", "profile" if shared else "agent", "npm"):
        if manifest["layout"].get(name) != str(final / name) or not safe_child(path, name).is_dir():
            raise ValidationError(f"invalid or missing release layout: {name}")
    if shared:
        files = validate_profile_tree(safe_child(path, "profile"))
        validate_profile_tree(safe_child(path, "profile/agent"), seed=True)
        if manifest.get("profileFiles") != {resource.relative_to(path).as_posix(): sha256_file(resource) for resource in files}:
            raise ValidationError("release profile digest mismatch")
        if manifest.get("settingsSha256") != sha256_file(safe_child(path, "config/settings.json")):
            raise ValidationError("release settings digest mismatch")
    else:
        for resource in safe_child(path, "agent").rglob("*"):
            if resource.is_symlink() or (resource.is_file() and resource.stat().st_nlink != 1):
                raise ValidationError(f"agent state must not alias files outside this release: {resource}")
    provenance = manifest["provenance"]
    for record in [provenance["core"], *provenance["npmPackages"]]:
        is_core = record is provenance["core"]
        name = "pi" if is_core else "npm"
        if is_core and record.get("installMethod") == "source":
            expected = {
                "installRoot": "pi",
                "lockFile": "pi/package-lock.json",
                "piBinary": f"pi/{CORE_CLI_REL}",
            }
            for key, rel in expected.items():
                actual = safe_child(path, rel)
                if record[key] != str(final / rel) or not actual.exists():
                    raise ValidationError(f"invalid or missing release {key}: {record[key]}")
            package_json = safe_child(path, "pi/packages/coding-agent/package.json")
            installed = load_json(package_json)
            version = record["expectedVersion"]
            if installed.get("name") != record["package"] or installed.get("version") != version:
                raise ValidationError("installed package pin mismatch")
            if sha256_file(safe_child(path, "pi/package-lock.json")) != record["lockSha256"]:
                raise ValidationError("installed dependency lock digest mismatch")
            install_root = safe_child(path, "pi")
            validate_installed_workspace_links(install_root, safe_child(install_root, "package-lock.json"))
            runtime_hashes = validate_source_core_layout(install_root, package=record["package"], version=version)
            if record.get("runtimeHashes") != runtime_hashes:
                raise ValidationError("source core runtime digest mismatch")
            try:
                executable = os.access(safe_child(path, expected["piBinary"]), os.X_OK)
            except OSError as exc:
                raise ValidationError("cannot inspect Pi CLI") from exc
            if not executable:
                raise ValidationError("Pi CLI is not executable")
            continue
        root_rel = f"{name}/node_modules/{record['package']}"
        expected = {"installRoot": root_rel, "lockFile": f"{name}/package-lock.json"}
        if is_core:
            expected["piBinary"] = root_rel + "/dist/bundle/cli.js"
        for key, rel in expected.items():
            actual = safe_child(path, rel)
            if record[key] != str(final / rel) or not actual.exists():
                raise ValidationError(f"invalid or missing release {key}: {record[key]}")
        installed = load_json(safe_child(path, root_rel, "package.json"))
        version = record["expectedVersion"] if is_core else record["version"]
        if installed.get("name") != record["package"] or installed.get("version") != version:
            raise ValidationError("installed package pin mismatch")
        if sha256_file(safe_child(path, f"{name}/package-lock.json")) != record["lockSha256"]:
            raise ValidationError("installed dependency lock digest mismatch")
        if is_core:
            try:
                executable = os.access(safe_child(path, expected["piBinary"]), os.X_OK)
            except OSError as exc:
                raise ValidationError("cannot inspect Pi CLI") from exc
            if not executable:
                raise ValidationError("Pi CLI is not executable")
    sources = provenance.get("sources")
    if not isinstance(sources, dict):
        raise ValidationError("manifest lacks source provenance")
    validate_sources_lock(sources)
    for entry in sources["submodules"]:
        if entry["path"] == CORE_SOURCE_SUBMODULE:
            continue
        for name in entry["runtimeEntryFiles"]:
            if not safe_child(path, entry["path"], name).is_file():
                raise ValidationError(f"release runtime entry missing: {entry['path']}/{name}")
    for config in sources["configs"]:
        target = safe_child(path, "config", Path(config["path"]).name)
        if not target.is_file() or sha256_file(target) != config["sha256"]:
            raise ValidationError(f"release config digest mismatch: {config['path']}")
    for agent_settings in (("config/settings.json",) if shared else ("config/settings.json", "agent/settings.json")):
        settings = load_json(safe_child(path, agent_settings))
        for key in ("packages", "themes", "extensions", "skills", "prompts"):
            entries = settings.get(key, [])
            if not isinstance(entries, list) or any(not isinstance(value, str) for value in entries):
                raise ValidationError(f"release settings {key} must be an array of paths")
            for value in entries:
                resource = Path(value)
                if not resource.is_absolute() or not resource.is_relative_to(final) or not safe_child(path, str(resource.relative_to(final))).exists():
                    raise ValidationError(f"release resource missing or outside release: {value}")
    return manifest


def register_release(state_root: Path, release_id: str, release_path: Path) -> None:
    validate_release_id(release_id)
    expected = release_dir(release_id, state_root)
    if release_path.is_symlink() or release_path.resolve() != expected:
        raise ValidationError("cannot register a release outside its managed directory")
    manifest = prepared_manifest(expected, release_id)
    state = load_state(state_root)
    record = {"path": str(expected), "preparedAt": manifest["preparedAt"]}
    if release_id in state["releases"] and state["releases"][release_id] != record:
        raise ValidationError("release is already registered with different metadata")
    state["releases"][release_id] = record
    save_state(state_root, state)


def activate_release(state_root: Path, release_id: str) -> None:
    validate_release_id(release_id)
    state = load_state(state_root)
    if release_id not in state["releases"]:
        raise ValidationError(f"unknown release: {release_id}")
    path = release_dir(release_id, state_root)
    require_shared_release(prepared_manifest(path, release_id))
    initialize_shared_agent(state_root, path)
    if state["active"] == release_id:
        return
    state["previous"], state["active"] = state["active"], release_id
    state["activatedAt"] = datetime.now(timezone.utc).isoformat()
    save_state(state_root, state)


def rollback(state_root: Path) -> str:
    state = load_state(state_root)
    previous = state["previous"]
    if previous is None:
        raise ValidationError("no previous release to roll back to")
    activate_release(state_root, previous)
    return previous


def active_release_path(state_root: Path) -> Path | None:
    state = load_state(state_root)
    if state["active"] is None:
        return None
    path = release_dir(state["active"], state_root)
    prepared_manifest(path, state["active"])
    return path


def _with_legacy_env_aliases(env: dict[str, str]) -> dict[str, str]:
    aliases = {
        "ATTRO_RESOURCE_DIR": "PIATTRO_RESOURCE_DIR",
        "ATTRO_RELEASE_ID": "PIATTRO_RELEASE_ID",
        "ATTRO_RELEASE_ROOT": "PIATTRO_RELEASE_ROOT",
        "ATTRO_PI_BIN": "PIATTRO_PI_BIN",
        "ATTRO_MANAGED": "PIATTRO_MANAGED",
        "ATTRO_MANAGED_RESOURCE_ARGV": "PIATTRO_MANAGED_RESOURCE_ARGV",
        "ATTRO_TRY": "PIATTRO_TRY",
    }
    merged = dict(env)
    for canonical, legacy in aliases.items():
        if canonical in merged:
            merged[legacy] = merged[canonical]
    return merged


def release_env(release_path: Path, *, agent_dir: Path | None = None, manifest: dict[str, Any] | None = None) -> dict[str, str]:
    manifest = manifest or prepared_manifest(release_path)
    require_shared_release(manifest)
    agent = agent_dir or validate_shared_agent(release_path.resolve().parents[1])
    return _with_legacy_env_aliases({
        "PI_CODING_AGENT_DIR": str(agent),
        "RPIV_CONFIG_HOME": str(agent / "rpiv-config"),
        "PI_LENS_CONFIG_PATH": str(agent / "lens-config.json"),
        "ATTRO_RESOURCE_DIR": str(release_path.resolve() / "profile/resources"),
        "ATTRO_RELEASE_ID": manifest["releaseId"],
        "ATTRO_RELEASE_ROOT": str(release_path.resolve()),
        "ATTRO_PI_BIN": manifest["provenance"]["core"]["piBinary"],
        "ATTRO_MANAGED": "1", "PI_OFFLINE": "1", "PI_SKIP_VERSION_CHECK": "1",
    })
