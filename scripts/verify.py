#!/usr/bin/env python3
"""Verify the checked-in source pins and copied configuration.

Default mode is intentionally a source/configuration check.  It does not install,
build, authenticate, fetch, or write anything.  Use --runtime after performing the
documented Lens build to require listed runtime files to be present; that option
still does not check dependencies or host compatibility.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "sources.lock.json"
PUBLIC_SUBAGENTS = "https://github.com/ernestjsf/pi-subagents.git"


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"git operation failed (exit {result.returncode})")
    return result.stdout.strip()


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def verify_submodule(entry: dict, runtime: bool, failures: list[str], notes: list[str]) -> None:
    rel = entry["path"]
    path = ROOT / rel
    pin = entry["pin"]
    if not path.is_dir():
        fail(f"{rel}: submodule directory is missing", failures)
        return

    stage = git("ls-files", "--stage", "--", rel)
    fields = stage.split()
    if len(fields) < 4 or fields[0] != "160000":
        fail(f"{rel}: root index does not contain a gitlink", failures)
    elif fields[1] != pin:
        fail(f"{rel}: gitlink {fields[1]} != manifest pin {pin}", failures)

    try:
        head = git("rev-parse", "HEAD", cwd=path)
    except RuntimeError as error:
        fail(f"{rel}: {error}", failures)
        return
    if head != pin:
        fail(f"{rel}: checked-out HEAD {head} != manifest pin {pin}", failures)

    status = git("status", "--porcelain", "--untracked-files=all", cwd=path)
    if status:
        fail(f"{rel}: submodule is dirty:\n{status}", failures)

    origin = git("remote", "get-url", "origin", cwd=path)
    if origin != entry["origin"]:
        fail(f"{rel}: origin does not match the approved private origin", failures)
    if origin == PUBLIC_SUBAGENTS:
        fail(f"{rel}: public pi-subagents origin is forbidden", failures)

    # Upstream remotes are local clone configuration, not versioned state.  If
    # present, still ensure they point at the documented provenance source.
    remotes = git("remote", cwd=path).splitlines()
    if "upstream" in remotes:
        upstream = git("remote", "get-url", "upstream", cwd=path)
        if upstream != entry["upstream"]:
            fail(f"{rel}: upstream does not match documented provenance", failures)

    root_package_file = path / "package.json"
    if not root_package_file.is_file():
        fail(f"{rel}: root package.json is missing", failures)
    else:
        try:
            package = load_json(root_package_file)
        except RuntimeError as error:
            fail(f"{rel}: {error}", failures)
            package = {}
        if package.get("name") != entry["name"]:
            fail(f"{rel}: root package name does not match manifest", failures)
        if package.get("version") != entry["baseVersion"]:
            fail(f"{rel}: root package version does not match manifest baseVersion", failures)

    package_path = path / entry["packagePath"]
    package_name = entry.get("packageName")
    if package_name:
        package_file = package_path / "package.json"
        if not package_file.is_file():
            fail(f"{rel}: runtime package.json is missing at {entry['packagePath']}", failures)
        else:
            try:
                runtime_package = load_json(package_file)
            except RuntimeError as error:
                fail(f"{rel}: {error}", failures)
                runtime_package = {}
            if runtime_package.get("name") != package_name:
                fail(f"{rel}: runtime package name does not match manifest", failures)
            if runtime_package.get("version") != entry["packageVersion"]:
                fail(f"{rel}: runtime package version does not match manifest", failures)

    lock_name = entry.get("dependencyLock")
    if lock_name:
        lock_path = path / lock_name
        if not lock_path.is_file():
            fail(f"{rel}: dependency lockfile {lock_name} is missing", failures)
        else:
            try:
                lock = load_json(lock_path)
            except RuntimeError as error:
                fail(f"{rel}: {error}", failures)
                lock = {}
            if lock.get("lockfileVersion") != entry["dependencyLockVersion"]:
                fail(f"{rel}: dependency lockfile version does not match manifest", failures)
    elif entry.get("dependencyLockVersion") is not None:
        fail(f"{rel}: lockfile version is set without a lockfile", failures)

    for source_file in entry["sourceEntryFiles"]:
        if not (path / source_file).is_file():
            fail(f"{rel}: required source entry is missing: {source_file}", failures)

    missing_runtime = [
        runtime_file
        for runtime_file in entry["runtimeEntryFiles"]
        if not (path / runtime_file).is_file()
    ]
    if missing_runtime:
        message = f"{rel}: preparation-required runtime entries missing: {', '.join(missing_runtime)}"
        if runtime:
            fail(message, failures)
        else:
            notes.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime",
        action="store_true",
        help="also require listed runtime files to be present; no build or compatibility check",
    )
    args = parser.parse_args()

    failures: list[str] = []
    notes: list[str] = []
    if not LOCK.is_file():
        print("FAIL: sources.lock.json is missing", file=sys.stderr)
        return 1
    try:
        manifest = load_json(LOCK)
        package = load_json(ROOT / "package.json")
    except RuntimeError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if type(package.get("private")) != bool or not package.get("private") or package.get("version") != "0.1.0":
        fail("root package must be private at version 0.1.0", failures)
    expected_quattro_themes = ["./themes/quattro-amber.json", "./themes/quattro-green.json"]
    pi_manifest = package.get("pi")
    if pi_manifest != {"themes": expected_quattro_themes}:
        fail("root pi manifest must declare Quattro themes for originalPi checkout use", failures)
    for rel in expected_quattro_themes:
        if not (ROOT / rel.removeprefix("./")).is_file():
            fail(f"root pi theme source missing: {rel}", failures)
    profile = load_json(ROOT / "profile" / "settings.json")
    if "theme" in profile or "themes" in profile:
        fail("profile/settings.json must not declare theme defaults for new Attro releases", failures)
    config_paths = {entry["path"] for entry in manifest["configs"]}
    if config_paths & {"themes/quattro-green.json", "themes/quattro-amber.json"}:
        fail("sources.lock.json must not copy Quattro themes into new Attro releases", failures)
    if config_paths != {"config/zentui.json", "config/claude-code-style.json", "config/rpiv-todo.json"}:
        fail("sources.lock.json configs must match the three shared display defaults", failures)

    expected_gitmodules = {
        entry["path"]: entry["origin"] for entry in manifest["submodules"]
    }
    for rel, expected_url in expected_gitmodules.items():
        configured = git("config", "--file", ".gitmodules", "--get", f"submodule.{rel}.url")
        if configured != expected_url:
            fail(f"{rel}: .gitmodules URL is not the approved origin", failures)

    for entry in manifest["submodules"]:
        verify_submodule(entry, args.runtime, failures, notes)

    for config in manifest["configs"]:
        path = ROOT / config["path"]
        if not path.is_file():
            fail(f"config missing: {config['path']}", failures)
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != config["sha256"]:
            fail(f"config hash mismatch: {config['path']}", failures)

    for note in notes:
        print(f"PREPARATION: {note}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("PASS: source pins, clean submodules, approved origins, entry files, and config hashes verified")
    print("NOTE: this check does not inspect activation or modify live settings/packages")
    if not args.runtime:
        print("NOTE: runtime-file presence is not checked; run the documented Lens build, then verify.py --runtime")
        print("NOTE: --runtime checks file presence only; it does not prove dependency or host compatibility")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
