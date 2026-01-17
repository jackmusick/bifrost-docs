# API Response Model Simplification

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace manual field-by-field response construction with `model_validate()` to eliminate silent field omission bugs.

**Architecture:** Create a `PublicEntityBase` class with shared Pydantic features (UUID serialization, `metadata_` alias, common fields). Each entity's `*Public` model inherits from this base. Routers call `Model.model_validate(orm_object)` instead of manual field mapping.

**Tech Stack:** Pydantic v2 (`ConfigDict`, `field_serializer`, `computed_field`, `validation_alias`), FastAPI, SQLAlchemy ORM

---

## Summary of Changes

| Entity | Complexity | Special Handling |
|--------|------------|------------------|
| Location | Simple | None - baseline test |
| Document | Simple | None |
| Organization | Simple | No `organization_id` field (special base) |
| Password | Medium | Computed `has_totp` field |
| Configuration | Medium | Joined relationship names (`type_name`, `status_name`) |
| CustomAsset | Complex | Password field filtering (keep helper functions) |

---

## Task 1: Create PublicEntityBase Class

**Files:**
- Create: `api/src/models/contracts/base.py`
- Modify: `api/src/models/contracts/__init__.py`
- Create: `api/tests/unit/models/test_base_contracts.py`

### Step 1: Write the failing tests

```python
# api/tests/unit/models/test_base_contracts.py
"""Unit tests for base contract classes."""

from datetime import datetime, UTC
from uuid import UUID, uuid4

import pytest


class TestPublicEntityBase:
    """Tests for PublicEntityBase ORM-to-Pydantic conversion."""

    def test_uuid_fields_serialize_to_strings(self):
        """UUID fields should serialize to strings in JSON output."""
        from src.models.contracts.base import PublicEntityBase

        class TestEntity:
            """Mock ORM entity."""
            id = uuid4()
            organization_id = uuid4()
            is_enabled = True
            metadata_ = {"key": "value"}
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        result = PublicEntityBase.model_validate(TestEntity())
        json_data = result.model_dump(mode="json")

        # UUIDs should be strings in JSON
        assert isinstance(json_data["id"], str)
        assert isinstance(json_data["organization_id"], str)
        assert json_data["id"] == str(TestEntity.id)

    def test_metadata_alias_maps_from_metadata_underscore(self):
        """metadata_ ORM field should map to metadata in response."""
        from src.models.contracts.base import PublicEntityBase

        class TestEntity:
            """Mock ORM entity with metadata_ field."""
            id = uuid4()
            organization_id = uuid4()
            is_enabled = True
            metadata_ = {"source": "test", "version": 1}
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        result = PublicEntityBase.model_validate(TestEntity())

        assert result.metadata == {"source": "test", "version": 1}

    def test_metadata_defaults_to_empty_dict_when_none(self):
        """metadata should default to empty dict if ORM field is None."""
        from src.models.contracts.base import PublicEntityBase

        class TestEntity:
            """Mock ORM entity with None metadata."""
            id = uuid4()
            organization_id = uuid4()
            is_enabled = True
            metadata_ = None
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        result = PublicEntityBase.model_validate(TestEntity())

        assert result.metadata == {}

    def test_is_enabled_preserves_false_value(self):
        """is_enabled=False should not be overwritten by default."""
        from src.models.contracts.base import PublicEntityBase

        class TestEntity:
            """Mock ORM entity with is_enabled=False."""
            id = uuid4()
            organization_id = uuid4()
            is_enabled = False  # This was the bug!
            metadata_ = {}
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        result = PublicEntityBase.model_validate(TestEntity())

        assert result.is_enabled is False


class TestPublicOrgBase:
    """Tests for PublicOrgBase (Organization-specific, no org_id)."""

    def test_org_base_has_no_organization_id_field(self):
        """PublicOrgBase should not have organization_id field."""
        from src.models.contracts.base import PublicOrgBase

        assert "organization_id" not in PublicOrgBase.model_fields

    def test_org_base_uuid_serialization(self):
        """PublicOrgBase should still serialize UUID to string."""
        from src.models.contracts.base import PublicOrgBase

        class TestOrg:
            """Mock Organization ORM entity."""
            id = uuid4()
            is_enabled = True
            metadata_ = {}
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        result = PublicOrgBase.model_validate(TestOrg())
        json_data = result.model_dump(mode="json")

        assert isinstance(json_data["id"], str)
```

