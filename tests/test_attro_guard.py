#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from attro.guard import blocked_pi_command  # noqa: E402


class BlockedPiCommandTests(unittest.TestCase):
    def test_blocks_core_mutators(self) -> None:
        self.assertEqual(blocked_pi_command(["update"]), ("update",))
        self.assertEqual(blocked_pi_command(["install", "pkg"]), ("install",))
        self.assertEqual(blocked_pi_command(["remove", "pkg"]), ("remove",))

    def test_allows_only_exact_model_refresh(self) -> None:
        self.assertIsNone(blocked_pi_command(["update", "--models"]))
        for extra in (["--self"], ["--all"], ["--extensions"], ["--extension", "pkg"], ["pkg"], ["--force"]):
            for command in (["update", "--models", *extra], ["update", *extra, "--models"]):
                with self.subTest(command=command):
                    self.assertEqual(blocked_pi_command(command), ("update",))
        self.assertEqual(blocked_pi_command(["package", "update", "--models"]), ("package", "update"))

    def test_blocks_package_subcommands(self) -> None:
        self.assertEqual(blocked_pi_command(["package", "install", "x"]), ("package", "install"))
        self.assertEqual(blocked_pi_command(["package", "remove", "x"]), ("package", "remove"))

    def test_allows_normal_invocation(self) -> None:
        self.assertIsNone(blocked_pi_command([]))
        self.assertIsNone(blocked_pi_command(["--version"]))
        self.assertIsNone(blocked_pi_command(["-p", "hello"]))
        self.assertIsNone(blocked_pi_command(["package", "list"]))


if __name__ == "__main__":
    unittest.main()
