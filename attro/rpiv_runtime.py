"""Reviewed todo-only RPIV recipe; npm's publish manifest owns file selection."""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path
from typing import Any

from attro.constants import NPM_CI
from attro.paths import safe_child
from attro.validate import ValidationError, assert_copy_allowed, load_json, relative_path, run_command, sha256_file, validate_public_npm_lock

RPIV_PATH = "plugins/rpiv-mono"
LOCK_SOURCE = "runtime/rpiv-todo"
RECIPE = "rpiv-todo-v1"
PACKAGES = {
    "rpiv-todo": "packages/rpiv-todo",
    "rpiv-config": "node_modules/@juicesharp/rpiv-config",
    "rpiv-i18n": "node_modules/@juicesharp/rpiv-i18n",
}
DEPENDENCIES = {
    "rpiv-todo": {"@juicesharp/rpiv-config": "^2.9.0", "typebox": "^1.1.24"},
    "rpiv-config": {"typebox": "^1.1.24"},
    "rpiv-i18n": {"@juicesharp/rpiv-config": "^2.9.0"},
}
HOST_PEERS = {"@earendil-works/pi-ai", "@earendil-works/pi-coding-agent", "@earendil-works/pi-tui"}
EXTERNAL = {"typebox": "1.3.6"}
PACK = ["npm", "pack", "--dry-run", "--json", "--ignore-scripts", "--workspaces=false"]


def _regular_file(path: Path) -> None:
    if not path.is_file() or not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_nlink != 1:
        raise ValidationError(f"RPIV runtime requires a regular unaliased file: {path}")


def _inventory(root: Path) -> dict[str, str]:
    files = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        path = safe_child(root, relative_path(rel, "RPIV runtime file"))
        if path.is_dir():
            continue
        _regular_file(path)
        assert_copy_allowed(rel)
        files[rel] = sha256_file(path)
    return files


def _validate_lock(root: Path) -> None:
    package = load_json(safe_child(root, "package.json"))
    if package != {"name": "attro-rpiv-todo-runtime", "private": True, "dependencies": EXTERNAL}:
        raise ValidationError("RPIV runtime package.json does not match reviewed external closure")
    lock_path = safe_child(root, "package-lock.json")
    validate_public_npm_lock(lock_path)
    lock = load_json(lock_path)
    packages = lock.get("packages", {})
    if lock.get("lockfileVersion") != 3 or set(packages) != {"", "node_modules/typebox"}:
        raise ValidationError("RPIV runtime lock must contain only the reviewed typebox closure")
    if packages[""].get("dependencies") != EXTERNAL:
        raise ValidationError("RPIV runtime lock dependencies mismatch")
    external = packages["node_modules/typebox"]
    if (external.get("version") != EXTERNAL["typebox"] or not external.get("integrity")
            or external.get("resolved") != "https://registry.npmjs.org/typebox/-/typebox-1.3.6.tgz"):
        raise ValidationError("RPIV runtime typebox pin/integrity missing or mismatched")


def _validate_package(root: Path, name: str) -> dict[str, Any]:
    package = load_json(safe_child(root, "package.json"))
    if package.get("name") != f"@juicesharp/{name}" or package.get("version") != "2.9.0":
        raise ValidationError(f"RPIV runtime package pin mismatch: {name}")
    peers = package.get("peerDependencies", {})
    allowed = HOST_PEERS | ({"@juicesharp/rpiv-i18n"} if name == "rpiv-todo" else set())
    if (package.get("dependencies") != DEPENDENCIES[name] or package.get("optionalDependencies")
            or package.get("bundledDependencies") or package.get("bundleDependencies")
            or not isinstance(peers, dict) or any(key not in allowed or value != "*" for key, value in peers.items())):
        raise ValidationError(f"RPIV runtime dependency closure changed; review recipe: {name}")
    return package


