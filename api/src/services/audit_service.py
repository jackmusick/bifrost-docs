"""
Audit Service

Provides centralized audit logging for all trackable actions.
Designed for fire-and-forget logging that doesn't block request handling.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import UserPrincipal
from src.models.enums import ActorType, AuditAction
from src.models.orm.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for recording audit log entries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID,
        *,
        actor: UserPrincipal | None = None,
        actor_api_key_id: UUID | None = None,
        actor_label: str | None = None,
        organization_id: UUID | None = None,
        dedupe_seconds: int = 0,
    ) -> None:
        """
        Record an audit log entry.

        Args:
            action: The action being performed
            entity_type: Type of entity (document, password, user, etc.)
            entity_id: UUID of the entity being acted upon
            actor: UserPrincipal if action is by a user
            actor_api_key_id: API key ID if action is via API key
            actor_label: Label for system actions (e.g., "cleanup_job")
            organization_id: Organization context (None for auth/system events)
            dedupe_seconds: If > 0, skip logging if same actor/entity/action
                exists within this time window. Useful for VIEW actions to
                avoid spamming logs on page refreshes.
        """
        # Check for recent duplicate if dedupe is enabled
        if dedupe_seconds > 0 and actor is not None:
            cutoff = datetime.now(UTC) - timedelta(seconds=dedupe_seconds)
            stmt = (
                select(AuditLog)
                .where(
                    AuditLog.actor_user_id == actor.user_id,
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id == entity_id,
                    AuditLog.action == action.value,
                    AuditLog.created_at >= cutoff,
                )
                .limit(1)
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is not None:
                logger.debug(
                    f"Audit dedupe: skipping duplicate {action.value} "
                    f"{entity_type}/{entity_id} (within {dedupe_seconds}s)"
                )
                return  # Skip duplicate
        # Determine actor type and IDs
        if actor is not None:
            if actor.api_key_id is not None:
                actor_type = ActorType.API_KEY
                actor_user_id = actor.user_id
                api_key_id = actor.api_key_id
            else:
                actor_type = ActorType.USER
                actor_user_id = actor.user_id
                api_key_id = None
        elif actor_api_key_id is not None:
            actor_type = ActorType.API_KEY
            actor_user_id = None
            api_key_id = actor_api_key_id
        else:
            actor_type = ActorType.SYSTEM
            actor_user_id = None
            api_key_id = None

        audit_log = AuditLog(
            organization_id=organization_id,
            action=action.value,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_type=actor_type.value,
            actor_user_id=actor_user_id,
            actor_api_key_id=api_key_id,
            actor_label=actor_label,
        )

        self.db.add(audit_log)

        # Don't await flush - let it commit with the transaction
        # This ensures audit logs are atomic with the operation

        logger.debug(
            f"Audit: {action.value} {entity_type}/{entity_id}",
            extra={
                "action": action.value,
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "actor_type": actor_type.value,
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
                "organization_id": str(organization_id) if organization_id else None,
            },
        )


def get_audit_service(db: AsyncSession) -> AuditService:
    """Factory function for AuditService."""
    return AuditService(db)
