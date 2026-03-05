#!/usr/bin/env bash
# acp-worktree-setup.sh — Create isolated git worktree for an ACP worker.
# Returns the worktree path on stdout. Caller uses it as cwd for sessions_spawn.
#
# Usage: acp-worktree-setup.sh <repo_dir> <branch_name>
# Example: acp-worktree-setup.sh /path/to/repo feat/my-task
#   → Creates worktree at /path/to/repo-worktrees/<branch_name>
#   → Creates and checks out <branch_name> from current HEAD
#   → Prints worktree path

set -euo pipefail

REPO_DIR="${1:?Usage: acp-worktree-setup.sh <repo_dir> <branch_name>}"
BRANCH="${2:?Usage: acp-worktree-setup.sh <repo_dir> <branch_name>}"

WORKTREE_BASE="${REPO_DIR}-worktrees"
WORKTREE_DIR="${WORKTREE_BASE}/${BRANCH//\//-}"

mkdir -p "$WORKTREE_BASE"

cd "$REPO_DIR"

# Clean up stale worktree if exists
if [ -d "$WORKTREE_DIR" ]; then
    git worktree remove --force "$WORKTREE_DIR" 2>/dev/null || rm -rf "$WORKTREE_DIR"
fi

# Delete branch if exists (stale from previous run)
git branch -D "$BRANCH" 2>/dev/null || true

# Create worktree with new branch from HEAD
git worktree add -b "$BRANCH" "$WORKTREE_DIR" HEAD 2>/dev/null

echo "$WORKTREE_DIR"
