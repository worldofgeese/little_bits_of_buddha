# LBOB Phase 3 Session Bootstrap

Paste this at the start of a clean session to give Kypris full context.

---

## Context Load

Read these files in order before doing anything:

1. `memory/projects/little-bits-of-buddha.md` — Project status, bot credentials, hard-won lessons
2. `projects/little_bits_of_buddha/phase2-plan.md` — Phase 2 plan (completed), architecture decisions, risk mitigations
3. `projects/little_bits_of_buddha/docs/lbob-vision-updated.html` — Full vision document with Redis/Dapr maximization research
4. `memory/context/sdlc-patterns.md` — How we dispatch work (TDD, branch-per-task, judge pipeline, ACP workers)
5. `memory/context/lessons.md` — ACP completion signaling, dispatch patterns, debugging lessons
6. `memory/context/multi-agent.md` — Model chain, worker dispatch, routing rules

## Skills to Read

- `skills/coding-agent/SKILL.md` — For CC dispatch
- `skills/visual-explainer/SKILL.md` — For rendering plans/architecture as HTML

## What's Built (Phase 1 + 2 — all on main, Docker images built)

### Services:
- **telegram-bot-service** — Telegram bot with /start, /level, /forget, /help + pub/sub message forwarding
- **seeker-actor-service** — Dapr Virtual Actor host. One SeekerActor per user. Holds conversation history, practice level, explored topics. Calls wisdom-service via Dapr service invocation.
- **wisdom-service** — LLM + RAG pipeline. Semantic sutta vector search (286 suttas, all-MiniLM-L6-v2, 384-dim). Practice-level-adapted system prompts. Dapr Conversation API (caching, PII scrubbing) with raw httpx fallback. Returns response + suttas_cited + detected_themes.
- **Level detector** — Heuristic practice level detection (newcomer → beginner → intermediate → experienced) based on vocabulary, question complexity, conversation count. Level only goes up.

### Tests:
- `test_seeker_actor.py`, `test_wisdom_service.py`, `test_level_detector.py`, `test_phase2_infra.py`, `test_telegram_commands.py`, `test_phase2_integration.py` (881 lines)

### Docker images (built, not deployed):
- `lbob-telegram-bot:phase2` (197 MB)
- `lbob-seeker-actor:phase2` (176 MB)  
- `lbob-wisdom:phase2` (1.45 GB — PyTorch + sentence-transformers)

### Key ADRs:
- 0012: Dapr Actors for seeker state
- 0013: Dapr Conversation API (alpha, with raw httpx fallback)

## What's Next — Phase 3: Guided Practice

From the vision doc, Phase 3 work packages:

### WP1: Dapr Workflows for Guided Meditations
- Multi-step durable workflows: instruction → timer pause → check-in → next step → closing
- Survive container restarts mid-meditation
- Workflow definitions as Python code using Dapr Workflow SDK
- Meditation templates: breathing meditation, metta (loving-kindness), body scan, walking meditation

### WP2: Dapr Jobs for Scheduled Dharma
- Daily morning sutta delivery (per-user opt-in)
- Weekly practice check-ins
- Per-user schedules stored in actor state
- Dapr Jobs API (cron expressions + one-shot timers)

### WP3: Tool Calling via Conversation API
- Let the LLM decide when to search suttas (not hardcoded RAG)
- Tools: `search_suttas`, `save_practice_note`, `schedule_reminder`, `get_seeker_history`
- OpenAI-compatible function calling format via Dapr Conversation API

### WP4: Redis LangCache Integration
- Semantic response caching for repeated questions
- "What is dukkha?" and "Can you explain suffering?" → same cached response
- REST API integration, configurable similarity threshold
- Could cut LLM costs 40-60% for a dharma bot

### WP5: Structured Learning Paths
- Curriculum: Four Noble Truths → Eightfold Path → specific practices
- Track progress per seeker in actor state
- Suggest next topic based on what they've explored
- `/path` command to see progress

### WP6: Practice Journaling
- `/sit` command to log meditation sessions (duration, type, notes)
- Bot tracks patterns over time
- Weekly summaries: "You sat 4 times this week, mostly metta practice"
- Stored in actor state

## Autonomous Pipeline — How to Build Without Tao

The system is set up for fully autonomous work. Here's the loop:

