"""Conversation history state management using Dapr state store.

This module provides functions to save and retrieve conversation history
for each chat_id using Dapr's state management building block.
"""

import json
from datetime import datetime, timezone

from dapr.clients import DaprClient


def save_message(chat_id: str, role: str, content: str) -> None:
    """Append a message to conversation history in Dapr state store.

    Args:
        chat_id: Unique identifier for the conversation
        role: Message role ("user" or "assistant")
        content: Message content text

    The message is stored as JSON with structure:
        {"role": str, "content": str, "timestamp": str}
    """
    key = f"seeker:{chat_id}"

    with DaprClient() as client:
        # Get existing history
        state = client.get_state(store_name="statestore", key=key)
        if state.data:
            history = json.loads(state.data)
        else:
            history = []

        # Append new message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        history.append(message)

        # Save back to state store
        client.save_state(
            store_name="statestore", key=key, value=json.dumps(history)
        )


def get_history(chat_id: str, limit: int = 10) -> list[dict]:
    """Retrieve the last N messages from conversation history.

    Args:
        chat_id: Unique identifier for the conversation
        limit: Maximum number of recent messages to return (default 10)

    Returns:
        List of message dictionaries, each containing:
        {"role": str, "content": str, "timestamp": str}
        Returns empty list if no history exists.
    """
    key = f"seeker:{chat_id}"

    with DaprClient() as client:
        state = client.get_state(store_name="statestore", key=key)
        if not state.data:
            return []

        history = json.loads(state.data)
        # Return last N messages
        return history[-limit:] if len(history) > limit else history


def clear_history(chat_id: str) -> None:
    """Reset conversation history by deleting all messages.

    Args:
        chat_id: Unique identifier for the conversation
    """
    key = f"seeker:{chat_id}"

    with DaprClient() as client:
        client.delete_state(store_name="statestore", key=key)
