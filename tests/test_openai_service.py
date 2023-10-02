import pytest
import requests

from openai_service_worldofgeese.__main__ import wait_for_dapr_ready

def test_wait_for_dapr_ready(mocker):
    # Mock the requests.get call to return a response with status code 204
    mock_get = mocker.patch('requests.get')
    mock_get.return_value.status_code = 204

    # Call the function
    wait_for_dapr_ready()

    # Assert that requests.get was called with the correct URL
    mock_get.assert_called_once_with('http://localhost:3500/v1.0/healthz')
    
