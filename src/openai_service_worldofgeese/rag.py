"""RAG pipeline for Little Bits of Buddha.

This module assembles the full prompt for LLM calls by:
1. Loading conversation history from Dapr state store
2. Searching for relevant suttas via vector search
3. Constructing an augmented system prompt with sutta context
4. Returning the full message list ready for the LLM
"""

import logging

from openai_service_worldofgeese.seeker_state import get_history

logger = logging.getLogger(__name__)


async def build_rag_prompt(
    chat_id: str,
    user_message: str,
    system_prompt: str,
) -> list[dict]:
    """Build the full message list for the LLM call with RAG context.

    This function orchestrates the RAG pipeline:
    1. Load conversation history (last 10 messages) via seeker_state.get_history()
    2. Search for relevant suttas via sutta_search.search_suttas(user_message, top_k=3)
    3. Construct the message list:
       - system message (original Buddha persona + injected sutta context)
       - conversation history messages
       - current user message
    4. Return the full messages list ready for _call_lego_mps()

    Args:
        chat_id: Unique identifier for the conversation
        user_message: The current user message to respond to
        system_prompt: The base system prompt (Buddha persona)

    Returns:
        List of message dicts with 'role' and 'content' keys,
        ready to pass to the LLM API.

    Graceful degradation:
        - If sutta search fails (Redis down, numpy missing): falls back to plain prompt
        - If state store fails (Dapr down): falls back to stateless mode
        - Logs errors but never crashes
    """
    # Step 1: Load conversation history (graceful fallback)
    history = []
    try:
        history = await get_history(chat_id, limit=10)
    except Exception as e:
        logger.warning(
            f"Failed to load conversation history: {e}. Continuing without history."
        )

    # Step 2: Search for relevant suttas (graceful fallback)
    # Import lazily to avoid numpy dependency at module import time
    suttas = []
    try:
        from openai_service_worldofgeese.sutta_search import search_suttas

        suttas = search_suttas(user_message, top_k=3)
    except (ImportError, RuntimeError, Exception) as e:
        logger.warning(
            f"Failed to search suttas: {e}. Continuing without sutta context."
        )

    # Step 3: Construct augmented system prompt
    augmented_system_prompt = system_prompt

    if suttas:
        # Build sutta context section
        sutta_context_lines = [
            "",
            "The following suttas are relevant to this conversation. Draw from them when appropriate, citing the sutta name:",
            "",
        ]

        for sutta in suttas:
            sutta_context_lines.append("---")
            sutta_context_lines.append(f"{sutta['title']} ({sutta['id']})")
            sutta_context_lines.append(sutta["text"])
            sutta_context_lines.append("---")

        sutta_context = "\n".join(sutta_context_lines)
        augmented_system_prompt = system_prompt + sutta_context

    # Step 4: Build the full message list
    messages = [{"role": "system", "content": augmented_system_prompt}]

    # Add conversation history (excluding timestamps)
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    return messages
