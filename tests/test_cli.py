"""Tests for CLI argument parsing."""

import unittest
from unittest.mock import patch, MagicMock

from git_bisect_tool.cli import create_parser, main


class TestCreateParser(unittest.TestCase):
    """Tests for argument parser creation."""

    def setUp(self):
        self.parser = create_parser()

    def test_required_args_good_and_test(self):
        """--good and --test are required."""
        args = self.parser.parse_args(["--good", "abc123", "--test", "./test.sh"])
        self.assertEqual(args.good, "abc123")
        self.assertEqual(args.test, "./test.sh")

    def test_short_args(self):
        """Short argument forms work."""
        args = self.parser.parse_args(["-g", "abc123", "-t", "./test.sh"])
        self.assertEqual(args.good, "abc123")
        self.assertEqual(args.test, "./test.sh")

    def test_default_values(self):
        """Default values are set correctly."""
        args = self.parser.parse_args(["--good", "abc", "--test", "./t.sh"])
        self.assertEqual(args.repo, ".")
        self.assertEqual(args.bad, "HEAD")
        self.assertIsNone(args.branch)
        self.assertFalse(args.worktree)
        self.assertFalse(args.show_ancestry)
        self.assertFalse(args.dry_run)
        self.assertFalse(args.verbose)

    def test_all_optional_args(self):
        """All optional arguments can be set."""
        args = self.parser.parse_args(
            [
                "--good",
                "abc123",
                "--test",
                "./test.sh",
                "--repo",
                "/path/to/repo",
                "--branch",
                "main",
                "--bad",
                "def456",
                "--worktree",
                "--show-ancestry",
                "--dry-run",
                "--verbose",
            ]
        )
        self.assertEqual(args.repo, "/path/to/repo")
        self.assertEqual(args.branch, "main")
        self.assertEqual(args.bad, "def456")
        self.assertTrue(args.worktree)
        self.assertTrue(args.show_ancestry)
        self.assertTrue(args.dry_run)
        self.assertTrue(args.verbose)

    def test_missing_good_errors(self):
        """Missing --good causes error."""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["--test", "./test.sh"])

    def test_missing_test_errors(self):
        """Missing --test causes error."""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["--good", "abc123"])


class TestMain(unittest.TestCase):
    """Tests for main entry point."""

    @patch("git_bisect_tool.cli.BisectRunner")
    @patch("git_bisect_tool.cli.Colors")
    def test_main_creates_runner(self, mock_colors, mock_runner_class):
        """main() creates BisectRunner with correct args."""
        mock_runner = MagicMock()
        mock_runner.run.return_value = 0
        mock_runner_class.return_value = mock_runner

        result = main(["--good", "abc", "--test", "./test.sh", "--verbose"])

        self.assertEqual(result, 0)
        mock_runner_class.assert_called_once()
        call_kwargs = mock_runner_class.call_args[1]
        self.assertEqual(call_kwargs["good_commit"], "abc")
        self.assertEqual(call_kwargs["test_script"], "./test.sh")
        self.assertTrue(call_kwargs["verbose"])

    @patch("git_bisect_tool.cli.BisectRunner")
    @patch("git_bisect_tool.cli.Colors")
    def test_main_passes_all_options(self, mock_colors, mock_runner_class):
        """main() passes all CLI options to BisectRunner."""
        mock_runner = MagicMock()
        mock_runner.run.return_value = 0
        mock_runner_class.return_value = mock_runner

        result = main(
            [
                "--good",
                "abc",
                "--test",
                "./test.sh",
                "--repo",
                "/repo",
                "--branch",
                "dev",
                "--bad",
                "def",
                "--worktree",
                "--show-ancestry",
                "--dry-run",
            ]
        )

        self.assertEqual(result, 0)
        call_kwargs = mock_runner_class.call_args[1]
        self.assertEqual(call_kwargs["repo_path"], "/repo")
        self.assertEqual(call_kwargs["branch"], "dev")
        self.assertEqual(call_kwargs["bad_commit"], "def")
        self.assertTrue(call_kwargs["use_worktree"])
        self.assertTrue(call_kwargs["show_ancestry"])
        self.assertTrue(call_kwargs["dry_run"])


if __name__ == "__main__":
    unittest.main()
