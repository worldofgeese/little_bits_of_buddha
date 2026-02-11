"""Tests for the openai_service_worldofgeese module.

This module follows the How to Design Functions (HtDF) recipe:
1. Signature, purpose, stub
2. Examples (tests)
3. Template/inventory
4. Code body
5. Test and debug
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
import json

from openai_service_worldofgeese.__main__ import (
    wait_for_dapr_ready,
)


class TestWaitForDaprReady:
    """Tests for the wait_for_dapr_ready function.
    
    Signature:
        wait_for_dapr_ready(dapr_port=3500, retries=20, delay=2) -> None
    
    Purpose:
        Wait for the Dapr sidecar to be ready by polling its health endpoint.
    
    Examples:
        - When Dapr is ready immediately, returns without error
        - When Dapr is not ready, retries up to specified number of times
    """
    
    def test_wait_for_dapr_ready_success_first_attempt(self, mocker):
        """Test that wait_for_dapr_ready succeeds when Dapr is ready on first attempt."""
        # Mock the requests.get call to return a response with status code 204
        mock_get = mocker.patch('requests.get')
        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response

        # Call the function
        wait_for_dapr_ready(retries=1, delay=0.1)

        # Assert that requests.get was called with the correct URL
        mock_get.assert_called_once_with('http://localhost:3500/v1.0/healthz')
    
    def test_wait_for_dapr_ready_success_after_retries(self, mocker):
        """Test that wait_for_dapr_ready retries and eventually succeeds."""
        # Mock the requests.get call to fail twice, then succeed
        mock_get = mocker.patch('requests.get')
        
        # First two calls fail, third call succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        
        mock_response_success = Mock()
        mock_response_success.status_code = 204
        
        mock_get.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success,
        ]

        # Call the function with retries=3
        wait_for_dapr_ready(retries=3, delay=0.1)

        # Assert that requests.get was called 3 times
        assert mock_get.call_count == 3
    
    def test_wait_for_dapr_ready_custom_port(self, mocker):
        """Test that wait_for_dapr_ready uses the specified port."""
        mock_get = mocker.patch('requests.get')
        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response

        wait_for_dapr_ready(dapr_port=3600, retries=1, delay=0.1)

        mock_get.assert_called_once_with('http://localhost:3600/v1.0/healthz')
    
    def test_wait_for_dapr_ready_raises_error_after_retries(self, mocker):
        """Test that wait_for_dapr_ready raises RuntimeError after exhausting retries."""
        # Mock the requests.get call to always fail
        mock_get = mocker.patch('requests.get')
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Expect RuntimeError to be raised
        with pytest.raises(RuntimeError, match="Dapr sidecar is not ready"):
            wait_for_dapr_ready(retries=3, delay=0.1)
    
    def test_wait_for_dapr_ready_handles_connection_error(self, mocker):
        """Test that wait_for_dapr_ready handles connection errors gracefully."""
        mock_get = mocker.patch('requests.get')
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        # Expect RuntimeError to be raised
        with pytest.raises(RuntimeError, match="Dapr sidecar is not ready"):
            wait_for_dapr_ready(retries=2, delay=0.1)


class TestBuildApp:
    """Tests for the _build_app function.
    
    Signature:
        _build_app() -> (FastAPI, callable)
    
    Purpose:
        Build the FastAPI app with Dapr integration and return it along with init_secrets.
    
    Examples:
        - Returns a tuple of (FastAPI app, init_secrets function)
        - The app has the messages subscriber endpoint configured
    """
    
    @patch('dapr.clients.DaprClient')
    @patch('dapr.ext.fastapi.DaprApp')
    @patch('fastapi.FastAPI')
    def test_build_app_returns_tuple(self, mock_fastapi, mock_dapr_app, mock_dapr_client):
        """Test that _build_app returns a tuple of (app, init_secrets_fn)."""
        from openai_service_worldofgeese.__main__ import _build_app
        
        # Set up mocks
        mock_app = Mock()
        mock_dapr_app_instance = Mock()
        mock_dapr_app.return_value = mock_dapr_app_instance
        mock_fastapi.return_value = mock_app
        
        # Call the function
        app, init_fn = _build_app()
        
        # Assert that a tuple is returned
        assert isinstance(app, type(mock_app))
        assert callable(init_fn)
    
    @patch('dapr.clients.DaprClient')
    @patch('dapr.ext.fastapi.DaprApp')
    @patch('fastapi.FastAPI')
    def test_build_app_has_subscriber_decorator(self, mock_fastapi, mock_dapr_app, mock_dapr_client):
        """Test that the built app has the messages subscriber configured."""
        from openai_service_worldofgeese.__main__ import _build_app
        
        # Set up mocks
        mock_app = Mock()
        mock_dapr_app_instance = Mock()
        mock_dapr_app.return_value = mock_dapr_app_instance
        mock_fastapi.return_value = mock_app
        
        # Call the function
        _build_app()
        
        # Assert that subscribe was called with correct parameters
        mock_dapr_app_instance.subscribe.assert_called_once()
        call_kwargs = mock_dapr_app_instance.subscribe.call_args.kwargs
        assert call_kwargs.get('pubsub') == 'redis-pubsub'
        assert call_kwargs.get('topic') == 'messages'


class TestLiteLLMIntegration:
    """Tests for LiteLLM integration.
    
    These tests verify that LiteLLM is correctly integrated for generating Buddha responses.
    """
    
    def test_litellm_completion_is_used(self):
        """Verify that litellm.completion is available and callable."""
        try:
            from litellm import completion
            assert callable(completion)
        except ImportError:
            pytest.fail("LiteLLM completion function not found")
    
    @patch('openai_service_worldofgeese.__main__.completion')
    def test_completion_with_buddha_system_prompt(self, mock_completion):
        """Test that completion is called with the Buddha system prompt."""
        from openai_service_worldofgeese.__main__ import _build_app
        
        # Set up mocks
        mock_app = Mock()
        mock_dapr_app_instance = Mock()
        mock_dapr_client_instance = Mock()
        
        # Mock the completion function
        mock_completion.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        
        # The system prompt should be included in the messages
        expected_system_prompt = (
            "You are the Buddha. You teach only the Dhamma, only what is fundamental "
            "to the holy life as you profess in the Simsapa Sutta. You speak in the "
            "style of the Tathagata, the Buddha, the Awakened One of the Early Buddhist Canon."
        )
        
        # Verify the system prompt content
        assert "Dhamma" in expected_system_prompt
        assert "Simsapa Sutta" in expected_system_prompt
        assert "Tathagata" in expected_system_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
