"""
User Preferences Router

Provides endpoints for storing and retrieving user UI preferences.
Preferences are per-user and per-entity-type (e.g., passwords, configurations).
"""

import logging

from fastapi import APIRouter, HTTPException, status

from src.core.auth import CurrentActiveUser
from src.core.database import DbSession
from src.models.contracts.user_preferences import (
    PreferencesData,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from src.repositories.user_preferences import UserPreferencesRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


@router.get("/{entity_type}", response_model=UserPreferencesResponse)
async def get_preferences(
    entity_type: str,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> UserPreferencesResponse:
    """
    Get user preferences for an entity type.

    Returns preferences if found, or empty defaults if no preferences exist.
    This allows the frontend to always receive a valid response structure.

    Args:
        entity_type: Entity type identifier (e.g., "passwords", "configurations",
                     "custom_asset_{uuid}")

    Returns:
        User preferences for the entity type (or defaults)
    """
    # Validate entity_type length
    if len(entity_type) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entity type must be 100 characters or less",
        )

    repo = UserPreferencesRepository(db)
    prefs = await repo.get_by_user_and_entity(
        user_id=current_user.user_id,
        entity_type=entity_type,
    )

    if prefs:
        # Parse stored preferences into structured response
        return UserPreferencesResponse(
            entity_type=entity_type,
            preferences=PreferencesData.model_validate(prefs.preferences),
        )

    # Return empty defaults
    return UserPreferencesResponse(
        entity_type=entity_type,
        preferences=PreferencesData(),
    )


@router.put("/{entity_type}", response_model=UserPreferencesResponse)
async def upsert_preferences(
    entity_type: str,
    update_data: UserPreferencesUpdate,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> UserPreferencesResponse:
    """
    Create or update user preferences for an entity type.

    Uses upsert semantics - creates if not exists, updates if exists.

    Args:
        entity_type: Entity type identifier
        update_data: New preferences data

    Returns:
        Updated user preferences
    """
    # Validate entity_type length
    if len(entity_type) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entity type must be 100 characters or less",
        )

    repo = UserPreferencesRepository(db)
    prefs = await repo.upsert(
        user_id=current_user.user_id,
        entity_type=entity_type,
        preferences=update_data.preferences.model_dump(),
    )

    logger.info(
        "User preferences updated",
        extra={
            "user_id": str(current_user.user_id),
            "entity_type": entity_type,
        },
    )

    return UserPreferencesResponse(
        entity_type=entity_type,
        preferences=PreferencesData.model_validate(prefs.preferences),
    )


@router.delete("/{entity_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preferences(
    entity_type: str,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> None:
    """
    Delete user preferences for an entity type.

    Resets preferences to defaults by removing the stored record.

    Args:
        entity_type: Entity type identifier
    """
    # Validate entity_type length
    if len(entity_type) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entity type must be 100 characters or less",
        )

    repo = UserPreferencesRepository(db)
    deleted = await repo.delete_by_user_and_entity(
        user_id=current_user.user_id,
        entity_type=entity_type,
    )

    if deleted:
        logger.info(
            "User preferences deleted",
            extra={
                "user_id": str(current_user.user_id),
                "entity_type": entity_type,
            },
        )
