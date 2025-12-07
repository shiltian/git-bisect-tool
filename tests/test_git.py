"""Tests for Git wrapper."""

import subprocess
import unittest
from unittest.mock import patch, MagicMock

from git_bisect_tool.git import Git, GitError


class TestGit(unittest.TestCase):
    """Tests for Git wrapper class."""

    def setUp(self):
        self.git = Git('/path/to/repo')

    @patch('git_bisect_tool.git.subprocess.run')
    def test_run_success(self, mock_run):
        """run() executes git command and returns result."""
        mock_run.return_value = MagicMock(
            stdout='output\n',
            stderr='',
            returncode=0,
        )

        result = self.git.run('status')

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd, ['git', '-C', '/path/to/repo', 'status'])

    @patch('git_bisect_tool.git.subprocess.run')
    def test_run_with_cwd(self, mock_run):
        """run() uses provided cwd instead of repo_path."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)

        self.git.run('status', cwd='/other/path')

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd, ['git', '-C', '/other/path', 'status'])

    @patch('git_bisect_tool.git.subprocess.run')
    def test_run_failure_raises(self, mock_run):
        """run() raises GitError on failure when check=True."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'git', stderr='error message'
        )

        with self.assertRaises(GitError):
            self.git.run('bad-command')

    @patch('git_bisect_tool.git.subprocess.run')
    def test_run_failure_no_raise(self, mock_run):
        """run() does not raise when check=False."""
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='')

        result = self.git.run('command', check=False)

        self.assertEqual(result.returncode, 1)

    @patch('git_bisect_tool.git.subprocess.run')
    def test_get_commit_hash(self, mock_run):
        """get_commit_hash returns full hash."""
        mock_run.return_value = MagicMock(
            stdout='abc123def456\n',
            returncode=0,
        )

        result = self.git.get_commit_hash('HEAD')

        self.assertEqual(result, 'abc123def456')

    @patch('git_bisect_tool.git.subprocess.run')
    def test_get_commit_info(self, mock_run):
        """get_commit_info returns parsed commit details."""
        mock_run.return_value = MagicMock(
            stdout='abc123\nabc\nFix bug\nJohn Doe\njohn@example.com\n2025-01-01 12:00:00\n',
            returncode=0,
        )

        result = self.git.get_commit_info('abc123')

        self.assertEqual(result['hash'], 'abc123')
        self.assertEqual(result['short_hash'], 'abc')
        self.assertEqual(result['subject'], 'Fix bug')
        self.assertEqual(result['author_name'], 'John Doe')
        self.assertEqual(result['author_email'], 'john@example.com')

    @patch('git_bisect_tool.git.subprocess.run')
    def test_count_commits_between(self, mock_run):
        """count_commits_between returns integer count."""
        mock_run.return_value = MagicMock(stdout='42\n', returncode=0)

        result = self.git.count_commits_between('good', 'bad')

        self.assertEqual(result, 42)

    @patch('git_bisect_tool.git.subprocess.run')
    def test_is_ancestor_true(self, mock_run):
        """is_ancestor returns True when ancestor relationship exists."""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.git.is_ancestor('old', 'new')

        self.assertTrue(result)

    @patch('git_bisect_tool.git.subprocess.run')
    def test_is_ancestor_false(self, mock_run):
        """is_ancestor returns False when no ancestor relationship."""
        mock_run.return_value = MagicMock(returncode=1)

        result = self.git.is_ancestor('new', 'old')

        self.assertFalse(result)

    @patch('git_bisect_tool.git.subprocess.run')
    def test_bisect_start(self, mock_run):
        """bisect_start calls git bisect start with bad and good."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)

        self.git.bisect_start('bad123', 'good456')

        cmd = mock_run.call_args[0][0]
        self.assertIn('bisect', cmd)
        self.assertIn('start', cmd)
        self.assertIn('bad123', cmd)
        self.assertIn('good456', cmd)

    @patch('git_bisect_tool.git.subprocess.run')
    def test_bisect_good(self, mock_run):
        """bisect_good marks commit as good."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)

        self.git.bisect_good('abc123')

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd, ['git', '-C', '/path/to/repo', 'bisect', 'good', 'abc123'])

    @patch('git_bisect_tool.git.subprocess.run')
    def test_bisect_bad(self, mock_run):
        """bisect_bad marks commit as bad."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)

        self.git.bisect_bad('def456')

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd, ['git', '-C', '/path/to/repo', 'bisect', 'bad', 'def456'])

    @patch('git_bisect_tool.git.subprocess.run')
    def test_bisect_reset(self, mock_run):
        """bisect_reset calls git bisect reset."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)

        self.git.bisect_reset()

        cmd = mock_run.call_args[0][0]
        self.assertIn('bisect', cmd)
        self.assertIn('reset', cmd)

    @patch('git_bisect_tool.git.subprocess.run')
    def test_create_worktree(self, mock_run):
        """create_worktree calls git worktree add."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)

        result = self.git.create_worktree('/tmp/wt', 'HEAD')

        self.assertEqual(result, '/tmp/wt')
        cmd = mock_run.call_args[0][0]
        self.assertIn('worktree', cmd)
        self.assertIn('add', cmd)

    @patch('git_bisect_tool.git.subprocess.run')
    def test_remove_worktree(self, mock_run):
        """remove_worktree calls git worktree remove."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)

        self.git.remove_worktree('/tmp/wt')

        cmd = mock_run.call_args[0][0]
        self.assertIn('worktree', cmd)
        self.assertIn('remove', cmd)


if __name__ == '__main__':
    unittest.main()