### Step 2: Run tests to verify they fail

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/unit/models/test_base_contracts.py -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'src.models.contracts.base'`

### Step 3: Implement the base classes

```python
# api/src/models/contracts/base.py
"""
Base classes for API response models.

These base classes handle common ORM-to-Pydantic conversion patterns:
- UUID serialization to strings
- metadata_ -> metadata field aliasing
- Common timestamp and enabled fields
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class PublicEntityBase(BaseModel):
    """
    Base class for organization-scoped public API response models.

    Handles:
    - Automatic UUID-to-string serialization for id and organization_id
    - metadata_ -> metadata field mapping via validation_alias
    - Common fields: id, organization_id, is_enabled, created_at, updated_at

    Usage:
        class LocationPublic(PublicEntityBase):
            name: str
            notes: str | None = None
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    is_enabled: bool
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    @field_serializer("id", "organization_id")
    def serialize_uuid(self, v: UUID) -> str:
        """Serialize UUID fields to strings for JSON output."""
        return str(v)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, v):
        """Ensure metadata is never None."""
        if v is None:
            return {}
        return v


class PublicOrgBase(BaseModel):
    """
    Base class for Organization response model (no organization_id field).

    Organizations don't have an organization_id since they ARE the organization.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_enabled: bool
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        """Serialize UUID field to string for JSON output."""
        return str(v)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, v):
        """Ensure metadata is never None."""
        if v is None:
            return {}
        return v
```

### Step 4: Run tests to verify they pass

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/unit/models/test_base_contracts.py -v
```

Expected: PASS

### Step 5: Commit

```bash
cd /Users/jack/GitHub/gocovi-docs/api
git add src/models/contracts/base.py tests/unit/models/test_base_contracts.py
git commit -m "$(cat <<'EOF'
feat(contracts): add PublicEntityBase and PublicOrgBase classes

Pydantic base classes for API response models that handle:
- UUID serialization to strings via field_serializer
- metadata_ -> metadata field mapping via validation_alias
- Common fields (id, org_id, is_enabled, timestamps)

This enables using model_validate() instead of manual field mapping.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Migrate LocationPublic (Baseline)

**Files:**
- Modify: `api/src/models/contracts/location.py`
- Modify: `api/src/routers/locations.py`

### Step 1: Add contract test for model_validate

```python
# Add to api/tests/unit/models/test_base_contracts.py

class TestLocationPublicModelValidate:
    """Tests for LocationPublic using model_validate."""

    def test_location_public_from_orm(self):
        """LocationPublic should work with model_validate from ORM object."""
        from src.models.contracts.location import LocationPublic
        from datetime import datetime, UTC
        from uuid import uuid4

        class MockLocation:
            """Mock Location ORM object."""
            id = uuid4()
            organization_id = uuid4()
            name = "Test Location"
            notes = "Some notes"
            is_enabled = False
            metadata_ = {"floor": 3}
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        result = LocationPublic.model_validate(MockLocation())

        assert result.name == "Test Location"
        assert result.notes == "Some notes"
        assert result.is_enabled is False
        assert result.metadata == {"floor": 3}
```

### Step 2: Run test to verify it fails

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/unit/models/test_base_contracts.py::TestLocationPublicModelValidate -v
```

Expected: FAIL - `metadata` field won't populate correctly (no `validation_alias`)

### Step 3: Update LocationPublic to inherit from base

```python
# api/src/models/contracts/location.py
"""
Location contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.contracts.base import PublicEntityBase


class LocationCreate(BaseModel):
    """Location creation request model."""

    name: str = Field(..., min_length=1, max_length=255)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided


class LocationUpdate(BaseModel):
    """Location update request model."""

    name: str | None = Field(None, min_length=1, max_length=255)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Don't change if not provided


class LocationPublic(PublicEntityBase):
    """Location public response model."""

    name: str
    notes: str | None = None
```

### Step 4: Run test to verify it passes

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/unit/models/test_base_contracts.py::TestLocationPublicModelValidate -v
```

Expected: PASS

### Step 5: Update router to use model_validate

