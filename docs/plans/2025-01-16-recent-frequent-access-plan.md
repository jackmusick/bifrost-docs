# Recently Accessed & Frequently Accessed Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add recently accessed (per-user) and frequently accessed (per-org) tracking to improve navigation across the platform.

**Architecture:** Leverage existing audit_log table with VIEW action. Add dedupe logic to audit service. Create new repository for access tracking queries. Extend organizations endpoint with optional include param.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), React 19, TanStack Query, shadcn/ui, Tailwind CSS

---

## Task 1: Add Dedupe Support to Audit Service

**Files:**
- Modify: `api/src/services/audit_service.py`
- Test: `api/tests/unit/services/test_audit_service.py`

**Step 1: Write the failing test**

```python
# api/tests/unit/services/test_audit_service.py

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.models.enums import AuditAction
from src.services.audit_service import AuditService


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def audit_service(mock_db):
    return AuditService(mock_db)


@pytest.fixture
def mock_actor():
    actor = MagicMock()
    actor.user_id = uuid4()
    return actor


@pytest.mark.asyncio
async def test_log_with_dedupe_skips_duplicate(audit_service, mock_db, mock_actor):
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


@pytest.mark.asyncio
async def test_log_with_dedupe_logs_when_no_recent(audit_service, mock_db, mock_actor):
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


@pytest.mark.asyncio
async def test_log_without_dedupe_always_logs(audit_service, mock_db, mock_actor):
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
```

**Step 2: Run test to verify it fails**

```bash
pytest api/tests/unit/services/test_audit_service.py -v
```

Expected: FAIL - `dedupe_seconds` parameter doesn't exist

**Step 3: Implement dedupe logic in audit service**

```python
# api/src/services/audit_service.py
# Add these imports at top
from datetime import datetime, timedelta
from sqlalchemy import select

# Modify the log method signature and implementation
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
        dedupe_seconds: If > 0, skip logging if same user+entity was logged
                       within this many seconds. Only applies when actor is set.
    """
    # Check for recent duplicate if dedupe is enabled
    if dedupe_seconds > 0 and actor is not None:
        cutoff = datetime.utcnow() - timedelta(seconds=dedupe_seconds)
        stmt = select(AuditLog).where(
            AuditLog.actor_user_id == actor.user_id,
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
            AuditLog.action == action.value,
            AuditLog.created_at >= cutoff,
        ).limit(1)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            return  # Skip duplicate

    # Existing log creation logic (unchanged)
    # ... rest of existing code
```

**Step 4: Run test to verify it passes**

```bash
pytest api/tests/unit/services/test_audit_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add api/src/services/audit_service.py api/tests/unit/services/test_audit_service.py
git commit -m "feat(audit): add dedupe support to audit service

Add dedupe_seconds parameter to skip duplicate VIEW logs within a time window.
This prevents audit log spam when users refresh pages repeatedly."
```

---

## Task 2: Add VIEW Logging to Password GET Endpoint

**Files:**
- Modify: `api/src/routers/passwords.py`
- Test: `api/tests/integration/test_passwords.py` (if exists, or create)

**Step 1: Locate the get_password endpoint**

Find the `GET /{password_id}` endpoint in `api/src/routers/passwords.py`. It should be around line 270-310.

**Step 2: Add VIEW logging after fetching the password**

```python
# In the get_password function, after fetching the password and before returning:

# Log view (with 60-second dedupe)
audit_service = get_audit_service(db)
await audit_service.log(
    AuditAction.VIEW,
    "password",
    password.id,
    actor=current_user,
    organization_id=org_id,
    dedupe_seconds=60,
)
```

**Step 3: Run existing tests to ensure no regression**

```bash
pytest api/tests/ -k password -v
```

Expected: All existing tests pass

**Step 4: Commit**

```bash
git add api/src/routers/passwords.py
git commit -m "feat(audit): add VIEW logging to password GET endpoint

Log view action when fetching password details with 60s dedupe."
```

---

## Task 3: Add VIEW Logging to Remaining Entity Endpoints

**Files:**
- Modify: `api/src/routers/configurations.py`
- Modify: `api/src/routers/locations.py`
- Modify: `api/src/routers/documents.py`
- Modify: `api/src/routers/custom_assets.py`
- Modify: `api/src/routers/organizations.py`

**Step 1: Add VIEW logging to configurations GET endpoint**

Locate `GET /{configuration_id}` in `api/src/routers/configurations.py` and add:

```python
# After fetching configuration, before return
audit_service = get_audit_service(db)
await audit_service.log(
    AuditAction.VIEW,
    "configuration",
    configuration.id,
    actor=current_user,
    organization_id=org_id,
    dedupe_seconds=60,
)
```

**Step 2: Add VIEW logging to locations GET endpoint**

Locate `GET /{location_id}` in `api/src/routers/locations.py` and add:

```python
audit_service = get_audit_service(db)
await audit_service.log(
    AuditAction.VIEW,
    "location",
    location.id,
    actor=current_user,
    organization_id=org_id,
    dedupe_seconds=60,
)
```

**Step 3: Add VIEW logging to documents GET endpoint**

Locate `GET /{document_id}` in `api/src/routers/documents.py` and add:

```python
audit_service = get_audit_service(db)
await audit_service.log(
    AuditAction.VIEW,
    "document",
    document.id,
    actor=current_user,
    organization_id=org_id,
    dedupe_seconds=60,
)
```

**Step 4: Add VIEW logging to custom_assets GET endpoint**

Locate `GET /{asset_id}` in `api/src/routers/custom_assets.py` and add:

```python
audit_service = get_audit_service(db)
await audit_service.log(
    AuditAction.VIEW,
    "custom_asset",
    asset.id,
    actor=current_user,
    organization_id=org_id,
    dedupe_seconds=60,
)
```

**Step 5: Add VIEW logging to organizations GET endpoint**

Locate `GET /{org_id}` in `api/src/routers/organizations.py` and add:

```python
audit_service = get_audit_service(db)
await audit_service.log(
    AuditAction.VIEW,
    "organization",
    org.id,
    actor=current_user,
    organization_id=org.id,
    dedupe_seconds=60,
)
```

**Step 6: Run all tests**

```bash
pytest api/tests/ -v
```

Expected: All tests pass

**Step 7: Commit**

```bash
git add api/src/routers/configurations.py api/src/routers/locations.py api/src/routers/documents.py api/src/routers/custom_assets.py api/src/routers/organizations.py
git commit -m "feat(audit): add VIEW logging to all entity GET endpoints

Track view actions for configurations, locations, documents, custom_assets,
and organizations with 60s dedupe to prevent spam."
```

---

## Task 4: Create Access Tracking Repository

**Files:**
- Create: `api/src/repositories/access_tracking.py`
- Create: `api/src/models/contracts/access_tracking.py`
- Test: `api/tests/unit/repositories/test_access_tracking.py`

**Step 1: Create the contract models**

```python
# api/src/models/contracts/access_tracking.py

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RecentItem(BaseModel):
    """A recently accessed entity."""

    entity_type: str
    entity_id: UUID
    organization_id: UUID | None
    org_name: str | None
    name: str
    viewed_at: datetime


class FrequentItem(BaseModel):
    """A frequently accessed entity within an organization."""

    entity_type: str
    entity_id: UUID
    name: str
    view_count: int
```

**Step 2: Write failing test for get_recent_for_user**

```python
# api/tests/unit/repositories/test_access_tracking.py

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.repositories.access_tracking import AccessTrackingRepository


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def repo(mock_db):
    return AccessTrackingRepository(mock_db)


@pytest.mark.asyncio
async def test_get_recent_for_user_returns_recent_items(repo, mock_db):
    """Should return recently viewed entities for a user."""
    user_id = uuid4()

    # Mock the query result
    mock_row = MagicMock()
    mock_row.entity_type = "password"
    mock_row.entity_id = uuid4()
    mock_row.organization_id = uuid4()
    mock_row.org_name = "Acme Corp"
    mock_row.name = "Admin Password"
    mock_row.viewed_at = datetime.utcnow()

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_result

    items = await repo.get_recent_for_user(user_id, limit=10)

    assert len(items) == 1
    assert items[0].entity_type == "password"
    assert items[0].name == "Admin Password"
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_recent_for_user_respects_limit(repo, mock_db):
    """Should respect the limit parameter."""
    user_id = uuid4()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute.return_value = mock_result

    await repo.get_recent_for_user(user_id, limit=5)

    # Verify limit is in the query (check the call args)
    call_args = mock_db.execute.call_args
    assert call_args is not None
```

**Step 3: Run test to verify it fails**

```bash
pytest api/tests/unit/repositories/test_access_tracking.py -v
```

Expected: FAIL - module not found

**Step 4: Implement AccessTrackingRepository**

