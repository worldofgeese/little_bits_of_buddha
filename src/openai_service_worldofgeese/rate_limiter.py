"""Rate limiting module using Redis.

This module provides per-user rate limiting using Redis CL.THROTTLE command
(redis-cell module) with a fallback to INCR + EXPIRE pattern if redis-cell
is not available.
"""

import os

import redis.asyncio as aioredis


def get_redis_client() -> aioredis.Redis:
    """Get a Redis client instance.

    Returns:
        Redis client connected to localhost:6379
    """
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    return aioredis.Redis(host=redis_host, port=redis_port, decode_responses=True)


async def check_rate_limit(chat_id: str) -> tuple[bool, int]:
    """Check if a user has exceeded their rate limit.

    Uses Redis CL.THROTTLE command (redis-cell module) for precise rate limiting.
    Falls back to INCR + EXPIRE pattern if redis-cell is not available.

    Arguments:
        chat_id: Unique identifier for the chat/user

    Returns:
        tuple[bool, int]: (allowed, retry_after_seconds)
            - allowed: True if request is allowed, False if rate-limited
            - retry_after_seconds: seconds until next request allowed (0 if allowed)

    Environment variables:
        RATE_LIMIT_COUNT: Max requests per period (default: 20)
        RATE_LIMIT_PERIOD: Period in seconds (default: 3600 = 1 hour)
    """
    redis_client = get_redis_client()
    key = f"rate_limit:{chat_id}"

    # Get rate limit configuration from environment
    limit_count = int(os.environ.get("RATE_LIMIT_COUNT", "20"))
    limit_period = int(os.environ.get("RATE_LIMIT_PERIOD", "3600"))

    try:
        # Try using redis-cell CL.THROTTLE command
        # CL.THROTTLE <key> <max_burst> <count> <period> <quantity>
        # max_burst is typically count - 1 to allow bursts up to the limit
        max_burst = limit_count - 1

        result = await redis_client.execute_command(
            "CL.THROTTLE", key, max_burst, limit_count, limit_period, 1
        )

        # CL.THROTTLE returns: [allowed, limit, remaining, retry_after, reset_after]
        # allowed: 0 if allowed, 1 if rate-limited
        # limit: the total limit
        # remaining: remaining requests in current window
        # retry_after: seconds until next request (-1 if allowed)
        # reset_after: seconds until counter resets
        allowed = result[0] == 0
        retry_after = result[3] if not allowed else 0

        await redis_client.aclose()
        return (allowed, retry_after)

    except aioredis.ResponseError as e:
        # redis-cell module not available, fall back to INCR + EXPIRE
        error_msg = str(e).lower()
        if (
            "unknown command" in error_msg
            or "cl.throttle" in error_msg
            or error_msg.startswith("err")
        ):
            return await _fallback_rate_limit(
                redis_client, key, limit_count, limit_period
            )
        # Other Redis errors - fail open (allow the request)
        await redis_client.aclose()
        return (True, 0)

    except Exception:
        # Unexpected error - fail open to avoid breaking the service
        try:
            await redis_client.aclose()
        except Exception:
            pass
        return (True, 0)


async def _fallback_rate_limit(
    redis_client: aioredis.Redis, key: str, limit_count: int, limit_period: int
) -> tuple[bool, int]:
    """Fallback rate limiting using INCR + EXPIRE pattern.

    Less precise than redis-cell but works without additional modules.

    Arguments:
        redis_client: Redis client instance
        key: Rate limit key
        limit_count: Maximum requests allowed
        limit_period: Period in seconds

    Returns:
        tuple[bool, int]: (allowed, retry_after_seconds)
    """
    try:
        # Increment the counter
        count = await redis_client.incr(key)

        # Set expiry on first request
        if count == 1:
            await redis_client.expire(key, limit_period)

        # Check if over limit
        if count > limit_count:
            # Get remaining TTL for retry_after
            ttl = await redis_client.ttl(key)
            retry_after = ttl if ttl > 0 else limit_period
            await redis_client.aclose()
            return (False, retry_after)

        # Request allowed
        await redis_client.aclose()
        return (True, 0)

    except Exception:
        # On error, fail open
        try:
            await redis_client.aclose()
        except Exception:
            pass
        return (True, 0)