```python
# api/src/routers/locations.py - Replace _to_public function

def _to_public(location: Location) -> LocationPublic:
    """Convert Location ORM model to public response."""
    return LocationPublic.model_validate(location)
```

### Step 6: Run integration tests

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/integration/test_locations.py -v
```

Expected: PASS

### Step 7: Commit

```bash
cd /Users/jack/GitHub/gocovi-docs/api
git add src/models/contracts/location.py src/routers/locations.py tests/unit/models/test_base_contracts.py
git commit -m "$(cat <<'EOF'
refactor(locations): use model_validate for response construction

LocationPublic now inherits from PublicEntityBase and uses
model_validate() instead of manual field-by-field construction.

No API changes - same JSON output, but now impossible to forget fields.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Migrate DocumentPublic

**Files:**
- Modify: `api/src/models/contracts/document.py`
- Modify: `api/src/routers/documents.py`

### Step 1: Update DocumentPublic contract

```python
# api/src/models/contracts/document.py
"""
Document contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.contracts.base import PublicEntityBase


class DocumentCreate(BaseModel):
    """Document creation request model."""

    path: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Virtual folder path, e.g., /Infrastructure/Network/Diagrams",
    )
    name: str = Field(..., min_length=1, max_length=255, description="Document title")
    content: str = Field(default="", description="Markdown content")
    metadata: dict | None = Field(default=None, description="External system metadata")
    is_enabled: bool | None = None  # Defaults to True if not provided


class DocumentUpdate(BaseModel):
    """Document update request model."""

    path: str | None = Field(
        default=None,
        min_length=1,
        max_length=1024,
        description="Virtual folder path",
    )
    name: str | None = Field(
        default=None, min_length=1, max_length=255, description="Document title"
    )
    content: str | None = Field(default=None, description="Markdown content")
    metadata: dict | None = Field(default=None, description="External system metadata")
    is_enabled: bool | None = None  # Don't change if not provided


class DocumentPublic(PublicEntityBase):
    """Document public response model."""

    path: str
    name: str
    content: str


class FolderCount(BaseModel):
    """Folder with document count."""

    path: str = Field(..., description="Folder path")
    count: int = Field(..., ge=0, description="Number of documents in this folder")


class FolderList(BaseModel):
    """List of distinct folder paths with document counts."""

    folders: list[FolderCount] = Field(
        default_factory=list, description="List of folders with document counts"
    )
```

### Step 2: Update router helper and inline constructions

Replace all `DocumentPublic(...)` constructions in `api/src/routers/documents.py`:

```python
# In list_documents (lines 91-104):
items = [DocumentPublic.model_validate(doc) for doc in documents]

# In create_document (lines 184-194):
return DocumentPublic.model_validate(doc)

# In get_document (lines 228-238):
return DocumentPublic.model_validate(doc)

# In update_document (lines 300-310):
return DocumentPublic.model_validate(doc)
```

### Step 3: Run tests

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/integration/test_documents.py -v
```

Expected: PASS

### Step 4: Commit

```bash
cd /Users/jack/GitHub/gocovi-docs/api
git add src/models/contracts/document.py src/routers/documents.py
git commit -m "$(cat <<'EOF'
refactor(documents): use model_validate for response construction

DocumentPublic now inherits from PublicEntityBase.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Migrate OrganizationPublic

**Files:**
- Modify: `api/src/models/contracts/organization.py`
- Modify: `api/src/routers/organizations.py`

### Step 1: Update OrganizationPublic contract

```python
# api/src/models/contracts/organization.py - OrganizationPublic class only
"""
Organization contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.contracts.base import PublicOrgBase


class OrganizationCreate(BaseModel):
    """Organization creation request model."""

    name: str
    metadata: dict | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided


class OrganizationUpdate(BaseModel):
    """Organization update request model."""

    name: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Don't change if not provided


class OrganizationPublic(PublicOrgBase):
    """Organization public response model."""

    name: str


# ... rest of file unchanged (SidebarItemCount, SidebarData)
```

### Step 2: Update router constructions

Replace all `OrganizationPublic(...)` in `api/src/routers/organizations.py`:

```python
# list_organizations (lines 61-71):
return [OrganizationPublic.model_validate(org) for org in organizations]

# create_organization (lines 106-113):
return OrganizationPublic.model_validate(org)

# get_organization (lines 147-154):
return OrganizationPublic.model_validate(org)

# update_organization (lines 205-212):
return OrganizationPublic.model_validate(org)
```