```python
# api/src/repositories/access_tracking.py

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, func, desc, and_, case, literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.models.orm.audit_log import AuditLog
from src.models.orm.organization import Organization
from src.models.orm.password import Password
from src.models.orm.configuration import Configuration
from src.models.orm.location import Location
from src.models.orm.document import Document
from src.models.orm.custom_asset import CustomAsset
from src.models.contracts.access_tracking import RecentItem, FrequentItem


class AccessTrackingRepository:
    """Repository for querying recent and frequently accessed entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_recent_for_user(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[RecentItem]:
        """
        Get user's recently viewed entities.

        Returns the most recent view per unique (entity_type, entity_id),
        ordered by viewed_at descending.
        """
        # Subquery to get latest view per entity
        latest_views = (
            select(
                AuditLog.entity_type,
                AuditLog.entity_id,
                AuditLog.organization_id,
                func.max(AuditLog.created_at).label("viewed_at"),
            )
            .where(
                AuditLog.actor_user_id == user_id,
                AuditLog.action == "view",
            )
            .group_by(
                AuditLog.entity_type,
                AuditLog.entity_id,
                AuditLog.organization_id,
            )
            .subquery()
        )

        # Main query joining to entity tables for names
        # Using UNION ALL for each entity type
        results = []

        # Query for each entity type and collect results
        entity_configs = [
            ("password", Password),
            ("configuration", Configuration),
            ("location", Location),
            ("document", Document),
            ("custom_asset", CustomAsset),
            ("organization", Organization),
        ]

        for entity_type, model in entity_configs:
            if entity_type == "organization":
                stmt = (
                    select(
                        literal(entity_type).label("entity_type"),
                        model.id.label("entity_id"),
                        model.id.label("organization_id"),
                        model.name.label("org_name"),
                        model.name.label("name"),
                        latest_views.c.viewed_at,
                    )
                    .join(
                        latest_views,
                        and_(
                            latest_views.c.entity_type == entity_type,
                            latest_views.c.entity_id == model.id,
                        ),
                    )
                )
            else:
                org_alias = aliased(Organization)
                stmt = (
                    select(
                        literal(entity_type).label("entity_type"),
                        model.id.label("entity_id"),
                        model.organization_id.label("organization_id"),
                        org_alias.name.label("org_name"),
                        model.name.label("name"),
                        latest_views.c.viewed_at,
                    )
                    .join(
                        latest_views,
                        and_(
                            latest_views.c.entity_type == entity_type,
                            latest_views.c.entity_id == model.id,
                        ),
                    )
                    .join(org_alias, model.organization_id == org_alias.id)
                )

            result = await self.db.execute(stmt)
            results.extend(result.all())

        # Sort by viewed_at and limit
        results.sort(key=lambda x: x.viewed_at, reverse=True)
        results = results[:limit]

        return [
            RecentItem(
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                organization_id=row.organization_id,
                org_name=row.org_name,
                name=row.name,
                viewed_at=row.viewed_at,
            )
            for row in results
        ]

    async def get_frequently_accessed(
        self,
        org_id: UUID,
        limit: int = 6,
        days: int = 30,
    ) -> list[FrequentItem]:
        """
        Get most frequently accessed entities in an organization.

        Counts views over the specified time period, grouped by entity.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Subquery for view counts per entity
        view_counts = (
            select(
                AuditLog.entity_type,
                AuditLog.entity_id,
                func.count().label("view_count"),
            )
            .where(
                AuditLog.organization_id == org_id,
                AuditLog.action == "view",
                AuditLog.created_at >= cutoff,
            )
            .group_by(AuditLog.entity_type, AuditLog.entity_id)
            .subquery()
        )

        results = []

        entity_configs = [
            ("password", Password),
            ("configuration", Configuration),
            ("location", Location),
            ("document", Document),
            ("custom_asset", CustomAsset),
        ]

        for entity_type, model in entity_configs:
            stmt = (
                select(
                    literal(entity_type).label("entity_type"),
                    model.id.label("entity_id"),
                    model.name.label("name"),
                    view_counts.c.view_count,
                )
                .join(
                    view_counts,
                    and_(
                        view_counts.c.entity_type == entity_type,
                        view_counts.c.entity_id == model.id,
                    ),
                )
                .where(model.organization_id == org_id)
            )

            result = await self.db.execute(stmt)
            results.extend(result.all())

        # Sort by view_count descending and limit
        results.sort(key=lambda x: x.view_count, reverse=True)
        results = results[:limit]

        return [
            FrequentItem(
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                name=row.name,
                view_count=row.view_count,
            )
            for row in results
        ]
```

**Step 5: Run tests**

