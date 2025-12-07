"""Tests for state persistence."""

import json
import os
import tempfile
import unittest

from git_bisect_tool.state import BisectState, BisectStep


class TestBisectStep(unittest.TestCase):
    """Tests for BisectStep dataclass."""

    def test_create_step(self):
        """BisectStep can be created with all fields."""
        step = BisectStep(
            commit='abc123',
            result='good',
            exit_code=0,
            timestamp='2025-01-01T00:00:00',
            duration_seconds=1.5,
        )
        self.assertEqual(step.commit, 'abc123')
        self.assertEqual(step.result, 'good')
        self.assertEqual(step.exit_code, 0)
        self.assertEqual(step.timestamp, '2025-01-01T00:00:00')
        self.assertEqual(step.duration_seconds, 1.5)


class TestBisectState(unittest.TestCase):
    """Tests for BisectState persistence."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, 'state.json')

    def tearDown(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        os.rmdir(self.temp_dir)

    def test_create_state(self):
        """BisectState can be created with required fields."""
        state = BisectState(
            repo_path='/path/to/repo',
            branch='main',
            good_commit='abc123',
            bad_commit='def456',
            test_script='./test.sh',
        )
        self.assertEqual(state.repo_path, '/path/to/repo')
        self.assertEqual(state.branch, 'main')
        self.assertEqual(state.status, 'in_progress')
        self.assertEqual(state.steps, [])

    def test_save_and_load(self):
        """State can be saved and loaded."""
        state = BisectState(
            repo_path='/path/to/repo',
            branch='main',
            good_commit='abc123',
            bad_commit='def456',
            test_script='./test.sh',
            started_at='2025-01-01T00:00:00',
        )
        state.add_step(BisectStep(
            commit='commit1',
            result='good',
            exit_code=0,
            timestamp='2025-01-01T00:01:00',
            duration_seconds=10.0,
        ))
        state.add_step(BisectStep(
            commit='commit2',
            result='bad',
            exit_code=1,
            timestamp='2025-01-01T00:02:00',
            duration_seconds=15.0,
        ))
        state.found_bad_commit = 'commit2'
        state.status = 'completed'

        state.save(self.state_file)

        # Verify file exists and is valid JSON
        self.assertTrue(os.path.exists(self.state_file))
        with open(self.state_file) as f:
            data = json.load(f)
        self.assertEqual(data['repo_path'], '/path/to/repo')
        self.assertEqual(len(data['steps']), 2)

        # Load and verify
        loaded = BisectState.load(self.state_file)
        self.assertEqual(loaded.repo_path, '/path/to/repo')
        self.assertEqual(loaded.branch, 'main')
        self.assertEqual(loaded.good_commit, 'abc123')
        self.assertEqual(loaded.bad_commit, 'def456')
        self.assertEqual(loaded.test_script, './test.sh')
        self.assertEqual(loaded.found_bad_commit, 'commit2')
        self.assertEqual(loaded.status, 'completed')
        self.assertEqual(len(loaded.steps), 2)
        self.assertEqual(loaded.steps[0].commit, 'commit1')
        self.assertEqual(loaded.steps[0].result, 'good')
        self.assertEqual(loaded.steps[1].commit, 'commit2')
        self.assertEqual(loaded.steps[1].result, 'bad')

    def test_get_total_duration(self):
        """get_total_duration sums all step durations."""
        state = BisectState(
            repo_path='/repo',
            branch='main',
            good_commit='a',
            bad_commit='b',
            test_script='./t.sh',
        )
        state.add_step(BisectStep('c1', 'good', 0, 't1', 10.0))
        state.add_step(BisectStep('c2', 'bad', 1, 't2', 20.0))
        state.add_step(BisectStep('c3', 'good', 0, 't3', 15.5))

        self.assertEqual(state.get_total_duration(), 45.5)

    def test_get_total_duration_with_dicts(self):
        """get_total_duration works with dict steps (from JSON load)."""
        state = BisectState(
            repo_path='/repo',
            branch='main',
            good_commit='a',
            bad_commit='b',
            test_script='./t.sh',
        )
        # Simulate dict steps (before they're converted to BisectStep)
        state.steps = [
            {'commit': 'c1', 'result': 'good', 'exit_code': 0, 'timestamp': 't1', 'duration_seconds': 10.0},
            {'commit': 'c2', 'result': 'bad', 'exit_code': 1, 'timestamp': 't2', 'duration_seconds': 20.0},
        ]

        self.assertEqual(state.get_total_duration(), 30.0)

    def test_worktree_path_saved(self):
        """Worktree path is saved and loaded."""
        state = BisectState(
            repo_path='/repo',
            branch='main',
            good_commit='a',
            bad_commit='b',
            test_script='./t.sh',
        )
        state.worktree_path = '/tmp/worktree'
        state.save(self.state_file)

        loaded = BisectState.load(self.state_file)
        self.assertEqual(loaded.worktree_path, '/tmp/worktree')


if __name__ == '__main__':
    unittest.main()

