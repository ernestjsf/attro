#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from attro.git_export import export_tracked_tree  # noqa: E402
from attro.validate import ValidationError  # noqa: E402


class GitExportTests(unittest.TestCase):
    def test_exports_only_tracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
            (repo / "ignored.txt").write_text("skip\n", encoding="utf-8")
            (repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
            dst = Path(tmp) / "out"
            export_tracked_tree(repo, dst)
            self.assertTrue((dst / "tracked.txt").is_file())
            self.assertFalse((dst / "ignored.txt").exists())

    def test_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            (repo / "target.txt").write_text("data\n", encoding="utf-8")
            (repo / "link.txt").symlink_to("target.txt")
            subprocess.run(["git", "add", "target.txt", "link.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
            with self.assertRaises(ValidationError):
                export_tracked_tree(repo, Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()
