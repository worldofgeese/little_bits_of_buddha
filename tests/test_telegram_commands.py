"""Test Telegram bot commands for Phase 2.

Tests verify that:
1. /start sends welcome message and activates actor
2. /level returns formatted summary
3. /forget clears state and confirms
4. /help returns command list
5. Non-command messages return False
6. Commands are case-insensitive
7. Commands with @botname suffix work
8. Unknown commands return False
9. Error handling for unreachable actor
"""

import pytest
import trio
from unittest.mock import AsyncMock, Mock, patch

from telegram_bot_service_worldofgeese.commands import handle_command


class TestCommandHandling:
    """Test the main command dispatcher."""

    @pytest.mark.trio
    async def test_non_command_returns_false(self):
        """Non-command messages should return False."""
        bot = Mock()
        message = {"chat": {"id": 12345}, "text": "What is the Noble Eightfold Path?"}
        result = await handle_command(bot, message)
        assert result is False

    @pytest.mark.trio
    async def test_empty_message_returns_false(self):
        """Empty messages should return False."""
        bot = Mock()
        message = {"chat": {"id": 12345}, "text": ""}
        result = await handle_command(bot, message)
        assert result is False

    @pytest.mark.trio
    async def test_unknown_command_returns_false(self):
        """Unknown commands should return False."""
        bot = Mock()
        message = {"chat": {"id": 12345}, "text": "/unknown_command"}
        result = await handle_command(bot, message)
        assert result is False

    @pytest.mark.trio
    async def test_command_case_insensitive(self):
        """Commands should be case-insensitive."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/START"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await handle_command(bot, message)
            assert result is True
            bot.api.send_message.assert_called_once()

    @pytest.mark.trio
    async def test_command_with_botname_suffix(self):
        """Commands with @botname suffix should work."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/start@LittleBitsOfBuddhaBot"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await handle_command(bot, message)
            assert result is True
            bot.api.send_message.assert_called_once()


class TestStartCommand:
    """Test /start command."""

    @pytest.mark.trio
    async def test_start_sends_welcome_message(self):
        """Test that /start sends the welcome message."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/start"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await handle_command(bot, message)

            assert result is True
            bot.api.send_message.assert_called_once()
            call_args = bot.api.send_message.call_args
            assert call_args[1]["params"]["chat_id"] == 12345
            assert "Welcome" in call_args[1]["params"]["text"]
            assert "Dhamma" in call_args[1]["params"]["text"]

    @pytest.mark.trio
    async def test_start_activates_actor(self):
        """Test that /start invokes the SeekerActor."""
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
            mock_http.post.assert_called_once()
            call_args = mock_http.post.call_args
            assert (
                "http://localhost:3500/v1.0/actors/SeekerActor/12345/method/get_state"
                in call_args[0][0]
            )

    @pytest.mark.trio
    async def test_start_works_if_actor_unreachable(self):
        """Test that /start still sends welcome if actor is unreachable."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/start"}

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
            assert call_args[1]["params"]["chat_id"] == 12345


class TestLevelCommand:
    """Test /level command."""

    @pytest.mark.trio
    async def test_level_returns_formatted_summary(self):
        """Test that /level returns a formatted summary."""
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
                "topics": ["dukkha", "anicca"],
            }
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            bot.api.send_message.assert_called_once()
            call_args = bot.api.send_message.call_args
            assert call_args[1]["params"]["chat_id"] == 12345
            text = call_args[1]["params"]["text"]
            assert "📿 Practice level: beginner" in text
            assert "💬 Conversations: 5" in text
            assert "📚 Topics explored:" in text

    @pytest.mark.trio
    async def test_level_handles_actor_unreachable(self):
        """Test that /level handles unreachable actor gracefully."""
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


class TestForgetCommand:
    """Test /forget command."""

    @pytest.mark.trio
    async def test_forget_clears_state_and_confirms(self):
        """Test that /forget clears state and confirms to user."""
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
            call_args = mock_http.delete.call_args
            assert (
                "http://localhost:3500/v1.0/state/statestore/seeker-12345"
                in call_args[0][0]
            )

            bot.api.send_message.assert_called_once()
            call_args = bot.api.send_message.call_args
            assert (
                "conversation history has been cleared"
                in call_args[1]["params"]["text"]
            )


class TestHelpCommand:
    """Test /help command."""

    @pytest.mark.trio
    async def test_help_returns_command_list(self):
        """Test that /help returns the list of available commands."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/help"}

        result = await handle_command(bot, message)

        assert result is True
        bot.api.send_message.assert_called_once()
        call_args = bot.api.send_message.call_args
        assert call_args[1]["params"]["chat_id"] == 12345
        text = call_args[1]["params"]["text"]
        assert "/start" in text
        assert "/level" in text
        assert "/forget" in text
        assert "/help" in text
        assert "Available commands" in text


class TestMeditateCommand:
    """Test /meditate command."""

    @pytest.mark.trio
    async def test_meditate_default_params(self):
        """Test that /meditate with no args uses defaults (breathing, 5 min)."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/meditate"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "instance_id": "meditation-12345-1234567890",
                "status": "started",
            }
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            mock_http.post.assert_called_once()
            call_args = mock_http.post.call_args
            assert "http://localhost:3500/v1.0/invoke/meditation-workflow-service/method/meditate/start" in call_args[0][0]

            # Check payload
            payload = call_args[1]["json"]
            assert payload["chat_id"] == 12345
            assert payload["type"] == "breathing_meditation"
            assert payload["duration_minutes"] == 5

            bot.api.send_message.assert_called_once()
            text = bot.api.send_message.call_args[1]["params"]["text"]
            assert "meditation" in text.lower()
            assert "meditation-12345-1234567890" in text

    @pytest.mark.trio
    async def test_meditate_with_type(self):
        """Test that /meditate breathing works."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/meditate breathing"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "instance_id": "meditation-12345-1234567890",
                "status": "started",
            }
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            payload = mock_http.post.call_args[1]["json"]
            assert payload["type"] == "breathing_meditation"
            assert payload["duration_minutes"] == 5

    @pytest.mark.trio
    async def test_meditate_with_type_and_duration(self):
        """Test that /meditate metta 10 works."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/meditate metta 10"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "instance_id": "meditation-12345-1234567890",
                "status": "started",
            }
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            payload = mock_http.post.call_args[1]["json"]
            assert payload["type"] == "metta_meditation"
            assert payload["duration_minutes"] == 10

    @pytest.mark.trio
    async def test_meditate_with_duration_only(self):
        """Test that /meditate 15 works (numeric-only means duration)."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/meditate 15"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "instance_id": "meditation-12345-1234567890",
                "status": "started",
            }
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            payload = mock_http.post.call_args[1]["json"]
            assert payload["type"] == "breathing_meditation"
            assert payload["duration_minutes"] == 15

    @pytest.mark.trio
    async def test_meditate_handles_service_error(self):
        """Test that /meditate handles service errors gracefully."""
        bot = Mock()
        bot.api = Mock()
        bot.api.send_message = AsyncMock()

        message = {"chat": {"id": 12345}, "text": "/meditate"}

        with patch(
            "telegram_bot_service_worldofgeese.commands.httpx.AsyncClient"
        ) as mock_client:
            mock_http = Mock()
            mock_http.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.return_value.__aenter__.return_value = mock_http

            result = await handle_command(bot, message)

            assert result is True
            bot.api.send_message.assert_called_once()
            text = bot.api.send_message.call_args[1]["params"]["text"]
            assert "couldn't start" in text.lower() or "try again" in text.lower()
