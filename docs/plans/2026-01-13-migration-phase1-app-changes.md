# Migration Tool Phase 1: App Changes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add metadata JSONB columns, interfaces column, and stable image URL endpoint to support IT Glue migration.

**Architecture:** Add JSONB metadata column to 6 entity tables for tracking external IDs (itglue_id). Add interfaces JSONB to configurations for network interface data. Add /view endpoint for stable attachment URLs that don't expire.

**Tech Stack:** SQLAlchemy 2.0, Alembic migrations, FastAPI, Pydantic v2

**Reference:** See `docs/plans/MIGRATION_TOOL.md` for full context.

---

## Task 1: Database Migration - Add metadata JSONB columns

**Files:**
- Create: `api/alembic/versions/20260113_005000_add_metadata_columns.py`

**Step 1: Create the migration file**

```python
"""Add metadata JSONB columns to entities for external system tracking

Revision ID: 20260113_005000
Revises: 20260113_004000
Create Date: 2026-01-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260113_005000"
down_revision: str | None = "20260113_004000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add metadata column to organizations
    op.add_column(
        "organizations",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_organizations_metadata_itglue_id",
        "organizations",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to documents
    op.add_column(
        "documents",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_documents_metadata_itglue_id",
        "documents",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to configurations
    op.add_column(
        "configurations",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_configurations_metadata_itglue_id",
        "configurations",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to passwords
    op.add_column(
        "passwords",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_passwords_metadata_itglue_id",
        "passwords",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to locations
    op.add_column(
        "locations",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_locations_metadata_itglue_id",
        "locations",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to custom_assets
    op.add_column(
        "custom_assets",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_custom_assets_metadata_itglue_id",
        "custom_assets",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )


def downgrade() -> None:
    # Drop indexes and columns in reverse order
    op.drop_index("ix_custom_assets_metadata_itglue_id", table_name="custom_assets")
    op.drop_column("custom_assets", "metadata")

    op.drop_index("ix_locations_metadata_itglue_id", table_name="locations")
    op.drop_column("locations", "metadata")

    op.drop_index("ix_passwords_metadata_itglue_id", table_name="passwords")
    op.drop_column("passwords", "metadata")

    op.drop_index("ix_configurations_metadata_itglue_id", table_name="configurations")
    op.drop_column("configurations", "metadata")

    op.drop_index("ix_documents_metadata_itglue_id", table_name="documents")
    op.drop_column("documents", "metadata")

    op.drop_index("ix_organizations_metadata_itglue_id", table_name="organizations")
    op.drop_column("organizations", "metadata")
```

**Step 2: Run the migration**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && alembic upgrade head
```

Expected: Migration applies successfully, 6 tables updated.

**Step 3: Verify migration applied**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && alembic current
```

Expected: Shows `20260113_005000` as current revision.

**Step 4: Commit**

```bash
git add api/alembic/versions/20260113_005000_add_metadata_columns.py
git commit -m "feat(db): add metadata JSONB columns for external system tracking"
```

---

## Task 2: Database Migration - Add interfaces column to configurations

**Files:**
- Create: `api/alembic/versions/20260113_006000_add_interfaces_to_configurations.py`

**Step 1: Create the migration file**

```python
"""Add interfaces JSONB column to configurations for network interface data

Revision ID: 20260113_006000
Revises: 20260113_005000
Create Date: 2026-01-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260113_006000"
down_revision: str | None = "20260113_005000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "configurations",
        sa.Column("interfaces", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("configurations", "interfaces")
```

**Step 2: Run the migration**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && alembic upgrade head
```

**Step 3: Commit**

```bash
git add api/alembic/versions/20260113_006000_add_interfaces_to_configurations.py
git commit -m "feat(db): add interfaces JSONB column to configurations"
```

---

## Task 3: Update ORM Models - Add metadata to all entities

**Files:**
- Modify: `api/src/models/orm/organization.py`
- Modify: `api/src/models/orm/document.py`
- Modify: `api/src/models/orm/configuration.py`
- Modify: `api/src/models/orm/password.py`
- Modify: `api/src/models/orm/location.py`
- Modify: `api/src/models/orm/custom_asset.py`

**Step 1: Update Organization model**

Add to `api/src/models/orm/organization.py` after the `updated_at` column:

```python
from sqlalchemy.dialects.postgresql import JSONB