```bash
pytest api/tests/unit/repositories/test_access_tracking.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add api/src/repositories/access_tracking.py api/src/models/contracts/access_tracking.py api/tests/unit/repositories/test_access_tracking.py
git commit -m "feat(access): create AccessTrackingRepository

Add repository for querying recently accessed (per-user) and
frequently accessed (per-org) entities from audit logs."
```

---

## Task 5: Create GET /api/me/recent Endpoint

**Files:**
- Create: `api/src/routers/me.py`
- Modify: `api/src/main.py` (to include router)
- Test: `api/tests/integration/test_me.py`

**Step 1: Write failing integration test**

```python
# api/tests/integration/test_me.py

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_recent_returns_list(client: AsyncClient, auth_headers: dict):
    """Should return a list of recently accessed items."""
    response = await client.get("/api/me/recent", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_recent_respects_limit(client: AsyncClient, auth_headers: dict):
    """Should respect the limit query parameter."""
    response = await client.get("/api/me/recent?limit=5", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
```

**Step 2: Run test to verify it fails**

```bash
pytest api/tests/integration/test_me.py -v
```

Expected: FAIL - 404 Not Found

**Step 3: Create the me router**

```python
# api/src/routers/me.py

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import CurrentActiveUser, DbSession
from src.models.contracts.access_tracking import RecentItem
from src.repositories.access_tracking import AccessTrackingRepository

router = APIRouter(prefix="/me", tags=["me"])


def get_access_tracking_repo(db: AsyncSession) -> AccessTrackingRepository:
    return AccessTrackingRepository(db)


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
    repo = get_access_tracking_repo(db)
    return await repo.get_recent_for_user(current_user.user_id, limit=limit)
```

**Step 4: Register the router in main.py**

```python
# In api/src/main.py, add import and include_router

from src.routers import me

# In the router registration section:
app.include_router(me.router, prefix="/api")
```

**Step 5: Run tests**

```bash
pytest api/tests/integration/test_me.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add api/src/routers/me.py api/src/main.py api/tests/integration/test_me.py
git commit -m "feat(api): add GET /api/me/recent endpoint

Returns user's recently accessed entities from audit log views."
```

---

## Task 6: Add frequently_accessed Include to Organizations Endpoint

**Files:**
- Modify: `api/src/routers/organizations.py`
- Modify: `api/src/models/contracts/organization.py` (response model)
- Test: `api/tests/integration/test_organizations.py`

**Step 1: Update the response model**

```python
# In api/src/models/contracts/organization.py
# Add new response model that includes frequently_accessed

from src.models.contracts.access_tracking import FrequentItem

class OrganizationWithFrequent(OrganizationPublic):
    """Organization with optional frequently accessed entities."""
    frequently_accessed: list[FrequentItem] | None = None
```

**Step 2: Modify the GET endpoint**

```python
# In api/src/routers/organizations.py

from src.models.contracts.access_tracking import FrequentItem
from src.models.contracts.organization import OrganizationWithFrequent
from src.repositories.access_tracking import AccessTrackingRepository

@router.get("/{org_id}", response_model=OrganizationWithFrequent)
async def get_organization(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    include: list[str] = Query(default=[], description="Include additional data: frequently_accessed"),
) -> OrganizationWithFrequent:
    """Get an organization by ID."""
    repo = get_organization_repo(db)
    org = await repo.get(org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Log view
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.VIEW,
        "organization",
        org.id,
        actor=current_user,
        organization_id=org.id,
        dedupe_seconds=60,
    )

    # Build response
    response = OrganizationWithFrequent(
        id=org.id,
        name=org.name,
        is_enabled=org.is_enabled,
        created_at=org.created_at,
        updated_at=org.updated_at,
        frequently_accessed=None,
    )

    # Include frequently accessed if requested
    if "frequently_accessed" in include:
        access_repo = AccessTrackingRepository(db)
        response.frequently_accessed = await access_repo.get_frequently_accessed(
            org_id, limit=6, days=30
        )

    return response
```

**Step 3: Run tests**

```bash
pytest api/tests/ -k organization -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add api/src/routers/organizations.py api/src/models/contracts/organization.py
git commit -m "feat(api): add frequently_accessed include to org endpoint

GET /api/organizations/{id}?include=frequently_accessed now returns
the most viewed entities in that org over the last 30 days."
```

---

## Task 7: Add Database Index for Efficient Queries

**Files:**
- Create: `api/alembic/versions/xxx_add_audit_log_view_index.py`

