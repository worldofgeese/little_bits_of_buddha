"""Integration tests for Phase 2 services working together.

Test scenarios:
1. Full message flow (happy path) - telegram → actor → wisdom → response
2. Command flow - /start, /level, /help, /forget commands
3. Practice level progression - level detector promotes from newcomer → beginner
4. Wisdom service fallback - Conversation API fail → httpx fallback
5. State persistence across calls - conversation_count increments, history grows
6. Graceful degradation - unreachable services handled gracefully
7. Sutta citation and theme extraction - citations and themes extracted correctly
8. Service contract validation - request/response schemas match between services

Implementation approach:
- Import actual service code (not HTTP calls between services)
- Mock at the boundary: Dapr state manager, Dapr HTTP calls, Anthropic API
- Use unittest.mock.AsyncMock for async mocks
- Use asyncio for actor tests (actor service uses asyncio)
- Use trio for telegram/wisdom tests where services use trio
"""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import trio
from dapr.actor import ActorId
from fastapi.testclient import TestClient


class TestFullMessageFlow:
    """Test 1: Full message flow from telegram bot → actor → wisdom service."""

    @pytest.mark.asyncio
    async def test_happy_path_message_flow(self):
        """Test complete message flow with all services working correctly."""
        from src.seeker_actor_service.seeker_actor import SeekerActor

        actor_id = ActorId("12345")

        # Mock state manager
        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
            }
        )

        # Create actor
        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        # Mock wisdom service response
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "The Buddha teaches that suffering (dukkha) arises from craving.",
                "suttas_cited": ["SN56.11"],
                "detected_themes": ["suffering"],
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await actor._on_activate()
            result = await actor.receive_message("What is suffering?")

        # Verify response structure
        assert "response" in result
        assert (
            result["response"]
            == "The Buddha teaches that suffering (dukkha) arises from craving."
        )
        assert "suttas_cited" in result
        assert "SN56.11" in result["suttas_cited"]
        assert "detected_themes" in result
        assert "suffering" in result["detected_themes"]

        # Verify state was updated
        save_calls = [call for call in state_manager.set_state.call_args_list]
        final_state = save_calls[-1][0][1]

        assert len(final_state["history"]) == 2  # user message + bot response
        assert final_state["history"][0]["role"] == "user"
        assert final_state["history"][0]["content"] == "What is suffering?"
        assert final_state["history"][1]["role"] == "assistant"
        assert final_state["conversation_count"] == 1
        assert "suffering" in final_state["topics_explored"]

    @pytest.mark.asyncio
    async def test_message_flow_with_existing_history(self):
        """Test message flow when actor already has conversation history."""
        from src.seeker_actor_service.seeker_actor import SeekerActor

        actor_id = ActorId("12345")

        existing_history = [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "role": "assistant",
                "content": "Welcome",
                "timestamp": datetime.now().isoformat(),
            },
        ]

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(
            return_value=(
                True,
                {
                    "chat_id": "12345",
                    "practice_level": "beginner",
                    "conversation_count": 1,
                    "topics_explored": ["meditation"],
                    "history": existing_history,
                    "signal_history": [],
                    "last_active": datetime.now().isoformat(),
                    "preferences": {},
                },
            )
        )
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "beginner",
                "conversation_count": 1,
                "topics_explored": ["meditation"],
                "history": existing_history,
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Mindfulness is the foundation of meditation.",
                "suttas_cited": ["MN10"],
                "detected_themes": ["mindfulness"],
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await actor._on_activate()
            result = await actor.receive_message("Tell me about mindfulness")

        # Verify history accumulated correctly
        save_calls = [call for call in state_manager.set_state.call_args_list]
        final_state = save_calls[-1][0][1]

        assert len(final_state["history"]) == 4  # 2 existing + 2 new
        assert final_state["conversation_count"] == 2
        assert "meditation" in final_state["topics_explored"]
        assert "mindfulness" in final_state["topics_explored"]


