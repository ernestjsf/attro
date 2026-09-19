#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profile"
sys.path.insert(0, str(ROOT))

from attro.launch import managed_resource_args  # noqa: E402
from attro.profile import initialize_shared_agent, seed_agent  # noqa: E402
from attro.validate import load_json, render_profile, validate_descriptor  # noqa: E402

PERSONAL_SETTINGS_KEYS = frozenset({
    "defaultProvider",
    "defaultModel",
    "enabledModels",
    "defaultThinkingLevel",
    "modelThinkingLevels",
})

EXPECTED_PACKAGES = [
    "{{NPM:@narumitw/pi-caffeinate}}",
    "{{NPM:pi-btw}}",
    "{{NPM:pi-ask-user}}",
    "{{PLUGIN_PI_LENS}}",
    "{{NPM:pi-web-access}}",
    "{{NPM:pi-cursor-sdk}}",
    "{{PLUGIN_PI_SUBAGENTS}}",
    "{{PLUGIN_RPIV_TODO}}",
    "{{PLUGIN_PI_CC_EXTENSIONS}}",
    "{{PLUGIN_PI_ZENTUI}}",
]

EXPECTED_UI_DEFAULTS = {
    "quietStartup": True,
    "hideThinkingBlock": True,
    "editorPaddingX": 0,
    "outputPad": 1,
    "tuiMode": "fullscreen",
    "fullscreenScrollbar": "auto",
    "fullscreenExitOutput": "resume-hint",
    "collapseChangelog": True,
    "markdown": {"mermaid": "final"},
}


