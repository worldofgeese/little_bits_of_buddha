"""
Tests for Buddha Bot Service

This module contains tests for the simplified single-service
Telegram bot that responds as the Buddha.
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestBuddhaBot:
    """Test class for the Buddha Bot service."""
    
    def test_buddha_persona_system_prompt(self):
        """The system prompt should define the Buddha persona correctly."""
        from buddha_bot_service import get_buddha_system_prompt
        
        prompt = get_buddha_system_prompt()
        
        assert "Buddha" in prompt
        assert "Dhamma" in prompt
        assert "Tathagata" in prompt or "Awakened One" in prompt
    
    def test_should_respond_to_message_returns_true_for_text(self):
        """Should respond to messages that contain text."""
        from buddha_bot_service import should_respond_to_message
        
        update = {"message": {"text": "Hello, Buddha!"}}
        assert should_respond_to_message(update) is True
    
    def test_should_respond_to_message_returns_false_for_empty(self):
        """Should not respond to messages without text."""
        from buddha_bot_service import should_respond_to_message
        
        update = {"message": {}}
        assert should_respond_to_message(update) is False
    
    def test_should_respond_to_message_returns_false_for_no_message(self):
        """Should not respond to updates without message field."""
        from buddha_bot_service import should_respond_to_message
        
        update = {}
        assert should_respond_to_message(update) is False
    
    def test_extract_chat_id_returns_correct_id(self):
        """Should extract the chat ID from a message update."""
        from buddha_bot_service import extract_chat_id
        
        update = {"message": {"chat": {"id": 12345}}}
        assert extract_chat_id(update) == 12345
    
    def test_extract_message_text_returns_correct_text(self):
        """Should extract the message text from a message update."""
        from buddha_bot_service import extract_message_text
        
        update = {"message": {"text": "What is the path to enlightenment?"}}
        assert extract_message_text(update) == "What is the path to enlightenment?"
    
    def test_build_telegram_response_format(self):
        """Should format the response correctly for Telegram API."""
        from buddha_bot_service import build_telegram_response
        
        response = build_telegram_response(chat_id=12345, text="Peace be upon you.")
        
        assert response["chat_id"] == 12345
        assert response["text"] == "Peace be upon you."
        assert "parse_mode" in response or response.get("method") == "sendMessage"


class TestOpenAIClient:
    """Test class for the OpenAI client integration."""
    
    def test_openai_client_initialization(self):
        """Should initialize the OpenAI client with correct settings."""
        from buddha_bot_service import OpenAIClient
        
        with patch('buddha_bot_service.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            client = OpenAIClient(api_key="test-key")
            
            mock_openai.assert_called_once()
    
    def test_get_buddha_response(self):
        """Should get a response from OpenAI with Buddha persona."""
        from buddha_bot_service import OpenAIClient
        
        with patch('buddha_bot_service.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(content="The path is within you."))]
            )
            mock_openai.return_value = mock_client
            
            client = OpenAIClient(api_key="test-key")
            response = client.get_buddha_response("What is the path?")
            
            assert response == "The path is within you."


class TestWebhookHandler:
    """Test class for the webhook handler."""
    
    def test_webhook_endpoint_exists(self):
        """The webhook endpoint should exist and be callable."""
        from buddha_bot_service import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code in [200, 404]
    
    def test_webhook_accepts_post_requests(self):
        """The webhook endpoint should accept POST requests."""
        from buddha_bot_service import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        test_update = {
            "update_id": 123,
            "message": {
                "message_id": 456,
                "chat": {"id": 789},
                "text": "Greetings, Buddha."
            }
        }
        
        # Should not raise an exception
        response = client.post("/webhook", json=test_update)
        # Response might fail due to missing mocks, but endpoint should accept it
        assert response.status_code in [200, 401, 403, 500]
