"""Tests for Wisdom Service (WP2)

Test coverage:
1. /healthz returns 200
2. /wisdom/ask returns valid WisdomResponse shape
3. System prompt changes based on practice_level (newcomer vs experienced)
4. Sutta context is injected into messages by RAG
5. Sutta citation extraction from response text
6. Theme detection from user message
7. Fallback to raw httpx when Conversation API fails
8. Conversation API called first when available
9. Empty history handled gracefully
10. Missing practice_level defaults to "newcomer"
11. Long messages are handled without truncation errors
12. Concurrent requests don't interfere (stateless service)
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Import and return the FastAPI app."""
    from wisdom_service.__main__ import app

    return app


@pytest.fixture
def client(app):
    """Create a test client for the wisdom service."""
    return TestClient(app)


@pytest.fixture
def mock_sutta_results():
    """Mock sutta search results."""
    return [
        {
            "id": "SN56.11",
            "title": "Dhammacakkappavattana Sutta",
            "collection": "Samyutta Nikaya",
            "text": "This is the noble truth of suffering...",
            "themes": ["four noble truths", "suffering"],
            "score": 0.95,
        },
        {
            "id": "MN10",
            "title": "Satipatthana Sutta",
            "collection": "Majjhima Nikaya",
            "text": "Mindfulness of the body...",
            "themes": ["mindfulness", "meditation"],
            "score": 0.87,
        },
    ]


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": "Suffering arises from craving, as taught in SN56.11. Practice mindfulness as in MN10.",
                    "role": "assistant",
                },
                "finish_reason": "stop",
            }
        ],
        "model": "anthropic.claude-sonnet-4-5-20250929-v1:0",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


