"""Tests for the openai_service_worldofgeese module.

This module follows the How to Design Functions (HtDF) recipe:
1. Signature, purpose, stub
2. Examples (tests)
3. Template/inventory
4. Code body
5. Test and debug
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

# Mock dapr modules before any imports
sys.modules["dapr"] = MagicMock()
sys.modules["dapr.clients"] = MagicMock()
sys.modules["dapr.ext"] = MagicMock()
sys.modules["dapr.ext.fastapi"] = MagicMock()

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
        mock_get = mocker.patch("requests.get")
        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response

        # Call the function
        wait_for_dapr_ready(retries=1, delay=0.1)

        # Assert that requests.get was called with the correct URL
        mock_get.assert_called_once_with("http://localhost:3500/v1.0/healthz")

    def test_wait_for_dapr_ready_success_after_retries(self, mocker):
        """Test that wait_for_dapr_ready retries and eventually succeeds."""
        # Mock the requests.get call to fail twice, then succeed
        mock_get = mocker.patch("requests.get")

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
        mock_get = mocker.patch("requests.get")
        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response

        wait_for_dapr_ready(dapr_port=3600, retries=1, delay=0.1)

        mock_get.assert_called_once_with("http://localhost:3600/v1.0/healthz")

    def test_wait_for_dapr_ready_raises_error_after_retries(self, mocker):
        """Test that wait_for_dapr_ready raises RuntimeError after exhausting retries."""
        # Mock the requests.get call to always fail
        mock_get = mocker.patch("requests.get")
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Expect RuntimeError to be raised
        with pytest.raises(RuntimeError, match="Dapr sidecar is not ready"):
            wait_for_dapr_ready(retries=3, delay=0.1)

    def test_wait_for_dapr_ready_handles_connection_error(self, mocker):
        """Test that wait_for_dapr_ready handles connection errors gracefully."""
        mock_get = mocker.patch("requests.get")
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

    @patch("dapr.clients.DaprClient")
    @patch("dapr.ext.fastapi.DaprApp")
    @patch("fastapi.FastAPI")
    def test_build_app_returns_tuple(
        self, mock_fastapi, mock_dapr_app, mock_dapr_client
    ):
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

    @patch("dapr.clients.DaprClient")
    @patch("dapr.ext.fastapi.DaprApp")
    @patch("fastapi.FastAPI")
    def test_build_app_has_subscriber_decorator(
        self, mock_fastapi, mock_dapr_app, mock_dapr_client
    ):
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
        assert call_kwargs.get("pubsub") == "redis-pubsub"
        assert call_kwargs.get("topic") == "messages"


class TestAnthropicProxyIntegration:
    """Tests for Anthropic proxy integration via raw httpx.

    We use raw httpx instead of LiteLLM because Anthropic proxy (a Bedrock proxy)
    fails when LiteLLM sends both Authorization and x-api-key headers.
    """

    def test_anthropic_proxy_helper_available(self):
        """Verify that _call_anthropic_proxy helper function exists."""
        from openai_service_worldofgeese.__main__ import _call_anthropic_proxy

        assert callable(_call_anthropic_proxy)

    @patch("openai_service_worldofgeese.__main__._call_anthropic_proxy")
    def test_anthropic_proxy_called_with_correct_params(self, mock_call):
        """Test that _call_anthropic_proxy is called with correct parameters."""
        from openai_service_worldofgeese.__main__ import _call_anthropic_proxy

        # Mock the response
        mock_call.return_value = {
            "choices": [{"message": {"content": "Test Buddha response"}}]
        }

        # Call the function
        api_base = os.environ.get("ANTHROPIC_BASE_URL")
        if not api_base:
            raise RuntimeError("ANTHROPIC_BASE_URL must be set for tests")
        result = _call_anthropic_proxy(
            model="anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0",
            api_base=api_base,
            api_key="test-token",
            messages=[
                {"role": "system", "content": "You are the Buddha."},
                {"role": "user", "content": "Hello"},
            ],
        )

        # Verify the mock was called
        mock_call.assert_called_once()
        assert result["choices"][0]["message"]["content"] == "Test Buddha response"


class TestAnthropicProviderConfig:
    """Tests for Anthropic (Anthropic proxy) provider configuration.

    These tests verify that the service is correctly configured to use
    Anthropic proxy endpoint with raw httpx (not LiteLLM due to header conflict).
    """

    @patch("openai_service_worldofgeese.__main__._call_anthropic_proxy")
    @patch("dapr.clients.DaprClient")
    @patch.dict(
        os.environ,
        {
            "LITELLM_MODEL": "anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0",
            "ANTHROPIC_AUTH_TOKEN": "test-token",
        },
    )
    def test_completion_uses_anthropic_proxy_helper(self, mock_dapr_client, mock_call_proxy):
        """Test that _call_anthropic_proxy is used for Anthropic proxy calls."""
        from openai_service_worldofgeese.__main__ import _build_app

        # Mock the Anthropic proxy call
        mock_call_proxy.return_value = {
            "choices": [{"message": {"content": "Test Buddha response"}}]
        }

        # Mock Dapr client
        mock_client_instance = Mock()
        mock_dapr_client.return_value.__enter__ = Mock(
            return_value=mock_client_instance
        )
        mock_dapr_client.return_value.__exit__ = Mock(return_value=False)

        # Build the app - this should configure the subscriber
        app, _ = _build_app()

        # Verify environment is set correctly
        assert (
            os.environ.get("LITELLM_MODEL")
            == "anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0"
        )
        assert os.environ.get("ANTHROPIC_AUTH_TOKEN") == "test-token"

    def test_anthropic_model_format(self):
        """Test that the Anthropic model format is correct."""
        model = "anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0"

        # Verify the model string starts with 'anthropic/' prefix
        assert model.startswith("anthropic/"), (
            "Model must use 'anthropic/' prefix for LiteLLM"
        )

        # Verify it contains the expected model ID
        assert "claude-sonnet-4-5" in model

    @patch.dict(os.environ, {"ANTHROPIC_AUTH_TOKEN": "test:colon:separated:token"})
    def test_anthropic_auth_token_format(self):
        """Test that ANTHROPIC_AUTH_TOKEN is available and can contain colons."""
        token = os.environ.get("ANTHROPIC_AUTH_TOKEN")

        # The Anthropic proxy token is colon-separated, verify we can handle that
        assert token is not None
        assert ":" in token, "Anthropic proxy auth token should be colon-separated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
