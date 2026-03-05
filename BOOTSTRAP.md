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
- **Main branch HEAD**: `185fd3e` (Phase 3 complete — all 3 waves merged)
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
write projects/lbob-<name>/prompts/<task>.md

# 2. Create git worktree
cd projects/little_bits_of_buddha && git worktree add ../lbob-<name> -b feat/<branch> main

# 3. Dispatch via ACP
sessions_spawn(runtime="acp", model="anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0", label="lbob-<name>", task="Read task brief at .../prompts/<task>.md and complete all tasks.")

# 4. Register with tracker (include branch + baseline SHA)
bash scripts/subagent-tracker.sh register <label> <sessionKey> 90
# Then update memory/active-tasks.json with branch and baseline fields

# 5. Message Tao with what you dispatched
```

## How Completion Detection Works

**Critical: You will NOT receive completion events in your session.**

- ACP workers have no OpenClaw tools. They can't sessions_send.
- ACP announce goes to Tao's Telegram channel, not to your session.
- `sessions_list` is blind to ACP sessions.

The `acp-branch-watcher` cron (every 3 min, claude-sonnet-4.5, isolated) handles the full pipeline:
1. Polls git branches in `memory/active-tasks.json`
2. Detects new commits (compares HEAD to baseline SHA)
3. Merges to main, pushes, messages Tao directly
4. Writes `memory/pipeline-state.json` on success
5. Writes `memory/pipeline-errors.txt` on failure

**Your heartbeat** checks these state files and handles follow-up orchestration (dispatching next workers, cleaning worktrees).

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
