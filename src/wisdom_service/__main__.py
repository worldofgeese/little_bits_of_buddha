"""Wisdom Service — LLM + RAG pipeline for LBOB.

Extracted from openai_service_worldofgeese (Phase 1).
Called by SeekerActor via Dapr service invocation.

Provides:
- /wisdom/ask endpoint for LLM inference with RAG context
- Dapr Conversation API as primary client (with fallback to raw httpx)
- Practice-level-adapted system prompts
- Sutta citation extraction and theme detection
"""

import logging
import os
import re

import trio
from fastapi import FastAPI
from hypercorn.config import Config
from hypercorn.trio import serve
from pydantic import BaseModel

from wisdom_service.anthropic_client import _call_anthropic_proxy, wait_for_dapr_ready
from wisdom_service.langcache import LangCache
from wisdom_service.prompts import get_system_prompt
from wisdom_service.rag import build_rag_prompt
from wisdom_service.sutta_search import get_embedding_model, get_redis_client

logger = logging.getLogger(__name__)

app = FastAPI()

# Global LangCache instance (initialized at startup)
_langcache = None


def get_langcache() -> LangCache:
    """Get or create the LangCache instance."""
    global _langcache
    if _langcache is None:
        redis_client = get_redis_client()
        embedding_model = get_embedding_model()
        _langcache = LangCache(redis_client, embedding_model, similarity_threshold=0.92)
        try:
            _langcache.setup_index()
        except Exception as e:
            logger.warning(f"Failed to setup LangCache index: {e}")
    return _langcache


class WisdomRequest(BaseModel):
    chat_id: str
    message: str
    context: dict  # practice_level, history, topics_explored


class WisdomResponse(BaseModel):
    response: str
    suttas_cited: list[str]
    detected_themes: list[str]
    from_cache: bool = False


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/wisdom/ask")
async def ask(request: WisdomRequest) -> WisdomResponse:
    practice_level = request.context.get("practice_level", "newcomer")
    history = request.context.get("history", [])

    # Check cache before calling LLM
    langcache = get_langcache()
    cached_response = await trio.to_thread.run_sync(
        lambda: langcache.lookup(request.message, practice_level)
    )

    if cached_response:
        logger.info(f"LangCache HIT for practice_level={practice_level}")
        return WisdomResponse(
            response=cached_response,
            suttas_cited=[],
            detected_themes=[],
            from_cache=True,
        )

    system_prompt = get_system_prompt(practice_level)

    # Build initial messages (without RAG - let LLM decide if it needs suttas)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": request.message})

    # Get API configuration
    model = os.environ.get(
        "LITELLM_MODEL", "anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    api_base = os.environ.get("ANTHROPIC_BASE_URL", "")
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

    # Import tool calling functions
    from dapr.clients import DaprClient
    from wisdom_service.tools import (
        TOOLS,
        call_anthropic_with_tools,
        execute_tool_calls,
        has_tool_use,
    )

    # First LLM call WITH tools
    response = await trio.to_thread.run_sync(
        lambda: call_anthropic_with_tools(
            messages[1:],  # Exclude system from messages array
            system_prompt,
            TOOLS,
            api_base,
            api_key,
            model,
        )
    )

    # Tool call loop (max 3 iterations)
    tool_use_count = 0
    while has_tool_use(response) and tool_use_count < 3:
        logger.info(f"Tool use detected, iteration {tool_use_count + 1}")

        # Execute tools with Dapr client
        def execute_tools():
            with DaprClient() as dapr_client:
                return execute_tool_calls(response, dapr_client, request.chat_id)

        tool_results = await trio.to_thread.run_sync(execute_tools)

        # Append assistant's response with tool use
        messages.append({"role": "assistant", "content": response["content"]})

        # Append tool results as user message
        messages.append({"role": "user", "content": tool_results})

        # Call LLM again with tool results
        response = await trio.to_thread.run_sync(
            lambda: call_anthropic_with_tools(
                messages[1:],  # Exclude system from messages array
                system_prompt,
                TOOLS,
                api_base,
                api_key,
                model,
            )
        )
        tool_use_count += 1

    # If no tools were called, fall back to mandatory RAG (existing behavior)
    if tool_use_count == 0:
        logger.info("No tools used, falling back to mandatory RAG")
        messages = await build_rag_prompt(
            user_message=request.message,
            system_prompt=system_prompt,
            history=history,
        )

        # Use existing fallback to raw httpx
        result = await trio.to_thread.run_sync(
            lambda: _call_anthropic_proxy(model, api_base, api_key, messages)
        )
        response_text = result["choices"][0]["message"]["content"]
    else:
        # Extract text from content blocks
        response_text = ""
        for block in response.get("content", []):
            if block.get("type") == "text":
                response_text += block.get("text", "")

    # Extract sutta citations and themes from response (simple heuristic)
    suttas_cited = _extract_sutta_citations(response_text)
    detected_themes = _extract_themes(request.message)

    # Store in cache (only if no tools were used)
    if tool_use_count == 0:
        await trio.to_thread.run_sync(
            lambda: langcache.store(request.message, response_text, practice_level)
        )

    return WisdomResponse(
        response=response_text,
        suttas_cited=suttas_cited,
        detected_themes=detected_themes,
        from_cache=False,
    )


def _extract_sutta_citations(text: str) -> list[str]:
    """Extract sutta references like SN56.11, MN10, DN22 from response text."""
    pattern = r"\b([A-Z]{2,3}\d+(?:\.\d+)?)\b"
    return list(set(re.findall(pattern, text)))


def _extract_themes(message: str) -> list[str]:
    """Simple keyword-based theme detection from user message."""
    theme_keywords = {
        "suffering": ["suffering", "dukkha", "pain", "sorrow"],
        "impermanence": ["impermanence", "anicca", "change", "passing"],
        "non-self": ["non-self", "anatta", "self", "ego", "identity"],
        "meditation": [
            "meditation",
            "meditate",
            "sit",
            "mindfulness",
            "sati",
            "samadhi",
            "jhana",
        ],
        "ethics": ["ethics", "sila", "precepts", "moral", "right action"],
        "compassion": ["compassion", "metta", "loving-kindness", "karuna"],
        "wisdom": ["wisdom", "panna", "understanding", "insight", "vipassana"],
        "dependent origination": [
            "dependent origination",
            "paticca samuppada",
            "conditions",
            "causation",
        ],
        "four noble truths": ["four noble truths", "noble truths", "eightfold path"],
        "nibbana": [
            "nibbana",
            "nirvana",
            "liberation",
            "enlightenment",
            "awakening",
        ],
    }
    message_lower = message.lower()
    return [
        theme
        for theme, keywords in theme_keywords.items()
        if any(kw in message_lower for kw in keywords)
    ]


async def main():
    config = Config()
    config.bind = ["0.0.0.0:8080"]
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve, app, config)
        await trio.to_thread.run_sync(wait_for_dapr_ready)


if __name__ == "__main__":
    trio.run(main)
