#!/usr/bin/env bash
# acp-merge-pipeline.sh — Mechanical merge pipeline for completed ACP workers.
# Reads signal files from memory/acp-completions/, merges branches, pushes, cleans up.
# Zero LLM. Called by heartbeat or manually.
#
# Usage: acp-merge-pipeline.sh [signal_file]
#   If signal_file given: process just that one.
#   If omitted: process all signal files in memory/acp-completions/

set -euo pipefail

WORKSPACE="/home/node/.openclaw/workspace"
COMPLETIONS_DIR="$WORKSPACE/memory/acp-completions"
TASKS_FILE="$WORKSPACE/memory/active-tasks.json"
PIPELINE_STATE="$WORKSPACE/memory/pipeline-state.json"
PIPELINE_ERRORS="$WORKSPACE/memory/pipeline-errors.txt"

process_signal() {
    local signal_file="$1"
    local label branch baseline head repo_dir

    label=$(jq -r '.label' "$signal_file")
    branch=$(jq -r '.branch' "$signal_file")
    baseline=$(jq -r '.baseline // empty' "$signal_file")
    head=$(jq -r '.head' "$signal_file")
    repo_dir=$(jq -r '.repoDir' "$signal_file")
    commit_count=$(jq -r '.commitCount // "?"' "$signal_file")

    echo "Processing: $label (branch=$branch, commits=$commit_count)"

    cd "$repo_dir"
    git fetch origin --prune 2>/dev/null

    # Ensure we're on main
    git checkout main 2>/dev/null
    git pull --ff-only origin main 2>/dev/null || true

    # Merge
    if git merge --no-edit "origin/$branch" 2>/dev/null; then
        echo "  Merged $branch → main"

        # Push
        if git push origin main 2>/dev/null; then
            echo "  Pushed to origin/main"

            # Get merge commit and diff stats
            merge_sha=$(git rev-parse HEAD)
            diff_stat=$(git diff --stat "${baseline}..HEAD" 2>/dev/null | tail -1 || echo "unknown")

            # Update tracker
            bash "$WORKSPACE/scripts/subagent-tracker.sh" complete "$label" 2>/dev/null || true

            # Write pipeline state
            cat > "$PIPELINE_STATE" <<EOF
{
  "lastMerge": {
    "label": "$label",
    "branch": "$branch",
    "mergedAt": "$(date -Iseconds)",
    "mergeSha": "$merge_sha",
    "commitCount": "$commit_count",
    "diffStat": "$diff_stat"
  }
}
EOF

            # Delete remote branch (cleanup)
            git push origin --delete "$branch" 2>/dev/null || true

            # Remove signal file
            rm -f "$signal_file"

            # Output for caller (heartbeat) to message Tao
            echo "MERGED|$label|$branch|$commit_count|$merge_sha|$diff_stat"
            return 0
        else
            echo "  ERROR: push failed"
            echo "[$(date -Iseconds)] PUSH FAILED: $label branch=$branch" >> "$PIPELINE_ERRORS"
            return 1
        fi
    else
        # Merge conflict
        git merge --abort 2>/dev/null || true
        echo "  ERROR: merge conflict on $branch"
        echo "[$(date -Iseconds)] MERGE CONFLICT: $label branch=$branch" >> "$PIPELINE_ERRORS"
        # Don't remove signal file — let heartbeat escalate
        return 1
    fi
}

# Main
if [ -n "${1:-}" ]; then
    process_signal "$1"
else
    found=0
    for f in "$COMPLETIONS_DIR"/*.json; do
        [ -f "$f" ] || continue
        found=1
        process_signal "$f" || true
    done
    if [ "$found" -eq 0 ]; then
        echo "NO_COMPLETIONS"
    fi
fi
