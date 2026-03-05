# Task: WP3 — Tool Calling via Wisdom Service

## Context
Little Bits of Buddha — Telegram Dhamma teacher bot. Python 3.12, trio (NOT asyncio). The wisdom-service handles LLM + RAG via raw httpx to Anthropic proxy (Bedrock). Currently, every message gets mandatory sutta RAG. We want the LLM to DECIDE when to search suttas using Anthropic function calling.

## Branch
Work on branch: `feat/tool-calling` (already checked out).
Do NOT work on main.

## TDD
Write failing tests FIRST in `tests/test_tool_calling.py`. Commit them.
Then implement until tests pass. Commit again.

## Existing Files to Read First
- `src/wisdom_service/__main__.py` — Current LLM call + RAG pipeline, `/wisdom/ask` endpoint
- `src/wisdom_service/rag.py` — RAG pipeline (sutta context injection)
- `src/wisdom_service/sutta_search.py` — Vector search for suttas
- `src/wisdom_service/langcache.py` — LangCache (just merged, check before/after cache for tool calls)
- `docs/adr/0009-raw-httpx-anthropic.md` or `docs/adr/0013-dapr-conversation-api.md` — How we call the LLM

## What to Build

### 1. `src/wisdom_service/tools.py`

Tool definitions and implementations:

```python
"""Tool definitions for Anthropic function calling."""

# Tool definitions in Anthropic format
TOOLS = [
    {
        "name": "search_suttas",
        "description": "Search the sutta corpus for teachings relevant to the seeker's question. Use when the seeker asks about specific Buddhist concepts, teachings, or practices.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for finding relevant suttas"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of suttas to return (default: 3)",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "save_practice_note",
        "description": "Save a practice note for the seeker. Use when the seeker shares an insight, experience, or intention about their practice that's worth remembering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "Seeker's Telegram chat ID"
                },
                "note": {
                    "type": "string",
                    "description": "The practice note to save"
                }
            },
            "required": ["chat_id", "note"]
        }
    },
    {
        "name": "get_seeker_history",
        "description": "Get recent conversation history for context. Use when you need to recall what was discussed previously.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "Seeker's Telegram chat ID"
                },
                "last_n": {
                    "type": "integer",
                    "description": "Number of recent messages to retrieve (default: 5)",
                    "default": 5
                }
            },
            "required": ["chat_id"]
        }
    }
]


def execute_search_suttas(sutta_search, query: str, limit: int = 3) -> str:
    """Execute sutta search and return formatted results."""
    results = sutta_search.search(query, top_k=limit)
    if not results:
        return "No matching suttas found."
    formatted = []
    for r in results:
        formatted.append(f"**{r['title']}** ({r['id']})\n{r['excerpt']}")
    return "\n\n---\n\n".join(formatted)


def execute_save_practice_note(dapr_client, chat_id: str, note: str) -> str:
    """Save a practice note to the seeker's actor state."""
    import json
    result = dapr_client.invoke_method(
        app_id="seeker-actor-service",
        method_name=f"actors/SeekerActor/{chat_id}/method/log_sit",
        data=json.dumps({
            "duration_minutes": 0,
            "practice_type": "other",
            "notes": note,
            "from_workflow": False
        }),
        content_type="application/json",
        http_verb="POST"
    )
    return f"Practice note saved."


def execute_get_seeker_history(dapr_client, chat_id: str, last_n: int = 5) -> str:
    """Get recent conversation history from seeker actor."""
    import json
    result = dapr_client.invoke_method(
        app_id="seeker-actor-service",
        method_name=f"actors/SeekerActor/{chat_id}/method/get_state",
        http_verb="GET"
    )
    state = json.loads(result.text())
    history = state.get("history", [])[-last_n:]
    if not history:
        return "No previous conversation history."
    formatted = []
    for msg in history:
        role = msg.get("role", "unknown")
        text = msg.get("content", "")[:200]
        formatted.append(f"{role}: {text}")
    return "\n".join(formatted)
```

### 2. Modify `/wisdom/ask` endpoint for tool calling

In `src/wisdom_service/__main__.py`, update the LLM call:

**Current flow:** message → mandatory RAG → LLM → response
**New flow:** message → LLM with tools → (tool calls?) → tool results → LLM → response

