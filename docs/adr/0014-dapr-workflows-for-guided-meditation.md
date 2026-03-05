# ADR 0014: Dapr Workflows for Guided Meditation

**Status:** Accepted

**Date:** 2026-03-05

**Context:** Phase 3 — Guided Practice

## Decision

We are implementing **Dapr Workflows** to orchestrate multi-step guided meditation sessions in Little Bits of Buddha.

Guided meditations (breathing meditation, metta practice) will be implemented as **generator-based workflows** in a new `meditation-workflow-service`. Each meditation session is a durable workflow that can survive container restarts and coordinate multiple activities over extended periods (5-20 minutes).

## Context

### Requirements for Guided Meditation

Little Bits of Buddha aims to offer guided meditation practice rooted in the Pali Canon:

1. **Breathing meditation (ānāpānasati):** Multi-phase guided sit with:
   - Welcome message adapted to practice level
   - 30-second settling period
   - Breathing focus instruction
   - Main meditation timer (5/10/15/20 minutes)
   - Check-in bell with optional user response
   - Closing + practice logging + sutta suggestion

2. **Metta (loving-kindness) meditation:** Sequential phases:
   - Self-directed metta (2 min)
   - Loved one (2 min)
   - Neutral person (2 min)
   - Difficult person (2 min)
   - All beings (3 min)
   - Closing + practice logging + sutta suggestion

### Why Not Just Use Actors?

We already have Dapr Actors (`SeekerActor`) for per-user state. Why add Workflows?

**Actors are state machines; Workflows are orchestrators.**

If we tried to implement guided meditation in actors:

1. **Complex state management:** We'd need to manually track "current meditation phase", "timer expiry time", "waiting for user response", etc. in actor state. This quickly becomes error-prone.

2. **Timer coordination:** Actors support Dapr timers, but coordinating multiple sequential timers (settle → main period → check-in timeout) requires explicit state transitions and timer cleanup logic.

3. **No natural sequencing:** Actor methods don't have built-in sequencing semantics. We'd need a state machine pattern with explicit phase transitions, making the code harder to read and maintain.

4. **Long-running blocking:** Waiting for external events (user responses) while keeping actor state consistent requires careful design. We'd need to store "waiting_for_event" flags and handle event arrival in separate method calls.

5. **No retry/compensation logic:** If a step fails (e.g., wisdom service is down when fetching sutta suggestion), actors don't provide automatic retry or compensation patterns.

### Why Dapr Workflows?

Dapr Workflows provide **durable orchestration** with built-in primitives for:

1. **Sequential execution:** Workflows are expressed as linear code (generators in Python). Each step is a `yield` statement. The workflow runtime handles sequencing automatically.

   ```python
   # Natural sequential flow
   yield ctx.call_activity("send_welcome")
   yield ctx.create_timer(timedelta(seconds=30))
   yield ctx.call_activity("send_focus_instruction")
   yield ctx.create_timer(timedelta(minutes=duration))
   ```

2. **Timers:** First-class support for durable timers. If the container restarts mid-meditation, the timer resumes from the correct point.

3. **External events:** Native `wait_for_external_event()` with timeouts. Ideal for waiting for user check-in responses with a 5-minute timeout.

4. **Activities:** Workflow logic (sequencing) is separate from activities (sending messages, calling services). Activities are synchronous functions that can be tested independently.

5. **State persistence:** Workflow state (current phase, inputs, activity results) is automatically persisted to Redis via Dapr state store. Container restarts don't lose meditation progress.

6. **Observability:** Each workflow instance has a unique ID and runtime status (`RUNNING`, `COMPLETED`, `FAILED`). Easy to monitor and debug.

### Why a Separate Service?

The meditation-workflow-service is a **separate process** from existing trio-based services (telegram-bot-service, wisdom-service).

**Reason:** Dapr Workflows use **generator-based concurrency** (Python 3.12+ `yield` semantics), which is incompatible with trio/asyncio.