**Step 1: Generate migration**

```bash
cd api && alembic revision -m "add_audit_log_view_index"
```

**Step 2: Edit the migration file**

```python
# api/alembic/versions/xxx_add_audit_log_view_index.py

"""add_audit_log_view_index

Revision ID: xxx
Revises: yyy
Create Date: 2025-01-16
"""
from alembic import op

revision = "xxx"
down_revision = "yyy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_audit_log_user_views
        ON audit_log (actor_user_id, action, created_at DESC)
        WHERE action = 'view'
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_log_user_views")
```

**Step 3: Run migration**

```bash
cd api && alembic upgrade head
```

**Step 4: Commit**

```bash
git add api/alembic/versions/
git commit -m "feat(db): add index for audit log view queries

Partial index on (actor_user_id, action, created_at) for view actions
to speed up recent/frequent access queries."
```

---

## Task 8: Create useRecentlyAccessed Hook

**Files:**
- Create: `client/src/hooks/useRecentlyAccessed.ts`

**Step 1: Create the hook**

```typescript
// client/src/hooks/useRecentlyAccessed.ts

import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";

export interface RecentItem {
  entity_type: string;
  entity_id: string;
  organization_id: string | null;
  org_name: string | null;
  name: string;
  viewed_at: string;
}

export function useRecentlyAccessed(limit = 10) {
  return useQuery({
    queryKey: ["recent", limit],
    queryFn: async () => {
      const response = await api.get<RecentItem[]>(`/api/me/recent`, {
        params: { limit },
      });
      return response.data;
    },
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to invalidate the recent list.
 * Call this after navigating to an entity detail page.
 */
export function useInvalidateRecent() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: ["recent"] });
  };
}
```

**Step 2: Run type check**

```bash
cd client && npm run tsc
```

Expected: No errors

**Step 3: Commit**

```bash
git add client/src/hooks/useRecentlyAccessed.ts
git commit -m "feat(client): add useRecentlyAccessed hook

Query hook for fetching user's recently accessed entities."
```

---

## Task 9: Update Organization Hook to Support Include Param

**Files:**
- Modify: `client/src/hooks/useOrganizations.ts`

**Step 1: Update the hook**

```typescript
// In client/src/hooks/useOrganizations.ts

// Add new interface for organization with frequently accessed
export interface FrequentItem {
  entity_type: string;
  entity_id: string;
  name: string;
  view_count: number;
}

export interface OrganizationWithFrequent extends Organization {
  frequently_accessed?: FrequentItem[] | null;
}

interface UseOrganizationOptions {
  include?: string[];
}

export function useOrganization(orgId: string, options?: UseOrganizationOptions) {
  return useQuery({
    queryKey: ["organization", orgId, options?.include],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (options?.include?.length) {
        params.include = options.include.join(",");
      }
      const response = await api.get<OrganizationWithFrequent>(
        `/api/organizations/${orgId}`,
        { params }
      );
      return response.data;
    },
    enabled: !!orgId,
  });
}
```

**Step 2: Run type check**

```bash
cd client && npm run tsc
```

Expected: No errors

**Step 3: Commit**

```bash
git add client/src/hooks/useOrganizations.ts
git commit -m "feat(client): add include param support to useOrganization

Supports fetching frequently_accessed with organization data."
```

---

## Task 10: Create RecentEntityCard Component

**Files:**
- Create: `client/src/components/RecentEntityCard.tsx`

**Step 1: Create the component**

