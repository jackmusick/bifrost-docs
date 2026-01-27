"""
arq Worker Configuration.

This module defines the background task worker for processing search indexing jobs.
Tasks are dispatched from API routes and processed asynchronously to avoid blocking
HTTP requests.

Run the worker with:
    arq src.worker.WorkerSettings
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from uuid import UUID

from arq import cron, func
from arq.connections import RedisSettings

from src.config import get_settings

logger = logging.getLogger(__name__)

# Valid entity types for indexing - must match EntityType in search_indexing.py
EntityType = Literal["password", "configuration", "location", "document", "custom_asset"]
VALID_ENTITY_TYPES: set[str] = {"password", "configuration", "location", "document", "custom_asset"}


async def index_entity_task(
    _ctx: dict[str, Any],
    entity_type: str,
    entity_id: str,
    org_id: str,
) -> None:
    """
    Process a single entity indexing job.

    This task is queued when entities are created or updated in the API.
    It generates embeddings and stores them in the search index.

    IMPORTANT: Only enabled entities are indexed. If an entity is disabled,
    it will be removed from the index instead of being indexed.

    Args:
        _ctx: arq context (contains redis connection, job info, etc.)
        entity_type: Type of entity (password, configuration, location, document, custom_asset)
        entity_id: Entity UUID as string
        org_id: Organization UUID as string
    """
    from sqlalchemy import select

    from src.core.database import get_db_context
    from src.models.orm.configuration import Configuration
    from src.models.orm.custom_asset import CustomAsset
    from src.models.orm.document import Document
    from src.models.orm.location import Location
    from src.models.orm.password import Password
    from src.services.embeddings import get_embeddings_service
    from src.services.llm.factory import is_indexing_enabled

    logger.info(
        f"Processing index job for {entity_type}/{entity_id}",
        extra={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "org_id": org_id,
        },
    )

    # Validate entity_type
    if entity_type not in VALID_ENTITY_TYPES:
        logger.error(f"Invalid entity_type: {entity_type}")
        raise ValueError(f"Invalid entity_type: {entity_type}")

    typed_entity_type = cast(EntityType, entity_type)
    entity_uuid = UUID(entity_id)

    async with get_db_context() as db:
        # Check if indexing is enabled
        if not await is_indexing_enabled(db):
            logger.debug(f"Skipping indexing for {entity_type}/{entity_id} - indexing disabled")
            return

        # Check if entity is enabled - only index enabled entities
        entity_models: dict[str, type] = {
            "password": Password,
            "configuration": Configuration,
            "location": Location,
            "document": Document,
            "custom_asset": CustomAsset,
        }
        model = entity_models[entity_type]
        result = await db.execute(select(model.is_enabled).where(model.id == entity_uuid))
        is_enabled = result.scalar_one_or_none()

        embeddings_service = get_embeddings_service(db)

        # If entity is disabled or doesn't exist, remove from index
        if is_enabled is None or not is_enabled:
            logger.info(
                f"Entity {entity_type}/{entity_id} is disabled or not found, removing from index",
                extra={"entity_type": entity_type, "entity_id": entity_id},
            )
            await embeddings_service.delete_index(db, typed_entity_type, entity_uuid)
            return

        # Entity is enabled - proceed with indexing
        if not await embeddings_service.check_openai_available():
            logger.debug(f"Skipping indexing for {entity_type}/{entity_id} - OpenAI not configured")
            return

        await embeddings_service.index_entity(
            db,
            typed_entity_type,
            entity_uuid,
            UUID(org_id),
        )

    logger.info(
        f"Completed index job for {entity_type}/{entity_id}",
        extra={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "org_id": org_id,
        },
    )


async def remove_entity_task(
    _ctx: dict[str, Any],
    entity_type: str,
    entity_id: str,
) -> None:
    """
    Process entity removal from search index.

    This task is queued when entities are deleted from the API.
    It removes the entity's embeddings from the search index.

    Args:
        _ctx: arq context (contains redis connection, job info, etc.)
        entity_type: Type of entity (password, configuration, location, document, custom_asset)
        entity_id: Entity UUID as string
    """
    from src.core.database import get_db_context
    from src.services.embeddings import get_embeddings_service

    logger.info(
        f"Processing remove job for {entity_type}/{entity_id}",
        extra={
            "entity_type": entity_type,
            "entity_id": entity_id,
        },
    )

    # Validate entity_type
    if entity_type not in VALID_ENTITY_TYPES:
        logger.error(f"Invalid entity_type: {entity_type}")
        raise ValueError(f"Invalid entity_type: {entity_type}")

    typed_entity_type = cast(EntityType, entity_type)

    async with get_db_context() as db:
        # Call embeddings service directly (not search_indexing which enqueues)
        embeddings_service = get_embeddings_service(db)
        await embeddings_service.delete_index(db, typed_entity_type, UUID(entity_id))

    logger.info(
        f"Completed remove job for {entity_type}/{entity_id}",
        extra={
            "entity_type": entity_type,
            "entity_id": entity_id,
        },
    )


async def reindex_task(
    ctx: dict[str, Any],  # noqa: ARG001
    job_id: str,
    entity_type: str | None,
    organization_id: str | None,
    total: int,
) -> None:
    """
    Process a full reindex job.

    This task handles the entire reindex operation, processing only entities
    that don't yet have embeddings. This makes the job naturally resumable -
    if it fails partway through, re-running will pick up where it left off.

    Args:
        ctx: arq context (unused but required by arq)
        job_id: Unique job ID for progress tracking
        entity_type: Optional specific entity type to reindex (or all if None)
        organization_id: Optional org filter (or all orgs if None)
        total: Total number of entities to index (may include already-indexed)
    """
    import asyncio
    import time

    from redis.asyncio import Redis
    from sqlalchemy import and_, select

    from src.core.database import get_db_context
    from src.core.pubsub import (
        publish_reindex_cancelled,
        publish_reindex_completed,
        publish_reindex_failed,
        publish_reindex_progress,
    )
    from src.models.orm.configuration import Configuration
    from src.models.orm.custom_asset import CustomAsset
    from src.models.orm.document import Document
    from src.models.orm.embedding_index import EmbeddingIndex
    from src.models.orm.location import Location
    from src.models.orm.password import Password
    from src.services.embeddings import get_embeddings_service
    from src.services.llm.factory import is_indexing_enabled
    from src.services.reindex_state import ReindexStateService

    logger.info(
        f"Starting reindex job {job_id} with {total} entities",
        extra={"job_id": job_id, "total": total, "entity_type": entity_type, "organization_id": organization_id},
    )

    start_time = time.time()
    processed = 0
    already_indexed = 0
    errors = 0
    counts_by_type: dict[str, int] = {}

    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    state_service = ReindexStateService(redis)

    org_uuid = UUID(organization_id) if organization_id else None

    try:
        async with get_db_context() as db:
            # Check if indexing is enabled
            if not await is_indexing_enabled(db):
                logger.warning(f"Reindex {job_id} skipped - indexing disabled")
                await state_service.fail_job(job_id, "Indexing is disabled")
                await publish_reindex_failed(job_id=job_id, error="Indexing is disabled")
                logger.info(f"Published reindex_failed for job {job_id} (indexing disabled)")
                return

            embeddings_service = get_embeddings_service(db)
            if not await embeddings_service.check_openai_available():
                logger.warning(f"Reindex {job_id} skipped - OpenAI not configured")
                await state_service.fail_job(job_id, "OpenAI not configured")
                await publish_reindex_failed(job_id=job_id, error="OpenAI not configured")
                logger.info(f"Published reindex_failed for job {job_id} (OpenAI not configured)")
                return

            logger.info(f"Reindex {job_id} - indexing enabled, OpenAI available, starting processing")

            # Define entity types to process
            entity_types: list[str] = (
                [entity_type] if entity_type else ["password", "configuration", "location", "document", "custom_asset"]
            )

            # Entity model mapping for building queries
            entity_models: dict[str, type] = {
                "password": Password,
                "configuration": Configuration,
                "location": Location,
                "document": Document,
                "custom_asset": CustomAsset,
            }

            for etype in entity_types:
                counts_by_type[etype] = 0
                typed_etype = cast(EntityType, etype)

                model = entity_models.get(etype)
                if model is None:
                    continue

                # Query for ENABLED entities WITHOUT embeddings (LEFT JOIN + NULL check)
                # This makes the job naturally resumable - only processes what's missing
                # Only index enabled entities - disabled ones should not be in the index
                stmt = (
                    select(model.id, model.organization_id)
                    .outerjoin(
                        EmbeddingIndex,
                        and_(
                            EmbeddingIndex.entity_type == etype,
                            EmbeddingIndex.entity_id == model.id,
                        ),
                    )
                    .where(EmbeddingIndex.id.is_(None))
                    .where(model.is_enabled.is_(True))  # Only index enabled entities
                )

                if org_uuid is not None:
                    stmt = stmt.where(model.organization_id == org_uuid)

                result = await db.execute(stmt)
                entities = result.all()

                entities_needing_index = len(entities)
                logger.info(f"Reindex {job_id}: {entities_needing_index} {etype}s need indexing")

                # Index each entity that doesn't have an embedding
                for entity_id, entity_org_id in entities:
                    # Check for cancellation before each entity
                    if await state_service.is_cancelled(job_id):
                        logger.info(f"Reindex {job_id} cancelled by user at {processed}/{total}")
                        await state_service.mark_cancelled(job_id)
                        await publish_reindex_cancelled(
                            job_id=job_id,
                            processed=processed,
                            total=total,
                            force=False,
                        )
                        return

                    try:
                        await embeddings_service.index_entity(db, typed_etype, entity_id, entity_org_id)
                        processed += 1
                        counts_by_type[etype] += 1
                    except Exception as e:
                        logger.error(f"Failed to index {etype}/{entity_id}: {e}", exc_info=True)
                        errors += 1

                    # Update progress (processed + already_indexed for accurate total progress)
                    current_progress = processed + already_indexed
                    await state_service.update_progress(job_id, current_progress, errors, etype)
                    await publish_reindex_progress(
                        job_id=job_id,
                        phase=f"Indexing {etype}s",
                        current=current_progress,
                        total=total,
                        entity_type=etype,
                    )

                    # Log every 10 entities to avoid log spam
                    if processed % 10 == 0:
                        logger.info(f"Reindex {job_id} progress: {current_progress}/{total} ({etype})")

                    # Small delay to avoid overwhelming OpenAI API
                    await asyncio.sleep(0.1)

            await db.commit()

        # Complete
        duration = time.time() - start_time
        await state_service.complete_job(job_id)
        await publish_reindex_completed(job_id=job_id, counts=counts_by_type, duration_seconds=duration)

        logger.info(
            f"Reindex {job_id} completed - published completion event",
            extra={
                "job_id": job_id,
                "processed": processed,
                "already_indexed": already_indexed,
                "errors": errors,
                "duration": duration,
                "counts": counts_by_type,
            },
        )

    except Exception as e:
        logger.error(f"Reindex {job_id} failed: {e}", exc_info=True)
        await state_service.fail_job(job_id, str(e))
        await publish_reindex_failed(job_id=job_id, error=str(e))

    finally:
        await redis.aclose()


async def cleanup_audit_logs_task(
    ctx: dict[str, Any],
) -> None:
    """
    Clean up audit logs older than 1 year.

    This task runs daily via cron to maintain audit log retention policy.
    Deletes all audit log entries created more than 365 days ago.

    Args:
        ctx: arq context (contains redis connection, job info, etc.)
    """
    from src.core.database import get_db_context
    from src.repositories.audit import AuditRepository

    logger.info("Starting audit log cleanup")

    cutoff = datetime.now(UTC) - timedelta(days=365)

    async with get_db_context() as db:
        audit_repo = AuditRepository(db)
        deleted_count = await audit_repo.delete_older_than(cutoff)
        await db.commit()

    logger.info(
        f"Audit log cleanup complete: deleted {deleted_count} records older than {cutoff}",
        extra={
            "deleted_count": deleted_count,
            "cutoff": cutoff.isoformat(),
        },
    )


class WorkerSettings:
    """
    arq worker settings.

    Configures the worker's connection to Redis, task functions,
    concurrency limits, timeouts, and retry behavior.
    """

    # Task functions to register with the worker
    # reindex_task gets a 6-hour timeout since it processes thousands of entities
    # Other tasks use the global job_timeout (60s)
    functions = [
        index_entity_task,
        remove_entity_task,
        func(reindex_task, timeout=21600),  # 6 hours for bulk reindexing
        cleanup_audit_logs_task,
    ]

    # Cron jobs for scheduled tasks
    cron_jobs = [
        cron(cleanup_audit_logs_task, hour=3, minute=0),  # Run daily at 3am
    ]

    # Redis connection settings (loaded from environment)
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

    # Concurrency: max jobs processed simultaneously per worker
    # Keep low to avoid overwhelming OpenAI API rate limits
    max_jobs = 10

    # Job timeout in seconds (embeddings API calls can be slow)
    job_timeout = 60

    # Retry failed jobs
    retry_jobs = True

    # Max retry attempts before marking job as failed
    max_tries = 3
