"""Validation of trusted source inputs and confined release metadata."""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from piattro.constants import PROFILE_PLACEHOLDERS, SUPPORTED_PLATFORMS
from piattro.paths import safe_child

RELEASE_ID_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}")
CORE_PACKAGE = "@earendil-works/pi-coding-agent"
NODE_MIN_RE = re.compile(r">=(\d+)\.(\d+)\.(\d+)")


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValidationError(f"refusing JSON symlink: {path}")
    try:
        data = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"JSON root is not an object: {path}")
    return data


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    if path.is_symlink():
        raise ValidationError(f"refusing JSON symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        fsync_dir(path.parent)
    finally:
        tmp.unlink(missing_ok=True)


def schema(data: dict[str, Any], key: str = "schemaVersion") -> None:
    if type(data.get(key)) is not int or data[key] != 1:
        raise ValidationError(f"unsupported {key}: {data.get(key)!r}")


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def relative_path(value: Any, label: str) -> str:
    value = text(value, label)
    if value.startswith("/") or "\\" in value or "\x00" in value or any(p in {"", ".", "..", ".git"} for p in value.split("/")):
        raise ValidationError(f"invalid {label}: {value!r}")
    return value


def validate_release_id(release_id: Any) -> None:
    if not isinstance(release_id, str) or not RELEASE_ID_RE.fullmatch(release_id):
        raise ValidationError(f"invalid release id: {release_id!r}")


def validate_descriptor(path: Path) -> dict[str, Any]:
    from piattro.npm_packages import normalize_npm_packages, validate_version

    data = load_json(path)
    for key in ("schemaVersion", "stateSchemaVersion", "manifestSchemaVersion"):
        schema(data, key)
    validate_release_id(text(data.get("distribution"), "distribution"))
    validate_version(text(data.get("version"), "version"))
    for key in ("profile", "sourcesLock"):
        relative_path(data.get(key), key)
    core = data.get("core")
    if not isinstance(core, dict) or core.get("package") != CORE_PACKAGE:
        raise ValidationError(f"core.package must be {CORE_PACKAGE}")
    validate_version(text(core.get("version"), "core version"))
    engines = core.get("engines")
    if not isinstance(engines, dict) or not isinstance(engines.get("node"), str) or not NODE_MIN_RE.fullmatch(engines["node"]):
        raise ValidationError("core.engines.node must be an exact minimum (>=major.minor.patch)")
    supported = data.get("supportedPlatforms", sorted(SUPPORTED_PLATFORMS))
    if not isinstance(supported, list) or not supported or any(not isinstance(p, str) or p not in SUPPORTED_PLATFORMS for p in supported):
        raise ValidationError("invalid supportedPlatforms")
    if sys.platform not in supported:
        raise ValidationError(f"unsupported platform {sys.platform}")
    data["npmPackages"] = normalize_npm_packages(data.get("npmPackages", []))
    return data


def validate_state(data: dict[str, Any]) -> None:
    schema(data)
    releases = data.get("releases")
    if not isinstance(releases, dict):
        raise ValidationError("state releases must be an object")
    for rid, entry in releases.items():
        validate_release_id(rid)
        if not isinstance(entry, dict):
            raise ValidationError(f"invalid release record: {rid}")
        text(entry.get("path"), "release path")
        text(entry.get("preparedAt"), "preparedAt")
    for key in ("active", "previous"):
        if key not in data:
            raise ValidationError(f"state missing {key}")
        if data[key] is not None:
            validate_release_id(data[key])
            if data[key] not in releases:
                raise ValidationError(f"state {key} references an unknown release")


def validate_manifest(data: dict[str, Any]) -> None:
    from piattro.npm_packages import normalize_npm_packages, validate_version

    schema(data)
    validate_release_id(text(data.get("releaseId"), "releaseId"))
    for key in ("preparedAt", "checkoutRoot", "distribution", "descriptorVersion"):
        text(data.get(key), key)
    provenance = data.get("provenance")
    if not isinstance(provenance, dict) or not isinstance(data.get("layout"), dict):
        raise ValidationError("manifest requires provenance and layout objects")
    if not re.fullmatch(r"[0-9a-f]{40,64}", text(provenance.get("checkoutHead"), "checkoutHead")):
        raise ValidationError("invalid checkoutHead")
    core = provenance.get("core")
    if not isinstance(core, dict) or core.get("package") != CORE_PACKAGE or core.get("installMethod") != "npm":
        raise ValidationError("invalid core provenance")
    validate_version(text(core.get("expectedVersion"), "expectedVersion"))
    if core.get("installedVersion") != core["expectedVersion"]:
        raise ValidationError("core pin mismatch")
    if not isinstance(core.get("nodeMinimum"), str) or not NODE_MIN_RE.fullmatch(core["nodeMinimum"]):
        raise ValidationError("invalid core node minimum")
    entries = provenance.get("npmPackages")
    normalize_npm_packages(entries)
    if not isinstance(entries, list):
        raise ValidationError("missing npm provenance")
    for record in [core, *entries]:
        for key in ("installRoot", "lockFile"):
            text(record.get(key), key)
        if not re.fullmatch(r"[0-9a-f]{64}", text(record.get("lockSha256"), "lockSha256")):
            raise ValidationError("invalid lock digest")
    text(core.get("piBinary"), "piBinary")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(cmd: list[str], cwd: Path, timeout: int = 900) -> subprocess.CompletedProcess:
    try:
        process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    except OSError as exc:
        raise ValidationError(f"command unavailable: {' '.join(cmd)}: {exc}") from exc
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        if isinstance(exc, KeyboardInterrupt):
            raise
        raise ValidationError(f"command timed out: {' '.join(cmd)}") from exc
    result = subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)
    if result.returncode:
        raise ValidationError(f"command failed in {cwd}: {' '.join(cmd)}\n{(result.stderr or result.stdout).strip()[-8000:]}")
    return result