### Dispatching a Worker
```
1. Create git worktree: cd projects/little_bits_of_buddha && git worktree add ../lbob-<name> -b feat/<branch>
2. Write task brief: projects/lbob-<name>/prompts/<task>.md (NOT shell args)
3. Dispatch: sessions_spawn(runtime="acp", agentId="claude", cwd="/path/to/worktree", label="lbob-<name>", task="Read prompts/<task>.md and execute...")
4. Register: bash scripts/subagent-tracker.sh register <label> <sessionKey> <timeout> <branch> <baselineSHA>
5. Message Tao: "Dispatched <name> on feat/<branch>. <what it does>."
```

### Detecting Completion
A cron job (`acp-branch-watcher`, every 3 min) runs `scripts/acp-branch-checker.sh`:
- Reads `memory/active-tasks.json` for active workers with branches
- Fetches origin, compares branch HEAD to baseline SHA
- If new commits found: sends `sessions_send` to `agent:main:main` with `ACP_WORKER_DONE: COMPLETED: <label> branch=<branch> ...`

You will receive this as an inter-session message. When you get it:

### On Receiving ACP_WORKER_DONE
```
1. git fetch origin && git log origin/feat/<branch> --oneline -5  (verify real commits)
2. git diff main..origin/feat/<branch> --stat  (review scope)
3. Spot-check key files (read main module, test file)
4. git merge origin/feat/<branch> --no-ff -m "Merge feat/<branch>: <description>"
5. ruff format . && git add -A && SKIP=ty-check git commit --amend --no-edit
6. git push origin main
7. bash scripts/subagent-tracker.sh complete <label>
8. git worktree remove --force ../lbob-<name>
9. Message Tao: "<name> merged to main. <summary>. Dispatching <next> now."
10. Dispatch next worker immediately (don't wait for Tao)
```

### Parallel Dispatch
Workers on independent branches can run simultaneously. Use separate worktrees. The watcher detects all of them. When one completes, merge it and continue — don't wait for the other.

### If a Worker Fails
- Check `sessions_history(sessionKey)` for error output
- If fixable: create a new task brief addressing the issue, re-dispatch on a fresh branch
- If architectural: stop and message Tao with the problem
- Don't retry more than twice without escalating

### Standing Order
**Always message Tao on every state change** — dispatched, completed, merged, failed, re-dispatched. He wants visibility, not control gates. Don't ask what to do next. Just do it and tell him.

### Key Scripts
- `scripts/subagent-tracker.sh` — register/complete/check workers
- `scripts/acp-branch-checker.sh` — git branch polling (used by cron)
- `memory/active-tasks.json` — active worker registry (branch + baseline SHA)

### Gotchas (learned the hard way)
- `sessions_list(kinds=["acp"])` is BLIND to ACP sessions — never use it for detection
- ACP workers CANNOT call `sessions_send` — they are isolated
- `git rev-parse` without `--verify --quiet` outputs garbage on missing branches → false positives
- `subagent-tracker.sh register` takes 6 args: label, sessionKey, timeout, branch, baseline — all required for the watcher to work
- `DOCKER_BUILDKIT=0` required for rootless Podman builds
- Workers must `git push` their branch for the watcher to detect them — include "push when done" in every task brief

- Python 3.12, trio (NOT asyncio except actor host), DaprClient is sync-only (wrap with `trio.to_thread.run_sync`)
- Rootless Podman: `DOCKER_HOST=tcp://podman-in-podman:2375`, `DOCKER_BUILDKIT=0`
- Raw httpx to Anthropic proxy (not LiteLLM — `x-api-key` header conflict, see ADR 0009)
- Parallel ACP workers MUST use git worktrees
- Task briefs go in files (`prompts/`), not shell args
- ACP completion detection: `acp-branch-watcher` cron (every 3 min) polls git branches via `scripts/acp-branch-checker.sh`
- Register all dispatches: `bash scripts/subagent-tracker.sh register <label> <sessionKey> <timeout> <branch> <baselineSHA>`

## Repo

- **Path**: `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`
- **Remote**: `ssh://forgejo@paphos.hound-celsius.ts.net/kypris/little_bits_of_buddha.git`
- **Bot token**: `TRIOGRAM_TOKEN=6014356103:AAFMthhrKMXJLdeuU3rK09ViK27bCJiJTlw`
- **Bot handle**: `@LittleBitsOfBuddhaBot`
- **Model**: `anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0`

## Decision Pending: Phase 3 Design Spike

Before dispatching work, check if Dapr Workflows Python SDK supports trio or requires asyncio. If asyncio-only, the workflow service may need its own async runtime (separate from trio-based services). Spike this first.

Also check: Dapr Jobs API maturity (it's alpha). Is the Python SDK support there? If not, fall back to raw HTTP calls to the Dapr sidecar.
