# Task: WP5 — Redis-Cell Rate Limiting

## Context
Project: Little Bits of Buddha (LBOB)
Stack: Python 3.11, FastAPI, Dapr, Redis, PDM, trio
Repo: `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`

## Branch
Create and work on branch: `feat/rate-limiting`
Do NOT work on main.

## TDD
Write failing tests FIRST in `tests/test_rate_limiter.py`. Commit them.
Then implement until tests pass. Commit again.

## What to do

1. **Create `src/openai_service_worldofgeese/rate_limiter.py`**:
   - Use Redis `CL.THROTTLE` command (redis-cell module) for per-user rate limiting
   - `async def check_rate_limit(chat_id: str) -> tuple[bool, int]` — returns (allowed: bool, retry_after_seconds: int)
   - Default limit: 20 messages per hour per user
   - Configurable via env vars: `RATE_LIMIT_COUNT=20`, `RATE_LIMIT_PERIOD=3600`
   - If redis-cell is NOT available (module not loaded), fall back to a simple Redis INCR + EXPIRE pattern

2. **Wire into message handler** in `src/openai_service_worldofgeese/__main__.py`:
   - Before processing: check rate limit
   - If rate-limited: publish a gentle response instead of calling LLM:
     ```
     "Take a moment to sit with what we've discussed. The Dhamma unfolds in silence as much as in words. I'll be here when you're ready to continue."
     ```
   - Include `retry_after` seconds in the response metadata (for client-side display)

3. **Redis-cell module** — verify `redis/redis-stack-server` image includes it (it does). If WP2 hasn't already switched the image, update `compose.yaml`.

4. **Fallback implementation** — if `CL.THROTTLE` returns a Redis error (module not loaded):
   - Use `INCR chat_limit:{chat_id}` + `EXPIRE chat_limit:{chat_id} 3600`
   - Check if count > limit
   - Less precise but works without redis-cell

5. **Tests** (`tests/test_rate_limiter.py`):
   - Test check_rate_limit allows messages under limit (mock Redis)
   - Test check_rate_limit blocks messages over limit
   - Test retry_after_seconds is correct
   - Test fallback works when CL.THROTTLE unavailable
   - Test rate limit response message is sent (mock Dapr publish)

## Constraints
- Only modify/create: `src/openai_service_worldofgeese/rate_limiter.py`, `src/openai_service_worldofgeese/__main__.py` (add rate check), `tests/test_rate_limiter.py`
- Do NOT modify: telegram service, sutta search, state store
- Keep the gentle Buddhist tone in rate-limit responses

## Branch & Push
Work on branch: `feat/rate-limiting`. Commit AND push to the branch when done.

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
