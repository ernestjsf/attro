"""Offline public-command lifecycle tests using committed source fixtures."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from piattro.cli import main
from piattro.validate import ValidationError, run_command, sha256_file
from piattro.launch import build_exec_env, populate_try_agent


class LifecycleTests(unittest.TestCase):
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
        (plugin / ".gitignore").write_text("ignored.txt\n")
        (plugin / "ignored.txt").write_text("do not export")
        self.git("add", ".", cwd=plugin)
        self.git("commit", "-m", "plugin", cwd=plugin)
        pin = self.git("rev-parse", "HEAD", cwd=plugin)
        self.descriptor = {
            "schemaVersion": 1, "distribution": "piattro", "version": "0.1.0",
            "stateSchemaVersion": 1, "manifestSchemaVersion": 1,
            "profile": "profile/settings.json", "sourcesLock": "sources.lock.json",
            "core": {"package": "@earendil-works/pi-coding-agent", "version": "0.85.0", "engines": {"node": ">=22.19.0"}},
            "npmPackages": [{"package": "fixture-addon", "version": "1.2.3"}],
        }
        profile = self.repo / "profile"
        profile.mkdir()
        (profile / "settings.json").write_text(json.dumps({"packages": ["{{PLUGIN_RPIV_TODO}}"], "themes": ["{{THEME_QUATTRO_GREEN}}"]}))
        (self.repo / "themes").mkdir()
        theme = self.repo / "themes/quattro-green.json"
        theme.write_text('{}\n')
        self.lock = {
            "schemaVersion": 1, "branch": "quattro",
            "submodules": [{"path": "plugins/rpiv-mono", "origin": "https://example.invalid/rpiv.git", "pin": pin,
                            "packagePath": "packages/rpiv-todo", "runtimeGenerated": False,
                            "sourceEntryFiles": ["packages/rpiv-todo/index.ts"], "runtimeEntryFiles": ["packages/rpiv-todo/index.ts"], "dependencyLock": None}],
            "configs": [{"path": "themes/quattro-green.json", "sha256": sha256_file(theme)}],
        }
        self.commit_inputs()
        self.npm_log = self.base / "fixture-npm.log"
        fakebin = self.base / "fakebin"
        fakebin.mkdir()
        npm = fakebin / "npm"
        npm.write_text("#!/usr/bin/env python3\n" + f'''import json, os, pathlib, sys
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

if args[:2] == ["run", "build:dist"]:
    if os.environ.get("FIXTURE_LENS_BUILD_FAIL"):
        sys.exit("fixture Lens build failed")
    dist = root / "dist" / "index.js"
    dist.parent.mkdir(parents=True, exist_ok=True)
    dist.write_text("export {{}};\\n")
    sys.exit(0)

if args[:2] == ["run", "check:grammars"]:
    gram = root / "grammars" / "tree-sitter-typescript.wasm"
    if not gram.is_file():
        sys.exit("fixture check:grammars: missing grammar")
    sys.exit(0)

install_deps()
(root / "package-lock.json").write_text(json.dumps({{"lockfileVersion": 3, "packages": {{}}}}))
''')
        npm.chmod(0o755)
        node = fakebin / "node"
        node.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo "${FIXTURE_NODE_VERSION:-v26.0.0}"; exit 0; fi\ncase "$1" in\n  scripts/download-grammars.js|*/download-grammars.js)\n    dest=grammars\n    i=1\n    while [ $i -le $# ]; do eval "arg=\\$$i"; if [ "$arg" = "--dest" ]; then i=$((i+1)); eval "dest=\\$$i"; fi; i=$((i+1)); done\n    mkdir -p "$dest"\n    printf wasm > "$dest/tree-sitter-typescript.wasm"\n    exit 0\n    ;;\nesac\necho "fixture pi"\n')
        node.chmod(0o755)
        env = mock.patch.dict(os.environ, {"PATH": str(fakebin) + os.pathsep + os.environ["PATH"]})
        env.start()
        self.addCleanup(env.stop)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, check=True, capture_output=True, text=True).stdout.strip()

    def commit_inputs(self):
        (self.repo / "piattro.json").write_text(json.dumps(self.descriptor))
        (self.repo / "sources.lock.json").write_text(json.dumps(self.lock))
        self.git("add", ".")
        self.git("commit", "-m", "inputs")

    def configure_locked_plugin(self):
        plugin = self.repo / "plugins/rpiv-mono"
        lock_path = plugin / "package-lock.json"
        lock_path.write_text(json.dumps({"lockfileVersion": 3, "packages": {}}))
        self.git("add", ".", cwd=plugin)
        self.git("commit", "-m", "plugin lock", cwd=plugin)
        pin = self.git("rev-parse", "HEAD", cwd=plugin)
        entry = self.lock["submodules"][0]
        entry.update({"pin": pin, "dependencyLock": "package-lock.json", "dependencyLockVersion": 3})
        self.git("add", "plugins/rpiv-mono")
        self.commit_inputs()
        return sha256_file(lock_path)

    def configure_lens_plugin(self):
        import shutil
        rpiv = self.repo / "plugins/rpiv-mono"
        if rpiv.exists():
            shutil.rmtree(rpiv)
        lens = self.repo / "plugins/pi-lens"
        lens.mkdir(parents=True)
        self.git("init", cwd=lens)
        self.git("config", "user.name", "Fixture", cwd=lens)
        self.git("config", "user.email", "fixture@example.invalid", cwd=lens)
        self.git("remote", "add", "origin", "https://example.invalid/pi-lens.git", cwd=lens)
        (lens / "index.ts").write_text("export default () => {};\n")
        (lens / "tools").mkdir()
        (lens / "tools/render-compact.ts").write_text("export default () => {};\n")
        (lens / "scripts").mkdir()
        (lens / "scripts/download-grammars.js").write_text("")
        (lens / "package.json").write_text(json.dumps({
            "name": "pi-lens-fixture",
            "scripts": {"build:dist": "true", "check:grammars": "true"},
        }))
        (lens / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {}}))
        self.git("add", ".", cwd=lens)
        self.git("commit", "-m", "lens plugin", cwd=lens)
        pin = self.git("rev-parse", "HEAD", cwd=lens)
        self.lock["submodules"][0] = {
            "path": "plugins/pi-lens", "origin": "https://example.invalid/pi-lens.git", "pin": pin,
            "packagePath": ".", "runtimeGenerated": True,
            "sourceEntryFiles": ["index.ts", "tools/render-compact.ts"],
            "runtimeEntryFiles": ["dist/index.js", "grammars/tree-sitter-typescript.wasm"],
            "dependencyLock": "package-lock.json", "dependencyLockVersion": 3,
        }
        profile = self.repo / "profile/settings.json"
        profile.write_text(json.dumps({"packages": ["{{PLUGIN_PI_LENS}}"], "themes": ["{{THEME_QUATTRO_GREEN}}"]}))
        self.git("add", "plugins/pi-lens", "profile/settings.json")
        self.commit_inputs()
        return lens

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

    def setup_release(self):
        output, _ = self.cli("--json", "setup", "--repo", str(self.repo), "--activate")
        return json.loads(output)

    def test_setup_activate_rollback_without_checkout(self):
        a = self.setup_release()
        release_a = self.state / "releases" / a["releaseId"]
        settings_before = (release_a / "agent/settings.json").read_bytes()
        settings = json.loads(settings_before)
        self.assertEqual(settings["packages"], [str(release_a / "plugins/rpiv-mono/packages/rpiv-todo"), str(release_a / "npm/node_modules/fixture-addon")])
        for value in settings["packages"] + settings["themes"]:
            self.assertTrue(Path(value).exists(), value)
        self.assertFalse((release_a / "plugins/rpiv-mono/ignored.txt").exists())
        for record in [a["provenance"]["core"], *a["provenance"]["npmPackages"]]:
            for key in ("installRoot", "lockFile", "piBinary"):
                if key in record:
                    self.assertTrue(Path(record[key]).exists(), record[key])
                    self.assertTrue(Path(record[key]).is_relative_to(release_a))
        self.descriptor["version"] = "0.2.0"
        self.commit_inputs()
        b = self.setup_release()
        self.repo.rename(self.base / "unavailable")
        self.cli("rollback")
        state = json.loads(self.cli("--json", "status")[0])
        self.assertEqual(state["active"], a["releaseId"])
        self.assertEqual(state["previous"], b["releaseId"])
        self.assertEqual((release_a / "agent/settings.json").read_bytes(), settings_before)
        self.cli("doctor")
        self.cli("exec", "--dry-run", "--", "--version")
        self.cli("try", "--dry-run", "--", "--version")

    def test_failed_prepare_preserves_state(self):
        self.setup_release()
        before = (self.state / "state.json").read_bytes()
        self.descriptor["version"] = "0.2.0"
        self.commit_inputs()
        with mock.patch.dict(os.environ, {"FIXTURE_NPM_FAIL": "1"}):
            self.cli("setup", "--repo", str(self.repo), "--activate", success=False)
        self.assertEqual((self.state / "state.json").read_bytes(), before)
        self.assertEqual(list((self.state / "staging").iterdir()), [])

    def test_root_dirty_refused(self):
        (self.repo / "piattro.json").write_text(json.dumps({**self.descriptor, "version": "0.9.0"}))
        self.cli("setup", "--repo", str(self.repo), success=False)

    def test_npm_pin_mismatch_refused(self):
        with mock.patch.dict(os.environ, {"FIXTURE_NPM_MISMATCH": "1"}):
            self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertFalse((self.state / "state.json").exists())

    def test_node_minimum_enforced(self):
        with mock.patch.dict(os.environ, {"FIXTURE_NODE_VERSION": "v22.18.0"}):
            self.cli("setup", "--repo", str(self.repo), success=False)

    def test_reject_descriptor_traversal_and_schema_types(self):
        for key, value in [("profile", "../outside.json"), ("schemaVersion", True), ("core", {"package": "../evil", "version": "latest"})]:
            with self.subTest(key=key):
                old = self.descriptor[key]
                self.descriptor[key] = value
                self.commit_inputs()
                self.cli("setup", "--repo", str(self.repo), success=False)
                self.descriptor[key] = old

    def test_existing_release_target_is_not_deleted(self):
        a = self.setup_release()
        release = self.state / "releases" / a["releaseId"]
        (release / ".prepared").unlink()
        sentinel = release / "preserve-me"
        sentinel.write_text("data")
        self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertEqual(sentinel.read_text(), "data")

    def test_reject_registry_escape(self):
        self.setup_release()
        path = self.state / "state.json"
        state = json.loads(path.read_text())
        state["releases"][state["active"]]["path"] = str(self.repo)
        path.write_text(json.dumps(state))
        self.cli("status", success=False)
        self.cli("exec", "--dry-run", success=False)

    def test_reject_managed_symlink(self):
        self.state.mkdir()
        outside = self.base / "outside"
        outside.mkdir()
        (self.state / "releases").symlink_to(outside, target_is_directory=True)
        self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_checkout_cannot_be_state_root(self):
        self.state = self.repo
        self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertFalse((self.repo / ".operations.lock").exists())

    def test_actual_wrapper_flags_and_symlink(self):
        self.setup_release()
        wrapper = Path(__file__).resolve().parents[1] / "bin/pi"
        symlink = self.base / "pi"
        symlink.symlink_to(wrapper)
        for command in ([str(wrapper), "--version"], [str(wrapper), "-p", "hello"], [str(symlink), "--version"]):
            result = subprocess.run(command, env={**os.environ, "PIATTRO_HOME": str(self.state)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("fixture pi", result.stdout)
        result = subprocess.run([str(wrapper), "update"], env={**os.environ, "PIATTRO_HOME": str(self.state)}, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing managed pi command", result.stderr)

    def test_interrupted_activation_keeps_complete_old_pointer(self):
        a = self.setup_release()
        self.descriptor["version"] = "0.2.0"
        self.commit_inputs()
        b = json.loads(self.cli("--json", "update", "--repo", str(self.repo))[0])
        before = (self.state / "state.json").read_bytes()
        with mock.patch("piattro.validate.os.replace", side_effect=OSError("interrupted replacement")):
            self.cli("activate", b["releaseId"], success=False)
        self.assertEqual((self.state / "state.json").read_bytes(), before)
        self.assertEqual(json.loads(before)["active"], a["releaseId"])
        self.cli("activate", b["releaseId"])
        self.cli("rollback")

    def test_real_process_lock_contention_and_recovery(self):
        code = "from pathlib import Path; import sys,time; from piattro.lock import operation_lock\nwith operation_lock(Path(sys.argv[1])):\n print('locked', flush=True)\n time.sleep(30)\n"
        process = subprocess.Popen([sys.executable, "-c", code, str(self.state)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            assert process.stdout is not None
            self.assertEqual(process.stdout.readline().strip(), "locked")
            _, error = self.cli("setup", "--repo", str(self.repo), success=False)
            self.assertIn("already running", error)
        finally:
            process.kill()
            process.communicate(timeout=10)
        self.setup_release()

    def test_try_uses_pristine_config_and_no_tokens(self):
        a = self.setup_release()
        release = self.state / "releases" / a["releaseId"]
        (release / "agent/auth.json").write_text('{"token":"do-not-copy"}')
        (release / "agent/trust.json").write_text('{}')
        settings = json.loads((release / "agent/settings.json").read_text())
        settings.update({"sessionDir": "/live/sessions", "defaultProvider": "example", "defaultModel": "example"})
        (release / "agent/settings.json").write_text(json.dumps(settings))
        isolated = self.base / "trial-agent"
        populate_try_agent(release, isolated)
        trial = json.loads((isolated / "settings.json").read_text())
        for key in ("sessionDir", "defaultProvider", "defaultModel"):
            self.assertNotIn(key, trial)
        self.assertFalse((isolated / "auth.json").exists())
        self.assertFalse((isolated / "trust.json").exists())
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "PI_CODING_AGENT_SESSION_DIR": "/live/sessions", "PI_PACKAGE_DIR": "/live/package"}):
            env = build_exec_env(release)
        self.assertEqual(env["ANTHROPIC_API_KEY"], "test-key")
        self.assertNotIn("PI_CODING_AGENT_SESSION_DIR", env)
        self.assertNotIn("PI_PACKAGE_DIR", env)
        self.cli("try", "--", "--version")

    def test_agent_credential_alias_refused(self):
        a = self.setup_release()
        release = self.state / "releases" / a["releaseId"]
        credential = self.base / "auth.json"
        credential.write_text('{"token":"preserve"}')
        alias = release / "agent/auth.json"
        alias.symlink_to(credential)
        self.cli("exec", "--dry-run", success=False)
        alias.unlink()
        os.link(credential, alias)
        self.cli("exec", "--dry-run", success=False)
        self.assertEqual(credential.read_text(), '{"token":"preserve"}')

    def test_core_pin_mismatch_refused(self):
        with mock.patch.dict(os.environ, {"FIXTURE_NPM_MISMATCH": "@earendil-works/pi-coding-agent"}):
            self.cli("setup", "--repo", str(self.repo), success=False)
        self.assertFalse((self.state / "state.json").exists())

    def test_source_lock_traversal_refused(self):
        self.lock["submodules"][0]["runtimeEntryFiles"] = ["../../outside"]
        self.commit_inputs()
        self.cli("setup", "--repo", str(self.repo), success=False)

    def test_profile_source_symlink_refused(self):
        profile = self.repo / "profile/settings.json"
        outside = self.base / "profile.json"
        outside.write_text(profile.read_text())
        profile.unlink()
        profile.symlink_to(outside)
        self.commit_inputs()
        self.cli("setup", "--repo", str(self.repo), success=False)

    def test_release_manifest_escape_and_schema_refused(self):
        a = self.setup_release()
        manifest_path = self.state / "releases" / a["releaseId"] / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["provenance"]["core"]["piBinary"] = "/outside/cli.js"
        manifest_path.write_text(json.dumps(manifest))
        self.cli("exec", "--dry-run", success=False)
        manifest["schemaVersion"] = True
        manifest_path.write_text(json.dumps(manifest))
        self.cli("doctor", success=False)

    def test_command_timeout_is_clean_validation_error(self):
        with self.assertRaisesRegex(ValidationError, "timed out"):
            run_command([sys.executable, "-c", "import time; time.sleep(30)"], self.base, timeout=1)

    def test_profile_ui_and_package_order(self):
        root = Path(__file__).resolve().parents[1]
        profile = json.loads((root / "profile/settings.json").read_text())
        self.assertEqual(profile["packages"], ["{{PLUGIN_PI_ZENTUI}}", "{{PLUGIN_PI_CC_EXTENSIONS}}", "{{PLUGIN_PI_WEB_ACCESS}}", "{{PLUGIN_PI_LENS}}", "{{PLUGIN_RPIV_TODO}}", "{{PLUGIN_PI_ASK_USER}}", "{{PLUGIN_PI_SUBAGENTS}}"])
        expected = {"quietStartup": True, "hideThinkingBlock": False, "editorPaddingX": 0, "outputPad": 1, "tuiMode": "fullscreen", "fullscreenScrollbar": "auto", "fullscreenExitOutput": "resume-hint", "collapseChangelog": True, "markdown": {"mermaid": "final"}}
        for key, value in expected.items():
            self.assertEqual(profile[key], value)
        for key in ("defaultProvider", "defaultModel", "defaultProjectTrust"):
            self.assertNotIn(key, profile)

    def test_committed_plugin_dependency_lock_preserved(self):
        digest = self.configure_locked_plugin()
        output, _ = self.cli("--json", "setup", "--repo", str(self.repo), "--activate")
        release = json.loads(output)
        locks = release["provenance"]["pluginDependencyLocks"]
        self.assertEqual(len(locks), 1)
        record = locks[0]
        self.assertEqual(record["sha256"], digest)
        self.assertTrue(record["path"].endswith("plugins/rpiv-mono/package-lock.json"))
        release_root = self.state / "releases" / release["releaseId"]
        lock_file = release_root / "plugins/rpiv-mono/package-lock.json"
        self.assertTrue(lock_file.is_file())
        self.assertEqual(sha256_file(lock_file), digest)

    def test_npm_ci_lock_change_preserves_active_state(self):
        self.configure_locked_plugin()
        first = self.setup_release()
        before = (self.state / "state.json").read_bytes()
        self.descriptor["version"] = "0.2.0"
        self.commit_inputs()
        with mock.patch.dict(os.environ, {"FIXTURE_NPM_LOCK_REWRITE": "1"}):
            self.cli("setup", "--repo", str(self.repo), "--activate", success=False)
        self.assertEqual((self.state / "state.json").read_bytes(), before)
        self.assertEqual(list((self.state / "staging").iterdir()), [])
        active = json.loads(self.cli("--json", "status")[0])
        self.assertEqual(active["active"], first["releaseId"])

    def test_npm_ci_failure_preserves_active_state(self):
        self.configure_locked_plugin()
        first = self.setup_release()
        before = (self.state / "state.json").read_bytes()
        self.descriptor["version"] = "0.2.0"
        self.commit_inputs()
        with mock.patch.dict(os.environ, {"FIXTURE_NPM_FAIL": "1"}):
            self.cli("setup", "--repo", str(self.repo), "--activate", success=False)
        self.assertEqual((self.state / "state.json").read_bytes(), before)
        self.assertEqual(list((self.state / "staging").iterdir()), [])
        active = json.loads(self.cli("--json", "status")[0])
        self.assertEqual(active["active"], first["releaseId"])

    def test_lens_runtime_generated_build_success(self):
        lens = self.configure_lens_plugin()
        output, _ = self.cli("--json", "setup", "--repo", str(self.repo), "--activate")
        release = json.loads(output)
        release_root = self.state / "releases" / release["releaseId"]
        dist = release_root / "plugins/pi-lens/dist/index.js"
        gram = release_root / "plugins/pi-lens/grammars/tree-sitter-typescript.wasm"
        self.assertTrue(dist.is_file(), dist)
        self.assertTrue(gram.is_file(), gram)
        self.assertFalse((lens / "dist/index.js").exists())
        self.assertFalse((lens / "grammars/tree-sitter-typescript.wasm").exists())
        calls = self.npm_calls()
        build_idx = next(i for i, line in enumerate(calls) if line == "npm run build:dist")
        check_idx = next(i for i, line in enumerate(calls) if line == "npm run check:grammars")
        self.assertLess(build_idx, check_idx)

    def test_lens_build_failure_preserves_active_state(self):
        self.configure_lens_plugin()
        first = self.setup_release()
        before = (self.state / "state.json").read_bytes()
        self.descriptor["version"] = "0.2.0"
        self.commit_inputs()
        with mock.patch.dict(os.environ, {"FIXTURE_LENS_BUILD_FAIL": "1"}):
            _, error = self.cli("setup", "--repo", str(self.repo), "--activate", success=False)
        self.assertIn("fixture Lens build failed", error)
        self.assertEqual((self.state / "state.json").read_bytes(), before)
        self.assertEqual(list((self.state / "staging").iterdir()), [])
        active = json.loads(self.cli("--json", "status")[0])
        self.assertEqual(active["active"], first["releaseId"])


if __name__ == "__main__":
    unittest.main()