# Inside the Organization class, add:
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
```

Note: Using `metadata_` as Python attribute name since `metadata` is reserved by SQLAlchemy.

**Step 2: Update Document model**

Add to `api/src/models/orm/document.py`:

```python
from sqlalchemy.dialects.postgresql import JSONB

# Inside the Document class, add:
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
```

**Step 3: Update Configuration model**

Add to `api/src/models/orm/configuration.py`:

```python
from sqlalchemy.dialects.postgresql import JSONB

# Inside the Configuration class, add:
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    interfaces: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
```

**Step 4: Update Password model**

Add to `api/src/models/orm/password.py`:

```python
from sqlalchemy.dialects.postgresql import JSONB

# Inside the Password class, add:
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
```

**Step 5: Update Location model**

Add to `api/src/models/orm/location.py`:

```python
from sqlalchemy.dialects.postgresql import JSONB

# Inside the Location class, add:
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
```

**Step 6: Update CustomAsset model**

Add to `api/src/models/orm/custom_asset.py`:

```python
# Inside the CustomAsset class, add (JSONB already imported for values):
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
```

**Step 7: Run tests to verify models work**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/ -v --tb=short -x
```

Expected: All tests pass.

**Step 8: Commit**

```bash
git add api/src/models/orm/
git commit -m "feat(models): add metadata and interfaces columns to ORM models"
```

---

## Task 4: Update Pydantic Contracts - Add metadata to Create/Update/Public

**Files:**
- Modify: `api/src/models/contracts/organization.py`
- Modify: `api/src/models/contracts/document.py`
- Modify: `api/src/models/contracts/configuration.py`
- Modify: `api/src/models/contracts/password.py`
- Modify: `api/src/models/contracts/location.py`
- Modify: `api/src/models/contracts/custom_asset.py`

**Step 1: Update Organization contracts**

In `api/src/models/contracts/organization.py`:

```python
# Add to OrganizationCreate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to OrganizationUpdate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to OrganizationPublic:
    metadata: dict = Field(default_factory=dict, description="External system metadata")
```

**Step 2: Update Document contracts**

In `api/src/models/contracts/document.py`:

```python
# Add to DocumentCreate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to DocumentUpdate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to DocumentPublic:
    metadata: dict = Field(default_factory=dict, description="External system metadata")
```

**Step 3: Update Configuration contracts**

In `api/src/models/contracts/configuration.py`:

```python
# Add to ConfigurationCreate:
    metadata: dict | None = Field(default=None, description="External system metadata")
    interfaces: list | None = Field(default=None, description="Network interfaces")

# Add to ConfigurationUpdate:
    metadata: dict | None = Field(default=None, description="External system metadata")
    interfaces: list | None = Field(default=None, description="Network interfaces")

# Add to ConfigurationPublic:
    metadata: dict = Field(default_factory=dict, description="External system metadata")
    interfaces: list = Field(default_factory=list, description="Network interfaces")
```

**Step 4: Update Password contracts**

In `api/src/models/contracts/password.py`:

```python
# Add to PasswordCreate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to PasswordUpdate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to PasswordPublic and PasswordReveal:
    metadata: dict = Field(default_factory=dict, description="External system metadata")
```

**Step 5: Update Location contracts**

In `api/src/models/contracts/location.py`:

```python
# Add to LocationCreate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to LocationUpdate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to LocationPublic:
    metadata: dict = Field(default_factory=dict, description="External system metadata")
```

**Step 6: Update CustomAsset contracts**

In `api/src/models/contracts/custom_asset.py`:

```python
# Add to CustomAssetCreate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to CustomAssetUpdate:
    metadata: dict | None = Field(default=None, description="External system metadata")

# Add to CustomAssetPublic and CustomAssetReveal:
    metadata: dict = Field(default_factory=dict, description="External system metadata")
```

