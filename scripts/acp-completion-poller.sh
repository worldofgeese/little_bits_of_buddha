#!/usr/bin/env bash
# acp-completion-poller.sh — Background process that polls active ACP worker branches
# Writes signal files to memory/acp-completions/ when new commits detected.
# Zero LLM cost. Runs until killed.
#
# Usage: acp-completion-poller.sh [poll_interval_seconds]
# Default interval: 60s

set -euo pipefail

POLL_INTERVAL="${1:-60}"
WORKSPACE="/home/node/.openclaw/workspace"
TASKS_FILE="$WORKSPACE/memory/active-tasks.json"
COMPLETIONS_DIR="$WORKSPACE/memory/acp-completions"
PIDFILE="$WORKSPACE/memory/acp-poller.pid"
LOGFILE="$WORKSPACE/memory/acp-poller.log"

mkdir -p "$COMPLETIONS_DIR"

# Write PID for management
echo $$ > "$PIDFILE"

log() {
    echo "[$(date -Iseconds)] $*" >> "$LOGFILE"
}

cleanup() {
    rm -f "$PIDFILE"
    log "Poller stopped (PID $$)"
    exit 0
}
trap cleanup EXIT INT TERM

log "Poller started (PID $$, interval ${POLL_INTERVAL}s)"

# Trim log if >100KB
trim_log() {
    if [ -f "$LOGFILE" ] && [ "$(stat -c%s "$LOGFILE" 2>/dev/null || echo 0)" -gt 102400 ]; then
        tail -200 "$LOGFILE" > "${LOGFILE}.tmp" && mv "${LOGFILE}.tmp" "$LOGFILE"
    fi
}

while true; do
    trim_log

    # Check if there are active tasks
    if [ ! -f "$TASKS_FILE" ] || [ "$(cat "$TASKS_FILE" 2>/dev/null)" = "[]" ]; then
        sleep "$POLL_INTERVAL"
        continue
    fi

    # Parse each running task
    while IFS= read -r task; do
        label=$(echo "$task" | jq -r '.label')
        branch=$(echo "$task" | jq -r '.branch // empty')
        baseline=$(echo "$task" | jq -r '.baseline // empty')
        status=$(echo "$task" | jq -r '.status // "running"')
        repo_dir=$(echo "$task" | jq -r '.repoDir // empty')

        [ "$status" != "running" ] && continue
        [ -z "$branch" ] && continue

        # Default repo dir (legacy tasks don't have repoDir)
        if [ -z "$repo_dir" ]; then
            repo_dir="$WORKSPACE/projects/little_bits_of_buddha"
        fi

        [ ! -d "$repo_dir" ] && continue

        # Skip if signal already written
        signal_file="$COMPLETIONS_DIR/${label}.json"
        [ -f "$signal_file" ] && continue

        # Check remote
        cd "$repo_dir"
        git fetch origin --prune 2>/dev/null || continue

        remote_head=$(git rev-parse --verify --quiet "origin/$branch" 2>/dev/null || echo "")
        [ -z "$remote_head" ] && continue

        # Compare to baseline
        if [ -n "$baseline" ] && [ "$remote_head" = "$baseline" ]; then
            continue
        fi

        # New commits! Write signal file.
        commit_count=$(git rev-list --count "${baseline}..origin/${branch}" 2>/dev/null || echo "?")
        last_msg=$(git log "origin/$branch" --oneline -1 2>/dev/null || echo "unknown")

        cat > "$signal_file" <<EOF
{
  "label": "$label",
  "branch": "$branch",
  "baseline": "$baseline",
  "head": "$remote_head",
  "commitCount": "$commit_count",
  "lastCommitMsg": "$last_msg",
  "repoDir": "$repo_dir",
  "detectedAt": "$(date -Iseconds)",
  "detectedBy": "poller"
}
EOF
        log "COMPLETION DETECTED: $label branch=$branch commits=$commit_count head=$remote_head"

        # Run merge pipeline immediately (don't wait for heartbeat)
        MERGE_SCRIPT="$WORKSPACE/scripts/acp-merge-pipeline.sh"
        if [ -x "$MERGE_SCRIPT" ] || [ -f "$MERGE_SCRIPT" ]; then
            log "Running merge pipeline for $label..."
            merge_output=$(bash "$MERGE_SCRIPT" "$signal_file" 2>&1) || true
            log "Merge output: $merge_output"

            # If merged successfully, notify via openclaw message (best effort)
            if echo "$merge_output" | grep -q "^MERGED|"; then
                merged_line=$(echo "$merge_output" | grep "^MERGED|")
                m_label=$(echo "$merged_line" | cut -d'|' -f2)
                m_branch=$(echo "$merged_line" | cut -d'|' -f3)
                m_commits=$(echo "$merged_line" | cut -d'|' -f4)
                m_sha=$(echo "$merged_line" | cut -d'|' -f5 | head -c 7)
                m_stat=$(echo "$merged_line" | cut -d'|' -f6)
                log "MERGE SUCCESS: $m_label ($m_branch, $m_commits commits, $m_sha)"
            else
                log "MERGE ISSUE: $label — output: $merge_output"
            fi
        fi

    done < <(jq -c '.[]' "$TASKS_FILE" 2>/dev/null || true)

    sleep "$POLL_INTERVAL"
done
