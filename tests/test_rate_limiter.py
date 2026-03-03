"""Tests for the rate limiter module.

This module follows the How to Design Functions (HtDF) recipe:
1. Signature, purpose, stub
2. Examples (tests)
3. Template/inventory
4. Code body
5. Test and debug
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest
import redis.asyncio as aioredis


class TestCheckRateLimit:
    """Tests for the check_rate_limit function.

    Signature:
        async def check_rate_limit(chat_id: str) -> tuple[bool, int]

    Purpose:
        Check if a user (identified by chat_id) has exceeded their rate limit.
        Uses Redis CL.THROTTLE command (redis-cell module) for per-user rate limiting.
        Falls back to INCR + EXPIRE pattern if redis-cell is not available.

    Returns:
        tuple[bool, int]: (allowed: bool, retry_after_seconds: int)
            - allowed: True if the request is allowed, False if rate-limited
            - retry_after_seconds: seconds until the user can make another request (0 if allowed)

    Examples:
        - First request from a user: allowed=True, retry_after=0
        - Request under limit: allowed=True, retry_after=0
        - Request over limit: allowed=False, retry_after=N (seconds)
        - Redis error: should handle gracefully
    """

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_first_request(self, mocker):
        """Test that the first request from a user is allowed."""
        # Mock Redis client
        mock_redis = AsyncMock(spec=aioredis.Redis)
        mock_execute_command = AsyncMock(return_value=[0, 20, 19, -1, 3600])
        mock_redis.execute_command = mock_execute_command

        mocker.patch(
            "openai_service_worldofgeese.rate_limiter.get_redis_client",
            return_value=mock_redis,
        )

        from openai_service_worldofgeese.rate_limiter import check_rate_limit

        # Call the function
        allowed, retry_after = await check_rate_limit("chat_123")

        # Assert that the request is allowed
        assert allowed is True
        assert retry_after == 0

        # Verify CL.THROTTLE was called with correct parameters
        mock_execute_command.assert_called_once_with(
            "CL.THROTTLE", "rate_limit:chat_123", 19, 20, 3600, 1
        )

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_request_under_limit(self, mocker):
        """Test that requests under the limit are allowed."""
        # Mock Redis client - 10 requests used out of 20
        mock_redis = AsyncMock(spec=aioredis.Redis)
        mock_execute_command = AsyncMock(return_value=[0, 20, 9, -1, 1800])
        mock_redis.execute_command = mock_execute_command

        mocker.patch(
            "openai_service_worldofgeese.rate_limiter.get_redis_client",
            return_value=mock_redis,
        )

        from openai_service_worldofgeese.rate_limiter import check_rate_limit

        allowed, retry_after = await check_rate_limit("chat_456")

        assert allowed is True
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_request_over_limit(self, mocker):
        """Test that requests over the limit are blocked."""
        # Mock Redis client - rate limited, need to wait 120 seconds
        mock_redis = AsyncMock(spec=aioredis.Redis)
        mock_execute_command = AsyncMock(return_value=[1, 20, 0, 120, 3600])
        mock_redis.execute_command = mock_execute_command

        mocker.patch(
            "openai_service_worldofgeese.rate_limiter.get_redis_client",
            return_value=mock_redis,
        )

        from openai_service_worldofgeese.rate_limiter import check_rate_limit

        allowed, retry_after = await check_rate_limit("chat_789")

        assert allowed is False
        assert retry_after == 120

    @pytest.mark.asyncio
    async def test_check_rate_limit_respects_env_vars(self, mocker):
        """Test that rate limit configuration respects environment variables."""
        # Mock environment variables
        mocker.patch.dict(
            os.environ, {"RATE_LIMIT_COUNT": "10", "RATE_LIMIT_PERIOD": "1800"}
        )

        # Mock Redis client
        mock_redis = AsyncMock(spec=aioredis.Redis)
        mock_execute_command = AsyncMock(return_value=[0, 10, 9, -1, 1800])
        mock_redis.execute_command = mock_execute_command

        mocker.patch(
            "openai_service_worldofgeese.rate_limiter.get_redis_client",
            return_value=mock_redis,
        )

        from openai_service_worldofgeese.rate_limiter import check_rate_limit

        await check_rate_limit("chat_custom")

        # Verify CL.THROTTLE was called with custom values
        # CL.THROTTLE key max_burst count_per_period period 1
        # max_burst = count - 1 = 9
        mock_execute_command.assert_called_once_with(
            "CL.THROTTLE", "rate_limit:chat_custom", 9, 10, 1800, 1
        )

    @pytest.mark.asyncio
    async def test_check_rate_limit_fallback_when_module_unavailable(self, mocker):
        """Test fallback to INCR + EXPIRE when redis-cell module is not available."""
        # Mock Redis client that raises error for CL.THROTTLE
        mock_redis = AsyncMock(spec=aioredis.Redis)
        mock_execute_command = AsyncMock(
            side_effect=aioredis.ResponseError("ERR unknown command 'CL.THROTTLE'")
        )
        mock_redis.execute_command = mock_execute_command

        # Mock fallback methods
        mock_redis.incr = AsyncMock(return_value=5)
        mock_redis.expire = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=3000)

        mocker.patch(
            "openai_service_worldofgeese.rate_limiter.get_redis_client",
            return_value=mock_redis,
        )

        from openai_service_worldofgeese.rate_limiter import check_rate_limit

        allowed, retry_after = await check_rate_limit("chat_fallback")

        # Should allow request (5 < 20)
        assert allowed is True
        assert retry_after == 0

        # Verify fallback was used
        mock_redis.incr.assert_called_once_with("rate_limit:chat_fallback")
        # expire should NOT be called when count > 1 (this is the 5th request)
        mock_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_rate_limit_fallback_blocks_over_limit(self, mocker):
        """Test that fallback pattern blocks requests over the limit."""
        # Mock Redis client with fallback
        mock_redis = AsyncMock(spec=aioredis.Redis)
        mock_execute_command = AsyncMock(
            side_effect=aioredis.ResponseError("ERR unknown command")
        )
        mock_redis.execute_command = mock_execute_command

        # Mock fallback - 25 requests (over limit of 20)
        mock_redis.incr = AsyncMock(return_value=25)
        mock_redis.expire = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=1200)  # 20 minutes remaining

        mocker.patch(
            "openai_service_worldofgeese.rate_limiter.get_redis_client",
            return_value=mock_redis,
        )

        from openai_service_worldofgeese.rate_limiter import check_rate_limit

        allowed, retry_after = await check_rate_limit("chat_over")

        # Should block request
        assert allowed is False
        assert retry_after == 1200

    @pytest.mark.asyncio
    async def test_check_rate_limit_fallback_sets_expire_on_first_request(
        self, mocker
    ):
        """Test that fallback pattern sets expiry on the first request."""
        # Mock Redis client with fallback
        mock_redis = AsyncMock(spec=aioredis.Redis)
        mock_execute_command = AsyncMock(side_effect=aioredis.ResponseError("ERR"))
        mock_redis.execute_command = mock_execute_command

        # First request (count = 1)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=3600)

        mocker.patch(
            "openai_service_worldofgeese.rate_limiter.get_redis_client",
            return_value=mock_redis,
        )

        from openai_service_worldofgeese.rate_limiter import check_rate_limit

        await check_rate_limit("chat_first")

        # Verify expire was called
        mock_redis.expire.assert_called_once_with("rate_limit:chat_first", 3600)


class TestRateLimitIntegration:
    """Integration tests for rate limiting in the message handler.

    Note: These tests verify the rate limiting logic is integrated into __main__.py.
    Full integration testing with Dapr requires the integration test environment.
    """

    @pytest.mark.integration
    def test_rate_limiter_integration_placeholder(self):
        """Placeholder for rate limiter integration tests.

        The rate_limiter module is integrated into __main__.py's messages_subscriber.
        Full end-to-end testing requires a running Dapr environment and is marked
        as integration testing.

        This test serves as documentation that integration tests exist in the
        integration test suite.
        """
        # The actual integration with __main__.py is verified by:
        # 1. The import of check_rate_limit in _build_app()
        # 2. The rate limit check before LLM processing
        # 3. The gentle Buddhist response when rate-limited
        # Integration tests are run separately with Dapr environment
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
