# Remove User-Organization Scoping for V1

## Summary

Remove `user_organizations` table and API key org-scoping. V1 design is "all users see all organizations" - these structures are unused and causing confusion.

---

## Phase 1: Database Migration

Create migration file: `api/alembic/versions/20260113_005000_remove_user_org_scoping.py`

- [ ] Drop foreign key constraint `api_keys_organization_id_fkey` from `api_keys`
- [ ] Drop index `ix_api_keys_organization_id` from `api_keys`
- [ ] Drop column `organization_id` from `api_keys`
- [ ] Drop table `user_organizations`
- [ ] Write downgrade function that recreates both

---

## Phase 2: Delete Files

- [ ] Delete `api/src/models/orm/user_organization.py`

---

## Phase 3: Update ORM Models

### `api/src/models/orm/api_key.py`
- [ ] Remove `organization_id: Mapped[UUID]` column (line 28)
- [ ] Remove `from src.models.orm.organization import Organization` TYPE_CHECKING import
- [ ] Remove `organization: Mapped["Organization"]` relationship (line 43)
- [ ] Remove `Index("ix_api_keys_organization_id", "organization_id")` from `__table_args__` (line 54)

### `api/src/models/orm/user.py`
- [ ] Remove `user_organizations` relationship
- [ ] Remove `UserOrganization` TYPE_CHECKING import if present

### `api/src/models/orm/organization.py`
- [ ] Remove `user_organizations` relationship
- [ ] Remove `api_keys` relationship
- [ ] Remove `UserOrganization` and `APIKey` TYPE_CHECKING imports if present

### `api/src/models/orm/__init__.py`
- [ ] Remove `from src.models.orm.user_organization import UserOrganization`
- [ ] Remove `UserOrganization` from `__all__`

---

## Phase 4: Update Contracts

### `api/src/models/contracts/api_key.py`
- [ ] Remove `organization_id` field from `ApiKeyCreate` (if present)
- [ ] Remove `organization_id` field from `ApiKeyPublic`
- [ ] Remove `organization_id` field from `ApiKeyCreated`

---

## Phase 5: Update Repositories

### `api/src/repositories/organization.py`
- [ ] Delete `get_user_organizations()` method (lines 38-53)
- [ ] Delete `add_user_to_organization()` method (lines 55-71)
- [ ] Delete `remove_user_from_organization()` method (lines 73-95)
- [ ] Delete `is_user_in_organization()` method (lines 97-114)
- [ ] Remove `UserOrganization` import (line 13)

### `api/src/repositories/user.py`
- [ ] Delete `get_user_organizations()` method (line 80+)
- [ ] Remove any `UserOrganization` imports

---

## Phase 6: Update Auth System

### `api/src/core/auth.py`
- [ ] Remove `organization_id: UUID | None` from `UserPrincipal` dataclass (line 42)
- [ ] Remove comment about org_id on line 41
- [ ] In `_authenticate_api_key()`: remove `organization_id=api_key_obj.organization_id` from UserPrincipal construction (line 142)
- [ ] In `get_current_user_optional()`: remove `org_id` extraction from JWT (lines 219-228)
- [ ] In `get_current_user_optional()`: remove validation requiring org_id for non-admin roles (lines 231-236)
- [ ] In `get_current_user_optional()`: remove `organization_id=org_id` from UserPrincipal construction (line 241)
- [ ] Update `ExecutionContext` if it references `user.organization_id`

---

## Phase 7: Update Routers - Remove Membership Checks

### `api/src/routers/passwords.py`
- [ ] Delete `_verify_org_membership()` function (lines 41-53)
- [ ] Remove call to `_verify_org_membership()` in endpoints
- [ ] Remove `OrganizationRepository` import if no longer needed

### `api/src/routers/configurations.py`
- [ ] Delete `is_user_in_organization()` check (line 47)
- [ ] Remove associated imports

### `api/src/routers/documents.py`
- [ ] Delete `is_user_in_organization()` check (line 53)
- [ ] Remove associated imports

