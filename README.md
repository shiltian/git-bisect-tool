# Git Bisect Tool

A Python wrapper around `git bisect run` with enhanced logging and UX for finding faulty commits in complex branch histories.

## Usage

```bash
# Basic usage
./git-bisect-tool --good <good-commit> --test ./test.sh

# With worktree isolation
./git-bisect-tool --good v1.0.0 --bad HEAD --test ./test.sh --worktree

# Dry run (show config and estimate without running)
./git-bisect-tool --good abc123 --test ./test.sh --dry-run
```

## Test Script

Your test script receives `<commit_hash> <worktree_path>` and should exit with:
- `0` — Good commit
- `1-124` — Bad commit
- `125` — Skip (can't test)

See `templates/` for example test scripts.

## Installation

```bash
pip install -e .
```

Or run directly without installing:

```bash
./git-bisect-tool --help
```

## License

MIT
