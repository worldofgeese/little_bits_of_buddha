#!/usr/bin/env python3
"""Integration test script to verify Anthropic proxy works with raw httpx."""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from openai_service_worldofgeese.__main__ import _call_anthropic_proxy


@pytest.mark.integration
def test_anthropic_proxy_connection():
    """Test that we can connect to Anthropic proxy via raw httpx."""
    # Get credentials from environment
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not auth_token:
        raise ValueError("ANTHROPIC_AUTH_TOKEN environment variable is not set")

    print("✓ ANTHROPIC_AUTH_TOKEN is set")

    # Test configuration
    model = "anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0"
    api_base = os.environ.get("ANTHROPIC_BASE_URL")
    if not api_base:
        raise ValueError("ANTHROPIC_BASE_URL environment variable is not set for integration test")
    test_message = "Hello Buddha, please respond with a single word: 'Success'"

    print("\nTesting Anthropic proxy integration:")
    print(f"  Model: {model}")
    print(f"  API Base: {api_base}")
    print("  Using: raw httpx (avoiding LiteLLM's x-api-key header)")

    try:
        # Make the completion call using our helper
        print("\nSending test message to Anthropic proxy...")
        response = _call_anthropic_proxy(
            model=model,
            api_base=api_base,
            api_key=auth_token,
            messages=[
                {"role": "system", "content": "You are the Buddha."},
                {"role": "user", "content": test_message},
            ],
        )

        # Extract and display the response
        response_text = response["choices"][0]["message"]["content"]
        print("\n✓ Successfully received response from Anthropic proxy!")
        print(f"Response: {response_text}")

        return True

    except Exception as e:
        print("\n✗ Failed to call Anthropic proxy")
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    try:
        test_anthropic_proxy_connection()
        print("\n" + "=" * 60)
        print("SUCCESS: Anthropic proxy integration is working!")
        print("=" * 60)
    except Exception:
        print("\n" + "=" * 60)
        print("FAILURE: Anthropic proxy integration test failed")
        print("=" * 60)
        sys.exit(1)
