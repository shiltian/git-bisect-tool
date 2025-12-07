"""Command line interface for git bisect tool."""

import argparse
import sys

from . import __version__
from .bisect import BisectRunner
from .templates import generate_template, list_templates


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="git-bisect-tool",
        description="Git Bisect Tool - Find faulty commits with enhanced logging and UX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  git-bisect-tool --good abc123 --test ./test.sh

  # With worktree isolation and state saving
  git-bisect-tool --good v1.0.0 --bad HEAD --test ./test.sh --worktree --state-file bisect.json

  # Generate a test script template
  git-bisect-tool --generate-template ./my_test.sh

  # Generate LLVM-specific template
  git-bisect-tool --generate-template ./my_test.sh --template-type llvm

  # Show what would happen without running
  git-bisect-tool --good abc123 --test ./test.sh --dry-run

Exit Codes:
  0 - Bad commit found successfully
  1 - Bisect failed or inconclusive
  2 - Invalid arguments
        """
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    # Required arguments (unless generating template)
    parser.add_argument(
        "--good", "-g",
        metavar="COMMIT",
        help="Known good commit (required unless --generate-template)"
    )
    parser.add_argument(
        "--test", "-t",
        metavar="SCRIPT",
        help="Path to test script (required unless --generate-template)"
    )

    # Optional arguments
    parser.add_argument(
        "--repo", "-r",
        metavar="PATH",
        default=".",
        help="Path to git repository (default: current directory)"
    )
    parser.add_argument(
        "--branch", "-b",
        metavar="BRANCH",
        help="Branch to bisect (default: current branch)"
    )
    parser.add_argument(
        "--bad",
        metavar="COMMIT",
        default="HEAD",
        help="Known bad commit (default: HEAD)"
    )
    parser.add_argument(
        "--worktree", "-w",
        action="store_true",
        help="Use a temporary worktree for isolation"
    )
    parser.add_argument(
        "--state-file", "-s",
        metavar="FILE",
        help="Save/resume state from this file"
    )
    parser.add_argument(
        "--show-ancestry", "-a",
        action="store_true",
        help="Show merge ancestry of the found commit"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show configuration and estimates without running"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    # Template generation
    parser.add_argument(
        "--generate-template",
        metavar="PATH",
        help="Generate a test script template at the specified path"
    )
    parser.add_argument(
        "--template-type",
        choices=list_templates(),
        default="generic",
        help="Type of template to generate (default: generic)"
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List available template types"
    )

    return parser


def main(argv=None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command line arguments (default: sys.argv[1:]).

    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Handle list templates
    if args.list_templates:
        print("Available templates:")
        for name in list_templates():
            print(f"  - {name}")
        return 0

    # Handle template generation
    if args.generate_template:
        generate_template(args.generate_template, args.template_type)
        print(f"Test script template generated: {args.generate_template}")
        print(f"Template type: {args.template_type}")
        print("Edit this file to add your build and test commands.")
        return 0

    # Validate required arguments
    if not args.good:
        parser.error("--good is required (unless using --generate-template)")
    if not args.test:
        parser.error("--test is required (unless using --generate-template)")

    # Run bisect
    runner = BisectRunner(
        repo_path=args.repo,
        good_commit=args.good,
        bad_commit=args.bad,
        test_script=args.test,
        branch=args.branch,
        use_worktree=args.worktree,
        state_file=args.state_file,
        show_ancestry=args.show_ancestry,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    return runner.run()


if __name__ == "__main__":
    sys.exit(main())

