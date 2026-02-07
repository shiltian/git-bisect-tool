"""Tests for BisectRunner."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from git_bisect_tool.bisect import BisectRunner


class TestBisectRunnerInit(unittest.TestCase):
    """Tests for BisectRunner initialization."""

    @patch("git_bisect_tool.bisect.Git")
    @patch("git_bisect_tool.bisect.setup_logging")
    def test_init_resolves_commits(self, mock_logging, mock_git_class):
        """BisectRunner resolves commit refs to full hashes."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "main"
        mock_git.get_commit_hash.side_effect = ["abc123full", "def456full"]
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, "test.sh")
            with open(test_script, "w") as f:
                f.write("#!/bin/bash\nexit 0")

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit="abc",
                bad_commit="def",
                test_script=test_script,
            )

        self.assertEqual(runner.good_commit, "abc123full")
        self.assertEqual(runner.bad_commit, "def456full")

    @patch("git_bisect_tool.bisect.Git")
    @patch("git_bisect_tool.bisect.setup_logging")
    def test_init_uses_provided_branch(self, mock_logging, mock_git_class):
        """BisectRunner uses explicit branch when provided."""
        mock_git = MagicMock()
        mock_git.get_commit_hash.return_value = "abc123"
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, "test.sh")
            with open(test_script, "w") as f:
                f.write("#!/bin/bash\nexit 0")

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit="good",
                bad_commit="bad",
                test_script=test_script,
                branch="develop",
            )

        self.assertEqual(runner.branch, "develop")
        mock_git.get_current_branch.assert_not_called()

    @patch("git_bisect_tool.bisect.Git")
    @patch("git_bisect_tool.bisect.setup_logging")
    def test_init_detects_branch(self, mock_logging, mock_git_class):
        """BisectRunner detects current branch when none provided."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "main"
        mock_git.get_commit_hash.return_value = "abc123"
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, "test.sh")
            with open(test_script, "w") as f:
                f.write("#!/bin/bash\nexit 0")

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit="good",
                bad_commit="bad",
                test_script=test_script,
            )

        self.assertEqual(runner.branch, "main")


class TestBisectRunnerValidate(unittest.TestCase):
    """Tests for validation logic."""

    @patch("git_bisect_tool.bisect.Git")
    @patch("git_bisect_tool.bisect.setup_logging")
    def test_validate_missing_repo(self, mock_logging, mock_git_class):
        """Validation fails if repo doesn't exist."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "main"
        mock_git.get_commit_hash.return_value = "abc123"
        mock_git_class.return_value = mock_git

        runner = BisectRunner(
            repo_path="/nonexistent/repo",
            good_commit="good",
            bad_commit="bad",
            test_script="./test.sh",
        )

        self.assertFalse(runner.validate())

    @patch("git_bisect_tool.bisect.Git")
    @patch("git_bisect_tool.bisect.setup_logging")
    def test_validate_missing_test_script(self, mock_logging, mock_git_class):
        """Validation fails if test script doesn't exist."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "main"
        mock_git.get_commit_hash.return_value = "abc123"
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .git directory to make it look like a repo
            os.makedirs(os.path.join(tmpdir, ".git"))

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit="good",
                bad_commit="bad",
                test_script="/nonexistent/test.sh",
            )

            self.assertFalse(runner.validate())

    @patch("git_bisect_tool.bisect.Git")
    @patch("git_bisect_tool.bisect.setup_logging")
    def test_validate_good_not_ancestor(self, mock_logging, mock_git_class):
        """Validation fails if good is not ancestor of bad."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "main"
        mock_git.get_commit_hash.return_value = "abc123"
        mock_git.is_ancestor.return_value = False
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"))
            test_script = os.path.join(tmpdir, "test.sh")
            with open(test_script, "w") as f:
                f.write("#!/bin/bash\nexit 0")
            os.chmod(test_script, 0o755)

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit="good",
                bad_commit="bad",
                test_script=test_script,
            )

            self.assertFalse(runner.validate())

    @patch("git_bisect_tool.bisect.Git")
    @patch("git_bisect_tool.bisect.setup_logging")
    def test_validate_no_commits_between(self, mock_logging, mock_git_class):
        """Validation fails if no commits between good and bad."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "main"
        mock_git.get_commit_hash.return_value = "abc123"
        mock_git.is_ancestor.return_value = True
        mock_git.count_commits_between.return_value = 0
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"))
            test_script = os.path.join(tmpdir, "test.sh")
            with open(test_script, "w") as f:
                f.write("#!/bin/bash\nexit 0")
            os.chmod(test_script, 0o755)

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit="good",
                bad_commit="bad",
                test_script=test_script,
            )

            self.assertFalse(runner.validate())

    @patch("git_bisect_tool.bisect.Git")
    @patch("git_bisect_tool.bisect.setup_logging")
    def test_validate_success(self, mock_logging, mock_git_class):
        """Validation passes with valid config."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "main"
        mock_git.get_commit_hash.return_value = "abc123"
        mock_git.is_ancestor.return_value = True
        mock_git.count_commits_between.return_value = 10
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"))
            test_script = os.path.join(tmpdir, "test.sh")
            with open(test_script, "w") as f:
                f.write("#!/bin/bash\nexit 0")
            os.chmod(test_script, 0o755)

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit="good",
                bad_commit="bad",
                test_script=test_script,
            )

            self.assertTrue(runner.validate())


if __name__ == "__main__":
    unittest.main()