class TestHealthz:
    """Test the healthz endpoint."""

    def test_healthz_returns_200(self, client):
        """Test that /healthz returns 200 OK."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestWisdomAsk:
    """Test the /wisdom/ask endpoint."""

    @patch("wisdom_service.rag.build_rag_prompt")
    @patch("wisdom_service.__main__._call_anthropic_proxy")
    def test_wisdom_ask_returns_valid_response_shape(
        self, mock_proxy, mock_rag, client, mock_anthropic_response
    ):
        """Test that /wisdom/ask returns a valid WisdomResponse."""
        mock_rag.return_value = [
            {"role": "system", "content": "You are the Buddha."},
            {"role": "user", "content": "What is suffering?"},
        ]
        mock_proxy.return_value = mock_anthropic_response

        response = client.post(
            "/wisdom/ask",
            json={
                "chat_id": "test123",
                "message": "What is suffering?",
                "context": {
                    "practice_level": "newcomer",
                    "history": [],
                    "topics_explored": [],
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "suttas_cited" in data
        assert "detected_themes" in data
        assert isinstance(data["suttas_cited"], list)
        assert isinstance(data["detected_themes"], list)

    @patch("wisdom_service.rag.build_rag_prompt")
    @patch("wisdom_service.__main__._call_anthropic_proxy")
    def test_system_prompt_changes_with_practice_level_newcomer(
        self, mock_proxy, mock_rag, client, mock_anthropic_response
    ):
        """Test that system prompt adapts for newcomer practice level."""
        mock_rag.return_value = [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "test"},
        ]
        mock_proxy.return_value = mock_anthropic_response

        client.post(
            "/wisdom/ask",
            json={
                "chat_id": "test123",
                "message": "What is meditation?",
                "context": {"practice_level": "newcomer", "history": []},
            },
        )

        # Check that build_rag_prompt was called with the newcomer system prompt
        call_args = mock_rag.call_args
        assert (
            "encountering the Dhamma for the first time"
            in call_args.kwargs["system_prompt"]
        )

    @patch("wisdom_service.rag.build_rag_prompt")
    @patch("wisdom_service.__main__._call_anthropic_proxy")
    def test_system_prompt_changes_with_practice_level_experienced(
        self, mock_proxy, mock_rag, client, mock_anthropic_response
    ):
        """Test that system prompt adapts for experienced practice level."""
        mock_rag.return_value = [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "test"},
        ]
        mock_proxy.return_value = mock_anthropic_response

        client.post(
            "/wisdom/ask",
            json={
                "chat_id": "test123",
                "message": "Explain jhana factors.",
                "context": {"practice_level": "experienced", "history": []},
            },
        )

        call_args = mock_rag.call_args
        assert "experienced practitioner" in call_args.kwargs["system_prompt"]

    @patch("wisdom_service.sutta_search.search_suttas")
    @patch("wisdom_service.__main__._call_anthropic_proxy")
    def test_sutta_context_injected_by_rag(
        self,
        mock_proxy,
        mock_search,
        client,
        mock_sutta_results,
        mock_anthropic_response,
    ):
        """Test that sutta search results are injected into the RAG prompt."""
        mock_search.return_value = mock_sutta_results
        mock_proxy.return_value = mock_anthropic_response

        response = client.post(
            "/wisdom/ask",
            json={
                "chat_id": "test123",
                "message": "What is the first noble truth?",
                "context": {"practice_level": "beginner", "history": []},
            },
        )

        # Verify sutta_search was called
        mock_search.assert_called_once()
        # Verify response is successful
        assert response.status_code == 200

    def test_sutta_citation_extraction(self, client):
        """Test extraction of sutta citations from response text."""
        from wisdom_service.__main__ import _extract_sutta_citations

        text = (
            "As taught in SN56.11 and MN10, the path leads to DN22. See also AN4.170."
        )
        citations = _extract_sutta_citations(text)

        assert "SN56.11" in citations
        assert "MN10" in citations
        assert "DN22" in citations
        assert "AN4.170" in citations
        assert len(citations) == 4

    def test_theme_detection_from_user_message(self, client):
        """Test theme detection from user message keywords."""
        from wisdom_service.__main__ import _extract_themes

        # Test suffering theme
        themes = _extract_themes("I am experiencing so much suffering and pain")
        assert "suffering" in themes

        # Test meditation theme
        themes = _extract_themes("How do I practice mindfulness meditation?")
        assert "meditation" in themes

        # Test multiple themes
        themes = _extract_themes(
            "What is the relationship between suffering, impermanence, and non-self?"
        )
        assert "suffering" in themes
        assert "impermanence" in themes
        assert "non-self" in themes

    @patch("wisdom_service.conversation_client.call_via_conversation_api")
    @patch("wisdom_service.rag.build_rag_prompt")
    def test_conversation_api_called_first_when_available(
        self, mock_rag, mock_conversation_api, client
    ):
        """Test that Conversation API is tried first when available."""
        mock_rag.return_value = [{"role": "user", "content": "test"}]
        mock_conversation_api.return_value = {
            "response": "Test response from Conversation API",
            "cached": False,
        }

        response = client.post(
            "/wisdom/ask",
            json={
                "chat_id": "test123",
                "message": "Test message",
                "context": {"practice_level": "newcomer", "history": []},
            },
        )

        # Verify Conversation API was called
        mock_conversation_api.assert_called_once()
        assert response.status_code == 200
        assert "Test response from Conversation API" in response.json()["response"]

    @patch("wisdom_service.conversation_client.call_via_conversation_api")
    @patch("wisdom_service.__main__._call_anthropic_proxy")
    @patch("wisdom_service.rag.build_rag_prompt")
    def test_fallback_to_raw_httpx_when_conversation_api_fails(
        self,
        mock_rag,
        mock_proxy,
        mock_conversation_api,
        client,
        mock_anthropic_response,
    ):
        """Test fallback to raw httpx when Conversation API fails."""
        mock_rag.return_value = [{"role": "user", "content": "test"}]
        mock_conversation_api.side_effect = Exception("Conversation API unavailable")
        mock_proxy.return_value = mock_anthropic_response

        response = client.post(
            "/wisdom/ask",
            json={
                "chat_id": "test123",
                "message": "Test message",
                "context": {"practice_level": "newcomer", "history": []},
            },
        )

        # Verify fallback was used
        mock_proxy.assert_called_once()
        assert response.status_code == 200

    @patch("wisdom_service.rag.build_rag_prompt")
    @patch("wisdom_service.__main__._call_anthropic_proxy")
    def test_empty_history_handled_gracefully(
        self, mock_proxy, mock_rag, client, mock_anthropic_response
    ):
        """Test that empty history is handled without errors."""
        mock_rag.return_value = [{"role": "user", "content": "test"}]
        mock_proxy.return_value = mock_anthropic_response

        response = client.post(
            "/wisdom/ask",
            json={
                "chat_id": "test123",
                "message": "First message",
                "context": {"practice_level": "newcomer", "history": []},
            },
        )

        assert response.status_code == 200
        # Verify build_rag_prompt was called with empty history
        call_args = mock_rag.call_args
        assert call_args.kwargs["history"] == []

    @patch("wisdom_service.rag.build_rag_prompt")
    @patch("wisdom_service.__main__._call_anthropic_proxy")
    def test_missing_practice_level_defaults_to_newcomer(
        self, mock_proxy, mock_rag, client, mock_anthropic_response
    ):
        """Test that missing practice_level defaults to newcomer."""
        mock_rag.return_value = [{"role": "user", "content": "test"}]
        mock_proxy.return_value = mock_anthropic_response

        response = client.post(
            "/wisdom/ask",
            json={
                "chat_id": "test123",
                "message": "Test message",
                "context": {"history": []},  # No practice_level
            },
        )

        assert response.status_code == 200
        call_args = mock_rag.call_args
        assert (
            "encountering the Dhamma for the first time"
            in call_args.kwargs["system_prompt"]
        )

    @patch("wisdom_service.rag.build_rag_prompt")
    @patch("wisdom_service.__main__._call_anthropic_proxy")
    def test_long_messages_handled_without_truncation_errors(
        self, mock_proxy, mock_rag, client, mock_anthropic_response
    ):
        """Test that long messages are handled without errors."""
        mock_rag.return_value = [{"role": "user", "content": "test"}]
        mock_proxy.return_value = mock_anthropic_response

        long_message = "What is suffering? " * 500  # Very long message
        response = client.post(
            "/wisdom/ask",
            json={
                "chat_id": "test123",
                "message": long_message,
                "context": {"practice_level": "newcomer", "history": []},
            },
        )

        assert response.status_code == 200

    @patch("wisdom_service.rag.build_rag_prompt")
    @patch("wisdom_service.__main__._call_anthropic_proxy")
    def test_concurrent_requests_dont_interfere(
        self, mock_proxy, mock_rag, client, mock_anthropic_response
    ):
        """Test that concurrent requests are handled independently (stateless)."""
        mock_rag.return_value = [{"role": "user", "content": "test"}]
        mock_proxy.return_value = mock_anthropic_response

        # Make multiple requests with different chat_ids
        responses = []
        for i in range(5):
            response = client.post(
                "/wisdom/ask",
                json={
                    "chat_id": f"test{i}",
                    "message": f"Message {i}",
                    "context": {"practice_level": "newcomer", "history": []},
                },
            )
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200


class TestRAGModule:
    """Test the RAG module."""

    @pytest.mark.trio
    @patch("wisdom_service.sutta_search.search_suttas")
    async def test_build_rag_prompt_with_suttas(self, mock_search, mock_sutta_results):
        """Test that build_rag_prompt assembles messages with sutta context."""
        from wisdom_service.rag import build_rag_prompt

        mock_search.return_value = mock_sutta_results

        messages = await build_rag_prompt(
            user_message="What is suffering?",
            system_prompt="You are the Buddha.",
            history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Welcome"},
            ],
        )

        # Check structure
        assert messages[0]["role"] == "system"
        assert "You are the Buddha." in messages[0]["content"]
        assert "SN56.11" in messages[0]["content"]  # Sutta context injected
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Welcome"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "What is suffering?"

    @pytest.mark.trio
    @patch("wisdom_service.sutta_search.search_suttas")
    async def test_build_rag_prompt_graceful_fallback_no_suttas(self, mock_search):
        """Test graceful fallback when sutta search fails."""
        from wisdom_service.rag import build_rag_prompt

        mock_search.side_effect = Exception("Redis unavailable")

        messages = await build_rag_prompt(
            user_message="What is suffering?",
            system_prompt="You are the Buddha.",
            history=[],
        )

        # Should still return valid messages, just without sutta context
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


class TestPromptsModule:
    """Test the prompts module."""

    def test_get_system_prompt_for_all_levels(self):
        """Test that system prompts exist for all practice levels."""
        from wisdom_service.prompts import get_system_prompt

        levels = ["newcomer", "beginner", "intermediate", "experienced"]
        for level in levels:
            prompt = get_system_prompt(level)
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_get_system_prompt_defaults_to_newcomer(self):
        """Test that unknown practice levels default to newcomer."""
        from wisdom_service.prompts import get_system_prompt

        prompt = get_system_prompt("unknown_level")
        newcomer_prompt = get_system_prompt("newcomer")
        assert prompt == newcomer_prompt


class TestAnthropicClient:
    """Test the Anthropic client module."""

    @patch("httpx.Client")
    def test_call_anthropic_proxy_success(self, mock_httpx_client):
        """Test successful call to Anthropic proxy."""
        from wisdom_service.anthropic_client import _call_anthropic_proxy

        # Mock httpx response
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": [{"text": "This is the response"}],
            "stop_reason": "stop",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        mock_response.raise_for_status = Mock()

        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        result = _call_anthropic_proxy(
            model="anthropic/claude-sonnet",
            api_base="https://api.example.com",
            api_key="test-key",
            messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
            ],
        )

        assert result["choices"][0]["message"]["content"] == "This is the response"
        assert result["model"] == "anthropic/claude-sonnet"

    @patch("httpx.get")
    def test_wait_for_dapr_ready_success(self, mock_get):
        """Test successful Dapr ready check."""
        from wisdom_service.anthropic_client import wait_for_dapr_ready

        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response

        # Should not raise
        wait_for_dapr_ready(retries=1, delay=0)

    @patch("httpx.get")
    def test_wait_for_dapr_ready_timeout(self, mock_get):
        """Test Dapr ready check timeout."""
        from wisdom_service.anthropic_client import wait_for_dapr_ready

        mock_get.side_effect = Exception("Connection refused")

        with pytest.raises(RuntimeError, match="Dapr sidecar is not ready"):
            wait_for_dapr_ready(retries=2, delay=0)


class TestSuttaSearch:
    """Test the sutta_search module."""

    def test_embed_text_returns_vector(self):
        """Test that embed_text returns a vector of correct dimension."""
        from wisdom_service.sutta_search import EMBEDDING_DIM, embed_text

        text = "What is suffering?"
        embedding = embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == EMBEDDING_DIM
        assert all(isinstance(x, float) for x in embedding)

    @patch("wisdom_service.sutta_search.get_redis_client")
    def test_search_suttas_returns_results(self, mock_redis_client, mock_sutta_results):
        """Test that search_suttas returns formatted results."""
        from wisdom_service.sutta_search import search_suttas

        # Mock Redis search results
        mock_doc1 = Mock()
        mock_doc1.id = "sutta:SN56.11"
        mock_doc1.title = "Dhammacakkappavattana Sutta"
        mock_doc1.collection = "Samyutta Nikaya"
        mock_doc1.text = "This is the noble truth..."
        mock_doc1.themes = '["suffering"]'
        mock_doc1.score = 0.95

        mock_results = Mock()
        mock_results.docs = [mock_doc1]

        mock_client = Mock()
        mock_client.ft.return_value.search.return_value = mock_results
        mock_redis_client.return_value = mock_client

        results = search_suttas("What is suffering?", top_k=1)

        assert len(results) == 1
        assert results[0]["id"] == "SN56.11"
        assert results[0]["title"] == "Dhammacakkappavattana Sutta"
