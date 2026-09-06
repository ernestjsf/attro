"""Descriptor npm package pins and release-local install paths."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from attro.validate import ValidationError

PACKAGE_NAME_RE = re.compile(
    r"(?:(@[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*)|([a-z0-9][a-z0-9._-]*))"
)
VERSION_RE = re.compile(
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
NPM_SPEC_RE = re.compile(
    r"^(?:(@[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)|([a-zA-Z0-9._-]+))@(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-.+a-zA-Z0-9._]*)?$"
)


def parse_npm_spec(spec: str) -> tuple[str, str]:
    match = NPM_SPEC_RE.match(spec.strip())
    if not match:
        raise ValidationError(f"invalid npm package spec: {spec!r}")
    package = match.group(1) or match.group(2)
    version = spec.strip().rsplit("@", 1)[-1]
    return package, version


def npm_spec(package: str, version: str) -> str:
    return f"{package}@{version}"


def validate_package_name(package: Any) -> str:
    if not isinstance(package, str) or not PACKAGE_NAME_RE.fullmatch(package):
        raise ValidationError(f"invalid npm package name: {package!r}")
    return package


def validate_version(version: Any) -> str:
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise ValidationError(f"invalid npm package version: {version!r}")
    return version


def npm_package_install_dir(release_root: Path, package_name: str) -> Path:
    validate_package_name(package_name)
    if package_name.startswith("@"):
        scope, name = package_name.split("/", 1)
        return release_root / "npm" / "node_modules" / scope / name
    return release_root / "npm" / "node_modules" / package_name


def normalize_npm_packages(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        raise ValidationError("attro.json npmPackages must be an array")
    normalized: list[dict[str, str]] = []
    seen_packages: set[str] = set()
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValidationError(f"npmPackages[{index}] must be an object")
        package_raw = entry.get("package")
        version_raw = entry.get("version")
        if not isinstance(package_raw, str) or not package_raw.strip():
            raise ValidationError(f"npmPackages[{index}].package must be a non-empty string")
        if not isinstance(version_raw, str) or not version_raw.strip():
            raise ValidationError(f"npmPackages[{index}].version must be a non-empty string")
        package = validate_package_name(package_raw)
        version = validate_version(version_raw)
        if package in seen_packages:
            raise ValidationError(f"duplicate npm package: {package}")
        seen_packages.add(package)
        normalized.append({"package": package, "version": version})
    return normalized


def npm_dependencies_from_entries(entries: list[dict[str, str]]) -> dict[str, str]:
    deps: dict[str, str] = {}
    for entry in entries:
        package = entry["package"]
        version = entry["version"]
        if package in deps and deps[package] != version:
            raise ValidationError(f"conflicting versions for npm package {package}")
        deps[package] = version
    return deps
