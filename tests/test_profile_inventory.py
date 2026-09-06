#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profile"
sys.path.insert(0, str(ROOT))

from attro.profile import validate_profile_tree, validate_resource_package  # noqa: E402
from attro.validate import load_json  # noqa: E402

USERNAME_RE = re.compile(r"/Users/[^/\s\"']+|ernestjusuf")
AGENT_FRONTMATTER_RE = re.compile(r"^---\n(?P<body>.*?)\n---", re.DOTALL)

REQUIRED_AGENT_SEED = {
    "AGENTS.md",
    "keybindings.json",
    "models.json",
    "subagents.json",
    "cursor-sdk.json",
    "cursor-sdk-context-windows.json",
    "pi-caffeinate.json",
    "safety-guard.json",
    "web-search.json",
    "lens-config.json",
    "rpiv-config/rpiv-todo/config.json",
    "claude-plugins.json",
    "extensions/pi-automode/config.json",
}

REQUIRED_AGENTS = {
    "advisor.md",
    "comment-cleaner.md",
    "gitops.md",
    "reviewer.md",
    "scout.md",
    "worker.md",
}

REQUIRED_RESOURCE_PATHS = {
    "package.json",
    "extensions/auto-session-name.ts",
    "extensions/turn-status.ts",
    "extensions/safety-guard.ts",
    "extensions/herdr-agent-state.ts",
    "extensions/herdr-agent-state.NOTICE.md",
    "extensions/herdr-pi-metadata.ts",
    "prompts/issue.md",
    "prompts/review.md",
    "skills/commit/SKILL.md",
    "skills/handoff/SKILL.md",
    "skills/ui-design/SKILL.md",
    "skills/ui-design/NOTICE.md",
    "skills/writing-great-skills/SKILL.md",
    "skills/writing-great-skills/GLOSSARY.md",
    "skills/writing-great-skills/mattpocock-LICENSE",
    "skills/bb-cli/SKILL.md",
    "skills/bb-cli/NOTICE.md",
    "skills/bb-cli/references/app-settings.md",
    "skills/bb-cli/references/theming.md",
    "skills/herdr/SKILL.md",
    "skills/herdr/NOTICE.md",
    "licenses/get-bb-bb-MIT",
    "licenses/herdrdev-herdr-Apache-2.0",
}


