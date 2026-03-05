"""Dapr Conversation API client for Wisdom Service.

This module provides the primary LLM client using Dapr's Conversation API component.
Falls back to anthropic_client._call_anthropic_proxy() if unavailable.

The Conversation API is alpha and provides:
- Automatic caching (same question = cached answer, saves LLM costs)
- PII scrubbing
- Circuit breakers and retry logic
"""

import logging

from dapr.clients import DaprClient

logger = logging.getLogger(__name__)


def call_via_conversation_api(message: str, context: dict) -> dict:
    """Call LLM via Dapr Conversation API component.

    Uses the 'anthropic-conversation' component defined in .dapr/components/conversation.yaml.
    Benefits: caching, PII scrubbing, circuit breakers.

    Args:
        message: The user message to send
        context: Request context with practice_level, history, topics_explored

    Returns:
        dict with keys:
            - response: str - The LLM response text
            - cached: bool - Whether the response was cached (TODO: detect when API supports it)

    Raises:
        Exception: If the Conversation API is unavailable or the call fails
    """
    # NOTE: Dapr Conversation API is alpha. The Python SDK may not have client.converse() yet.
    # Check if the method exists, otherwise fall back to raw HTTP
    with DaprClient() as client:
        # Try to use the converse method if it exists
        if hasattr(client, "converse"):
            result = client.converse(
                name="anthropic-conversation",
                inputs=[{"message": message, "role": "user"}],
                # context and metadata as supported by the API
            )
            return {
                "response": result.outputs[0].result,
                "cached": False,  # TODO: detect cache hits when API supports it
            }
        else:
            # Fallback: implement as raw HTTP call
            import httpx
            import os

            dapr_endpoint = os.environ.get(
                "DAPR_HTTP_ENDPOINT", "http://localhost:3500"
            ).rstrip("/")
            url = f"{dapr_endpoint}/v1alpha1/conversation/anthropic-conversation/converse"

            payload = {
                "inputs": [{"message": message, "role": "user"}],
                "parameters": context,  # Pass practice level and other context
            }

            response = httpx.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            return {
                "response": data["outputs"][0]["result"],
                "cached": data.get("cached", False),
            }