**Step 7: Run tests**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/ -v --tb=short -x
```

**Step 8: Commit**

```bash
git add api/src/models/contracts/
git commit -m "feat(contracts): add metadata and interfaces fields to API contracts"
```

---

## Task 5: Update Routers - Handle metadata in create/update

**Files:**
- Modify: `api/src/routers/organizations.py`
- Modify: `api/src/routers/documents.py`
- Modify: `api/src/routers/configurations.py`
- Modify: `api/src/routers/passwords.py`
- Modify: `api/src/routers/locations.py`
- Modify: `api/src/routers/custom_assets.py`

**Step 1: Review current router patterns**

Read each router file to understand the current create/update patterns. The changes should be minimal since Pydantic will handle the new fields automatically if routers use `data.model_dump(exclude_unset=True)`.

**Step 2: Verify routers pass through all fields**

Check that each router's create/update endpoints pass through all fields from the Pydantic model. If they explicitly list fields, add `metadata` (and `interfaces` for configurations).

**Step 3: Run integration tests**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/integration/ -v --tb=short
```

**Step 4: Commit if changes needed**

```bash
git add api/src/routers/
git commit -m "feat(routers): ensure metadata and interfaces fields passed through"
```

---

## Task 6: Add Attachment View Endpoint

**Files:**
- Modify: `api/src/routers/attachments.py`
- Create: `api/tests/integration/test_attachment_view.py`

**Step 1: Write the failing test**

Create `api/tests/integration/test_attachment_view.py`:

```python
"""Tests for attachment view endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_view_attachment_redirects_to_presigned_url(
    client: AsyncClient,
    auth_headers: dict,
    test_org_id: str,
    test_attachment_id: str,
) -> None:
    """Test that view endpoint returns redirect to presigned URL."""
    response = await client.get(
        f"/api/organizations/{test_org_id}/attachments/{test_attachment_id}/view",
        headers=auth_headers,
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "Location" in response.headers
    location = response.headers["Location"]
    # Should be a presigned S3 URL
    assert "X-Amz-Signature" in location or "localhost" in location


@pytest.mark.asyncio
async def test_view_attachment_not_found(
    client: AsyncClient,
    auth_headers: dict,
    test_org_id: str,
) -> None:
    """Test that view returns 404 for non-existent attachment."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/api/organizations/{test_org_id}/attachments/{fake_id}/view",
        headers=auth_headers,
        follow_redirects=False,
    )

    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/integration/test_attachment_view.py -v
```

Expected: FAIL - endpoint doesn't exist.

**Step 3: Implement the view endpoint**

Add to `api/src/routers/attachments.py`:

```python
from fastapi.responses import RedirectResponse

@router.get("/{attachment_id}/view")
async def view_attachment(
    org_id: UUID,
    attachment_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> RedirectResponse:
    """Get a redirect to a fresh presigned URL for viewing an attachment.

    This endpoint provides stable URLs for embedding in documents.
    The redirect target is a presigned S3 URL that expires after 1 hour.
    """
    await _verify_org_membership(org_id, current_user, db)

    repo = AttachmentRepository(db)
    attachment = await repo.get_by_id(attachment_id)

    if not attachment or attachment.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    file_storage = get_file_storage_service()
    presigned_url = file_storage.generate_presigned_url(
        s3_key=attachment.s3_key,
        expires_in=3600,  # 1 hour
        content_type=attachment.content_type,
    )

    return RedirectResponse(url=presigned_url, status_code=302)
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/integration/test_attachment_view.py -v
```

Expected: PASS

**Step 5: Run full test suite**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/ -v --tb=short
```

**Step 6: Commit**

```bash
git add api/src/routers/attachments.py api/tests/integration/test_attachment_view.py
git commit -m "feat(attachments): add /view endpoint for stable image URLs"
```

---

## Task 7: Update Document Image Upload Response

**Files:**
- Modify: `api/src/routers/attachments.py`
- Modify: `api/tests/integration/test_attachments.py`

**Step 1: Update the document image upload endpoint**

In `api/src/routers/attachments.py`, find the `upload_document_image` endpoint and change the `image_url` to use the stable `/view` path instead of a presigned URL:

```python
# Change from:
# image_url = presigned_url

