# Task: WP6 — Practice Journaling

## Context
Little Bits of Buddha — Telegram Dhamma teacher bot. Python 3.12, trio (NOT asyncio). SeekerActor (Dapr Virtual Actor) holds per-user state. We want seekers to log meditation sessions and review their practice patterns.

## Branch
Work on branch: `feat/practice-journal` (already checked out).
Do NOT work on main.

## TDD
Write failing tests FIRST in `tests/test_practice_journal.py`. Commit them.
Then implement until tests pass. Commit again.

## Existing Files to Read First
- `src/seeker_actor_service/seeker_actor.py` — Actor implementation with SeekerState
- `src/seeker_actor_service/seeker_interface.py` — ActorInterface
- `src/telegram_bot_service/__main__.py` — Telegram bot with /start /level /forget commands
- `tests/test_seeker_actor.py` — Existing actor tests

## What to Build

### 1. Add journal state to SeekerActor

In `src/seeker_actor_service/seeker_actor.py`, extend `SeekerState`:

```python
@dataclass
class SitEntry:
    timestamp: str  # ISO 8601
    duration_minutes: int
    practice_type: str  # "breathing" | "metta" | "body_scan" | "walking" | "other"
    notes: str | None = None
    from_workflow: bool = False  # True if auto-logged after guided meditation

class SeekerState:
    # ... existing fields ...
    practice_journal: list[dict] = field(default_factory=list)  # List of SitEntry dicts, max 90 days
```

### 2. Add actor methods

In `src/seeker_actor_service/seeker_interface.py`, add to interface:
```python
@actormethod(name="log_sit")
async def log_sit(self, data: dict) -> dict: ...

@actormethod(name="get_journal")
async def get_journal(self, data: dict) -> dict: ...

@actormethod(name="get_weekly_summary")  
async def get_weekly_summary(self, data: dict) -> dict: ...
```

In `src/seeker_actor_service/seeker_actor.py`, implement:

**`log_sit`:**
- Parse: duration_minutes, practice_type, notes, from_workflow
- Add SitEntry to practice_journal
- Prune entries older than 90 days
- Save state
- Return: {"status": "logged", "total_sits": len(journal)}

**`get_journal`:**
- Accept: `days` parameter (default 7)
- Return entries from last N days
- Return: {"entries": [...], "total_duration_minutes": sum}

**`get_weekly_summary`:**
- Calculate: total sits, total minutes, most practiced type, longest sit, streak
- Return structured summary data
- The LLM summary generation happens in telegram-bot-service (not here)

### 3. Add Telegram commands

In `src/telegram_bot_service/__main__.py`, add handlers:

**`/sit [duration] [type] [notes]`:**
- Parse: `/sit 20 breathing` or `/sit 10 metta "Focused on family"`
- Default type: "other" if not specified
- Call seeker-actor: `log_sit` method
- Respond: "🪷 Logged: 20 min breathing meditation. You've sat {total} times."

**`/journal [week]`:**
- No args: show last 7 days of entries (simple list)
- `week`: call `get_weekly_summary`, then call wisdom-service to generate a warm summary
- Respond with formatted list or LLM-generated summary

### 4. Tests (`tests/test_practice_journal.py`)

Write these FIRST as failing tests:
1. **Log sit** — log_sit adds entry to journal, returns correct total
2. **Parse /sit command** — "20 breathing" → duration=20, type="breathing"
3. **Parse /sit with notes** — `10 metta "Focused on family"` → correct parsing
4. **Get journal** — returns only entries within date range
5. **Weekly summary** — correct calculation of totals, most practiced, longest
6. **90-day pruning** — entries older than 90 days are removed on log_sit
7. **Default type** — `/sit 15` → type="other"
8. **From workflow flag** — log_sit with from_workflow=True stores correctly
9. **Empty journal** — get_journal on new seeker returns empty list

## Constraints
- This project uses **trio**, NOT asyncio. Use `@pytest.mark.trio` for async tests.
- DaprClient is sync-only — wrap with `trio.to_thread.run_sync` in actor methods.
- Actor state is persisted by Dapr to Redis automatically.
- Journal entries stored as list of dicts (JSON-serializable).
- 90-day cap enforced on every `log_sit` call.
- practice_type must be one of: "breathing", "metta", "body_scan", "walking", "other"
- Do NOT add /meditate or /daily commands (those are WP1 and WP2).

## Branch & Push
Work on branch: `feat/practice-journal`. Commit AND push when done.

## Self-Review (mandatory before final commit)
Re-read your entire diff (`git diff main..HEAD`). Write out:

**Concerns (list exactly 3):**
1. [Something specific that could break]
2. [An edge case you didn't test]
3. [An assumption you're uncertain about]

**TDD compliance check:**
- [ ] I committed failing tests BEFORE implementation
- [ ] Tests and implementation are in separate commits
- [ ] All tests pass
