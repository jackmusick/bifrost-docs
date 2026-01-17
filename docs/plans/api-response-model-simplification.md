# API Response Model Simplification Plan

## Status: NOT STARTED

## Problem Statement

Both `gocovi-docs` and `bifrost-api` construct API responses field-by-field:

```python
# Current pattern (error-prone, 15+ lines)
return PasswordPublic(
    id=str(password.id),
    organization_id=str(password.organization_id),
    name=password.name,
    username=password.username,
    url=password.url,
    notes=password.notes,
    has_totp=bool(password.totp_secret_encrypted),
    metadata=password.metadata_ if isinstance(password.metadata_, dict) else {},
    is_enabled=password.is_enabled,  # ← This was missing, causing all Switches to show "Enabled"
    created_at=password.created_at,
    updated_at=password.updated_at,
)
```

**Bug found:** `is_enabled` was omitted from every router → Pydantic used default `True` → all Switch toggles showed "Enabled" regardless of actual state.

## Why This Wasn't Done Originally

1. **Manual construction seemed simpler** - just map fields one by one, no Pydantic magic needed
2. **SQLAlchemy reserves `metadata`** - ORM models use `metadata_` as workaround, requires manual mapping
3. **UUID-to-string was copy-pasted** - easier than learning Pydantic serializers
4. **It worked until it didn't** - this bug exposed the fragility after months of use

## Goal

Replace manual field-by-field construction with:

```python
# Target pattern (1 line, no bugs)
return PasswordPublic.model_validate(password)
```

---

## Blockers to Direct `model_validate()` Usage

| Issue | ORM Model | Pydantic Model | Solution |
|-------|-----------|----------------|----------|
| Field naming | `metadata_` | `metadata` | `validation_alias="metadata_"` |
| UUID output | `UUID` | `str` (in JSON) | `field_serializer` |
| Computed fields | `totp_secret_encrypted` | `has_totp: bool` | `@computed_field` |
| Sensitive exclusion | `password_encrypted` | (not in model) | Don't declare field |

---

## Implementation Plan

### Phase 1: Create Base Infrastructure

#### 1.1 Create `PublicEntityBase` class

**File:** `api/src/models/contracts/base.py` (NEW FILE)

```python
"""Base classes for API contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class PublicEntityBase(BaseModel):
    """
    Base class for all public API response models.

    Features:
    - Automatic UUID-to-string serialization
    - Automatic metadata_ → metadata field mapping
    - Common fields (id, org_id, is_enabled, timestamps)

    Usage:
        class PasswordPublic(PublicEntityBase):
            name: str
            username: str | None = None
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")

    @field_serializer("id", "organization_id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)
```

**Checklist:**
- [ ] Create file `api/src/models/contracts/base.py`
- [ ] Add `PublicEntityBase` class with:
  - [ ] `model_config = ConfigDict(from_attributes=True)`
  - [ ] `id: UUID` field
  - [ ] `organization_id: UUID` field
  - [ ] `is_enabled: bool = True` field
  - [ ] `created_at: datetime` field
  - [ ] `updated_at: datetime` field
  - [ ] `metadata: dict = Field(default_factory=dict, validation_alias="metadata_")`
  - [ ] `@field_serializer("id", "organization_id")` for UUID→str
- [ ] Add to `api/src/models/contracts/__init__.py`

#### 1.2 Add Unit Tests for Base Class

**File:** `api/tests/unit/models/test_base_contracts.py` (NEW FILE)

**Checklist:**
- [ ] Create test file
- [ ] Test UUID serialization: `id: UUID` → JSON `"id": "uuid-string"`
- [ ] Test metadata alias: ORM `metadata_` → JSON `"metadata": {...}`
- [ ] Test from_attributes works with mock ORM object
- [ ] Test missing fields use defaults (is_enabled=True, metadata={})

---

### Phase 2: Migrate Entity Models

For each entity, follow this checklist:

#### 2.1 LocationPublic (Simplest - start here)

**File:** `api/src/models/contracts/location.py`

**Current:**
```python
class LocationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    name: str
    notes: str | None
    metadata: dict = Field(default_factory=dict)
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
```

**Target:**
```python
from .base import PublicEntityBase

class LocationPublic(PublicEntityBase):
    """Location response model."""
    name: str
    notes: str | None = None
```

