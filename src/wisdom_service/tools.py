"""Tool definitions for Anthropic function calling.

This module provides tool definitions in Anthropic format and execution functions
for tool calls made by the LLM.

Tools:
- search_suttas: Search the sutta corpus for relevant teachings
- save_practice_note: Save a practice note to the seeker's actor state
- get_seeker_history: Get recent conversation history for context
"""

import json

import httpx

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
                    "description": "Search query for finding relevant suttas",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of suttas to return (default: 3)",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_practice_note",
        "description": "Save a practice note for the seeker. Use when the seeker shares an insight, experience, or intention about their practice that's worth remembering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "Seeker's Telegram chat ID",
                },
                "note": {
                    "type": "string",
                    "description": "The practice note to save",
                },
            },
            "required": ["chat_id", "note"],
        },
    },
    {
        "name": "get_seeker_history",
        "description": "Get recent conversation history for context. Use when you need to recall what was discussed previously.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "Seeker's Telegram chat ID",
                },
                "last_n": {
                    "type": "integer",
                    "description": "Number of recent messages to retrieve (default: 5)",
                    "default": 5,
                },
            },
            "required": ["chat_id"],
        },
    },
]


def execute_search_suttas(query: str, limit: int = 3) -> str:
    """Execute sutta search and return formatted results.

    Args:
        query: Search query text
        limit: Maximum number of results to return

    Returns:
        Formatted string with sutta results or message if no results
    """
    from wisdom_service.sutta_search import search_suttas

    results = search_suttas(query, top_k=limit)
    if not results:
        return "No matching suttas found."

    formatted = []
    for r in results:
        # Format with title, ID, and truncated excerpt for conciseness
        excerpt = r.get("text", r.get("excerpt", ""))[:200]
        formatted.append(f"**{r['title']}** ({r['id']})\n{excerpt}")

    return "\n\n---\n\n".join(formatted)


def execute_save_practice_note(dapr_client, chat_id: str, note: str) -> str:
    """Save a practice note to the seeker's actor state.

    Args:
        dapr_client: Dapr client instance
        chat_id: Telegram chat ID
        note: Practice note text to save

    Returns:
        Success message
    """
    dapr_client.invoke_method(
        app_id="seeker-actor-service",
        method_name=f"actors/SeekerActor/{chat_id}/method/log_sit",
        data=json.dumps(
            {
                "duration_minutes": 0,
                "practice_type": "other",
                "notes": note,
                "from_workflow": False,
            }
        ),
        content_type="application/json",
        http_verb="POST",
    )
    return "Practice note saved."


def execute_get_seeker_history(dapr_client, chat_id: str, last_n: int = 5) -> str:
    """Get recent conversation history from seeker actor.

    Args:
        dapr_client: Dapr client instance
        chat_id: Telegram chat ID
        last_n: Number of recent messages to retrieve

    Returns:
        Formatted conversation history or message if no history
    """
    result = dapr_client.invoke_method(
        app_id="seeker-actor-service",
        method_name=f"actors/SeekerActor/{chat_id}/method/get_state",
        http_verb="GET",
    )
    state = json.loads(result.text())
    history = state.get("history", [])[-last_n:]
    if not history:
        return "No previous conversation history."

    formatted = []
    for msg in history:
        role = msg.get("role", "unknown")
        text = msg.get("content", "")[:200]  # Truncate to 200 chars
        formatted.append(f"{role}: {text}")

    return "\n".join(formatted)


def has_tool_use(response: dict) -> bool:
    """Check if response contains tool_use blocks.

    Args:
        response: Anthropic API response

    Returns:
        True if response contains tool_use blocks, False otherwise
    """
    content = response.get("content", [])
    return any(block.get("type") == "tool_use" for block in content)


def execute_tool_calls(response: dict, dapr_client, chat_id: str) -> list:
    """Execute all tool calls and return tool_result blocks.

    Args:
        response: Anthropic API response containing tool_use blocks
        dapr_client: Dapr client instance
        chat_id: Telegram chat ID for context

    Returns:
        List of tool_result blocks in Anthropic format
    """
    results = []
    for block in response.get("content", []):
        if block.get("type") == "tool_use":
            tool_name = block["name"]
            tool_input = block["input"]
            tool_id = block["id"]

            # Execute the appropriate tool
            if tool_name == "search_suttas":
                result = execute_search_suttas(**tool_input)
            elif tool_name == "save_practice_note":
                # Inject chat_id if not provided
                if "chat_id" not in tool_input:
                    tool_input["chat_id"] = chat_id
                result = execute_save_practice_note(dapr_client, **tool_input)
            elif tool_name == "get_seeker_history":
                # Inject chat_id if not provided
                if "chat_id" not in tool_input:
                    tool_input["chat_id"] = chat_id
                result = execute_get_seeker_history(dapr_client, **tool_input)
            else:
                result = f"Unknown tool: {tool_name}"

            results.append(
                {"type": "tool_result", "tool_use_id": tool_id, "content": result}
            )

    return results


def call_anthropic_with_tools(
    messages: list[dict],
    system: str,
    tools: list[dict],
    api_base: str,
    api_key: str,
    model: str,
) -> dict:
    """Call Anthropic API with tool definitions.

    Args:
        messages: List of message dicts with 'role' and 'content'
        system: System prompt text
        tools: List of tool definitions in Anthropic format
        api_base: API base URL
        api_key: API key
        model: Model name

    Returns:
        Anthropic API response as dict
    """
    url = f"{api_base}/v1/messages"
    headers = {
        "content-type": "application/json",
        "accept": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": model.replace("anthropic/", ""),  # Strip prefix if present
        "max_tokens": 2048,
        "system": system,
        "messages": messages,
        "tools": tools,
    }

    response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
    response.raise_for_status()
    return response.json()
