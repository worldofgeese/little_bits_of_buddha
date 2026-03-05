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

    messages = await build_rag_prompt(
        user_message=request.message,
        system_prompt=system_prompt,
        history=history,
    )

    # Try Dapr Conversation API first, fall back to raw httpx
    used_tools = False  # Currently we don't detect tool usage
    try:
        from wisdom_service.conversation_client import call_via_conversation_api

        result = await trio.to_thread.run_sync(
            lambda: call_via_conversation_api(request.message, request.context)
        )
        response_text = result["response"]
    except Exception as e:
        logger.warning(f"Conversation API failed: {e}. Falling back to raw httpx.")
        model = os.environ.get(
            "LITELLM_MODEL", "anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0"
        )
        api_base = os.environ.get("ANTHROPIC_BASE_URL", "")
        api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

        result = await trio.to_thread.run_sync(
            lambda: _call_anthropic_proxy(model, api_base, api_key, messages)
        )
        response_text = result["choices"][0]["message"]["content"]

    # Extract sutta citations and themes from response (simple heuristic)
    suttas_cited = _extract_sutta_citations(response_text)
    detected_themes = _extract_themes(request.message)

    # Store in cache (only if no tools were used)
    if not used_tools:
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
