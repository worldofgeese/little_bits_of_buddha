# Phase 3 Plan — Guided Practice

> "The teacher who walks beside you."

## Overview

Phase 3 transforms LBOB from a conversational teacher into a practice guide — a bot that leads meditations, delivers daily suttas, tracks your sits, and adapts its curriculum to where you are on the path. The core technology shifts: **Dapr Workflows** for durable multi-step guided sessions, **Dapr Jobs** for scheduled delivery, and **tool calling** to let the LLM decide when to search suttas rather than hardcoding RAG.

**Prerequisites from Phase 2:**
- ✅ SeekerActor (stateful per-user identity)
- ✅ Wisdom Service (LLM + RAG + sutta vector search)
- ✅ Practice Level Detection (newcomer → experienced)
- ✅ 286 suttas, Docker images built
- ✅ Autonomous pipeline operational

## Design Spike Results (2026-03-05)

**Dapr Workflows Python SDK:** Generator-based (`yield ctx.call_activity(...)`), not async/await. Uses Durable Task Framework's own execution model. No trio/asyncio conflict — workflow service runs as a separate process.

**Dapr Jobs API:** Alpha (`v1.0-alpha1`). Python SDK has gRPC support. HTTP works for dev. Stable enough for daily sutta delivery + weekly check-ins.

**Dapr v1.17:** Workflow versioning, 41% throughput improvement, state retention policies. Production-ready.

**Decision:** Meditation workflow service = separate process. Activities are sync functions calling other services via Dapr service invocation.

---

## Architecture Changes

### Phase 2 (Current)
```
Telegram → pub/sub → seeker-actor-service → wisdom-service → pub/sub → Telegram
                         ↕                        ↕
                   Redis (actor state)      Redis (sutta vectors)
```

### Phase 3
```
Telegram → pub/sub → seeker-actor-service → wisdom-service → pub/sub → Telegram
                         ↕         ↕              ↕
                   Redis       meditation-    Redis (vectors + LangCache)
                   (state)     workflow-svc
                                   ↕
                              Dapr Workflows (durable state in Redis)
                              Dapr Jobs (scheduler → cron triggers)
```

New services:
- **meditation-workflow-service** — Dapr Workflow host + Jobs handler. Generator-based workflows for guided meditations. Activities call wisdom-service and seeker-actor-service via Dapr service invocation.

Existing service changes:
- **wisdom-service** — Add tool calling (search_suttas, save_practice_note, get_seeker_history). Add Redis LangCache for semantic response caching.
- **seeker-actor-service** — Add practice journal state, learning path progress, workflow instance tracking.
- **telegram-bot-service** — New commands: /meditate, /daily, /sit, /path, /journal.

---

## Work Packages

### WP1: Meditation Workflow Service (Dapr Workflows)
**Size: XL | Priority: P0 | Branch: `feat/meditation-workflows`**

New service: durable multi-step guided meditations.

**Files to create:**
- `src/meditation_workflow_service/__init__.py`
- `src/meditation_workflow_service/__main__.py` — FastAPI + WorkflowRuntime
- `src/meditation_workflow_service/workflows/breathing.py` — Breathing meditation workflow
- `src/meditation_workflow_service/workflows/metta.py` — Loving-kindness workflow
- `src/meditation_workflow_service/activities.py` — Shared activities (send_instruction, wait_timer, check_in, get_seeker_state)
- `src/meditation_workflow_service/templates.py` — Meditation template definitions
- `src/meditation_workflow_service/requirements.txt`
- `tests/test_meditation_workflows.py`

**Workflow pattern (breathing meditation):**
```python
@wfr.workflow(name='breathing_meditation')
def breathing_meditation(ctx: DaprWorkflowContext, input):
    # 1. Send welcome + posture instruction
    yield ctx.call_activity(send_instruction, input={"chat_id": input["chat_id"], "step": "welcome"})
    
    # 2. Wait 30s for settling
    yield ctx.create_timer(timedelta(seconds=30))
    
    # 3. Send breathing focus instruction
    yield ctx.call_activity(send_instruction, input={"chat_id": input["chat_id"], "step": "breathing_focus"})
    
    # 4. Main meditation timer (configurable, default 5 min)
    yield ctx.create_timer(timedelta(minutes=input.get("duration_min", 5)))
    
    # 5. Gentle bell + check-in question
    yield ctx.call_activity(send_instruction, input={"chat_id": input["chat_id"], "step": "checkin"})
    
    # 6. Wait for external event (user response) with timeout
    event = ctx.wait_for_external_event("checkin_response")
    timeout = ctx.create_timer(timedelta(minutes=5))
    winner = yield when_any([event, timeout])
    
    # 7. Closing instruction + sutta suggestion
    response = winner if winner != timeout else None
    yield ctx.call_activity(close_meditation, input={"chat_id": input["chat_id"], "response": response})
```

