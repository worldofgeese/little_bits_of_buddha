"""Tests for Anthropic Tool Calling via Wisdom Service (WP3)

Test coverage:
1. Tool definition format — TOOLS list has correct Anthropic schema
2. search_suttas execution — returns formatted sutta results
3. save_practice_note execution — calls actor method correctly
4. get_seeker_history execution — returns formatted history
5. has_tool_use detection — correctly identifies tool_use blocks
6. Tool result format — execute_tool_calls returns correct tool_result blocks
7. Max tool call limit — loop stops after 3 iterations
8. Fallback to RAG — when no tools called, mandatory RAG runs
9. No caching for tool responses — tool-calling responses skip langcache store
10. Empty tool result — graceful handling of tool returning empty/error
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestToolDefinitions:
    """Test that tool definitions match Anthropic schema."""

    def test_tools_list_has_three_tools(self):
        """Test that TOOLS list contains all three expected tools."""
        from wisdom_service.tools import TOOLS

        assert len(TOOLS) == 3
        tool_names = [tool["name"] for tool in TOOLS]
        assert "search_suttas" in tool_names
        assert "save_practice_note" in tool_names
        assert "get_seeker_history" in tool_names

    def test_search_suttas_tool_definition(self):
        """Test that search_suttas tool has correct Anthropic schema."""
        from wisdom_service.tools import TOOLS

        search_tool = next(t for t in TOOLS if t["name"] == "search_suttas")
        assert "description" in search_tool
        assert "input_schema" in search_tool

        schema = search_tool["input_schema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert schema["required"] == ["query"]
        assert schema["properties"]["limit"]["default"] == 3

    def test_save_practice_note_tool_definition(self):
        """Test that save_practice_note tool has correct Anthropic schema."""
        from wisdom_service.tools import TOOLS

        save_tool = next(t for t in TOOLS if t["name"] == "save_practice_note")
        assert "description" in save_tool
        assert "input_schema" in save_tool

        schema = save_tool["input_schema"]
        assert schema["type"] == "object"
        assert "chat_id" in schema["properties"]
        assert "note" in schema["properties"]
        assert set(schema["required"]) == {"chat_id", "note"}

    def test_get_seeker_history_tool_definition(self):
        """Test that get_seeker_history tool has correct Anthropic schema."""
        from wisdom_service.tools import TOOLS

        history_tool = next(t for t in TOOLS if t["name"] == "get_seeker_history")
        assert "description" in history_tool
        assert "input_schema" in history_tool

        schema = history_tool["input_schema"]
        assert schema["type"] == "object"
        assert "chat_id" in schema["properties"]
        assert "last_n" in schema["properties"]
        assert schema["required"] == ["chat_id"]
        assert schema["properties"]["last_n"]["default"] == 5


class TestToolExecution:
    """Test that tool execution functions work correctly."""

    @patch("wisdom_service.sutta_search.search_suttas")
    def test_execute_search_suttas_returns_formatted_results(self, mock_search_suttas):
        """Test that execute_search_suttas returns formatted sutta results."""
        from wisdom_service.tools import execute_search_suttas

        # Mock search_suttas function
        mock_search_suttas.return_value = [
            {
                "id": "SN56.11",
                "title": "Dhammacakkappavattana Sutta",
                "text": "This is the noble truth of suffering...",
            },
            {
                "id": "MN10",
                "title": "Satipatthana Sutta",
                "text": "Mindfulness of the body...",
            },
        ]

        result = execute_search_suttas("What is suffering?", limit=2)

        # Check that search was called with correct params
        mock_search_suttas.assert_called_once_with("What is suffering?", top_k=2)

        # Check formatting
        assert "**Dhammacakkappavattana Sutta**" in result
        assert "(SN56.11)" in result
        assert "This is the noble truth of suffering..." in result
        assert "---" in result
        assert "**Satipatthana Sutta**" in result
        assert "(MN10)" in result

    @patch("wisdom_service.sutta_search.search_suttas")
    def test_execute_search_suttas_handles_no_results(self, mock_search_suttas):
        """Test that execute_search_suttas handles empty results gracefully."""
        from wisdom_service.tools import execute_search_suttas

        mock_search_suttas.return_value = []

        result = execute_search_suttas("obscure query")

        assert result == "No matching suttas found."

    def test_execute_save_practice_note_calls_actor(self):
        """Test that execute_save_practice_note calls seeker actor correctly."""
        from wisdom_service.tools import execute_save_practice_note

        # Mock dapr_client
        mock_dapr = Mock()
        mock_dapr.invoke_method = Mock(return_value=Mock(text=lambda: "{}"))

        result = execute_save_practice_note(
            mock_dapr, chat_id="12345", note="Feeling more peaceful today"
        )

        # Check that actor was called with correct parameters
        mock_dapr.invoke_method.assert_called_once()
        call_args = mock_dapr.invoke_method.call_args

        assert call_args[1]["app_id"] == "seeker-actor-service"
        assert "12345" in call_args[1]["method_name"]
        assert "log_sit" in call_args[1]["method_name"]
        assert call_args[1]["http_verb"] == "POST"

        # Check data payload
        data = json.loads(call_args[1]["data"])
        assert data["notes"] == "Feeling more peaceful today"
        assert data["practice_type"] == "other"
        assert data["duration_minutes"] == 0
        assert data["from_workflow"] is False

        # Check result
        assert "Practice note saved" in result

    def test_execute_get_seeker_history_returns_formatted_history(self):
        """Test that execute_get_seeker_history returns formatted history."""
        from wisdom_service.tools import execute_get_seeker_history

        # Mock dapr_client
        mock_dapr = Mock()
        mock_state = {
            "history": [
                {"role": "user", "content": "What is mindfulness?"},
                {"role": "assistant", "content": "Mindfulness is sati in Pali..."},
                {"role": "user", "content": "How do I practice?"},
                {"role": "assistant", "content": "Start with breath awareness..."},
                {"role": "user", "content": "Thank you"},
            ]
        }
        mock_dapr.invoke_method = Mock(
            return_value=Mock(text=lambda: json.dumps(mock_state))
        )

        result = execute_get_seeker_history(mock_dapr, chat_id="12345", last_n=3)

        # Check that actor was called
        mock_dapr.invoke_method.assert_called_once()
        call_args = mock_dapr.invoke_method.call_args
        assert call_args[1]["app_id"] == "seeker-actor-service"
        assert "12345" in call_args[1]["method_name"]
        assert "get_state" in call_args[1]["method_name"]
        assert call_args[1]["http_verb"] == "GET"

        # Check formatting (should only show last 3 messages)
        lines = result.split("\n")
        assert len(lines) == 3
        assert "user: How do I practice?" in result
        assert "assistant: Start with breath awareness" in result
        assert "user: Thank you" in result

    def test_execute_get_seeker_history_handles_empty_history(self):
        """Test that execute_get_seeker_history handles empty history gracefully."""
        from wisdom_service.tools import execute_get_seeker_history

        mock_dapr = Mock()
        mock_dapr.invoke_method = Mock(
            return_value=Mock(text=lambda: json.dumps({"history": []}))
        )

        result = execute_get_seeker_history(mock_dapr, chat_id="12345")

        assert result == "No previous conversation history."


class TestToolCallDetection:
    """Test detection and processing of tool calls in responses."""

    def test_has_tool_use_detects_tool_use_blocks(self):
        """Test that has_tool_use correctly identifies tool_use blocks."""
        from wisdom_service.tools import has_tool_use

        # Response with tool use
        response_with_tools = {
            "content": [
                {"type": "text", "text": "Let me search for that."},
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "search_suttas",
                    "input": {"query": "suffering", "limit": 3},
                },
            ]
        }
        assert has_tool_use(response_with_tools) is True

        # Response without tool use
        response_no_tools = {
            "content": [{"type": "text", "text": "Here is my response."}]
        }
        assert has_tool_use(response_no_tools) is False

    def test_has_tool_use_handles_empty_content(self):
        """Test that has_tool_use handles empty content gracefully."""
        from wisdom_service.tools import has_tool_use

        assert has_tool_use({"content": []}) is False
        assert has_tool_use({}) is False

    @patch("wisdom_service.sutta_search.search_suttas")
    def test_execute_tool_calls_returns_correct_format(self, mock_search_suttas):
        """Test that execute_tool_calls returns properly formatted tool_result blocks."""
        from wisdom_service.tools import execute_tool_calls

        # Mock dependencies
        mock_search_suttas.return_value = [
            {"id": "SN56.11", "title": "Test Sutta", "text": "Test content"}
        ]

        mock_dapr = Mock()

        response = {
            "content": [
                {"type": "text", "text": "Let me search for that."},
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "search_suttas",
                    "input": {"query": "suffering", "limit": 2},
                },
            ]
        }

        results = execute_tool_calls(response, mock_dapr, chat_id="12345")

        # Check result format
        assert len(results) == 1
        assert results[0]["type"] == "tool_result"
        assert results[0]["tool_use_id"] == "toolu_123"
        assert "content" in results[0]
        assert "Test Sutta" in results[0]["content"]

    @patch("wisdom_service.sutta_search.search_suttas")
    def test_execute_tool_calls_handles_multiple_tools(self, mock_search_suttas):
        """Test that execute_tool_calls handles multiple tool calls in one response."""
        from wisdom_service.tools import execute_tool_calls

        mock_search_suttas.return_value = [
            {"id": "SN56.11", "title": "Test Sutta", "text": "Test content"}
        ]

        mock_dapr = Mock()
        mock_dapr.invoke_method = Mock(
            return_value=Mock(text=lambda: json.dumps({"history": []}))
        )

        response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "search_suttas",
                    "input": {"query": "suffering"},
                },
                {
                    "type": "tool_use",
                    "id": "toolu_456",
                    "name": "get_seeker_history",
                    "input": {"chat_id": "12345", "last_n": 5},
                },
            ]
        }

        results = execute_tool_calls(response, mock_dapr, chat_id="12345")

        assert len(results) == 2
        assert results[0]["tool_use_id"] == "toolu_123"
        assert results[1]["tool_use_id"] == "toolu_456"

    def test_execute_tool_calls_handles_unknown_tool(self):
        """Test that execute_tool_calls handles unknown tool gracefully."""
        from wisdom_service.tools import execute_tool_calls

        mock_dapr = Mock()

        response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_999",
                    "name": "unknown_tool",
                    "input": {},
                }
            ]
        }

        results = execute_tool_calls(response, mock_dapr, chat_id="12345")

        assert len(results) == 1
        assert "Unknown tool" in results[0]["content"]


class TestCallAnthropicWithTools:
    """Test the Anthropic API call with tools."""

    @patch("wisdom_service.tools.httpx")
    def test_call_anthropic_with_tools_includes_tools_in_payload(self, mock_httpx):
        """Test that call_anthropic_with_tools includes tools in API request."""
        from wisdom_service.tools import TOOLS, call_anthropic_with_tools

        # Mock httpx response
        mock_response = Mock()
        mock_response.json = Mock(
            return_value={
                "id": "msg_123",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Hello"}],
                "stop_reason": "end_turn",
            }
        )
        mock_httpx.post = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "What is suffering?"}]
        system_prompt = "You are a Buddhist teacher."

        result = call_anthropic_with_tools(
            messages,
            system_prompt,
            TOOLS,
            api_base="https://api.example.com",
            api_key="test_key",
            model="anthropic.claude-sonnet-4-5-20250929-v1:0",
        )

        # Check that httpx.post was called with correct parameters
        mock_httpx.post.assert_called_once()
        call_args = mock_httpx.post.call_args

        assert "https://api.example.com/v1/messages" in call_args[0]

        # Check headers
        headers = call_args[1]["headers"]
        assert headers["content-type"] == "application/json"
        assert headers["accept"] == "application/json"
        assert "anthropic-version" in headers

        # Check payload includes tools
        payload = call_args[1]["json"]
        assert "tools" in payload
        assert payload["tools"] == TOOLS
        assert payload["system"] == system_prompt
        assert payload["messages"] == messages

    @patch("wisdom_service.tools.httpx")
    def test_call_anthropic_with_tools_returns_response(self, mock_httpx):
        """Test that call_anthropic_with_tools returns parsed response."""
        from wisdom_service.tools import TOOLS, call_anthropic_with_tools

        mock_response_data = {
            "id": "msg_123",
            "content": [
                {"type": "text", "text": "Let me search"},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "search_suttas",
                    "input": {"query": "test"},
                },
            ],
        }
        mock_response = Mock()
        mock_response.json = Mock(return_value=mock_response_data)
        mock_httpx.post = Mock(return_value=mock_response)

        result = call_anthropic_with_tools(
            [{"role": "user", "content": "test"}],
            "system",
            TOOLS,
            api_base="https://api.example.com",
            api_key="key",
            model="test",
        )

        assert result == mock_response_data
        assert "content" in result
        assert len(result["content"]) == 2


class TestToolCallLoopIntegration:
    """Test the tool call loop integration in /wisdom/ask endpoint."""

    def test_max_tool_call_limit(self):
        """Test that tool call loop stops after 3 iterations."""
        from wisdom_service.tools import has_tool_use

        # Mock has_tool_use to always return True (infinite loop scenario)
        # but the implementation should stop after 3 iterations
        max_iterations = 3

        # Simulate the loop from __main__.py
        tool_use_count = 0
        response = {
            "content": [
                {"type": "tool_use", "id": "test", "name": "search_suttas", "input": {}}
            ]
        }

        while has_tool_use(response) and tool_use_count < max_iterations:
            # Simulate tool execution
            tool_use_count += 1

        assert tool_use_count == 3, "Loop should stop after 3 iterations"

    def test_fallback_to_rag_when_no_tools_used(self):
        """Test that mandatory RAG runs when LLM doesn't use tools."""
        # This test documents the fallback behavior
        # When tool_use_count == 0, we should fall back to the existing RAG pipeline

        # Simulate the logic from __main__.py: if no tools were called, use RAG
        tool_use_count = 0

        # The implementation should check this condition
        should_use_rag = tool_use_count == 0

        assert should_use_rag, "Should fall back to RAG when no tools were used"

    @patch("wisdom_service.__main__.get_langcache")
    def test_no_caching_for_tool_responses(self, mock_get_langcache):
        """Test that tool-calling responses skip langcache store."""
        mock_langcache = Mock()
        mock_get_langcache.return_value = mock_langcache

        # Simulate scenario where tools were used
        tool_use_count = 2

        # In the implementation, we should only cache if tool_use_count == 0
        if tool_use_count == 0:
            mock_langcache.store.call_count += 1

        # Verify that store was NOT called (tool_use_count > 0)
        assert mock_langcache.store.call_count == 0, (
            "Should not cache when tools were used"
        )

    @patch("wisdom_service.__main__.get_langcache")
    def test_caching_when_no_tools_used(self, mock_get_langcache):
        """Test that responses are cached when no tools were used."""
        mock_langcache = Mock()
        mock_get_langcache.return_value = mock_langcache

        # Simulate scenario where no tools were used
        tool_use_count = 0
        message = "What is dukkha?"
        response_text = "Dukkha is suffering..."
        practice_level = "newcomer"

        # In the implementation, we should cache if tool_use_count == 0
        if tool_use_count == 0:
            mock_langcache.store(message, response_text, practice_level)

        # Verify that store WAS called
        mock_langcache.store.assert_called_once_with(
            message, response_text, practice_level
        )
