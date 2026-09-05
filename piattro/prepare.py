"""Prepare independent retained releases from a trusted, clean Git snapshot."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from piattro.constants import AGENT_SEED_CONFIGS, LENS_BUILD, LENS_CHECK_GRAMMARS, LENS_GRAMMARS, MANIFEST_FILE, NPM_CI, NPM_INSTALL, PREPARED_MARKER
from piattro.git_export import export_tracked_tree
from piattro.npm_packages import npm_dependencies_from_entries, npm_spec
from piattro.paths import release_dir, releases_dir, safe_child, staging_dir, validate_state_root
from piattro.validate import ValidationError, check_node, compute_release_id, fsync_dir, git, load_json, render_profile, run_command, sha256_file, validate_checkout, validate_descriptor, write_json_atomic


def _install_packages(stage: Path, final: Path, entries: list[dict[str, str]], *, core: bool = False) -> list[dict[str, Any]]:
    name = "pi" if core else "npm"
    install_root = stage / name
    install_root.mkdir()
    write_json_atomic(install_root / "package.json", {"name": f"piattro-release-{name}", "private": True, "dependencies": npm_dependencies_from_entries(entries)})
    run_command(NPM_INSTALL, install_root)
    lock = safe_child(install_root, "package-lock.json")
    if not lock.is_file():
        raise ValidationError(f"npm did not create a dependency lock in {install_root}")
    records = []
    for entry in entries:
        target = safe_child(install_root, "node_modules", entry["package"])
        package = load_json(safe_child(target, "package.json"))
        if package.get("name") != entry["package"] or package.get("version") != entry["version"]:
            raise ValidationError(f"installed npm package does not match pin: {npm_spec(entry['package'], entry['version'])}")
        record = {
            **entry,
            "installRoot": str(final / name / "node_modules" / entry["package"]),
            "lockFile": str(final / name / "package-lock.json"),
            "lockSha256": sha256_file(lock),
        }
        if core:
            cli = safe_child(target, "dist/bundle/cli.js")
            if not cli.is_file() or not os.access(cli, os.X_OK):
                raise ValidationError(f"release-local Pi CLI missing or not executable: {cli}")
            record.update({"expectedVersion": entry["version"], "installedVersion": entry["version"], "piBinary": str(final / cli.relative_to(stage)), "installMethod": "npm"})
        records.append(record)
    return records


def _validate_resources(stage: Path, final: Path, settings: dict[str, Any]) -> None:
    for key in ("packages", "themes", "extensions", "skills", "prompts"):
        for value in settings.get(key, []):
            path = Path(value)
            if not path.is_absolute() or not path.is_relative_to(final):
                raise ValidationError(f"profile {key} must resolve inside the release: {value}")
            if not safe_child(stage, str(path.relative_to(final))).exists():
                raise ValidationError(f"profile resource missing: {value}")


def prepare_release(checkout_root: Path, *, state_root: Path) -> dict[str, Any]:
    checkout_root = checkout_root.expanduser().resolve()
    state_root = validate_state_root(state_root, checkout_root)
    head = git("rev-parse", "HEAD", cwd=checkout_root)
    descriptor = validate_descriptor(safe_child(checkout_root, "piattro.json"))
    sources = validate_checkout(checkout_root, descriptor)
    if git("rev-parse", "HEAD", cwd=checkout_root) != head:
        raise ValidationError("checkout changed during validation; retry from a clean checkout")
    node_version = check_node(descriptor["core"]["engines"]["node"])
    stages = staging_dir(state_root)
    stages.mkdir(parents=True, exist_ok=True)
    releases_dir(state_root).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prepare-", dir=stages) as work:
        workspace = Path(work)
        snapshot = workspace / "source"
        export_tracked_tree(checkout_root, snapshot, head)
        committed_descriptor = validate_descriptor(safe_child(snapshot, "piattro.json"))
        committed_sources = load_json(safe_child(snapshot, committed_descriptor["sourcesLock"]))
        if committed_descriptor != descriptor or committed_sources != sources:
            raise ValidationError("descriptor or sources lock differs from committed snapshot")
        descriptor, sources = committed_descriptor, committed_sources
        rid = compute_release_id(descriptor, sources, checkout_root, head=head)
        final = release_dir(rid, state_root)
        if final.exists():
            from piattro.state import prepared_manifest

            existing = prepared_manifest(final, rid)
            if existing["provenance"]["checkoutHead"] != head:
                raise ValidationError("existing release has different provenance")
            return existing
        stage = workspace / "release"
        stage.mkdir()
        (stage / "plugins").mkdir()
        dependency_locks = []
        for entry in sources["submodules"]:
            dst = safe_child(stage, entry["path"])
            export_tracked_tree(safe_child(checkout_root, entry["path"]), dst, entry["pin"])
            lock = entry.get("dependencyLock")
            if lock:
                lock_path = safe_child(dst, lock)
                if not lock_path.is_file():
                    raise ValidationError(f"dependency lock missing: {entry['path']}")
                digest = sha256_file(lock_path)
                run_command(NPM_CI, dst)
                if sha256_file(lock_path) != digest:
                    raise ValidationError(f"dependency lock changed during npm ci: {entry['path']}")
                dependency_locks.append({"path": str(final / entry["path"] / lock), "sha256": digest})
            if entry["runtimeGenerated"]:
                for command in (LENS_BUILD, LENS_GRAMMARS, LENS_CHECK_GRAMMARS):
                    run_command(command, dst)
            for name in entry["runtimeEntryFiles"]:
                if not safe_child(dst, name).is_file():
                    raise ValidationError(f"runtime file missing after staging: {entry['path']}/{name}")
        config_dir = stage / "config"
        config_dir.mkdir()
        for config in sources["configs"]:
            src = safe_child(snapshot, config["path"])
            if not src.is_file() or sha256_file(src) != config["sha256"]:
                raise ValidationError(f"config missing or hash mismatch in snapshot: {config['path']}")
            shutil.copyfile(src, config_dir / Path(config["path"]).name)
        npm = _install_packages(stage, final, descriptor["npmPackages"]) if descriptor["npmPackages"] else []
        if not npm:
            (stage / "npm").mkdir()
        core = _install_packages(stage, final, [{"package": descriptor["core"]["package"], "version": descriptor["core"]["version"]}], core=True)[0]
        core["nodeMinimum"] = descriptor["core"]["engines"]["node"]
        profile = safe_child(snapshot, descriptor["profile"]).read_text()
        settings = json.loads(render_profile(profile, final, checkout_root, descriptor))
        _validate_resources(stage, final, settings)
        write_json_atomic(config_dir / "settings.json", settings)
        agent_dir = stage / "agent"
        agent_dir.mkdir()
        write_json_atomic(agent_dir / "settings.json", settings)
        for name in AGENT_SEED_CONFIGS:
            if (config_dir / name).is_file():
                shutil.copyfile(config_dir / name, agent_dir / name)
        prepared_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "schemaVersion": 1, "releaseId": rid, "preparedAt": prepared_at,
            "checkoutRoot": str(checkout_root), "descriptorVersion": descriptor["version"], "distribution": descriptor["distribution"],
            "layout": {name: str(final / name) for name in ("pi", "plugins", "config", "agent", "npm")},
            "provenance": {"checkoutHead": head, "sourcesLock": descriptor["sourcesLock"], "sources": sources, "nodeVersion": node_version, "core": core, "npmPackages": npm, "pluginDependencyLocks": dependency_locks,
                           "dependencyResolution": "Plugin npm ci uses committed locks; core/npm locks are newly resolved per preparation, not globally reproducible."},
        }
        write_json_atomic(stage / "pi/core.json", core)
        write_json_atomic(stage / "npm/packages.json", {"packages": npm})
        write_json_atomic(stage / MANIFEST_FILE, manifest)
        with (stage / PREPARED_MARKER).open("x") as marker:
            marker.write(prepared_at + "\n")
            marker.flush()
            os.fsync(marker.fileno())
        fsync_dir(stage)
        from piattro.state import prepared_manifest

        prepared_manifest(stage, rid, final_root=final)
        if final.exists() or final.is_symlink():
            raise ValidationError(f"release target already exists: {final}")
        stage.rename(final)
        fsync_dir(final.parent)
        return manifest
