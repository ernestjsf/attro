from __future__ import annotations

ATTRO_STATE_SCHEMA = 1
ATTRO_DESCRIPTOR_SCHEMA = 1
ATTRO_MANIFEST_SCHEMA = 1
SUPPORTED_PLATFORMS = frozenset({"darwin", "linux"})
PREPARED_MARKER = ".prepared"
OPERATIONS_LOCK = ".operations.lock"
STATE_FILE = "state.json"
MANIFEST_FILE = "manifest.json"
DESCRIPTOR_FILE = "attro.json"

# Hardcoded reviewed shell commands only — never execute manifest shell strings.
NPM_CI = ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
NPM_INSTALL = ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"]
LENS_BUILD = ["npm", "run", "build:dist"]
LENS_GRAMMARS = ["node", "scripts/download-grammars.js", "--core", "--dest", "grammars"]
LENS_CHECK_GRAMMARS = ["npm", "run", "check:grammars"]
CORE_BUILD_OFFLINE = ["npm", "run", "build:offline"]
CORE_CHECK_MODEL_DATA = ["node", "packages/ai/scripts/check-model-data.ts"]
CORE_SOURCE_SUBMODULE = "plugins/attro-core"
CORE_MODEL_DATA_REL = "packages/ai/src/providers/data"
CORE_CLI_REL = "packages/coding-agent/dist/bundle/cli.js"
RUNTIME_GENERATED_SUBMODULES = frozenset({"plugins/pi-lens", "plugins/attro-core"})

PLUGIN_PATHS = {
    "pi-zentui": "plugins/pi-zentui",
    "pi-cc-extensions": "plugins/pi-cc-extensions",
    "pi-web-access": "plugins/pi-web-access",
    "pi-lens": "plugins/pi-lens",
    "rpiv-todo": "plugins/rpiv-mono/packages/rpiv-todo",
    "pi-ask-user": "plugins/pi-ask-user",
    "pi-subagents": "plugins/pi-subagents",
}

PROFILE_PLACEHOLDERS = {
    "{{PLUGIN_PI_ZENTUI}}": PLUGIN_PATHS["pi-zentui"],
    "{{PLUGIN_PI_CC_EXTENSIONS}}": PLUGIN_PATHS["pi-cc-extensions"],
    "{{PLUGIN_PI_WEB_ACCESS}}": PLUGIN_PATHS["pi-web-access"],
    "{{PLUGIN_PI_LENS}}": PLUGIN_PATHS["pi-lens"],
    "{{PLUGIN_RPIV_TODO}}": PLUGIN_PATHS["rpiv-todo"],
    "{{PLUGIN_PI_ASK_USER}}": PLUGIN_PATHS["pi-ask-user"],
    "{{PLUGIN_PI_SUBAGENTS}}": PLUGIN_PATHS["pi-subagents"],
    "{{THEME_QUATTRO_GREEN}}": "config/quattro-green.json",
    "{{THEME_QUATTRO_AMBER}}": "config/quattro-amber.json",
}

AGENT_SEED_CONFIGS = (
    "zentui.json",
    "claude-code-style.json",
    "rpiv-todo.json",
)

# Private files we never copy into managed releases.
FORBIDDEN_COPY_PATTERNS = (
    "auth.json",
    "credentials",
    "sessions",
    "trust.json",
    ".env",
)
