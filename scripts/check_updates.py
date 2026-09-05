#!/usr/bin/env python3
"""Discover upstream updates for Piattro-maintained fork pins.

Read-only discovery: does not mutate sources.lock.json, submodules, or live
checkouts. Emits a deterministic JSON report. Errors are recorded explicitly;
they must not be reported as "up to date".

Optional merge assessment clones the public fork origin at the pinned commit,
fetches upstream HEAD, and tests merge in a disposable temp repo with hooks
and signing disabled. Unreachable private forks report explicit errors.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "sources.lock.json"
DEFAULT_DESCRIPTOR = ROOT / "piattro.json"
DEFAULT_PI_PACKAGE = "@earendil-works/pi-coding-agent"
NPM_REGISTRY = "https://registry.npmjs.org"

SCHEMA_VERSION = 1
DESCRIPTOR_SCHEMA_VERSION = 1
GIT_TIMEOUT = 120
HTTP_TIMEOUT = 30
ALLOWED_GIT_HOSTS = frozenset({"github.com"})
SUPPORTED_CORE_PACKAGES = frozenset({DEFAULT_PI_PACKAGE})
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

GitRunner = Callable[..., subprocess.CompletedProcess[str]]
HttpFetcher = Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class GitRemoteHead:
    default_ref: str | None
    head: str | None
    error: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def validate_git_sha(value: str, *, label: str) -> str | None:
    if not isinstance(value, str) or not GIT_SHA_RE.fullmatch(value):
        return f"{label} must be a 40-character lowercase hex SHA"
    return None


def validate_git_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return "URL must use https"
    if parsed.username or parsed.password:
        return "URL must not embed credentials"
    if parsed.port is not None:
        return "URL must not include an explicit port"
    if parsed.query or parsed.fragment:
        return "URL must not include query or fragment"
    host = parsed.hostname
    if host not in ALLOWED_GIT_HOSTS:
        return f"URL host must be one of {sorted(ALLOWED_GIT_HOSTS)}"
    if not parsed.path.endswith(".git"):
        return "URL must end with .git"
    repo_path = parsed.path[: -len(".git")]
    segments = [segment for segment in repo_path.split("/") if segment]
    if len(segments) != 2:
        return "URL path must be /owner/repo.git"
    owner, repo = segments
    if not owner or not repo or owner.startswith(".") or repo.startswith("."):
        return "URL owner and repo must be non-empty"
    return None


def git_safe_env() -> list[str]:
    return [
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "tag.gpgSign=false",
        "-c",
        "gpg.program=true",
    ]


def default_git_runner(*args: str, cwd: Path | None = None, timeout: int = GIT_TIMEOUT) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except OSError as error:
        return subprocess.CompletedProcess(
            args=("git", *args),
            returncode=127,
            stdout="",
            stderr=f"git execution failed: {error}",
        )


def parse_ls_remote_symref(stdout: str) -> GitRemoteHead:
    default_ref: str | None = None
    head: str | None = None
    for line in stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        left, right = parts
        if right == "HEAD" and left.startswith("ref: "):
            default_ref = left.removeprefix("ref: ").strip()
            continue
        if right == "HEAD" and GIT_SHA_RE.fullmatch(left):
            head = left
            continue
        if default_ref and right == default_ref and GIT_SHA_RE.fullmatch(left):
            head = left
    if head is None:
        return GitRemoteHead(default_ref=default_ref, head=None, error="upstream HEAD not found")
    invalid = validate_git_sha(head, label="upstream HEAD")
    if invalid:
        return GitRemoteHead(default_ref=default_ref, head=None, error=invalid)
    return GitRemoteHead(default_ref=default_ref, head=head, error=None)


def git_ls_remote_head(url: str, git: GitRunner = default_git_runner) -> GitRemoteHead:
    invalid = validate_git_url(url)
    if invalid:
        return GitRemoteHead(default_ref=None, head=None, error=invalid)
    try:
        result = git("ls-remote", "--symref", url, "HEAD")
    except subprocess.TimeoutExpired:
        return GitRemoteHead(default_ref=None, head=None, error="git ls-remote timed out")
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "git ls-remote failed").strip()
        return GitRemoteHead(default_ref=None, head=None, error=message)
    return parse_ls_remote_symref(result.stdout)


def default_http_fetch(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "pi-customizations-check-updates/1"})
    with urlopen(request, timeout=HTTP_TIMEOUT) as response:
        payload = response.read().decode("utf-8")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise RuntimeError("npm registry response is not an object")
    return value


def npm_registry_latest_url(package_name: str) -> str:
    encoded = quote(package_name, safe="")
    return f"{NPM_REGISTRY}/{encoded}/latest"



def fetch_npm_latest(package_name: str, fetch_json: HttpFetcher) -> tuple[str | None, str | None]:
    try:
        latest_doc = fetch_json(npm_registry_latest_url(package_name))
    except (URLError, TimeoutError, json.JSONDecodeError, RuntimeError, OSError) as error:
        return None, f"npm lookup failed for {package_name}: {error}"
    version = latest_doc.get("version")
    if isinstance(version, str) and version.strip():
        return version.strip(), None
    return None, f"npm latest response missing version for {package_name}"


def discover_descriptor(
    descriptor_path: Path,
    fetch_json: HttpFetcher = default_http_fetch,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    rel_path = str(descriptor_path.relative_to(ROOT)) if descriptor_path.is_relative_to(ROOT) else str(descriptor_path)

    if not descriptor_path.is_file():
        errors.append(f"descriptor missing: {rel_path}")
        return {
            "descriptorPath": rel_path,
            "descriptorPresent": False,
            "descriptorSchemaVersion": None,
            "distribution": None,
            "releaseVersion": None,
            "core": None,
            "npmPackages": [],
        }, errors

    try:
        descriptor = load_json(descriptor_path)
    except RuntimeError as error:
        errors.append(str(error))
        return {
            "descriptorPath": rel_path,
            "descriptorPresent": True,
            "descriptorSchemaVersion": None,
            "distribution": None,
            "releaseVersion": None,
            "core": None,
            "npmPackages": [],
        }, errors

    schema = descriptor.get("schemaVersion")
    if schema != DESCRIPTOR_SCHEMA_VERSION:
        errors.append(
            f"descriptor schemaVersion must be exactly {DESCRIPTOR_SCHEMA_VERSION}, got {schema!r}"
        )

    distribution = descriptor.get("distribution")
    if not isinstance(distribution, str) or not distribution.strip():
        errors.append("descriptor distribution must be a non-empty string")
        distribution = None
    else:
        distribution = distribution.strip()

    release_version = descriptor.get("version")
    if not isinstance(release_version, str) or not release_version.strip():
        errors.append("descriptor version must be a non-empty string")
        release_version = None
    else:
        release_version = release_version.strip()

    core_section = descriptor.get("core")
    core_report: dict[str, Any] | None = None
    if not isinstance(core_section, dict):
        errors.append("descriptor core must be an object")
    else:
        package_name = core_section.get("package")
        pinned_version = core_section.get("version")
        if not isinstance(package_name, str) or not package_name.strip():
            errors.append("descriptor core.package must be a non-empty string")
            package_name = None
        else:
            package_name = package_name.strip()
            if package_name not in SUPPORTED_CORE_PACKAGES:
                errors.append(
                    f"descriptor core.package {package_name!r} is not supported; "
                    f"expected one of {sorted(SUPPORTED_CORE_PACKAGES)}"
                )
        if not isinstance(pinned_version, str) or not pinned_version.strip():
            errors.append("descriptor core.version must be a non-empty string")
            pinned_version = None
        else:
            pinned_version = pinned_version.strip()

        npm_latest: str | None = None
        npm_error: str | None = None
        if package_name:
            npm_latest, npm_error = fetch_npm_latest(package_name, fetch_json)
            if npm_error:
                errors.append(npm_error)

        update_available = bool(
            package_name
            and pinned_version
            and npm_latest
            and pinned_version != npm_latest
        )
        core_report = {
            "packageName": package_name,
            "pinnedVersion": pinned_version,
            "npmLatest": npm_latest,
            "updateAvailable": update_available,
            "error": npm_error,
        }

    npm_packages_raw = descriptor.get("npmPackages")
    npm_package_reports: list[dict[str, Any]] = []
    if npm_packages_raw is None:
        pass
    elif not isinstance(npm_packages_raw, list):
        errors.append("descriptor npmPackages must be an array when present")
    else:
        for index, item in enumerate(npm_packages_raw):
            label = f"npmPackages[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label} must be an object")
                continue
            package_name = item.get("package")
            pinned_version = item.get("version")
            if not isinstance(package_name, str) or not package_name.strip():
                errors.append(f"{label}.package must be a non-empty string")
                npm_package_reports.append(
                    {
                        "package": package_name,
                        "pinnedVersion": None,
                        "npmLatest": None,
                        "updateAvailable": False,
                        "error": "invalid package record",
                    }
                )
                continue
            package_name = package_name.strip()
            if not isinstance(pinned_version, str) or not pinned_version.strip():
                errors.append(f"{label}.version must be a non-empty string")
                npm_package_reports.append(
                    {
                        "package": package_name,
                        "pinnedVersion": None,
                        "npmLatest": None,
                        "updateAvailable": False,
                        "error": "invalid package record",
                    }
                )
                continue
            pinned_version = pinned_version.strip()
            npm_latest, npm_error = fetch_npm_latest(package_name, fetch_json)
            if npm_error:
                errors.append(f"{label}: {npm_error}")
            npm_package_reports.append(
                {
                    "package": package_name,
                    "pinnedVersion": pinned_version,
                    "npmLatest": npm_latest,
                    "updateAvailable": bool(npm_latest and pinned_version != npm_latest),
                    "error": npm_error,
                }
            )

    npm_package_reports.sort(key=lambda item: str(item.get("package") or ""))

    return {
        "descriptorPath": rel_path,
        "descriptorPresent": True,
        "descriptorSchemaVersion": schema if isinstance(schema, int) else None,
        "distribution": distribution,
        "releaseVersion": release_version,
        "core": core_report,
        "npmPackages": npm_package_reports,
    }, errors


def assess_fork_merge(
    origin_url: str,
    fork_pin: str,
    upstream_url: str,
    upstream_head: str,
    git: GitRunner = default_git_runner,
) -> dict[str, Any]:
    for url, label in ((origin_url, "origin"), (upstream_url, "upstream")):
        invalid = validate_git_url(url)
        if invalid:
            return {"status": "error", "clean": None, "error": f"{label} URL invalid: {invalid}"}

    for value, label in ((fork_pin, "fork pin"), (upstream_head, "upstream head")):
        invalid = validate_git_sha(value, label=label)
        if invalid:
            return {"status": "error", "clean": None, "error": invalid}

    if fork_pin == upstream_head:
        return {"status": "clean", "clean": True, "error": None}

    safe = git_safe_env()
    with tempfile.TemporaryDirectory(prefix="piattro-merge-check-") as tmp:
        repo = Path(tmp) / "fork"
        try:
            clone = git("clone", "--no-checkout", origin_url, str(repo))
            if clone.returncode != 0:
                message = (clone.stderr or clone.stdout or "git clone failed").strip()
                return {"status": "error", "clean": None, "error": message}

            fetch_pin = git(*safe, "fetch", "origin", fork_pin, cwd=repo)
            if fetch_pin.returncode != 0:
                message = (fetch_pin.stderr or fetch_pin.stdout or "fetch fork pin failed").strip()
                return {"status": "error", "clean": None, "error": message}

            checkout = git(*safe, "checkout", "--detach", fork_pin, cwd=repo)
            if checkout.returncode != 0:
                message = (checkout.stderr or checkout.stdout or "checkout fork pin failed").strip()
                return {"status": "error", "clean": None, "error": message}

            add_upstream = git("remote", "add", "upstream", upstream_url, cwd=repo)
            if add_upstream.returncode != 0:
                message = (add_upstream.stderr or add_upstream.stdout or "add upstream remote failed").strip()
                return {"status": "error", "clean": None, "error": message}

            fetch_upstream = git(*safe, "fetch", "upstream", upstream_head, cwd=repo)
            if fetch_upstream.returncode != 0:
                message = (fetch_upstream.stderr or fetch_upstream.stdout or "fetch upstream head failed").strip()
                return {"status": "error", "clean": None, "error": message}

            merge = git(
                *safe,
                "merge",
                "--no-commit",
                "--no-ff",
                "FETCH_HEAD",
                cwd=repo,
            )
            if merge.returncode == 0:
                return {"status": "clean", "clean": True, "error": None}
            if merge.returncode == 1:
                git(*safe, "merge", "--abort", cwd=repo)
                return {"status": "conflict", "clean": False, "error": None}
            message = (merge.stderr or merge.stdout or "git merge failed").strip()
            return {"status": "error", "clean": None, "error": message}
        except subprocess.TimeoutExpired:
            return {"status": "error", "clean": None, "error": "merge assessment timed out"}


def discover_submodule(
    entry: dict[str, Any],
    *,
    assess_merges: bool,
    git: GitRunner,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    name = entry.get("name", entry.get("path", "unknown"))
    upstream_url = entry.get("upstream")
    origin_url = entry.get("origin")
    if not isinstance(upstream_url, str):
        errors.append(f"{name}: missing upstream URL")
        upstream_url = ""
    if not isinstance(origin_url, str):
        errors.append(f"{name}: missing origin URL")
        origin_url = ""

    remote = git_ls_remote_head(upstream_url, git=git) if upstream_url else GitRemoteHead(None, None, "missing upstream URL")
    if remote.error:
        errors.append(f"{name}: upstream lookup failed: {remote.error}")

    pin = entry.get("pin")
    base_commit = entry.get("baseCommit")
    if isinstance(pin, str):
        invalid_pin = validate_git_sha(pin, label=f"{name} pin")
        if invalid_pin:
            errors.append(f"{name}: {invalid_pin}")
    if isinstance(base_commit, str):
        invalid_base = validate_git_sha(base_commit, label=f"{name} baseCommit")
        if invalid_base:
            errors.append(f"{name}: {invalid_base}")

    upstream_head = remote.head
    upstream_moved = bool(
        isinstance(base_commit, str)
        and isinstance(upstream_head, str)
        and base_commit != upstream_head
    )
    pin_behind_upstream = bool(
        isinstance(pin, str) and isinstance(upstream_head, str) and pin != upstream_head
    )

    merge_assessment: dict[str, Any]
    if not assess_merges:
        merge_assessment = {"requested": False, "status": "skipped", "clean": None, "error": None}
    elif remote.error:
        merge_assessment = {
            "requested": True,
            "status": "skipped",
            "clean": None,
            "error": "upstream lookup failed before merge assessment",
        }
    elif not isinstance(pin, str) or validate_git_sha(pin, label="pin"):
        merge_assessment = {
            "requested": True,
            "status": "error",
            "clean": None,
            "error": "fork pin missing or invalid",
        }
        errors.append(f"{name}: fork pin missing or invalid for merge assessment")
    elif upstream_head is None:
        merge_assessment = {
            "requested": True,
            "status": "error",
            "clean": None,
            "error": "upstream head missing",
        }
    elif pin == upstream_head:
        merge_assessment = {"requested": True, "status": "skipped", "clean": True, "error": None}
    else:
        assessed = assess_fork_merge(origin_url, pin, upstream_url, upstream_head, git=git)
        merge_assessment = {
            "requested": True,
            "status": assessed["status"],
            "clean": assessed["clean"],
            "error": assessed["error"],
        }
        if assessed["status"] == "error" and assessed["error"]:
            errors.append(f"{name}: merge assessment failed: {assessed['error']}")

    record = {
        "name": name,
        "path": entry.get("path"),
        "pin": pin,
        "baseCommit": base_commit,
        "baseVersion": entry.get("baseVersion"),
        "origin": origin_url,
        "upstream": {
            "url": upstream_url,
            "defaultRef": remote.default_ref,
            "head": upstream_head,
            "error": remote.error,
        },
        "discovery": {
            "upstreamMovedSinceBase": upstream_moved,
            "pinDiffersFromUpstreamHead": pin_behind_upstream,
        },
        "mergeAssessment": merge_assessment,
    }
    return record, errors


def descriptor_has_updates(descriptor: dict[str, Any]) -> bool:
    core = descriptor.get("core")
    if isinstance(core, dict) and core.get("updateAvailable"):
        return True
    for item in descriptor.get("npmPackages") or []:
        if isinstance(item, dict) and item.get("updateAvailable"):
            return True
    return False


def build_report(
    lock_path: Path,
    descriptor_path: Path,
    *,
    assess_merges: bool,
    git: GitRunner = default_git_runner,
    fetch_json: HttpFetcher = default_http_fetch,
) -> dict[str, Any]:
    report_errors: list[str] = []
    descriptor, descriptor_errors = discover_descriptor(descriptor_path, fetch_json=fetch_json)
    report_errors.extend(descriptor_errors)

    try:
        manifest = load_json(lock_path)
    except RuntimeError as error:
        report_errors.append(str(error))
        return {
            "schemaVersion": SCHEMA_VERSION,
            "generatedAt": utc_now_iso(),
            "status": "error",
            "sourcesLock": {"path": str(lock_path), "error": str(error)},
            "descriptor": descriptor,
            "submodules": [],
            "errors": report_errors,
            "summary": {
                "submodulesWithUpstreamUpdates": 0,
                "submodulesWithErrors": 0,
                "descriptorUpdatesAvailable": False,
            },
        }

    submodules_raw = manifest.get("submodules")
    if not isinstance(submodules_raw, list):
        report_errors.append("sources.lock.json submodules must be a list")

    submodule_records: list[dict[str, Any]] = []
    submodule_errors = 0
    upstream_updates = 0
    if isinstance(submodules_raw, list):
        for entry in submodules_raw:
            if not isinstance(entry, dict):
                report_errors.append("submodules entry is not an object")
                continue
            record, entry_errors = discover_submodule(entry, assess_merges=assess_merges, git=git)
            submodule_records.append(record)
            if entry_errors:
                submodule_errors += 1
                report_errors.extend(entry_errors)
            if record["discovery"]["upstreamMovedSinceBase"]:
                upstream_updates += 1

    descriptor_updates = descriptor_has_updates(descriptor)
    has_updates = upstream_updates > 0 or descriptor_updates
    if report_errors:
        status = "error"
    elif has_updates:
        status = "updates_available"
    else:
        status = "ok"

    submodule_records.sort(key=lambda item: str(item.get("path") or item.get("name") or ""))

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": utc_now_iso(),
        "status": status,
        "sourcesLock": {
            "path": str(lock_path.relative_to(ROOT)) if lock_path.is_relative_to(ROOT) else str(lock_path),
            "schemaVersion": manifest.get("schemaVersion"),
            "branch": manifest.get("branch"),
            "submoduleCount": len(submodule_records),
        },
        "descriptor": descriptor,
        "submodules": submodule_records,
        "errors": report_errors,
        "summary": {
            "submodulesWithUpstreamUpdates": upstream_updates,
            "submodulesWithErrors": submodule_errors,
            "descriptorUpdatesAvailable": descriptor_updates,
        },
    }


def dumps_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def exit_code_for_report(report: dict[str, Any], *, fail_on_updates: bool) -> int:
    if report.get("errors"):
        return 1
    if fail_on_updates and report.get("status") == "updates_available":
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lock",
        type=Path,
        default=DEFAULT_LOCK,
        help="path to sources.lock.json (default: repo root)",
    )
    parser.add_argument(
        "--descriptor",
        type=Path,
        default=DEFAULT_DESCRIPTOR,
        help="piattro release descriptor (required)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="write JSON report to this path (default: stdout)",
    )
    parser.add_argument(
        "--assess-merges",
        action="store_true",
        help="assess fork pin vs upstream HEAD in disposable origin clones",
    )
    parser.add_argument(
        "--fail-on-updates",
        action="store_true",
        help="exit 2 when updates are available and no errors occurred",
    )
    args = parser.parse_args(argv)

    lock_path = args.lock.resolve()
    descriptor_path = args.descriptor.resolve()
    if not lock_path.is_file():
        print(f"FAIL: lock file missing: {lock_path}", file=sys.stderr)
        return 1

    report = build_report(
        lock_path,
        descriptor_path,
        assess_merges=args.assess_merges,
    )
    rendered = dumps_report(report)
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)

    code = exit_code_for_report(report, fail_on_updates=args.fail_on_updates)
    if code == 1:
        for error in report.get("errors", []):
            print(f"FAIL: {error}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
