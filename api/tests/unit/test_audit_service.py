"""Unit tests for AuditService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.enums import ActorType, AuditAction
from src.services.audit_service import AuditService


@pytest.fixture
def mock_db():
    """Create mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def audit_service(mock_db):
    """Create AuditService with mocked database."""
    return AuditService(mock_db)


class TestAuditService:
    """Tests for AuditService.log() method."""

    @pytest.mark.asyncio
    async def test_log_user_action(self, audit_service, mock_db):
        """Test logging action by authenticated user."""
        user = MagicMock()
        user.user_id = uuid4()
        user.api_key_id = None

        await audit_service.log(
            AuditAction.CREATE,
            "document",
            uuid4(),
            actor=user,
            organization_id=uuid4(),
        )

        mock_db.add.assert_called_once()
        audit_log = mock_db.add.call_args[0][0]
        assert audit_log.actor_type == ActorType.USER.value
        assert audit_log.actor_user_id == user.user_id
        assert audit_log.actor_api_key_id is None

    @pytest.mark.asyncio
    async def test_log_api_key_action_via_principal(self, audit_service, mock_db):
        """Test logging action via API key through UserPrincipal."""
        user = MagicMock()
        user.user_id = uuid4()
        user.api_key_id = uuid4()  # Has API key ID

        await audit_service.log(
            AuditAction.VIEW,
            "password",
            uuid4(),
            actor=user,
            organization_id=uuid4(),
        )

        mock_db.add.assert_called_once()
        audit_log = mock_db.add.call_args[0][0]
        assert audit_log.actor_type == ActorType.API_KEY.value
        assert audit_log.actor_user_id == user.user_id
        assert audit_log.actor_api_key_id == user.api_key_id

    @pytest.mark.asyncio
    async def test_log_api_key_action_direct(self, audit_service, mock_db):
        """Test logging action via direct API key ID."""
        api_key_id = uuid4()

        await audit_service.log(
            AuditAction.UPDATE,
            "configuration",
            uuid4(),
            actor_api_key_id=api_key_id,
            organization_id=uuid4(),
        )

        mock_db.add.assert_called_once()
        audit_log = mock_db.add.call_args[0][0]
        assert audit_log.actor_type == ActorType.API_KEY.value
        assert audit_log.actor_user_id is None
        assert audit_log.actor_api_key_id == api_key_id

    @pytest.mark.asyncio
    async def test_log_system_action(self, audit_service, mock_db):
        """Test logging system action with actor label."""
        entity_id = uuid4()

        await audit_service.log(
            AuditAction.DELETE,
            "audit_log",
            entity_id,
            actor_label="cleanup_job",
        )

        mock_db.add.assert_called_once()
        audit_log = mock_db.add.call_args[0][0]
        assert audit_log.actor_type == ActorType.SYSTEM.value
        assert audit_log.actor_user_id is None
        assert audit_log.actor_api_key_id is None
        assert audit_log.actor_label == "cleanup_job"

    @pytest.mark.asyncio
    async def test_log_with_organization_id(self, audit_service, mock_db):
        """Test logging action with organization context."""
        user = MagicMock()
        user.user_id = uuid4()
        user.api_key_id = None
        org_id = uuid4()
        entity_id = uuid4()

        await audit_service.log(
            AuditAction.CREATE,
            "document",
            entity_id,
            actor=user,
            organization_id=org_id,
        )

        mock_db.add.assert_called_once()
        audit_log = mock_db.add.call_args[0][0]
        assert audit_log.organization_id == org_id
        assert audit_log.entity_id == entity_id

    @pytest.mark.asyncio
    async def test_log_without_organization_id(self, audit_service, mock_db):
        """Test logging auth event without organization context."""
        user = MagicMock()
        user.user_id = uuid4()
        user.api_key_id = None

        await audit_service.log(
            AuditAction.LOGIN,
            "user",
            user.user_id,
            actor=user,
            # No organization_id - auth events are system-wide
        )

        mock_db.add.assert_called_once()
        audit_log = mock_db.add.call_args[0][0]
        assert audit_log.organization_id is None

    @pytest.mark.asyncio
    async def test_log_stores_action_value(self, audit_service, mock_db):
        """Test that action enum value is stored correctly."""
        user = MagicMock()
        user.user_id = uuid4()
        user.api_key_id = None

        await audit_service.log(
            AuditAction.LOGIN_FAILED,
            "user",
            user.user_id,
            actor_label="192.168.1.1",
        )

        mock_db.add.assert_called_once()
        audit_log = mock_db.add.call_args[0][0]
        assert audit_log.action == "login_failed"
