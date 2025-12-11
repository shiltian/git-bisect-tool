"""Main bisect orchestration class."""

import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from typing import Optional

from .colors import Colors
from .git import Git, GitError
from .logging_setup import setup_logging
from .state import BisectState, BisectStep


class BisectRunner:
    """Main bisect orchestration class.

    This class manages the entire bisect process, including:
    - Configuration validation
    - Worktree setup/teardown
    - Running git bisect with the test script
    - State persistence for crash recovery
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
        state_file: Optional[str] = None,
        show_ancestry: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
        resume_state: Optional[BisectState] = None,
    ):
        """Initialize the bisect runner.

        Args:
            repo_path: Path to the git repository.
            good_commit: Known good commit reference.
            bad_commit: Known bad commit reference.
            test_script: Path to the test script.
            branch: Branch to bisect (default: current branch).
            use_worktree: Whether to use a temporary worktree.
            state_file: Path to save/resume state.
            show_ancestry: Whether to show merge ancestry of found commit.
            dry_run: If True, show config without running.
            verbose: If True, enable verbose logging.
            resume_state: Optional state to resume from.
        """
        self.logger = setup_logging(verbose)
        self.verbose = verbose
        self.resuming = resume_state is not None

        self.repo_path = os.path.abspath(repo_path)
        self.git = Git(self.repo_path, self.logger)

        # Resolve branch
        if branch:
            self.branch = branch
        else:
            self.branch = self.git.get_current_branch()

        # Resolve commits - when resuming, these are already full hashes
        if self.resuming:
            self.good_commit = good_commit
            self.bad_commit = bad_commit
        else:
            self.good_commit = self.git.get_commit_hash(good_commit)
            self.bad_commit = self.git.get_commit_hash(bad_commit)

        self.test_script = os.path.abspath(test_script)
        self.use_worktree = use_worktree
        self.state_file = state_file
        self.show_ancestry = show_ancestry
        self.dry_run = dry_run

        self.worktree_path: Optional[str] = None
        self.temp_dir: Optional[str] = None

        # Use resume state or create new state
        if resume_state:
            self.state = resume_state
            self.state.status = "in_progress"
        else:
            self.state = BisectState(
                repo_path=self.repo_path,
                branch=self.branch,
                good_commit=self.good_commit,
                bad_commit=self.bad_commit,
                test_script=self.test_script,
                started_at=datetime.now().isoformat(),
            )

    def print_banner(self):
        """Print a nice banner."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}║              🔍  Git Bisect Tool  🔍                         ║{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════════════════╝{Colors.RESET}\n", flush=True)

    def print_config(self):
        """Print the configuration."""
        good_info = self.git.get_commit_info(self.good_commit)
        bad_info = self.git.get_commit_info(self.bad_commit)

        if self.resuming:
            print(f"{Colors.BOLD}{Colors.YELLOW}Resuming interrupted bisect...{Colors.RESET}")
            print(f"  Previous steps: {Colors.CYAN}{len(self.state.steps)}{Colors.RESET}")
            print()

        print(f"{Colors.BOLD}Configuration:{Colors.RESET}")
        print(f"  Repository:   {Colors.WHITE}{self.repo_path}{Colors.RESET}")
        print(f"  Branch:       {Colors.MAGENTA}{self.branch}{Colors.RESET}")
        print(f"  Good commit:  {Colors.GREEN}{good_info['short_hash']}{Colors.RESET} - {good_info['subject'][:50]}")
        print(f"  Bad commit:   {Colors.RED}{bad_info['short_hash']}{Colors.RESET} - {bad_info['subject'][:50]}")
        print(f"  Test script:  {Colors.WHITE}{self.test_script}{Colors.RESET}")
        print(f"  Use worktree: {Colors.YELLOW}{'Yes' if self.use_worktree else 'No'}{Colors.RESET}")
        if self.state_file:
            print(f"  State file:   {Colors.WHITE}{self.state_file}{Colors.RESET}")
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
        if not os.path.isdir(self.repo_path):
            self.logger.error(f"Repository not found: {self.repo_path}")
            return False

        if not os.path.isdir(os.path.join(self.repo_path, ".git")):
            self.logger.error(f"Not a git repository: {self.repo_path}")
            return False

        # Check if test script exists and is executable
        if not os.path.isfile(self.test_script):
            self.logger.error(f"Test script not found: {self.test_script}")
            return False

        if not os.access(self.test_script, os.X_OK):
            self.logger.warning(f"Test script is not executable: {self.test_script}")
            self.logger.warning("Attempting to make it executable...")
            os.chmod(self.test_script, 0o755)

        # Check if good is ancestor of bad
        if not self.git.is_ancestor(self.good_commit, self.bad_commit):
            self.logger.error("Good commit is not an ancestor of bad commit!")
            self.logger.error("Make sure good commit comes before bad commit in history.")
            return False

        # Check commit count
        commit_count = self.git.count_commits_between(self.good_commit, self.bad_commit)
        if commit_count == 0:
            self.logger.error("No commits between good and bad commits!")
            return False

        self.logger.info("Validation passed ✓")
        return True

    def setup_worktree(self) -> str:
        """Set up a temporary worktree for isolated testing.

        Returns:
            Path to the created worktree.
        """
        self.temp_dir = tempfile.mkdtemp(prefix="git-bisect-")
        self.worktree_path = os.path.join(self.temp_dir, "worktree")

        self.logger.info(f"Creating worktree at: {self.worktree_path}")
        self.git.create_worktree(self.worktree_path, self.bad_commit)

        self.state.worktree_path = self.worktree_path
        return self.worktree_path

    def cleanup_worktree(self):
        """Clean up the temporary worktree."""
        if self.worktree_path and os.path.exists(self.worktree_path):
            self.logger.info("Cleaning up worktree...")
            self.git.remove_worktree(self.worktree_path)

        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def save_state(self):
        """Save state to file if state_file is configured."""
        if self.state_file:
            self.state.save(self.state_file)
            self.logger.debug(f"State saved to: {self.state_file}")

    def run_test(self, commit: str, work_dir: str) -> int:
        """Run the test script for a specific commit.

        Args:
            commit: Commit hash to test.
            work_dir: Working directory for the test.

        Returns:
            Exit code from the test script.
        """
        self.logger.info(f"Testing commit: {Colors.YELLOW}{commit[:12]}{Colors.RESET}")

        commit_info = self.git.get_commit_info(commit)
        self.logger.debug(f"  Subject: {commit_info['subject']}")
        self.logger.debug(f"  Author: {commit_info['author_name']}")

        # Checkout the commit
        self.git.checkout(commit, cwd=work_dir)

        # Run the test script
        start_time = time.time()
        try:
            result = subprocess.run(
                [self.test_script, commit, work_dir],
                capture_output=not self.verbose,
                text=True,
                cwd=work_dir,
            )
            exit_code = result.returncode
        except Exception as e:
            self.logger.error(f"Error running test script: {e}")
            exit_code = 128

        duration = time.time() - start_time

        # Determine result
        if exit_code == 0:
            result_str = "good"
            color = Colors.GREEN
        elif exit_code == 125:
            result_str = "skip"
            color = Colors.YELLOW
        elif exit_code >= 128:
            result_str = "error"
            color = Colors.RED
        else:
            result_str = "bad"
            color = Colors.RED

        self.logger.info(
            f"  Result: {color}{result_str.upper()}{Colors.RESET} "
            f"(exit code: {exit_code}, duration: {duration:.1f}s)"
        )

        # Record step
        step = BisectStep(
            commit=commit,
            result=result_str,
            exit_code=exit_code,
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration,
        )
        self.state.add_step(step)
        self.save_state()

        return exit_code

    def replay_bisect_trace(self, work_dir: str):
        """Replay recorded bisect steps to restore git's bisect state.

        Args:
            work_dir: Working directory for the bisect.
        """
        if not self.state.steps:
            return

        self.logger.info(f"Replaying {len(self.state.steps)} previous steps...")

        for step in self.state.steps:
            # Handle both BisectStep objects and dicts
            if isinstance(step, BisectStep):
                commit = step.commit
                result = step.result
            else:
                commit = step['commit']
                result = step['result']

            # Only replay good/bad results, skip errors
            if result == "good":
                self.logger.debug(f"  Replaying: {commit[:12]} -> good")
                self.git.bisect_good(commit, cwd=work_dir)
            elif result == "bad":
                self.logger.debug(f"  Replaying: {commit[:12]} -> bad")
                self.git.bisect_bad(commit, cwd=work_dir)
            # Skip 'skip' and 'error' results - they don't help narrow down

        self.logger.info("Replay complete, continuing bisect...")

    def run_bisect(self) -> Optional[str]:
        """Run the bisect process.

        Returns:
            The bad commit hash if found, None otherwise.
        """
        work_dir = self.worktree_path if self.use_worktree else self.repo_path

        # Create wrapper script for git bisect run
        wrapper_script = self._create_wrapper_script(work_dir)

        try:
            # Start bisect
            self.logger.info("Starting git bisect...")
            self.git.bisect_start(self.bad_commit, self.good_commit, cwd=work_dir)

            # Replay previous steps if resuming
            if self.resuming:
                self.replay_bisect_trace(work_dir)

            # Run bisect
            self.logger.info("Running bisect with test script...")
            print()  # Blank line for readability

            result = subprocess.run(
                ["git", "-C", work_dir, "bisect", "run", wrapper_script],
                capture_output=False,
                text=True,
            )

            # Get the result
            bisect_log = subprocess.run(
                ["git", "-C", work_dir, "bisect", "log"],
                capture_output=True,
                text=True,
            )

            # Parse the bad commit from bisect log
            bad_commit = None
            for line in bisect_log.stdout.split('\n'):
                if 'is the first bad commit' in line:
                    match = re.search(r'([a-f0-9]{40})', line)
                    if match:
                        bad_commit = match.group(1)
                        break

            # Alternative: get current HEAD after bisect
            if not bad_commit:
                try:
                    bad_commit = self.git.get_current_bisect_commit(cwd=work_dir)
                except:
                    pass

            return bad_commit

        finally:
            # Clean up wrapper script
            if os.path.exists(wrapper_script):
                os.remove(wrapper_script)

            # Reset bisect
            self.git.bisect_reset(cwd=work_dir)

    def _create_wrapper_script(self, work_dir: str) -> str:
        """Create a wrapper script for git bisect run.

        Args:
            work_dir: Working directory for the bisect.

        Returns:
            Path to the created wrapper script.
        """
        wrapper_content = f'''#!/bin/bash
COMMIT=$(git rev-parse HEAD)
exec "{self.test_script}" "$COMMIT" "{work_dir}"
'''
        wrapper_path = os.path.join(
            self.temp_dir if self.temp_dir else tempfile.gettempdir(),
            "bisect_wrapper.sh"
        )
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)
        return wrapper_path

    def print_result(self, bad_commit: str):
        """Print the final result.

        Args:
            bad_commit: The found bad commit hash.
        """
        print()
        print(f"{Colors.BOLD}{Colors.RED}╔══════════════════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.RED}║                    🐛  BAD COMMIT FOUND  🐛                  ║{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.RED}╚══════════════════════════════════════════════════════════════╝{Colors.RESET}")
        print()

        commit_info = self.git.get_commit_info(bad_commit)

        print(f"{Colors.BOLD}Commit Details:{Colors.RESET}")
        print(f"  Hash:    {Colors.RED}{commit_info['hash']}{Colors.RESET}")
        print(f"  Subject: {commit_info['subject']}")
        print(f"  Author:  {commit_info['author_name']} <{commit_info['author_email']}>")
        print(f"  Date:    {commit_info['author_date']}")
        print()

        # Show ancestry if requested
        if self.show_ancestry:
            self.print_ancestry(bad_commit)

        # Print summary
        print(f"{Colors.BOLD}Bisect Summary:{Colors.RESET}")
        print(f"  Total steps: {len(self.state.steps)}")
        total_duration = self.state.get_total_duration()
        if total_duration > 0:
            print(f"  Total time:  {total_duration:.1f}s")
        print()

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
            print(f"  {Colors.DIM}This commit reached {self.branch} through:{Colors.RESET}")
            for i, item in enumerate(reversed(ancestry[-5:])):  # Show last 5
                prefix = "  └─" if i == len(ancestry) - 1 else "  ├─"
                branch_info = f" (from {item['source_branch']})" if item['source_branch'] else ""
                print(f"  {prefix} {Colors.MAGENTA}{item['merge_commit']}{Colors.RESET}{branch_info}")
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
            print(f"{Colors.YELLOW}Dry run mode - not actually running bisect{Colors.RESET}")
            return 0

        try:
            # Set up worktree if requested
            if self.use_worktree:
                self.setup_worktree()

            # Run bisect
            bad_commit = self.run_bisect()

            if bad_commit:
                self.state.found_bad_commit = bad_commit
                self.state.status = "completed"
                self.save_state()

                self.print_result(bad_commit)
                return 0
            else:
                self.logger.error("Could not determine the bad commit")
                self.state.status = "aborted"
                self.save_state()
                return 1

        except KeyboardInterrupt:
            print()
            self.logger.warning("Bisect interrupted by user")
            self.state.status = "aborted"
            self.save_state()
            if self.state_file:
                self.logger.info(f"State saved to: {self.state_file}")
                self.logger.info(f"Resume with: --resume-from {self.state_file}")
            return 1

        except Exception as e:
            self.logger.error(f"Bisect failed: {e}")
            self.state.status = "aborted"
            self.save_state()
            if self.verbose:
                import traceback
                traceback.print_exc()
            return 1

        finally:
            if self.use_worktree:
                self.cleanup_worktree()
