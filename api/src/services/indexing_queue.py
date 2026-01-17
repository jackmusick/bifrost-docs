"""
Indexing Queue Service.

Provides async functions to enqueue indexing jobs for background processing.
Jobs are processed by the arq worker (src/worker.py).

This allows indexing to happen asynchronously without blocking API responses.
"""

import logging

from arq import create_pool
from arq.connections import RedisSettings

from src.config import get_settings

logger = logging.getLogger(__name__)


async def enqueue_index_entity(
    entity_type: str,
    entity_id: str,
    org_id: str,
) -> None:
    """
    Enqueue an entity for indexing.

    Called from routers after create/update operations.
    The job will be processed asynchronously by the worker.

    Args:
        entity_type: Type of entity (password, document, configuration, etc.)
        entity_id: UUID of the entity as string
        org_id: UUID of the organization as string
    """
    settings = get_settings()
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job(
            "index_entity_task",
            entity_type,
            entity_id,
            org_id,
        )
        logger.debug(
            f"Enqueued index job for {entity_type}/{entity_id}",
            extra={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "org_id": org_id,
            },
        )
    except Exception as e:
        # Log but don't fail the request - indexing is best-effort
        logger.warning(
            f"Failed to enqueue index job for {entity_type}/{entity_id}: {e}",
            extra={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "org_id": org_id,
                "error": str(e),
            },
        )


async def enqueue_remove_entity(
    entity_type: str,
    entity_id: str,
) -> None:
    """
    Enqueue entity removal from index.

    Called from routers after delete operations.
    The job will be processed asynchronously by the worker.

    Args:
        entity_type: Type of entity (password, document, configuration, etc.)
        entity_id: UUID of the entity as string
    """
    settings = get_settings()
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job(
            "remove_entity_task",
            entity_type,
            entity_id,
        )
        logger.debug(
            f"Enqueued remove job for {entity_type}/{entity_id}",
            extra={
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
        )
    except Exception as e:
        # Log but don't fail the request - index removal is best-effort
        logger.warning(
            f"Failed to enqueue remove job for {entity_type}/{entity_id}: {e}",
            extra={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "error": str(e),
            },
        )
