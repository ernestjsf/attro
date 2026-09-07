"""Build and validate Pi core from the maintained attro-core Git submodule."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import stat
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from attro.constants import (
    CORE_BUILD_OFFLINE,
    CORE_CHECK_MODEL_DATA,
    CORE_CLI_REL,
    CORE_MODEL_DATA_REL,
    CORE_SOURCE_SUBMODULE,
    NPM_CI,
)
from attro.git_export import export_tracked_tree
from attro.npm_packages import validate_package_name, validate_version
from attro.paths import safe_child
from attro.validate import ValidationError, load_json, relative_path, run_command, sha256_file, text, validate_model_snapshot_url

SNAPSHOT_DOWNLOAD_LIMIT = 256 * 1024 * 1024
SNAPSHOT_EXPANSION_LIMIT = 512 * 1024 * 1024
SNAPSHOT_FILE_LIMIT = 8 * 1024 * 1024
SNAPSHOT_DATA_LIMIT = 64 * 1024 * 1024
SNAPSHOT_MEMBER_LIMIT = 100_000
BUILD_RECIPE = "npm-ci-build-offline-v1"
REGISTRY_PREFIX = "https://registry.npmjs.org/"
CRITICAL_WORKSPACES = {
    "@earendil-works/pi-coding-agent": "packages/coding-agent",
    "@earendil-works/pi-ai": "packages/ai",
    "@earendil-works/pi-tui": "packages/tui",
}


def _digest_runtime_file(path: Path | str, key: str, *, dir_fd: int | None = None) -> str:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
        with os.fdopen(fd, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise ValidationError(f"source core runtime is not a regular file: {key}")
            if metadata.st_nlink != 1:
                raise ValidationError(f"source core runtime must not alias another file: {key}")
            return _sha256_bytes(stream.read())
    except OSError as exc:
        raise ValidationError(f"source core runtime is not a regular file: {key}") from exc


def _open_runtime_directory(root_fd: int, key: str) -> int:
    fd = os.dup(root_fd)
    try:
        for component in key.split("/"):
            child_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _hash_runtime_resource(install_root: Path, resource: Path, rel_key: str) -> dict[str, str]:
    if not resource.exists():
        if resource.is_symlink():
            raise ValidationError(f"source core runtime is symlinked: {resource}")
        return {}
    safe_child(install_root, rel_key)
    if resource.is_file():
        return {rel_key: _digest_runtime_file(resource, rel_key)}
    if not resource.is_dir():
        raise ValidationError(f"source core runtime is not a regular file: {rel_key}")
    hashes: dict[str, str] = {}
    root_fd = os.open(install_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        keys = [rel_key]
        while keys:
            prefix = keys.pop()
            directory_fd = _open_runtime_directory(root_fd, prefix)
            try:
                with os.scandir(directory_fd) as entries:
                    for entry in entries:
                        if entry.name == "node_modules" and entry.is_dir():
                            continue
                        key = f"{prefix}/{entry.name}"
                        if "\\" in entry.name:
                            raise ValidationError(f"invalid relative path: {key!r}")
                        if entry.is_file(follow_symlinks=False):
                            hashes[key] = _digest_runtime_file(entry.name, key, dir_fd=directory_fd)
                        elif entry.is_dir(follow_symlinks=False):
                            keys.append(key)
                        else:
                            raise ValidationError(f"source core runtime is not a regular file: {key}")
                current_directory = safe_child(install_root, prefix)
                if not os.path.samestat(os.fstat(directory_fd), current_directory.stat()):
                    raise ValidationError(f"source core runtime directory changed during validation: {prefix}")
            finally:
                os.close(directory_fd)
    finally:
        os.close(root_fd)
    return hashes


def _validate_tree_symlinks(root: Path, pending_bins: dict[Path, Path]) -> None:
    stack = [root]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_symlink():
                    link = Path(entry.path)
                    try:
                        resolved = link.resolve(strict=True)
                    except FileNotFoundError as exc:
                        resolved = link.resolve()
                        if pending_bins.get(link) != resolved:
                            raise ValidationError(f"installed link is broken: {link}") from exc
                    except (OSError, RuntimeError) as exc:
                        raise ValidationError(f"installed link is broken: {link}") from exc
                    if Path(os.readlink(link)).is_absolute() or not resolved.is_relative_to(root):
                        raise ValidationError(f"installed link must be relative and contained: {link}")
                elif entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitized_build_env(home: Path) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    temporary = safe_child(home, "tmp")
    temporary.mkdir(exist_ok=True)
    return {"HOME": str(home), "PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "TMPDIR": str(temporary)}


def _declared_workspaces(install_root: Path) -> dict[str, str]:
    package = load_json(safe_child(install_root, "package.json"))
    patterns = package.get("workspaces")
    if not isinstance(patterns, list) or not patterns:
        raise ValidationError("source package must declare workspaces")
    workspaces: dict[str, str] = {}
    for pattern in patterns:
        relative_path(pattern, "workspace pattern")
        if not re.fullmatch(r"[A-Za-z0-9_./*-]+", pattern) or "**" in pattern or "node_modules" in pattern.split("/"):
            raise ValidationError(f"unsupported workspace pattern: {pattern}")
        found = False
        for target in sorted(install_root.glob(pattern)):
            rel = target.relative_to(install_root).as_posix()
            meta_path = safe_child(install_root, rel, "package.json")
            if not meta_path.is_file():
                continue
            found = True
            meta = load_json(meta_path)
            name = validate_package_name(meta.get("name"))
            validate_version(meta.get("version"))
            if name in workspaces:
                raise ValidationError(f"duplicate declared workspace: {name}")
            workspaces[name] = rel
        if not found:
            raise ValidationError(f"workspace pattern has no packages: {pattern}")
    version = load_json(safe_child(install_root, "packages/coding-agent/package.json")).get("version")
    for name, rel in CRITICAL_WORKSPACES.items():
        if workspaces.get(name) != rel:
            raise ValidationError(f"critical workspace identity mismatch: {name}")
        if load_json(safe_child(install_root, rel, "package.json")).get("version") != version:
            raise ValidationError(f"critical workspace version mismatch: {name}")
    return workspaces


def _validate_registry_url(value: Any) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"https://registry\.npmjs\.org/[A-Za-z0-9@._~+/-]+", value):
        raise ValidationError("source lock resolved URL is not public registry")
    relative_path(value.removeprefix(REGISTRY_PREFIX), "source lock registry path")


def validate_source_lock(path: Path, install_root: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValidationError(f"source core lock missing: {path}")
    lock = load_json(path)
    packages = lock.get("packages")
    if lock.get("lockfileVersion") != 3 or not isinstance(packages, dict):
        raise ValidationError("source lock must be v3 with a packages object")
    workspaces = _declared_workspaces(install_root)
    package = load_json(safe_child(install_root, "package.json"))
    root_entry = packages.get("")
    if not isinstance(root_entry, dict) or any(root_entry.get(key) != package.get(key) for key in ("name", "version", "workspaces")):
        raise ValidationError("source lock root identity/workspaces mismatch")
    for name, rel in workspaces.items():
        meta = load_json(safe_child(install_root, rel, "package.json"))
        entry = packages.get(rel)
        if not isinstance(entry, dict) or entry.get("name") != name or entry.get("version") != meta["version"]:
            raise ValidationError(f"source lock workspace identity mismatch: {rel}")
    links: dict[str, str] = {}
    for key, entry in packages.items():
        if key:
            relative_path(key, "source lock package path")
        if not isinstance(entry, dict):
            raise ValidationError(f"invalid source lock package entry: {key}")
        if "link" in entry and type(entry["link"]) is not bool:
            raise ValidationError(f"invalid workspace link flag: {key}")
        if entry.get("link") is True:
            if not key.startswith("node_modules/"):
                raise ValidationError(f"unexpected workspace link key: {key}")
            name = validate_package_name(key.removeprefix("node_modules/"))
            resolved = relative_path(entry.get("resolved"), "workspace link target")
            if workspaces.get(name) != resolved:
                raise ValidationError(f"workspace link target mismatch: {name}")
            links[name] = resolved
        elif key == "" or key in workspaces.values():
            if "resolved" in entry:
                raise ValidationError(f"unexpected workspace resolved source: {key}")
        else:
            if "node_modules" not in key.split("/"):
                raise ValidationError(f"undeclared workspace in source lock: {key}")
            if any(key.endswith("node_modules/" + name) for name in CRITICAL_WORKSPACES):
                raise ValidationError(f"registry package shadows critical workspace: {key}")
            _validate_registry_url(entry.get("resolved"))
    if links != workspaces:
        raise ValidationError("source lock workspace links do not match declared workspaces")
    pending: list[Any] = [lock]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"npm_auth", "_authToken", "_auth"}:
                    raise ValidationError(f"source lock contains credentials: {path}")
                if key == "resolved" and not any(value is packages["node_modules/" + name] for name in links):
                    _validate_registry_url(item)
                pending.append(item)
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, str) and value.startswith(("file:", "git+", "git://")):
            raise ValidationError(f"source lock contains unsupported source: {path}")
    return links


def validate_installed_workspace_links(install_root: Path, lock_path: Path, *, before_build: bool = False) -> None:
    root = install_root.resolve()
    links = validate_source_lock(lock_path, root)
    pending_bins: dict[Path, Path] = {}
    for name, rel in links.items():
        parent = safe_child(root, "node_modules")
        if "/" in name:
            parent = safe_child(parent, str(Path(name).parent))
        module_link = parent / Path(name).name
        if not module_link.is_symlink() or Path(os.readlink(module_link)).is_absolute():
            raise ValidationError(f"installed workspace link must be a relative symlink: {name}")
        try:
            resolved = module_link.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValidationError(f"installed workspace link is broken: {name}") from exc
        if resolved != safe_child(root, rel):
            raise ValidationError(f"installed workspace link mismatch: {name}")
        if before_build:
            bins = load_json(safe_child(root, rel, "package.json")).get("bin", {})
            if not isinstance(bins, dict):
                raise ValidationError(f"invalid workspace bin map: {name}")
            for command, target in bins.items():
                validate_package_name(command)
                if "/" in command:
                    raise ValidationError(f"invalid workspace bin command: {command}")
                pending_bins[root / "node_modules/.bin" / command] = safe_child(root, rel, relative_path(target, "workspace bin target"))
    _validate_tree_symlinks(root, pending_bins)


def apply_model_snapshot(url: str, expected_sha256: str, target_dir: Path) -> dict[str, str | int]:
    validate_model_snapshot_url(url)
    if not re.fullmatch(r"[0-9a-f]{64}", text(expected_sha256, "modelSnapshot.sha256")):
        raise ValidationError("invalid modelSnapshot.sha256")
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read(SNAPSHOT_DOWNLOAD_LIMIT + 1)
    except OSError as exc:
        raise ValidationError(f"cannot download model snapshot: {exc}") from exc
    if len(payload) > SNAPSHOT_DOWNLOAD_LIMIT:
        raise ValidationError("model snapshot exceeds download limit")
    digest = _sha256_bytes(payload)
    if digest != expected_sha256:
        raise ValidationError("model snapshot sha256 mismatch")
    if target_dir.exists() or target_dir.is_symlink():
        raise ValidationError(f"refusing to overwrite existing model data: {target_dir}")
    selected: dict[str, bytes] = {}
    seen: set[str] = set()
    prefix: str | None = None
    total = 0
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as compressed:
            expanded = compressed.read(SNAPSHOT_EXPANSION_LIMIT + 1)
        if len(expanded) > SNAPSHOT_EXPANSION_LIMIT:
            raise ValidationError("model snapshot exceeds expansion limit")
        with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as archive:
            for count, member in enumerate(archive, 1):
                if count > SNAPSHOT_MEMBER_LIMIT:
                    raise ValidationError("model snapshot exceeds member limit")
                name = member.name.removeprefix("./").rstrip("/")
                match = re.search(r"(?:^|/)" + re.escape(CORE_MODEL_DATA_REL) + r"(?:/|$)", name)
                if match is None:
                    continue
                relative_path(name, "snapshot model data path")
                current_prefix = name[:match.end()].removesuffix("/")
                inner = name[match.end():]
                if prefix is not None and current_prefix != prefix:
                    raise ValidationError("snapshot archive has ambiguous model-data prefix")
                prefix = current_prefix
                if inner in seen:
                    raise ValidationError(f"snapshot duplicate model data entry: {inner}")
                seen.add(inner)
                if not inner and member.isdir():
                    continue
                if not member.isfile() or member.issparse():
                    raise ValidationError(f"snapshot model data member is not a regular file: {name}")
                if not re.fullmatch(r"(?:[a-z0-9][a-z0-9-]*\.json|\.manifest\.json)", inner):
                    raise ValidationError(f"unexpected snapshot model data file: {name}")
                if member.size < 0 or member.size > SNAPSHOT_FILE_LIMIT:
                    raise ValidationError("model snapshot exceeds per-file limit")
                total += member.size
                if total > SNAPSHOT_DATA_LIMIT:
                    raise ValidationError("model snapshot exceeds selected data limit")
                source = archive.extractfile(member)
                if source is None:
                    raise ValidationError(f"cannot extract snapshot member: {name}")
                with source:
                    selected[inner] = source.read(SNAPSHOT_FILE_LIMIT + 1)
                if len(selected[inner]) != member.size:
                    raise ValidationError(f"snapshot file size mismatch: {name}")
        manifest_data = selected.get(".manifest.json")
        if manifest_data is None:
            raise ValidationError("snapshot model data missing .manifest.json")
        manifest = json.loads(manifest_data)
        if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 3:
            raise ValidationError("invalid snapshot model data manifest schema")
        structure_hash = manifest.get("structureHash")
        if not isinstance(structure_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", structure_hash):
            raise ValidationError("snapshot model data manifest lacks structureHash")
        hashes = {name: _sha256_bytes(body) for name, body in selected.items() if name != ".manifest.json"}
        if not hashes or manifest.get("files") != hashes:
            raise ValidationError("snapshot model data manifest file hashes mismatch")
        for name, body in selected.items():
            if not isinstance(json.loads(body), dict):
                raise ValidationError(f"snapshot model data JSON is not an object: {name}")
    except (OSError, EOFError, tarfile.TarError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid model snapshot: {exc}") from exc
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir()
    for name, body in selected.items():
        with safe_child(target_dir, name).open("xb") as stream:
            stream.write(body)
    return {
        "manifestSha256": _sha256_bytes(manifest_data),
        "structureHash": structure_hash,
        "fileCount": len(selected),
    }


def validate_source_core_layout(install_root: Path, *, package: str, version: str) -> dict[str, str]:
    cli = safe_child(install_root, CORE_CLI_REL)
    if not cli.is_file():
        raise ValidationError(f"source core CLI missing: {CORE_CLI_REL}")
    try:
        executable = os.access(cli, os.X_OK)
    except OSError as exc:
        raise ValidationError(f"cannot inspect source core CLI: {cli}") from exc
    if not executable:
        raise ValidationError(f"source core CLI is not executable: {cli}")
    package_json = safe_child(install_root, "packages/coding-agent/package.json")
    meta = load_json(package_json)
    if meta.get("name") != package or meta.get("version") != version:
        raise ValidationError("built coding-agent package identity mismatch")
    workspaces = _declared_workspaces(install_root)
    for rel in CRITICAL_WORKSPACES.values():
        if not safe_child(install_root, rel, "dist/index.js").is_file():
            raise ValidationError(f"critical source core runtime missing: {rel}/dist/index.js")
    runtime_hashes = {"package.json": sha256_file(safe_child(install_root, "package.json"))}
    for rel in workspaces.values():
        workspace = safe_child(install_root, rel)
        roots = [workspace / "package.json", workspace / "src", workspace / "dist"]
        if rel == "packages/coding-agent":
            roots.extend(workspace / name for name in ("README.md", "CHANGELOG.md", "docs", "examples", "containerization.md"))
        for resource in roots:
            key_prefix = resource.relative_to(install_root).as_posix()
            runtime_hashes.update(_hash_runtime_resource(install_root, resource, key_prefix))
    return runtime_hashes


def prepare_source_core(
    stage: Path,
    final: Path,
    *,
    checkout_root: Path,
    core_entry: dict[str, Any],
    descriptor: dict[str, Any],
    node_version: str,
) -> dict[str, Any]:
    source = descriptor["core"]["source"]
    rel = text(source.get("path"), "core.source.path")
    if rel != CORE_SOURCE_SUBMODULE:
        raise ValidationError(f"core.source.path must be {CORE_SOURCE_SUBMODULE}")
    install_root = stage / "pi"
    export_tracked_tree(safe_child(checkout_root, rel), install_root, core_entry["pin"])
    lock_path = safe_child(install_root, "package-lock.json")
    input_lock_sha = sha256_file(lock_path)
    validate_source_lock(lock_path, install_root)
    with tempfile.TemporaryDirectory(prefix="attro-core-home-") as home_dir:
        home = Path(home_dir)
        env = sanitized_build_env(home)
        npm_config = [f"--userconfig={home / '.npmrc'}", f"--globalconfig={home / 'global-npmrc'}"]
        run_command([*NPM_CI, *npm_config], install_root, env=env)
        if sha256_file(lock_path) != input_lock_sha:
            raise ValidationError("dependency lock changed during npm ci: pi")
        validate_installed_workspace_links(install_root, lock_path, before_build=True)
        snapshot = source["modelSnapshot"]
        data_dir = safe_child(install_root, CORE_MODEL_DATA_REL)
        snapshot_meta = apply_model_snapshot(snapshot["url"], snapshot["sha256"], data_dir)
        run_command(CORE_CHECK_MODEL_DATA, install_root, env=env)
        run_command([*CORE_BUILD_OFFLINE, *npm_config], install_root, env=env)
        npm_ver = run_command(["npm", "--version", *npm_config], install_root, env=env, timeout=30).stdout.strip()
        if sha256_file(lock_path) != input_lock_sha:
            raise ValidationError("dependency lock changed during source build: pi")
        validate_installed_workspace_links(install_root, lock_path)
    runtime_hashes = validate_source_core_layout(
        install_root,
        package=descriptor["core"]["package"],
        version=descriptor["core"]["version"],
    )
    return {
        "package": descriptor["core"]["package"],
        "expectedVersion": descriptor["core"]["version"],
        "installedVersion": descriptor["core"]["version"],
        "installMethod": "source",
        "installRoot": str(final / "pi"),
        "piBinary": str(final / "pi" / CORE_CLI_REL),
        "lockFile": str(final / "pi/package-lock.json"),
        "lockSha256": input_lock_sha,
        "nodeMinimum": descriptor["core"]["engines"]["node"],
        "source": {
            "path": rel,
            "origin": text(core_entry.get("origin"), "origin"),
            "commit": text(core_entry.get("pin"), "pin"),
        },
        "buildRecipe": BUILD_RECIPE,
        "buildVersions": {"node": node_version, "npm": npm_ver},
        "modelSnapshot": {
            "url": snapshot["url"],
            "sha256": snapshot["sha256"],
            **snapshot_meta,
        },
        "runtimeHashes": runtime_hashes,
    }