class ProfileInventoryTests(unittest.TestCase):
    def test_inventory_exists_and_has_entries(self) -> None:
        inventory = load_json(PROFILE / "inventory.json")
        self.assertEqual(inventory["schemaVersion"], 1)
        self.assertGreater(len(inventory["included"]), 0)
        self.assertGreater(len(inventory["excluded"]), 0)
        for entry in inventory["included"]:
            self.assertIn("source", entry)
            self.assertIn("sourceSha256", entry)
            self.assertIn("destination", entry)
            dest = ROOT / entry["destination"]
            self.assertTrue(dest.is_file(), msg=entry["destination"])

    def test_no_username_paths_in_profile_content(self) -> None:
        for path in PROFILE.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text()
            self.assertIsNone(
                USERNAME_RE.search(text),
                msg=f"username-specific path in {path.relative_to(ROOT)}",
            )

    def test_all_json_files_are_valid(self) -> None:
        for path in PROFILE.rglob("*.json"):
            load_json(path)

    def test_settings_preserves_live_provider_model_prefs(self) -> None:
        settings = load_json(PROFILE / "settings.json")
        self.assertEqual(settings["defaultProvider"], "openai-codex")
        self.assertEqual(settings["defaultModel"], "gpt-6-astra")
        self.assertIn("openai-codex/gpt-6-astra", settings["enabledModels"])
        self.assertNotIn("lastChangelogVersion", settings)
        packages = settings["packages"]
        self.assertEqual(packages[0], "{{NPM:@narumitw/pi-caffeinate}}")
        self.assertEqual(packages[-1], "{{PLUGIN_PI_ZENTUI}}")
        self.assertEqual(
            settings["themes"],
            ["{{THEME_QUATTRO_GREEN}}", "{{THEME_QUATTRO_AMBER}}"],
        )

    def test_safety_guard_seed_disabled_not_neutralized(self) -> None:
        config = load_json(PROFILE / "agent/safety-guard.json")
        self.assertFalse(config["enabled"])
        inventory = load_json(PROFILE / "inventory.json")
        self.assertFalse(inventory["notes"]["safetyGuardEnabled"])

    def test_agent_seed_files_present(self) -> None:
        agent = PROFILE / "agent"
        for rel in REQUIRED_AGENT_SEED:
            self.assertTrue((agent / rel).is_file(), msg=rel)
        for name in REQUIRED_AGENTS:
            self.assertTrue((agent / "agents" / name).is_file(), msg=name)

    def test_agent_definitions_have_frontmatter(self) -> None:
        for path in (PROFILE / "agent" / "agents").glob("*.md"):
            text = path.read_text()
            match = AGENT_FRONTMATTER_RE.match(text)
            self.assertIsNotNone(match, msg=path.name)
            assert match is not None
            body = match.group("body")
            self.assertIn("name:", body)
            self.assertIn("model:", body)

    def test_resource_bundle_paths_present(self) -> None:
        resources = PROFILE / "resources"
        for rel in REQUIRED_RESOURCE_PATHS:
            self.assertTrue((resources / rel).is_file(), msg=rel)

    def test_resource_package_validates(self) -> None:
        validate_profile_tree(PROFILE / "resources")
        validate_resource_package(PROFILE / "resources")

    def test_safety_guard_extension_uses_get_agent_dir(self) -> None:
        text = (PROFILE / "resources/extensions/safety-guard.ts").read_text()
        self.assertIn("getAgentDir()", text)
        self.assertNotIn("homedir()", text)
        self.assertNotIn(".pi/agent", text)

    def test_gitops_references_resource_commit_skill(self) -> None:
        text = (PROFILE / "agent/agents/gitops.md").read_text()
        self.assertIn("${ATTRO_RESOURCE_DIR}/skills/commit/SKILL.md", text)

    def test_writing_great_skills_license_resolves(self) -> None:
        skill = (PROFILE / "resources/skills/writing-great-skills/SKILL.md").read_text()
        self.assertIn("license: ./mattpocock-LICENSE", skill)
        license_path = PROFILE / "resources/skills/writing-great-skills/mattpocock-LICENSE"
        self.assertTrue(license_path.is_file())
        self.assertIn("Matt Pocock", license_path.read_text())

    def test_external_skill_licenses_resolve(self) -> None:
        bb_skill = (PROFILE / "resources/skills/bb-cli/SKILL.md").read_text()
        self.assertIn("license: ../../licenses/get-bb-bb-MIT", bb_skill)
        bb_license = PROFILE / "resources/licenses/get-bb-bb-MIT"
        self.assertTrue(bb_license.is_file())
        self.assertIn("Michael Yong", bb_license.read_text())
        self.assertTrue((PROFILE / "resources/skills/bb-cli/NOTICE.md").is_file())

        herdr_skill = (PROFILE / "resources/skills/herdr/SKILL.md").read_text()
        self.assertIn("license: ../../licenses/herdrdev-herdr-Apache-2.0", herdr_skill)
        self.assertIn("Requires HERDR_ENV=1.", herdr_skill)
        herdr_license = PROFILE / "resources/licenses/herdrdev-herdr-Apache-2.0"
        self.assertTrue(herdr_license.is_file())
        self.assertIn("Apache License", herdr_license.read_text())
        self.assertTrue((PROFILE / "resources/skills/herdr/NOTICE.md").is_file())
        self.assertTrue((PROFILE / "resources/extensions/herdr-agent-state.NOTICE.md").is_file())

    def test_external_skills_not_excluded_from_inventory(self) -> None:
        inventory = load_json(PROFILE / "inventory.json")
        excluded_sources = {entry["source"] for entry in inventory["excluded"]}
        self.assertNotIn("~/.agents/skills/bb-cli", excluded_sources)
        self.assertNotIn("~/.agents/skills/herdr", excluded_sources)
        destinations = {entry["destination"] for entry in inventory["included"]}
        self.assertIn("profile/resources/skills/bb-cli/SKILL.md", destinations)
        self.assertIn("profile/resources/skills/herdr/SKILL.md", destinations)
        self.assertIn("profile/resources/licenses/get-bb-bb-MIT", destinations)
        self.assertIn("profile/resources/licenses/herdrdev-herdr-Apache-2.0", destinations)

    def test_all_inventory_destination_hashes_match(self) -> None:
        inventory = load_json(PROFILE / "inventory.json")
        for entry in inventory["included"]:
            path = ROOT / entry["destination"]
            expected = entry.get("destinationSha256", entry["sourceSha256"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected, entry["destination"])

    def test_inventory_parity_hashes_for_untransformed_seeds(self) -> None:
        inventory = load_json(PROFILE / "inventory.json")
        by_dest = {entry["destination"]: entry for entry in inventory["included"]}
        unchanged = [
            "profile/agent/keybindings.json",
            "profile/agent/models.json",
            "profile/agent/subagents.json",
            "profile/agent/safety-guard.json",
            "profile/agent/web-search.json",
            "profile/agent/lens-config.json",
            "profile/agent/rpiv-config/rpiv-todo/config.json",
        ]
        for dest in unchanged:
            entry = by_dest[dest]
            path = ROOT / dest
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(entry["sourceSha256"], digest, msg=dest)


if __name__ == "__main__":
    unittest.main()