def git(*args: str, cwd: Path) -> str:
    return run_command(["git", *args], cwd, timeout=60).stdout.strip()


def check_node(requirement: str) -> str:
    expected = NODE_MIN_RE.fullmatch(requirement)
    if expected is None:
        raise ValidationError(f"invalid Node minimum: {requirement}")
    version = run_command(["node", "--version"], Path.cwd(), timeout=10).stdout.strip()
    actual = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", version)
    if actual is None or tuple(map(int, actual.groups())) < tuple(map(int, expected.groups())):
        raise ValidationError(f"Node {version} does not satisfy {requirement}")
    return version


def validate_sources_lock(manifest: dict[str, Any]) -> None:
    schema(manifest)
    if manifest.get("branch") != "quattro":
        raise ValidationError("sources.lock.json branch must be quattro")
    entries, configs = manifest.get("submodules"), manifest.get("configs")
    if not isinstance(entries, list) or not isinstance(configs, list):
        raise ValidationError("sources lock requires submodules and configs arrays")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("invalid submodule entry")
        rel = relative_path(entry.get("path"), "submodule path")
        if len(Path(rel).parts) != 2 or Path(rel).parts[0] != "plugins" or rel in seen:
            raise ValidationError(f"invalid or duplicate submodule path: {rel}")
        seen.add(rel)
        assert_copy_allowed(rel)
        if not re.fullmatch(r"[0-9a-f]{40,64}", text(entry.get("pin"), "pin")):
            raise ValidationError(f"invalid pin for {rel}")
        text(entry.get("origin"), "origin")
        if entry.get("packagePath", ".") != ".":
            relative_path(entry["packagePath"], "packagePath")
        if type(entry.get("runtimeGenerated")) is not bool:
            raise ValidationError("runtimeGenerated must be a boolean")
        if entry["runtimeGenerated"] and rel != "plugins/pi-lens":
            raise ValidationError(f"no reviewed build for {rel}")
        for key in ("sourceEntryFiles", "runtimeEntryFiles"):
            if not isinstance(entry.get(key), list) or not entry[key]:
                raise ValidationError(f"{rel}: {key} must be a non-empty array")
            for value in entry[key]:
                relative_path(value, key)
        lock = entry.get("dependencyLock")
        if lock is not None and lock != "package-lock.json":
            raise ValidationError(f"unsupported dependency lock for {rel}")
    seen = set()
    allowed_configs = {"themes/quattro-green.json", "themes/quattro-amber.json", "config/zentui.json", "config/claude-code-style.json", "config/rpiv-todo.json"}
    for config in configs:
        if not isinstance(config, dict):
            raise ValidationError("invalid config entry")
        rel = relative_path(config.get("path"), "config path")
        if rel not in allowed_configs or rel in seen:
            raise ValidationError(f"config not allowlisted or duplicated: {rel}")
        seen.add(rel)
        if not re.fullmatch(r"[0-9a-f]{64}", text(config.get("sha256"), "config sha256")):
            raise ValidationError(f"invalid config digest: {rel}")


