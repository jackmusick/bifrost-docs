"""
Redis Cache Module

Provides a shared Redis client for caching and temporary data storage.
Used for WebAuthn challenges, session tokens, and other short-lived data.
"""

import redis.asyncio as redis

from src.config import get_settings

# Module-level cache for the Redis client
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """
    Get the shared Redis client instance.

    Creates a new connection on first call, reuses for subsequent calls.
    The client should be closed on application shutdown.

    Returns:
        Async Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    return _redis_client


async def close_redis() -> None:
    """
    Close the Redis connection.

    Should be called on application shutdown.
    """
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
