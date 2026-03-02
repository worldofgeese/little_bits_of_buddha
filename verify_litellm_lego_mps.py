#!/usr/bin/env python3
"""Integration test script to verify LiteLLM -> LEGO MPS works.

This script tests that we can successfully call the LEGO MPS endpoint
via LiteLLM with the Anthropic provider.
"""

import os

from litellm import completion


def test_lego_mps_connection():
    """Test that we can connect to LEGO MPS via LiteLLM."""
    # Get credentials from environment
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not auth_token:
        raise ValueError("ANTHROPIC_AUTH_TOKEN environment variable is not set")

    # Verify the token has the expected format (colon-separated)
    if ":" not in auth_token:
        raise ValueError(
            "ANTHROPIC_AUTH_TOKEN should be colon-separated (LEGO MPS format)"
        )

    print("✓ ANTHROPIC_AUTH_TOKEN is set and has correct format")

    # Test configuration
    model = "anthropic/anthropic.claude-sonnet-4-5-20250929-v1:0"
    api_base = "https://ANTHROPIC_PROXY_HOST/claude"
    test_message = "Hello, please respond with a single word: 'Success'"

    print("\nTesting LiteLLM configuration:")
    print(f"  Model: {model}")
    print(f"  API Base: {api_base}")
    print("  Note: LiteLLM will append /v1/messages to the base URL")

    try:
        # Make the completion call
        print("\nSending test message to LEGO MPS...")
        response = completion(
            model=model,
            api_base=api_base,
            api_key=auth_token,
            messages=[{"role": "user", "content": test_message}],
        )

        # Extract and display the response
        response_text = response["choices"][0]["message"]["content"]
        print("\n✓ Successfully received response from LEGO MPS!")
        print(f"Response: {response_text}")

        return True

    except Exception as e:
        print("\n✗ Failed to call LEGO MPS via LiteLLM")
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    try:
        test_lego_mps_connection()
        print("\n" + "=" * 60)
        print("SUCCESS: LiteLLM -> LEGO MPS integration is working!")
        print("=" * 60)
    except Exception:
        print("\n" + "=" * 60)
        print("FAILURE: LiteLLM -> LEGO MPS integration test failed")
        print("=" * 60)
        raise
