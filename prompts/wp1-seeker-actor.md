# Task: WP1 — SeekerActor (Dapr Virtual Actor)

## Context

Little Bits of Buddha (LBOB) is a Telegram chatbot teaching Early Buddhist Dhamma. Phase 2 adds Dapr Virtual Actors — one per Telegram user. This task implements the core SeekerActor.

**Repo:** This worktree at the current directory.
**Python:** 3.12+ (venv at `.venv/`)
**Branch:** `feat/seeker-actor` (already checked out)
**Run tests:** `.venv/bin/pytest tests/ -v --tb=short`

Read `phase2-plan.md` in the repo root for full architectural context.

## What Already Exists (from WP3 + WP5)

- `src/seeker_actor_service/__init__.py` — package init
- `src/seeker_actor_service/__main__.py` — FastAPI stub with `/healthz`
- `src/seeker_actor_service/requirements.txt` — deps including dapr, dapr-ext-fastapi, trio, hypercorn
- `src/seeker_actor_service/level_detector.py` — practice level detection (22 passing tests)
- `.dapr/components/statestore.yaml` — Redis state store with `actorStateStore: "true"`
- `.dapr/components/conversation.yaml` — Dapr Conversation API component (placeholder)

## What to Build

### `src/seeker_actor_service/seeker_actor.py`

The Dapr Actor implementation.

```python
from dapr.actor import Actor, ActorInterface, actormethod
from dapr.actor.runtime.config import ActorRuntimeConfig

class SeekerActorInterface(ActorInterface):
    @actormethod(name="receive_message")
    async def receive_message(self, text: str) -> dict: ...
    
    @actormethod(name="get_state")
    async def get_state(self) -> dict: ...
    
    @actormethod(name="update_practice_level")
    async def update_practice_level(self, level: str) -> None: ...
    
    @actormethod(name="get_summary")
    async def get_summary(self) -> dict: ...

class SeekerActor(Actor, SeekerActorInterface):
    """One actor per Telegram user (actor_id = chat_id)."""
    
    async def _on_activate(self) -> None:
        """Load or initialize seeker state from Dapr state store."""
        ...
    
    async def receive_message(self, text: str) -> dict:
        """
        Main entry point. Called by telegram-bot-service via pub/sub → actor invocation.
        1. Load state
        2. Update conversation history
        3. Detect practice level change (using level_detector)
        4. Call wisdom-service via Dapr service invocation
        5. Save state
        6. Return response
        """
        ...
    
    async def get_state(self) -> dict:
        """Return current seeker state as dict."""
        ...
    
    async def update_practice_level(self, level: str) -> None:
        """Manual override of practice level."""
        ...
    
    async def get_summary(self) -> dict:
        """Return conversation stats."""
        ...
```

**State schema:**
```python
{
    "chat_id": str,
    "practice_level": str,  # newcomer|beginner|intermediate|experienced
    "conversation_count": int,
    "topics_explored": list[str],
    "last_active": str,  # ISO datetime
    "preferences": dict,
    "history": list[dict],  # last 20 messages [{role, content, timestamp}]
    "signal_history": list[dict],  # for level_detector
}
```

**Key behaviors:**
- History capped at 20 messages (oldest dropped)
- `receive_message` calls wisdom-service via httpx to `http://localhost:3500/v1.0/invoke/wisdom-service/method/wisdom/ask` (Dapr service invocation)
- If wisdom-service is unreachable, return a graceful fallback: "I'm having trouble reaching my library right now. Please try again in a moment."
- After each message, run `detect_practice_level` from `level_detector.py` and update state if level changes
- State saved via `self._state_manager.set_state("seeker_state", state_dict)`

### Update `src/seeker_actor_service/__main__.py`

Replace the stub with the full actor host:

```python
from fastapi import FastAPI
from dapr.ext.fastapi import DaprActor
from seeker_actor_service.seeker_actor import SeekerActor, SeekerActorInterface

app = FastAPI()
actor = DaprActor(app)

@app.on_event("startup")
async def startup():
    await actor.register_actor(SeekerActor)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
```

**Important:** The DaprActor extension uses asyncio internally. Do NOT use trio in this service's main loop. Use uvicorn or hypercorn in asyncio mode. This is the spike result — actor hosting must be asyncio. The level_detector is pure sync, so it works fine in any context.

### Tests: `tests/test_seeker_actor.py`

**Write tests FIRST, commit, then implement.**

Test cases:
1. Actor activation creates default state (newcomer, empty history)
2. `receive_message` adds to history
3. History capped at 20 messages
4. Practice level detection triggers on message
5. Practice level never decreases via `receive_message`
6. `update_practice_level` manual override works
7. `get_state` returns full state dict
8. `get_summary` returns conversation stats
9. Wisdom service timeout returns graceful fallback
10. State persistence across calls (mock state manager)
11. `last_active` updates on each message
12. `topics_explored` updated from wisdom-service response themes

Use mocks for Dapr state manager and wisdom-service HTTP calls. Use `unittest.mock.AsyncMock` for async methods.

## Constraints

- Only create/modify files in `src/seeker_actor_service/` and `tests/`
- Do NOT modify `level_detector.py` (already tested, leave it)
- Do NOT modify compose.yaml, Dockerfile, or Dapr components
- asyncio for the actor host (NOT trio — Dapr actor SDK requires asyncio)
- All state must be JSON-serializable (for Dapr state store)

## Branch & Push

Work on branch: `feat/seeker-actor`. Commit AND push when done.
TDD: commit failing tests first, then implementation.

## Self-Review

Re-read diff. 3 concerns. TDD compliance.
