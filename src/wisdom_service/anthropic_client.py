"""Anthropic proxy client for Wisdom Service.

This module provides the fallback HTTP client for calling the Anthropic API
when the Dapr Conversation API is unavailable.

Extracted from openai_service_worldofgeese/__main__.py (Phase 1).
"""

import os
import time

import httpx


def _call_anthropic_proxy(model, api_base, api_key, messages):
    """Call Anthropic proxy via raw httpx, avoiding LiteLLM's incompatible headers.

    Anthropic proxy is a Bedrock proxy that expects Anthropic Messages API format
    but fails when both Authorization and x-api-key headers are present.
    LiteLLM always sends x-api-key for anthropic/ provider, so we use raw httpx.
    """
    url = f"{api_base}/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "anthropic-version": "2023-06-01",
    }

    # Convert messages to Anthropic format
    system_msg = None
    user_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            user_messages.append(msg)

    payload = {
        "model": model.replace("anthropic/", ""),  # Strip prefix for Anthropic proxy
        "max_tokens": 4096,
        "messages": [
            {"role": m["role"], "content": m["content"]} for m in user_messages
        ],
    }
    if system_msg:
        payload["system"] = system_msg

    with httpx.Client(timeout=60) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    # Convert Anthropic response to LiteLLM-compatible format
    return {
        "choices": [
            {
                "message": {
                    "content": data["content"][0]["text"],
                    "role": "assistant",
                },
                "finish_reason": data.get("stop_reason", "stop"),
            }
        ],
        "model": model,
        "usage": data.get("usage", {}),
    }


def wait_for_dapr_ready(dapr_port=3500, retries=20, delay=2):
    """Wait for the Dapr sidecar to be ready.

    Uses DAPR_HTTP_ENDPOINT if set (for separate-container sidecars),
    otherwise falls back to localhost (shared network namespace).
    """
    dapr_endpoint = os.environ.get(
        "DAPR_HTTP_ENDPOINT", f"http://localhost:{dapr_port}"
    ).rstrip("/")
    dapr_url = f"{dapr_endpoint}/v1.0/healthz"
    for _ in range(retries):
        try:
            response = httpx.get(dapr_url, timeout=5)
            if response.status_code == 204:
                print("Dapr is ready.")
                return
        except Exception as e:
            print(f"Dapr is not ready yet: {e}")
        time.sleep(delay)

    raise RuntimeError("Dapr sidecar is not ready.")