**Activities (sync functions, called by workflows):**
- `send_instruction(ctx, input)` — Calls telegram-bot-service via Dapr to send a message to the seeker
- `wait_for_response(ctx, input)` — Handled via external events (workflow pauses, Telegram handler raises event)
- `close_meditation(ctx, input)` — Sends closing message, logs sit to actor state, suggests relevant sutta via wisdom-service
- `get_seeker_state(ctx, input)` — Reads seeker actor state to personalize instructions

**Dapr components:**
- `.dapr/components/workflow.yaml` — Workflow component (uses actor state store)
- Update `compose.yaml` with meditation-workflow-service + sidecar

**Meditation templates (Phase 3 scope):**
1. **Breathing meditation** (ānāpānasati) — 5/10/15/20 min
2. **Metta (loving-kindness)** — guided phrases, expanding circles
3. **Body scan** — sequential attention through body parts
4. **Walking meditation** — instruction-only (no timer, just guidance)

**Constraints:**
- Workflows are generators (yield), NOT async/await
- Activities are sync functions — use `httpx` (sync) for Dapr service invocation within activities
- Workflow service is a SEPARATE process from trio-based services
- External events bridge Telegram messages to paused workflows

**Tests (TDD — failing first):**
- Test breathing workflow end-to-end (mock activities)
- Test timer behavior (mock `create_timer`)
- Test external event handling + timeout fallback
- Test metta workflow phrase progression
- Test workflow survives "restart" (replay from checkpoint)

**ADR:** `0014-dapr-workflows-for-guided-meditation.md`

---

### WP2: Dapr Jobs for Scheduled Delivery
**Size: L | Priority: P1 | Branch: `feat/scheduled-delivery`**

Daily morning sutta delivery and weekly practice check-ins, per-user opt-in.

**Changes:**
- `src/meditation_workflow_service/jobs.py` — Job handler (receives Dapr Job callbacks)
- `src/seeker_actor_service/seeker_actor.py` — Add `schedule_preferences` to actor state
- `tests/test_scheduled_delivery.py`

**Jobs:**
1. **Daily sutta** — Opt-in via `/daily on`. Dapr Job with `@daily` schedule per user. Callback selects a sutta matching the seeker's level + unexplored topics, sends via Telegram.
2. **Weekly check-in** — Opt-in. Sends "How has your practice been this week?" + summary of sits logged.

**Dapr components:**
- `.dapr/components/scheduler.yaml` — Scheduler component config
- Jobs registered via `DaprClient.schedule_job()` (gRPC) or HTTP fallback

**Per-user schedule storage:**
```python
# Added to SeekerState
schedule_preferences: dict = {
    "daily_sutta": False,       # opt-in
    "daily_sutta_time": "07:00", # local time (UTC offset stored)
    "weekly_checkin": False,
    "timezone": "UTC"
}
```

**Constraints:**
- Jobs API is alpha — use gRPC SDK if available, HTTP fallback if not
- One Dapr Job per user per schedule type (job name: `daily-sutta-{chat_id}`)
- Jobs survive container restarts (Dapr Scheduler persists them)

**Tests:**
- Test job registration creates correct schedule
- Test job callback selects appropriate sutta for level
- Test opt-in/opt-out state management
- Test weekly summary generation

---

### WP3: Tool Calling via Wisdom Service
**Size: M | Priority: P1 | Branch: `feat/tool-calling`**

Let the LLM decide when to search suttas instead of hardcoding RAG on every message.

**Changes:**
- `src/wisdom_service/__main__.py` — Add tool definitions to LLM call
- `src/wisdom_service/tools.py` — Tool implementations
- `tests/test_tool_calling.py`

**Tools:**
1. `search_suttas(query: str, limit: int = 3)` — Semantic sutta search (already exists as RAG, now callable by LLM)
2. `save_practice_note(chat_id: str, note: str)` — Save a note to seeker's practice journal
3. `schedule_reminder(chat_id: str, type: str, time: str)` — Schedule a Dapr Job for the seeker
4. `get_seeker_history(chat_id: str, last_n: int = 5)` — Get recent conversation context

