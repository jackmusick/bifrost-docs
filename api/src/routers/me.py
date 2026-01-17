"""
User-specific endpoints.

Provides endpoints for the current user's data such as recently accessed entities.
"""

from fastapi import APIRouter, Query

from src.core.auth import CurrentActiveUser
from src.core.database import DbSession
from src.models.contracts.access_tracking import RecentItem
from src.repositories.access_tracking import AccessTrackingRepository

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("/recent", response_model=list[RecentItem])
async def get_recent(
    current_user: CurrentActiveUser,
    db: DbSession,
    limit: int = Query(10, ge=1, le=50, description="Number of items to return"),
) -> list[RecentItem]:
    """
    Get the current user's recently accessed entities.

    Returns the most recent view per unique entity, ordered by viewed_at descending.
    """
    repo = AccessTrackingRepository(db)
    return await repo.get_recent_for_user(current_user.user_id, limit=limit)
