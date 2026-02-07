"""Git command wrapper with logging."""

import logging
import re
import subprocess
from typing import Optional, TypedDict


class GitError(Exception):
    """Exception for git command failures."""

    pass


class CommitInfo(TypedDict):
    """Typed dictionary for commit information."""

    hash: str
    short_hash: str
    subject: str
    author_name: str
    author_email: str
    author_date: str


class MergeAncestryEntry(TypedDict):
    """Typed dictionary for merge ancestry entries."""

    merge_commit: str
    message: str
    source_branch: Optional[str]


class Git:
    """Git command wrapper with logging."""

    def __init__(self, repo_path: str, logger: Optional[logging.Logger] = None):
        """Initialize Git wrapper.

        Args:
            repo_path: Path to the git repository.
            logger: Optional logger instance. If not provided, uses module logger.
        """
        self.repo_path = repo_path
        self.logger = logger or logging.getLogger("git-bisect-tool")

    def run(
        self,
        *args: str,
        capture_output: bool = True,
        check: bool = True,
        cwd: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """Run a git command.

        Args:
            *args: Git command arguments.
            capture_output: Whether to capture stdout/stderr.
            check: Whether to raise exception on non-zero exit.
            cwd: Working directory (defaults to repo_path).

        Returns:
            CompletedProcess instance with command results.

        Raises:
            GitError: If command fails and check=True.
        """
        cmd = ["git", "-C", cwd or self.repo_path, *args]
        self.logger.debug("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd, capture_output=capture_output, text=True, check=check
            )
            if result.stdout:
                self.logger.debug("stdout: %s", result.stdout.strip())
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error("Git command failed: %s", e.stderr)
            raise GitError(f"Git command failed: {' '.join(cmd)}\n{e.stderr}") from e

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self.run("rev-parse", "--abbrev-ref", "HEAD")
        return result.stdout.strip()

    def get_commit_hash(self, ref: str) -> str:
        """Get the full commit hash for a ref."""
        result = self.run("rev-parse", ref)
        return result.stdout.strip()

    def get_commit_info(self, ref: str) -> CommitInfo:
        """Get detailed commit information.

        Returns:
            CommitInfo with hash, short_hash, subject, author_name,
            author_email, author_date.
        """
        result = self.run("log", "-1", "--format=%H%n%h%n%s%n%an%n%ae%n%ai", ref)
        lines = result.stdout.strip().split("\n")
        return CommitInfo(
            hash=lines[0],
            short_hash=lines[1],
            subject=lines[2],
            author_name=lines[3],
            author_email=lines[4],
            author_date=lines[5],
        )

    def count_commits_between(self, good: str, bad: str) -> int:
        """Count the number of commits between good and bad."""
        result = self.run("rev-list", "--count", f"{good}..{bad}")
        return int(result.stdout.strip())

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        """Check if one commit is an ancestor of another."""
        result = self.run(
            "merge-base", "--is-ancestor", ancestor, descendant, check=False
        )
        return result.returncode == 0

    def get_merge_ancestry(
        self, commit: str, target_branch: str
    ) -> list[MergeAncestryEntry]:
        """Get the merge ancestry path of a commit.

        Returns a list showing how the commit was merged into the target branch.
        """
        ancestry: list[MergeAncestryEntry] = []

        result = self.run(
            "log",
            "--ancestry-path",
            "--merges",
            "--format=%H %s",
            f"{commit}..{target_branch}",
        )

        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split(" ", 1)
                merge_hash = parts[0]
                merge_subject = parts[1] if len(parts) > 1 else ""

                # Try to extract branch name from merge commit message
                branch_match = re.search(
                    r"Merge (?:branch |pull request .* from )['\"]?([^'\"\s]+)",
                    merge_subject,
                )
                branch_name = branch_match.group(1) if branch_match else None

                ancestry.append(
                    MergeAncestryEntry(
                        merge_commit=merge_hash[:12],
                        message=merge_subject,
                        source_branch=branch_name,
                    )
                )

        return ancestry

    def create_worktree(self, path: str, ref: str) -> str:
        """Create a git worktree at the specified path."""
        self.run("worktree", "add", "--detach", path, ref)
        return path

    def remove_worktree(self, path: str):
        """Remove a git worktree."""
        self.run("worktree", "remove", "--force", path, check=False)

    def bisect_start(self, bad: str, good: str, cwd: Optional[str] = None):
        """Start a git bisect session."""
        self.run("bisect", "start", bad, good, cwd=cwd)

    def bisect_reset(self, cwd: Optional[str] = None):
        """Reset a git bisect session."""
        self.run("bisect", "reset", cwd=cwd, check=False)

    def bisect_estimate(self, bad: str, good: str) -> Optional[int]:
        """Return git bisect's step estimate without moving HEAD."""
        start = self.run(
            "bisect",
            "start",
            "--no-checkout",
            bad,
            good,
            capture_output=True,
            check=False,
        )
        try:
            output = (start.stdout or "") + (start.stderr or "")
            match = re.search(r"roughly (\d+) steps?", output)
            return int(match.group(1)) if match else None
        finally:
            self.run("bisect", "reset", check=False)