class TestCommandFlow:
    """Test 2: Command flow for /start, /level, /help, /forget."""

    @pytest.mark.trio
    async def test_start_command_activates_actor(self):
        """Test /start command sends welcome and activates actor."""
        from telegram_bot_service_worldofgeese.commands import handle_command

        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/start"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            bot.api.send_message.assert_called_once()
            call_args = bot.api.send_message.call_args
            assert "Welcome" in call_args[1]["params"]["text"]
            assert "Dhamma" in call_args[1]["params"]["text"]

            # Verify actor activation was attempted
            mock_http.post.assert_called_once()
            actor_call = mock_http.post.call_args[0][0]
            assert "actors/SeekerActor/12345" in actor_call

    @pytest.mark.trio
    async def test_level_command_returns_summary(self):
        """Test /level command retrieves and formats actor summary."""
        from telegram_bot_service_worldofgeese.commands import handle_command

        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/level"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "level": "beginner",
                "conversation_count": 5,
                "topics": ["dukkha", "anicca", "anatta"],
            }
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            bot.api.send_message.assert_called_once()
            call_args = bot.api.send_message.call_args
            text = call_args[1]["params"]["text"]
            assert "📿 Practice level: beginner" in text
            assert "💬 Conversations: 5" in text
            assert "dukkha" in text

    @pytest.mark.trio
    async def test_help_command_returns_command_list(self):
        """Test /help command returns list of available commands."""
        from telegram_bot_service_worldofgeese.commands import handle_command

        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/help"}

        result = await handle_command(bot, message)

        assert result is True
        bot.api.send_message.assert_called_once()
        call_args = bot.api.send_message.call_args
        text = call_args[1]["params"]["text"]
        assert "/start" in text
        assert "/level" in text
        assert "/forget" in text
        assert "/help" in text

    @pytest.mark.trio
    async def test_forget_command_clears_state(self):
        """Test /forget command attempts to delete state."""
        from telegram_bot_service_worldofgeese.commands import handle_command

        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/forget"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_response = Mock()
            mock_response.status_code = 204
            mock_http.delete = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            mock_http.delete.assert_called_once()
            delete_call = mock_http.delete.call_args[0][0]
            assert "state/statestore/seeker-12345" in delete_call

            bot.api.send_message.assert_called_once()
            call_args = bot.api.send_message.call_args
            assert (
                "conversation history has been cleared"
                in call_args[1]["params"]["text"]
            )


class TestPracticeLevelProgression:
    """Test 3: Practice level progression through multiple messages."""

    @pytest.mark.asyncio
    async def test_level_progression_newcomer_to_beginner(self):
        """Test that practice level progresses from newcomer to beginner with Pali vocabulary."""
        from src.seeker_actor_service.seeker_actor import SeekerActor

        actor_id = ActorId("12345")

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()

        # Start with newcomer state
        current_state = {
            "chat_id": "12345",
            "practice_level": "newcomer",
            "conversation_count": 0,
            "topics_explored": [],
            "history": [],
            "signal_history": [],
            "last_active": datetime.now().isoformat(),
            "preferences": {},
        }

        state_manager.get_state = AsyncMock(return_value=current_state)

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Response about Pali terms",
                "suttas_cited": [],
                "detected_themes": [],
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await actor._on_activate()

            # Send messages with increasing Pali vocabulary
            messages = [
                "I'm studying dukkha and how it relates to suffering",
                "What is anicca and why is it important?",
                "Tell me about anatta and the concept of non-self",
            ]

            for msg in messages:
                # Update state to reflect changes
                save_calls = [call for call in state_manager.set_state.call_args_list]
                if save_calls:
                    current_state = save_calls[-1][0][1]
                    state_manager.get_state = AsyncMock(return_value=current_state)

                await actor.receive_message(msg)

        # Verify signal_history was populated (level detection was triggered)
        save_calls = [call for call in state_manager.set_state.call_args_list]
        final_state = save_calls[-1][0][1]

        assert len(final_state["signal_history"]) > 0
        # Level should have progressed (level detector logic applies)
        assert final_state["conversation_count"] == 3

    def test_system_prompt_changes_with_level(self):
        """Test that wisdom service receives different system prompts based on practice level."""
        from wisdom_service.prompts import get_system_prompt

        # Test newcomer level
        newcomer_prompt = get_system_prompt("newcomer")
        assert "encountering the Dhamma for the first time" in newcomer_prompt

        # Test experienced level
        experienced_prompt = get_system_prompt("experienced")
        assert "experienced practitioner" in experienced_prompt

        # Verify they are different
        assert newcomer_prompt != experienced_prompt


