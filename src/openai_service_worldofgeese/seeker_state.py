"""Conversation history management using Dapr state store."""

import json
from datetime import datetime, timezone

import trio
from dapr.clients import DaprClient


async def save_message(chat_id: str, role: str, content: str) -> None:
    """Append a message to conversation history in Dapr state store."""

    def _save():
        with DaprClient() as client:
            response = client.get_state(
                store_name="statestore", key=f"seeker:{chat_id}"
            )

            history = json.loads(response.data.decode("utf-8")) if response.data else []

            history.append(
                {
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            client.save_state(
                store_name="statestore",
                key=f"seeker:{chat_id}",
                value=json.dumps(history),
            )

    await trio.to_thread.run_sync(_save)  # type: ignore[call-non-callable]


async def get_history(chat_id: str, limit: int = 10) -> list[dict]:
    """Retrieve the last N messages from conversation history."""

    def _get():
        with DaprClient() as client:
            response = client.get_state(
                store_name="statestore", key=f"seeker:{chat_id}"
            )

            if not response.data:
                return []

            history = json.loads(response.data.decode("utf-8"))
            return history[-limit:] if len(history) > limit else history

    return await trio.to_thread.run_sync(_get)  # type: ignore[call-non-callable]


async def clear_history(chat_id: str) -> None:
    """Delete all conversation history for a chat."""

    def _clear():
        with DaprClient() as client:
            client.delete_state(store_name="statestore", key=f"seeker:{chat_id}")

    await trio.to_thread.run_sync(_clear)  # type: ignore[call-non-callable]
