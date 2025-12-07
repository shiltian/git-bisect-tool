"""State management for crash recovery."""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Union


@dataclass
class BisectStep:
    """Record of a single bisect step."""
    commit: str
    result: str  # "good", "bad", "skip", "error"
    exit_code: int
    timestamp: str
    duration_seconds: float


@dataclass
class BisectState:
    """Persistent state for crash recovery.

    This class tracks the state of a bisect operation, allowing it to be
    saved and resumed if interrupted.
    """
    repo_path: str
    branch: str
    good_commit: str
    bad_commit: str
    test_script: str
    worktree_path: Optional[str] = None
    started_at: str = ""
    steps: List[Union[BisectStep, dict]] = field(default_factory=list)
    current_commit: Optional[str] = None
    found_bad_commit: Optional[str] = None
    status: str = "in_progress"  # "in_progress", "completed", "aborted"

    def save(self, path: str):
        """Save state to a JSON file.

        Args:
            path: Path to save the state file.
        """
        # Convert BisectStep objects to dicts for JSON serialization
        data = asdict(self)
        data['steps'] = [
            asdict(s) if isinstance(s, BisectStep) else s
            for s in self.steps
        ]
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'BisectState':
        """Load state from a JSON file.

        Args:
            path: Path to the state file.

        Returns:
            BisectState instance with loaded data.
        """
        with open(path, 'r') as f:
            data = json.load(f)

        state = cls(
            repo_path=data['repo_path'],
            branch=data['branch'],
            good_commit=data['good_commit'],
            bad_commit=data['bad_commit'],
            test_script=data['test_script'],
        )
        state.worktree_path = data.get('worktree_path')
        state.started_at = data.get('started_at', '')
        state.steps = [
            BisectStep(**s) if isinstance(s, dict) else s
            for s in data.get('steps', [])
        ]
        state.current_commit = data.get('current_commit')
        state.found_bad_commit = data.get('found_bad_commit')
        state.status = data.get('status', 'in_progress')
        return state

    def add_step(self, step: BisectStep):
        """Add a step to the history.

        Args:
            step: BisectStep to add.
        """
        self.steps.append(step)

    def get_total_duration(self) -> float:
        """Get the total duration of all steps in seconds."""
        total = 0.0
        for step in self.steps:
            if isinstance(step, BisectStep):
                total += step.duration_seconds
            elif isinstance(step, dict):
                total += step.get('duration_seconds', 0)
        return total

