# Task: Phase 1 Cleanup — Fix All Test & Integration Bugs

## Context
Project: Little Bits of Buddha (LBOB)
Stack: Python 3.11, FastAPI, Dapr, Redis, PDM, **trio** (NOT asyncio)
Repo: `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`

**This project uses trio, NOT asyncio.** All async code must use trio patterns.

## Branch
Create and work on branch: `fix/phase1-cleanup`
Do NOT work on main.

## What to fix (6 items)

### 1. seeker_state.py — DaprClient is sync-only
`DaprClient()` is a **sync** context manager. The current code uses `async with DaprClient()` which fails.
Fix: wrap all DaprClient calls with `trio.to_thread.run_sync()`.
```python
from trio import to_thread

async def save_message(chat_id, role, content):
    def _save():
        with DaprClient() as client:
            # ... sync state store operations
    await to_thread.run_sync(_save)
```

### 2. test_seeker_state.py — fix async test patterns
Change all `async with DaprClient()` mocks to match the sync pattern above.
Use `@pytest.mark.trio` (NOT `@pytest.mark.asyncio`).
Add `pytest-trio` to dev dependencies if not present.

### 3. test_rate_limiter.py — wrong async test framework
Change `@pytest.mark.asyncio` → `@pytest.mark.trio` everywhere.
Fix mock patterns to work with trio.

### 4. rate_limiter.py — wire into message handler
Add to `src/openai_service_worldofgeese/__main__.py` in the `messages_subscriber` function:
- Import: `from openai_service_worldofgeese.rate_limiter import check_rate_limit`
- Before the LLM call, add rate limit check
- If rate-limited, publish a gentle Buddhist response instead of calling the LLM
- Rate-limited response: "Take a moment to sit with what we've discussed. The Dhamma unfolds in silence as much as in words. I'll be here when you're ready to continue."

### 5. sutta_search.py — fix type errors
- Fix tuple vs list for Redis index fields (ty flagged this)
- Fix unresolved redis import (may need `types-redis` or fix import path)

### 6. pyproject.toml — add missing test deps
Ensure these are in dev dependencies:
- `pytest-trio` (for `@pytest.mark.trio`)
- All imports used by tests are available

## Verification
After all fixes:
```bash
python -m pytest tests/ -x -v  # All tests must pass
```
Run `ruff check` and `ruff format` too.

## Constraints
- This project uses **trio**, NOT asyncio
- DaprClient is **sync-only** — always wrap with `trio.to_thread.run_sync`
- Do NOT change the Dapr architecture or compose files
- Do NOT modify sutta_corpus/suttas.json

## Branch & Push
Work on branch: `fix/phase1-cleanup`. Commit AND push when done.

## Self-Review (mandatory)
List exactly 3 concerns after reviewing your diff.
