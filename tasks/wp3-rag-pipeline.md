# Task: WP3 — RAG Pipeline (Wire Sutta Search + Conversation History into LLM)

## Context
Project: Little Bits of Buddha (LBOB)
Stack: Python 3.11, FastAPI, Dapr, Redis, PDM, **trio** (NOT asyncio)
Repo: `/home/node/.openclaw/workspace/projects/little_bits_of_buddha`

WP1 (state store / conversation history) and WP2 (sutta vector search) are already merged to main. This task wires them together into the LLM call.

## Branch
Create and work on branch: `feat/rag-pipeline`
Do NOT work on main.

## TDD
Write failing tests FIRST in `tests/test_rag_pipeline.py`. Commit them.
Then implement until tests pass. Commit again.

## What to do

### 1. Create `src/openai_service_worldofgeese/rag.py`
A thin module that assembles the full prompt:

```python
async def build_rag_prompt(
    chat_id: str,
    user_message: str,
    system_prompt: str,
) -> list[dict]:
    """Build the full message list for the LLM call with RAG context.
    
    1. Load conversation history (last 10 messages) via seeker_state.get_history()
    2. Search for relevant suttas via sutta_search.search_suttas(user_message, top_k=3)
    3. Construct the message list:
       - system message (original Buddha persona + injected sutta context)
       - conversation history messages
       - current user message
    4. Return the full messages list ready for _call_lego_mps()
    """
```

The system prompt should be augmented like:
```
{original_system_prompt}

The following suttas are relevant to this conversation. Draw from them when appropriate, citing the sutta name:

---
{sutta_1_title} ({sutta_1_id})
{sutta_1_text}
---
{sutta_2_title} ({sutta_2_id})  
{sutta_2_text}
---
```

If no relevant suttas are found (empty corpus or search returns nothing), just use the original system prompt without the sutta section.

### 2. Update `src/openai_service_worldofgeese/__main__.py`
In the `messages_subscriber` function:

```python
# BEFORE (current):
response = _call_lego_mps(model=model, api_base=api_base, api_key=api_key, messages=[...])

# AFTER:
from openai_service_worldofgeese.rag import build_rag_prompt

messages = await build_rag_prompt(
    chat_id=str(event.data.get("chat_id")),
    user_message=text,
    system_prompt="You are the Buddha. You teach only the Dhamma...",
)
response = _call_lego_mps(model=model, api_base=api_base, api_key=api_key, messages=messages)
```

Also: after getting the LLM response, save both the user message AND the assistant response to state:
```python
from openai_service_worldofgeese.seeker_state import save_message
await save_message(chat_id, "user", text)
await save_message(chat_id, "assistant", response_text)
```

### 3. Handle sutta search gracefully
- If `sutta_search` fails (Redis not available, index not created, numpy missing): catch the exception and fall back to the original prompt without suttas
- Log the error but don't crash
- If `seeker_state` fails: same — fall back to stateless mode

### 4. Tests (`tests/test_rag_pipeline.py`)
Write these as failing tests FIRST:

1. `test_build_rag_prompt_includes_sutta_context` — mock seeker_state and sutta_search, verify system prompt contains sutta text
2. `test_build_rag_prompt_includes_conversation_history` — verify history messages appear in correct order
3. `test_build_rag_prompt_no_suttas_found` — when search returns empty, system prompt is unmodified
4. `test_build_rag_prompt_sutta_search_fails_gracefully` — when search throws, falls back to plain prompt
5. `test_build_rag_prompt_state_fails_gracefully` — when get_history throws, falls back to no history
6. `test_message_handler_uses_rag_prompt` — verify __main__.py calls build_rag_prompt and passes result to _call_lego_mps

Use `@pytest.mark.trio` for all async tests. Mock `sutta_search.search_suttas` and `seeker_state.get_history` — do NOT call real Redis.

### 5. Also fix the xfail test
The test `test_message_handler_includes_history_in_llm_call` in `test_seeker_state.py` is marked `xfail`. After wiring is done, it should pass. Remove the `xfail` marker and fix it if needed.

## Constraints
- This project uses **trio**, NOT asyncio
- DaprClient is **sync-only** — wrap with `trio.to_thread.run_sync`
- `sutta_search` uses numpy/sentence-transformers — may not be available in all environments. Always catch ImportError/RuntimeError.
- Do NOT modify: sutta_corpus/, compose.yaml, Dockerfile
- Do NOT change the Dapr pub/sub architecture

## Branch & Push
Work on branch: `feat/rag-pipeline`. Commit AND push when done.

## Self-Review (mandatory)
List exactly 3 concerns after reviewing your diff.
