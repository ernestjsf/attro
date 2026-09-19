"""Offline tests for source-built Pi core preparation."""

from __future__ import annotations

import contextlib
import io
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from attro.cli import main
from attro.constants import CORE_CLI_REL, CORE_MODEL_DATA_REL, CORE_SOURCE_SUBMODULE
from attro.core_source import (
    apply_model_snapshot,
    sanitized_build_env,
    validate_source_core_layout,
    validate_installed_workspace_links,
    validate_source_lock,
)
from attro.validate import ValidationError, run_command, sha256_file, validate_descriptor
from attro.state import prepared_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_URL = "https://github.com/earendil-works/pi/releases/download/v0.85.0/pi-0.85.0-source.tar.gz"
CORE_UPSTREAM_COMMIT = "107d79f11072bbc8a3a757ed7fd69596bee7d68c"
CORE_UPSTREAM_TREE = "f5103239060686ea2983e18906857b3df54428f5"
CORE_FORK_ROOT_COMMIT = "36b02b695383ad89bc3a22b73633be3fa27be3c1"

class SourceCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "checkout"
        self.repo.mkdir()
        self.state = self.base / "managed"
        self.git("init")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.snapshot_path = self.base / "model-snapshot.tar.gz"
        self.snapshot_sha = self._write_model_snapshot(self.snapshot_path)
        download = mock.patch("attro.core_source.urllib.request.urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(self.snapshot_path.read_bytes()))
        download.start()
        self.addCleanup(download.stop)
        self.core = self.repo / CORE_SOURCE_SUBMODULE
        self._init_core_submodule()
        plugin = self.repo / "plugins/rpiv-mono"
        plugin.mkdir(parents=True)
        self.git("init", cwd=plugin)
        self.git("config", "user.name", "Fixture", cwd=plugin)
        self.git("config", "user.email", "fixture@example.invalid", cwd=plugin)
        self.git("remote", "add", "origin", "https://example.invalid/rpiv.git", cwd=plugin)
        package = plugin / "packages/rpiv-todo"
        package.mkdir(parents=True)
        (package / "index.ts").write_text("export default () => {};\n")
        (package / "package.json").write_text('{"name":"rpiv-todo","pi":{"extensions":["index.ts"]}}')
        (plugin / "package.json").write_text('{"name":"rpiv-mono"}')
        self.git("add", ".", cwd=plugin)
        self.git("commit", "-m", "plugin", cwd=plugin)
        self.plugin_pin = self.git("rev-parse", "HEAD", cwd=plugin)
        self.descriptor = {
            "schemaVersion": 1,
            "distribution": "attro",
            "version": "0.2.0",
            "stateSchemaVersion": 1,
            "manifestSchemaVersion": 1,
            "profile": "profile/settings.json",
            "sourcesLock": "sources.lock.json",
            "runtimeLocks": {"npm": "runtime/npm"},
            "core": {
                "package": "@earendil-works/pi-coding-agent",
                "version": "0.85.0",
                "installMethod": "source",
                "engines": {"node": ">=22.19.0"},
                "source": {
                    "path": CORE_SOURCE_SUBMODULE,
                    "modelSnapshot": {
                        "url": SNAPSHOT_URL,
                        "sha256": self.snapshot_sha,
                    },
                },
            },
            "npmPackages": [{"package": "fixture-addon", "version": "1.2.3"}],
        }
        profile = self.repo / "profile"
        profile.mkdir()
        (profile / "settings.json").write_text(json.dumps({"packages": ["{{PLUGIN_RPIV_TODO}}"], "themes": ["{{THEME_QUATTRO_GREEN}}"]}))
        (self.repo / "themes").mkdir()
        theme = self.repo / "themes/quattro-green.json"
        theme.write_text("{}\n")
        docs = self.repo / "docs"
        docs.mkdir()
        shutil.copyfile(REPO_ROOT / "docs/core-provenance.md", docs / "core-provenance.md")
        self.lock = {
            "schemaVersion": 1,
            "branch": "quattro",
            "submodules": [
                {
                    "path": CORE_SOURCE_SUBMODULE,
                    "name": "pi-monorepo",
                    "origin": "https://example.invalid/attro-core.git",
                    "upstream": "https://github.com/earendil-works/pi-mono.git",
                    "pin": self.core_pin,
                    "baseCommit": CORE_UPSTREAM_COMMIT,
                    "forkRootCommit": CORE_FORK_ROOT_COMMIT,
                    "baseVersion": "0.85.0",
                    "packagePath": ".",
                    "runtimeGenerated": True,
                    "sourceEntryFiles": ["package.json", "package-lock.json", "packages/coding-agent/package.json"],
                    "runtimeEntryFiles": [CORE_CLI_REL],
                    "dependencyLock": "package-lock.json",
                    "dependencyLockVersion": 3,
                    "sourceArchive": {
                        "url": SNAPSHOT_URL,
                        "sha256": self.snapshot_sha,
                        "commit": CORE_UPSTREAM_COMMIT,
                        "tree": CORE_UPSTREAM_TREE,
                    },
                    "forkComparison": {
                        "pin": self.core_pin,
                        "method": "git-archive-pinned-commit-vs-release-archive",
                        "forkTreePathCount": 1688,
                        "commonPathCount": 1658,
                        "identicalPathCount": 1588,
                        "differentPathCount": 70,
                        "forkOnlyPathCount": 30,
                        "archiveOnlyPathCount": 40,
                        "archiveOnlyNote": "All 40 archive-only paths are generated provider model data under packages/ai/src/providers/data.",
                    },
                    "provenance": "docs/core-provenance.md",
                },
                {
                    "path": "plugins/rpiv-mono",
                    "origin": "https://example.invalid/rpiv.git",
                    "pin": self.plugin_pin,
                    "packagePath": "packages/rpiv-todo",
                    "runtimeGenerated": False,
                    "sourceEntryFiles": ["packages/rpiv-todo/index.ts"],
                    "runtimeEntryFiles": ["packages/rpiv-todo/index.ts"],
                    "dependencyLock": None,
                },
            ],
            "configs": [{"path": "themes/quattro-green.json", "sha256": sha256_file(theme)}],
        }
        self.write_runtime_locks()
        self.npm_log = self.base / "fixture-npm.log"
        fakebin = self.base / "fakebin"
        fakebin.mkdir()
        npm = fakebin / "npm"
        npm.write_text(
            "#!/usr/bin/env python3\n"
            + f"""import json, os, pathlib, sys
root = pathlib.Path.cwd()
log = pathlib.Path({json.dumps(str(self.npm_log))})
args = sys.argv[1:]
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("a") as fh:
    fh.write("npm " + " ".join(args) + "\\n")

def install_deps():
    package_path = root / "package.json"
    if not package_path.is_file():
        return
    package = json.loads(package_path.read_text())
    for name, version in package.get("dependencies", {{}}).items():
        target = root / "node_modules" / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "package.json").write_text(json.dumps({{"name": name, "version": version}}))

def workspace_layout():
    for rel in ("packages/coding-agent", "packages/ai", "packages/tui"):
        (root / rel).mkdir(parents=True, exist_ok=True)
    coding = root / "packages/coding-agent"
    cli = coding / "dist/bundle/cli.js"
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text("#!/usr/bin/env node\\nconsole.log('fixture pi');\\n")
    cli.chmod(0o755)
    (coding / "dist/index.js").write_text("export {{}};\\n")
    (root / "packages/tui/dist").mkdir(parents=True, exist_ok=True)
    (root / "packages/ai/dist").mkdir(parents=True, exist_ok=True)
    (root / "packages/tui/dist/index.js").write_text("exports.tui = true;\\n")
    (root / "packages/ai/dist/index.js").write_text("exports.ai = true;\\n")
    for name, rel in [
        ("@earendil-works/pi-coding-agent", "packages/coding-agent"),
        ("@earendil-works/pi-ai", "packages/ai"),
        ("@earendil-works/pi-tui", "packages/tui"),
    ]:
        target = root / "node_modules" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            os.symlink(os.path.relpath(root / rel, target.parent), target)

def is_core_monorepo():
    return (root / "packages/coding-agent/package.json").is_file()

if os.environ.get("FIXTURE_NPM_FAIL"):
    sys.exit("fixture npm failed")

if args[:2] == ["run", "build:offline"]:
    if is_core_monorepo():
        workspace_layout()
        if pathlib.Path({json.dumps(str(self.base / 'rewrite-build'))}).exists():
            (root / "package-lock.json").write_text("{{}}")
        if pathlib.Path({json.dumps(str(self.base / 'break-build-link'))}).exists():
            link = root / "node_modules/@earendil-works/pi-tui"
            link.unlink()
            link.mkdir()
    sys.exit(0)

if args[:1] == ["ci"]:
    lock_path = root / "package-lock.json"
    if not lock_path.is_file():
        sys.exit("fixture npm ci: missing package-lock.json")
    before = lock_path.read_bytes()
    if is_core_monorepo():
        workspace_layout()
    else:
        install_deps()
    if is_core_monorepo() and pathlib.Path({json.dumps(str(self.base / 'rewrite-ci'))}).exists():
        lock_path.write_text(json.dumps({{"lockfileVersion": 3, "packages": {{}}, "fixture": "rewritten"}}))
    elif lock_path.read_bytes() != before:
        sys.exit("fixture npm ci: unexpected lock mutation")
    sys.exit(0)

if args[:1] == ["--version"]:
    print("10.0.0")
    sys.exit(0)

(root / "package-lock.json").write_text(json.dumps({{"lockfileVersion": 3, "packages": {{}}}}))
"""
        )
        npm.chmod(0o755)
        node = fakebin / "node"
        node.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo "${FIXTURE_NODE_VERSION:-v26.0.0}"; exit 0; fi\nexit 0\n')
        node.chmod(0o755)
        env = mock.patch.dict(os.environ, {"PATH": str(fakebin) + os.pathsep + os.environ["PATH"]})
        env.start()
        self.addCleanup(env.stop)
        self.commit_inputs()

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, check=True, capture_output=True, text=True).stdout.strip()

    def _write_model_snapshot(self, path: Path) -> str:
        payload = json.dumps({"anthropic": {"messages": {"claude-3": {}}}}).encode()
        manifest = {
            "schemaVersion": 3,
            "generatedAt": "2026-01-01T00:00:00Z",
            "structureHash": "a" * 64,
            "files": {"anthropic.json": hashlib.sha256(payload).hexdigest()},
        }
        with tarfile.open(path, "w:gz") as archive:
            data = json.dumps(manifest).encode()
            for name, body in (
                (f"{CORE_MODEL_DATA_REL}/.manifest.json", data),
                (f"{CORE_MODEL_DATA_REL}/anthropic.json", payload),
            ):
                info = tarfile.TarInfo(name=name)
                info.size = len(body)
                archive.addfile(info, io.BytesIO(body))
        return sha256_file(path)

    def _init_core_submodule(self) -> None:
        self.core.mkdir(parents=True)
        self.git("init", cwd=self.core)
        self.git("config", "user.name", "Fixture", cwd=self.core)
        self.git("config", "user.email", "fixture@example.invalid", cwd=self.core)
        self.git("remote", "add", "origin", "https://example.invalid/attro-core.git", cwd=self.core)
        (self.core / "package.json").write_text('{"name":"pi-monorepo","private":true,"workspaces":["packages/*"]}\n')
        coding = self.core / "packages/coding-agent"
        coding.mkdir(parents=True)
        (coding / "package.json").write_text('{"name":"@earendil-works/pi-coding-agent","version":"0.85.0"}\n')
        lock = {
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "pi-monorepo", "workspaces": ["packages/*"]},
                "node_modules/@earendil-works/pi-coding-agent": {"link": True, "resolved": "packages/coding-agent"},
                "node_modules/@earendil-works/pi-ai": {"link": True, "resolved": "packages/ai"},
                "node_modules/@earendil-works/pi-tui": {"link": True, "resolved": "packages/tui"},
                "node_modules/lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                },
            },
        }
        for short in ("coding-agent", "ai", "tui"):
            rel = f"packages/{short}"
            pkg = self.core / rel
            pkg.mkdir(parents=True, exist_ok=True)
            meta = {"name": f"@earendil-works/pi-{short}", "version": "0.85.0"}
            (pkg / "package.json").write_text(json.dumps(meta))
            lock["packages"][rel] = meta
        (self.core / "package-lock.json").write_text(json.dumps(lock, sort_keys=True) + "\n")
        check_script = self.core / "packages/ai/scripts/check-model-data.ts"
        check_script.parent.mkdir(parents=True, exist_ok=True)
        check_script.write_text("// fixture\n")
        self.git("add", ".", cwd=self.core)
        self.git("commit", "-m", "core", cwd=self.core)
        self.core_pin = self.git("rev-parse", "HEAD", cwd=self.core)

    def write_runtime_locks(self):
        npm_dir = self.repo / "runtime/npm"
        npm_dir.mkdir(parents=True, exist_ok=True)
        (npm_dir / "package.json").write_text(
            json.dumps({"name": "attro-release-npm", "private": True, "dependencies": {"fixture-addon": "1.2.3"}}, sort_keys=True) + "\n"
        )
        (npm_dir / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {}}) + "\n")

    def commit_inputs(self):
        (self.repo / "attro.json").write_text(json.dumps(self.descriptor, sort_keys=True) + "\n")
        (self.repo / "sources.lock.json").write_text(json.dumps(self.lock, sort_keys=True) + "\n")
        self.git("add", "-A")
        if subprocess.run(["git", "status", "--porcelain"], cwd=self.repo, capture_output=True, text=True).stdout.strip():
            self.git("commit", "-m", "inputs")

    def cli(self, *args, success=True):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(["--state-root", str(self.state), *args])
        if success:
            self.assertEqual(result, 0, stderr.getvalue())
        else:
            self.assertNotEqual(result, 0, stdout.getvalue())
        return stdout.getvalue(), stderr.getvalue()

    def test_descriptor_accepts_source_core(self):
        data = validate_descriptor(REPO_ROOT / "attro.json")
        self.assertEqual(data["core"]["installMethod"], "source")
        self.assertEqual(data["core"]["source"]["path"], CORE_SOURCE_SUBMODULE)
        self.assertNotIn("core", data.get("runtimeLocks", {}))

    def test_source_lock_rejects_registry_tamper(self):
        lock_path = self.core / "package-lock.json"
        lock = json.loads(lock_path.read_text())
        lock["packages"]["node_modules/evil"] = {
            "version": "1.0.0",
            "resolved": "https://evil.example/pkg.tgz",
        }
        lock_path.write_text(json.dumps(lock))
        with self.assertRaises(ValidationError):
            validate_source_lock(lock_path, self.core)

    def test_snapshot_rejects_traversal(self):
        bad = self.base / "bad.tar.gz"
        manifest = {"schemaVersion": 3, "generatedAt": "x", "structureHash": "a" * 64, "files": {}}
        with tarfile.open(bad, "w:gz") as archive:
            body = b"{}"
            info = tarfile.TarInfo(name=f"{CORE_MODEL_DATA_REL}/../escape.json")
            info.size = len(body)
            archive.addfile(info, io.BytesIO(body))
        digest = sha256_file(bad)
        target = self.base / "data"
        with mock.patch("attro.core_source.urllib.request.urlopen", return_value=io.BytesIO(bad.read_bytes())):
            with self.assertRaises(ValidationError):
                apply_model_snapshot(SNAPSHOT_URL, digest, target)

    def test_prepare_source_core_green(self):
        output, _ = self.cli("--json", "setup", "--repo", str(self.repo), "--activate")
        manifest = json.loads(output)
        core = manifest["provenance"]["core"]
        self.assertEqual(core["installMethod"], "source")
        self.assertEqual(core["source"]["commit"], self.core_pin)
        self.assertIn("modelSnapshot", core)
        release = self.state / "releases" / manifest["releaseId"]
        cli = release / "pi" / CORE_CLI_REL
        self.assertTrue(cli.is_file())
        self.assertTrue(os.access(cli, os.X_OK))

    def test_tampered_lock_fails_before_activation(self):
        (self.base / "rewrite-ci").touch()
        _, stderr = self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertIn("dependency lock changed during npm ci", stderr)
        self.assertFalse((self.state / "state.json").exists())

    def test_build_lock_rewrite_rejected(self):
        (self.base / "rewrite-build").touch()
        _, stderr = self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertIn("dependency lock changed during source build", stderr)
        self.assertFalse((self.state / "state.json").exists())

    def test_build_workspace_link_replacement_rejected(self):
        (self.base / "break-build-link").touch()
        _, stderr = self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertIn("workspace link", stderr)
        self.assertFalse((self.state / "state.json").exists())

    def test_activation_requires_complete_runtime_hash_set(self):
        output, _ = self.cli("--json", "setup", "--repo", str(self.repo))
        manifest = json.loads(output)
        release = self.state / "releases" / manifest["releaseId"]
        manifest["provenance"]["core"]["runtimeHashes"] = {CORE_CLI_REL: sha256_file(release / "pi" / CORE_CLI_REL)}
        (release / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValidationError, "runtime digest"):
            prepared_manifest(release)

    def test_activation_rejects_added_or_modified_runtime_assets(self):
        output, _ = self.cli("--json", "setup", "--repo", str(self.repo))
        manifest = json.loads(output)
        release = self.state / "releases" / manifest["releaseId"]
        extra = release / "pi/packages/tui/dist/editor.js"
        extra.write_text("tampered")
        with self.assertRaisesRegex(ValidationError, "runtime digest"):
            prepared_manifest(release)
        extra.unlink()
        asset = release / "pi" / CORE_MODEL_DATA_REL / "anthropic.json"
        asset.write_text("{}")
        with self.assertRaisesRegex(ValidationError, "runtime digest"):
            prepared_manifest(release)

    def test_descriptor_rejects_nonobject_runtime_locks(self):
        for value in ([], "wrong", 1):
            with self.subTest(value=value):
                self.descriptor["runtimeLocks"] = value
                path = self.base / "descriptor.json"
                path.write_text(json.dumps(self.descriptor))
                with self.assertRaises(ValidationError):
                    validate_descriptor(path)

    def test_source_lock_rejects_malformed_entries_and_workspace_identity(self):
        path = self.core / "package-lock.json"
        original = path.read_text()
        for entry in (None, [], {"resolved": 1}, {"resolved": "ftp://registry.npmjs.org/pkg"},
                      {"resolved": "arbitrary"}, {"version": "1.0.0"}, {"link": "true", "resolved": "packages/ai"}):
            with self.subTest(entry=entry):
                lock = json.loads(original)
                lock["packages"]["node_modules/evil"] = entry
                path.write_text(json.dumps(lock))
                with self.assertRaises(ValidationError):
                    validate_source_lock(path, self.core)
        for key, value in (("name", "@earendil-works/pi-tui"), ("version", "0.0.1")):
            with self.subTest(key=key):
                lock = json.loads(original)
                lock["packages"]["packages/ai"][key] = value
                path.write_text(json.dumps(lock))
                with self.assertRaises(ValidationError):
                    validate_source_lock(path, self.core)
        lock = json.loads(original)
        del lock["packages"]["node_modules/@earendil-works/pi-tui"]
        path.write_text(json.dumps(lock))
        with self.assertRaises(ValidationError):
            validate_source_lock(path, self.core)

    def test_installed_links_must_be_relative_symlinks_and_all_contained(self):
        path = self.core / "package-lock.json"
        for short in ("coding-agent", "ai", "tui"):
            link = self.core / "node_modules/@earendil-works" / f"pi-{short}"
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(f"../../packages/{short}")
        validate_installed_workspace_links(self.core, path)
        tui = self.core / "node_modules/@earendil-works/pi-tui"
        tui.unlink()
        tui.mkdir()
        with self.assertRaises(ValidationError):
            validate_installed_workspace_links(self.core, path)
        tui.rmdir()
        tui.symlink_to(self.core / "packages/tui")
        with self.assertRaises(ValidationError):
            validate_installed_workspace_links(self.core, path)
        tui.unlink()
        tui.symlink_to("../../packages/tui")
        extra = self.core / "node_modules/extra"
        for target in ("missing", "../../outside"):
            extra.symlink_to(target)
            with self.assertRaises(ValidationError):
                validate_installed_workspace_links(self.core, path)
            extra.unlink()

    def test_only_declared_workspace_bins_may_be_pending_before_build(self):
        meta_path = self.core / "packages/ai/package.json"
        meta = json.loads(meta_path.read_text())
        meta["bin"] = {"pi-ai": "dist/cli.js"}
        meta_path.write_text(json.dumps(meta))
        for short in ("coding-agent", "ai", "tui"):
            link = self.core / "node_modules/@earendil-works" / f"pi-{short}"
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(f"../../packages/{short}")
        pending = self.core / "node_modules/.bin/pi-ai"
        pending.parent.mkdir()
        pending.symlink_to("../@earendil-works/pi-ai/dist/cli.js")
        lock = self.core / "package-lock.json"
        validate_installed_workspace_links(self.core, lock, before_build=True)
        with self.assertRaisesRegex(ValidationError, "broken"):
            validate_installed_workspace_links(self.core, lock)
        pending.unlink()
        pending.symlink_to("../@earendil-works/pi-ai/dist/wrong.js")
        with self.assertRaisesRegex(ValidationError, "broken"):
            validate_installed_workspace_links(self.core, lock, before_build=True)

    def test_layout_requires_ai_and_tui_and_hashes_nested_outputs(self):
        cli = self.core / CORE_CLI_REL
        cli.parent.mkdir(parents=True)
        cli.write_text("#!/usr/bin/env node\n")
        cli.chmod(0o755)
        with self.assertRaises(ValidationError):
            validate_source_core_layout(self.core, package=self.descriptor["core"]["package"], version="0.85.0")
        for short in ("coding-agent", "ai", "tui"):
            index = self.core / f"packages/{short}/dist/index.js"
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text("export {};\n")
        extra = self.core / "packages/tui/dist/components/editor.js"
        extra.parent.mkdir()
        extra.write_text("export {};\n")
        hashes = validate_source_core_layout(self.core, package=self.descriptor["core"]["package"], version="0.85.0")
        self.assertIn("packages/tui/dist/components/editor.js", hashes)
        self.assertIn("packages/tui/package.json", hashes)

    def test_broken_workspace_link_rejected(self):
        root = self.base / "link-root"
        root.mkdir()
        (root / "packages/coding-agent").mkdir(parents=True)
        lock = {
            "lockfileVersion": 3,
            "packages": {
                "node_modules/@earendil-works/pi-coding-agent": {"link": True, "resolved": "packages/coding-agent"},
            },
        }
        (root / "package-lock.json").write_text(json.dumps(lock))
        (root / "node_modules/@earendil-works").mkdir(parents=True)
        link = root / "node_modules/@earendil-works/pi-coding-agent"
        link.symlink_to("/tmp/outside")
        with self.assertRaises(ValidationError):
            validate_installed_workspace_links(root, root / "package-lock.json")


class SourceBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)

    def snapshot(self, entries=(), *, manifest_files=None, directory=False):
        body = b'{"messages":{}}'
        manifest = {"schemaVersion": 3, "generatedAt": "2026-01-01T00:00:00Z", "structureHash": "a" * 64,
                    "files": {"anthropic.json": hashlib.sha256(body).hexdigest()} if manifest_files is None else manifest_files}
        members = [(".manifest.json", json.dumps(manifest).encode(), tarfile.REGTYPE), ("anthropic.json", body, tarfile.REGTYPE)]
        if directory:
            members.insert(0, ("", b"", tarfile.DIRTYPE))
        members.extend(entries)
        result = io.BytesIO()
        with tarfile.open(fileobj=result, mode="w:gz") as archive:
            for name, data, kind in members:
                member = tarfile.TarInfo(f"pi-0.85.0/{CORE_MODEL_DATA_REL}/{name}")
                member.type = kind
                member.size = len(data)
                member.linkname = "elsewhere"
                archive.addfile(member, io.BytesIO(data))
        return result.getvalue()

    def extract(self, payload, target="data"):
        with mock.patch("attro.core_source.urllib.request.urlopen", return_value=io.BytesIO(payload)):
            return apply_model_snapshot(SNAPSHOT_URL, hashlib.sha256(payload).hexdigest(), self.base / target)

    def test_build_environment_is_allowlisted_in_actual_child(self):
        hostile = {"AWS_ACCESS_KEY_ID": "secret", "AWS_SECRET_ACCESS_KEY": "secret", "GOOGLE_APPLICATION_CREDENTIALS": "secret",
                   "NODE_OPTIONS": "--require=/bad", "NODE_PATH": "/bad", "PYTHONPATH": "/bad", "LD_PRELOAD": "/bad",
                   "DYLD_INSERT_LIBRARIES": "/bad", "HTTPS_PROXY": "http://secret", "NPM_CONFIG_REGISTRY": "http://secret",
                   "UNRECOGNIZED_PRIVATE_VALUE": "secret"}
        with mock.patch.dict(os.environ, hostile):
            env = sanitized_build_env(self.base / "home")
            child = run_command([sys.executable, "-c", "import json,os; print(json.dumps(dict(os.environ)))"], self.base, env=env)
        actual = json.loads(child.stdout)
        for key in hostile:
            self.assertNotIn(key, actual)
        self.assertEqual(actual["HOME"], str(self.base / "home"))
        allowed = {"HOME", "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TMP", "TEMP"}
        self.assertLessEqual(set(env), allowed)
        self.assertLessEqual(set(actual), allowed | {"__CF_USER_TEXT_ENCODING"})

    def test_snapshot_directory_header_and_hashes(self):
        result = self.extract(self.snapshot(directory=True))
        self.assertEqual(result["fileCount"], 2)
        self.assertEqual(set(p.name for p in (self.base / "data").iterdir()), {".manifest.json", "anthropic.json"})

    def test_snapshot_rejects_links_nested_files_duplicates_and_traversal(self):
        for index, (name, kind) in enumerate((("anthropic.json", tarfile.SYMTYPE), ("anthropic.json", tarfile.LNKTYPE),
                           ("nested/anthropic.json", tarfile.REGTYPE), ("../escape.json", tarfile.REGTYPE),
                           ("x.py", tarfile.REGTYPE), ("nested", tarfile.DIRTYPE))):
            with self.subTest(name=name, kind=kind):
                with self.assertRaises(ValidationError):
                    self.extract(self.snapshot([(name, b"", kind)]), target=f"data-{index}")
                self.assertFalse((self.base / f"data-{index}").exists())
        with self.assertRaises(ValidationError):
            self.extract(self.snapshot([("anthropic.json", b"{}", tarfile.REGTYPE)] * 2))
        self.assertFalse((self.base / "data").exists())

    def test_snapshot_requires_exact_manifest_file_hashes(self):
        for files in ({}, {"anthropic.json": "b" * 64}, {"anthropic.json": 1}, {"missing.json": "a" * 64}):
            with self.subTest(files=files):
                with self.assertRaises(ValidationError):
                    self.extract(self.snapshot(manifest_files=files))
                self.assertFalse((self.base / "data").exists())

    def test_snapshot_expansion_is_bounded(self):
        payload = self.snapshot()
        with mock.patch("attro.core_source.SNAPSHOT_EXPANSION_LIMIT", 1024):
            with self.assertRaisesRegex(ValidationError, "expansion limit"):
                self.extract(payload)
        with mock.patch("attro.core_source.SNAPSHOT_FILE_LIMIT", 1):
            with self.assertRaisesRegex(ValidationError, "file limit"):
                self.extract(payload)

    def test_snapshot_url_is_approved_before_download(self):
        for url in ("file:///etc/passwd", "http://github.com/earendil-works/pi/releases/download/v0.85.0/pi-0.85.0-source.tar.gz",
                    SNAPSHOT_URL + "?token=secret", SNAPSHOT_URL + "#fragment", SNAPSHOT_URL.replace("github.com/", "u:p@github.com/"),
                    SNAPSHOT_URL.replace("earendil-works", "attacker"), SNAPSHOT_URL.replace("0.85.0-source", "0.85.1-source")):
            with self.subTest(url=url), mock.patch("attro.core_source.urllib.request.urlopen") as download:
                with self.assertRaises(ValidationError):
                    apply_model_snapshot(url, "a" * 64, self.base / "data")
                download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