### Step 3: Run tests

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/ -k "organization" -v
```

Expected: PASS

### Step 4: Commit

```bash
cd /Users/jack/GitHub/gocovi-docs/api
git add src/models/contracts/organization.py src/routers/organizations.py
git commit -m "$(cat <<'EOF'
refactor(organizations): use model_validate for response construction

OrganizationPublic now inherits from PublicOrgBase (no org_id field).

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Migrate PasswordPublic (Computed Field)

**Files:**
- Modify: `api/src/models/contracts/password.py`
- Modify: `api/src/routers/passwords.py`
- Add: `api/tests/unit/models/test_base_contracts.py` (password tests)

### Step 1: Add test for computed has_totp field

```python
# Add to api/tests/unit/models/test_base_contracts.py

class TestPasswordPublicModelValidate:
    """Tests for PasswordPublic computed field handling."""

    def test_has_totp_true_when_secret_present(self):
        """has_totp should be True when totp_secret_encrypted exists."""
        from src.models.contracts.password import PasswordPublic
        from datetime import datetime, UTC
        from uuid import uuid4

        class MockPassword:
            id = uuid4()
            organization_id = uuid4()
            name = "Admin"
            username = "admin"
            url = "https://example.com"
            notes = None
            totp_secret_encrypted = "encrypted_secret_here"
            is_enabled = True
            metadata_ = {}
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        result = PasswordPublic.model_validate(MockPassword())

        assert result.has_totp is True

    def test_has_totp_false_when_secret_none(self):
        """has_totp should be False when totp_secret_encrypted is None."""
        from src.models.contracts.password import PasswordPublic
        from datetime import datetime, UTC
        from uuid import uuid4

        class MockPassword:
            id = uuid4()
            organization_id = uuid4()
            name = "Admin"
            username = "admin"
            url = None
            notes = None
            totp_secret_encrypted = None
            is_enabled = True
            metadata_ = {}
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        result = PasswordPublic.model_validate(MockPassword())

        assert result.has_totp is False

    def test_password_encrypted_not_in_output(self):
        """password_encrypted should never appear in JSON output."""
        from src.models.contracts.password import PasswordPublic
        from datetime import datetime, UTC
        from uuid import uuid4

        class MockPassword:
            id = uuid4()
            organization_id = uuid4()
            name = "Admin"
            username = "admin"
            url = None
            notes = None
            password_encrypted = "should_not_appear"
            totp_secret_encrypted = None
            is_enabled = True
            metadata_ = {}
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        result = PasswordPublic.model_validate(MockPassword())
        json_data = result.model_dump(mode="json")

        assert "password_encrypted" not in json_data
        assert "password" not in json_data
```

### Step 2: Run tests to verify they fail

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/unit/models/test_base_contracts.py::TestPasswordPublicModelValidate -v
```

Expected: FAIL

### Step 3: Update PasswordPublic with computed field

```python
# api/src/models/contracts/password.py
"""
Password contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from src.models.contracts.base import PublicEntityBase


class PasswordCreate(BaseModel):
    """Password creation request model."""

    name: str = Field(..., min_length=1, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    password: str = Field(..., min_length=1)
    totp_secret: str | None = None
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided


class PasswordUpdate(BaseModel):
    """Password update request model."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=1)
    totp_secret: str | None = None
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Don't change if not provided


class PasswordPublic(PublicEntityBase):
    """Password public response model (without password value)."""

    name: str
    username: str | None = None
    url: str | None = None
    notes: str | None = None

    # Read from ORM but exclude from JSON output
    totp_secret_encrypted: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def has_totp(self) -> bool:
        """Whether this password has TOTP configured."""
        return bool(self.totp_secret_encrypted)


class PasswordReveal(PasswordPublic):
    """Password response model with decrypted password and TOTP secret."""

    password: str
    totp_secret: str | None = None
```

### Step 4: Run tests to verify they pass

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/unit/models/test_base_contracts.py::TestPasswordPublicModelValidate -v
```

Expected: PASS

### Step 5: Update router - remove manual constructions