**Checklist:**
- [ ] Import `PublicEntityBase` from `.base`
- [ ] Change `LocationPublic` to inherit from `PublicEntityBase`
- [ ] Remove redundant fields (id, organization_id, is_enabled, created_at, updated_at, metadata)
- [ ] Keep only entity-specific fields (name, notes)
- [ ] Verify `LocationCreate` and `LocationUpdate` unchanged (they don't inherit base)

**Router:** `api/src/routers/locations.py`

**Current:**
```python
def _to_public(location: Location) -> LocationPublic:
    return LocationPublic(
        id=str(location.id),
        organization_id=str(location.organization_id),
        name=location.name,
        notes=location.notes,
        metadata=location.metadata_ if isinstance(location.metadata_, dict) else {},
        is_enabled=location.is_enabled,
        created_at=location.created_at,
        updated_at=location.updated_at,
    )
```

**Target:**
```python
def _to_public(location: Location) -> LocationPublic:
    return LocationPublic.model_validate(location)
```

**Checklist:**
- [ ] Update `_to_public()` helper to use `model_validate()`
- [ ] Remove manual field mapping
- [ ] Run `pytest api/tests/ -k location` to verify
- [ ] Manually test location detail page Switch toggle

---

#### 2.2 DocumentPublic

**File:** `api/src/models/contracts/document.py`

**Target:**
```python
from .base import PublicEntityBase

class DocumentPublic(PublicEntityBase):
    """Document response model."""
    name: str
    description: str | None = None
    file_path: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
```

**Checklist:**
- [ ] Import `PublicEntityBase` from `.base`
- [ ] Change `DocumentPublic` to inherit from `PublicEntityBase`
- [ ] Remove redundant fields inherited from base
- [ ] Keep only entity-specific fields

**Router:** `api/src/routers/documents.py`

**Checklist:**
- [ ] Find all `DocumentPublic(...)` constructions
- [ ] Replace with `DocumentPublic.model_validate(doc)`
- [ ] Run `pytest api/tests/ -k document`
- [ ] Manually test document detail page Switch toggle

---

#### 2.3 ConfigurationPublic

**File:** `api/src/models/contracts/configuration.py`

**Target:**
```python
from .base import PublicEntityBase

class ConfigurationPublic(PublicEntityBase):
    """Configuration response model."""
    configuration_type_id: str | None = None
    configuration_status_id: str | None = None
    name: str
    serial_number: str | None = None
    asset_tag: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    notes: str | None = None
    interfaces: list = Field(default_factory=list)

    # Joined fields (not from ORM directly)
    configuration_type_name: str | None = None
    configuration_status_name: str | None = None
```

**Note:** Has foreign key IDs that need UUID→str serialization. Add to `field_serializer`:

```python
@field_serializer("id", "organization_id", "configuration_type_id", "configuration_status_id")
def serialize_uuid(self, v: UUID | None) -> str | None:
    return str(v) if v else None
```

**Checklist:**
- [ ] Import `PublicEntityBase` from `.base`
- [ ] Change `ConfigurationPublic` to inherit from `PublicEntityBase`
- [ ] Add FK UUID fields to serializer OR handle in class
- [ ] Handle joined fields (`configuration_type_name`, `configuration_status_name`) - these come from relationships, not direct ORM attributes
- [ ] May need custom `model_validate()` call or post-processing for joined fields

**Router:** `api/src/routers/configurations.py`

**Checklist:**
- [ ] Update `_configuration_to_public()` helper
- [ ] Handle joined fields (type_name, status_name) separately if needed
- [ ] Run `pytest api/tests/ -k configuration`
- [ ] Manually test configuration detail page Switch toggle

---

#### 2.4 CustomAssetPublic

**File:** `api/src/models/contracts/custom_asset.py`

**Target:**
```python
from .base import PublicEntityBase

class CustomAssetPublic(PublicEntityBase):
    """Custom asset response model."""
    asset_type_id: str
    name: str
    values: dict = Field(default_factory=dict)

    # Joined
    asset_type_name: str | None = None
```

**Checklist:**
- [ ] Import `PublicEntityBase` from `.base`
- [ ] Inherit from base, keep entity-specific fields
- [ ] Handle `asset_type_id` UUID serialization
- [ ] Handle joined `asset_type_name`

**Router:** `api/src/routers/custom_assets.py`

**Checklist:**
- [ ] Update `_to_public()` helper
- [ ] Handle joined field
- [ ] Run tests
- [ ] Manual verification

---

#### 2.5 OrganizationPublic

**File:** `api/src/models/contracts/organization.py`

**Note:** Organization doesn't have `organization_id` (it IS the org). May need separate base or override.

**Target:**
```python
class OrganizationPublic(BaseModel):
    """Organization response model - special case, no org_id."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")

    @field_serializer("id")
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)
```

**Checklist:**
- [ ] Organization is special - no `organization_id` field
- [ ] Either: don't inherit from `PublicEntityBase`, OR create `PublicOrgBase` without org_id
- [ ] Update router to use `model_validate()`
- [ ] Run tests
- [ ] Manual verification

---

#### 2.6 PasswordPublic (Most Complex - do last)

**File:** `api/src/models/contracts/password.py`

**Complexity:** Has computed field `has_totp` derived from `totp_secret_encrypted`.

**Target:**
```python
from pydantic import Field, computed_field
from .base import PublicEntityBase

class PasswordPublic(PublicEntityBase):
    """Password response model (without sensitive data)."""
    name: str
    username: str | None = None
    url: str | None = None
    notes: str | None = None

    # Read from ORM but exclude from JSON output (for computed field)
    totp_secret_encrypted: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def has_totp(self) -> bool:
        """Whether this password has TOTP configured."""
        return bool(self.totp_secret_encrypted)
```

**Checklist:**
- [ ] Import `PublicEntityBase` and `computed_field`
- [ ] Inherit from base
- [ ] Add `totp_secret_encrypted` with `exclude=True` (reads from ORM, not in JSON)
- [ ] Add `@computed_field` for `has_totp`
- [ ] Verify `password_encrypted` is NOT declared (auto-excluded)

**Router:** `api/src/routers/passwords.py`

**Checklist:**
- [ ] Replace all 4 `PasswordPublic(...)` constructions with `model_validate()`
- [ ] Verify `PasswordReveal` still works (different model, needs password decryption)
- [ ] Run `pytest api/tests/ -k password`
- [ ] Manual test: toggle Switch, refresh, verify state persists

---

### Phase 3: Handle PasswordReveal Special Case

The `/reveal` endpoint returns decrypted sensitive data. It can't use pure `model_validate()`.

**File:** `api/src/models/contracts/password.py`

```python
class PasswordReveal(PasswordPublic):
    """Password response with decrypted values."""
    password: str  # Decrypted password
    totp_secret: str | None = None  # Decrypted TOTP secret (optional)
    totp_code: str | None = None  # Current 6-digit code
    totp_time_remaining: int | None = None  # Seconds until code expires
```

**Router pattern:**
```python
@router.get("/{password_id}/reveal")
async def reveal_password(...) -> PasswordReveal:
    password = await repo.get_by_id_and_org(password_id, org_id)

    # Start with base fields
    data = PasswordReveal.model_validate(password).model_dump()

    # Add decrypted sensitive fields
    data["password"] = decrypt_secret(password.password_encrypted)

    if password.totp_secret_encrypted:
        totp_secret = decrypt_secret(password.totp_secret_encrypted)
        data["totp_secret"] = totp_secret
        data["totp_code"] = generate_totp_code(totp_secret)
        data["totp_time_remaining"] = 30 - (int(time.time()) % 30)

    return PasswordReveal(**data)
```

**Checklist:**
- [ ] Update `PasswordReveal` to inherit from `PasswordPublic`
- [ ] Add TOTP computed fields (code, time_remaining)
- [ ] Update reveal endpoint to use hybrid approach
- [ ] Test reveal endpoint returns correct TOTP data

---

### Phase 4: Cleanup and Verification

#### 4.1 Remove Dead Code

**Checklist:**
- [ ] Delete helper functions like `_to_public()` if now single-line
- [ ] Remove any `# type: ignore` comments that were working around this
- [ ] Check for any remaining manual `PasswordPublic(...)` constructions

#### 4.2 Run Full Test Suite

```bash
cd api
pytest
pyright
ruff check .
```

**Checklist:**
- [ ] `pytest` passes 100%
- [ ] `pyright` has zero errors
- [ ] `ruff check` has zero errors

#### 4.3 Manual Verification

**Checklist:**
- [ ] Password detail page: Toggle Switch to Disabled → Refresh → Still Disabled
- [ ] Location detail page: Same test
- [ ] Configuration detail page: Same test
- [ ] Document detail page: Same test
- [ ] Custom Asset detail page: Same test
- [ ] Organization page: Same test
- [ ] List pages: "Show Disabled" filter works correctly

---

## Success Criteria

### Code Quality
- [ ] No manual `*Public(id=str(...), ...)` constructions remain
- [ ] All public models use `model_validate()` or inherit pattern
- [ ] `PublicEntityBase` handles common fields DRY

### Functionality
- [ ] All Switch toggles bind to state correctly
- [ ] List filtering by `is_enabled` works
- [ ] TOTP reveal shows code + time remaining
- [ ] All existing tests pass

### Maintainability
- [ ] Adding a new field to an entity = add to model only (not every router)
- [ ] No field can be "forgotten" (pattern prevents it)

---

## Estimated Effort

| Phase | Tasks | Time |
|-------|-------|------|
| Phase 1 | Base class + tests | 1 hour |
| Phase 2.1 | LocationPublic | 30 min |
| Phase 2.2 | DocumentPublic | 30 min |
| Phase 2.3 | ConfigurationPublic | 45 min (joined fields) |
| Phase 2.4 | CustomAssetPublic | 30 min |
| Phase 2.5 | OrganizationPublic | 30 min (special case) |
| Phase 2.6 | PasswordPublic | 1 hour (computed field) |
| Phase 3 | PasswordReveal | 30 min |
| Phase 4 | Cleanup + verify | 1 hour |
| **Total** | | **~6.5 hours** |

---

## Rollback Plan

If issues arise mid-implementation:
1. Each entity migration is independent - can rollback one without affecting others
2. Manual construction pattern still works - just verbose
3. Git revert to pre-migration commit if needed

---

## Future Work

After this refactor succeeds in gocovi-docs:
- [ ] Apply same pattern to bifrost-api
- [ ] Consider shared package for base classes if both apps need identical patterns
