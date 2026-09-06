#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import check_updates

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40

VALID_DESCRIPTOR = {
    "schemaVersion": 1,
    "distribution": "attro",
    "version": "0.1.0",
    "core": {
        "package": "@earendil-works/pi-coding-agent",
        "version": "0.85.0",
    },
}


def ls_remote_result(head: str) -> subprocess.CompletedProcess[str]:
    stdout = "\n".join(
        [
            "ref: refs/heads/main\tHEAD",
            f"{head}\trefs/heads/main",
        ]
    )
    return subprocess.CompletedProcess(args=("git",), returncode=0, stdout=stdout, stderr="")


class ValidateGitUrlTests(unittest.TestCase):
    def test_accepts_public_github_https_git_url(self) -> None:
        self.assertIsNone(check_updates.validate_git_url("https://github.com/example/repo.git"))

    def test_rejects_non_https(self) -> None:
        self.assertEqual(
            check_updates.validate_git_url("http://github.com/example/repo.git"),
            "URL must use https",
        )

    def test_rejects_credentials(self) -> None:
        self.assertEqual(
            check_updates.validate_git_url("https://token@github.com/example/repo.git"),
            "URL must not embed credentials",
        )

    def test_rejects_query_fragment_and_port(self) -> None:
        self.assertEqual(
            check_updates.validate_git_url("https://github.com:443/example/repo.git"),
            "URL must not include an explicit port",
        )
        self.assertEqual(
            check_updates.validate_git_url("https://github.com/example/repo.git?go=1"),
            "URL must not include query or fragment",
        )
        self.assertEqual(
            check_updates.validate_git_url("https://github.com/example/repo.git#main"),
            "URL must not include query or fragment",
        )

    def test_rejects_non_owner_repo_path(self) -> None:
        self.assertEqual(
            check_updates.validate_git_url("https://github.com/org/extra/repo.git"),
            "URL path must be /owner/repo.git",
        )


class ValidateGitShaTests(unittest.TestCase):
    def test_rejects_invalid_head(self) -> None:
        parsed = check_updates.parse_ls_remote_symref(
            "ref: refs/heads/main\tHEAD\nZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ\trefs/heads/main\n"
        )
        self.assertIsNotNone(parsed.error)


class DiscoverDescriptorTests(unittest.TestCase):
    def test_missing_descriptor_is_error_not_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "sources.lock.json"
            lock_path.write_text(json.dumps({"schemaVersion": 1, "submodules": []}), encoding="utf-8")
            report = check_updates.build_report(
                lock_path,
                Path(tmp) / "attro.json",
                assess_merges=False,
                git=lambda *a, **k: ls_remote_result(SHA_A),
                fetch_json=lambda url: {"version": "0.85.0"},
            )
        self.assertEqual(report["status"], "error")
        self.assertTrue(any("descriptor missing" in err for err in report["errors"]))

    def test_release_version_is_not_used_as_core_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            descriptor_path = Path(tmp) / "attro.json"
            descriptor_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "distribution": "attro",
                        "version": "0.99.0",
                    }
                ),
                encoding="utf-8",
            )
            descriptor, errors = check_updates.discover_descriptor(
                descriptor_path,
                fetch_json=lambda url: {"version": "1.0.0"},
            )
        self.assertTrue(any("core must be an object" in err for err in errors))
        self.assertIsNone(descriptor["core"])

    def test_core_package_must_be_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            descriptor_path = Path(tmp) / "attro.json"
            bad = dict(VALID_DESCRIPTOR)
            bad["core"] = {"package": "other-package", "version": "1.0.0"}
            descriptor_path.write_text(json.dumps(bad), encoding="utf-8")
            _, errors = check_updates.discover_descriptor(
                descriptor_path,
                fetch_json=lambda url: {"version": "1.0.0"},
            )
        self.assertTrue(any("not supported" in err for err in errors))

    def test_npm_lookup_uses_resolved_core_package(self) -> None:
        seen: list[str] = []

        def fetch(url: str) -> dict[str, str]:
            seen.append(url)
            return {"version": "0.86.0"}

        with tempfile.TemporaryDirectory() as tmp:
            descriptor_path = Path(tmp) / "attro.json"
            descriptor_path.write_text(json.dumps(VALID_DESCRIPTOR), encoding="utf-8")
            descriptor, errors = check_updates.discover_descriptor(descriptor_path, fetch_json=fetch)

        self.assertFalse(errors)
        self.assertTrue(
            seen[0].endswith("%40earendil-works%2Fpi-coding-agent/latest"),
            seen,
        )
        self.assertTrue(descriptor["core"]["updateAvailable"])

    def test_discovers_npm_packages_canonical_records(self) -> None:
        descriptor = dict(VALID_DESCRIPTOR)
        descriptor["npmPackages"] = [
            {"package": "pi-btw", "version": "0.4.1"},
            {"package": "@narumitw/pi-goal", "version": "0.54.4"},
        ]
        fetch_map = {
            check_updates.npm_registry_latest_url("@earendil-works/pi-coding-agent"): {"version": "0.85.0"},
            check_updates.npm_registry_latest_url("pi-btw"): {"version": "0.4.2"},
            check_updates.npm_registry_latest_url("@narumitw/pi-goal"): {"version": "0.54.4"},
        }

        with tempfile.TemporaryDirectory() as tmp:
            descriptor_path = Path(tmp) / "attro.json"
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
            result, errors = check_updates.discover_descriptor(
                descriptor_path,
                fetch_json=lambda url: fetch_map[url],
            )

        self.assertFalse(errors)
        self.assertEqual(len(result["npmPackages"]), 2)
        by_name = {item["package"]: item for item in result["npmPackages"]}
        self.assertTrue(by_name["pi-btw"]["updateAvailable"])
        self.assertFalse(by_name["@narumitw/pi-goal"]["updateAvailable"])

    def test_rejects_legacy_spec_shape(self) -> None:
        descriptor = dict(VALID_DESCRIPTOR)
        descriptor["npmPackages"] = [{"spec": "pi-btw@0.4.1", "placeholder": "{{X}}"}]
        with tempfile.TemporaryDirectory() as tmp:
            descriptor_path = Path(tmp) / "attro.json"
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
            _, errors = check_updates.discover_descriptor(
                descriptor_path,
                fetch_json=lambda url: {"version": "0.85.0"},
            )
        self.assertTrue(any("npmPackages[0].package must be a non-empty string" in err for err in errors))