- Existing services: `trio` for async I/O (websockets, HTTP clients)
- Workflow service: **generator-based**, no trio/asyncio
- Activities: **synchronous** functions using sync `DaprClient`

This separation avoids runtime conflicts and keeps the architecture clean.

## Implementation

### Service Architecture

```
meditation-workflow-service (port 8003)
├── workflows/
│   ├── breathing.py       # Breathing meditation workflow (generator)
│   └── metta.py           # Metta meditation workflow (generator)
├── activities.py          # Shared activities (sync functions)
├── templates.py           # Meditation instruction texts
└── __main__.py            # FastAPI + WorkflowRuntime
```

### Workflow Lifecycle

1. **Start:** Seeker actor or Telegram bot calls `POST /meditate/start` with `chat_id`, `type`, `duration_minutes`
2. **Execution:** Workflow schedules activities (send messages via pub/sub) and timers (meditation phases)
3. **User interaction:** If check-in response arrives, raise external event via `POST /meditate/event`
4. **Completion:** Workflow calls `close_meditation` activity to log sit, get sutta suggestion, send closing messages
5. **Status:** Any service can query `GET /meditate/status/{instance_id}` to check progress

### Integration with Existing Services

- **Pub/sub:** Activities publish meditation instructions to the `responses` topic (same as wisdom-service responses)
- **Service invocation:** Activities call seeker-actor-service (`log_sit`) and wisdom-service (`get sutta suggestion`)
- **State store:** Workflow state persisted to Redis via Dapr state store (same backing store as actors)

### Key Constraints

1. **Workflows are generators:** Use `yield`, NOT `async`/`await`
2. **Activities are synchronous:** Use sync `DaprClient`, NOT trio/asyncio
3. **Separate process:** No shared memory with trio-based services
4. **Idempotent activities:** Activities may be retried on failure (Dapr guarantees)

## Consequences

### Positive

- **Natural expression:** Meditation flow is expressed as linear code, easy to read and maintain
- **Durability:** Container restarts don't interrupt meditation sessions
- **Testability:** Workflows and activities can be tested independently with mocks
- **Extensibility:** Easy to add new meditation types (body scan, jhana practice) following the same pattern
- **Observability:** Each session has a unique workflow instance with status tracking
- **No trio conflict:** Separate service keeps generator-based concurrency isolated

### Negative

- **Additional service:** One more container to deploy and monitor (meditation-workflow-service + dapr sidecar)
- **Learning curve:** Team needs to understand generator-based workflow semantics (different from async/await)
- **Redis dependency:** Workflow state adds load to Redis (though minimal — state is small and accessed infrequently)

### Neutral

- **Not for all features:** Workflows are great for multi-step orchestration, but simple request/response features should still use actors or stateless services
- **Coordination overhead:** Seeker actor needs to know workflow instance IDs to raise events (stored in actor state)

## Alternatives Considered

### Alternative 1: Implement in Seeker Actor with state machine

**Rejected:** Too complex. Manual phase tracking, timer coordination, and event waiting would make actor code hard to maintain. Workflows provide these primitives for free.

### Alternative 2: Use Celery or Temporal

**Rejected:** Dapr Workflows integrate natively with our existing Dapr infrastructure (state store, pub/sub, service invocation). Adding Celery or Temporal would introduce new dependencies, deployment complexity, and operational burden.

### Alternative 3: Client-side timers (Telegram bot)

**Rejected:** Not durable. If the bot restarts, meditation progress is lost. Also, Telegram rate limits prevent sending many messages in quick succession, making timer coordination difficult.

## References

- [Dapr Workflows Documentation](https://docs.dapr.io/developing-applications/building-blocks/workflow/)
- [Dapr Python SDK - Workflow Extension](https://github.com/dapr/python-sdk/tree/master/ext/dapr-ext-workflow)
- Ānāpānasati Sutta (MN 118) — source text for breathing meditation
- Karaniya Metta Sutta (Snp 1.8) — source text for loving-kindness meditation
