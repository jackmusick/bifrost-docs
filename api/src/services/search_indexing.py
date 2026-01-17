"""
Search Indexing Service.

Provides helper functions for enqueueing entities for search indexing.
These functions handle errors gracefully and don't block the main request.
Actual indexing is performed asynchronously by the worker (src/worker.py).
"""

import logging
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.llm.factory import is_indexing_enabled

logger = logging.getLogger(__name__)

EntityType = Literal["password", "configuration", "location", "document", "custom_asset"]


async def index_entity_for_search(
    db: AsyncSession,
    entity_type: EntityType,
    entity_id: UUID,
    org_id: UUID,
) -> None:
    """
    Enqueue an entity for semantic search indexing.

    This function is designed to be called from routers after create/update.
    It handles errors gracefully - failures don't affect the main request.
    Actual indexing is processed asynchronously by the worker.

    Args:
        db: Database session
        entity_type: Type of entity
        entity_id: Entity UUID
        org_id: Organization UUID
    """
    try:
        # Check if indexing is enabled (don't even enqueue if disabled)
        if not await is_indexing_enabled(db):
            logger.debug(
                f"Skipping indexing for {entity_type}/{entity_id} - indexing disabled",
                extra={
                    "entity_type": entity_type,
                    "entity_id": str(entity_id),
                    "org_id": str(org_id),
                },
            )
            return

        # Enqueue for async processing by the worker
        from src.services.indexing_queue import enqueue_index_entity

        await enqueue_index_entity(entity_type, str(entity_id), str(org_id))
    except Exception as e:
        # Log but don't fail the request
        logger.warning(
            f"Failed to enqueue {entity_type}/{entity_id} for indexing: {e}",
            extra={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "org_id": str(org_id),
            },
        )


async def remove_entity_from_search(
    db: AsyncSession,  # noqa: ARG001 - kept for API compatibility
    entity_type: EntityType,
    entity_id: UUID,
) -> None:
    """
    Enqueue entity removal from the search index.

    This function is designed to be called from routers after delete.
    It handles errors gracefully - failures don't affect the main request.
    Actual removal is processed asynchronously by the worker.

    Args:
        db: Database session (kept for API compatibility)
        entity_type: Type of entity
        entity_id: Entity UUID
    """
    try:
        # Enqueue for async processing by the worker
        from src.services.indexing_queue import enqueue_remove_entity

        await enqueue_remove_entity(entity_type, str(entity_id))
    except Exception as e:
        # Log but don't fail the request
        logger.warning(
            f"Failed to enqueue {entity_type}/{entity_id} for removal from index: {e}",
            extra={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
            },
        )