class ProfileBoundaryTests(unittest.TestCase):
    def test_shipped_descriptor_excludes_personal_seed_and_resources(self) -> None:
        descriptor = validate_descriptor(ROOT / "attro.json")
        self.assertNotIn("profileSeed", descriptor)
        self.assertNotIn("profileResources", descriptor)
        self.assertEqual(descriptor["profile"], "profile/settings.json")

    def test_shipped_profile_tree_has_no_personal_bundles(self) -> None:
        self.assertFalse((PROFILE / "agent").exists())
        self.assertFalse((PROFILE / "resources").exists())
        self.assertFalse((PROFILE / "inventory.json").exists())

    def test_shipped_settings_json_valid(self) -> None:
        load_json(PROFILE / "settings.json")

    def test_shipped_settings_ui_defaults_without_personal_routing(self) -> None:
        settings = load_json(PROFILE / "settings.json")
        for key in PERSONAL_SETTINGS_KEYS:
            self.assertNotIn(key, settings, msg=key)
        self.assertNotIn("defaultProjectTrust", settings)
        self.assertNotIn("sessionDir", settings)
        self.assertNotIn("theme", settings)
        self.assertNotIn("themes", settings)
        self.assertEqual(settings["packages"], EXPECTED_PACKAGES)
        for key, value in EXPECTED_UI_DEFAULTS.items():
            self.assertEqual(settings[key], value)

    def test_render_profile_omits_resource_bundle_package(self) -> None:
        descriptor = validate_descriptor(ROOT / "attro.json")
        rendered = json.loads(
            render_profile(
                (PROFILE / "settings.json").read_text(),
                ROOT,
                ROOT,
                descriptor,
            )
        )
        for key in PERSONAL_SETTINGS_KEYS:
            self.assertNotIn(key, rendered, msg=key)
        package_paths = rendered["packages"]
        self.assertFalse(any(path.endswith("/profile/resources") for path in package_paths))

    def test_seed_agent_from_ui_only_release(self) -> None:
        descriptor = validate_descriptor(ROOT / "attro.json")
        rendered = json.loads(
            render_profile(
                (PROFILE / "settings.json").read_text(),
                ROOT,
                ROOT,
                descriptor,
            )
        )
        with tempfile.TemporaryDirectory() as work:
            release = Path(work) / "release"
            config = release / "config"
            config.mkdir(parents=True)
            (config / "settings.json").write_text(json.dumps(rendered) + "\n")
            for name in ("zentui.json", "claude-code-style.json", "rpiv-todo.json"):
                shutil_copy = ROOT / "config" / name
                if shutil_copy.is_file():
                    (config / name).write_bytes(shutil_copy.read_bytes())
            (release / "profile" / "agent").mkdir(parents=True)
            target = Path(work) / "agent"
            seed_agent(release, target)
            settings = load_json(target / "settings.json")
            for key in PERSONAL_SETTINGS_KEYS:
                self.assertNotIn(key, settings, msg=key)
            self.assertNotIn("theme", settings)
            self.assertNotIn("packages", settings)
            self.assertNotIn("themes", settings)
            self.assertFalse((target / "AGENTS.md").exists())
            self.assertFalse((target / "models.json").exists())
            self.assertFalse((target / "subagents.json").exists())
            self.assertFalse((target / "agents").exists())
            self.assertTrue((target / "rpiv-config/rpiv-todo/config.json").is_file())

    def test_shipped_sources_lock_omits_theme_configs(self) -> None:
        lock = load_json(ROOT / "sources.lock.json")
        config_paths = {entry["path"] for entry in lock["configs"]}
        self.assertFalse(config_paths & {"themes/quattro-green.json", "themes/quattro-amber.json"})
        self.assertEqual(
            config_paths,
            {"config/zentui.json", "config/claude-code-style.json", "config/rpiv-todo.json"},
        )

    def test_root_package_exports_quattro_themes_for_original_pi_only(self) -> None:
        package = load_json(ROOT / "package.json")
        themes = package.get("pi", {}).get("themes", [])
        self.assertEqual(themes, ["./themes/quattro-amber.json", "./themes/quattro-green.json"])
        for rel in themes:
            self.assertTrue((ROOT / rel.removeprefix("./")).is_file(), rel)

    def test_managed_plugin_themes_are_not_quattro_recipe(self) -> None:
        cc = load_json(ROOT / "plugins/pi-cc-extensions/package.json")
        cc_themes = cc.get("pi", {}).get("themes", [])
        self.assertTrue(cc_themes)
        self.assertTrue(all("quattro" not in path for path in cc_themes))
        managed_packages = [
            ROOT / "plugins/pi-zentui/package.json",
            ROOT / "plugins/pi-lens/package.json",
            ROOT / "plugins/pi-subagents/package.json",
            ROOT / "plugins/rpiv-mono/packages/rpiv-todo/package.json",
        ]
        for path in managed_packages:
            if not path.is_file():
                continue
            pi = load_json(path).get("pi", {})
            self.assertNotIn("themes", pi, msg=str(path))

    def test_rendered_release_omits_theme_resources(self) -> None:
        descriptor = validate_descriptor(ROOT / "attro.json")
        rendered = json.loads(
            render_profile(
                (PROFILE / "settings.json").read_text(),
                ROOT,
                ROOT,
                descriptor,
            )
        )
        self.assertNotIn("theme", rendered)
        self.assertNotIn("themes", rendered)

    def test_managed_launch_omits_theme_flags(self) -> None:
        descriptor = validate_descriptor(ROOT / "attro.json")
        rendered = json.loads(
            render_profile(
                (PROFILE / "settings.json").read_text(),
                ROOT / "releases" / "fixture-release",
                ROOT,
                descriptor,
            )
        )
        with tempfile.TemporaryDirectory() as work:
            release = Path(work) / "release"
            config = release / "config"
            config.mkdir(parents=True)
            (config / "settings.json").write_text(json.dumps(rendered) + "\n")
            with mock.patch("attro.launch.prepared_manifest", return_value={"agentMode": "shared-v1"}):
                argv = managed_resource_args(release)
            self.assertNotIn("--theme", argv)

    def test_existing_theme_selection_retained_after_profile_init(self) -> None:
        descriptor = validate_descriptor(ROOT / "attro.json")
        rendered = json.loads(
            render_profile(
                (PROFILE / "settings.json").read_text(),
                ROOT,
                ROOT,
                descriptor,
            )
        )
        with tempfile.TemporaryDirectory() as work:
            state_root = Path(work) / "managed"
            state_root.mkdir()
            release = state_root / "releases" / "attro-0.2.0-fixture"
            config = release / "config"
            config.mkdir(parents=True)
            (config / "settings.json").write_text(json.dumps(rendered) + "\n")
            for name in ("zentui.json", "claude-code-style.json", "rpiv-todo.json"):
                source = ROOT / "config" / name
                if source.is_file():
                    (config / name).write_bytes(source.read_bytes())
            (release / "profile" / "agent").mkdir(parents=True)
            initialize_shared_agent(state_root, release)
            agent = state_root / "agent"
            settings = load_json(agent / "settings.json")
            self.assertNotIn("theme", settings)
            settings["theme"] = "quattro-green"
            (agent / "settings.json").write_text(json.dumps(settings) + "\n")
            initialize_shared_agent(state_root, release)
            self.assertEqual(load_json(agent / "settings.json")["theme"], "quattro-green")


if __name__ == "__main__":
    unittest.main()