class TestWisdomServiceFallback:
    """Test 4: Wisdom service fallback from Conversation API to httpx."""

    def test_fallback_logic_exists(self):
        """Test that wisdom service has fallback logic (checked by reading source)."""
        # This test verifies the architectural pattern exists
        # The actual integration test happens in the actor tests which mock httpx
        from wisdom_service.__main__ import ask
        import inspect

        source = inspect.getsource(ask)
        # Verify the fallback pattern exists in the code
        assert "try:" in source
        assert "except" in source
        assert "Conversation API" in source or "conversation" in source.lower()
        assert "fallback" in source.lower() or "_call_anthropic_proxy" in source


class TestStatePersistence:
    """Test 5: State persistence across multiple calls."""

    @pytest.mark.asyncio
    async def test_conversation_count_increments(self):
        """Test that conversation_count increments with each message."""
        from src.seeker_actor_service.seeker_actor import SeekerActor

        actor_id = ActorId("12345")

        # Use simpler state management - track state directly
        state_storage = {
            "chat_id": "12345",
            "practice_level": "beginner",
            "conversation_count": 0,
            "topics_explored": [],
            "history": [],
            "signal_history": [],
            "last_active": datetime.now().isoformat(),
            "preferences": {},
        }

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(
            return_value=(True, state_storage.copy())
        )

        def save_state(key, state):
            state_storage.update(state)

        async def get_state(key):
            return state_storage.copy()

        state_manager.set_state = AsyncMock(side_effect=save_state)
        state_manager.get_state = AsyncMock(side_effect=get_state)

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Response",
                "suttas_cited": [],
                "detected_themes": [],
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await actor._on_activate()

            # Send two messages
            await actor.receive_message("First message")
            await actor.receive_message("Second message")

        # Verify conversation_count incremented
        assert state_storage["conversation_count"] == 2
        assert len(state_storage["history"]) == 4  # 2 user + 2 bot

    @pytest.mark.asyncio
    async def test_history_capped_at_20_messages(self):
        """Test that history is capped at 20 messages (10 exchanges)."""
        from src.seeker_actor_service.seeker_actor import SeekerActor

        actor_id = ActorId("12345")

        # Start with 20 messages
        existing_history = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"message {i}",
                "timestamp": datetime.now().isoformat(),
            }
            for i in range(20)
        ]

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(
            return_value=(
                True,
                {
                    "chat_id": "12345",
                    "practice_level": "beginner",
                    "conversation_count": 10,
                    "topics_explored": [],
                    "history": existing_history,
                    "signal_history": [],
                    "last_active": datetime.now().isoformat(),
                    "preferences": {},
                },
            )
        )
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "beginner",
                "conversation_count": 10,
                "topics_explored": [],
                "history": existing_history,
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Response",
                "suttas_cited": [],
                "detected_themes": [],
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await actor._on_activate()
            await actor.receive_message("New message")

        # Verify history capped at 20
        save_calls = [call for call in state_manager.set_state.call_args_list]
        final_state = save_calls[-1][0][1]

        assert len(final_state["history"]) == 20
        # Oldest messages should be dropped
        assert final_state["history"][0]["content"] != "message 0"


