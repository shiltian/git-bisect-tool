"""Tests for CLI argument parsing."""

import unittest
from unittest.mock import patch, MagicMock

from git_bisect_tool.cli import create_parser, main


class TestCreateParser(unittest.TestCase):
    """Tests for argument parser creation."""

    def setUp(self):
        self.parser = create_parser()

    def test_required_args_good_and_test(self):
        """--good and --test are required for fresh start."""
        # Should work with both
        args = self.parser.parse_args(['--good', 'abc123', '--test', './test.sh'])
        self.assertEqual(args.good, 'abc123')
        self.assertEqual(args.test, './test.sh')

    def test_short_args(self):
        """Short argument forms work."""
        args = self.parser.parse_args(['-g', 'abc123', '-t', './test.sh'])
        self.assertEqual(args.good, 'abc123')
        self.assertEqual(args.test, './test.sh')

    def test_default_values(self):
        """Default values are set correctly."""
        args = self.parser.parse_args(['--good', 'abc', '--test', './t.sh'])
        self.assertEqual(args.repo, '.')
        self.assertEqual(args.bad, 'HEAD')
        self.assertIsNone(args.branch)
        self.assertFalse(args.worktree)
        self.assertIsNone(args.state_file)
        self.assertFalse(args.show_ancestry)
        self.assertFalse(args.dry_run)
        self.assertFalse(args.verbose)

    def test_all_optional_args(self):
        """All optional arguments can be set."""
        args = self.parser.parse_args([
            '--good', 'abc123',
            '--test', './test.sh',
            '--repo', '/path/to/repo',
            '--branch', 'main',
            '--bad', 'def456',
            '--worktree',
            '--state-file', 'state.json',
            '--show-ancestry',
            '--dry-run',
            '--verbose',
        ])
        self.assertEqual(args.repo, '/path/to/repo')
        self.assertEqual(args.branch, 'main')
        self.assertEqual(args.bad, 'def456')
        self.assertTrue(args.worktree)
        self.assertEqual(args.state_file, 'state.json')
        self.assertTrue(args.show_ancestry)
        self.assertTrue(args.dry_run)
        self.assertTrue(args.verbose)

    def test_resume_from_arg(self):
        """--resume-from argument works."""
        args = self.parser.parse_args(['--resume-from', 'state.json'])
        self.assertEqual(args.resume_from, 'state.json')
        # good and test are not required when resuming
        self.assertIsNone(args.good)
        self.assertIsNone(args.test)


class TestMain(unittest.TestCase):
    """Tests for main entry point."""

    @patch('git_bisect_tool.cli.BisectRunner')
    def test_main_creates_runner(self, mock_runner_class):
        """main() creates BisectRunner with correct args."""
        mock_runner = MagicMock()
        mock_runner.run.return_value = 0
        mock_runner_class.return_value = mock_runner

        with patch('git_bisect_tool.cli.os.path.isfile', return_value=True):
            result = main(['--good', 'abc', '--test', './test.sh', '--verbose'])

        self.assertEqual(result, 0)
        mock_runner_class.assert_called_once()
        call_kwargs = mock_runner_class.call_args[1]
        self.assertEqual(call_kwargs['good_commit'], 'abc')
        self.assertEqual(call_kwargs['test_script'], './test.sh')
        self.assertTrue(call_kwargs['verbose'])

    @patch('git_bisect_tool.cli.BisectState')
    @patch('git_bisect_tool.cli.BisectRunner')
    @patch('git_bisect_tool.cli.os.path.isfile', return_value=True)
    def test_main_resume_from(self, mock_isfile, mock_runner_class, mock_state_class):
        """main() with --resume-from loads state and creates runner."""
        mock_state = MagicMock()
        mock_state.repo_path = '/repo'
        mock_state.good_commit = 'good123'
        mock_state.bad_commit = 'bad456'
        mock_state.test_script = './test.sh'
        mock_state.branch = 'main'
        mock_state.worktree_path = None
        mock_state_class.load.return_value = mock_state

        mock_runner = MagicMock()
        mock_runner.run.return_value = 0
        mock_runner_class.return_value = mock_runner

        result = main(['--resume-from', 'state.json'])

        self.assertEqual(result, 0)
        mock_state_class.load.assert_called_once_with('state.json')
        call_kwargs = mock_runner_class.call_args[1]
        self.assertEqual(call_kwargs['repo_path'], '/repo')
        self.assertEqual(call_kwargs['good_commit'], 'good123')
        self.assertEqual(call_kwargs['resume_state'], mock_state)


if __name__ == '__main__':
    unittest.main()