```typescript
// client/src/components/RecentEntityCard.tsx

import { useNavigate } from "react-router-dom";
import {
  Key,
  Server,
  MapPin,
  FileText,
  Package,
  Building2,
  type LucideIcon,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface RecentEntityCardProps {
  entityType: string;
  entityId: string;
  organizationId: string | null;
  orgName: string | null;
  name: string;
  showOrg?: boolean;
  className?: string;
}

const entityConfig: Record<
  string,
  { icon: LucideIcon; label: string; path: (orgId: string, id: string) => string }
> = {
  password: {
    icon: Key,
    label: "Password",
    path: (orgId, id) => `/org/${orgId}/passwords/${id}`,
  },
  configuration: {
    icon: Server,
    label: "Configuration",
    path: (orgId, id) => `/org/${orgId}/configurations/${id}`,
  },
  location: {
    icon: MapPin,
    label: "Location",
    path: (orgId, id) => `/org/${orgId}/locations/${id}`,
  },
  document: {
    icon: FileText,
    label: "Document",
    path: (orgId, id) => `/org/${orgId}/documents/${id}`,
  },
  custom_asset: {
    icon: Package,
    label: "Asset",
    path: (orgId, id) => `/org/${orgId}/assets/${id}`,
  },
  organization: {
    icon: Building2,
    label: "Organization",
    path: (_, id) => `/org/${id}`,
  },
};

export function RecentEntityCard({
  entityType,
  entityId,
  organizationId,
  orgName,
  name,
  showOrg = true,
  className,
}: RecentEntityCardProps) {
  const navigate = useNavigate();
  const config = entityConfig[entityType] || {
    icon: Package,
    label: entityType,
    path: () => "#",
  };
  const Icon = config.icon;

  const handleClick = () => {
    const orgId = organizationId || entityId; // For organizations, use entityId
    navigate(config.path(orgId, entityId));
  };

  return (
    <Card
      className={cn(
        "hover:border-primary/50 transition-colors cursor-pointer group min-w-[180px]",
        className
      )}
      onClick={handleClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Icon className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium truncate">{name}</p>
            {showOrg && orgName && entityType !== "organization" && (
              <p className="text-xs text-muted-foreground truncate">{orgName}</p>
            )}
            {!showOrg && (
              <p className="text-xs text-muted-foreground">{config.label}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Run type check and lint**

```bash
cd client && npm run tsc && npm run lint
```

Expected: No errors

**Step 3: Commit**

```bash
git add client/src/components/RecentEntityCard.tsx
git commit -m "feat(client): add RecentEntityCard component

Compact card for displaying recently/frequently accessed entities."
```

---

## Task 11: Create RecentDropdown Component for Header

**Files:**
- Create: `client/src/components/layout/RecentDropdown.tsx`
- Modify: `client/src/components/layout/Header.tsx`

**Step 1: Create the dropdown component**

```typescript
// client/src/components/layout/RecentDropdown.tsx

import { Clock, Key, Server, MapPin, FileText, Package, Building2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useRecentlyAccessed, RecentItem } from "@/hooks/useRecentlyAccessed";
import { Skeleton } from "@/components/ui/skeleton";

const entityIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  password: Key,
  configuration: Server,
  location: MapPin,
  document: FileText,
  custom_asset: Package,
  organization: Building2,
};

function getEntityPath(item: RecentItem): string {
  if (item.entity_type === "organization") {
    return `/org/${item.entity_id}`;
  }
  return `/org/${item.organization_id}/${item.entity_type}s/${item.entity_id}`;
}