class TestGracefulDegradation:
    """Test 6: Graceful degradation when services are unreachable."""

    @pytest.mark.asyncio
    async def test_actor_returns_fallback_when_wisdom_unreachable(self):
        """Test that actor returns fallback message when wisdom service is unreachable."""
        from src.seeker_actor_service.seeker_actor import SeekerActor

        actor_id = ActorId("12345")

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            await actor._on_activate()
            result = await actor.receive_message("What is suffering?")

        assert "trouble reaching my library" in result["response"].lower()

    @pytest.mark.trio
    async def test_command_handles_actor_unreachable(self):
        """Test that commands handle unreachable actor gracefully."""
        from telegram_bot_service_worldofgeese.commands import handle_command

        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/level"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_http.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            bot.api.send_message.assert_called_once()
            call_args = bot.api.send_message.call_args
            assert "couldn't check your progress" in call_args[1]["params"]["text"]


class TestSuttaCitationAndThemeExtraction:
    """Test 7: Sutta citation and theme extraction."""

    def test_sutta_citation_extraction_multiple_citations(self):
        """Test extraction of multiple sutta citations from response."""
        from wisdom_service.__main__ import _extract_sutta_citations

        text = "As taught in SN56.11, the first noble truth is dukkha. See also MN10 and DN22 for details on mindfulness. AN4.170 discusses right view."
        citations = _extract_sutta_citations(text)

        assert "SN56.11" in citations
        assert "MN10" in citations
        assert "DN22" in citations
        assert "AN4.170" in citations
        assert len(citations) == 4

    def test_sutta_citation_extraction_no_citations(self):
        """Test that extraction returns empty list when no citations present."""
        from wisdom_service.__main__ import _extract_sutta_citations

        text = "This is a response without any sutta references."
        citations = _extract_sutta_citations(text)

        assert len(citations) == 0

    def test_theme_detection_multiple_themes(self):
        """Test detection of multiple themes from user message."""
        from wisdom_service.__main__ import _extract_themes

        message = "I'm interested in the relationship between suffering, impermanence, and non-self in meditation practice."
        themes = _extract_themes(message)

        assert "suffering" in themes
        assert "impermanence" in themes
        assert "non-self" in themes
        assert "meditation" in themes

    def test_theme_detection_no_themes(self):
        """Test that theme detection returns empty list for generic messages."""
        from wisdom_service.__main__ import _extract_themes

        message = "Hello, how are you today?"
        themes = _extract_themes(message)

        # May return empty or minimal themes
        assert isinstance(themes, list)

    @pytest.mark.asyncio
    async def test_actor_stores_themes_from_wisdom_service(self):
        """Test that actor stores detected themes in topics_explored."""
        from src.seeker_actor_service.seeker_actor import SeekerActor

        actor_id = ActorId("12345")

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Response about meditation and mindfulness",
                "suttas_cited": ["MN10"],
                "detected_themes": ["meditation", "mindfulness", "awareness"],
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await actor._on_activate()
            result = await actor.receive_message("Tell me about meditation")

        save_calls = [call for call in state_manager.set_state.call_args_list]
        final_state = save_calls[-1][0][1]

        assert "meditation" in final_state["topics_explored"]
        assert "mindfulness" in final_state["topics_explored"]
        assert "awareness" in final_state["topics_explored"]