# To:
image_url = f"/api/organizations/{org_id}/attachments/{attachment.id}/view"
```

**Step 2: Update tests if needed**

Update any tests that assert on the `image_url` format.

**Step 3: Run tests**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/integration/test_attachments.py -v
```

**Step 4: Commit**

```bash
git add api/src/routers/attachments.py api/tests/integration/test_attachments.py
git commit -m "feat(attachments): return stable /view URL from document image upload"
```

---

## Task 8: Integration Test - Full metadata flow

**Files:**
- Create: `api/tests/integration/test_metadata.py`

**Step 1: Write comprehensive metadata test**

```python
"""Tests for metadata field support across all entities."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_configuration_with_metadata_and_interfaces(
    client: AsyncClient,
    auth_headers: dict,
    test_org_id: str,
    test_config_type_id: str,
    test_config_status_id: str,
) -> None:
    """Test creating configuration with metadata and interfaces."""
    response = await client.post(
        f"/api/organizations/{test_org_id}/configurations",
        headers=auth_headers,
        json={
            "name": "Test Server",
            "configuration_type_id": test_config_type_id,
            "configuration_status_id": test_config_status_id,
            "metadata": {
                "itglue_id": "12345",
                "itglue_last_updated": "2024-01-15T10:30:00Z"
            },
            "interfaces": [
                {
                    "name": "eth0",
                    "ip_address": "192.168.1.100",
                    "mac_address": "00:11:22:33:44:55",
                    "primary": True
                }
            ]
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["metadata"]["itglue_id"] == "12345"
    assert len(data["interfaces"]) == 1
    assert data["interfaces"][0]["ip_address"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_document_with_metadata(
    client: AsyncClient,
    auth_headers: dict,
    test_org_id: str,
) -> None:
    """Test creating document with metadata."""
    response = await client.post(
        f"/api/organizations/{test_org_id}/documents",
        headers=auth_headers,
        json={
            "name": "Test Document",
            "path": "/Test",
            "content": "<p>Test content</p>",
            "metadata": {
                "itglue_id": "67890",
                "itglue_last_updated": "2024-01-15T10:30:00Z"
            }
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["metadata"]["itglue_id"] == "67890"


@pytest.mark.asyncio
async def test_password_with_metadata(
    client: AsyncClient,
    auth_headers: dict,
    test_org_id: str,
) -> None:
    """Test creating password with metadata."""
    response = await client.post(
        f"/api/organizations/{test_org_id}/passwords",
        headers=auth_headers,
        json={
            "name": "Test Password",
            "username": "admin",
            "password": "secret123",
            "metadata": {
                "itglue_id": "11111",
                "itglue_resource_type": "Configuration",
                "itglue_resource_id": "22222"
            }
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["metadata"]["itglue_id"] == "11111"
```

**Step 2: Run the test**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/integration/test_metadata.py -v
```

**Step 3: Commit**

```bash
git add api/tests/integration/test_metadata.py
git commit -m "test: add integration tests for metadata field support"
```

---

## Task 9: Run Full Test Suite and Type Checks

**Step 1: Run all tests**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/ -v
```

Expected: All tests pass.

**Step 2: Run type checker**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && pyright
```

Expected: No errors.

**Step 3: Run linter**

```bash
cd /Users/jack/GitHub/gocovi-docs/api && ruff check
```

Expected: No errors.

**Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address any remaining type/lint issues"
```

---

## Summary

After completing all tasks:

- [x] `metadata JSONB` added to 6 tables (organizations, documents, configurations, passwords, locations, custom_assets)
- [x] `interfaces JSONB` added to configurations
- [x] Partial indexes on `metadata->>'itglue_id'` for efficient lookups
- [x] ORM models updated with new columns
- [x] Pydantic contracts support metadata and interfaces
- [x] Routers pass through new fields
- [x] `/attachments/{id}/view` endpoint returns redirect to fresh presigned URL
- [x] Document image upload returns stable `/view` URL
- [x] All tests pass
- [x] Type checking passes
- [x] Linting passes

**Next:** Proceed to Phase 2 - Migration Tool implementation.