export function RecentDropdown() {
  const navigate = useNavigate();
  const { data: recentItems, isLoading } = useRecentlyAccessed(10);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Clock className="h-4 w-4" />
          <span className="sr-only">Recent items</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel>Recently Accessed</DropdownMenuLabel>
        <DropdownMenuSeparator />

        {isLoading ? (
          <div className="p-2 space-y-2">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : recentItems && recentItems.length > 0 ? (
          recentItems.map((item) => {
            const Icon = entityIcons[item.entity_type] || Package;
            return (
              <DropdownMenuItem
                key={`${item.entity_type}-${item.entity_id}`}
                onClick={() => navigate(getEntityPath(item))}
                className="cursor-pointer"
              >
                <Icon className="h-4 w-4 mr-3 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{item.name}</p>
                  {item.org_name && item.entity_type !== "organization" && (
                    <p className="text-xs text-muted-foreground truncate">
                      {item.org_name}
                    </p>
                  )}
                </div>
              </DropdownMenuItem>
            );
          })
        ) : (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No recent activity
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

**Step 2: Add RecentDropdown to Header**

```typescript
// In client/src/components/layout/Header.tsx

import { RecentDropdown } from "./RecentDropdown";

// In the right section of the header, before the chat button:
<RecentDropdown />
```

**Step 3: Run type check and lint**

```bash
cd client && npm run tsc && npm run lint
```

Expected: No errors

**Step 4: Commit**

```bash
git add client/src/components/layout/RecentDropdown.tsx client/src/components/layout/Header.tsx
git commit -m "feat(client): add RecentDropdown to header

Shows last 10 accessed entities in a dropdown menu."
```

---

## Task 12: Add Recent Sections to Dashboard

**Files:**
- Modify: `client/src/pages/DashboardPage.tsx`

**Step 1: Update DashboardPage**

```typescript
// In client/src/pages/DashboardPage.tsx

import { useRecentlyAccessed } from "@/hooks/useRecentlyAccessed";
import { RecentEntityCard } from "@/components/RecentEntityCard";

export function DashboardPage() {
  const { data: recentItems, isLoading: recentLoading } = useRecentlyAccessed(12);

  // Separate organizations from other entities
  const recentOrgs = recentItems?.filter((item) => item.entity_type === "organization").slice(0, 6) || [];
  const recentEntities = recentItems?.filter((item) => item.entity_type !== "organization").slice(0, 6) || [];

  return (
    <div className="space-y-8">
      {/* Existing header content */}

      {/* Recent Organizations Section */}
      {!recentLoading && recentOrgs.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent Organizations</h2>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {recentOrgs.map((item) => (
              <RecentEntityCard
                key={`${item.entity_type}-${item.entity_id}`}
                entityType={item.entity_type}
                entityId={item.entity_id}
                organizationId={item.organization_id}
                orgName={item.org_name}
                name={item.name}
                showOrg={false}
              />
            ))}
          </div>
        </div>
      )}

      {/* Recent Entities Section */}
      {!recentLoading && recentEntities.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent Items</h2>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {recentEntities.map((item) => (
              <RecentEntityCard
                key={`${item.entity_type}-${item.entity_id}`}
                entityType={item.entity_type}
                entityId={item.entity_id}
                organizationId={item.organization_id}
                orgName={item.org_name}
                name={item.name}
              />
            ))}
          </div>
        </div>
      )}

      {/* Rest of existing dashboard content */}
    </div>
  );
}
```

**Step 2: Run type check and lint**

```bash
cd client && npm run tsc && npm run lint
```

Expected: No errors

**Step 3: Commit**

```bash
git add client/src/pages/DashboardPage.tsx
git commit -m "feat(client): add recent sections to dashboard

Shows recent organizations and recent entities in horizontal card rows."
```

---

## Task 13: Add Recent Cards to Organizations Page

**Files:**
- Modify: `client/src/pages/organizations/OrganizationsListPage.tsx`

**Step 1: Update OrganizationsListPage**

```typescript
// In client/src/pages/organizations/OrganizationsListPage.tsx

import { useRecentlyAccessed } from "@/hooks/useRecentlyAccessed";
import { RecentEntityCard } from "@/components/RecentEntityCard";

export function OrganizationsListPage() {
  // Existing code...

  const { data: recentItems } = useRecentlyAccessed(6);
  const recentOrgs = recentItems?.filter((item) => item.entity_type === "organization") || [];

  return (
    <div className="space-y-8">
      {/* Header section */}

      {/* Recent Organizations Section - above the list */}
      {recentOrgs.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent</h2>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {recentOrgs.map((item) => (
              <RecentEntityCard
                key={item.entity_id}
                entityType={item.entity_type}
                entityId={item.entity_id}
                organizationId={item.organization_id}
                orgName={item.org_name}
                name={item.name}
                showOrg={false}
              />
            ))}
          </div>
        </div>
      )}

      {/* Search and Filter Controls */}
      {/* Existing grid with organizations */}
    </div>
  );
}
```

**Step 2: Run type check and lint**

```bash
cd client && npm run tsc && npm run lint
```

Expected: No errors

**Step 3: Commit**

```bash
git add client/src/pages/organizations/OrganizationsListPage.tsx
git commit -m "feat(client): add recent organizations cards to list page

Shows recent orgs above the main organization list."
```

---

## Task 14: Add Frequently Accessed to Org Home Page

**Files:**
- Modify: `client/src/pages/OrgHomePage.tsx`

**Step 1: Update OrgHomePage**

```typescript
// In client/src/pages/OrgHomePage.tsx

import { RecentEntityCard } from "@/components/RecentEntityCard";

export function OrgHomePage() {
  const { orgId } = useParams<{ orgId: string }>();

  // Fetch org with frequently accessed
  const { data: organization, isLoading } = useOrganization(orgId || "", {
    include: ["frequently_accessed"],
  });

  const frequentItems = organization?.frequently_accessed || [];

  return (
    <div className="space-y-8">
      {/* Existing header and stats */}

      {/* Frequently Accessed Section */}
      {frequentItems.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Frequently Accessed</h2>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {frequentItems.map((item) => (
              <RecentEntityCard
                key={`${item.entity_type}-${item.entity_id}`}
                entityType={item.entity_type}
                entityId={item.entity_id}
                organizationId={orgId || null}
                orgName={null}
                name={item.name}
                showOrg={false}
              />
            ))}
          </div>
        </div>
      )}

      {/* Rest of existing content */}
    </div>
  );
}
```

**Step 2: Run type check and lint**

```bash
cd client && npm run tsc && npm run lint
```

Expected: No errors

**Step 3: Commit**

```bash
git add client/src/pages/OrgHomePage.tsx
git commit -m "feat(client): add frequently accessed section to org home

Shows most viewed entities in the org over the last 30 days."
```

---

## Task 15: Add Query Invalidation on Navigation

**Files:**
- Create: `client/src/hooks/useTrackNavigation.ts`
- Modify: `client/src/App.tsx` or relevant layout component

**Step 1: Create navigation tracking hook**

```typescript
// client/src/hooks/useTrackNavigation.ts

import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

/**
 * Invalidates the recent items query when navigating to entity detail pages.
 * This ensures the recent list stays up-to-date as views are logged server-side.
 */
export function useTrackNavigation() {
  const location = useLocation();
  const queryClient = useQueryClient();

  useEffect(() => {
    // Match entity detail page patterns
    const entityPatterns = [
      /\/org\/[^/]+\/passwords\/[^/]+$/,
      /\/org\/[^/]+\/configurations\/[^/]+$/,
      /\/org\/[^/]+\/locations\/[^/]+$/,
      /\/org\/[^/]+\/documents\/[^/]+$/,
      /\/org\/[^/]+\/assets\/[^/]+$/,
      /\/org\/[^/]+$/, // Org home page
    ];

    const isEntityDetailPage = entityPatterns.some((pattern) =>
      pattern.test(location.pathname)
    );

    if (isEntityDetailPage) {
      // Invalidate recent list after a short delay to allow the view to be logged
      const timeout = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["recent"] });
      }, 500);

      return () => clearTimeout(timeout);
    }
  }, [location.pathname, queryClient]);
}
```

**Step 2: Add hook to app layout**

```typescript
// In client/src/components/layout/AppLayout.tsx or similar

import { useTrackNavigation } from "@/hooks/useTrackNavigation";

export function AppLayout({ children }: { children: React.ReactNode }) {
  useTrackNavigation();

  return (
    // ... existing layout
  );
}
```

**Step 3: Run type check and lint**

```bash
cd client && npm run tsc && npm run lint
```

Expected: No errors

**Step 4: Commit**

```bash
git add client/src/hooks/useTrackNavigation.ts client/src/components/layout/AppLayout.tsx
git commit -m "feat(client): auto-invalidate recent list on navigation

Refreshes recent items when navigating to entity detail pages."
```

---

## Task 16: Final Integration Testing

**Step 1: Run all backend tests**

```bash
cd api && pytest -v
```

Expected: All tests pass

**Step 2: Run all frontend checks**

```bash
cd client && npm run tsc && npm run lint
```

Expected: No errors

**Step 3: Manual testing checklist**

- [ ] View a password → appears in recent dropdown
- [ ] View multiple entities → ordered by most recent
- [ ] Same entity viewed twice → only appears once
- [ ] Dashboard shows recent orgs and entities
- [ ] Organizations page shows recent orgs above list
- [ ] Org home page shows frequently accessed (need some view data)
- [ ] Empty states display correctly

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete recently/frequently accessed implementation

- Audit service with dedupe support
- VIEW logging on all entity GET endpoints
- AccessTrackingRepository for queries
- GET /api/me/recent endpoint
- Organization endpoint with frequently_accessed include
- RecentEntityCard component
- RecentDropdown in header
- Dashboard recent sections
- Organizations page recent cards
- Org home frequently accessed section
- Navigation tracking for query invalidation"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add dedupe to audit service | audit_service.py |
| 2 | VIEW logging - passwords | passwords.py |
| 3 | VIEW logging - all other entities | 5 router files |
| 4 | AccessTrackingRepository | access_tracking.py |
| 5 | GET /api/me/recent endpoint | me.py |
| 6 | Org endpoint with include | organizations.py |
| 7 | Database index | migration |
| 8 | useRecentlyAccessed hook | useRecentlyAccessed.ts |
| 9 | Update org hook | useOrganizations.ts |
| 10 | RecentEntityCard component | RecentEntityCard.tsx |
| 11 | RecentDropdown in header | RecentDropdown.tsx, Header.tsx |
| 12 | Dashboard recent sections | DashboardPage.tsx |
| 13 | Organizations page recent cards | OrganizationsListPage.tsx |
| 14 | Org home frequently accessed | OrgHomePage.tsx |
| 15 | Navigation tracking | useTrackNavigation.ts |
| 16 | Final integration testing | - |