class DiscoverSubmoduleTests(unittest.TestCase):
    def test_records_upstream_error_instead_of_up_to_date(self) -> None:
        def fake_git(*args: str, cwd: Path | None = None, timeout: int = 120):
            return subprocess.CompletedProcess(args=("git", *args), returncode=128, stdout="", stderr="fatal: repo missing")

        entry = {
            "path": "plugins/demo",
            "name": "demo",
            "pin": SHA_A,
            "baseCommit": SHA_B,
            "origin": "https://github.com/fork/demo.git",
            "upstream": "https://github.com/upstream/demo.git",
        }
        record, errors = check_updates.discover_submodule(entry, assess_merges=False, git=fake_git)
        self.assertTrue(errors)
        self.assertIsNotNone(record["upstream"]["error"])


class MergeAssessmentTests(unittest.TestCase):
    def test_real_merge_without_global_git_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upstream = root / "upstream"
            fork = root / "fork"
            env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

            def run(*args: str, cwd: Path | None = None):
                return subprocess.run(
                    ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True,
                )

            def commit(repo: Path, filename: str) -> str:
                (repo / filename).write_text(filename)
                run("add", filename, cwd=repo)
                run("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "commit", "-m", filename, cwd=repo)
                return run("rev-parse", "HEAD", cwd=repo).stdout.strip()

            run("init", str(upstream))
            commit(upstream, "base.txt")
            run("clone", str(upstream), str(fork))
            pin = commit(fork, "fork.txt")
            head = commit(upstream, "upstream.txt")

            def runner(*args: str, cwd: Path | None = None, timeout: int = 120):
                rewritten = [
                    str(fork) if arg == "https://github.com/fork/demo.git" else
                    str(upstream) if arg == "https://github.com/upstream/demo.git" else arg
                    for arg in args
                ]
                return subprocess.run(
                    ["git", *rewritten], cwd=cwd, env=env, capture_output=True,
                    text=True, check=False, timeout=timeout,
                )

            result = check_updates.assess_fork_merge(
                "https://github.com/fork/demo.git", pin,
                "https://github.com/upstream/demo.git", head, git=runner,
            )
            self.assertEqual(result["status"], "clean", result)
            self.assertEqual(run("rev-parse", "HEAD", cwd=fork).stdout.strip(), pin)

    def test_merge_assessment_clones_origin_and_merges_upstream_head(self) -> None:
        calls: list[list[str]] = []

        def fake_git(*args: str, cwd: Path | None = None, timeout: int = 120):
            calls.append(list(args))
            if args[:2] == ("clone", "--no-checkout"):
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            if args[:3] == ("-c", "core.hooksPath=/dev/null", "fetch") and args[3] == "origin":
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            if args[:4] == ("-c", "core.hooksPath=/dev/null", "checkout", "--detach"):
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            if args[:2] == ("remote", "add"):
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            if args[:3] == ("-c", "core.hooksPath=/dev/null", "fetch") and args[3] == "upstream":
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            if args[:3] == ("-c", "core.hooksPath=/dev/null", "merge"):
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        result = check_updates.assess_fork_merge(
            "https://github.com/fork/demo.git",
            SHA_A,
            "https://github.com/upstream/demo.git",
            SHA_C,
            git=fake_git,
        )
        self.assertEqual(result["status"], "clean")
        self.assertEqual(calls[0][:3], ["clone", "--no-checkout", "https://github.com/fork/demo.git"])
        self.assertFalse(any("--depth=1" in call for call in calls))
        self.assertTrue(any(call[:2] == ["remote", "add"] for call in calls))

    def test_merge_assessment_reports_conflict(self) -> None:
        def fake_git(*args: str, cwd: Path | None = None, timeout: int = 120):
            if args[:2] == ("clone", "--no-checkout"):
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            if "merge" in args and "--abort" not in args:
                return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="CONFLICT")
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        result = check_updates.assess_fork_merge(
            "https://github.com/fork/demo.git",
            SHA_A,
            "https://github.com/upstream/demo.git",
            SHA_C,
            git=fake_git,
        )
        self.assertEqual(result["status"], "conflict")
        self.assertFalse(result["clean"])


