#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profile"
sys.path.insert(0, str(ROOT))

from attro.profile import seed_agent  # noqa: E402
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
    "{{PLUGIN_PI_ASK_USER}}",
    "{{PLUGIN_PI_LENS}}",
    "{{PLUGIN_PI_WEB_ACCESS}}",
    "{{NPM:@narumitw/pi-goal}}",
    "{{NPM:pi-cursor-sdk}}",
    "{{PLUGIN_PI_SUBAGENTS}}",
    "{{PLUGIN_RPIV_TODO}}",
    "{{PLUGIN_PI_CC_EXTENSIONS}}",
    "{{PLUGIN_PI_ZENTUI}}",
]

EXPECTED_UI_DEFAULTS = {
    "quietStartup": True,
    "hideThinkingBlock": False,
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
        self.assertEqual(settings["theme"], "quattro-green")
        self.assertEqual(settings["packages"], EXPECTED_PACKAGES)
        self.assertEqual(
            settings["themes"],
            ["{{THEME_QUATTRO_GREEN}}", "{{THEME_QUATTRO_AMBER}}"],
        )
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
            self.assertEqual(settings["theme"], "quattro-green")
            self.assertNotIn("packages", settings)
            self.assertNotIn("themes", settings)
            self.assertFalse((target / "AGENTS.md").exists())
            self.assertFalse((target / "models.json").exists())
            self.assertFalse((target / "subagents.json").exists())
            self.assertFalse((target / "agents").exists())
            self.assertTrue((target / "rpiv-config/rpiv-todo/config.json").is_file())


if __name__ == "__main__":
    unittest.main()
