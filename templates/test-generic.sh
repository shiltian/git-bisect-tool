#!/bin/bash
# =============================================================================
# Git Bisect Test Script Template - Generic
# =============================================================================
#
# This script is called by git-bisect-tool for each commit being tested.
#
# Arguments:
#   $1 - Commit hash being tested
#   $2 - Path to the worktree (or repo if not using --worktree)
#
# Exit codes:
#   0        - Good commit (test passes)
#   1-124    - Bad commit (test fails)
#   125      - Skip this commit (can't build/test)
#   126-127  - Bad commit (test fails)
#   128+     - Abort bisect (fatal error)
#
# Usage:
#   1. Copy this template to a new file
#   2. Modify the BUILD STEP and TEST STEP sections
#   3. Run: git-bisect-tool --good <good> --test ./your_test.sh --worktree
#
# =============================================================================

set -e  # Exit on error (comment out if you need custom error handling)

COMMIT_HASH="$1"
WORKTREE_PATH="$2"

# Validate arguments
if [[ -z "$COMMIT_HASH" ]]; then
    echo "Error: No commit hash provided"
    exit 128
fi

if [[ -z "$WORKTREE_PATH" ]]; then
    echo "Error: No worktree path provided"
    exit 128
fi

echo "=============================================="
echo "Testing commit: $COMMIT_HASH"
echo "Worktree path:  $WORKTREE_PATH"
echo "=============================================="

cd "$WORKTREE_PATH"

# =============================================================================
# BUILD STEP
# =============================================================================
# Customize this section for your project's build system.
#
# IMPORTANT: If build fails in a way that means this commit can't be tested
# (e.g., unrelated build breakage), use `exit 125` to skip the commit.
# =============================================================================

build() {
    echo ">>> Building..."

    # ---------------------------------------------------------------------
    # Example: CMake project
    # ---------------------------------------------------------------------
    # BUILD_DIR="$WORKTREE_PATH/build"
    # mkdir -p "$BUILD_DIR"
    # cd "$BUILD_DIR"
    #
    # cmake -G Ninja \
    #     -DCMAKE_BUILD_TYPE=Release \
    #     -DCMAKE_C_COMPILER=clang \
    #     -DCMAKE_CXX_COMPILER=clang++ \
    #     "$WORKTREE_PATH"
    #
    # ninja -j$(nproc) my_target

    # ---------------------------------------------------------------------
    # Example: Make project
    # ---------------------------------------------------------------------
    # make clean
    # make -j$(nproc)

    # ---------------------------------------------------------------------
    # Example: Python project
    # ---------------------------------------------------------------------
    # pip install -e .

    # ---------------------------------------------------------------------
    # TODO: Add your build commands here
    # ---------------------------------------------------------------------
    echo ">>> Build completed"
}

# =============================================================================
# TEST STEP
# =============================================================================
# Customize this section for your specific test case.
#
# Return 0 if the test PASSES (commit is good)
# Return 1-124 or 126-127 if the test FAILS (commit is bad)
# =============================================================================

run_test() {
    echo ">>> Running test..."

    # ---------------------------------------------------------------------
    # Example: Run a specific test binary
    # ---------------------------------------------------------------------
    # ./build/my_test --input test_input.txt

    # ---------------------------------------------------------------------
    # Example: Check if output matches expected
    # ---------------------------------------------------------------------
    # output=$(./build/my_program --process data.txt)
    # if [[ "$output" == *"expected result"* ]]; then
    #     echo ">>> Test PASSED: Found expected output"
    #     return 0
    # else
    #     echo ">>> Test FAILED: Did not find expected output"
    #     return 1
    # fi

    # ---------------------------------------------------------------------
    # Example: Check if program crashes
    # ---------------------------------------------------------------------
    # if ./build/my_program --test 2>&1; then
    #     echo ">>> Test PASSED: No crash"
    #     return 0
    # else
    #     echo ">>> Test FAILED: Program crashed"
    #     return 1
    # fi

    # ---------------------------------------------------------------------
    # Example: Check for specific error in output
    # ---------------------------------------------------------------------
    # output=$(./build/my_program 2>&1 || true)
    # if echo "$output" | grep -q "FATAL ERROR"; then
    #     echo ">>> Test FAILED: Found fatal error"
    #     return 1
    # else
    #     echo ">>> Test PASSED: No fatal error"
    #     return 0
    # fi

    # ---------------------------------------------------------------------
    # Example: Run in Docker container
    # ---------------------------------------------------------------------
    # docker exec my_container /path/to/test.sh

    # ---------------------------------------------------------------------
    # TODO: Add your test commands here
    # ---------------------------------------------------------------------
    echo ">>> Test completed"
    return 0
}

# =============================================================================
# MAIN
# =============================================================================

# Run build step
# If build fails, we might want to skip this commit
if ! build; then
    echo ">>> Build failed, skipping commit"
    exit 125
fi

# Run test step
if run_test; then
    echo "=============================================="
    echo "Result: GOOD (test passed)"
    echo "=============================================="
    exit 0
else
    echo "=============================================="
    echo "Result: BAD (test failed)"
    echo "=============================================="
    exit 1
fi

