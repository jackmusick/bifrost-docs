"""
API Keys Router

Provides endpoints for user API key management.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.core.auth import CurrentActiveUser
from src.core.database import DbSession
from src.core.security import generate_api_key, hash_api_key
from src.models.contracts.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyPublic
from src.models.orm.api_key import APIKey
from src.repositories.api_key import ApiKeyRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyPublic])
async def list_api_keys(
    current_user: CurrentActiveUser,
    db: DbSession,
) -> list[ApiKeyPublic]:
    """
    List all API keys for the current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of user's API keys (without key values)
    """
    api_key_repo = ApiKeyRepository(db)
    api_keys = await api_key_repo.get_by_user(current_user.user_id)

    return [
        ApiKeyPublic(
            id=str(key.id),
            user_id=str(key.user_id),
            name=key.name,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
            created_at=key.created_at,
        )
        for key in api_keys
    ]


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: ApiKeyCreate,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> ApiKeyCreated:
    """
    Create a new API key.

    The full API key is returned ONLY in this response. Store it securely
    as it cannot be retrieved again.

    Args:
        api_key_data: API key creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created API key with the full key value
    """
    # Generate the API key and hash it
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    api_key_repo = ApiKeyRepository(db)
    api_key = APIKey(
        user_id=current_user.user_id,
        name=api_key_data.name,
        key_hash=key_hash,
        expires_at=api_key_data.expires_at,
    )
    api_key = await api_key_repo.create(api_key)

    logger.info(
        f"API key created: {api_key.name}",
        extra={
            "api_key_id": str(api_key.id),
            "user_id": str(current_user.user_id),
        },
    )

    return ApiKeyCreated(
        id=str(api_key.id),
        user_id=str(api_key.user_id),
        name=api_key.name,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        key=raw_key,  # Return the full key only on creation
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> None:
    """
    Delete/revoke an API key.

    Args:
        key_id: API key UUID to delete
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If API key not found or doesn't belong to user
    """
    api_key_repo = ApiKeyRepository(db)
    api_key = await api_key_repo.get_by_id_and_user(key_id, current_user.user_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await api_key_repo.delete(api_key)

    logger.info(
        f"API key deleted: {api_key.name}",
        extra={
            "api_key_id": str(api_key.id),
            "user_id": str(current_user.user_id),
        },
    )