```python
# api/src/routers/passwords.py

# list_passwords (lines 85-100):
items = [PasswordPublic.model_validate(p) for p in passwords]

# create_password (lines 159-171):
return PasswordPublic.model_validate(password)

# get_password (lines 205-217):
return PasswordPublic.model_validate(password)

# update_password (lines 341-353):
return PasswordPublic.model_validate(password)
```

### Step 6: Update reveal_password endpoint

The reveal endpoint needs hybrid handling since it adds decrypted values:

```python
# api/src/routers/passwords.py - reveal_password function

@router.get("/{password_id}/reveal", response_model=PasswordReveal)
async def reveal_password(
    org_id: UUID,
    password_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> PasswordReveal:
    """Get a password with the decrypted password value."""
    password_repo = PasswordRepository(db)
    password = await password_repo.get_by_id_and_org(password_id, org_id)

    if not password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Password not found",
        )

    # Decrypt secrets
    decrypted_password = decrypt_secret(password.password_encrypted)
    decrypted_totp = None
    if password.totp_secret_encrypted:
        decrypted_totp = decrypt_secret(password.totp_secret_encrypted)

    logger.info(
        f"Password revealed: {password.name}",
        extra={"password_id": str(password.id), "org_id": str(org_id), "user_id": str(current_user.user_id)},
    )

    # Build response with decrypted values
    return PasswordReveal(
        **PasswordPublic.model_validate(password).model_dump(),
        password=decrypted_password,
        totp_secret=decrypted_totp,
    )
```

### Step 7: Run all password tests

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/ -k "password" -v
```

Expected: PASS

### Step 8: Commit

```bash
cd /Users/jack/GitHub/gocovi-docs/api
git add src/models/contracts/password.py src/routers/passwords.py tests/unit/models/test_base_contracts.py
git commit -m "$(cat <<'EOF'
refactor(passwords): use model_validate with computed has_totp field

PasswordPublic now uses @computed_field for has_totp derivation.
totp_secret_encrypted is read from ORM but excluded from JSON output.
PasswordReveal uses hybrid approach for decrypted values.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Migrate ConfigurationPublic (Joined Fields)

**Files:**
- Modify: `api/src/models/contracts/configuration.py`
- Modify: `api/src/routers/configurations.py`

### Step 1: Update ConfigurationPublic contract

Configuration has joined relationship fields (`configuration_type_name`, `configuration_status_name`) that don't come directly from ORM attributes. We need a custom approach.

```python
# api/src/models/contracts/configuration.py - ConfigurationPublic section

from uuid import UUID

from pydantic import Field, field_serializer

from src.models.contracts.base import PublicEntityBase


class ConfigurationPublic(PublicEntityBase):
    """Configuration public response model."""

    configuration_type_id: UUID | None = None
    configuration_status_id: UUID | None = None
    name: str
    serial_number: str | None = None
    asset_tag: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    notes: str | None = None
    interfaces: list = Field(default_factory=list)

    # Joined fields - populated separately
    configuration_type_name: str | None = None
    configuration_status_name: str | None = None

    @field_serializer("configuration_type_id", "configuration_status_id")
    def serialize_optional_uuid(self, v: UUID | None) -> str | None:
        """Serialize optional UUID fields to strings."""
        return str(v) if v else None
```

### Step 2: Update router helper function

The Configuration router needs a helper that combines model_validate with joined fields:

```python
# api/src/routers/configurations.py

def _configuration_to_public(config: Configuration) -> ConfigurationPublic:
    """Convert Configuration ORM model to public response with joined names."""
    result = ConfigurationPublic.model_validate(config)
    # Add joined relationship names
    result.configuration_type_name = config.configuration_type.name if config.configuration_type else None
    result.configuration_status_name = config.configuration_status.name if config.configuration_status else None
    return result
```

### Step 3: Run tests

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/integration/test_configurations.py -v
```

Expected: PASS

### Step 4: Commit

```bash
cd /Users/jack/GitHub/gocovi-docs/api
git add src/models/contracts/configuration.py src/routers/configurations.py
git commit -m "$(cat <<'EOF'
refactor(configurations): use model_validate with joined field handling

ConfigurationPublic inherits from PublicEntityBase with additional
UUID serializer for FK fields. Joined names populated post-validation.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Migrate CustomAssetPublic (Keep Helper Functions)

