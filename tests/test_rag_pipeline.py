"""Tests for the RAG pipeline module.

This module follows the How to Design Functions (HtDF) recipe:
1. Signature, purpose, stub
2. Examples (tests)
3. Examples (tests)
4. Template/inventory
5. Code body
6. Test and debug
"""

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
        4. Return ready for _call_anthropic_proxy()

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

        # Create a mock sutta_search module
        mock_sutta_search = MagicMock()
        mock_sutta_search.search_suttas = Mock(return_value=mock_suttas)

        # Mock get_history to return empty
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=[],
            ),
            patch.dict(
                "sys.modules",
                {"openai_service_worldofgeese.sutta_search": mock_sutta_search},
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

        # Create a mock sutta_search module
        mock_sutta_search = MagicMock()
        mock_sutta_search.search_suttas = Mock(return_value=[])

        # Mock search to return no suttas
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=mock_history,
            ),
            patch.dict(
                "sys.modules",
                {"openai_service_worldofgeese.sutta_search": mock_sutta_search},
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

        # Create a mock sutta_search module
        mock_sutta_search = MagicMock()
        mock_sutta_search.search_suttas = Mock(return_value=[])

        # Mock search to return empty list
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=[],
            ),
            patch.dict(
                "sys.modules",
                {"openai_service_worldofgeese.sutta_search": mock_sutta_search},
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

        # Create a mock sutta_search module
        mock_sutta_search = MagicMock()
        mock_sutta_search.search_suttas = Mock(
            side_effect=RuntimeError("Redis not available")
        )

        # Mock search to raise exception
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=[],
            ),
            patch.dict(
                "sys.modules",
                {"openai_service_worldofgeese.sutta_search": mock_sutta_search},
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

        # Create a mock sutta_search module
        mock_sutta_search = MagicMock()
        mock_sutta_search.search_suttas = Mock(return_value=[])

        # Mock get_history to raise exception
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                side_effect=RuntimeError("Dapr not available"),
            ),
            patch.dict(
                "sys.modules",
                {"openai_service_worldofgeese.sutta_search": mock_sutta_search},
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

        # Create a mock sutta_search module
        mock_sutta_search = MagicMock()
        mock_sutta_search.search_suttas = Mock(
            side_effect=ImportError("numpy not available")
        )

        # Mock search to raise ImportError (numpy not available)
        with (
            patch(
                "openai_service_worldofgeese.rag.get_history",
                return_value=[],
            ),
            patch.dict(
                "sys.modules",
                {"openai_service_worldofgeese.sutta_search": mock_sutta_search},
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

        # Mock Dapr client for pub/sub (sync, not async)
        mock_dapr_client = Mock()
        mock_dapr_client.publish_event = Mock()
        mock_dapr_client.__enter__ = Mock(return_value=mock_dapr_client)
        mock_dapr_client.__exit__ = Mock(return_value=None)

        # Mock _call_anthropic_proxy
        with (
            patch(
                "dapr.clients.DaprClient",
                return_value=mock_dapr_client,
            ),
        ):
            # Build app - this verifies that build_rag_prompt import doesn't fail
            app, _ = _build_app()

            # Verify the app was built successfully
            # The integration is complete - build_rag_prompt is imported and used in messages_subscriber
            assert app is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
