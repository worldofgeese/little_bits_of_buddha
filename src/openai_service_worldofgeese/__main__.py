import json
import logging
import os
import time
import warnings

import httpx
import requests
import trio
from trio import TrioDeprecationWarning, to_thread

# Filter out any deprecation warnings
warnings.filterwarnings(action="ignore", category=TrioDeprecationWarning)


def _call_lego_mps(model, api_base, api_key, messages):
    """Call LEGO MPS via raw httpx, avoiding LiteLLM's incompatible headers.

    LEGO MPS is a Bedrock proxy that expects Anthropic Messages API format
    but fails when both Authorization and x-api-key headers are present.
    LiteLLM always sends x-api-key for anthropic/ provider, so we use raw httpx.
    """
    url = f"{api_base}/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
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
        "model": model.replace("anthropic/", ""),  # Strip prefix for LEGO MPS
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

    Arguments:
    dapr_port -- The port on which the Dapr sidecar is listening.
    retries -- The number of times to check if Dapr is ready before giving up.
    delay -- The delay between checks.
    """
    dapr_url = f"http://localhost:{dapr_port}/v1.0/healthz"
    for _ in range(retries):
        try:
            response = requests.get(dapr_url)
            if response.status_code == 204:
                print("Dapr is ready.")
                return
        except Exception as e:
            print(f"Dapr is not ready yet: {e}")
        time.sleep(delay)

    raise RuntimeError("Dapr sidecar is not ready.")


def _build_app():
    """Build the FastAPI app with Dapr integration. Heavy imports live here."""
    from dapr.clients import DaprClient
    from dapr.ext.fastapi import DaprApp
    from fastapi import FastAPI
    from pydantic import BaseModel

    from openai_service_worldofgeese import init_secrets

    app = FastAPI()
    dapr_app = DaprApp(app)

    class CloudEvent(BaseModel):
        datacontenttype: str
        source: str
        topic: str
        pubsubname: str
        data: dict
        id: str
        specversion: str
        tracestate: str
        type: str
        traceid: str

    @dapr_app.subscribe(pubsub="redis-pubsub", topic="messages")
    async def messages_subscriber(event: CloudEvent):
        logging.info(f"Received message: {event.data}")
        text = event.data.get("text")

        # Get the model from environment variable, default to Anthropic via LEGO MPS
        model = os.environ.get(
            "LITELLM_MODEL", "anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0"
        )
        api_base = os.environ.get(
            "ANTHROPIC_BASE_URL", "https://models.assistant.legogroup.io/claude"
        )
        api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN")

        # Use raw httpx for LEGO MPS (LiteLLM sends incompatible x-api-key header)
        response = _call_lego_mps(
            model=model,
            api_base=api_base,
            api_key=api_key,
            messages=[
                {
                    "role": "system",
                    "content": "You are the Buddha. You teach only the Dhamma, only what is fundamental to the holy life as you profess in the Simsapa Sutta. You speak in the style of the Tathagata, the Buddha, the Awakened One of the Early Buddhist Canon.",
                },
                {"role": "user", "content": text},
            ],
        )

        response_text = response["choices"][0]["message"]["content"]

        output_response = {
            "chat_id": event.data.get("chat_id"),
            "text": response_text,
        }

        with DaprClient() as dapr_client:
            dapr_client.publish_event(
                pubsub_name="redis-pubsub",
                topic_name="responses",
                data=json.dumps(output_response),
                data_content_type="application/json",
            )

        return {"success": True}

    return app, init_secrets


async def async_wait_for_dapr_ready(task_status=trio.TASK_STATUS_IGNORED):
    await to_thread.run_sync(wait_for_dapr_ready)
    task_status.started()


async def async_init_secrets(init_secrets_fn, task_status=trio.TASK_STATUS_IGNORED):
    await to_thread.run_sync(init_secrets_fn)
    task_status.started()


async def main():
    from hypercorn.config import Config
    from hypercorn.trio import serve

    app, init_secrets_fn = _build_app()
    config = Config()
    config.bind = ["0.0.0.0:8080"]

    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve, app, config)
        await nursery.start(async_wait_for_dapr_ready)
        await nursery.start(async_init_secrets, init_secrets_fn)


if __name__ == "__main__":
    trio.run(main)
