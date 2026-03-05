# Phase 2 Plan — Actors & Personality

> "The bot that knows you."

## Overview

Phase 2 transforms LBOB from a stateless RAG chatbot into a personalized teacher that remembers each seeker, adapts its tone, and can proactively reach out. The core technology shift: **Dapr Virtual Actors** replace the current flat state-store pattern, giving each Telegram user a persistent, lifecycle-managed identity inside the system.

**Prerequisites from Phase 1:**
- ✅ Dapr state store (Redis) for conversation history
- ✅ RAG pipeline (sutta vector search → context injection → LLM)
- ✅ Rate limiting per user
- ✅ 286 curated suttas from SuttaCentral

**What Phase 2 adds:**
- Dapr Actors: one per seeker, holding state + practice level + preferences
- Actor timers: daily mindfulness prompts, practice reminders
- Adaptive tone: detect beginner vs practitioner from conversation patterns
- Multi-tradition routing (stretch goal): Theravada, Zen, secular

---

## Architecture Changes

### Current (Phase 1)

```
Telegram → pub/sub → openai-service (stateless handler) → pub/sub → Telegram
                          ↕
                    Redis (state store: flat key "seeker:{chat_id}")
                    Redis (vector search: sutta_idx)
```

### Phase 2

```
Telegram → pub/sub → seeker-actor-service (Dapr Actor host)
                          ↕
                    Dapr Actor runtime (manages SeekerActor per chat_id)
                          ↕
                    Redis (actor state: practice level, preferences, history)
                          ↓
                    wisdom-service (LLM + RAG, extracted from openai-service)
                          ↕
                    Redis (vector search: sutta_idx)
                          ↓
                    pub/sub → Telegram
```

Key change: **openai-service splits into two services:**
1. **seeker-actor-service** — hosts Dapr Actors, manages per-user state and lifecycle
2. **wisdom-service** — pure LLM inference + RAG (stateless, called by actors via Dapr service invocation)

This split is necessary because Dapr Actors require a dedicated actor host process, and mixing actor hosting with LLM inference (which has long response times) would block actor method calls.

---

## Work Packages

### WP1: SeekerActor — Core Actor Implementation
**Size: L | Priority: P0 | Branch: `feat/seeker-actor`**

Create the Dapr Actor that represents a seeker (user).

**Files to create:**
- `src/seeker_actor_service/__init__.py`
- `src/seeker_actor_service/__main__.py` — FastAPI app hosting the actor
- `src/seeker_actor_service/seeker_interface.py` — ActorInterface definition
- `src/seeker_actor_service/seeker_actor.py` — Actor implementation
- `src/seeker_actor_service/requirements.txt`

**Actor state schema:**
```python
class SeekerState:
    chat_id: str
    practice_level: str  # "newcomer" | "beginner" | "intermediate" | "experienced"
    tradition: str  # "theravada" (default) | "zen" | "secular"
    conversation_count: int
    topics_explored: list[str]  # theme tags from suttas discussed
    last_active: datetime
    preferences: dict  # tone, verbosity, etc.
    history: list[dict]  # last N messages (moved from flat state store)
```

**Actor methods:**
- `receive_message(text: str) -> str` — Main entry point. Loads state, calls wisdom-service, saves state, returns response.
- `get_state() -> SeekerState` — Read current seeker state.
- `update_practice_level(level: str)` — Manual override.
- `set_tradition(tradition: str)` — User preference.
- `get_summary() -> dict` — Returns conversation stats for the seeker.

**Constraints:**
- Actor methods are `async` but DaprClient is sync → use `trio.to_thread.run_sync` (consistent with Phase 1 pattern)
- Actor host must use FastAPI + DaprApp (required by `dapr-ext-fastapi`)
- Actor state is automatically persisted by Dapr to Redis state store

**Tests:**
- Use `create_mock_actor` from `dapr.actor.runtime.mock_actor`
- Test state transitions (newcomer → beginner after 5 conversations)
- Test that `receive_message` calls wisdom-service and saves state
- Test practice level detection heuristic

**ADR:** `0012-dapr-actors-for-seeker-state.md` — Why actors over flat state store (lifecycle management, single-threaded guarantees, timer support)

---

### WP2: Wisdom Service — Extract LLM/RAG into Standalone Service
**Size: M | Priority: P0 | Branch: `feat/wisdom-service`**

Extract the LLM call + RAG pipeline from `openai-service` into a new `wisdom-service` that actors call via Dapr service invocation.

**Files to create:**
- `src/wisdom_service/__init__.py`
- `src/wisdom_service/__main__.py` — FastAPI app with `/wisdom/ask` endpoint
- `src/wisdom_service/requirements.txt`

