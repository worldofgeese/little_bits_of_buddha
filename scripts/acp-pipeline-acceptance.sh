#!/usr/bin/env bash
# acp-pipeline-acceptance.sh — Validates the ACP completion pipeline end-to-end.
# Creates 2 workers on isolated worktrees, simulates pushes, verifies poller detects + merges both.
# Exit 0 = pass, Exit 1 = fail.
#
# Usage: acp-pipeline-acceptance.sh <repo_dir>

set -euo pipefail

REPO="${1:?Usage: acp-pipeline-acceptance.sh <repo_dir>}"
WORKSPACE="/home/node/.openclaw/workspace"
TASKS_FILE="$WORKSPACE/memory/active-tasks.json"
COMPLETIONS_DIR="$WORKSPACE/memory/acp-completions"
BASELINE=$(cd "$REPO" && git rev-parse HEAD)

echo "=== ACP Pipeline Acceptance Test ==="
echo "Repo: $REPO"
echo "Baseline: $BASELINE"

PASS=0
FAIL=0

assert() {
    local desc="$1" result="$2"
    if [ "$result" = "true" ]; then
        echo "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc"
        FAIL=$((FAIL + 1))
    fi
}

# --- Test 1: Worktree isolation ---
echo ""
echo "--- Test 1: Worktree isolation ---"

WT_A=$(bash "$WORKSPACE/scripts/acp-worktree-setup.sh" "$REPO" "test/accept-a" 2>/dev/null | tail -1)
WT_B=$(bash "$WORKSPACE/scripts/acp-worktree-setup.sh" "$REPO" "test/accept-b" 2>/dev/null | tail -1)

assert "Worktree A exists" "$([ -d "$WT_A" ] && echo true || echo false)"
assert "Worktree B exists" "$([ -d "$WT_B" ] && echo true || echo false)"
assert "Worktree A != Worktree B" "$([ "$WT_A" != "$WT_B" ] && echo true || echo false)"

# Each worktree on its own branch
BRANCH_A=$(cd "$WT_A" && git branch --show-current)
BRANCH_B=$(cd "$WT_B" && git branch --show-current)
assert "Worktree A on branch test/accept-a" "$([ "$BRANCH_A" = "test/accept-a" ] && echo true || echo false)"
assert "Worktree B on branch test/accept-b" "$([ "$BRANCH_B" = "test/accept-b" ] && echo true || echo false)"

# --- Test 2: Cross-contamination prevention ---
echo ""
echo "--- Test 2: Cross-contamination ---"

# Create a file in A, verify it's NOT in B
echo "worker-a" > "$WT_A/accept-test-a.txt"
assert "File in A not visible in B" "$([ ! -f "$WT_B/accept-test-a.txt" ] && echo true || echo false)"

echo "worker-b" > "$WT_B/accept-test-b.txt"
assert "File in B not visible in A" "$([ ! -f "$WT_A/accept-test-b.txt" ] && echo true || echo false)"

# --- Test 3: Independent commits ---
echo ""
echo "--- Test 3: Independent commits ---"

cd "$WT_A"
git add accept-test-a.txt && git commit -m "accept: worker A" --no-verify -q
git push origin test/accept-a -q 2>/dev/null

cd "$WT_B"
git add accept-test-b.txt && git commit -m "accept: worker B" --no-verify -q
git push origin test/accept-b -q 2>/dev/null

cd "$REPO"
git fetch origin --prune 2>/dev/null

HEAD_A=$(git rev-parse "origin/test/accept-a")
HEAD_B=$(git rev-parse "origin/test/accept-b")
assert "Branch A has new commit" "$([ "$HEAD_A" != "$BASELINE" ] && echo true || echo false)"
assert "Branch B has new commit" "$([ "$HEAD_B" != "$BASELINE" ] && echo true || echo false)"
assert "Branch A != Branch B" "$([ "$HEAD_A" != "$HEAD_B" ] && echo true || echo false)"

# --- Test 4: Poller detection (register + wait) ---
echo ""
echo "--- Test 4: Poller detection ---"

# Register tasks
NOW=$(date +%s)
jq -n --argjson now "$NOW" --arg bl "$BASELINE" --arg repo "$REPO" '[
  {label:"accept-a",sessionKey:"test",spawnedAt:$now,deadlineAt:($now+300),timeoutMinutes:5,status:"running",branch:"test/accept-a",baseline:$bl,repoDir:$repo},
  {label:"accept-b",sessionKey:"test",spawnedAt:$now,deadlineAt:($now+300),timeoutMinutes:5,status:"running",branch:"test/accept-b",baseline:$bl,repoDir:$repo}
]' > "$TASKS_FILE"

# Wait for poller (up to 90s)
echo "  Waiting for poller to detect + merge (up to 90s)..."
for i in $(seq 1 9); do
    sleep 10
    A_GONE=$(git rev-parse --verify "origin/test/accept-a" 2>/dev/null && echo "no" || echo "yes")
    B_GONE=$(git rev-parse --verify "origin/test/accept-b" 2>/dev/null && echo "no" || echo "yes")
    git fetch origin --prune 2>/dev/null
    if [ "$A_GONE" = "yes" ] && [ "$B_GONE" = "yes" ]; then
        break
    fi
done

# Refresh
cd "$REPO"
git fetch origin --prune 2>/dev/null
git pull --ff-only origin main 2>/dev/null || true

A_MERGED=$(git log --oneline | grep -c "accept: worker A" || true)
B_MERGED=$(git log --oneline | grep -c "accept: worker B" || true)

assert "Worker A commit merged to main" "$([ "$A_MERGED" -ge 1 ] && echo true || echo false)"
assert "Worker B commit merged to main" "$([ "$B_MERGED" -ge 1 ] && echo true || echo false)"

# Check both files present on main
assert "accept-test-a.txt on main" "$([ -f "$REPO/accept-test-a.txt" ] && echo true || echo false)"
assert "accept-test-b.txt on main" "$([ -f "$REPO/accept-test-b.txt" ] && echo true || echo false)"

# --- Cleanup ---
echo ""
echo "--- Cleanup ---"
cd "$REPO"
git worktree remove --force "$WT_A" 2>/dev/null || true
git worktree remove --force "$WT_B" 2>/dev/null || true
git push origin --delete test/accept-a 2>/dev/null || true
git push origin --delete test/accept-b 2>/dev/null || true
git branch -D test/accept-a test/accept-b 2>/dev/null || true
rmdir "$(dirname "$WT_A")" 2>/dev/null || true

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
