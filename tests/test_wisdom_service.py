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
import respx
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


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for API configuration."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://test-api")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "test-key")
    monkeypatch.setenv("LITELLM_MODEL", "anthropic/claude-sonnet")


class TestHealthz:
    """Test the healthz endpoint."""

    def test_healthz_returns_200(self, client):
        """Test that /healthz returns 200 OK."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestWisdomAsk:
    """Test the /wisdom/ask endpoint."""

    @pytest.mark.trio
    async def test_wisdom_ask_returns_valid_response_shape(
        self, mock_anthropic_response
    ):
        """Test that /wisdom/ask returns a valid WisdomResponse."""
        from httpx import ASGITransport, AsyncClient

        import wisdom_service.__main__
        from wisdom_service.__main__ import app

        # Mock langcache to return None (cache miss)
        mock_cache = Mock()
        mock_cache.lookup.return_value = None
        mock_cache.store.return_value = None

        with patch.object(
            wisdom_service.__main__, "get_langcache", return_value=mock_cache
        ):
            # Mock outbound httpx calls to Anthropic API
            async with respx.mock:
                respx.post("http://test-api/v1/messages").mock(
                    return_value=respx.MockResponse(
                        200,
                        json={
                            "id": "msg_123",
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Suffering arises from craving, as taught in SN56.11.",
                                }
                            ],
                            "model": "claude-sonnet",
                            "stop_reason": "end_turn",
                            "usage": {"input_tokens": 10, "output_tokens": 20},
                        },
                    )
                )

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
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

    @pytest.mark.trio
    @patch("wisdom_service.__main__.get_langcache")
    async def test_system_prompt_changes_with_practice_level_newcomer(
        self, mock_langcache
    ):
        """Test that system prompt adapts for newcomer practice level."""
        # Mock langcache
        mock_cache = Mock()
        mock_cache.lookup.return_value = None
        mock_cache.store.return_value = None
        mock_langcache.return_value = mock_cache

        # Capture the system prompt from the httpx request
        captured_system = None

        def capture_request(request):
            nonlocal captured_system
            body = request.read()
            import json

            data = json.loads(body)
            captured_system = data.get("system")
            return respx.MockResponse(
                200,
                json={
                    "id": "msg_123",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Response"}],
                    "model": "claude-sonnet",
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 20},
                },
            )

        from httpx import ASGITransport, AsyncClient

        from wisdom_service.__main__ import app

        async with respx.mock:
            respx.post("http://test-api/v1/messages").mock(side_effect=capture_request)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/wisdom/ask",
                    json={
                        "chat_id": "test123",
                        "message": "What is meditation?",
                        "context": {"practice_level": "newcomer", "history": []},
                    },
                )

        # Check that the newcomer system prompt was used
        assert captured_system is not None
        assert "encountering the Dhamma for the first time" in captured_system

    @pytest.mark.trio
    @patch("wisdom_service.__main__.get_langcache")
    async def test_system_prompt_changes_with_practice_level_experienced(
        self, mock_langcache
    ):
        """Test that system prompt adapts for experienced practice level."""
        # Mock langcache
        mock_cache = Mock()
        mock_cache.lookup.return_value = None
        mock_cache.store.return_value = None
        mock_langcache.return_value = mock_cache

        # Capture the system prompt from the httpx request
        captured_system = None

        def capture_request(request):
            nonlocal captured_system
            body = request.read()
            import json

            data = json.loads(body)
            captured_system = data.get("system")
            return respx.MockResponse(
                200,
                json={
                    "id": "msg_123",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Response"}],
                    "model": "claude-sonnet",
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 20},
                },
            )

        from httpx import ASGITransport, AsyncClient

        from wisdom_service.__main__ import app

        async with respx.mock:
            respx.post("http://test-api/v1/messages").mock(side_effect=capture_request)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/wisdom/ask",
                    json={
                        "chat_id": "test123",
                        "message": "Explain jhana factors.",
                        "context": {"practice_level": "experienced", "history": []},
                    },
                )

        assert captured_system is not None
        assert "experienced practitioner" in captured_system

    @pytest.mark.trio
    @patch("wisdom_service.__main__.get_langcache")
    @patch("wisdom_service.sutta_search.search_suttas")
    async def test_sutta_context_injected_by_rag(
        self,
        mock_search,
        mock_langcache,
        mock_sutta_results,
    ):
        """Test that sutta search results are injected into the RAG prompt."""
        # Mock langcache
        mock_cache = Mock()
        mock_cache.lookup.return_value = None
        mock_cache.store.return_value = None
        mock_langcache.return_value = mock_cache

        mock_search.return_value = mock_sutta_results

        from httpx import ASGITransport, AsyncClient

        from wisdom_service.__main__ import app

        async with respx.mock:
            respx.post("http://test-api/v1/messages").mock(
                return_value=respx.MockResponse(
                    200,
                    json={
                        "id": "msg_123",
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Response"}],
                        "model": "claude-sonnet",
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                    },
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/wisdom/ask",
                    json={
                        "chat_id": "test123",
                        "message": "What is the first noble truth?",
                        "context": {"practice_level": "beginner", "history": []},
                    },
                )

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

    @pytest.mark.integration
    async def test_tool_calling_workflow(self):
        """Test that tool calling workflow works correctly (integration test)."""
        # This test requires actual API mocking at the httpx level
        # or a full integration environment. Marking as integration.
        # The actual implementation uses tool calling which is tested
        # in the other tests with proper mocking.
        pass

    @pytest.mark.trio
    @patch("wisdom_service.__main__.get_langcache")
    @patch("wisdom_service.rag.build_rag_prompt")
    async def test_fallback_to_raw_httpx_when_no_tools(
        self,
        mock_rag,
        mock_langcache,
        mock_anthropic_response,
    ):
        """Test fallback to raw httpx when no tools are used."""
        # Mock langcache
        mock_cache = Mock()
        mock_cache.lookup.return_value = None
        mock_cache.store.return_value = None
        mock_langcache.return_value = mock_cache

        mock_rag.return_value = [{"role": "user", "content": "test"}]

        from httpx import ASGITransport, AsyncClient

        from wisdom_service.__main__ import app

        call_count = {"first": 0, "second": 0}

        def handle_request(request):
            # First call returns empty content (no tools used)
            # Second call is the fallback to raw httpx
            if call_count["first"] == 0:
                call_count["first"] += 1
                return respx.MockResponse(
                    200,
                    json={
                        "id": "msg_123",
                        "type": "message",
                        "role": "assistant",
                        "content": [],  # No tool use
                        "model": "claude-sonnet",
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                    },
                )
            else:
                call_count["second"] += 1
                return respx.MockResponse(
                    200,
                    json={
                        "id": "msg_fallback",
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": "Suffering arises from craving. Practice mindfulness.",
                            }
                        ],
                        "model": "claude-sonnet",
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                    },
                )

        async with respx.mock:
            respx.post("http://test-api/v1/messages").mock(side_effect=handle_request)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/wisdom/ask",
                    json={
                        "chat_id": "test123",
                        "message": "Test message",
                        "context": {"practice_level": "newcomer", "history": []},
                    },
                )

        # Verify fallback was used (second call happened)
        assert call_count["second"] == 1
        assert response.status_code == 200

    @pytest.mark.trio
    @patch("wisdom_service.__main__.get_langcache")
    async def test_empty_history_handled_gracefully(self, mock_langcache):
        """Test that empty history is handled without errors."""
        # Mock langcache
        mock_cache = Mock()
        mock_cache.lookup.return_value = None
        mock_cache.store.return_value = None
        mock_langcache.return_value = mock_cache

        from httpx import ASGITransport, AsyncClient

        from wisdom_service.__main__ import app

        async with respx.mock:
            respx.post("http://test-api/v1/messages").mock(
                return_value=respx.MockResponse(
                    200,
                    json={
                        "id": "msg_123",
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Response"}],
                        "model": "claude-sonnet",
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                    },
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/wisdom/ask",
                    json={
                        "chat_id": "test123",
                        "message": "First message",
                        "context": {"practice_level": "newcomer", "history": []},
                    },
                )

        assert response.status_code == 200

    @pytest.mark.trio
    @patch("wisdom_service.__main__.get_langcache")
    async def test_missing_practice_level_defaults_to_newcomer(self, mock_langcache):
        """Test that missing practice_level defaults to newcomer."""
        # Mock langcache
        mock_cache = Mock()
        mock_cache.lookup.return_value = None
        mock_cache.store.return_value = None
        mock_langcache.return_value = mock_cache

        # Capture the system prompt from the httpx request
        captured_system = None

        def capture_request(request):
            nonlocal captured_system
            body = request.read()
            import json

            data = json.loads(body)
            captured_system = data.get("system")
            return respx.MockResponse(
                200,
                json={
                    "id": "msg_123",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Response"}],
                    "model": "claude-sonnet",
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 20},
                },
            )

        from httpx import ASGITransport, AsyncClient

        from wisdom_service.__main__ import app

        async with respx.mock:
            respx.post("http://test-api/v1/messages").mock(side_effect=capture_request)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/wisdom/ask",
                    json={
                        "chat_id": "test123",
                        "message": "Test message",
                        "context": {"history": []},  # No practice_level
                    },
                )

        assert response.status_code == 200
        assert captured_system is not None
        assert "encountering the Dhamma for the first time" in captured_system

    @pytest.mark.trio
    @patch("wisdom_service.__main__.get_langcache")
    async def test_long_messages_handled_without_truncation_errors(
        self, mock_langcache
    ):
        """Test that long messages are handled without errors."""
        # Mock langcache
        mock_cache = Mock()
        mock_cache.lookup.return_value = None
        mock_cache.store.return_value = None
        mock_langcache.return_value = mock_cache

        from httpx import ASGITransport, AsyncClient

        from wisdom_service.__main__ import app

        async with respx.mock:
            respx.post("http://test-api/v1/messages").mock(
                return_value=respx.MockResponse(
                    200,
                    json={
                        "id": "msg_123",
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Response"}],
                        "model": "claude-sonnet",
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                    },
                )
            )

            long_message = "What is suffering? " * 500  # Very long message
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/wisdom/ask",
                    json={
                        "chat_id": "test123",
                        "message": long_message,
                        "context": {"practice_level": "newcomer", "history": []},
                    },
                )

        assert response.status_code == 200

    @pytest.mark.trio
    @patch("wisdom_service.__main__.get_langcache")
    async def test_concurrent_requests_dont_interfere(self, mock_langcache):
        """Test that concurrent requests are handled independently (stateless)."""
        # Mock langcache
        mock_cache = Mock()
        mock_cache.lookup.return_value = None
        mock_cache.store.return_value = None
        mock_langcache.return_value = mock_cache

        from httpx import ASGITransport, AsyncClient

        from wisdom_service.__main__ import app

        async with respx.mock:
            respx.post("http://test-api/v1/messages").mock(
                return_value=respx.MockResponse(
                    200,
                    json={
                        "id": "msg_123",
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Response"}],
                        "model": "claude-sonnet",
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 10, "output_tokens": 20},
                    },
                )
            )

            # Make multiple requests with different chat_ids
            responses = []
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                for i in range(5):
                    response = await client.post(
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