**Files to move/refactor:**
- `src/openai_service_worldofgeese/rag.py` → `src/wisdom_service/rag.py`
- `src/openai_service_worldofgeese/sutta_search.py` → `src/wisdom_service/sutta_search.py`
- `src/openai_service_worldofgeese/__main__.py` → delete (replaced by actor + wisdom)

**API:**
```
POST /wisdom/ask
{
    "chat_id": "12345",
    "message": "What is the cause of suffering?",
    "context": {
        "practice_level": "beginner",
        "tradition": "theravada",
        "history": [...last 10 messages...],
        "topics_explored": ["four noble truths"]
    }
}
→ { "response": "...", "suttas_cited": ["SN56.11"], "detected_themes": ["suffering", "craving"] }
```

The wisdom service is stateless — all seeker context is passed in by the actor. This makes it independently scalable and testable.

**System prompt adaptation (based on practice_level):**
- `newcomer`: Simple language, define Pali terms, encourage questions, no assumptions about practice. "You are a patient teacher speaking to someone encountering the Dhamma for the first time."
- `beginner`: Can use basic terms (dukkha, sila, metta), reference practice. "You are a kind teacher speaking to a new practitioner."
- `intermediate`: Assume familiarity with core doctrines, can discuss subtleties. "You speak as the Tathagata to a sincere practitioner."
- `experienced`: Full Pali terminology, direct pointing, fewer explanations. "You speak as the Tathagata to an experienced practitioner of the path."

**Tests:**
- Test endpoint returns valid response format
- Test system prompt changes with practice level
- Test sutta citation extraction
- Test graceful degradation when Redis is down (no sutta context, still responds)

---

### WP3: Practice Level Detection
**Size: S | Priority: P1 | Branch: `feat/practice-level`**

Heuristic to detect and update a seeker's practice level based on conversation patterns.

**File:** `src/seeker_actor_service/level_detector.py`

**Signals (scored, not binary):**
- **Vocabulary signal:** Use of Pali terms (dukkha, anicca, anatta, sati, samadhi, jhana, vipassana, metta, upekkha, sila, panna) → higher level
- **Question complexity:** "What is meditation?" (newcomer) vs "How does the second jhana differ from the first?" (experienced)
- **Reference to practice:** "I've been meditating for..." → at least beginner
- **Topic depth:** Asking about dependent origination vs asking about basic ethics
- **Conversation count:** Threshold-based floor (0-2: newcomer, 3-10: beginner minimum, 10+: intermediate minimum)

