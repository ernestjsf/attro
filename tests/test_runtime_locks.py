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
from types import SimpleNamespace
from unittest import mock

from attro.cli import main
from attro.rpiv_runtime import DEPENDENCIES, EXTERNAL, PACK, RECIPE
from attro.state import prepared_manifest
from attro.validate import ValidationError, run_command, sha256_file, validate_descriptor, validate_public_npm_lock

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
        plugin = self.repo / "plugins/attro-rpiv"
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
            "distribution": "attro",
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
                    "path": "plugins/attro-rpiv",
                    "name": "rpiv-mono",
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
            json.dumps({"name": "attro-release-pi", "private": True, "dependencies": core_deps}, sort_keys=True) + "\n"
        )
        (npm_dir / "package.json").write_text(
            json.dumps({"name": "attro-release-npm", "private": True, "dependencies": npm_deps}, sort_keys=True) + "\n"
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
        (self.repo / "attro.json").write_text(json.dumps(self.descriptor, sort_keys=True) + "\n")
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

    def setup_todo_recipe(self):
        plugin = self.repo / "plugins/attro-rpiv"
        for name in ("rpiv-todo", "rpiv-config", "rpiv-i18n"):
            package = plugin / "packages" / name
            package.mkdir(parents=True, exist_ok=True)
            (package / "package.json").write_text(json.dumps({
                "name": f"@juicesharp/{name}", "version": "2.9.0", "dependencies": DEPENDENCIES[name],
            }))
        (plugin / "LICENSE").write_text("fixture license\n")
        (plugin / "package-lock.json").write_text('{"lockfileVersion":3,"packages":{}}\n')
        self.git("add", "-A", cwd=plugin)
        self.git("commit", "-m", "recipe fixture", cwd=plugin)
        self.lock["submodules"][0]["pin"] = self.git("rev-parse", "HEAD", cwd=plugin)
        self.lock["submodules"][0]["dependencyLock"] = "package-lock.json"
        self.descriptor["rpivTodoRuntime"] = "runtime/rpiv-todo"
        lock_root = self.repo / "runtime/rpiv-todo"
        lock_root.mkdir(parents=True)
        (lock_root / "package.json").write_text(json.dumps({
            "name": "attro-rpiv-todo-runtime", "private": True, "dependencies": EXTERNAL,
        }))
        (lock_root / "package-lock.json").write_text(json.dumps({
            "lockfileVersion": 3, "packages": {
                "": {"dependencies": EXTERNAL},
                "node_modules/typebox": {
                    "version": EXTERNAL["typebox"], "integrity": "sha512-fixture",
                    "resolved": "https://registry.npmjs.org/typebox/-/typebox-1.3.6.tgz",
                },
            },
        }))
        self.commit_inputs()

    def prepare_todo_recipe(self):
        self.setup_todo_recipe()
        calls = []

        def fixture_command(command, cwd, **kwargs):
            calls.append((command, cwd))
            if command == PACK:
                files = [{"path": "package.json", "size": (cwd / "package.json").stat().st_size}]
                if cwd.name == "rpiv-todo":
                    files.append({"path": "index.ts", "size": (cwd / "index.ts").stat().st_size})
                return SimpleNamespace(stdout=json.dumps([{
                    "name": f"@juicesharp/{cwd.name}", "version": "2.9.0", "files": files,
                }]))
            result = run_command(command, cwd, **kwargs)
            (cwd / "node_modules/.package-lock.json").write_text("{}")
            return result

        with mock.patch("attro.rpiv_runtime.run_command", side_effect=fixture_command):
            output, _ = self.cli("--json", "setup", "--repo", str(self.repo))
        return json.loads(output), calls

    def test_todo_recipe_dispatch_and_artifact_validation(self):
        manifest, calls = self.prepare_todo_recipe()
        release = self.state / "releases" / manifest["releaseId"]
        rpiv = release / "plugins/attro-rpiv"
        record = manifest["provenance"]["rpivTodoRuntime"]
        self.assertEqual(record["recipe"], RECIPE)
        self.assertEqual(record["lockSource"], "runtime/rpiv-todo")
        self.assertIn("packages/rpiv-todo/index.ts", record["files"])
        self.assertNotIn("packages/rpiv-config/package.json", record["files"])
        self.assertIn("node_modules/@juicesharp/rpiv-config/package.json", record["files"])
        self.assertFalse((rpiv / "packages/rpiv-config").exists())
        self.assertEqual([cmd for cmd, _ in calls].count(PACK), 3)
        self.assertEqual([cwd.name for cmd, cwd in calls if cmd[:2] == ["npm", "ci"]], ["attro-rpiv"])
        self.assertEqual(self.npm_calls().count("npm ci --ignore-scripts --no-audit --no-fund"), 2)
        self.assertIn("npm ci --ignore-scripts --no-audit --no-fund --omit=dev --legacy-peer-deps", self.npm_calls())
        prepared_manifest(release)

        payload = rpiv / "packages/rpiv-todo/index.ts"
        original = payload.read_bytes()
        payload.write_text("tampered\n")
        with self.assertRaisesRegex(ValidationError, "inventory/digest mismatch"):
            prepared_manifest(release)
        payload.write_bytes(original)
        self.assertEqual(prepared_manifest(release)["releaseId"], manifest["releaseId"])

        helper = rpiv / "node_modules/@juicesharp/rpiv-config/package.json"
        helper.unlink()
        helper.symlink_to(rpiv / "LICENSE")
        with self.assertRaisesRegex(ValidationError, "refusing symlink"):
            prepared_manifest(release)

    def test_prepared_release_with_retired_rpiv_path_still_validates(self):
        manifest, _ = self.prepare_todo_recipe()
        release = self.state / "releases" / manifest["releaseId"]
        (release / "plugins/attro-rpiv").rename(release / "plugins/rpiv-mono")
        settings = release / "config/settings.json"
        settings.write_text(settings.read_text().replace("plugins/attro-rpiv", "plugins/rpiv-mono"))
        legacy = json.loads((release / "manifest.json").read_text())
        legacy["settingsSha256"] = sha256_file(settings)
        for entry in legacy["provenance"]["sources"]["submodules"]:
            if entry.get("name") == "rpiv-mono":
                entry["path"] = "plugins/rpiv-mono"
        (release / "manifest.json").write_text(json.dumps(legacy))
        self.assertEqual(prepared_manifest(release)["releaseId"], manifest["releaseId"])
        data = json.loads((release / "manifest.json").read_text())
        data["provenance"]["sources"]["submodules"] = [e for e in data["provenance"]["sources"]["submodules"] if e.get("name") != "rpiv-mono"]
        (release / "manifest.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(ValidationError, "lacks rpiv-mono source entry"):
            prepared_manifest(release)

    def test_descriptor_accepts_runtime_locks(self):
        data = validate_descriptor(REPO_ROOT / "attro.json")
        self.assertEqual(data["core"]["installMethod"], "source")
        self.assertEqual(data["runtimeLocks"], {"npm": "runtime/npm"})
        self.assertEqual(data["rpivTodoRuntime"], "runtime/rpiv-todo")

    def test_shipped_runtime_locks_are_public(self):
        validate_public_npm_lock(REPO_ROOT / "runtime/core/package-lock.json")
        validate_public_npm_lock(REPO_ROOT / "runtime/npm/package-lock.json")
        validate_public_npm_lock(REPO_ROOT / "runtime/rpiv-todo/package-lock.json")

    def test_shipped_npm_lock_matches_cursor_free_recipe(self):
        descriptor = validate_descriptor(REPO_ROOT / "attro.json")
        package = json.loads((REPO_ROOT / "runtime/npm/package.json").read_text())
        lock = json.loads((REPO_ROOT / "runtime/npm/package-lock.json").read_text())
        expected = {entry["package"]: entry["version"] for entry in descriptor["npmPackages"]}
        self.assertEqual(package["dependencies"], expected)
        self.assertEqual(lock["packages"][""]["dependencies"], expected)
        self.assertFalse(any(path == "node_modules/pi-cursor-sdk" or path.startswith("node_modules/@cursor/sdk") for path in lock["packages"]))
        self.assertFalse(any(
            "@cursor/sdk" in record.get(key, {})
            for record in lock["packages"].values()
            for key in ("dependencies", "optionalDependencies", "peerDependencies")
        ))

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
        self.assertNotIn("rpivTodoRuntime", manifest["provenance"])
        self.assertTrue((self.state / "releases" / manifest["releaseId"] / "plugins/attro-rpiv/packages/rpiv-todo/index.ts").is_file())

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