def prepare_rpiv_runtime(source: Path, destination: Path, snapshot: Path) -> dict[str, Any]:
    """Source is a disposable pinned export, never an installed or working tree."""
    if destination.exists() or destination.is_symlink():
        raise ValidationError(f"RPIV runtime target already exists: {destination}")
    lock_root = safe_child(snapshot, LOCK_SOURCE)
    _validate_lock(lock_root)
    destination.mkdir(parents=True)
    for name in ("package.json", "package-lock.json"):
        src = safe_child(lock_root, name)
        _regular_file(src)
        shutil.copyfile(src, destination / name)
    lock_sha = sha256_file(destination / "package-lock.json")
    # Install only the external closure, before copying local packages: npm must
    # never auto-install the helpers' host Pi peers or monorepo development graph.
    run_command([*NPM_CI, "--omit=dev", "--legacy-peer-deps"], destination)
    if sha256_file(destination / "package-lock.json") != lock_sha:
        raise ValidationError("RPIV dependency lock changed during npm ci")
    for name, target in PACKAGES.items():
        package_root = safe_child(source, "packages", name)
        _validate_package(package_root, name)
        result = run_command(PACK, package_root)
        try:
            packed = json.loads(result.stdout)
        except (ValueError, TypeError) as exc:
            raise ValidationError("invalid npm pack inventory") from exc
        if not isinstance(packed, list) or len(packed) != 1 or not isinstance(packed[0], dict):
            raise ValidationError("invalid npm pack inventory")
        packed = packed[0]
        if packed.get("name") != f"@juicesharp/{name}" or packed.get("version") != "2.9.0" or packed.get("bundled"):
            raise ValidationError(f"unexpected npm pack package: {name}")
        files = packed.get("files")
        if not isinstance(files, list) or not files:
            raise ValidationError(f"empty npm pack inventory: {name}")
        seen = set()
        for entry in files:
            if not isinstance(entry, dict):
                raise ValidationError("invalid npm pack file")
            rel = relative_path(entry.get("path"), "npm pack file")
            if rel in seen or "node_modules" in Path(rel).parts:
                raise ValidationError(f"unexpected npm pack file: {rel}")
            seen.add(rel)
            assert_copy_allowed(rel)
            src = safe_child(package_root, rel)
            _regular_file(src)
            if src.stat().st_size != entry.get("size"):
                raise ValidationError(f"npm pack file changed: {rel}")
            dst = safe_child(destination, target, rel)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        if "package.json" not in seen:
            raise ValidationError(f"npm pack omitted package.json: {name}")
    # rpiv-config's files manifest has no package license; preserve the source
    # monorepo license alongside the payload and its full lock as provenance only.
    for src_name, dst_name in (("LICENSE", "LICENSE"), ("package-lock.json", "source-package-lock.json")):
        src = safe_child(source, src_name)
        _regular_file(src)
        shutil.copyfile(src, destination / dst_name)
    record = {
        "recipe": RECIPE,
        "lockSource": LOCK_SOURCE,
        "lockSha256": lock_sha,
        "sourceLockSha256": sha256_file(destination / "source-package-lock.json"),
        "files": _inventory(destination),
    }
    validate_rpiv_runtime(destination, record)
    return record


def validate_rpiv_runtime(root: Path, record: Any) -> None:
    if not isinstance(record, dict) or record.get("recipe") != RECIPE or record.get("lockSource") != LOCK_SOURCE:
        raise ValidationError("unsupported RPIV runtime provenance")
    _validate_lock(root)
    if (record.get("lockSha256") != sha256_file(safe_child(root, "package-lock.json"))
            or record.get("sourceLockSha256") != sha256_file(safe_child(root, "source-package-lock.json"))):
        raise ValidationError("RPIV runtime lock digest mismatch")
    files = record.get("files")
    if not isinstance(files, dict) or not files or files != _inventory(root):
        raise ValidationError("RPIV runtime file inventory/digest mismatch")
    for name, target in PACKAGES.items():
        _validate_package(safe_child(root, target), name)
    installed = load_json(safe_child(root, "node_modules/typebox/package.json"))
    if installed.get("name") != "typebox" or installed.get("version") != EXTERNAL["typebox"]:
        raise ValidationError("RPIV installed typebox pin mismatch")
    modules = safe_child(root, "node_modules")
    if {path.name for path in modules.iterdir()} != {"typebox", "@juicesharp", ".package-lock.json"}:
        raise ValidationError("unexpected RPIV installed dependency")
    if {path.name for path in safe_child(modules, "@juicesharp").iterdir()} != {"rpiv-config", "rpiv-i18n"}:
        raise ValidationError("unexpected RPIV helper package")