def validate_checkout(root: Path, descriptor: dict[str, Any], runtime: bool = False, *, sources_lock: dict[str, Any] | None = None) -> dict[str, Any]:
    if git("rev-parse", "--show-toplevel", cwd=root) != str(root.resolve()):
        raise ValidationError("--repo must name a Git checkout root")
    if git("status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none", cwd=root):
        raise ValidationError("checkout is dirty (including untracked files/submodules)")
    manifest = sources_lock if sources_lock is not None else load_json(safe_child(root, descriptor["sourcesLock"]))
    validate_sources_lock(manifest)
    for entry in manifest["submodules"]:
        rel, pin = entry["path"], entry["pin"]
        path = safe_child(root, rel)
        stage = git("ls-tree", "HEAD", "--", rel, cwd=root).split()
        if len(stage) != 4 or stage[0] != "160000" or stage[2] != pin:
            raise ValidationError(f"{rel}: gitlink does not match pin")
        if git("rev-parse", "HEAD", cwd=path) != pin:
            raise ValidationError(f"{rel}: HEAD does not match pin")
        if git("status", "--porcelain", "--untracked-files=all", cwd=path):
            raise ValidationError(f"{rel}: dirty submodule")
        if git("remote", "get-url", "origin", cwd=path) != entry["origin"]:
            raise ValidationError(f"{rel}: origin mismatch")
        for name in entry["sourceEntryFiles"] + (entry["runtimeEntryFiles"] if runtime else []):
            if not safe_child(path, name).is_file():
                raise ValidationError(f"{rel}: required file missing: {name}")
    for config in manifest["configs"]:
        cfg = safe_child(root, config["path"])
        if not cfg.is_file() or sha256_file(cfg) != config["sha256"]:
            raise ValidationError(f"config missing or hash mismatch: {config['path']}")
    return manifest


def assert_copy_allowed(rel_path: str) -> None:
    relative_path(rel_path, "copy path")
    path = Path(rel_path.lower())
    if path.name in {"auth.json", "credentials", "credentials.json", "trust.json", ".env"} or path.name.startswith(".env.") or ("sessions" in path.parts and path.suffix == ".jsonl"):
        raise ValidationError(f"refusing to copy private/sensitive path: {rel_path}")


def compute_release_id(descriptor: dict[str, Any], sources_lock: dict[str, Any], checkout_root: Path, *, head: str | None = None) -> str:
    digest = hashlib.sha256(json.dumps({"descriptor": descriptor, "sourcesLock": sources_lock, "head": head or git("rev-parse", "HEAD", cwd=checkout_root)}, sort_keys=True).encode()).hexdigest()[:12]
    rid = f"{descriptor['distribution']}-{descriptor['version']}-{digest}"
    validate_release_id(rid)
    return rid


def render_profile(profile_text: str, release_root: Path, checkout_root: Path, descriptor: dict[str, Any] | None = None) -> str:
    from piattro.npm_packages import npm_package_install_dir

    try:
        payload = json.loads(profile_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid profile JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError("profile must be an object")
    release_root = release_root.resolve()
    replacements = {key: str(release_root / value) for key, value in PROFILE_PLACEHOLDERS.items()}
    for key in ("packages", "themes", "extensions", "skills", "prompts"):
        values = payload.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise ValidationError(f"profile {key} must be an array of paths")
        payload[key] = [replacements.get(value, value) for value in values]
        if any("{{" in value for value in payload[key]):
            raise ValidationError(f"unresolved profile placeholder in {key}")
    for entry in (descriptor or {}).get("npmPackages", []):
        payload["packages"].append(str(npm_package_install_dir(release_root, entry["package"])))
    return json.dumps(payload, indent=2) + "\n"
