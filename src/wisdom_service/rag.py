"""RAG pipeline for Wisdom Service.

This module assembles the full prompt for LLM calls by:
1. Searching for relevant suttas via vector search
2. Constructing an augmented system prompt with sutta context
3. Returning the full message list ready for the LLM

Adapted from openai_service_worldofgeese/rag.py:
- Removed dependency on seeker_state (history is now passed in)
- History management now handled by SeekerActor
"""

import logging

logger = logging.getLogger(__name__)


async def build_rag_prompt(
    user_message: str,
    system_prompt: str,
    history: list[dict],
) -> list[dict]:
    """Build the full message list for the LLM call with RAG context.

    This function orchestrates the RAG pipeline:
    1. Search for relevant suttas via sutta_search.search_suttas(user_message, top_k=3)
    2. Construct the message list:
       - system message (original Buddha persona + injected sutta context)
       - conversation history messages
       - current user message
    3. Return the full messages list ready for the LLM API

    Args:
        user_message: The current user message to respond to
        system_prompt: The base system prompt (Buddha persona adapted by practice level)
        history: Conversation history (list of {"role": str, "content": str} dicts)

    Returns:
        List of message dicts with 'role' and 'content' keys,
        ready to pass to the LLM API.

    Graceful degradation:
        - If sutta search fails (Redis down, numpy missing): falls back to plain prompt
        - Logs errors but never crashes
    """
    # Step 1: Search for relevant suttas (graceful fallback)
    # Import lazily to avoid numpy dependency at module import time
    suttas = []
    try:
        from wisdom_service.sutta_search import search_suttas

        suttas = search_suttas(user_message, top_k=3)
    except (ImportError, RuntimeError, Exception) as e:
        logger.warning(
            f"Failed to search suttas: {e}. Continuing without sutta context."
        )

    # Step 2: Construct augmented system prompt
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

    # Step 3: Build the full message list
    messages = [{"role": "system", "content": augmented_system_prompt}]

    # Add conversation history (excluding timestamps if present)
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    return messages
