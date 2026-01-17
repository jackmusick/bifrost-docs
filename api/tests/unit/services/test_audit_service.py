"""Tests for audit service with dedupe support."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.models.enums import AuditAction
from src.services.audit_service import AuditService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.add = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def audit_service(mock_db):
    """Create audit service with mock db."""
    return AuditService(mock_db)


@pytest.fixture
def mock_actor():
    """Create a mock UserPrincipal."""
    actor = MagicMock()
    actor.user_id = uuid4()
    actor.api_key_id = None
    return actor


@pytest.mark.unit
@pytest.mark.asyncio
class TestAuditServiceDedupe:
    """Tests for audit service dedupe functionality."""

    async def test_log_with_dedupe_skips_duplicate(
        self, audit_service, mock_db, mock_actor
    ):
        """Should skip logging if same entity was viewed within dedupe window."""
        entity_id = uuid4()
        org_id = uuid4()

        # Mock finding a recent view
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # Found recent view
        mock_db.execute.return_value = mock_result

        await audit_service.log(
            AuditAction.VIEW,
            "password",
            entity_id,
            actor=mock_actor,
            organization_id=org_id,
            dedupe_seconds=60,
        )

        # Should NOT add a new log entry
        mock_db.add.assert_not_called()

    async def test_log_with_dedupe_logs_when_no_recent(
        self, audit_service, mock_db, mock_actor
    ):
        """Should log if no recent view found within dedupe window."""
        entity_id = uuid4()
        org_id = uuid4()

        # Mock no recent view found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        await audit_service.log(
            AuditAction.VIEW,
            "password",
            entity_id,
            actor=mock_actor,
            organization_id=org_id,
            dedupe_seconds=60,
        )

        # Should add a new log entry
        mock_db.add.assert_called_once()

    async def test_log_without_dedupe_always_logs(
        self, audit_service, mock_db, mock_actor
    ):
        """Should always log when dedupe_seconds is 0 (default)."""
        entity_id = uuid4()
        org_id = uuid4()

        await audit_service.log(
            AuditAction.VIEW,
            "password",
            entity_id,
            actor=mock_actor,
            organization_id=org_id,
        )

        # Should add without checking for duplicates
        mock_db.add.assert_called_once()
        # execute should NOT be called (no dedupe check)
        mock_db.execute.assert_not_called()

    async def test_log_with_dedupe_but_no_actor_always_logs(
        self, audit_service, mock_db
    ):
        """Should always log when dedupe is enabled but no actor provided."""
        entity_id = uuid4()
        org_id = uuid4()

        await audit_service.log(
            AuditAction.VIEW,
            "password",
            entity_id,
            organization_id=org_id,
            dedupe_seconds=60,
        )

        # Should add without checking for duplicates (can't dedupe without actor)
        mock_db.add.assert_called_once()
        mock_db.execute.assert_not_called()
