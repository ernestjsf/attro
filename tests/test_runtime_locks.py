"""Offline tests for committed core/npm runtime dependency locks."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from piattro.cli import main
from piattro.validate import ValidationError, sha256_file, validate_descriptor, validate_public_npm_lock

REPO_ROOT = Path(__file__).resolve().parents[1]


class RuntimeLockTests(unittest.TestCase):
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
        pin = self.git("rev-parse", "HEAD", cwd=plugin)
        self.descriptor = {
            "schemaVersion": 1,
            "distribution": "piattro",
            "version": "0.2.0",
            "stateSchemaVersion": 1,
            "manifestSchemaVersion": 1,
            "profile": "profile/settings.json",
            "sourcesLock": "sources.lock.json",
            "runtimeLocks": {"core": "runtime/core", "npm": "runtime/npm"},
            "core": {"package": "@earendil-works/pi-coding-agent", "version": "0.85.0", "engines": {"node": ">=22.19.0"}},
            "npmPackages": [{"package": "fixture-addon", "version": "1.2.3"}],
        }
        profile = self.repo / "profile"
        profile.mkdir()
        (profile / "settings.json").write_text(json.dumps({"packages": ["{{PLUGIN_RPIV_TODO}}"], "themes": ["{{THEME_QUATTRO_GREEN}}"]}))
        (self.repo / "themes").mkdir()
        theme = self.repo / "themes/quattro-green.json"
        theme.write_text("{}\n")
        self.lock = {
            "schemaVersion": 1,
            "branch": "quattro",
            "submodules": [
                {
                    "path": "plugins/rpiv-mono",
                    "origin": "https://example.invalid/rpiv.git",
                    "pin": pin,
                    "packagePath": "packages/rpiv-todo",
                    "runtimeGenerated": False,
                    "sourceEntryFiles": ["packages/rpiv-todo/index.ts"],
                    "runtimeEntryFiles": ["packages/rpiv-todo/index.ts"],
                    "dependencyLock": None,
                }
            ],
            "configs": [{"path": "themes/quattro-green.json", "sha256": sha256_file(theme)}],
        }
        self.npm_log = self.base / "fixture-npm.log"
        fakebin = self.base / "fakebin"
        fakebin.mkdir()
        npm = fakebin / "npm"
        npm.write_text(
            "#!/usr/bin/env python3\n"
            + f'''import json, os, pathlib, sys
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
        if os.environ.get("FIXTURE_NPM_MISMATCH") in ("1", name):
            version = "0.0.0"
        (target / "package.json").write_text(json.dumps({{"name": name, "version": version}}))
        if name == "@earendil-works/pi-coding-agent":
            cli = target / "dist/bundle/cli.js"
            cli.parent.mkdir(parents=True, exist_ok=True)
            cli.write_text("#!/usr/bin/env node\\nconsole.log('fixture pi');\\n")
            cli.chmod(0o755)

if os.environ.get("FIXTURE_NPM_FAIL"):
    sys.exit("fixture npm failed")

if args[:1] == ["ci"]:
    lock_path = root / "package-lock.json"
    if not lock_path.is_file():
        sys.exit("fixture npm ci: missing package-lock.json")
    before = lock_path.read_bytes()
    install_deps()
    if os.environ.get("FIXTURE_NPM_LOCK_REWRITE"):
        lock_path.write_text(json.dumps({{"lockfileVersion": 3, "packages": {{}}, "fixture": "rewritten"}}))
    elif lock_path.read_bytes() != before:
        sys.exit("fixture npm ci: unexpected lock mutation")
    sys.exit(0)

install_deps()
(root / "package-lock.json").write_text(json.dumps({{"lockfileVersion": 3, "packages": {{}}}}))
'''
        )
        npm.chmod(0o755)
        node = fakebin / "node"
        node.write_text(
            '#!/bin/sh\nif [ "$1" = "--version" ]; then echo "${FIXTURE_NODE_VERSION:-v26.0.0}"; exit 0; fi\necho "fixture pi"\n'
        )
        node.chmod(0o755)
        env = mock.patch.dict(os.environ, {"PATH": str(fakebin) + os.pathsep + os.environ["PATH"]})
        env.start()
        self.addCleanup(env.stop)
        self.core_lock_sha, self.npm_lock_sha = self.write_runtime_locks()
        self.commit_inputs()

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, check=True, capture_output=True, text=True).stdout.strip()

    def write_runtime_locks(
        self,
        *,
        core_deps: dict[str, str] | None = None,
        npm_deps: dict[str, str] | None = None,
        include_core_lock: bool = True,
        include_npm_lock: bool = True,
    ) -> tuple[str | None, str | None]:
        core_deps = core_deps or {"@earendil-works/pi-coding-agent": "0.85.0"}
        npm_deps = npm_deps or {"fixture-addon": "1.2.3"}
        core_dir = self.repo / "runtime/core"
        npm_dir = self.repo / "runtime/npm"
        core_dir.mkdir(parents=True, exist_ok=True)
        npm_dir.mkdir(parents=True, exist_ok=True)
        (core_dir / "package.json").write_text(
            json.dumps({"name": "piattro-release-pi", "private": True, "dependencies": core_deps}, sort_keys=True) + "\n"
        )
        (npm_dir / "package.json").write_text(
            json.dumps({"name": "piattro-release-npm", "private": True, "dependencies": npm_deps}, sort_keys=True) + "\n"
        )
        lock_body = json.dumps({"lockfileVersion": 3, "packages": {}}) + "\n"
        core_sha = npm_sha = None
        core_lock = core_dir / "package-lock.json"
        npm_lock = npm_dir / "package-lock.json"
        if include_core_lock:
            core_lock.write_text(lock_body)
            core_sha = sha256_file(core_lock)
        elif core_lock.exists():
            core_lock.unlink()
        if include_npm_lock:
            npm_lock.write_text(lock_body)
            npm_sha = sha256_file(npm_lock)
        elif npm_lock.exists():
            npm_lock.unlink()
        return core_sha, npm_sha

    def commit_inputs(self):
        (self.repo / "piattro.json").write_text(json.dumps(self.descriptor, sort_keys=True) + "\n")
        (self.repo / "sources.lock.json").write_text(json.dumps(self.lock, sort_keys=True) + "\n")
        self.git("add", "-A")
        if subprocess.run(["git", "status", "--porcelain"], cwd=self.repo, capture_output=True, text=True).stdout.strip():
            self.git("commit", "-m", "inputs")

    def npm_calls(self):
        if not self.npm_log.is_file():
            return []
        return [line.strip() for line in self.npm_log.read_text().splitlines() if line.strip()]

    def cli(self, *args, success=True):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(["--state-root", str(self.state), *args])
        if success:
            self.assertEqual(result, 0, stderr.getvalue())
        else:
            self.assertNotEqual(result, 0, stdout.getvalue())
        return stdout.getvalue(), stderr.getvalue()

    def test_descriptor_accepts_runtime_locks(self):
        data = validate_descriptor(REPO_ROOT / "piattro.json")
        self.assertEqual(data["runtimeLocks"], {"core": "runtime/core", "npm": "runtime/npm"})

    def test_shipped_runtime_locks_are_public(self):
        validate_public_npm_lock(REPO_ROOT / "runtime/core/package-lock.json")
        validate_public_npm_lock(REPO_ROOT / "runtime/npm/package-lock.json")

    def test_committed_lock_uses_npm_ci(self):
        output, _ = self.cli("--json", "setup", "--repo", str(self.repo), "--activate")
        manifest = json.loads(output)
        calls = self.npm_calls()
        self.assertIn("npm ci --ignore-scripts --no-audit --no-fund", calls)
        self.assertNotIn("npm install --ignore-scripts --no-audit --no-fund", calls)
        core = manifest["provenance"]["core"]
        npm = manifest["provenance"]["npmPackages"][0]
        self.assertEqual(core["lockSource"], "runtime/core")
        self.assertEqual(npm["lockSource"], "runtime/npm")
        self.assertEqual(core["lockSha256"], self.core_lock_sha)
        self.assertEqual(npm["lockSha256"], self.npm_lock_sha)
        self.assertIn("committed dependency locks", manifest["provenance"]["dependencyResolution"])

    def test_package_json_mismatch_fails_before_activation(self):
        self.write_runtime_locks(core_deps={"@earendil-works/pi-coding-agent": "0.84.0"})
        self.commit_inputs()
        _, stderr = self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertIn("package.json dependencies do not match descriptor pins", stderr)
        self.assertEqual(list((self.state / "releases").glob("*")) if (self.state / "releases").exists() else [], [])

    def test_missing_lock_fails_before_activation(self):
        self.write_runtime_locks(include_core_lock=False)
        self.commit_inputs()
        _, stderr = self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertIn("runtime lock missing", stderr)
        self.assertEqual(list((self.state / "releases").glob("*")) if (self.state / "releases").exists() else [], [])

    def test_tampered_lock_fails_before_activation(self):
        with mock.patch.dict(os.environ, {"FIXTURE_NPM_LOCK_REWRITE": "1"}):
            _, stderr = self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertIn("dependency lock changed during npm ci", stderr)
        self.assertEqual(list((self.state / "releases").glob("*")) if (self.state / "releases").exists() else [], [])

    def test_public_lock_rejects_local_sources(self):
        path = self.base / "bad-lock.json"
        path.write_text('{"resolved":"file:../local.tgz"}\n')
        with self.assertRaises(ValidationError):
            validate_public_npm_lock(path)

    def test_compact_lock_cannot_hide_a_second_non_public_source(self):
        path = self.repo / "runtime/core/package-lock.json"
        lock = json.loads(path.read_text())
        lock["packages"]["node_modules/@earendil-works/pi-coding-agent"] = {
            "version": "0.85.0",
            "resolved": "https://registry.npmjs.org/@earendil-works/pi-coding-agent/-/pi-coding-agent-0.85.0.tgz",
        }
        lock["packages"]["node_modules/unexpected-source"] = {
            "version": "1.0.0",
            "resolved": "https://unapproved.example/package.tgz",
        }
        path.write_text(json.dumps(lock))
        self.commit_inputs()
        self.cli("setup", "--repo", str(self.repo), "--activate", success=False)
        self.assertFalse((self.state / "state.json").exists())


if __name__ == "__main__":
    unittest.main()
