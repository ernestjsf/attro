#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from attro.cursor_sdk_attribution_patch import (  # noqa: E402
    KNOWN_PATCHES,
    PATCH_ID,
    REPLACEMENTS,
    PatchFileSpec,
    PatchSpec,
    apply_cursor_sdk_attribution_patches,
    normalize_sdk_patches,
    resolve_cursor_sdk_root,
    validate_cursor_sdk_patch_provenance,
    _apply_replacements,
    _file_state,
    _validate_anchors,
    sha256_file_bytes,
)
from attro.state import load_state  # noqa: E402
from attro.validate import ValidationError, sha256_file, validate_descriptor  # noqa: E402

REAL_NODE = shutil.which("node")
REAL_SDK_ROOT = Path.home() / ".pi/agent/npm/node_modules/@cursor/sdk"
REAL_SDK_SMOKE = os.environ.get("ATTRO_REAL_SDK_SMOKE") == "1"

SYNTHETIC_SOURCE = (
    "function commits(y,E){return !y&&(E?.attribution?.attributeCommitsToAgent??!0);}"
    "function prs(y,E){return !y&&(E?.attribution?.attributePRsToAgent??!0);}"
)
TEST_PATCH_ID = "cursor-sdk-attribution-off@test-fixture"


def _build_test_patch_spec() -> PatchSpec:
    files: list[PatchFileSpec] = []
    for relative in ("dist/esm/357.js", "dist/cjs/616.js"):
        original = SYNTHETIC_SOURCE.encode("utf-8")
        patched = _apply_replacements(SYNTHETIC_SOURCE, relative=relative).encode("utf-8")
        files.append(
            PatchFileSpec(
                relative=relative,
                original_sha256=sha256_file_bytes(original),
                patched_sha256=sha256_file_bytes(patched),
            )
        )
    return PatchSpec(patch_id=TEST_PATCH_ID, sdk_version="1.0.27", files=tuple(files))


TEST_PATCH_SPEC = _build_test_patch_spec()


@contextmanager
def test_patch_registry():
    registry = {**KNOWN_PATCHES, TEST_PATCH_ID: TEST_PATCH_SPEC}
    with mock.patch.dict(KNOWN_PATCHES, registry, clear=True):
        yield TEST_PATCH_ID


def _install_synthetic_layout(
    base: Path,
    *,
    hoisted_marker: str | None = None,
    nested_marker: str | None = None,
) -> Path:
    npm_root = base / "npm"
    pi_pkg = npm_root / "node_modules/pi-cursor-sdk"
    pi_pkg.mkdir(parents=True)
    (pi_pkg / "package.json").write_text(json.dumps({"name": "pi-cursor-sdk", "version": "0.3.6"}) + "\n")

    def write_sdk(root: Path, marker: str | None) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "package.json").write_text(json.dumps({"name": "@cursor/sdk", "version": "1.0.27"}) + "\n")
        for spec in TEST_PATCH_SPEC.files:
            target = root / spec.relative
            target.parent.mkdir(parents=True, exist_ok=True)
            content = SYNTHETIC_SOURCE if marker is None else f"{marker}\n{SYNTHETIC_SOURCE}"
            target.write_text(content)

    hoisted_root = npm_root / "node_modules/@cursor/sdk"
    nested_root = pi_pkg / "node_modules/@cursor/sdk"
    if nested_marker is not None:
        write_sdk(nested_root, nested_marker)
    if hoisted_marker is not None or nested_marker is None:
        write_sdk(hoisted_root, hoisted_marker)
    return npm_root