CustomAsset is special - it has encrypted password fields that require filtering/decryption through service functions. The existing `_to_public` and `_to_reveal` helpers are appropriate and should be **kept** but simplified.

**Files:**
- Modify: `api/src/models/contracts/custom_asset.py`
- Modify: `api/src/routers/custom_assets.py`

### Step 1: Update CustomAssetPublic contract

```python
# api/src/models/contracts/custom_asset.py - CustomAssetPublic section

from uuid import UUID

from pydantic import Field, field_serializer

from src.models.contracts.base import PublicEntityBase


class CustomAssetPublic(PublicEntityBase):
    """Custom asset public response model (password fields filtered)."""

    custom_asset_type_id: UUID
    values: dict[str, Any]  # password fields excluded by helper

    @field_serializer("custom_asset_type_id")
    def serialize_type_uuid(self, v: UUID) -> str:
        """Serialize custom_asset_type_id to string."""
        return str(v)


class CustomAssetReveal(PublicEntityBase):
    """Custom asset reveal response model (password fields decrypted)."""

    custom_asset_type_id: UUID
    values: dict[str, Any]  # includes decrypted password fields

    @field_serializer("custom_asset_type_id")
    def serialize_type_uuid(self, v: UUID) -> str:
        """Serialize custom_asset_type_id to string."""
        return str(v)
```

### Step 2: Simplify router helper functions

```python
# api/src/routers/custom_assets.py

def _to_public(
    asset: CustomAsset,
    type_fields: list[FieldDefinition],
) -> CustomAssetPublic:
    """Convert ORM model to public response (password fields filtered)."""
    result = CustomAssetPublic.model_validate(asset)
    result.values = filter_password_fields(type_fields, asset.values)
    return result


def _to_reveal(
    asset: CustomAsset,
    type_fields: list[FieldDefinition],
) -> CustomAssetReveal:
    """Convert ORM model to reveal response (password fields decrypted)."""
    result = CustomAssetReveal.model_validate(asset)
    result.values = decrypt_password_fields(type_fields, asset.values)
    return result
```

### Step 3: Run tests

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest tests/integration/test_custom_assets.py -v
pytest tests/unit/test_custom_assets.py -v
```

Expected: PASS

### Step 4: Commit

```bash
cd /Users/jack/GitHub/gocovi-docs/api
git add src/models/contracts/custom_asset.py src/routers/custom_assets.py
git commit -m "$(cat <<'EOF'
refactor(custom-assets): use model_validate with values post-processing

CustomAssetPublic/Reveal inherit from PublicEntityBase.
Helper functions retained for password field filtering/decryption.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Final Verification

### Step 1: Run full test suite

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pytest
```

Expected: All tests pass

### Step 2: Run type checking

```bash
cd /Users/jack/GitHub/gocovi-docs/api
pyright
```

Expected: No errors

### Step 3: Run linting

```bash
cd /Users/jack/GitHub/gocovi-docs/api
ruff check .
```

Expected: No errors

### Step 4: Manual API verification

Start the API and verify responses:

```bash
cd /Users/jack/GitHub/gocovi-docs/api
# Start the API (adjust command as needed)
uvicorn src.main:app --reload
```

Test each endpoint type:
1. GET location - verify `is_enabled` field is correct
2. GET password - verify `has_totp` computed correctly
3. GET configuration - verify type/status names present
4. GET custom-asset - verify password fields filtered

### Step 5: Final commit

```bash
cd /Users/jack/GitHub/gocovi-docs/api
git add .
git commit -m "$(cat <<'EOF'
docs: complete model_validate simplification

All *Public response models now use model_validate() instead of
manual field-by-field construction. This prevents silent field
omission bugs like the is_enabled issue.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Verification Checklist

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] `pyright` reports no errors
- [ ] `ruff check` reports no errors
- [ ] `is_enabled=False` correctly returned in API responses
- [ ] UUID fields serialize to strings in JSON
- [ ] `metadata` field populated from `metadata_` ORM attribute
- [ ] `has_totp` computed correctly for passwords
- [ ] Configuration type/status names included
- [ ] Custom asset password fields filtered in public responses

---

## Rollback Plan

Each entity migration is independent. If issues arise:

1. Revert the specific entity's contract and router files
2. The manual construction pattern still works
3. `git revert <commit>` for atomic rollback