**Implementation:**
- Use Anthropic function calling format (tool_use / tool_result blocks)
- Raw httpx to Anthropic proxy (consistent with existing pattern)
- Iterative tool use: LLM calls tool → get result → LLM generates final response
- Fallback: if tool calling fails, fall back to mandatory RAG (current behavior)

**Constraints:**
- Keep mandatory RAG as fallback — tool calling enhances, doesn't replace
- Max 3 tool calls per turn (prevent runaway loops)
- Tool results must be concise (summarize sutta, don't send full text to LLM)

**Tests:**
- Test tool definition format
- Test LLM tool call parsing
- Test tool execution + result injection
- Test fallback to mandatory RAG on tool failure
- Test max tool call limit

---

### WP4: Redis LangCache
**Size: S | Priority: P2 | Branch: `feat/langcache`**

Semantic response caching — "What is dukkha?" and "Can you explain suffering?" → same cached response.

**Changes:**
- `src/wisdom_service/langcache.py` — LangCache client
- `src/wisdom_service/__main__.py` — Check cache before LLM call, store after
- `.dapr/components/` — Redis LangCache config (if Dapr component exists) or direct Redis connection
- `tests/test_langcache.py`

**Implementation:**
- Embed query with same model as sutta search (all-MiniLM-L6-v2)
- Store: `{query_embedding, response, practice_level, timestamp}`
- Lookup: cosine similarity > 0.92 threshold + same practice_level → cache hit
- Cache per practice_level (beginner gets different answer than experienced)
- TTL: 7 days (Dharma doesn't change, but our prompts might)

**Constraints:**
- Check Redis LangCache module availability first — if not available, use plain Redis with manual vector similarity
- Don't cache tool-calling responses (they may reference user-specific state)
- Cache key includes practice_level

**Tests:**
- Test cache miss → LLM call → cache store
- Test cache hit with similar query
- Test practice_level isolation
- Test TTL expiration
- Test threshold sensitivity

---

### WP5: Structured Learning Paths
**Size: M | Priority: P2 | Branch: `feat/learning-paths`**

Curriculum tracking: Four Noble Truths → Eightfold Path → specific practices.

**Changes:**
- `src/seeker_actor_service/learning_paths.py` — Path definitions + progress tracking
- `src/seeker_actor_service/seeker_actor.py` — Add `path_progress` to state
- `tests/test_learning_paths.py`

**Curriculum (Early Buddhism, progressive):**
```
1. The Four Noble Truths
   1.1 Dukkha (suffering/unsatisfactoriness)
   1.2 Samudaya (origin of dukkha — craving)
   1.3 Nirodha (cessation)
   1.4 Magga (the path)
2. The Noble Eightfold Path
   2.1 Right View (sammā diṭṭhi)
   2.2 Right Intention (sammā saṅkappa)
   2.3 Right Speech (sammā vācā)
   2.4 Right Action (sammā kammanta)
   2.5 Right Livelihood (sammā ājīva)
   2.6 Right Effort (sammā vāyāma)
   2.7 Right Mindfulness (sammā sati)
   2.8 Right Concentration (sammā samādhi)
3. Meditation Practices
   3.1 Ānāpānasati (breathing)
   3.2 Mettā bhāvanā (loving-kindness)
   3.3 Body contemplation
   3.4 Walking meditation
4. Key Doctrines
   4.1 Dependent Origination (paṭiccasamuppāda)
   4.2 Three Marks of Existence
   4.3 Five Aggregates (khandhas)
```

**Progress tracking:**
- Each topic: `not_started | introduced | explored | practiced`
- Topics marked `introduced` when the LLM discusses them (detected via themes from wisdom-service)
- Topics marked `explored` after 3+ conversations touching them
- Topics marked `practiced` only for meditation topics, after logged sits

**`/path` command:** Shows current progress as a visual map.

**Tests:**
- Test curriculum structure
- Test progress transitions
- Test topic suggestion logic (next unexplored topic)
- Test /path command output

---

### WP6: Practice Journaling
**Size: S | Priority: P2 | Branch: `feat/practice-journal`**

`/sit` command to log meditation sessions + weekly summaries.

**Changes:**
- `src/seeker_actor_service/seeker_actor.py` — Add `practice_journal` to state
- `src/telegram_bot_service/__main__.py` — Add /sit and /journal commands
- `tests/test_practice_journal.py`

**Journal entry:**
```python
class SitEntry:
    timestamp: datetime
    duration_minutes: int
    practice_type: str  # "breathing" | "metta" | "body_scan" | "walking" | "other"
    notes: str | None
    from_workflow: bool  # True if logged automatically after guided meditation
```

**Commands:**
- `/sit 20 breathing` — Log a 20-min breathing meditation
- `/sit 10 metta "Focused on family"` — With notes
- `/journal` — Show last 7 days of practice
- `/journal week` — Weekly summary with patterns

**Weekly summary (generated by LLM):**
> "You sat 4 times this week — mostly breathing practice, averaging 15 minutes. Your longest sit was 25 minutes on Tuesday. You might enjoy trying metta practice next."

**Constraints:**
- Automatic logging after guided meditations (WP1 close_meditation activity)
- Journal entries stored in actor state (capped at 90 days)
- Weekly summary uses wisdom-service LLM call with journal data as context

**Tests:**
- Test /sit parsing (duration, type, notes)
- Test journal entry storage + retrieval
- Test weekly summary generation
- Test automatic logging from workflow
- Test 90-day cap (oldest entries pruned)

---

## New Telegram Commands (all WPs)

| Command | WP | Description |
|---------|-----|-------------|
| `/meditate [type] [duration]` | WP1 | Start a guided meditation |
| `/daily on/off` | WP2 | Toggle daily sutta delivery |
| `/sit [min] [type] [notes]` | WP6 | Log a meditation session |
| `/path` | WP5 | Show learning path progress |
| `/journal [week]` | WP6 | View practice journal |

---

## Dependency Graph

```
WP4 (langcache) ─────────────────────────────────┐
WP6 (journaling) ────────────────────────────────┐│
                                                  ││
WP1 (workflows) ──→ WP2 (jobs, needs workflow svc)│├──→ Integration testing
                ──→ WP3 (tool calling)    ────────┘│
                ──→ WP5 (learning paths)  ─────────┘
```

**Parallel group 1 (no deps):** WP1 + WP4 + WP6
**Parallel group 2 (after WP1 skeleton):** WP2 + WP3 + WP5
**Final:** Integration testing + Telegram commands + compose update

---

## Sequencing

| Wave | WPs | Can parallelize | Est. effort |
|------|-----|----------------|-------------|
| 1 | WP1 (workflows) + WP4 (langcache) + WP6 (journaling) | All three | 6-8h + 2-3h + 2-3h |
| 2 | WP2 (jobs) + WP3 (tool calling) + WP5 (learning paths) | All three | 3-4h + 3-4h + 3-4h |
| 3 | Integration + Telegram commands + compose | Serial | 3-4h |

**Total estimate:** 22-30 hours worker time. With parallel dispatch: ~10-14 hours wall clock.

---

## Decisions

1. **Separate workflow service process.** Dapr Workflows use generator-based execution (Durable Task Framework). No trio/asyncio conflict because it's a separate process. Activities call other services via Dapr service invocation.

2. **Jobs API via HTTP fallback if gRPC SDK incomplete.** Alpha API but stable enough. HTTP for dev, migrate to gRPC when SDK matures.

3. **Tool calling enhances, doesn't replace, RAG.** Fallback to mandatory RAG if tool calling fails. The LLM should *choose* to search, but always has suttas available.

4. **LangCache per practice_level.** A beginner and an experienced practitioner asking the same question get different cached responses.

5. **90-day journal cap.** Actor state shouldn't grow unbounded. Oldest entries pruned.

6. **Proactive outreach is opt-in only.** `/daily on` explicitly. The Buddha does not nudge — the seeker chooses.

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Workflow replay determinism bugs | High — meditation restarts mid-session | Extensive replay tests. Dapr v1.17 has workflow versioning if we need to patch. |
| Jobs API breaking changes (alpha) | Medium | HTTP fallback. Thin wrapper for easy migration. |
| Tool calling latency (multi-turn LLM) | Medium — adds 1-2s per tool call | Max 3 tool calls per turn. Parallel tool execution where possible. |
| LangCache false positives | Low — wrong cached answer served | Conservative threshold (0.92). Practice_level isolation. Easy to tune. |
| Actor state bloat (journal + paths) | Low | 90-day cap. Periodic compaction in Phase 4 if needed. |

---

## Autonomous Pipeline Notes

Same pipeline as Phase 2 — proven and operational:
1. Create git worktree per worker
2. Write task brief to `prompts/`
3. `sessions_spawn(runtime="acp")` → register with tracker
4. `acp-branch-watcher` cron detects completion
5. Verify → merge → push → dispatch next
6. Message Tao on every state change

Three workers can run in parallel (Wave 1). Start with WP1 + WP4 + WP6.