class CursorSdkAttributionPatchTests(unittest.TestCase):
    def test_descriptor_accepts_known_patch_id(self) -> None:
        data = validate_descriptor(ROOT / "attro.json")
        self.assertEqual(data["sdkPatches"], [PATCH_ID])

    def test_unknown_patch_id_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "unknown sdk patch"):
            normalize_sdk_patches(["cursor-sdk-attribution-off@9.9.9"])

    def test_anchor_validation_requires_single_occurrence(self) -> None:
        anchors = " ".join(original for original, _ in REPLACEMENTS)
        _validate_anchors(f"one {anchors} only", relative="fixture.js")
        with self.assertRaisesRegex(ValidationError, "anchor count mismatch"):
            _validate_anchors(anchors + anchors, relative="fixture.js")

    def test_apply_replacements_changes_defaults_only(self) -> None:
        patched = _apply_replacements(SYNTHETIC_SOURCE, relative="dist/esm/357.js")
        self.assertIn("attributeCommitsToAgent??!1", patched)
        self.assertIn("attributePRsToAgent??!1", patched)
        self.assertNotIn("??!0", patched)

    @unittest.skipUnless(REAL_NODE, "node unavailable")
    def test_patched_fallback_preserves_explicit_and_admin_gate(self) -> None:
        original_source = (
            "const commits=!y&&(E?.attribution?.attributeCommitsToAgent??!0);"
            "const prs=!y&&(E?.attribution?.attributePRsToAgent??!0);"
        )
        patched_source = _apply_replacements(original_source, relative="fixture.js")
        self.assertIn("??!1", patched_source)
        self.assertNotIn("??!0", patched_source)
        script = f"""
const originalSource = {json.dumps(original_source)};
const patchedSource = {json.dumps(patched_source)};
function run(source) {{
  const body = source.replace(/^const commits=/, "var commits=").replace(/;const prs=/, "; var prs=") + "; return [commits, prs];";
  const evaluate = new Function("y", "E", body);
  const cases = [
    [true, {{ attribution: {{ attributeCommitsToAgent: true, attributePRsToAgent: true }} }}, false],
    [false, undefined, null],
    [false, {{}}, null],
    [false, {{ attribution: {{ attributeCommitsToAgent: true, attributePRsToAgent: true }} }}, true],
    [false, {{ attribution: {{ attributeCommitsToAgent: false, attributePRsToAgent: false }} }}, false],
  ];
  for (const [y, E, expectedWhenExplicit] of cases) {{
    const [commits, prs] = evaluate(y, E);
    const commitsValue = commits;
    const prsValue = prs;
    if (y) {{
      if (commitsValue !== false || prsValue !== false) process.exit(2);
      continue;
    }}
    if (expectedWhenExplicit === null) {{
      if (source.includes("??!0") && (commitsValue !== true || prsValue !== true)) process.exit(3);
      if (source.includes("??!1") && (commitsValue !== false || prsValue !== false)) process.exit(4);
      continue;
    }}
    if (commitsValue !== expectedWhenExplicit || prsValue !== expectedWhenExplicit) process.exit(5);
  }}
}}
run(originalSource);
run(patchedSource);
"""
        assert REAL_NODE is not None
        completed = subprocess.run([REAL_NODE, "-e", script], check=False, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_resolve_nested_wins_over_hoisted(self) -> None:
        with test_patch_registry():
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp), nested_marker="nested-sdk", hoisted_marker="hoisted-sdk")
                sdk_root = resolve_cursor_sdk_root(npm_root)
                nested = (npm_root / "node_modules/pi-cursor-sdk/node_modules/@cursor/sdk/dist/esm/357.js").resolve()
                self.assertEqual((sdk_root / "dist/esm/357.js").resolve(), nested)
                self.assertTrue(nested.read_text().startswith("nested-sdk"))

    def test_resolve_hoisted_when_nested_missing(self) -> None:
        with test_patch_registry():
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp), hoisted_marker="hoisted-only")
                sdk_root = resolve_cursor_sdk_root(npm_root)
                hoisted = (npm_root / "node_modules/@cursor/sdk/dist/esm/357.js").resolve()
                self.assertEqual((sdk_root / "dist/esm/357.js").resolve(), hoisted)

    def test_npm_root_symlink_rejected(self) -> None:
        with test_patch_registry():
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                npm_root = _install_synthetic_layout(base)
                link = base / "npm-link"
                link.symlink_to(npm_root)
                with self.assertRaisesRegex(ValidationError, "npm install root cannot be a symlink"):
                    resolve_cursor_sdk_root(link)

    def test_pi_cursor_sdk_required(self) -> None:
        with test_patch_registry():
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = Path(tmp) / "npm"
                npm_root.mkdir()
                sdk_root = npm_root / "node_modules/@cursor/sdk"
                sdk_root.mkdir(parents=True)
                (sdk_root / "package.json").write_text(json.dumps({"name": "@cursor/sdk", "version": "1.0.27"}) + "\n")
                with self.assertRaisesRegex(ValidationError, "pi-cursor-sdk not found"):
                    resolve_cursor_sdk_root(npm_root)

    def test_apply_is_idempotent_and_records_maintained_hashes(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                first = apply_cursor_sdk_attribution_patches(npm_root, [patch_id])
                second = apply_cursor_sdk_attribution_patches(npm_root, [patch_id])
                self.assertEqual(first, second)
                sdk_root = resolve_cursor_sdk_root(npm_root)
                for spec in TEST_PATCH_SPEC.files:
                    self.assertEqual(sha256_file(sdk_root / spec.relative), spec.patched_sha256)
                provenance = {"sdkPatchIds": [patch_id], "cursorSdkPatches": first}
                validate_cursor_sdk_patch_provenance(provenance, npm_root, expected_patch_ids=[patch_id])

    def test_preflight_rejects_second_file_bad_anchor_without_touching_first(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                sdk_root = resolve_cursor_sdk_root(npm_root)
                esm_spec, cjs_spec = TEST_PATCH_SPEC.files
                esm = sdk_root / esm_spec.relative
                esm_before = esm.read_bytes()

                def fail_on_cjs(text: str, *, relative: str) -> str:
                    if relative == cjs_spec.relative:
                        raise ValidationError(f"@cursor/sdk patch anchor count mismatch in {relative}: 'broken' (0)")
                    return _apply_replacements(text, relative=relative)

                with mock.patch("attro.cursor_sdk_attribution_patch._apply_replacements", side_effect=fail_on_cjs):
                    with self.assertRaisesRegex(ValidationError, "anchor count mismatch"):
                        apply_cursor_sdk_attribution_patches(npm_root, [patch_id])
                self.assertEqual(esm.read_bytes(), esm_before)
                self.assertEqual(_file_state(esm.read_bytes(), esm_spec), "original")

    def test_preflight_both_files_before_any_write_on_drift(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                sdk_root = resolve_cursor_sdk_root(npm_root)
                esm_spec, cjs_spec = TEST_PATCH_SPEC.files
                esm = sdk_root / esm_spec.relative
                cjs = sdk_root / cjs_spec.relative
                esm.write_text(_apply_replacements(esm.read_text(), relative=esm_spec.relative))
                self.assertEqual(_file_state(esm.read_bytes(), esm_spec), "patched")
                self.assertEqual(_file_state(cjs.read_bytes(), cjs_spec), "original")
                with self.assertRaisesRegex(ValidationError, "patch drift"):
                    apply_cursor_sdk_attribution_patches(npm_root, [patch_id])

    def test_unknown_digest_rejected(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                sdk_root = resolve_cursor_sdk_root(npm_root)
                target = sdk_root / "dist/esm/357.js"
                target.write_bytes(target.read_bytes() + b"\n")
                with self.assertRaisesRegex(ValidationError, "digest mismatch"):
                    apply_cursor_sdk_attribution_patches(npm_root, [patch_id])

    def test_symlink_target_rejected(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                sdk_root = resolve_cursor_sdk_root(npm_root)
                target = sdk_root / "dist/esm/357.js"
                original = target.read_bytes()
                alias = sdk_root / "dist/esm/357-alias.js"
                alias.write_bytes(original)
                target.unlink()
                target.symlink_to(alias)
                with self.assertRaisesRegex(ValidationError, "symlink"):
                    apply_cursor_sdk_attribution_patches(npm_root, [patch_id])

    def test_hardlink_target_rejected(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                sdk_root = resolve_cursor_sdk_root(npm_root)
                target = sdk_root / "dist/esm/357.js"
                original = target.read_bytes()
                alias = sdk_root / "dist/esm/357-alias.js"
                alias.write_bytes(original)
                target.unlink()
                os.link(alias, target)
                with self.assertRaisesRegex(ValidationError, "hard-linked"):
                    apply_cursor_sdk_attribution_patches(npm_root, [patch_id])

    def test_validator_rejects_self_declared_hashes(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                records = apply_cursor_sdk_attribution_patches(npm_root, [patch_id])
                records[0]["files"][0]["sha256"] = "0" * 64
                provenance = {"sdkPatchIds": [patch_id], "cursorSdkPatches": records}
                with self.assertRaisesRegex(ValidationError, "digest mismatch"):
                    validate_cursor_sdk_patch_provenance(provenance, npm_root, expected_patch_ids=[patch_id])

    def test_validator_rejects_duplicate_esm_and_skipped_cjs(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                records = apply_cursor_sdk_attribution_patches(npm_root, [patch_id])
                esm_spec = TEST_PATCH_SPEC.files[0]
                tampered = copy.deepcopy(records)
                tampered[0]["files"] = [
                    {"path": esm_spec.relative, "sha256": esm_spec.patched_sha256},
                    {"path": esm_spec.relative, "sha256": esm_spec.patched_sha256},
                ]
                provenance = {"sdkPatchIds": [patch_id], "cursorSdkPatches": tampered}
                with self.assertRaisesRegex(ValidationError, "duplicate cursor sdk patch file"):
                    validate_cursor_sdk_patch_provenance(provenance, npm_root, expected_patch_ids=[patch_id])

    def test_validator_rejects_tampered_cjs_with_duplicate_esm(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                records = apply_cursor_sdk_attribution_patches(npm_root, [patch_id])
                esm_spec, cjs_spec = TEST_PATCH_SPEC.files
                tampered = copy.deepcopy(records)
                tampered[0]["files"] = [
                    {"path": esm_spec.relative, "sha256": esm_spec.patched_sha256},
                    {"path": esm_spec.relative, "sha256": esm_spec.patched_sha256},
                ]
                sdk_root = resolve_cursor_sdk_root(npm_root)
                (sdk_root / cjs_spec.relative).write_bytes(b"tampered")
                provenance = {"sdkPatchIds": [patch_id], "cursorSdkPatches": tampered}
                with self.assertRaises(ValidationError) as ctx:
                    validate_cursor_sdk_patch_provenance(provenance, npm_root, expected_patch_ids=[patch_id])
                message = str(ctx.exception)
                self.assertTrue(
                    "duplicate cursor sdk patch file" in message or "cursor sdk patch files mismatch" in message,
                    message,
                )
                tampered[0]["files"] = [
                    {"path": esm_spec.relative, "sha256": esm_spec.patched_sha256},
                    {"path": cjs_spec.relative, "sha256": "0" * 64},
                ]
                provenance["cursorSdkPatches"] = tampered
                with self.assertRaisesRegex(ValidationError, "digest mismatch"):
                    validate_cursor_sdk_patch_provenance(provenance, npm_root, expected_patch_ids=[patch_id])

    def test_validator_rejects_installed_cjs_drift_with_valid_provenance(self) -> None:
        with test_patch_registry() as patch_id, tempfile.TemporaryDirectory() as tmp:
            npm_root = _install_synthetic_layout(Path(tmp))
            records = apply_cursor_sdk_attribution_patches(npm_root, [patch_id])
            sdk_root = resolve_cursor_sdk_root(npm_root)
            (sdk_root / TEST_PATCH_SPEC.files[1].relative).write_bytes(b"tampered")
            with self.assertRaisesRegex(ValidationError, "installed cursor sdk patch digest mismatch"):
                validate_cursor_sdk_patch_provenance(
                    {"sdkPatchIds": [patch_id], "cursorSdkPatches": records}, npm_root,
                )

    def test_wrong_sdk_version_rejected(self) -> None:
        with test_patch_registry() as patch_id:
            with tempfile.TemporaryDirectory() as tmp:
                npm_root = _install_synthetic_layout(Path(tmp))
                package_json = resolve_cursor_sdk_root(npm_root) / "package.json"
                package = json.loads(package_json.read_text())
                package["version"] = "1.0.26"
                package_json.write_text(json.dumps(package) + "\n")
                with self.assertRaisesRegex(ValidationError, "version mismatch"):
                    apply_cursor_sdk_attribution_patches(npm_root, [patch_id])


class PreparePatchIntegrationTests(unittest.TestCase):
    def _start_lifecycle(self):
        from tests.test_attro_lifecycle import LifecycleTests

        case = LifecycleTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def _lifecycle_with_synthetic_sdk(self):
        case = self._start_lifecycle()
        synthetic = json.dumps(SYNTHETIC_SOURCE)
        case.descriptor.update(
            {
                "version": "0.2.0",
                "npmPackages": [{"package": "pi-cursor-sdk", "version": "0.3.6"}],
                "sdkPatches": [TEST_PATCH_ID],
            }
        )
        profile = case.repo / "profile/settings.json"
        profile.write_text(json.dumps({"packages": ["{{NPM:pi-cursor-sdk}}"], "themes": ["{{THEME_QUATTRO_GREEN}}"]}))
        case.lock["submodules"][0]["dependencyLock"] = None
        case.commit_inputs()
        fake_npm = case.base / "fakebin/npm"
        marker = '(target / "package.json").write_text(json.dumps({"name": name, "version": version}))'
        replacement = marker + f'''
        if name == "pi-cursor-sdk":
            sdk = root / "node_modules" / "pi-cursor-sdk" / "node_modules" / "@cursor" / "sdk"
            sdk.mkdir(parents=True, exist_ok=True)
            (sdk / "package.json").write_text(json.dumps({{"name": "@cursor/sdk", "version": "1.0.27"}}))
            source = {synthetic}
            for rel in ("dist/esm/357.js", "dist/cjs/616.js"):
                target_file = sdk / rel
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(source)'''
        fake_npm.write_text(
            fake_npm.read_text().replace("import json, os, pathlib, sys", "import json, os, pathlib, sys").replace(marker, replacement)
        )
        return case, case.state, TEST_PATCH_ID

    def test_prepare_records_patch_provenance_and_validates(self) -> None:
        with test_patch_registry() as patch_id:
            case, state, _ = self._lifecycle_with_synthetic_sdk()
            with mock.patch.dict(os.environ, {"ATTRO_HOME": str(state)}, clear=False):
                manifest = json.loads(case.cli("--json", "setup", "--repo", str(case.repo), "--activate")[0])
            self.assertEqual(manifest["provenance"]["sdkPatchIds"], [patch_id])
            self.assertEqual(len(manifest["provenance"]["cursorSdkPatches"]), 1)
            release_path = state / "releases" / manifest["releaseId"]
            from attro.state import prepared_manifest

            prepared_manifest(release_path, manifest["releaseId"])
            original_manifest = copy.deepcopy(manifest)
            for missing_key in ("sdkPatchIds", "cursorSdkPatches"):
                with self.subTest(missing_key=missing_key):
                    malformed = copy.deepcopy(original_manifest)
                    del malformed["provenance"][missing_key]
                    (release_path / "manifest.json").write_text(json.dumps(malformed))
                    with self.assertRaisesRegex(ValidationError, "patch provenance|cursorSdkPatches provenance"):
                        prepared_manifest(release_path, manifest["releaseId"])

    def test_prepare_aborts_when_sdk_patch_targets_missing(self) -> None:
        case = self._start_lifecycle()
        case.descriptor.update(
            {
                "npmPackages": [{"package": "pi-cursor-sdk", "version": "0.3.6"}],
                "sdkPatches": [PATCH_ID],
            }
        )
        profile = case.repo / "profile/settings.json"
        profile.write_text(json.dumps({"packages": ["{{NPM:pi-cursor-sdk}}"], "themes": ["{{THEME_QUATTRO_GREEN}}"]}))
        case.commit_inputs()
        before = load_state(case.state)
        with mock.patch.dict(os.environ, {"ATTRO_HOME": str(case.state)}, clear=False):
            stdout, stderr = case.cli("--json", "setup", "--repo", str(case.repo), success=False)
        combined = stderr.lower() + stdout.lower()
        self.assertIn("not found under npm install root", combined)
        self.assertEqual(load_state(case.state), before)
        self.assertEqual(list((case.state / "releases").iterdir()), [])

    def test_prepare_aborts_on_patch_failure_without_retained_release(self) -> None:
        with test_patch_registry() as patch_id:
            case, state, _ = self._lifecycle_with_synthetic_sdk()
            fake_npm = case.base / "fakebin/npm"
            fake_npm.write_text(
                fake_npm.read_text().replace(
                    'target_file.write_text(source)',
                    'target_file.write_text("broken" if rel.endswith("616.js") else source)',
                )
            )
            before = load_state(state)
            with mock.patch.dict(os.environ, {"ATTRO_HOME": str(state)}, clear=False):
                case.cli("--json", "setup", "--repo", str(case.repo), success=False)
            self.assertEqual(load_state(state), before)
            self.assertEqual(list((state / "releases").iterdir()), [])


@unittest.skipUnless(REAL_SDK_SMOKE and REAL_SDK_ROOT.is_dir(), "set ATTRO_REAL_SDK_SMOKE=1 with real @cursor/sdk@1.0.27")
class RealSdkAttributionSmokeTests(unittest.TestCase):
    def test_real_sdk_patch_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            npm_root = base / "npm"
            pi_pkg = npm_root / "node_modules/pi-cursor-sdk"
            pi_pkg.mkdir(parents=True)
            (pi_pkg / "package.json").write_text(json.dumps({"name": "pi-cursor-sdk", "version": "0.3.6"}) + "\n")
            sdk_root = pi_pkg / "node_modules/@cursor/sdk"
            sdk_root.mkdir(parents=True)
            (sdk_root / "package.json").write_text(json.dumps({"name": "@cursor/sdk", "version": "1.0.27"}) + "\n")
            from attro.cursor_sdk_attribution_patch import CURSOR_SDK_ATTRIBUTION_OFF_1_0_27

            for spec in CURSOR_SDK_ATTRIBUTION_OFF_1_0_27.files:
                target = sdk_root / spec.relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REAL_SDK_ROOT / spec.relative, target)
            first = apply_cursor_sdk_attribution_patches(npm_root, [PATCH_ID])
            second = apply_cursor_sdk_attribution_patches(npm_root, [PATCH_ID])
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
