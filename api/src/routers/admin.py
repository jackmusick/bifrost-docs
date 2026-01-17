"""
Admin Router

Provides admin endpoints for platform configuration and user management.
Only accessible by platform administrators (OWNER or ADMINISTRATOR role).

Reindex progress is now streamed via WebSocket (reindex:{job_id} channel).
State is persisted in Redis for multi-worker support.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from redis.asyncio import Redis
from sqlalchemy import func, select, update

from src.config import get_settings
from src.core.auth import RequireAdmin, RequireOwner
from src.core.database import DbSession
from src.core.pubsub import (
    publish_reindex_cancelled,
    publish_reindex_cancelling,
    publish_reindex_failed,
)
from src.models.contracts.common import BatchToggleRequest, BatchToggleResponse
from src.models.enums import UserRole
from src.models.orm.configuration import Configuration
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.document import Document
from src.models.orm.embedding_index import EmbeddingIndex
from src.models.orm.location import Location
from src.models.orm.password import Password
from src.models.orm.user import User
from src.repositories.user import UserRepository
from src.services.embeddings import EntityType
from src.services.reindex_state import ReindexStateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# =============================================================================
# Request/Response Models
# =============================================================================


class AdminConfig(BaseModel):
    """Platform configuration."""

    openai_api_key_set: bool
    embedding_model: str


class AdminConfigUpdate(BaseModel):
    """Update platform configuration."""

    openai_api_key: str | None = None
    embedding_model: str | None = None


class TestConnectionResponse(BaseModel):
    """Connection test result."""

    success: bool
    error: str | None = None


class OrganizationUser(BaseModel):
    """User in organization context."""

    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: str


class CreateUserRequest(BaseModel):
    """Create user request."""

    email: EmailStr
    role: str = "contributor"


class CreateUserResponse(BaseModel):
    """Created user response."""

    id: str
    email: str
    name: str
    role: str
    is_active: bool


class UpdateUserRoleRequest(BaseModel):
    """Update user role request."""

    role: str


class TransferOwnershipRequest(BaseModel):
    """Transfer ownership request."""

    user_id: str


class ReindexRequest(BaseModel):
    """Reindex request parameters."""

    entity_type: EntityType | None = None
    organization_id: str | None = None


class ReindexStatusResponse(BaseModel):
    """Reindex status response."""

    is_running: bool
    status: str | None = None  # running, cancelling, cancelled, completed, failed
    current_entity_type: str | None = None
    processed: int = 0
    total: int = 0
    errors: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None


class ReindexStartResponse(BaseModel):
    """Response when reindex job is started."""

    message: str
    job_id: str


class ReindexCancelResponse(BaseModel):
    """Response when reindex job cancellation is requested."""

    message: str
    status: str  # "cancelling" or "cancelled"
    processed: int
    total: int


class IndexStatsResponse(BaseModel):
    """Statistics about the embedding index."""

    total_indexed: int
    total_entities: int
    total_unindexed: int
    last_indexed_at: str | None = None


# =============================================================================
# Redis Helper
# =============================================================================


async def _get_redis_client() -> Redis:
    """Get a Redis client instance for reindex state management."""
    return Redis.from_url(get_settings().redis_url)


# =============================================================================
# Config Endpoints
# =============================================================================


@router.get("/config", response_model=AdminConfig)
async def get_config(
    current_user: RequireAdmin,
) -> AdminConfig:
    """
    Get platform configuration.

    Requires: ADMINISTRATOR role or higher.

    Returns:
        Current platform configuration
    """
    # TODO: Read from database/settings table
    # For now, return defaults
    return AdminConfig(
        openai_api_key_set=False,
        embedding_model="text-embedding-3-small",
    )


@router.patch("/config", response_model=AdminConfig)
async def update_config(
    config_data: AdminConfigUpdate,
    current_user: RequireAdmin,
) -> AdminConfig:
    """
    Update platform configuration.

    Requires: ADMINISTRATOR role or higher.

    Args:
        config_data: Configuration updates

    Returns:
        Updated configuration
    """

    # TODO: Store in database/settings table
    logger.info(
        "Config updated",
        extra={
            "user_id": str(current_user.user_id),
            "openai_key_updated": config_data.openai_api_key is not None,
            "embedding_model": config_data.embedding_model,
        },
    )

    return AdminConfig(
        openai_api_key_set=config_data.openai_api_key is not None,
        embedding_model=config_data.embedding_model or "text-embedding-3-small",
    )


@router.post("/test-openai", response_model=TestConnectionResponse)
async def test_openai_connection(
    current_user: RequireAdmin,
) -> TestConnectionResponse:
    """
    Test OpenAI API connection.

    Requires: ADMINISTRATOR role or higher.

    Returns:
        Connection test result
    """
    # TODO: Actually test OpenAI connection
    # For now, return success stub
    return TestConnectionResponse(
        success=False,
        error="OpenAI API key not configured",
    )


# =============================================================================
# User Management Endpoints
# =============================================================================


@router.get("/users", response_model=list[OrganizationUser])
async def list_users(
    current_user: RequireAdmin,
    db: DbSession,
) -> list[OrganizationUser]:
    """
    List all users.

    Requires: ADMINISTRATOR role or higher.

    Returns:
        List of users
    """
    user_repo = UserRepository(db)
    users = await user_repo.get_all()

    return [
        OrganizationUser(
            id=str(user.id),
            email=user.email,
            name=user.name or "",
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
        )
        for user in users
    ]


@router.post("/users/create", response_model=CreateUserResponse)
async def create_user(
    user_data: CreateUserRequest,
    current_user: RequireAdmin,
    db: DbSession,
) -> CreateUserResponse:
    """
    Create a new user (pre-staging for SSO).

    Requires: ADMINISTRATOR role or higher.

    Creates a user with no password - they must login via SSO.
    When the user logs in via SSO, the OAuth account will be linked.

    Args:
        user_data: User details (email and role)

    Returns:
        Created user details

    Raises:
        HTTPException: If user already exists or role is invalid
    """
    # Validate the role
    try:
        role = UserRole(user_data.role.lower())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {user_data.role}. Valid roles: {[r.value for r in UserRole]}",
        ) from e

    # Only owners can create owner roles
    if role == UserRole.OWNER and current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can create users with owner role",
        )

    user_repo = UserRepository(db)

    # Check if user already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Create user with no password (SSO-only)
    user = await user_repo.create_user(
        email=user_data.email,
        hashed_password=None,  # No password - SSO only
        name=user_data.email.split('@')[0],  # Default name from email
        role=role,
    )

    await db.commit()

    logger.info(
        f"User created (pre-staged for SSO): {user.email}",
        extra={
            "creator_id": str(current_user.user_id),
            "created_user_id": str(user.id),
            "created_user_email": user.email,
            "role": user.role.value,
        },
    )

    return CreateUserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name or "",
        role=user.role.value,
        is_active=user.is_active,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: UUID,
    current_user: RequireAdmin,
    db: DbSession,
) -> None:
    """
    Remove a user.

    Requires: ADMINISTRATOR role or higher.
    Note: Cannot remove yourself or the last owner.

    Args:
        user_id: User to remove
    """
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent removing the last owner
    if user.role == UserRole.OWNER:
        owner_count = await user_repo.count_owners()
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner",
            )

    await user_repo.delete(user)

    logger.info(
        f"User removed: {user.email}",
        extra={
            "admin_id": str(current_user.user_id),
            "removed_user_id": str(user_id),
        },
    )


@router.patch("/users/{user_id}")
async def update_user_role(
    user_id: UUID,
    role_data: UpdateUserRoleRequest,
    current_user: RequireAdmin,
    db: DbSession,
) -> OrganizationUser:
    """
    Update a user's role.

    Requires: ADMINISTRATOR role or higher.
    Note: Only OWNER can grant/revoke OWNER role.

    Args:
        user_id: User to update
        role_data: New role

    Returns:
        Updated user
    """
    # Validate the new role
    try:
        new_role = UserRole(role_data.role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role_data.role}. Valid roles: {[r.value for r in UserRole]}",
        ) from e

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Only owners can grant/revoke owner role
    is_owner_change = new_role == UserRole.OWNER or user.role == UserRole.OWNER
    if is_owner_change and current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can grant or revoke owner role",
        )

    # Use repository method which has owner protection built-in
    try:
        user = await user_repo.update_role(user_id, new_role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    logger.info(
        f"User role updated: {user.email} -> {role_data.role}",
        extra={
            "admin_id": str(current_user.user_id),
            "user_id": str(user_id),
            "new_role": role_data.role,
        },
    )

    return OrganizationUser(
        id=str(user.id),
        email=user.email,
        name=user.name or "",
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )




@router.post("/transfer-ownership")
async def transfer_ownership(
    transfer_data: TransferOwnershipRequest,
    current_user: RequireOwner,
    db: DbSession,
) -> dict:
    """
    Transfer ownership to another user.

    Requires: OWNER role (only owners can transfer ownership).
    Note: This demotes the current owner to ADMINISTRATOR.

    Args:
        transfer_data: New owner user ID

    Returns:
        Success message
    """
    try:
        new_owner_id = UUID(transfer_data.user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        ) from e

    if new_owner_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already the owner",
        )

    user_repo = UserRepository(db)

    # Get new owner
    new_owner = await user_repo.get_by_id(new_owner_id)
    if not new_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get current owner
    current_owner = await user_repo.get_by_id(current_user.user_id)
    if not current_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current user not found",
        )

    # Transfer ownership: promote new owner, demote current to administrator
    new_owner.role = UserRole.OWNER
    current_owner.role = UserRole.ADMINISTRATOR

    await user_repo.update(new_owner)
    await user_repo.update(current_owner)

    logger.info(
        f"Ownership transferred from {current_owner.email} to {new_owner.email}",
        extra={
            "previous_owner_id": str(current_user.user_id),
            "new_owner_id": str(new_owner_id),
        },
    )

    return {"message": f"Ownership transferred to {new_owner.email}"}


# =============================================================================
# Reindex Endpoints
# =============================================================================


async def _enqueue_reindex(
    entity_type: EntityType | None,
    organization_id: UUID | None,
    job_id: str,
    total: int,
) -> None:
    """
    Enqueue reindex task to the worker.

    The worker handles the entire reindex operation including progress updates.
    """
    from arq import create_pool
    from arq.connections import RedisSettings

    settings = get_settings()

    try:
        redis_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        try:
            await redis_pool.enqueue_job(
                "reindex_task",
                job_id,
                entity_type,
                str(organization_id) if organization_id else None,
                total,
            )
            logger.info(f"Enqueued reindex job {job_id}", extra={"job_id": job_id, "total": total})
        finally:
            await redis_pool.close()

    except Exception as e:
        logger.error(f"Failed to enqueue reindex job: {e}", exc_info=True)

        # Mark job failed
        redis = await _get_redis_client()
        try:
            state_service = ReindexStateService(redis)
            await state_service.fail_job(job_id, str(e))
            await publish_reindex_failed(job_id=job_id, error=str(e))
        finally:
            await redis.aclose()


@router.post("/reindex", response_model=ReindexStartResponse)
async def start_reindex(
    background_tasks: BackgroundTasks,
    current_user: RequireAdmin,
    db: DbSession,
    entity_type: EntityType | None = Query(None, description="Entity type to reindex"),
    organization_id: str | None = Query(None, description="Organization ID to reindex"),
) -> ReindexStartResponse:
    """
    Start a reindex job.

    Requires: ADMINISTRATOR role or higher.

    Triggers reindexing of entities for vector search. The job runs in the
    background and progress can be monitored via GET /reindex/status.

    Args:
        entity_type: Optional entity type to reindex (password, configuration, etc.)
        organization_id: Optional organization ID to reindex

    Returns:
        Job ID and confirmation message
    """
    import uuid

    # Check if a job is already running via Redis
    redis = await _get_redis_client()
    state_service = ReindexStateService(redis)

    try:
        if await state_service.is_job_running():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A reindex job is already running",
            )

        # Parse organization_id if provided
        org_uuid: UUID | None = None
        if organization_id:
            try:
                org_uuid = UUID(organization_id)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid organization_id format",
                ) from e

        # Count total entities to index
        entity_types: list[EntityType] = (
            [entity_type] if entity_type else ["password", "configuration", "location", "document", "custom_asset"]
        )

        total = 0
        for etype in entity_types:
            if etype == "password":
                stmt = select(func.count(Password.id))
                if org_uuid:
                    stmt = stmt.where(Password.organization_id == org_uuid)
            elif etype == "configuration":
                stmt = select(func.count(Configuration.id))
                if org_uuid:
                    stmt = stmt.where(Configuration.organization_id == org_uuid)
            elif etype == "location":
                stmt = select(func.count(Location.id))
                if org_uuid:
                    stmt = stmt.where(Location.organization_id == org_uuid)
            elif etype == "document":
                stmt = select(func.count(Document.id))
                if org_uuid:
                    stmt = stmt.where(Document.organization_id == org_uuid)
            elif etype == "custom_asset":
                stmt = select(func.count(CustomAsset.id))
                if org_uuid:
                    stmt = stmt.where(CustomAsset.organization_id == org_uuid)
            else:
                continue

            result = await db.execute(stmt)
            total += result.scalar() or 0

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Start the job in Redis
        await state_service.start_job(job_id, total)

        # Enqueue to worker (pass total so it doesn't need to recount)
        background_tasks.add_task(_enqueue_reindex, entity_type, org_uuid, job_id, total)

        logger.info(
            "Reindex job started",
            extra={
                "job_id": job_id,
                "entity_type": entity_type,
                "organization_id": organization_id,
                "total_entities": total,
                "user_id": str(current_user.user_id),
            },
        )

        return ReindexStartResponse(
            message=f"Reindex job started with {total} entities",
            job_id=job_id,
        )
    finally:
        await redis.aclose()


@router.get("/reindex/status", response_model=ReindexStatusResponse)
async def get_reindex_status(
    current_user: RequireAdmin,
) -> ReindexStatusResponse:
    """
    Get the status of the current or last reindex job.

    Requires: ADMINISTRATOR role or higher.

    Returns:
        Current job status including progress and any errors
    """
    redis = await _get_redis_client()
    state_service = ReindexStateService(redis)

    try:
        job = await state_service.get_current_job()

        if job is None:
            # No job has been run yet
            return ReindexStatusResponse(
                is_running=False,
                status=None,
                current_entity_type=None,
                processed=0,
                total=0,
                errors=0,
                started_at=None,
                completed_at=None,
                error_message=None,
            )

        # Convert ReindexProgress to ReindexStatusResponse
        return ReindexStatusResponse(
            is_running=job.status in ("running", "cancelling"),
            status=job.status,
            current_entity_type=job.current_entity_type,
            processed=job.processed,
            total=job.total,
            errors=job.errors,
            started_at=datetime.fromtimestamp(job.started_at, tz=UTC).isoformat() if job.started_at else None,
            completed_at=datetime.fromtimestamp(job.completed_at, tz=UTC).isoformat() if job.completed_at else None,
            error_message=job.error_message,
        )
    finally:
        await redis.aclose()


@router.post("/reindex/cancel", response_model=ReindexCancelResponse)
async def cancel_reindex(
    current_user: RequireAdmin,
    force: bool = Query(False, description="Force cancel immediately without waiting for worker"),
) -> ReindexCancelResponse:
    """
    Cancel a running reindex job.

    Requires: ADMINISTRATOR role or higher.

    Args:
        force: If True, immediately clears the job state without waiting for
               the worker to confirm. Use when worker is unresponsive or stuck.
               If False (default), requests graceful cancellation and the worker
               will stop at the next entity boundary.

    Returns:
        Cancellation status
    """
    redis = await _get_redis_client()
    state_service = ReindexStateService(redis)

    try:
        job = await state_service.get_current_job()

        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No reindex job found",
            )

        if job.status not in ("running", "cancelling"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job is not running (status: {job.status})",
            )

        if force:
            # Force cancel - clear state immediately
            success = await state_service.force_cancel(job.job_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to force cancel job",
                )

            # Publish cancelled event directly (worker may not be running)
            await publish_reindex_cancelled(
                job_id=job.job_id,
                processed=job.processed,
                total=job.total,
                force=True,
            )

            logger.info(
                f"Reindex job {job.job_id} force cancelled",
                extra={
                    "job_id": job.job_id,
                    "user_id": str(current_user.user_id),
                    "processed": job.processed,
                    "total": job.total,
                },
            )

            return ReindexCancelResponse(
                message="Reindex job force cancelled",
                status="cancelled",
                processed=job.processed,
                total=job.total,
            )
        else:
            # Graceful cancel - request cancellation, worker will stop at next entity
            success = await state_service.request_cancel(job.job_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Job cannot be cancelled (may already be cancelling or finished)",
                )

            # Publish cancelling event
            await publish_reindex_cancelling(job_id=job.job_id)

            logger.info(
                f"Reindex job {job.job_id} cancellation requested",
                extra={
                    "job_id": job.job_id,
                    "user_id": str(current_user.user_id),
                    "processed": job.processed,
                    "total": job.total,
                },
            )

            return ReindexCancelResponse(
                message="Cancellation requested, waiting for worker to stop",
                status="cancelling",
                processed=job.processed,
                total=job.total,
            )
    finally:
        await redis.aclose()


@router.get("/index/stats", response_model=IndexStatsResponse)
async def get_index_stats(
    current_user: RequireAdmin,
    db: DbSession,
) -> IndexStatsResponse:
    """
    Get statistics about the embedding index.

    Requires: ADMINISTRATOR role or higher.

    Returns:
        Index statistics including total indexed, total entities, and unindexed count
    """
    from src.models.orm.configuration import Configuration
    from src.models.orm.custom_asset import CustomAsset
    from src.models.orm.document import Document
    from src.models.orm.location import Location
    from src.models.orm.password import Password

    # Total indexed
    total_indexed_result = await db.execute(select(func.count(EmbeddingIndex.id)))
    total_indexed = total_indexed_result.scalar() or 0

    # Count total entities across all indexable types
    total_entities = 0
    for model in [Password, Configuration, Location, Document, CustomAsset]:
        count_result = await db.execute(select(func.count(model.id)))
        total_entities += count_result.scalar() or 0

    # Last indexed timestamp
    last_result = await db.execute(
        select(func.max(EmbeddingIndex.updated_at))
    )
    last_indexed = last_result.scalar()

    return IndexStatsResponse(
        total_indexed=total_indexed,
        total_entities=total_entities,
        total_unindexed=total_entities - total_indexed,
        last_indexed_at=last_indexed.isoformat() if last_indexed else None,
    )
