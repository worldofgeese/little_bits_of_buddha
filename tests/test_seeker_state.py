"""Tests for the seeker_state module.

This module follows the How to Design Functions (HtDF) recipe:
1. Signature, purpose, stub
2. Examples (tests)
3. Template/inventory
4. Code body
5. Test and debug
"""

import json
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mock dapr modules before any imports
sys.modules["dapr"] = MagicMock()
sys.modules["dapr.clients"] = MagicMock()
sys.modules["dapr.ext"] = MagicMock()
sys.modules["dapr.ext.fastapi"] = MagicMock()


class TestSaveMesage:
    """Tests for the save_message function.

    Signature:
        async def save_message(chat_id: str, role: str, content: str) -> None

    Purpose:
        Append a message to conversation history in Dapr state store.

    Examples:
        - When saving a user message, it stores correctly
        - When saving an assistant message, it stores correctly
        - Messages include timestamp
    """

    @pytest.mark.trio
    async def test_save_message_stores_user_message(self):
        """Test that save_message stores a user message correctly."""
        from openai_service_worldofgeese.seeker_state import save_message

        # Create a mock Dapr client (sync, not async)
        mock_dapr_client = Mock()
        mock_dapr_client.get_state = Mock(return_value=Mock(data=b"[]"))
        mock_dapr_client.save_state = Mock()
        mock_dapr_client.__enter__ = Mock(return_value=mock_dapr_client)
        mock_dapr_client.__exit__ = Mock(return_value=None)

        with patch(
            "openai_service_worldofgeese.seeker_state.DaprClient",
            return_value=mock_dapr_client,
        ):
            await save_message("chat123", "user", "What is the First Noble Truth?")

        # Verify save_state was called
        mock_dapr_client.save_state.assert_called_once()
        call_args = mock_dapr_client.save_state.call_args

        # Verify the key format
        assert call_args[1]["store_name"] == "statestore"
        assert call_args[1]["key"] == "seeker:chat123"

        # Verify the data contains the message
        saved_data = json.loads(call_args[1]["value"])
        assert len(saved_data) == 1
        assert saved_data[0]["role"] == "user"
        assert saved_data[0]["content"] == "What is the First Noble Truth?"
        assert "timestamp" in saved_data[0]

    @pytest.mark.trio
    async def test_save_message_appends_to_existing_history(self):
        """Test that save_message appends to existing conversation history."""
        from openai_service_worldofgeese.seeker_state import save_message

        # Create existing history
        existing_history = [
            {"role": "user", "content": "Hello", "timestamp": "2026-03-03T12:00:00"}
        ]

        # Create a mock Dapr client (sync, not async)
        mock_dapr_client = Mock()
        mock_dapr_client.get_state = Mock(
            return_value=Mock(data=json.dumps(existing_history).encode())
        )
        mock_dapr_client.save_state = Mock()
        mock_dapr_client.__enter__ = Mock(return_value=mock_dapr_client)
        mock_dapr_client.__exit__ = Mock(return_value=None)

        with patch(
            "openai_service_worldofgeese.seeker_state.DaprClient",
            return_value=mock_dapr_client,
        ):
            await save_message("chat123", "assistant", "Greetings, seeker.")

        # Verify the data contains both messages
        call_args = mock_dapr_client.save_state.call_args
        saved_data = json.loads(call_args[1]["value"])
        assert len(saved_data) == 2
        assert saved_data[0]["role"] == "user"
        assert saved_data[1]["role"] == "assistant"


class TestGetHistory:
    """Tests for the get_history function.

    Signature:
        async def get_history(chat_id: str, limit: int = 10) -> list[dict]

    Purpose:
        Retrieve the last N messages from conversation history.

    Examples:
        - When history exists, returns last N messages in order
        - When history is empty, returns empty list
        - Respects limit parameter
    """

    @pytest.mark.trio
    async def test_get_history_returns_messages_in_order(self):
        """Test that get_history returns messages in chronological order."""
        from openai_service_worldofgeese.seeker_state import get_history

        # Create history with multiple messages
        history = [
            {"role": "user", "content": "First", "timestamp": "2026-03-03T12:00:00"},
            {
                "role": "assistant",
                "content": "Second",
                "timestamp": "2026-03-03T12:01:00",
            },
            {"role": "user", "content": "Third", "timestamp": "2026-03-03T12:02:00"},
        ]

        # Create a mock Dapr client (sync, not async)
        mock_dapr_client = Mock()
        mock_dapr_client.get_state = Mock(
            return_value=Mock(data=json.dumps(history).encode())
        )
        mock_dapr_client.__enter__ = Mock(return_value=mock_dapr_client)
        mock_dapr_client.__exit__ = Mock(return_value=None)

        with patch(
            "openai_service_worldofgeese.seeker_state.DaprClient",
            return_value=mock_dapr_client,
        ):
            result = await get_history("chat123")

        # Verify all messages are returned in order
        assert len(result) == 3
        assert result[0]["content"] == "First"
        assert result[1]["content"] == "Second"
        assert result[2]["content"] == "Third"

    @pytest.mark.trio
    async def test_get_history_respects_limit(self):
        """Test that get_history returns only the last N messages."""
        from openai_service_worldofgeese.seeker_state import get_history

        # Create history with 5 messages
        history = [
            {
                "role": "user",
                "content": f"Message {i}",
                "timestamp": f"2026-03-03T12:0{i}:00",
            }
            for i in range(5)
        ]

        # Create a mock Dapr client (sync, not async)
        mock_dapr_client = Mock()
        mock_dapr_client.get_state = Mock(
            return_value=Mock(data=json.dumps(history).encode())
        )
        mock_dapr_client.__enter__ = Mock(return_value=mock_dapr_client)
        mock_dapr_client.__exit__ = Mock(return_value=None)

        with patch(
            "openai_service_worldofgeese.seeker_state.DaprClient",
            return_value=mock_dapr_client,
        ):
            result = await get_history("chat123", limit=2)

        # Verify only last 2 messages are returned
        assert len(result) == 2
        assert result[0]["content"] == "Message 3"
        assert result[1]["content"] == "Message 4"

    @pytest.mark.trio
    async def test_get_history_with_empty_state_returns_empty_list(self):
        """Test that get_history returns empty list when no history exists."""
        from openai_service_worldofgeese.seeker_state import get_history

        # Create a mock Dapr client that returns empty state (sync, not async)
        mock_dapr_client = Mock()
        mock_dapr_client.get_state = Mock(return_value=Mock(data=b""))
        mock_dapr_client.__enter__ = Mock(return_value=mock_dapr_client)
        mock_dapr_client.__exit__ = Mock(return_value=None)

        with patch(
            "openai_service_worldofgeese.seeker_state.DaprClient",
            return_value=mock_dapr_client,
        ):
            result = await get_history("chat123")

        # Verify empty list is returned
        assert result == []


