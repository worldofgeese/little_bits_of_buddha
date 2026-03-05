# LBOB Phase 4 Bootstrap Prompt

Paste this at the start of a new session to give Kypris full context on Little Bits of Buddha.

---

## Context Load

Read these files in order before doing anything:

1. `memory/projects/little-bits-of-buddha.md` — project status, architecture, bot credentials, hard-won lessons
2. `memory/context/multi-agent.md` — ACP dispatch patterns, completion detection, cron architecture
3. `memory/context/sdlc-patterns.md` — TDD, task briefs, autonomous pipeline, self-correction loop
4. `memory/context/lessons.md` — operational lessons (especially the ACP completion section)
5. `projects/little_bits_of_buddha/phase3-plan.md` — completed Phase 3 plan (reference for patterns)
6. `projects/little_bits_of_buddha/docs/lbob-vision-updated.html` — vision doc with Phase 4 roadmap

## Project State

- **Repo**: `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`
- **Remote**: `ssh://forgejo@paphos.hound-celsius.ts.net/kypris/little_bits_of_buddha.git`
- **Main branch HEAD**: `89eb410` (Phase 3 complete, pipeline experiments cleaned up)
- **Bot**: `@LittleBitsOfBuddhaBot`, token in `TRIOGRAM_TOKEN` env var
- **Model**: `anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0` (via Bedrock proxy)

## What's Built (Phases 1-3, all complete)

- 4 services: telegram-bot, seeker-actor, wisdom, meditation-workflow
- 286 suttas from SuttaCentral (Bhikkhu Sujato, CC0) with vector embeddings
- Dapr Virtual Actors (one per seeker), Dapr Workflows (guided meditation), Dapr Jobs (daily sutta + weekly check-in)
- 9 Telegram commands: /start, /level, /forget, /help, /meditate, /daily, /sit, /path, /journal
- RAG pipeline, tool calling (LLM decides when to search), LangCache (semantic response caching)
- Practice journaling, learning paths, adaptive practice levels
- TDD throughout, integration tests

## What's NOT deployed yet

Phase 2 and 3 images haven't been pushed to Paphos. The bot needs new Docker images built and compose brought up. This should happen before Phase 4 work begins.

## How to Dispatch Workers

```
# 1. Write task brief to a file
write /tmp/lbob-<task>.md

# 2. Create isolated worktree (MANDATORY for parallel workers)
WORKTREE=$(bash scripts/acp-worktree-setup.sh projects/little_bits_of_buddha feat/<branch>)

# 3. Copy task brief into worktree
cp /tmp/lbob-<task>.md $WORKTREE/.acp-task.md

# 4. Dispatch via ACP with worktree as cwd
sessions_spawn(runtime="acp", agentId="claude", cwd=$WORKTREE, label="lbob-<name>", task="Read .acp-task.md and complete all tasks.")

# 5. Register with tracker
BASELINE=$(cd projects/little_bits_of_buddha && git rev-parse HEAD)
# Update memory/active-tasks.json with: label, sessionKey, branch, baseline, repoDir, status:"running"

# 6. Message Tao with what you dispatched
```

**The poller handles everything after push.** Detection → merge → cleanup → state update. You just dispatch and register.

## How Completion Detection Works (Validated 2026-03-05)

**Critical: You will NOT receive completion events in your session.**

- ACP workers have no OpenClaw tools. They can't sessions_send.
- ACP announce goes to Tao's Telegram channel, not to your session.
- `sessions_list` and `subagents list` are blind to ACP sessions.

**Architecture (zero LLM cost, validated with 14/14 acceptance tests):**

1. **Background poller** (`scripts/acp-completion-poller.sh`) — launched by `gateway:startup` hook
   - Polls git branches registered in `memory/active-tasks.json` every 60s
   - On detection: writes signal file to `memory/acp-completions/<label>.json` AND immediately runs `scripts/acp-merge-pipeline.sh` (merge → push → cleanup)
   - Zero LLM cost, survives gateway restarts via hook relaunch

2. **Merge pipeline** (`scripts/acp-merge-pipeline.sh`) — called by poller on detection
   - Merges branch to main (fast-forward or ort strategy), pushes, deletes remote branch
   - Updates `memory/pipeline-state.json` and `scripts/subagent-tracker.sh complete`
   - Logs failures to `memory/pipeline-errors.txt`

3. **Heartbeat** audits `memory/pipeline-state.json` and `memory/pipeline-errors.txt`
   - Does NOT run merges (poller handles that)
   - Dispatches follow-on work (next wave) or escalates errors to Tao

4. **Worktree isolation** — MANDATORY for parallel workers
   - `scripts/acp-worktree-setup.sh <repo> <branch>` creates isolated worktrees
   - Without worktrees, workers share a checkout and cross-contaminate branches (proven failure mode)

**Pipeline flow:**
```
Dispatch: sessions_spawn(runtime="acp", cwd=<worktree>) + register in active-tasks.json
    ↓
ACP worker completes → pushes to branch
    ↓
Background poller (60s) detects new commits → writes signal + runs merge
    ↓
Merged to main, pushed, branch deleted, tracker completed
    ↓
Heartbeat picks up pipeline-state.json → messages Tao, dispatches next wave
```

**Validated:** 7 experiments across 2 rounds (2-30 min durations), plus 14-assertion acceptance test covering worktree isolation, cross-contamination prevention, independent commits, and poller-driven merge.

**Key files:**
- `hooks/acp-pipeline/` — gateway:startup hook (launches poller)
- `scripts/acp-completion-poller.sh` — detection + merge trigger
- `scripts/acp-merge-pipeline.sh` — mechanical merge/push
- `scripts/acp-worktree-setup.sh` — per-worker worktree creation
- `scripts/acp-pipeline-acceptance.sh` — 14-assertion acceptance test
- `scripts/subagent-tracker.sh` — register/complete/check
- `memory/active-tasks.json` — worker registry
- `memory/acp-completions/` — signal files (audit trail)
- `memory/pipeline-state.json` — last merge record
- `memory/pipeline-errors.txt` — failure log

## Key Constraints

- Python 3.12, trio (NOT asyncio) for existing services
- Dapr Workflows use generators (separate process, no trio conflict)
- DaprClient is sync-only — wrap with `trio.to_thread.run_sync`
- Raw httpx to Anthropic proxy (not LiteLLM — header conflict, ADR 0009)
- Rootless Podman: `DOCKER_HOST=tcp://podman-in-podman:2375`, `DOCKER_BUILDKIT=0`
- This is an Early Buddhist Teachings bot ONLY — no Zen, no secular mindfulness, no multi-tradition routing

## Relevant Skills

- `skills/visual-explainer/SKILL.md` — for HTML deliverables
- `skills/paphos-ssh/SKILL.md` — for deployment to Paphos
- `skills/forgejo/SKILL.md` — for Forgejo repo management
- `skills/coding-agent/SKILL.md` — for CC dispatch details

## Phase 4 Planning

The vision doc lists Phase 4 features:
- Long-term seeker memory (Redis Agent Memory Server)
- Anonymous practice analytics (Redis TimeSeries)
- Hybrid search (full-text + vector)
- Full Tipiṭaka expansion (286 → 5,000+ suttas, int8 quantization)
- Group practice sessions
- Retreat mode

Start by: reading the vision doc, doing a design spike on the most impactful features, writing a phase4-plan.md similar to phase3-plan.md, then dispatching Wave 1.

But first: **deploy Phase 3** to Paphos. Build images, push, compose up.
