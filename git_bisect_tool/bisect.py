"""Main bisect orchestration class."""

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from .colors import Colors
from .git import Git
from .logging_setup import setup_logging


class BisectRunner:
    """Main bisect orchestration class.

    This class manages the entire bisect process, including:
    - Configuration validation
    - Worktree setup/teardown
    - Running git bisect with the test script
    - Result reporting
    """

    def __init__(
        self,
        repo_path: str,
        good_commit: str,
        bad_commit: str,
        test_script: str,
        branch: Optional[str] = None,
        use_worktree: bool = False,
        show_ancestry: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        """Initialize the bisect runner.

        Args:
            repo_path: Path to the git repository.
            good_commit: Known good commit reference.
            bad_commit: Known bad commit reference.
            test_script: Path to the test script.
            branch: Branch to bisect (default: current branch).
            use_worktree: Whether to use a temporary worktree.
            show_ancestry: Whether to show merge ancestry of found commit.
            dry_run: If True, show config without running.
            verbose: If True, enable verbose logging.
        """
        self.logger = setup_logging(verbose)
        self.verbose = verbose

        self.repo_path = Path(repo_path).resolve()
        self.git = Git(str(self.repo_path), self.logger)

        # Resolve branch
        self.branch = branch if branch else self.git.get_current_branch()

        # Resolve commits to full hashes
        self.good_commit = self.git.get_commit_hash(good_commit)
        self.bad_commit = self.git.get_commit_hash(bad_commit)

        self.test_script = Path(test_script).resolve()
        self.use_worktree = use_worktree
        self.show_ancestry = show_ancestry
        self.dry_run = dry_run

        self.worktree_path: Optional[Path] = None
        self.temp_dir: Optional[Path] = None

    def print_banner(self):
        """Print a nice banner."""
        print(
            f"\n{Colors.BOLD}{Colors.CYAN}"
            f"{'=' * 62}\n"
            f"  Git Bisect Tool\n"
            f"{'=' * 62}"
            f"{Colors.RESET}\n",
            flush=True,
        )

    def print_config(self):
        """Print the configuration."""
        good_info = self.git.get_commit_info(self.good_commit)
        bad_info = self.git.get_commit_info(self.bad_commit)

        print(f"{Colors.BOLD}Configuration:{Colors.RESET}")
        print(f"  Repository:   {Colors.WHITE}{self.repo_path}{Colors.RESET}")
        print(f"  Branch:       {Colors.MAGENTA}{self.branch}{Colors.RESET}")
        print(
            f"  Good commit:  {Colors.GREEN}{good_info['short_hash']}{Colors.RESET}"
            f" - {good_info['subject'][:50]}"
        )
        print(
            f"  Bad commit:   {Colors.RED}{bad_info['short_hash']}{Colors.RESET}"
            f" - {bad_info['subject'][:50]}"
        )
        print(f"  Test script:  {Colors.WHITE}{self.test_script}{Colors.RESET}")
        print(
            f"  Use worktree: "
            f"{Colors.YELLOW}{'Yes' if self.use_worktree else 'No'}{Colors.RESET}"
        )
        print(flush=True)

    def print_estimate(self):
        """Print git bisect's own estimated number of steps."""
        steps = self.git.bisect_estimate(self.bad_commit, self.good_commit)

        print(f"{Colors.BOLD}Bisect Estimate:{Colors.RESET}")
        if steps is not None:
            print(f"  From git bisect: {Colors.CYAN}~{steps}{Colors.RESET}")
        else:
            print(f"  From git bisect: {Colors.CYAN}unknown{Colors.RESET}")
        print(flush=True)

    def validate(self) -> bool:
        """Validate the configuration before starting.

        Returns:
            True if validation passes, False otherwise.
        """
        self.logger.info("Validating configuration...")

        # Check if repo exists
        if not self.repo_path.is_dir():
            self.logger.error("Repository not found: %s", self.repo_path)
            return False

        if not (self.repo_path / ".git").is_dir():
            self.logger.error("Not a git repository: %s", self.repo_path)
            return False

        # Check if test script exists and is executable
        if not self.test_script.is_file():
            self.logger.error("Test script not found: %s", self.test_script)
            return False

        if not os.access(self.test_script, os.X_OK):
            self.logger.warning("Test script is not executable: %s", self.test_script)
            self.logger.warning("Attempting to make it executable...")
            self.test_script.chmod(0o755)

        # Check if good is ancestor of bad
        if not self.git.is_ancestor(self.good_commit, self.bad_commit):
            self.logger.error("Good commit is not an ancestor of bad commit!")
            self.logger.error(
                "Make sure good commit comes before bad commit in history."
            )
            return False

        # Check commit count
        commit_count = self.git.count_commits_between(self.good_commit, self.bad_commit)
        if commit_count == 0:
            self.logger.error("No commits between good and bad commits!")
            return False

        self.logger.info("Validation passed")
        return True

    def setup_worktree(self) -> Path:
        """Set up a temporary worktree for isolated testing.

        Returns:
            Path to the created worktree.
        """
        self.temp_dir = Path(tempfile.mkdtemp(prefix="git-bisect-"))
        self.worktree_path = self.temp_dir / "worktree"

        self.logger.info("Creating worktree at: %s", self.worktree_path)
        self.git.create_worktree(str(self.worktree_path), self.bad_commit)

        return self.worktree_path

    def cleanup_worktree(self):
        """Clean up the temporary worktree."""
        if self.worktree_path and self.worktree_path.exists():
            self.logger.info("Cleaning up worktree...")
            self.git.remove_worktree(str(self.worktree_path))

        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_bisect(self) -> Optional[str]:
        """Run the bisect process.

        Returns:
            The bad commit hash if found, None otherwise.
        """
        work_dir = str(self.worktree_path) if self.use_worktree else str(self.repo_path)

        # Create wrapper script for git bisect run
        wrapper_script = self._create_wrapper_script()

        try:
            # Start bisect
            self.logger.info("Starting git bisect...")
            self.git.bisect_start(self.bad_commit, self.good_commit, cwd=work_dir)

            # Run bisect
            self.logger.info("Running bisect with test script...")
            print()  # Blank line for readability

            self.git.run(
                "bisect",
                "run",
                wrapper_script,
                cwd=work_dir,
                capture_output=False,
                check=False,
            )

            # Get the result from bisect log
            log_result = self.git.run("bisect", "log", cwd=work_dir, check=False)

            # Parse the bad commit from bisect log
            bad_commit = None
            for line in (log_result.stdout or "").split("\n"):
                if "is the first bad commit" in line:
                    match = re.search(r"([a-f0-9]{40})", line)
                    if match:
                        bad_commit = match.group(1)
                        break

            return bad_commit

        finally:
            # Clean up wrapper script
            wrapper = Path(wrapper_script)
            if wrapper.exists():
                wrapper.unlink()

            # Reset bisect
            self.git.bisect_reset(cwd=work_dir)

    def _create_wrapper_script(self) -> str:
        """Create a wrapper script for git bisect run.

        Returns:
            Path to the created wrapper script.
        """
        wrapper_content = (
            "#!/bin/bash\n"
            "COMMIT=$(git rev-parse HEAD)\n"
            f'exec "{self.test_script}" "$COMMIT" "$(pwd)"\n'
        )
        parent = self.temp_dir if self.temp_dir else Path(tempfile.gettempdir())
        wrapper_path = parent / "bisect_wrapper.sh"
        wrapper_path.write_text(wrapper_content)
        wrapper_path.chmod(0o755)
        return str(wrapper_path)

    def print_result(self, bad_commit: str):
        """Print the final result.

        Args:
            bad_commit: The found bad commit hash.
        """
        print()
        print(
            f"{Colors.BOLD}{Colors.RED}"
            f"{'=' * 62}\n"
            f"  BAD COMMIT FOUND\n"
            f"{'=' * 62}"
            f"{Colors.RESET}"
        )
        print()

        commit_info = self.git.get_commit_info(bad_commit)

        print(f"{Colors.BOLD}Commit Details:{Colors.RESET}")
        print(f"  Hash:    {Colors.RED}{commit_info['hash']}{Colors.RESET}")
        print(f"  Subject: {commit_info['subject']}")
        print(
            f"  Author:  {commit_info['author_name']}"
            f" <{commit_info['author_email']}>"
        )
        print(f"  Date:    {commit_info['author_date']}")
        print()

        # Show ancestry if requested
        if self.show_ancestry:
            self.print_ancestry(bad_commit)

    def print_ancestry(self, commit: str):
        """Print the merge ancestry of a commit.

        Args:
            commit: The commit to show ancestry for.
        """
        print(f"{Colors.BOLD}Merge Ancestry:{Colors.RESET}")

        ancestry = self.git.get_merge_ancestry(commit, self.branch)

        if not ancestry:
            print(f"  {Colors.DIM}(direct commit to {self.branch}){Colors.RESET}")
        else:
            print(
                f"  {Colors.DIM}This commit reached {self.branch} through:"
                f"{Colors.RESET}"
            )
            items = list(reversed(ancestry[-5:]))  # Show last 5
            for i, item in enumerate(items):
                prefix = "  \u2514\u2500" if i == len(items) - 1 else "  \u251c\u2500"
                branch_info = (
                    f" (from {item['source_branch']})" if item["source_branch"] else ""
                )
                print(
                    f"  {prefix} {Colors.MAGENTA}{item['merge_commit']}"
                    f"{Colors.RESET}{branch_info}"
                )
                print(f"       {Colors.DIM}{item['message'][:60]}{Colors.RESET}")
        print()

    def run(self) -> int:
        """Main entry point.

        Returns:
            Exit code: 0 for success, 1 for failure, 2 for invalid args.
        """
        self.print_banner()
        self.print_config()
        self.print_estimate()

        if not self.validate():
            return 2

        if self.dry_run:
            print(
                f"{Colors.YELLOW}Dry run mode"
                f" - not actually running bisect{Colors.RESET}"
            )
            return 0

        try:
            # Set up worktree if requested
            if self.use_worktree:
                self.setup_worktree()

            # Run bisect
            bad_commit = self.run_bisect()

            if bad_commit:
                self.print_result(bad_commit)
                return 0
            else:
                self.logger.error("Could not determine the bad commit")
                return 1

        except KeyboardInterrupt:
            print()
            self.logger.warning("Bisect interrupted by user")
            return 1

        except Exception as e:
            self.logger.error("Bisect failed: %s", e)
            if self.verbose:
                import traceback

                traceback.print_exc()
            return 1

        finally:
            if self.use_worktree:
                self.cleanup_worktree()
