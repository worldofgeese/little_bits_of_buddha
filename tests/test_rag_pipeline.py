"""Tests for the RAG pipeline module.

This module follows the How to Design Functions (HtDF) recipe:
1. Signature, purpose, stub
2. Examples (tests)
3. Examples (tests)
4. Template/inventory
5. Code body
6. Test and debug
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


class TestBuildRagPrompt:
    """Tests for the build_rag_prompt function.

    Signature:
        async def build_rag_prompt(
            chat_id: str,
            user_message: str,
            system_prompt: str,
        ) -> list[dict]

    Purpose:
        Build the full message list for the LLM call with RAG context.
        1. Load conversation history via seeker_state.get_history()
        2. Search for relevant suttas via sutta_search.search_suttas()
        3. Construct the message list with augmented system prompt
        4. Return ready for _call_lego_mps()

    Examples:
        - When suttas are found, system prompt includes sutta context
        - When history exists, messages include history + current message
        - When no suttas found, system prompt is unmodified
        - When sutta search fails, falls back to plain prompt
        - When state fails, falls back to no history
    """

    @pytest.mark.trio
    async def test_build_rag_prompt_includes_sutta_context(self):
        """Test that build_rag_prompt includes sutta text in system prompt."""
        from openai_service_worldofgeese.rag import build_rag_prompt

        # Mock search results
        mock_suttas = [
            {
                "id": "sn56.11",
                "title": "Setting in Motion the Wheel of the Dhamma",
                "text": "This is the first sermon where the Four Noble Truths were taught.",
                "collection": "Samyutta Nikaya",
                "themes": ["four_noble_truths"],
                "score": 0.95,
            },
            {
                "id": "mn10",
                "title": "Satipatthana Sutta",
                "text": "The foundations of mindfulness.",
                "collection": "Majjhima Nikaya",
                "themes": ["mindfulness"],
                "score": 0.88,
            },
        ]

        # Mock get_history to return empty
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=[],
            ),
            patch(
                "openai_service_worldofgeese.rag.search_suttas",
                return_value=mock_suttas,
            ),
        ):
            messages = await build_rag_prompt(
                chat_id="chat123",
                user_message="What are the Four Noble Truths?",
                system_prompt="You are the Buddha.",
            )

        # Verify system message includes sutta context
        assert len(messages) == 2  # system + user
        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert "You are the Buddha." in system_msg["content"]
        assert "Setting in Motion the Wheel of the Dhamma" in system_msg["content"]
        assert "sn56.11" in system_msg["content"]
        assert "first sermon" in system_msg["content"]
        assert "Satipatthana Sutta" in system_msg["content"]
        assert "mn10" in system_msg["content"]

        # Verify user message is present
        user_msg = messages[1]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == "What are the Four Noble Truths?"

    @pytest.mark.trio
    async def test_build_rag_prompt_includes_conversation_history(self):
        """Test that build_rag_prompt includes conversation history."""
        from openai_service_worldofgeese.rag import build_rag_prompt

        # Mock conversation history
        mock_history = [
            {
                "role": "user",
                "content": "What is dukkha?",
                "timestamp": "2026-03-03T12:00:00",
            },
            {
                "role": "assistant",
                "content": "Dukkha is suffering, the first noble truth.",
                "timestamp": "2026-03-03T12:01:00",
            },
            {
                "role": "user",
                "content": "Tell me more.",
                "timestamp": "2026-03-03T12:02:00",
            },
        ]

        # Mock search to return no suttas
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=mock_history,
            ),
            patch(
                "openai_service_worldofgeese.rag.search_suttas",
                return_value=[],
            ),
        ):
            messages = await build_rag_prompt(
                chat_id="chat123",
                user_message="Can you explain the path?",
                system_prompt="You are the Buddha.",
            )

        # Verify structure: system + history + current message
        assert len(messages) == 5  # system + 3 history + 1 current
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "What is dukkha?"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Dukkha is suffering, the first noble truth."
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "Tell me more."
        assert messages[4]["role"] == "user"
        assert messages[4]["content"] == "Can you explain the path?"

    @pytest.mark.trio
    async def test_build_rag_prompt_no_suttas_found(self):
        """Test that build_rag_prompt uses plain prompt when no suttas found."""
        from openai_service_worldofgeese.rag import build_rag_prompt

        # Mock search to return empty list
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=[],
            ),
            patch(
                "openai_service_worldofgeese.rag.search_suttas",
                return_value=[],
            ),
        ):
            messages = await build_rag_prompt(
                chat_id="chat123",
                user_message="Hello",
                system_prompt="You are the Buddha. Teach the Dhamma.",
            )

        # Verify system prompt is unmodified
        assert len(messages) == 2
        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert system_msg["content"] == "You are the Buddha. Teach the Dhamma."
        assert "following suttas" not in system_msg["content"]

    @pytest.mark.trio
    async def test_build_rag_prompt_sutta_search_fails_gracefully(self):
        """Test that build_rag_prompt handles sutta search failure."""
        from openai_service_worldofgeese.rag import build_rag_prompt

        # Mock search to raise exception
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=[],
            ),
            patch(
                "openai_service_worldofgeese.rag.search_suttas",
                side_effect=RuntimeError("Redis not available"),
            ),
        ):
            messages = await build_rag_prompt(
                chat_id="chat123",
                user_message="Hello",
                system_prompt="You are the Buddha.",
            )

        # Verify falls back to plain prompt
        assert len(messages) == 2
        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert system_msg["content"] == "You are the Buddha."
        assert "following suttas" not in system_msg["content"]

    @pytest.mark.trio
    async def test_build_rag_prompt_state_fails_gracefully(self):
        """Test that build_rag_prompt handles state store failure."""
        from openai_service_worldofgeese.rag import build_rag_prompt

        # Mock get_history to raise exception
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                side_effect=RuntimeError("Dapr not available"),
            ),
            patch(
                "openai_service_worldofgeese.rag.search_suttas",
                return_value=[],
            ),
        ):
            messages = await build_rag_prompt(
                chat_id="chat123",
                user_message="Hello",
                system_prompt="You are the Buddha.",
            )

        # Verify falls back to no history (just system + user message)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

    @pytest.mark.trio
    async def test_build_rag_prompt_handles_import_error(self):
        """Test that build_rag_prompt handles numpy import failures."""
        from openai_service_worldofgeese.rag import build_rag_prompt

        # Mock search to raise ImportError (numpy not available)
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=[],
            ),
            patch(
                "openai_service_worldofgeese.rag.search_suttas",
                side_effect=ImportError("numpy not available"),
            ),
        ):
            messages = await build_rag_prompt(
                chat_id="chat123",
                user_message="Hello",
                system_prompt="You are the Buddha.",
            )

        # Verify falls back to plain prompt
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are the Buddha."


class TestMessageHandlerUsesRagPrompt:
    """Test that the message handler integrates with build_rag_prompt."""

    @pytest.mark.trio
    async def test_message_handler_uses_rag_prompt(self):
        """Test that message handler calls build_rag_prompt and uses result."""
        from openai_service_worldofgeese.__main__ import _build_app

        # Mock the RAG prompt builder to return a specific message list
        mock_messages = [
            {"role": "system", "content": "System with suttas"},
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
            {"role": "user", "content": "What is the path?"},
        ]

        # Mock Dapr client for pub/sub (sync, not async)
        mock_dapr_client = Mock()
        mock_dapr_client.publish_event = Mock()
        mock_dapr_client.__enter__ = Mock(return_value=mock_dapr_client)
        mock_dapr_client.__exit__ = Mock(return_value=None)

        # Mock _call_lego_mps to verify it receives the RAG messages
        with (
            patch(
                "openai_service_worldofgeese.__main__.build_rag_prompt",
                return_value=mock_messages,
            ) as mock_build_rag,
            patch("openai_service_worldofgeese.__main__._call_lego_mps") as mock_lego,
            patch(
                "dapr.clients.DaprClient",
                return_value=mock_dapr_client,
            ),
            patch(
                "openai_service_worldofgeese.__main__.save_message",
                return_value=None,
            ),
            patch(
                "openai_service_worldofgeese.__main__.check_rate_limit",
                return_value=(True, None),
            ),
        ):
            mock_lego.return_value = {
                "choices": [{"message": {"content": "The Noble Eightfold Path."}}]
            }

            # Build app
            app, _ = _build_app()

            # Create a mock event
            from pydantic import BaseModel

            class MockCloudEvent(BaseModel):
                datacontenttype: str = "application/json"
                source: str = "test"
                topic: str = "messages"
                pubsubname: str = "redis-pubsub"
                data: dict = {"chat_id": "chat123", "text": "What is the path?"}
                id: str = "1"
                specversion: str = "1.0"
                tracestate: str = ""
                type: str = "com.dapr.event.sent"
                traceid: str = "00-123-456-00"

            # Note: This test verifies the integration
            # The actual call would require invoking the FastAPI route
            # For now, we verify that build_rag_prompt would be called
            # This test will fail until the integration is complete

        # Verify build_rag_prompt would be called with correct parameters
        # This assertion will fail until we implement the integration
        assert False, "Message handler integration with RAG not yet implemented"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
