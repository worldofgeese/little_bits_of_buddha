# ADR 0012: Dapr Virtual Actors for Seeker State Management

**Status:** Accepted

**Date:** 2026-03-05

**Context:** Phase 2 — Actors & Personality

## Decision

We are replacing the flat Redis state store pattern (`seeker:{chat_id}` keys) with **Dapr Virtual Actors** to represent each seeker (Telegram user) in Little Bits of Buddha.

Each Telegram user will have a corresponding `SeekerActor` instance hosted in the `seeker-actor-service`. The actor encapsulates:
- Conversation history
- Practice level (newcomer → beginner → intermediate → experienced)
- Topics explored (theme tags from suttas discussed)
- User preferences (tone, verbosity)
- Last active timestamp

## Context

### Phase 1 State Management

In Phase 1, we stored seeker state as flat Redis keys:

```python
key = f"seeker:{chat_id}"
value = json.dumps(conversation_history)  # List of message dicts
```

**Problems with this approach:**

1. **No lifecycle management** — State persists indefinitely. No automatic activation, deactivation, or cleanup.

2. **No single-threaded guarantees** — Concurrent requests for the same seeker could result in race conditions when reading and writing state. We'd need application-level locking.

3. **State logic scattered** — Conversation history management, rate limiting, practice level detection, and response generation are all mixed in the `openai-service`.

4. **No support for timers or reminders** — If we want proactive features in Phase 3 (reminder timers, scheduled reflections), we'd need to build a separate scheduling system.

5. **Scalability challenges** — As we add features (journaling, structured learning paths), the flat key-value pattern doesn't scale well. We'd end up with multiple keys per user (`seeker:{chat_id}:history`, `seeker:{chat_id}:level`, etc.) and complex coordination logic.

### Why Dapr Actors?

Dapr Virtual Actors solve these problems by providing:

1. **Lifecycle Management**
   - Actors are activated on-demand when a message arrives
   - Dapr handles actor placement across instances (for future horizontal scaling)
   - Actors can be deactivated after idle periods (configurable)
   - State is automatically persisted and restored by Dapr runtime

2. **Single-Threaded Execution**
   - Actor methods are executed serially, even if multiple requests arrive concurrently
   - No need for application-level locking or concurrency control
   - Simplifies state mutation logic

3. **Encapsulation**
   - All seeker-specific state and behavior is encapsulated in the `SeekerActor` class
   - Clear separation of concerns: actor manages state, wisdom-service handles LLM/RAG
   - Easier to test, reason about, and extend

4. **Foundation for Future Features**
   - **Timers:** Actors support Dapr timers for proactive features (Phase 3)
   - **Reminders:** Durable reminders survive actor deactivation
   - **State versioning:** Actor state can evolve over time with migration logic
   - **Multi-instance scaling:** Dapr placement service automatically distributes actors

5. **Observability**
   - Dapr provides built-in metrics for actor invocations, state operations, timers
   - Actor method calls are traced end-to-end via Dapr telemetry
   - Easier to monitor per-user behavior and debug issues

## Consequences

### Positive

- **Simplified concurrency model:** Single-threaded actor methods eliminate race conditions
- **Clear architecture:** One actor per user, one service for LLM/RAG
- **Future-proof:** Timers and reminders come for free when needed
- **Dapr-native:** Leverages Dapr runtime for state management, placement, lifecycle

### Negative

- **Learning curve:** Developers must understand the Dapr actor model
- **Deployment complexity:** Requires actor-enabled Dapr sidecars and state store configuration
- **Migration overhead:** One-time migration from Phase 1 keys to actor state (handled by `scripts/migrate_state_to_actors.py`)
- **Trio compatibility:** Actor methods are `async`, but Dapr Python SDK uses asyncio. We use `trio.to_thread.run_sync` to bridge the gap (same pattern as Phase 1 for `httpx` calls).

### Neutral

- **State store unchanged:** Still using Redis, just with Dapr actor key format (`actors||SeekerActor||{chat_id}||state`)
- **No immediate horizontal scaling:** Single-node deployment doesn't need Dapr placement service yet. But the foundation is ready when we do.

## Implementation Notes

### Actor State Schema

```python
class SeekerState:
    chat_id: str
    practice_level: str  # "newcomer" | "beginner" | "intermediate" | "experienced"
    conversation_count: int
    topics_explored: list[str]  # Theme tags from suttas
    last_active: str  # ISO 8601 timestamp
    preferences: dict  # Tone, verbosity, etc.
    history: list[dict]  # Conversation messages
```

### Actor Methods

- `receive_message(text: str) -> str` — Main entry point from pub/sub
- `get_state() -> SeekerState` — Read current state
- `update_practice_level(level: str)` — Manual override
- `get_summary() -> dict` — Stats for the user

### Service Topology

Phase 1:
```
Telegram → pub/sub → openai-service (stateless handler)
                          ↕
                    Redis (flat keys)
```

Phase 2:
```
Telegram → pub/sub → seeker-actor-service (hosts SeekerActor)
                          ↕
                    Dapr Actor runtime → Redis (actor state)
                          ↓
                    wisdom-service (LLM + RAG, stateless)
```

### Migration

Run `scripts/migrate_state_to_actors.py` once during Phase 2 deployment:

```bash
python scripts/migrate_state_to_actors.py --redis-host lbob-redis --redis-port 6379
```

This script:
1. Scans for `seeker:*` keys
2. Reads conversation history from each key
3. Creates actor state with default practice level ("newcomer")
4. Writes to Dapr actor key format
5. Does NOT delete old keys (manual cleanup after verification)

## Alternatives Considered

### 1. Keep Flat State Store + Add Locking

**Rejected:** Adds complexity without solving lifecycle or timer problems. Would need distributed locks (Redis Redlock, Dapr distributed lock) and careful lock management. Doesn't prepare us for future features.

### 2. Use Dapr Workflow Instead

**Rejected for now:** Dapr Workflow is better for long-running, multi-step processes (e.g., guided meditations, structured learning paths). For conversational state, actors are a better fit. We may use Workflow in Phase 3 for specific features.

### 3. Custom Actor-like System

**Rejected:** Reinventing what Dapr actors already provide. Higher maintenance burden, less observability, no community support.

## Related ADRs

- **ADR 0009:** Raw httpx for Anthropic proxy (replaced by ADR 0013 with Dapr Conversation API)
- **ADR 0013** (future): Dapr Conversation API for LLM calls

## References

- [Dapr Virtual Actors Documentation](https://docs.dapr.io/developing-applications/building-blocks/actors/actors-overview/)
- [Dapr Actor State Store Configuration](https://docs.dapr.io/reference/components-reference/supported-state-stores/)
- Phase 2 Plan: `/phase2-plan.md`
