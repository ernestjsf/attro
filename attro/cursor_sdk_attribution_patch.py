"""Versioned @cursor/sdk attribution-default patch for Attro release staging."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from attro.paths import safe_child
from attro.validate import ValidationError, sha256_file

PATCH_ID = "cursor-sdk-attribution-off@1.0.27"
SDK_PACKAGE = "@cursor/sdk"
SDK_VERSION = "1.0.27"
PI_CURSOR_SDK_PACKAGE = "pi-cursor-sdk"

REPLACEMENTS = (
    ("attributeCommitsToAgent??!0", "attributeCommitsToAgent??!1"),
    ("attributePRsToAgent??!0", "attributePRsToAgent??!1"),
)

FileState = Literal["original", "patched", "unknown"]


@dataclass(frozen=True)
class PatchFileSpec:
    relative: str
    original_sha256: str
    patched_sha256: str


@dataclass(frozen=True)
class PatchSpec:
    patch_id: str
    sdk_version: str
    files: tuple[PatchFileSpec, ...]


CURSOR_SDK_ATTRIBUTION_OFF_1_0_27 = PatchSpec(
    patch_id=PATCH_ID,
    sdk_version=SDK_VERSION,
    files=(
        PatchFileSpec(
            relative="dist/esm/357.js",
            original_sha256="8ee157b4a4af0283e1ce50effd6ae4db5ae0fd4c863dfe63fbe9aafe72815385",
            patched_sha256="9fe35cbda99e28653775ea013e5b0b7b0556a5cf1ad4e292da8852c290cd171a",
        ),
        PatchFileSpec(
            relative="dist/cjs/616.js",
            original_sha256="e802a95118eafb51c46133cc3bc5bb92aa8f68915eecd3cf74f0fab231901a0f",
            patched_sha256="e6a7022ccc71c8a8062413f8933bc8f8ddd68edead6da148f5979a23ab7b5cfb",
        ),
    ),
)

KNOWN_PATCHES: dict[str, PatchSpec] = {PATCH_ID: CURSOR_SDK_ATTRIBUTION_OFF_1_0_27}


def normalize_sdk_patches(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValidationError("attro.json sdkPatches must be an array")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, patch_id in enumerate(raw):
        if not isinstance(patch_id, str) or not patch_id.strip():
            raise ValidationError(f"sdkPatches[{index}] must be a non-empty string")
        patch_id = patch_id.strip()
        if patch_id not in KNOWN_PATCHES:
            raise ValidationError(f"unknown sdk patch: {patch_id!r}")
        if patch_id in seen:
            raise ValidationError(f"duplicate sdk patch: {patch_id!r}")
        seen.add(patch_id)
        normalized.append(patch_id)
    return normalized


def _read_confined_file(sdk_root: Path, relative: str) -> Path:
    path = safe_child(sdk_root, *relative.split("/"))
    if not path.is_file():
        raise ValidationError(f"@cursor/sdk patch target missing: {relative}")
    if path.is_symlink():
        raise ValidationError(f"@cursor/sdk patch target is a symlink: {relative}")
    try:
        if path.stat().st_nlink != 1:
            raise ValidationError(f"@cursor/sdk patch target must not be hard-linked: {relative}")
    except OSError as exc:
        raise ValidationError(f"cannot inspect @cursor/sdk patch target: {relative}") from exc
    return path


def _file_state(content: bytes, spec: PatchFileSpec) -> FileState:
    digest = sha256_file_bytes(content)
    if digest == spec.original_sha256:
        return "original"
    if digest == spec.patched_sha256:
        return "patched"
    return "unknown"


def sha256_file_bytes(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()


def _validate_anchors(text: str, *, relative: str) -> None:
    for original, _ in REPLACEMENTS:
        count = text.count(original)
        if count != 1:
            raise ValidationError(f"@cursor/sdk patch anchor count mismatch in {relative}: {original!r} ({count})")


def _apply_replacements(text: str, *, relative: str) -> str:
    _validate_anchors(text, relative=relative)
    patched = text
    for original, replacement in REPLACEMENTS:
        patched = patched.replace(original, replacement, 1)
    return patched


def _validated_sdk_root(candidate: Path) -> Path | None:
    package_json = safe_child(candidate, "package.json")
    if not package_json.is_file():
        return None
    from attro.validate import load_json

    package = load_json(package_json)
    if package.get("name") != SDK_PACKAGE:
        raise ValidationError(f"unexpected package name at {candidate}")
    if package.get("version") != SDK_VERSION:
        raise ValidationError(f"@cursor/sdk version mismatch: expected {SDK_VERSION}, found {package.get('version')!r}")
    return candidate


def resolve_cursor_sdk_root(npm_install_root: Path) -> Path:
    if npm_install_root.is_symlink():
        raise ValidationError("npm install root cannot be a symlink")
    npm_install_root = npm_install_root.resolve()
    pi_cursor_sdk = safe_child(npm_install_root, "node_modules", PI_CURSOR_SDK_PACKAGE)
    if not pi_cursor_sdk.is_dir() or not safe_child(pi_cursor_sdk, "package.json").is_file():
        raise ValidationError(f"{PI_CURSOR_SDK_PACKAGE} not found under npm install root")
    nested = safe_child(npm_install_root, "node_modules", PI_CURSOR_SDK_PACKAGE, "node_modules", "@cursor", "sdk")
    hoisted = safe_child(npm_install_root, "node_modules", "@cursor", "sdk")
    nested_root = _validated_sdk_root(nested)
    if nested_root is not None:
        return nested_root
    hoisted_root = _validated_sdk_root(hoisted)
    if hoisted_root is not None:
        return hoisted_root
    raise ValidationError(f"{SDK_PACKAGE}@{SDK_VERSION} not found under npm install root")


def apply_cursor_sdk_attribution_patches(npm_install_root: Path, patch_ids: list[str]) -> list[dict[str, Any]]:
    normalized = normalize_sdk_patches(patch_ids)
    if not normalized:
        return []
    sdk_root = resolve_cursor_sdk_root(npm_install_root)
    records: list[dict[str, Any]] = []
    for patch_id in normalized:
        spec = KNOWN_PATCHES[patch_id]
        file_states: list[tuple[PatchFileSpec, Path, bytes, FileState]] = []
        for file_spec in spec.files:
            path = _read_confined_file(sdk_root, file_spec.relative)
            content = path.read_bytes()
            state = _file_state(content, file_spec)
            if state == "unknown":
                raise ValidationError(f"@cursor/sdk digest mismatch for {file_spec.relative}")
            file_states.append((file_spec, path, content, state))
        states = {state for _, _, _, state in file_states}
        if states == {"patched"}:
            pass
        elif states == {"original"}:
            pending_writes: list[tuple[Path, bytes]] = []
            for file_spec, path, content, _ in file_states:
                patched_text = _apply_replacements(content.decode("utf-8"), relative=file_spec.relative)
                patched_bytes = patched_text.encode("utf-8")
                if sha256_file_bytes(patched_bytes) != file_spec.patched_sha256:
                    raise ValidationError(f"@cursor/sdk patched digest mismatch for {file_spec.relative}")
                pending_writes.append((path, patched_bytes))
            for path, patched_bytes in pending_writes:
                path.write_bytes(patched_bytes)
                with path.open("rb") as handle:
                    os.fsync(handle.fileno())
        else:
            raise ValidationError(f"@cursor/sdk patch drift: mixed original and patched files for {patch_id}")
        records.append(
            {
                "id": spec.patch_id,
                "sdkVersion": spec.sdk_version,
                "sdkRootRel": sdk_root.resolve().relative_to(npm_install_root.resolve()).as_posix(),
                "files": [
                    {"path": file_spec.relative, "sha256": file_spec.patched_sha256}
                    for file_spec in spec.files
                ],
            }
        )
    return records


def validate_cursor_sdk_patch_provenance(
    provenance: dict[str, Any],
    npm_install_root: Path,
    *,
    expected_patch_ids: list[str] | None = None,
) -> None:
    recorded_ids = provenance.get("sdkPatchIds")
    if recorded_ids is None:
        if expected_patch_ids or "sdkPatchIds" in provenance or "cursorSdkPatches" in provenance:
            raise ValidationError("manifest missing sdk patch provenance")
        return
    if not isinstance(recorded_ids, list) or any(not isinstance(value, str) for value in recorded_ids):
        raise ValidationError("invalid sdkPatchIds provenance")
    normalized_expected = normalize_sdk_patches(expected_patch_ids or recorded_ids)
    if normalize_sdk_patches(recorded_ids) != normalized_expected:
        raise ValidationError("sdkPatchIds provenance mismatch")
    records = provenance.get("cursorSdkPatches")
    if not isinstance(records, list):
        raise ValidationError("manifest missing cursorSdkPatches provenance")
    if len(records) != len(normalized_expected):
        raise ValidationError("cursorSdkPatches provenance count mismatch")
    sdk_root = resolve_cursor_sdk_root(npm_install_root)
    by_id = {record["id"]: record for record in records if isinstance(record, dict) and isinstance(record.get("id"), str)}
    for patch_id in normalized_expected:
        spec = KNOWN_PATCHES[patch_id]
        record = by_id.get(patch_id)
        if record is None:
            raise ValidationError(f"manifest missing cursor sdk patch record: {patch_id}")
        if record.get("sdkVersion") != spec.sdk_version:
            raise ValidationError(f"unexpected cursor sdk patch version for {patch_id}")
        sdk_root_rel = sdk_root.resolve().relative_to(npm_install_root.resolve()).as_posix()
        if record.get("sdkRootRel") != sdk_root_rel:
            raise ValidationError(f"cursor sdk patch root mismatch for {patch_id}")
        files = record.get("files")
        if not isinstance(files, list) or len(files) != len(spec.files):
            raise ValidationError(f"invalid cursor sdk patch files for {patch_id}")
        expected_files = {file_spec.relative: file_spec for file_spec in spec.files}
        seen_paths: set[str] = set()
        for entry in files:
            if not isinstance(entry, dict):
                raise ValidationError(f"invalid cursor sdk patch file record for {patch_id}")
            relative = entry.get("path")
            digest = entry.get("sha256")
            if not isinstance(relative, str) or relative not in expected_files:
                raise ValidationError(f"unexpected cursor sdk patch file for {patch_id}: {relative!r}")
            if relative in seen_paths:
                raise ValidationError(f"duplicate cursor sdk patch file for {patch_id}: {relative!r}")
            seen_paths.add(relative)
            file_spec = expected_files[relative]
            if digest != file_spec.patched_sha256:
                raise ValidationError(f"cursor sdk patch digest mismatch for {patch_id}: {relative}")
            path = _read_confined_file(sdk_root, relative)
            if sha256_file(path) != file_spec.patched_sha256:
                raise ValidationError(f"installed cursor sdk patch digest mismatch for {patch_id}: {relative}")
        if seen_paths != set(expected_files):
            raise ValidationError(f"cursor sdk patch files mismatch for {patch_id}")
