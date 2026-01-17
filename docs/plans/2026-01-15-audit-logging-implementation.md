# Audit Logging & Last Updated By - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `last_updated_by` tracking to 6 core entities and implement a comprehensive audit logging system for compliance, activity feeds, and debugging.

**Architecture:** Two-part implementation: (1) Add `updated_by_user_id` FK column to core entities with ORM relationship to User, (2) Create new `audit_logs` table with service layer for logging actions, API endpoints for querying, and scheduled cleanup job for 1-year retention.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), Alembic migrations, arq worker, PostgreSQL

---

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Database Schema (Migration) | ✅ Complete |
| Phase 2 | ORM Models & Enums | ✅ Complete |
| Phase 3 | Audit Service | ✅ Complete |
| Phase 4 | API Contracts | ✅ Complete |
| Phase 5 | Audit Repository & Router | ✅ Complete |
| Phase 6 | Wire Up Audit Logging | ✅ Complete (7 routers) |
| Phase 7 | Update Entity Response Mapping | ✅ Complete |
| Phase 8 | Cleanup Job | ✅ Complete |
| Phase 9 | Testing | ✅ Unit tests complete |
| Phase 10 | Verification | ⏳ Pending |
| Phase 11 | Frontend UI | ⏳ Not in original plan |

---

## Phase 1: Database Schema (Migration) ✅

### Task 1.1: Create Migration for `updated_by_user_id` Columns

**Files:**
- Create: `api/alembic/versions/20260115_170000_add_updated_by_user_id.py`

**Step 1: Generate migration file**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && alembic revision -m "add_updated_by_user_id"
```

**Step 2: Write migration content**

Edit the generated file to contain:

```python
"""Add updated_by_user_id to core entities

Adds updated_by_user_id column (FK to users) to:
- documents
- passwords
- configurations
- locations
- custom_assets
- organizations

Revision ID: [auto-generated]
Revises: [auto-detected]
Create Date: 2026-01-15
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "[auto-generated]"
down_revision: str | None = "[auto-detected]"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add updated_by_user_id to all 6 core entities
    for table in ["documents", "passwords", "configurations", "locations", "custom_assets", "organizations"]:
        op.add_column(
            table,
            sa.Column(
                "updated_by_user_id",
                sa.UUID(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(
            f"ix_{table}_updated_by_user_id",
            table,
            ["updated_by_user_id"],
        )


def downgrade() -> None:
    for table in ["documents", "passwords", "configurations", "locations", "custom_assets", "organizations"]:
        op.drop_index(f"ix_{table}_updated_by_user_id", table_name=table)
        op.drop_column(table, "updated_by_user_id")
```

**Step 3: Run migration**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && alembic upgrade head
```

Expected: Migration completes successfully

**Step 4: Verify migration**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && alembic current
```

Expected: Shows latest revision

---

### Task 1.2: Create Migration for `audit_logs` Table

**Files:**
- Create: `api/alembic/versions/20260115_171000_create_audit_logs_table.py`

**Step 1: Generate migration file**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && alembic revision -m "create_audit_logs_table"
```

**Step 2: Write migration content**

```python
"""Create audit_logs table

Comprehensive audit logging table for tracking:
- Entity mutations (create, update, delete)
- Password views (sensitive access)
- Auth events (login, logout, failed login)
- User management events

