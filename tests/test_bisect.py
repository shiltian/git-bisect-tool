"""Tests for BisectRunner."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from git_bisect_tool.bisect import BisectRunner
from git_bisect_tool.state import BisectState, BisectStep


class TestBisectRunnerInit(unittest.TestCase):
    """Tests for BisectRunner initialization."""

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_init_resolves_commits(self, mock_logging, mock_git_class):
        """BisectRunner resolves commit refs to full hashes."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git.get_commit_hash.side_effect = ['abc123full', 'def456full']
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, 'test.sh')
            with open(test_script, 'w') as f:
                f.write('#!/bin/bash\nexit 0')

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='abc',
                bad_commit='def',
                test_script=test_script,
            )

        self.assertEqual(runner.good_commit, 'abc123full')
        self.assertEqual(runner.bad_commit, 'def456full')

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_init_with_resume_state(self, mock_logging, mock_git_class):
        """BisectRunner uses resume_state instead of creating new."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git_class.return_value = mock_git

        resume_state = BisectState(
            repo_path='/repo',
            branch='main',
            good_commit='good123',
            bad_commit='bad456',
            test_script='./test.sh',
        )
        resume_state.add_step(BisectStep('c1', 'good', 0, 't', 1.0))

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, 'test.sh')
            with open(test_script, 'w') as f:
                f.write('#!/bin/bash\nexit 0')

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='good123',
                bad_commit='bad456',
                test_script=test_script,
                resume_state=resume_state,
            )

        self.assertTrue(runner.resuming)
        self.assertEqual(len(runner.state.steps), 1)
        self.assertEqual(runner.state.steps[0].commit, 'c1')


class TestBisectRunnerValidate(unittest.TestCase):
    """Tests for validation logic."""

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_validate_missing_repo(self, mock_logging, mock_git_class):
        """Validation fails if repo doesn't exist."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git.get_commit_hash.return_value = 'abc123'
        mock_git_class.return_value = mock_git

        runner = BisectRunner(
            repo_path='/nonexistent/repo',
            good_commit='good',
            bad_commit='bad',
            test_script='./test.sh',
        )

        self.assertFalse(runner.validate())

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_validate_missing_test_script(self, mock_logging, mock_git_class):
        """Validation fails if test script doesn't exist."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git.get_commit_hash.return_value = 'abc123'
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .git directory to make it look like a repo
            os.makedirs(os.path.join(tmpdir, '.git'))

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='good',
                bad_commit='bad',
                test_script='/nonexistent/test.sh',
            )

            self.assertFalse(runner.validate())

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_validate_good_not_ancestor(self, mock_logging, mock_git_class):
        """Validation fails if good is not ancestor of bad."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git.get_commit_hash.return_value = 'abc123'
        mock_git.is_ancestor.return_value = False
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, '.git'))
            test_script = os.path.join(tmpdir, 'test.sh')
            with open(test_script, 'w') as f:
                f.write('#!/bin/bash\nexit 0')
            os.chmod(test_script, 0o755)

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='good',
                bad_commit='bad',
                test_script=test_script,
            )

            self.assertFalse(runner.validate())

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_validate_success(self, mock_logging, mock_git_class):
        """Validation passes with valid config."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git.get_commit_hash.return_value = 'abc123'
        mock_git.is_ancestor.return_value = True
        mock_git.count_commits_between.return_value = 10
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, '.git'))
            test_script = os.path.join(tmpdir, 'test.sh')
            with open(test_script, 'w') as f:
                f.write('#!/bin/bash\nexit 0')
            os.chmod(test_script, 0o755)

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='good',
                bad_commit='bad',
                test_script=test_script,
            )

            self.assertTrue(runner.validate())


class TestBisectRunnerReplay(unittest.TestCase):
    """Tests for replay_bisect_trace."""

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_replay_bisect_trace(self, mock_logging, mock_git_class):
        """replay_bisect_trace calls git bisect good/bad for each step."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git_class.return_value = mock_git

        resume_state = BisectState(
            repo_path='/repo',
            branch='main',
            good_commit='good123',
            bad_commit='bad456',
            test_script='./test.sh',
        )
        resume_state.add_step(BisectStep('c1', 'good', 0, 't', 1.0))
        resume_state.add_step(BisectStep('c2', 'bad', 1, 't', 1.0))
        resume_state.add_step(BisectStep('c3', 'good', 0, 't', 1.0))

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, 'test.sh')
            with open(test_script, 'w') as f:
                f.write('#!/bin/bash\nexit 0')

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='good123',
                bad_commit='bad456',
                test_script=test_script,
                resume_state=resume_state,
            )

            runner.replay_bisect_trace('/work/dir')

        # Verify correct calls
        mock_git.bisect_good.assert_any_call('c1', cwd='/work/dir')
        mock_git.bisect_bad.assert_called_once_with('c2', cwd='/work/dir')
        mock_git.bisect_good.assert_any_call('c3', cwd='/work/dir')
        self.assertEqual(mock_git.bisect_good.call_count, 2)

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_replay_skips_error_steps(self, mock_logging, mock_git_class):
        """replay_bisect_trace skips error steps."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git_class.return_value = mock_git

        resume_state = BisectState(
            repo_path='/repo',
            branch='main',
            good_commit='good123',
            bad_commit='bad456',
            test_script='./test.sh',
        )
        resume_state.add_step(BisectStep('c1', 'good', 0, 't', 1.0))
        resume_state.add_step(BisectStep('c2', 'error', 128, 't', 1.0))  # Should be skipped

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, 'test.sh')
            with open(test_script, 'w') as f:
                f.write('#!/bin/bash\nexit 0')

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='good123',
                bad_commit='bad456',
                test_script=test_script,
                resume_state=resume_state,
            )

            runner.replay_bisect_trace('/work/dir')

        mock_git.bisect_good.assert_called_once_with('c1', cwd='/work/dir')
        mock_git.bisect_bad.assert_not_called()

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_replay_handles_dict_steps(self, mock_logging, mock_git_class):
        """replay_bisect_trace handles dict steps from JSON load."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git_class.return_value = mock_git

        resume_state = BisectState(
            repo_path='/repo',
            branch='main',
            good_commit='good123',
            bad_commit='bad456',
            test_script='./test.sh',
        )
        # Simulate dict steps (as would come from JSON)
        resume_state.steps = [
            {'commit': 'c1', 'result': 'good', 'exit_code': 0, 'timestamp': 't', 'duration_seconds': 1.0},
            {'commit': 'c2', 'result': 'bad', 'exit_code': 1, 'timestamp': 't', 'duration_seconds': 1.0},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, 'test.sh')
            with open(test_script, 'w') as f:
                f.write('#!/bin/bash\nexit 0')

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='good123',
                bad_commit='bad456',
                test_script=test_script,
                resume_state=resume_state,
            )

            runner.replay_bisect_trace('/work/dir')

        mock_git.bisect_good.assert_called_once_with('c1', cwd='/work/dir')
        mock_git.bisect_bad.assert_called_once_with('c2', cwd='/work/dir')