```python
# In the /wisdom/ask handler:

# 1. Check langcache first (existing)
# 2. Build messages with system prompt (existing)
# 3. First LLM call WITH tools
response = call_anthropic_with_tools(messages, system_prompt, TOOLS)

# 4. Tool call loop (max 3 iterations)
tool_use_count = 0
while has_tool_use(response) and tool_use_count < 3:
    tool_results = execute_tool_calls(response)
    messages.append({"role": "assistant", "content": response["content"]})
    messages.append({"role": "user", "content": tool_results})
    response = call_anthropic_with_tools(messages, system_prompt, TOOLS)
    tool_use_count += 1

# 5. If no tools were called, fall back to mandatory RAG (existing behavior)
if tool_use_count == 0:
    # Existing RAG pipeline as fallback
    sutta_context = search_suttas(message)
    messages_with_rag = inject_sutta_context(messages, sutta_context)
    response = call_anthropic(messages_with_rag, system_prompt)

# 6. Cache response (only if no tool calls — tool results may be user-specific)
if tool_use_count == 0:
    langcache.store(message, final_text, practice_level)
```

**Anthropic tool calling format (raw httpx):**
```python
def call_anthropic_with_tools(messages, system, tools):
    """Call Anthropic API with tool definitions."""
    payload = {
        "model": MODEL,
        "max_tokens": 2048,
        "system": system,
        "messages": messages,
        "tools": tools
    }
    # Use existing httpx call pattern from rag.py
    response = httpx.post(
        f"{ANTHROPIC_BASE_URL}/v1/messages",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "accept": "application/json"
        },
        json=payload,
        timeout=60.0
    )
    return response.json()

def has_tool_use(response) -> bool:
    """Check if response contains tool_use blocks."""
    return any(block["type"] == "tool_use" for block in response.get("content", []))

def execute_tool_calls(response) -> list:
    """Execute all tool calls and return tool_result blocks."""
    results = []
    for block in response["content"]:
        if block["type"] == "tool_use":
            tool_name = block["name"]
            tool_input = block["input"]
            tool_id = block["id"]
            
            if tool_name == "search_suttas":
                result = execute_search_suttas(sutta_search, **tool_input)
            elif tool_name == "save_practice_note":
                result = execute_save_practice_note(dapr_client, **tool_input)
            elif tool_name == "get_seeker_history":
                result = execute_get_seeker_history(dapr_client, **tool_input)
            else:
                result = f"Unknown tool: {tool_name}"
            
            results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result
            })
    return results
```

### 3. Tests (`tests/test_tool_calling.py`)

Write FIRST as failing tests:
1. **Tool definition format** — TOOLS list has correct Anthropic schema
2. **search_suttas execution** — returns formatted sutta results
3. **save_practice_note execution** — calls actor method correctly
4. **get_seeker_history execution** — returns formatted history
5. **has_tool_use detection** — correctly identifies tool_use blocks
6. **Tool result format** — execute_tool_calls returns correct tool_result blocks
7. **Max tool call limit** — loop stops after 3 iterations
8. **Fallback to RAG** — when no tools called, mandatory RAG runs
9. **No caching for tool responses** — tool-calling responses skip langcache store
10. **Empty tool result** — graceful handling of tool returning empty/error

## Constraints
- This project uses **trio**, NOT asyncio. Use `@pytest.mark.trio` for async tests.
- Raw httpx to Anthropic proxy (NOT LiteLLM — `x-api-key` header conflict, see ADR 0009)
- Include `Accept: application/json` header (406 without it)
- Anthropic model: `anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0` (from env `ANTHROPIC_MODEL`)
- Max 3 tool calls per turn
- Mandatory RAG is FALLBACK — only when LLM doesn't use tools
- Don't cache tool-calling responses in langcache
- Tool results must be concise (summarize, don't send full sutta text)
- `chat_id` must be passed into tool context so tools can access user-specific state

## Branch & Push
Work on branch: `feat/tool-calling`. Commit AND push when done.

## Self-Review (mandatory before final commit)
**Concerns (list exactly 3):**
1. [Something specific that could break]
2. [An edge case you didn't test]
3. [An assumption you're uncertain about]

**TDD compliance check:**
- [ ] I committed failing tests BEFORE implementation
- [ ] Tests and implementation are in separate commits
- [ ] All tests pass