class GitRunnerTests(unittest.TestCase):
    def test_oserror_becomes_bounded_report_error(self) -> None:
        with mock.patch.object(check_updates.subprocess, "run", side_effect=OSError("No such file or directory")):
            remote = check_updates.git_ls_remote_head("https://github.com/example/repo.git")
        self.assertIsNotNone(remote.error)
        self.assertIn("git execution failed", remote.error or "")


class BuildReportTests(unittest.TestCase):
    def test_missing_lock_is_error_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            descriptor_path = Path(tmp) / "attro.json"
            descriptor_path.write_text(json.dumps(VALID_DESCRIPTOR), encoding="utf-8")
            report = check_updates.build_report(
                Path(tmp) / "missing.lock.json",
                descriptor_path,
                assess_merges=False,
                git=lambda *a, **k: ls_remote_result(SHA_A),
                fetch_json=lambda url: {"version": "0.85.0"},
            )
        self.assertEqual(report["status"], "error")
        self.assertTrue(report["errors"])

    def test_valid_descriptor_reports_core_update(self) -> None:
        lock = {
            "schemaVersion": 1,
            "branch": "quattro",
            "submodules": [
                {
                    "path": "plugins/demo",
                    "name": "demo",
                    "pin": SHA_A,
                    "baseCommit": SHA_A,
                    "origin": "https://github.com/fork/demo.git",
                    "upstream": "https://github.com/upstream/demo.git",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "sources.lock.json"
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            descriptor_path = Path(tmp) / "attro.json"
            descriptor = dict(VALID_DESCRIPTOR)
            descriptor["core"]["version"] = "0.80.0"
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")

            report = check_updates.build_report(
                lock_path,
                descriptor_path,
                assess_merges=False,
                git=lambda *a, **k: ls_remote_result(SHA_A),
                fetch_json=lambda url: {"version": "0.85.0"},
            )

        self.assertEqual(report["status"], "updates_available")
        self.assertTrue(report["descriptor"]["core"]["updateAvailable"])


class MainIntegrationTests(unittest.TestCase):
    def test_main_fails_when_descriptor_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "sources.lock.json"
            lock_path.write_text(json.dumps({"schemaVersion": 1, "submodules": []}), encoding="utf-8")
            report_path = Path(tmp) / "report.json"
            code = check_updates.main(
                [
                    "--lock",
                    str(lock_path),
                    "--descriptor",
                    str(Path(tmp) / "attro.json"),
                    "--report",
                    str(report_path),
                ]
            )
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "error")


if __name__ == "__main__":
    unittest.main()
