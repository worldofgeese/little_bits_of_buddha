# Task: WP1 — Dapr State Store for Conversation History

## Context
Project: Little Bits of Buddha (LBOB)
Stack: Python 3.11, FastAPI, Dapr, Redis, PDM, trio
Repo: `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`
Vision: `docs/vision.html` · Plan: `docs/phase1-plan.md`

## Branch
Create and work on branch: `feat/state-store`
Do NOT work on main.

## TDD
Write failing tests FIRST in `tests/test_seeker_state.py`. Commit them.
Then implement until tests pass. Commit again.

## What to do

1. **Add Dapr state store component config** — create `components/statestore.yaml`:
   ```yaml
   apiVersion: dapr.io/v1alpha1
   kind: Component
   metadata:
     name: statestore
   spec:
     type: state.redis
     version: v1
     metadata:
     - name: redisHost
       value: redis:6379
     - name: redisPassword
       value: ""
   ```

2. **Create `src/openai_service_worldofgeese/seeker_state.py`**:
   - `async def save_message(chat_id: str, role: str, content: str)` — append to conversation history in Dapr state store (key: `seeker:{chat_id}`)
   - `async def get_history(chat_id: str, limit: int = 10) -> list[dict]` — retrieve last N messages
   - `async def clear_history(chat_id: str)` — reset conversation
   - Use `dapr.clients.DaprClient` for state operations
   - Store as JSON list of `{"role": str, "content": str, "timestamp": str}`

3. **Wire into message handler** in `src/openai_service_worldofgeese/__main__.py`:
   - After receiving a message: save user message to state
   - Before calling LLM: load last 10 messages as conversation context
   - After receiving LLM response: save assistant message to state
   - Pass full conversation history (not just current message) to `_call_anthropic_proxy`

4. **Tests** (`tests/test_seeker_state.py`):
   - Test save_message stores correctly (mock DaprClient)
   - Test get_history returns last N messages in order
   - Test get_history with empty state returns empty list
   - Test clear_history removes all messages
   - Test message handler includes history in LLM call (mock both Dapr + httpx)

## Constraints
- Only modify/create: `components/statestore.yaml`, `src/openai_service_worldofgeese/seeker_state.py`, `src/openai_service_worldofgeese/__main__.py`, `tests/test_seeker_state.py`
- Do NOT modify: telegram service, Redis config, compose files
- Use `dapr.clients.DaprClient` (already a dependency)
- Keep trio async patterns consistent with existing code

## Branch & Push
Work on branch: `feat/state-store`. Commit AND push to the branch when done.
The orchestrator handles merge to main after review.

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