Revision ID: [auto-generated]
Revises: [auto-detected]
Create Date: 2026-01-15
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "[auto-generated]"
down_revision: str | None = "[auto-detected]"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),

        # What happened
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),

        # Who did it
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_api_key_id", sa.UUID(), sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_label", sa.String(100), nullable=True),

        # When
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),

        # Constraint: valid actor based on type
        sa.CheckConstraint(
            "(actor_type = 'user' AND actor_user_id IS NOT NULL) OR "
            "(actor_type = 'api_key' AND actor_api_key_id IS NOT NULL) OR "
            "(actor_type = 'system')",
            name="valid_actor",
        ),
    )

    # Indexes for common query patterns
    op.create_index(
        "ix_audit_logs_org_created",
        "audit_logs",
        ["organization_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )
    op.create_index(
        "ix_audit_logs_system_created",
        "audit_logs",
        [sa.text("created_at DESC")],
        postgresql_where=sa.text("organization_id IS NULL"),
    )
    op.create_index(
        "ix_audit_logs_entity",
        "audit_logs",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_audit_logs_actor_user",
        "audit_logs",
        ["actor_user_id"],
        postgresql_where=sa.text("actor_user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_actor_user", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_system_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_created", table_name="audit_logs")
    op.drop_table("audit_logs")
```

**Step 3: Run migration**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && alembic upgrade head
```

**Step 4: Verify table exists**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && python -c "
from sqlalchemy import inspect
from src.core.database import engine
import asyncio

async def check():
    async with engine.connect() as conn:
        def sync_check(connection):
            inspector = inspect(connection)
            tables = inspector.get_table_names()
            print('audit_logs' in tables)
        await conn.run_sync(sync_check)

asyncio.run(check())
"
```

Expected: `True`

---

## Phase 2: ORM Models & Enums

### Task 2.1: Add Audit Enums

**Files:**
- Modify: `api/src/models/enums.py`

**Step 1: Add enums to enums.py**

Add at the end of the file:

```python
class AuditAction(str, Enum):
    """Actions tracked in audit logs."""

    # Entity mutations
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    # Status changes
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"

    # Sensitive access
    VIEW = "view"

    # Auth events
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    MFA_SETUP = "mfa_setup"
    MFA_VERIFY = "mfa_verify"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"


class ActorType(str, Enum):
    """Types of actors that can perform audited actions."""

    USER = "user"
    API_KEY = "api_key"
    SYSTEM = "system"
```

**Step 2: Verify enums load**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && python -c "from src.models.enums import AuditAction, ActorType; print(AuditAction.CREATE, ActorType.USER)"
```

Expected: `create user`

---

### Task 2.2: Create AuditLog ORM Model

**Files:**
- Create: `api/src/models/orm/audit_log.py`
- Modify: `api/src/models/orm/__init__.py`

**Step 1: Create audit_log.py**

```python
"""
AuditLog ORM model.

Tracks all auditable actions in the Bifrost Docs platform.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.api_key import APIKey
    from src.models.orm.organization import Organization
    from src.models.orm.user import User


class AuditLog(Base):
    """Audit log database table."""

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )

    # What happened
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)

    # Who did it
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_api_key_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # When
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )

    # Relationships (for eager loading display names)
    organization: Mapped["Organization | None"] = relationship()
    actor_user: Mapped["User | None"] = relationship()
    actor_api_key: Mapped["APIKey | None"] = relationship()
```

**Step 2: Add to __init__.py exports**

Add import and export in `api/src/models/orm/__init__.py`:

```python
from src.models.orm.audit_log import AuditLog
```

And add `"AuditLog"` to the `__all__` list.

**Step 3: Verify model loads**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && python -c "from src.models.orm import AuditLog; print(AuditLog.__tablename__)"
```

Expected: `audit_logs`

---

### Task 2.3: Add `updated_by_user_id` to ORM Models

**Files:**
- Modify: `api/src/models/orm/document.py`
- Modify: `api/src/models/orm/password.py`
- Modify: `api/src/models/orm/configuration.py`
- Modify: `api/src/models/orm/location.py`
- Modify: `api/src/models/orm/custom_asset.py`
- Modify: `api/src/models/orm/organization.py`

**Step 1: Update document.py**

Add import at top (in TYPE_CHECKING block):
```python
from src.models.orm.user import User
```

Add column after `updated_at`:
```python
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="documents")
    updated_by_user: Mapped["User | None"] = relationship()
```

**Step 2: Repeat for password.py, configuration.py, location.py, custom_asset.py, organization.py**

Each file needs:
1. Import `User` in TYPE_CHECKING block
2. Add `updated_by_user_id` column
3. Add `updated_by_user` relationship

**Step 3: Verify models load**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && python -c "
from src.models.orm import Document, Password, Configuration, Location, CustomAsset, Organization
for m in [Document, Password, Configuration, Location, CustomAsset, Organization]:
    assert hasattr(m, 'updated_by_user_id'), f'{m.__name__} missing updated_by_user_id'
print('All models have updated_by_user_id')
"
```

Expected: `All models have updated_by_user_id`

---

## Phase 3: Audit Service

### Task 3.1: Create Audit Service

**Files:**
- Create: `api/src/services/audit_service.py`

**Step 1: Create audit_service.py**

```python
"""
Audit Service

Provides centralized audit logging for all trackable actions.
Designed for fire-and-forget logging that doesn't block request handling.
"""

import logging
from uuid import UUID

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
        """
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
```

**Step 2: Verify service loads**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && python -c "from src.services.audit_service import AuditService, get_audit_service; print('OK')"
```

Expected: `OK`

---

## Phase 4: API Contracts

### Task 4.1: Create Audit Contracts

**Files:**
- Create: `api/src/models/contracts/audit.py`

**Step 1: Create audit.py**

```python
"""
Audit log contracts (API request/response schemas).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogEntry(BaseModel):
    """Single audit log entry for API response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None = None
    organization_name: str | None = None
    action: str
    entity_type: str
    entity_id: str
    entity_name: str | None = None  # Resolved from entity if available
    actor_type: str
    actor_user_id: str | None = None
    actor_display_name: str | None = None  # User email/name or API key name
    actor_label: str | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Paginated response for audit log list."""

    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int


class AuditLogFilters(BaseModel):
    """Query filters for audit logs."""

    organization_id: UUID | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    action: str | None = None
    actor_user_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
```

**Step 2: Verify contracts load**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && python -c "from src.models.contracts.audit import AuditLogEntry, AuditLogListResponse; print('OK')"
```

Expected: `OK`

---

### Task 4.2: Update Entity Contracts with `updated_by`

**Files:**
- Modify: `api/src/models/contracts/document.py`
- Modify: `api/src/models/contracts/password.py`
- Modify: `api/src/models/contracts/configuration.py`
- Modify: `api/src/models/contracts/location.py`
- Modify: `api/src/models/contracts/custom_asset.py`
- Modify: `api/src/models/contracts/organization.py`

**Step 1: Update DocumentPublic in document.py**

Add fields after `updated_at`:

```python
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None
```

**Step 2: Repeat for other entity contracts**

Add the same two fields to:
- `PasswordPublic` in password.py
- `ConfigurationPublic` in configuration.py
- `LocationPublic` in location.py
- `CustomAssetPublic` in custom_asset.py
- `OrganizationPublic` in organization.py

---

## Phase 5: Audit Repository & Router

### Task 5.1: Create Audit Repository

**Files:**
- Create: `api/src/repositories/audit.py`

**Step 1: Create audit.py**

```python
"""
Audit Log Repository

Provides database operations for querying audit logs.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.orm.audit_log import AuditLog


class AuditRepository:
    """Repository for AuditLog model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_paginated(
        self,
        *,
        organization_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        action: str | None = None,
        actor_user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
        include_system: bool = True,
    ) -> tuple[list[AuditLog], int]:
        """
        Get paginated audit logs with filters.

        Args:
            organization_id: Filter by organization (None = include all user has access to)
            entity_type: Filter by entity type
            entity_id: Filter by specific entity
            action: Filter by action type
            actor_user_id: Filter by actor user
            start_date: Filter by date range start
            end_date: Filter by date range end
            page: Page number (1-indexed)
            page_size: Items per page
            include_system: Include system-level events (org_id is NULL)

        Returns:
            Tuple of (audit logs, total count)
        """
        filters = []

        if organization_id is not None:
            if include_system:
                filters.append(
                    (AuditLog.organization_id == organization_id) | (AuditLog.organization_id.is_(None))
                )
            else:
                filters.append(AuditLog.organization_id == organization_id)

        if entity_type is not None:
            filters.append(AuditLog.entity_type == entity_type)

        if entity_id is not None:
            filters.append(AuditLog.entity_id == entity_id)

        if action is not None:
            filters.append(AuditLog.action == action)

        if actor_user_id is not None:
            filters.append(AuditLog.actor_user_id == actor_user_id)

        if start_date is not None:
            filters.append(AuditLog.created_at >= start_date)

        if end_date is not None:
            filters.append(AuditLog.created_at <= end_date)

        # Count query
        count_stmt = select(func.count(AuditLog.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query with eager loading
        stmt = (
            select(AuditLog)
            .options(
                joinedload(AuditLog.organization),
                joinedload(AuditLog.actor_user),
                joinedload(AuditLog.actor_api_key),
            )
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if filters:
            stmt = stmt.where(*filters)

        result = await self.session.execute(stmt)
        logs = list(result.scalars().unique().all())

        return logs, total

    async def delete_older_than(self, cutoff: datetime) -> int:
        """
        Delete audit logs older than cutoff date.

        Args:
            cutoff: Delete logs created before this datetime

        Returns:
            Number of deleted rows
        """
        from sqlalchemy import delete

        stmt = delete(AuditLog).where(AuditLog.created_at < cutoff)
        result = await self.session.execute(stmt)
        return result.rowcount
```

**Step 2: Verify repository loads**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && python -c "from src.repositories.audit import AuditRepository; print('OK')"
```

Expected: `OK`

---

### Task 5.2: Create Audit Router

**Files:**
- Create: `api/src/routers/audit.py`
- Modify: `api/src/main.py` (to register router)

**Step 1: Create audit.py router**

```python
"""
Audit Log Router

Provides endpoints for querying audit logs.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query

from src.core.auth import CurrentActiveUser
from src.core.database import DbSession
from src.models.contracts.audit import AuditLogEntry, AuditLogListResponse
from src.repositories.audit import AuditRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: CurrentActiveUser,
    db: DbSession,
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    action: str | None = Query(None, description="Filter by action"),
    actor_user_id: UUID | None = Query(None, description="Filter by actor user"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> AuditLogListResponse:
    """
    List audit logs with filtering and pagination.

    Global view showing all audit logs the user has access to.
    Filter by organization_id to scope to a specific org.
    """
    audit_repo = AuditRepository(db)
    logs, total = await audit_repo.get_paginated(
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_user_id=actor_user_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    items = [
        AuditLogEntry(
            id=str(log.id),
            organization_id=str(log.organization_id) if log.organization_id else None,
            organization_name=log.organization.name if log.organization else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=str(log.entity_id),
            entity_name=None,  # TODO: Resolve entity names in future iteration
            actor_type=log.actor_type,
            actor_user_id=str(log.actor_user_id) if log.actor_user_id else None,
            actor_display_name=(
                log.actor_user.email if log.actor_user
                else log.actor_api_key.name if log.actor_api_key
                else log.actor_label
            ),
            actor_label=log.actor_label,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# Organization-scoped endpoint
org_router = APIRouter(prefix="/api/organizations/{org_id}/audit-logs", tags=["audit"])


@org_router.get("", response_model=AuditLogListResponse)
async def list_org_audit_logs(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    action: str | None = Query(None, description="Filter by action"),
    actor_user_id: UUID | None = Query(None, description="Filter by actor user"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> AuditLogListResponse:
    """
    List audit logs for a specific organization.

    Includes both org-scoped events and system-level events.
    """
    audit_repo = AuditRepository(db)
    logs, total = await audit_repo.get_paginated(
        organization_id=org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_user_id=actor_user_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
        include_system=False,  # Org view doesn't include system events
    )

    items = [
        AuditLogEntry(
            id=str(log.id),
            organization_id=str(log.organization_id) if log.organization_id else None,
            organization_name=log.organization.name if log.organization else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=str(log.entity_id),
            entity_name=None,
            actor_type=log.actor_type,
            actor_user_id=str(log.actor_user_id) if log.actor_user_id else None,
            actor_display_name=(
                log.actor_user.email if log.actor_user
                else log.actor_api_key.name if log.actor_api_key
                else log.actor_label
            ),
            actor_label=log.actor_label,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
```

**Step 2: Register routers in main.py**

Add to the router includes in `api/src/main.py`:

```python
from src.routers.audit import router as audit_router, org_router as audit_org_router

app.include_router(audit_router)
app.include_router(audit_org_router)
```

**Step 3: Verify router loads**

Run:
```bash
cd /Users/jack/GitHub/gocovi-docs/api && python -c "from src.routers.audit import router, org_router; print('OK')"
```

Expected: `OK`

---

## Phase 6: Wire Up Audit Logging

### Task 6.1: Add Audit Logging to Documents Router

**Files:**
- Modify: `api/src/routers/documents.py`

**Step 1: Add imports**

```python
from src.models.enums import AuditAction
from src.services.audit_service import get_audit_service
```

**Step 2: Add to create_document endpoint (after doc is created)**

After `doc = await doc_repo.create(doc)`:

```python
    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.CREATE,
        "document",
        doc.id,
        actor=current_user,
        organization_id=org_id,
    )
```

**Step 3: Add to update_document endpoint**

After `doc = await doc_repo.update(doc)`:

```python
    # Update last_updated_by
    doc.updated_by_user_id = current_user.user_id

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.UPDATE,
        "document",
        doc.id,
        actor=current_user,
        organization_id=org_id,
    )
```

**Step 4: Add to delete_document endpoint**

Before `deleted = await doc_repo.delete_by_id_and_org(doc_id, org_id)`:

```python
    # Audit log (before delete so we have the entity)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.DELETE,
        "document",
        doc_id,
        actor=current_user,
        organization_id=org_id,
    )
```

---

### Task 6.2: Add Audit Logging to Passwords Router

**Files:**
- Modify: `api/src/routers/passwords.py`

**Step 1: Add imports**

```python
from src.models.enums import AuditAction
from src.services.audit_service import get_audit_service
```

**Step 2: Add to reveal_password endpoint (VIEW action)**

After retrieving the password but before returning:

```python
    # Audit log - sensitive access
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.VIEW,
        "password",
        password.id,
        actor=current_user,
        organization_id=org_id,
    )
```

**Step 3: Add CREATE, UPDATE, DELETE audit logging**

Same pattern as documents router.

---

### Task 6.3: Add Audit Logging to Auth Router

**Files:**
- Modify: `api/src/routers/auth.py`

**Step 1: Add imports**

```python
from src.models.enums import AuditAction
from src.services.audit_service import get_audit_service
```

**Step 2: Add to login endpoint (success)**

After `user.last_login = datetime.now(UTC)`:

```python
    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.LOGIN,
        "user",
        user.id,
        actor=UserPrincipal(
            user_id=user.id,
            email=user.email,
            name=user.name or "",
            role=user.role,
        ),
    )
```

**Step 3: Add to login endpoint (failure)**

In the exception handlers for invalid credentials, before raising:

```python
    # Audit failed login (with IP as label)
    if user:
        audit_service = get_audit_service(db)
        await audit_service.log(
            AuditAction.LOGIN_FAILED,
            "user",
            user.id,
            actor_label=request.client.host if request.client else "unknown",
        )
```

**Step 4: Add to logout endpoint**

```python
    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.LOGOUT,
        "user",
        current_user.user_id,
        actor=current_user,
    )
```

---

### Task 6.4: Repeat for Remaining Routers

**Files:**
- Modify: `api/src/routers/configurations.py`
- Modify: `api/src/routers/locations.py`
- Modify: `api/src/routers/custom_assets.py`
- Modify: `api/src/routers/organizations.py`

Apply the same pattern:
1. Add imports for `AuditAction` and `get_audit_service`
2. Add audit logging after create operations
3. Add audit logging and `updated_by_user_id` update after update operations
4. Add audit logging before delete operations

---

## Phase 7: Update Entity Response Mapping

### Task 7.1: Update Documents Router Response Mapping

**Files:**
- Modify: `api/src/routers/documents.py`

**Step 1: Update DocumentPublic creation in all endpoints**

Add to the DocumentPublic constructor:

```python
    updated_by_user_id=str(doc.updated_by_user_id) if doc.updated_by_user_id else None,
    updated_by_user_name=doc.updated_by_user.email if doc.updated_by_user else None,
```

**Step 2: Add eager loading for updated_by_user relationship**

In repository calls or add joinedload option.

---

### Task 7.2: Repeat for Other Entity Routers

Apply same pattern to passwords, configurations, locations, custom_assets, organizations routers.

---

## Phase 8: Cleanup Job

### Task 8.1: Add Audit Cleanup Task to Worker

**Files:**
- Modify: `api/src/worker.py`

**Step 1: Add cleanup task function**

```python
async def cleanup_audit_logs_task(
    _ctx: dict[str, Any],
) -> None:
    """
    Clean up audit logs older than 1 year.

    This task runs daily via cron to maintain audit log retention policy.
    """
    from datetime import timedelta

    from src.core.database import get_db_context
    from src.repositories.audit import AuditRepository

    logger.info("Starting audit log cleanup")

    cutoff = datetime.now(UTC) - timedelta(days=365)

    async with get_db_context() as db:
        audit_repo = AuditRepository(db)
        deleted_count = await audit_repo.delete_older_than(cutoff)
        await db.commit()

    logger.info(f"Audit log cleanup complete: deleted {deleted_count} records older than {cutoff}")
```

**Step 2: Add to WorkerSettings functions**

```python
functions = [index_entity_task, remove_entity_task, reindex_task, cleanup_audit_logs_task]
```

**Step 3: Add cron schedule (optional - can be triggered manually or via external scheduler)**

If using arq cron:
```python
cron_jobs = [
    cron(cleanup_audit_logs_task, hour=3, minute=0),  # Run at 3am daily
]
```

---

## Phase 9: Testing

### Task 9.1: Unit Tests for Audit Service

**Files:**
- Create: `api/tests/unit/test_audit_service.py`

```python
"""Unit tests for AuditService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.models.enums import ActorType, AuditAction
from src.services.audit_service import AuditService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def audit_service(mock_db):
    return AuditService(mock_db)


@pytest.mark.asyncio
async def test_log_user_action(audit_service, mock_db):
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


@pytest.mark.asyncio
async def test_log_api_key_action(audit_service, mock_db):
    """Test logging action via API key."""
    user = MagicMock()
    user.user_id = uuid4()
    user.api_key_id = uuid4()

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


@pytest.mark.asyncio
async def test_log_system_action(audit_service, mock_db):
    """Test logging system action."""
    await audit_service.log(
        AuditAction.DELETE,
        "audit_log",
        uuid4(),
        actor_label="cleanup_job",
    )

    mock_db.add.assert_called_once()
    audit_log = mock_db.add.call_args[0][0]
    assert audit_log.actor_type == ActorType.SYSTEM.value
    assert audit_log.actor_label == "cleanup_job"
```

**Step 2: Run tests**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/test_audit_service.py -v
```

---

### Task 9.2: Integration Tests for Audit Endpoints

**Files:**
- Create: `api/tests/integration/test_audit_endpoints.py`

```python
"""Integration tests for audit log endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_list_audit_logs(client: AsyncClient, auth_headers: dict):
    """Test listing audit logs."""
    response = await client.get(
        "/api/audit-logs",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.integration
async def test_list_org_audit_logs(client: AsyncClient, auth_headers: dict, test_org_id: str):
    """Test listing audit logs for organization."""
    response = await client.get(
        f"/api/organizations/{test_org_id}/audit-logs",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.integration
async def test_audit_log_filters(client: AsyncClient, auth_headers: dict):
    """Test audit log filtering."""
    response = await client.get(
        "/api/audit-logs",
        params={"entity_type": "document", "action": "create"},
        headers=auth_headers,
    )
    assert response.status_code == 200
```

---

## Phase 10: Verification

### Task 10.1: Full System Test

**Step 1: Start the API**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && uvicorn src.main:app --reload
```

**Step 2: Create a document and verify audit log**

```bash
# Create document
curl -X POST http://localhost:8000/api/organizations/{org_id}/documents \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"path": "/test", "name": "Test Doc", "content": "Test"}'

# Check audit logs
curl http://localhost:8000/api/audit-logs \
  -H "Authorization: Bearer {token}"
```

**Step 3: Verify audit log entry exists**

The audit logs response should contain an entry with:
- `action: "create"`
- `entity_type: "document"`
- `actor_type: "user"`

---

## Summary

This implementation plan covers:

1. **Database migrations** for `updated_by_user_id` columns and `audit_logs` table
2. **ORM models** with relationships for eager loading
3. **Audit service** for centralized, fire-and-forget logging
4. **API endpoints** for querying audit logs (global and org-scoped)
5. **Router integration** for all CRUD operations and auth events
6. **Response updates** to include `updated_by` information
7. **Cleanup job** for 1-year retention policy
8. **Tests** for service and endpoints

Total estimated effort: ~6 days