**Rules:**
- Level can only go UP, never down (you don't un-learn the Dhamma)
- Level changes require 3+ signals at the new level (avoid premature promotion from a single question)
- Actor stores the signal history to make decisions over multiple conversations

**Tests:**
- Test vocabulary scoring with known Pali terms
- Test conversation count thresholds
- Test that level never decreases
- Test multi-signal requirement

---

### WP4: Actor Timers — Daily Reminders
**Size: M | Priority: P1 | Branch: `feat/actor-timers`**

Dapr Actor timers to send proactive messages.

**Reminder types:**
1. **Daily practice prompt** — Short quote or teaching, different each day. Drawn from sutta corpus. Sent at user's preferred time (default: 7 AM).
2. **Follow-up** — "Last time we spoke about [topic]. Have you had time to reflect on it?" Sent 24-48 hours after last conversation.
3. **Gentle return** — "It's been a while since we last spoke. The path is always here." Sent after 7+ days of inactivity.

**Implementation:**
- Use `self.register_timer(name, callback, due_time, period)` in actor
- Timer fires → actor method generates message → publishes to `responses` topic → Telegram delivers
- User can opt out: `/silence` command disables all timers, `/remind` re-enables
- Timer state persisted in actor state (active timers, preferred send time, opt-out flag)

**Constraints:**
- Dapr actor timers survive container restarts (Dapr re-registers them)
- Timer callbacks must be idempotent (Dapr may fire them more than once)
- Must respect Telegram rate limits (not more than 30 messages/second globally)

**New Dapr component:** None — timers are built into the actor runtime. But need to configure actor idle timeout in Dapr config to prevent actors with active timers from being deactivated.

**Tests:**
- Test timer registration on first conversation
- Test opt-out disables timer
- Test follow-up content references last discussed topic
- Test idle detection (7+ days)

---

### WP5: Compose & Infrastructure Updates
**Size: M | Priority: P0 | Branch: `feat/phase2-infra`**

Update `compose.yaml`, Dockerfiles, and Dapr config for the new service topology.

**Changes to `compose.yaml`:**
- Remove: `openai-service` + `openai-dapr`
- Add: `seeker-actor-service` + `seeker-actor-dapr`
- Add: `wisdom-service` + `wisdom-dapr`
- Update Dapr sidecar configs:
  - `seeker-actor-dapr`: needs `--app-id=seeker-actor-service`, actor placement tables
  - `wisdom-dapr`: needs `--app-id=wisdom-service`, no actors

**New Dapr components:**
- `.dapr/components/actor-config.yaml` — Actor idle timeout, reentrancy settings
- Update `.dapr/components/statestore.yaml` — Actor state store config (same Redis, Dapr handles actor key prefixing)

**Dockerfile changes:**
- New build targets: `seeker-actor-service-production`, `wisdom-service-production`
- Wisdom service gets: sutta_corpus, sentence-transformers, torch (CPU), redis, httpx
- Seeker actor service gets: dapr, dapr-ext-fastapi, httpx (for service invocation), trio

**Migration:**
- Existing seeker state keys (`seeker:{chat_id}`) need migration to actor state format
- Write `scripts/migrate_state_to_actors.py` — reads old format, writes new format
- Run once during deployment, then delete old keys

---

### WP6: Telegram Service Updates
**Size: S | Priority: P1 | Branch: `feat/telegram-phase2`**

Update `telegram-bot-service` for new commands and actor interaction.

**New commands:**
- `/start` — Activates seeker actor, sends welcome message
- `/level` — Shows current practice level
- `/tradition [theravada|zen|secular]` — Sets preferred tradition
- `/silence` / `/remind` — Toggle daily reminders
- `/forget` — Clears conversation history (GDPR-friendly)

**Changes:**
- Messages now go to pub/sub as before, but the subscriber is the actor service (not openai-service)
- Response flow unchanged: `responses` topic → Telegram
- Command messages (starting with `/`) intercepted before pub/sub

---

## Dependency Graph

```
WP5 (infra) ─────────┐
                      ├──→ WP1 (actor) ──→ WP2 (wisdom) ──→ Integration testing
WP3 (level detect) ───┘         │
                                ├──→ WP4 (timers)
WP6 (telegram cmds) ────────────┘
```

**Critical path:** WP5 → WP1 → WP2 → integration test
**Parallel work:** WP3 can start immediately (pure logic, no infra deps). WP6 can start after WP1 skeleton exists.

---

## Sequencing

| Order | WP | Can parallelize with | Est. effort |
|-------|-----|---------------------|-------------|
| 1 | WP5 (infra) | WP3 (level detect) | 2-3 hours |
| 2 | WP1 (actor) | WP6 (telegram cmds) | 4-6 hours |
| 3 | WP2 (wisdom) | WP4 (timers) | 3-4 hours |
| 4 | WP4 (timers) | — | 2-3 hours |
| 5 | Integration test + migration | — | 2-3 hours |

**Total estimate:** 13-19 hours of worker time. With parallel dispatch: ~8-12 hours wall clock.

---

## Decisions to Make

1. **Dapr Conversation API** — Currently alpha. Vision doc lists it for Phase 2, but it's not stable. **Recommendation: Skip it.** Keep raw httpx to Anthropic proxy (ADR 0009 still applies). Revisit when Conversation API hits beta.

2. **Multi-tradition routing** — Full implementation (separate services per tradition) is Phase 3 complexity disguised as Phase 2. **Recommendation: Phase 2 does tradition as a system prompt variation only** (same wisdom service, different prompt prefix). Separate services deferred to Phase 3.

3. **Actor placement service** — For single-node deployment, Dapr's default placement service works. If we ever scale to multiple nodes, we'll need the placement service as a separate container. **Recommendation: Use default placement for now.** Add `dapr-placement` container to compose only if needed.

4. **State migration strategy** — Existing users have state in `seeker:{chat_id}` format. **Recommendation: Write migration script in WP5, run as one-time job.** No backward compatibility layer — clean cut.

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Dapr actor + trio incompatibility | High — actors are async but our stack is trio | Spike in WP1: verify `trio.to_thread.run_sync` works inside actor methods. Fallback: actor host runs on asyncio (separate from trio-based services) |
| Timer reliability on container restart | Medium — missed reminders | Test explicitly in WP4. Dapr should re-register timers but verify with podman restart cycle |
| LLM latency blocks actor methods | Medium — actor method timeout | WP2 extraction solves this: actor makes async service invocation call, doesn't block on LLM |
| sutta_corpus too large for wisdom-service cold start | Low — 286 suttas, ~1.5MB | Embed on startup, cache in Redis. Already works in Phase 1. |

---

## Out of Scope (Phase 3)

- Dapr Workflows for guided meditations
- Structured learning paths
- Practice journaling
- Redis TimeSeries analytics
- Separate tradition services (beyond prompt variation)
- Dapr Conversation API integration