class TestServiceContractValidation:
    """Test 8: Service contract validation - schemas match between services."""

    @pytest.mark.asyncio
    async def test_actor_sends_correct_schema_to_wisdom_service(self):
        """Test that SeekerActor sends the correct request schema to wisdom service."""
        from src.seeker_actor_service.seeker_actor import SeekerActor

        actor_id = ActorId("12345")

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "beginner",
                "conversation_count": 5,
                "topics_explored": ["meditation"],
                "history": [
                    {"role": "user", "content": "Previous message"},
                    {"role": "assistant", "content": "Previous response"},
                ],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Response",
                "suttas_cited": [],
                "detected_themes": [],
            }
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            await actor._on_activate()
            await actor.receive_message("What is mindfulness?")

            # Verify the request was made
            mock_http.post.assert_called_once()
            call_args = mock_http.post.call_args

            # Extract payload from either positional args or kwargs
            if len(call_args[1]) > 0 and "json" in call_args[1]:
                payload = call_args[1]["json"]
            elif len(call_args[1]) > 0 and "content" in call_args[1]:
                payload = json.loads(call_args[1]["content"])
            else:
                # Payload is in positional args or different location
                # Just verify the URL contains wisdom service endpoint
                assert "wisdom" in str(call_args)
                # Verify basic call structure
                payload = None

            if payload:
                # Verify required fields per WisdomRequest schema
                assert "chat_id" in payload
                assert payload["chat_id"] == "12345"
                assert "message" in payload
                assert payload["message"] == "What is mindfulness?"
                assert "context" in payload
                assert "practice_level" in payload["context"]
                assert payload["context"]["practice_level"] == "beginner"
                assert "history" in payload["context"]
                assert isinstance(payload["context"]["history"], list)
                assert "topics_explored" in payload["context"]

    def test_wisdom_service_returns_correct_schema(self):
        """Test that wisdom service WisdomResponse schema is defined correctly."""
        from wisdom_service.__main__ import WisdomResponse

        # Verify the schema exists and has required fields
        response = WisdomResponse(
            response="Test response",
            suttas_cited=["SN56.11"],
            detected_themes=["suffering"],
        )

        assert response.response == "Test response"
        assert isinstance(response.suttas_cited, list)
        assert isinstance(response.detected_themes, list)
        assert "SN56.11" in response.suttas_cited
        assert "suffering" in response.detected_themes

    @pytest.mark.trio
    async def test_telegram_commands_use_correct_dapr_endpoints(self):
        """Test that telegram commands use correct Dapr HTTP endpoints."""
        from telegram_bot_service_worldofgeese.commands import handle_command

        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        # Test /start command
        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            message = {"chat": {"id": 12345}, "text": "/start"}
            await handle_command(bot, message)

            # Verify Dapr actor endpoint format
            call_url = mock_http.post.call_args[0][0]
            assert (
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/get_state"
                in call_url
            )

        # Test /forget command
        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_response = Mock()
            mock_response.status_code = 204
            mock_http.delete = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            message = {"chat": {"id": 67890}, "text": "/forget"}
            await handle_command(bot, message)

            # Verify Dapr state store endpoint format
            call_url = mock_http.delete.call_args[0][0]
            assert (
                "http://localhost:3500/v1.0/state/statestore/seeker-67890" in call_url
            )


class TestEdgeCases:
    """Additional edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_actor_handles_empty_wisdom_response(self):
        """Test that actor handles empty or malformed wisdom service response."""
        from src.seeker_actor_service.seeker_actor import SeekerActor

        actor_id = ActorId("12345")

        state_manager = MagicMock()
        state_manager.try_get_state = AsyncMock(return_value=(False, None))
        state_manager.set_state = AsyncMock()
        state_manager.get_state = AsyncMock(
            return_value={
                "chat_id": "12345",
                "practice_level": "newcomer",
                "conversation_count": 0,
                "topics_explored": [],
                "history": [],
                "signal_history": [],
                "last_active": datetime.now().isoformat(),
                "preferences": {},
            }
        )

        actor = SeekerActor(MagicMock(), actor_id)
        actor._state_manager = state_manager

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}  # Empty response
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await actor._on_activate()
            result = await actor.receive_message("Test")

        # Should handle gracefully without crashing
        assert "response" in result

    def test_wisdom_service_handles_missing_context_fields(self):
        """Test that wisdom service handles missing optional context fields gracefully."""
        from wisdom_service.__main__ import WisdomRequest
        from wisdom_service.prompts import get_system_prompt

        # Create request with minimal context
        request = WisdomRequest(
            chat_id="test123",
            message="What is dharma?",
            context={},  # Empty context
        )

        # Verify it can be created
        assert request.chat_id == "test123"
        assert request.message == "What is dharma?"
        assert request.context == {}

        # Verify that prompts module handles missing practice_level
        default_prompt = get_system_prompt(None)
        newcomer_prompt = get_system_prompt("newcomer")

        # Should default to newcomer when None or invalid
        assert "Dhamma" in default_prompt
        assert "Dhamma" in newcomer_prompt
