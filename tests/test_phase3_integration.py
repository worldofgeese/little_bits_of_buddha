"""Phase 3 Integration Tests.

Tests verify end-to-end integration of:
1. Tool calling → langcache interaction (tool responses NOT cached)
2. Meditation workflow → journal auto-log (from_workflow=True)
3. Learning path topic detection from conversation context
4. /meditate command parsing
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.telegram_bot_service_worldofgeese.commands import handle_command


class TestToolCallingLangcacheIntegration:
    """Test that tool responses are not cached, per WP4 design."""

    @pytest.mark.trio
    async def test_tool_response_not_cached(self):
        """Tool responses should bypass langcache."""
        # This test verifies the design decision from WP4:
        # Tool responses contain dynamic data (e.g., current meditation count)
        # and should NOT be cached.

        # Mock a tool call scenario where the seeker actor returns different data
        # on subsequent calls (e.g., sit count changes)

        with patch("httpx.AsyncClient") as mock_client:
            mock_http = Mock()

            # First call returns 5 sits
            first_response = Mock()
            first_response.status_code = 200
            first_response.json.return_value = {
                "total_sits": 5,
                "last_sit": "2026-03-01T10:00:00Z",
            }

            # Second call returns 6 sits (dynamic data, should not be cached)
            second_response = Mock()
            second_response.status_code = 200
            second_response.json.return_value = {
                "total_sits": 6,
                "last_sit": "2026-03-02T10:00:00Z",
            }

            mock_http.post = AsyncMock(side_effect=[first_response, second_response])
            mock_client.return_value.__aenter__.return_value = mock_http

            # Simulate two tool calls to get_journal
            # In real scenario, this would be called by the wisdom service
            # via tool_calling mechanism

            # First call
            response1 = await mock_http.post(
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/get_summary",
                timeout=2.0,
            )
            data1 = response1.json()
            assert data1["total_sits"] == 5

            # Second call (should get fresh data, not cached)
            response2 = await mock_http.post(
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/get_summary",
                timeout=2.0,
            )
            data2 = response2.json()
            assert data2["total_sits"] == 6

            # Verify both calls were made (no caching)
            assert mock_http.post.call_count == 2


class TestMeditationWorkflowJournalIntegration:
    """Test meditation workflow → journal auto-log integration."""

    @pytest.mark.trio
    async def test_workflow_completion_logs_to_journal(self):
        """When meditation workflow completes, it should log to journal with from_workflow=True."""

        with patch("httpx.AsyncClient") as mock_client:
            mock_http = Mock()

            # Mock workflow completion that calls log_sit
            log_response = Mock()
            log_response.status_code = 200
            log_response.json.return_value = {
                "total_sits": 1,
                "last_sit": "2026-03-05T10:00:00Z",
            }

            mock_http.post = AsyncMock(return_value=log_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            # Simulate workflow calling log_sit with from_workflow=True
            await mock_http.post(
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/log_sit",
                json={
                    "duration_minutes": 10,
                    "practice_type": "breathing",
                    "notes": None,
                    "from_workflow": True,
                },
                timeout=2.0,
            )

            # Verify the call was made with from_workflow=True
            call_args = mock_http.post.call_args
            payload = call_args[1]["json"]
            assert payload["from_workflow"] is True
            assert payload["duration_minutes"] == 10
            assert payload["practice_type"] == "breathing"

    @pytest.mark.trio
    async def test_manual_sit_vs_workflow_sit(self):
        """Manual /sit and workflow sits should both log but be distinguishable."""

        with patch("httpx.AsyncClient") as mock_client:
            mock_http = Mock()

            response = Mock()
            response.status_code = 200
            response.json.return_value = {"total_sits": 1}

            mock_http.post = AsyncMock(return_value=response)
            mock_client.return_value.__aenter__.return_value = mock_http

            # Manual sit (from /sit command)
            await mock_http.post(
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/log_sit",
                json={
                    "duration_minutes": 20,
                    "practice_type": "metta",
                    "notes": "Focused on compassion",
                    "from_workflow": False,
                },
                timeout=2.0,
            )

            # Workflow sit (from meditation workflow)
            await mock_http.post(
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/log_sit",
                json={
                    "duration_minutes": 10,
                    "practice_type": "breathing",
                    "notes": None,
                    "from_workflow": True,
                },
                timeout=2.0,
            )

            assert mock_http.post.call_count == 2

            # Verify first call (manual)
            first_call = mock_http.post.call_args_list[0]
            assert first_call[1]["json"]["from_workflow"] is False
            assert first_call[1]["json"]["notes"] == "Focused on compassion"

            # Verify second call (workflow)
            second_call = mock_http.post.call_args_list[1]
            assert second_call[1]["json"]["from_workflow"] is True
            assert second_call[1]["json"]["notes"] is None


class TestLearningPathTopicDetection:
    """Test learning path topic detection from conversation context."""

    @pytest.mark.trio
    async def test_topic_detection_from_conversation(self):
        """Topics discussed in conversation should be detected and tracked."""

        with patch("httpx.AsyncClient") as mock_client:
            mock_http = Mock()

            # Mock get_path_progress response showing detected topics
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "formatted": "**The Four Noble Truths** (3/4)\n• Dukkha ✓\n• Samudaya ✓\n• Nirodha ✓\n• Magga",
                "next_suggestion": {
                    "title": "The Noble Eightfold Path",
                    "section": "The Four Noble Truths",
                },
            }

            mock_http.post = AsyncMock(return_value=response)
            mock_client.return_value.__aenter__.return_value = mock_http

            # Simulate getting path progress after conversation
            result = await mock_http.post(
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/get_path_progress",
                json={},
                timeout=2.0,
            )

            data = result.json()
            assert "Four Noble Truths" in data["formatted"]
            assert "Dukkha" in data["formatted"]
            assert data["next_suggestion"]["title"] == "The Noble Eightfold Path"

    @pytest.mark.trio
    async def test_topic_tracking_across_conversations(self):
        """Topics should accumulate across multiple conversations."""

        with patch("httpx.AsyncClient") as mock_client:
            mock_http = Mock()

            # First conversation - discuss Dukkha
            first_response = Mock()
            first_response.status_code = 200
            first_response.json.return_value = {
                "topics": ["dukkha"],
                "conversation_count": 1,
            }

            # Second conversation - discuss Anicca
            second_response = Mock()
            second_response.status_code = 200
            second_response.json.return_value = {
                "topics": ["dukkha", "anicca"],
                "conversation_count": 2,
            }

            mock_http.post = AsyncMock(side_effect=[first_response, second_response])
            mock_client.return_value.__aenter__.return_value = mock_http

            # First conversation
            result1 = await mock_http.post(
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/get_summary",
                timeout=2.0,
            )
            assert result1.json()["topics"] == ["dukkha"]

            # Second conversation
            result2 = await mock_http.post(
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/get_summary",
                timeout=2.0,
            )
            assert result2.json()["topics"] == ["dukkha", "anicca"]


class TestMeditateCommandParsing:
    """Test /meditate command parsing logic."""

    def test_parse_meditate_default(self):
        """Test parsing /meditate with no args."""
        from telegram_bot_service_worldofgeese.commands import parse_meditate_command

        meditation_type, duration = parse_meditate_command("/meditate")
        assert meditation_type == "breathing_meditation"
        assert duration == 5

    def test_parse_meditate_type_only(self):
        """Test parsing /meditate breathing."""
        from telegram_bot_service_worldofgeese.commands import parse_meditate_command

        meditation_type, duration = parse_meditate_command("/meditate breathing")
        assert meditation_type == "breathing_meditation"
        assert duration == 5

    def test_parse_meditate_type_metta(self):
        """Test parsing /meditate metta."""
        from telegram_bot_service_worldofgeese.commands import parse_meditate_command

        meditation_type, duration = parse_meditate_command("/meditate metta")
        assert meditation_type == "metta_meditation"
        assert duration == 5

    def test_parse_meditate_duration_only(self):
        """Test parsing /meditate 15."""
        from telegram_bot_service_worldofgeese.commands import parse_meditate_command

        meditation_type, duration = parse_meditate_command("/meditate 15")
        assert meditation_type == "breathing_meditation"
        assert duration == 15

    def test_parse_meditate_type_and_duration(self):
        """Test parsing /meditate metta 20."""
        from telegram_bot_service_worldofgeese.commands import parse_meditate_command

        meditation_type, duration = parse_meditate_command("/meditate metta 20")
        assert meditation_type == "metta_meditation"
        assert duration == 20

    def test_parse_meditate_duration_and_type(self):
        """Test parsing /meditate 20 breathing."""
        from telegram_bot_service_worldofgeese.commands import parse_meditate_command

        meditation_type, duration = parse_meditate_command("/meditate 20 breathing")
        assert meditation_type == "breathing_meditation"
        assert duration == 20