### `api/src/routers/locations.py`
- [ ] Delete `is_user_in_organization()` check (line 51)
- [ ] Remove associated imports

### `api/src/routers/custom_assets.py`
- [ ] Delete `is_user_in_organization()` check (line 61)
- [ ] Remove associated imports

### `api/src/routers/attachments.py`
- [ ] Delete `is_user_in_organization()` check (line 49)
- [ ] Remove associated imports

### `api/src/routers/relationships.py`
- [ ] Delete `is_user_in_organization()` check (line 40)
- [ ] Remove associated imports

### `api/src/routers/organizations.py`
- [ ] Delete `is_user_in_organization()` check (line 268)
- [ ] Delete `add_user_to_organization()` call (line 92)
- [ ] Remove associated imports

### `api/src/routers/search.py`
- [ ] Delete `is_user_in_organization()` checks (lines 96, 266)
- [ ] Delete `get_user_organizations()` calls (lines 105, 277)
- [ ] Replace with `org_repo.get_all()` if listing orgs is needed
- [ ] Remove associated imports

---

## Phase 8: Update Routers - Remove User-Org Association

### `api/src/routers/auth.py`
- [ ] Delete `get_user_organizations()` call (line 184)
- [ ] Delete `get_user_organizations()` call (line 287)
- [ ] Remove `org_id` from JWT token data construction (lines 192-198)
- [ ] Delete `add_user_to_organization()` call (line 421)
- [ ] Remove associated imports

### `api/src/routers/passkeys.py`
- [ ] Delete `get_user_organizations()` call (line 305)
- [ ] Remove `org_id` from JWT token data if present
- [ ] Remove associated imports

### `api/src/routers/oauth_sso.py`
- [ ] Delete `add_user_to_organization()` call (line 373)
- [ ] Delete `get_user_organizations()` call (line 395)
- [ ] Remove `org_id` from JWT token data if present
- [ ] Remove associated imports

### `api/src/routers/api_keys.py`
- [ ] Remove org context requirement check (lines 79-84)
- [ ] Remove `organization_id` from APIKey construction (line 93)
- [ ] Remove `organization_id` from ApiKeyCreated response (line 112)
- [ ] Remove `organization_id` from ApiKeyPublic response (line 46)
- [ ] Remove logging of `org_id` (line 105)

### `api/src/main.py`
- [ ] Delete `add_user_to_organization()` call (line 137)
- [ ] Remove associated imports

---

## Phase 9: Update Frontend

### `client/src/stores/auth.store.ts`
- [ ] Remove `organizationId` or `organization_id` from user state type
- [ ] Remove any references to user org context

### `client/src/hooks/useApiKeys.ts` (or equivalent)
- [ ] Remove `organization_id` from API key types

### `client/src/pages/settings/ApiKeys.tsx` (or equivalent)
- [ ] Remove organization column from API key list table
- [ ] Remove any org context from key creation

### General client search
- [ ] Search for `organization_id` in auth/user context and remove
- [ ] Keep `organization_id` for entity-level associations (passwords belong to orgs, etc.)

---

## Phase 10: Update Tests

- [ ] Remove/update tests in `api/tests/` that use `UserOrganization`
- [ ] Remove/update tests for `is_user_in_organization()`
- [ ] Remove/update tests for `add_user_to_organization()`
- [ ] Remove/update tests for `get_user_organizations()`
- [ ] Update API key tests to not expect `organization_id`
- [ ] Update auth tests to not expect `org_id` in JWT

---

## Phase 11: Verification

- [ ] Run `alembic upgrade head` - migration applies cleanly
- [ ] Run `pytest` - all tests pass
- [ ] Run `pyright` - no type errors
- [ ] Run `ruff check` - no lint errors
- [ ] Manual test: create API key without org context
- [ ] Manual test: use API key to access any org's data
- [ ] Manual test: login flow works without user_organizations
- [ ] Manual test: register flow works without user_organizations
- [ ] Manual test: OAuth flow works without user_organizations
