#!/bin/bash
# =============================================================================
# Git Bisect Test Script Template - LLVM/Clang Projects
# =============================================================================
#
# This script is designed for bisecting LLVM/Clang/LLVM-related projects.
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
#   1. Copy this template and modify the configuration section
#   2. Run: git-bisect-tool --good <good> --test ./your_test.sh --worktree
#
# =============================================================================

set -e  # Exit on error

COMMIT_HASH="$1"
WORKTREE_PATH="$2"

# =============================================================================
# CONFIGURATION - Modify these for your setup
# =============================================================================

# Build directory (separate from source for out-of-tree builds)
BUILD_DIR="${BUILD_ROOT:-/tmp}/llvm-bisect-build"

# Number of parallel jobs
NJOBS=${NJOBS:-$(nproc)}

# Build type
BUILD_TYPE="Release"

# Compilers to use for building LLVM
HOST_CC="${HOST_CC:-/usr/bin/clang}"
HOST_CXX="${HOST_CXX:-/usr/bin/clang++}"

# LLVM targets to build
LLVM_TARGETS="host;AMDGPU;NVPTX"

# LLVM projects to enable
LLVM_PROJECTS="clang;lld"

# LLVM runtimes to enable (can be empty)
LLVM_RUNTIMES=""

# Use ccache if available
if command -v ccache &> /dev/null; then
    CCACHE_LAUNCHER="-DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
else
    CCACHE_LAUNCHER=""
fi

# =============================================================================
# VALIDATION
# =============================================================================

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
echo "Build dir:      $BUILD_DIR"
echo "=============================================="

# =============================================================================
# BUILD STEP
# =============================================================================

build_llvm() {
    echo ">>> Building LLVM..."

    # Clean previous build
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"

    # Configure
    echo ">>> Configuring with CMake..."
    cmake -G Ninja \
        -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
        $CCACHE_LAUNCHER \
        -DCMAKE_C_COMPILER="$HOST_CC" \
        -DCMAKE_CXX_COMPILER="$HOST_CXX" \
        -DLLVM_TARGETS_TO_BUILD="$LLVM_TARGETS" \
        -DLLVM_ENABLE_PROJECTS="$LLVM_PROJECTS" \
        ${LLVM_RUNTIMES:+-DLLVM_ENABLE_RUNTIMES="$LLVM_RUNTIMES"} \
        -DLLVM_ENABLE_ASSERTIONS=ON \
        -DLLVM_ENABLE_LLD=ON \
        -DLLVM_INSTALL_UTILS=ON \
        -DLLVM_INCLUDE_BENCHMARKS=OFF \
        -DLLVM_INCLUDE_EXAMPLES=OFF \
        -DLLVM_INCLUDE_TESTS=OFF \
        -DLLVM_ENABLE_BINDINGS=OFF \
        -DLLVM_ENABLE_OCAMLDOC=OFF \
        -DLLVM_INCLUDE_DOCS=OFF \
        -B "$BUILD_DIR" \
        -S "$WORKTREE_PATH/llvm"

    # Build
    # TODO: Replace 'all' with specific target if you only need certain tools
    echo ">>> Building with Ninja..."
    ninja -C "$BUILD_DIR" -j"$NJOBS" all

    echo ">>> Build completed successfully"
}

# =============================================================================
# TEST STEP - Modify this section for your specific test case
# =============================================================================

run_test() {
    echo ">>> Running test..."

    # Path to built clang/tools
    CLANG="$BUILD_DIR/bin/clang"
    CLANGXX="$BUILD_DIR/bin/clang++"
    OPT="$BUILD_DIR/bin/opt"
    LLC="$BUILD_DIR/bin/llc"

    # ---------------------------------------------------------------------
    # Example 1: Test if clang compiles a specific file without crashing
    # ---------------------------------------------------------------------
    # $CLANG -c /path/to/test.c -o /dev/null

    # ---------------------------------------------------------------------
    # Example 2: Test if a specific optimization produces correct output
    # ---------------------------------------------------------------------
    # $OPT -passes=mem2reg /path/to/test.ll -o - | FileCheck /path/to/test.ll

    # ---------------------------------------------------------------------
    # Example 3: Test if LLVM test suite passes
    # ---------------------------------------------------------------------
    # ninja -C "$BUILD_DIR" check-llvm-<component>

    # ---------------------------------------------------------------------
    # Example 4: Test if program produces correct runtime output
    # ---------------------------------------------------------------------
    # $CLANG /path/to/program.c -o /tmp/test_prog
    # output=$(/tmp/test_prog 2>&1)
    # if [[ "$output" == *"expected output"* ]]; then
    #     echo ">>> Test PASSED"
    #     return 0
    # else
    #     echo ">>> Test FAILED: Got: $output"
    #     return 1
    # fi

    # ---------------------------------------------------------------------
    # Example 5: Test if a crash happens (looking for crash = bad commit)
    # ---------------------------------------------------------------------
    # if $CLANG -c /path/to/crashing.c -o /dev/null 2>&1; then
    #     echo ">>> Test PASSED: No crash"
    #     return 0
    # else
    #     echo ">>> Test FAILED: Clang crashed"
    #     return 1
    # fi

    # ---------------------------------------------------------------------
    # Example 6: Test if a miscompilation happens
    # ---------------------------------------------------------------------
    # $CLANG -O2 /path/to/test.c -o /tmp/optimized
    # $CLANG -O0 /path/to/test.c -o /tmp/unoptimized
    # opt_out=$(/tmp/optimized)
    # ref_out=$(/tmp/unoptimized)
    # if [[ "$opt_out" == "$ref_out" ]]; then
    #     echo ">>> Test PASSED: Output matches"
    #     return 0
    # else
    #     echo ">>> Test FAILED: Miscompilation detected"
    #     echo ">>> Optimized output:   $opt_out"
    #     echo ">>> Unoptimized output: $ref_out"
    #     return 1
    # fi

    # ---------------------------------------------------------------------
    # TODO: Add your test commands here
    # ---------------------------------------------------------------------

    echo ">>> Test completed"
    return 0
}

# =============================================================================
# MAIN
# =============================================================================

cd "$WORKTREE_PATH"

# Run build step
if ! build_llvm; then
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