class TestBisectRunnerEstimate(unittest.TestCase):
    """Tests for step estimation."""

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_estimate_steps(self, mock_logging, mock_git_class):
        """estimate_steps returns log2(n) + 1."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git.get_commit_hash.return_value = 'abc'
        mock_git.count_commits_between.return_value = 100
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, 'test.sh')
            with open(test_script, 'w') as f:
                f.write('#!/bin/bash\nexit 0')

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='good',
                bad_commit='bad',
                test_script=test_script,
            )

        # log2(100) ≈ 6.6, so 6 + 1 = 7
        self.assertEqual(runner.estimate_steps(), 7)

    @patch('git_bisect_tool.bisect.Git')
    @patch('git_bisect_tool.bisect.setup_logging')
    def test_estimate_steps_small(self, mock_logging, mock_git_class):
        """estimate_steps returns at least 1."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = 'main'
        mock_git.get_commit_hash.return_value = 'abc'
        mock_git.count_commits_between.return_value = 1
        mock_git_class.return_value = mock_git

        with tempfile.TemporaryDirectory() as tmpdir:
            test_script = os.path.join(tmpdir, 'test.sh')
            with open(test_script, 'w') as f:
                f.write('#!/bin/bash\nexit 0')

            runner = BisectRunner(
                repo_path=tmpdir,
                good_commit='good',
                bad_commit='bad',
                test_script=test_script,
            )

        self.assertEqual(runner.estimate_steps(), 1)


if __name__ == '__main__':
    unittest.main()