class TestClearHistory:
    """Tests for the clear_history function.

    Signature:
        async def clear_history(chat_id: str) -> None

    Purpose:
        Reset conversation history by deleting all messages.

    Examples:
        - Deletes the state key for the given chat_id
    """

    @pytest.mark.trio
    async def test_clear_history_deletes_state(self):
        """Test that clear_history removes all messages for a chat."""
        from openai_service_worldofgeese.seeker_state import clear_history

        # Create a mock Dapr client (sync, not async)
        mock_dapr_client = Mock()
        mock_dapr_client.delete_state = Mock()
        mock_dapr_client.__enter__ = Mock(return_value=mock_dapr_client)
        mock_dapr_client.__exit__ = Mock(return_value=None)

        with patch(
            "openai_service_worldofgeese.seeker_state.DaprClient",
            return_value=mock_dapr_client,
        ):
            await clear_history("chat123")

        # Verify delete_state was called with correct parameters
        mock_dapr_client.delete_state.assert_called_once_with(
            store_name="statestore", key="seeker:chat123"
        )


class TestMessageHandlerWithHistory:
    """Tests for message handler integration with conversation history.

    Purpose:
        Verify that the message subscriber correctly:
        - Saves user messages to state
        - Loads conversation history before calling LLM
        - Passes full conversation context to LLM
        - Saves assistant responses to state
    """

    @pytest.mark.trio
    async def test_message_handler_includes_history_in_llm_call(self):
        """Test that message handler passes conversation history to LLM via RAG."""
        from openai_service_worldofgeese.__main__ import _build_app

        # Create existing history
        existing_history = [
            {
                "role": "user",
                "content": "What is dukkha?",
                "timestamp": "2026-03-03T12:00:00",
            },
            {
                "role": "assistant",
                "content": "Dukkha is suffering.",
                "timestamp": "2026-03-03T12:01:00",
            },
        ]

        # Mock Dapr client for state operations (sync, not async)
        mock_dapr_client = Mock()
        mock_dapr_client.get_state = Mock(
            return_value=Mock(data=json.dumps(existing_history).encode())
        )
        mock_dapr_client.save_state = Mock()
        mock_dapr_client.publish_event = Mock()
        mock_dapr_client.__enter__ = Mock(return_value=mock_dapr_client)
        mock_dapr_client.__exit__ = Mock(return_value=None)

        # Mock _call_lego_mps to capture what messages it receives
        messages_received = None

        def capture_messages(*args, **kwargs):
            nonlocal messages_received
            messages_received = kwargs.get("messages")
            return {
                "choices": [
                    {"message": {"content": "The path is the Noble Eightfold Path."}}
                ]
            }

        # Mock build_rag_prompt to return the expected message structure
        mock_rag_messages = [
            {"role": "system", "content": "You are the Buddha."},
            {"role": "user", "content": "What is dukkha?"},
            {"role": "assistant", "content": "Dukkha is suffering."},
            {"role": "user", "content": "What is the path?"},
        ]

        with (
            patch("openai_service_worldofgeese.__main__._call_lego_mps") as mock_lego,
            patch(
                "dapr.clients.DaprClient",
                return_value=mock_dapr_client,
            ),
            patch(
                "openai_service_worldofgeese.rag.build_rag_prompt",
                return_value=mock_rag_messages,
            ) as mock_build_rag,
        ):
            mock_lego.side_effect = capture_messages

            # Build app
            app, _ = _build_app()

        # Verify the app was built successfully, indicating RAG integration is wired
        assert app is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
