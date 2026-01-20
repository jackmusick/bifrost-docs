# Permissions and Roles - Codebase Review Findings

## Source of Truth

This document captures the current state of the permissions and roles system in the Bifrost platform based on codebase analysis conducted on 2026-01-20.

---

## 1. Overview

The Bifrost platform uses a multi-layered access control system combining:

1. **User Types** - Platform Admin (superuser) vs Regular Org User
2. **Organization Scoping** - Cascade scoping for multi-tenant isolation
3. **Role-Based Access Control** - Roles assigned to users, then to entities (forms, agents, apps, workflows)
4. **Access Levels** - Per-entity setting controlling whether access requires authentication only or specific roles

### Key Files

| File | Purpose |
|------|---------|
| `/Users/jack/GitHub/bifrost/api/src/repositories/org_scoped.py` | OrgScopedRepository base class with cascade scoping and role checks |
| `/Users/jack/GitHub/bifrost/api/src/models/orm/users.py` | User, Role, UserRole ORM models |
| `/Users/jack/GitHub/bifrost/api/src/models/enums.py` | Access level enums (FormAccessLevel, AgentAccessLevel, AppAccessLevel) |
| `/Users/jack/GitHub/bifrost/api/src/services/workflow_role_service.py` | Workflow role sync service |
| `/Users/jack/GitHub/bifrost/api/src/core/auth.py` | UserPrincipal and authentication |

---

## 2. User Types

### Platform Admin (Superuser)

Users with `is_superuser=True` are platform administrators:

```python
@dataclass
class UserPrincipal:
    user_id: UUID
    email: str
    organization_id: UUID | None  # None for system accounts
    is_superuser: bool = False    # Platform admin flag

    @property
    def is_platform_admin(self) -> bool:
        return self.is_superuser
```

**Platform Admin Capabilities:**
- Bypass role checks (but NOT cascade scoping for name lookups)
- Access all resources via ID lookup
- Create/manage users, roles, organizations
- Create/manage workflows, forms, agents, applications
- View DEBUG/TRACEBACK logs
- View execution variables and resource metrics
- Access stuck execution cleanup tools

### Regular Organization User

Users with `is_superuser=False` and `organization_id` set:

**Regular User Capabilities:**
- Access forms assigned to their roles (if `access_level=role_based`)
- Access forms in their org (if `access_level=authenticated`)
- View own execution history
- Submit forms they have access to
- Cannot create workflows, forms, agents, or applications
- Cannot access admin endpoints

### User Model

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID]
    email: Mapped[str]              # Unique
    name: Mapped[str | None]
    hashed_password: Mapped[str | None]  # None for OAuth-only users
    is_active: Mapped[bool]
    is_superuser: Mapped[bool]      # Platform admin flag
    is_verified: Mapped[bool]
    is_registered: Mapped[bool]
    mfa_enabled: Mapped[bool]
    organization_id: Mapped[UUID | None]  # NULL for system accounts
    # ... timestamps, relationships
```

---

## 3. Role System

### Role Definition

Roles are **globally defined** - they are NOT scoped to organizations:

```python
class Role(Base):
    __tablename__ = "roles"

    id: Mapped[UUID]
    name: Mapped[str]              # e.g., "HR", "Finance", "Approvers"
    description: Mapped[str | None]
    is_active: Mapped[bool]
    created_by: Mapped[str]
    # ... timestamps
```

**Key Design Decision:** Organization scoping happens at the **entity level** (forms, apps, agents), not on roles themselves. This allows a single role (e.g., "Finance") to be used across multiple organizations.

### User-Role Assignment

Users are assigned to roles via the `UserRole` junction table:

```python
class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID]      # FK to users
    role_id: Mapped[UUID]      # FK to roles
    assigned_by: Mapped[str]   # Who assigned this role
    assigned_at: Mapped[datetime]
```

### Entity-Role Assignment

Entities (forms, apps, agents, workflows) are assigned to roles via junction tables:

| Junction Table | Entity | Pattern |
|---------------|--------|---------|
| `FormRole` | Form | `form_id`, `role_id`, `assigned_by`, `assigned_at` |
| `AppRole` | Application | `app_id`, `role_id`, `assigned_by`, `assigned_at` |
| `AgentRole` | Agent | `agent_id`, `role_id`, `assigned_by`, `assigned_at` |
| `WorkflowRole` | Workflow | `workflow_id`, `role_id`, `assigned_by`, `assigned_at` |

---

## 4. Access Levels

Entities have an `access_level` field that controls how access is evaluated:

```python
class FormAccessLevel(str, Enum):
    AUTHENTICATED = "authenticated"  # Any authenticated user in scope
    ROLE_BASED = "role_based"        # User must have matching role

class AgentAccessLevel(str, Enum):
    AUTHENTICATED = "authenticated"
    ROLE_BASED = "role_based"

class AppAccessLevel(str, Enum):
    AUTHENTICATED = "authenticated"
    ROLE_BASED = "role_based"
```

### Access Control Flow

```
1. User requests entity (form, agent, app)
2. Check cascade scope (org-specific + global)
3. If access_level = "authenticated":
   - Any authenticated user in scope can access
4. If access_level = "role_based":
   - Check if user has any role assigned to the entity
   - Access granted only if role intersection exists
```

---

## 5. OrgScopedRepository Pattern

The `OrgScopedRepository` base class implements standardized organization scoping and role-based access control:

### Constructor

```python
class OrgScopedRepository(Generic[ModelT]):
    def __init__(
        self,
        session: AsyncSession,
        org_id: UUID | None,
        user_id: UUID | None = None,
        is_superuser: bool = False,
    ):
```

### Cascade Scoping

For name/key lookups, cascade scoping applies:
1. Try org-specific lookup first
2. Fall back to global (org_id=NULL)

```python
# org_id set: WHERE (organization_id = org_id OR organization_id IS NULL)
# org_id None: WHERE organization_id IS NULL
```

### Access Control Logic

```python
async def _can_access_entity(self, entity: ModelT) -> bool:
    # Superusers bypass role checks
    if self.is_superuser:
        return True

    # No role table configured - cascade scoping only
    if not self._has_role_table():
        return True

    # No access_level attribute - cascade scoping only
    if not self._has_access_level(entity):
        return True

    if access_level == "authenticated":
        return True

    if access_level == "role_based":
        return await self._check_role_access(entity)

    return False
```

### Role Check Implementation

```python
async def _check_role_access(self, entity: ModelT) -> bool:
    # Get user's role IDs
    user_roles = await get_user_role_ids(self.user_id)

    # Get entity's role IDs from junction table
    entity_roles = await get_entity_role_ids(entity.id)

    # Check intersection
    return any(role_id in entity_roles for role_id in user_roles)
```

---

## 6. Workflow Role Sync

When forms, agents, or apps are saved with role assignments, the `WorkflowRoleService` automatically syncs those roles to referenced workflows:

```python
async def sync_form_roles_to_workflows(form: Form):
    # Extract workflow IDs from:
    # - form.workflow_id (main execution workflow)
    # - form.launch_workflow_id (startup workflow)
    # - form_fields.data_provider_id (dynamic field data providers)

    # Get form's role IDs
    role_ids = await get_form_role_ids(form.id)

    # Assign roles to all referenced workflows (additive)
    await sync_entity_roles_to_workflows(workflow_ids, role_ids)
```

This is **additive** - it never removes existing roles from workflows.

---

## 7. API Endpoints for Role Management

### Roles CRUD (Admin Only)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/roles` | POST | Create role |
| `GET /api/roles` | GET | List roles |
| `GET /api/roles/{id}` | GET | Get role |
| `PUT /api/roles/{id}` | PUT | Update role |
| `DELETE /api/roles/{id}` | DELETE | Delete role |

### Role Assignments (Admin Only)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/roles/{id}/users` | POST | Assign users to role |
| `GET /api/roles/{id}/users` | GET | Get users in role |
| `DELETE /api/roles/{id}/users/{user_id}` | DELETE | Remove user from role |
| `POST /api/roles/{id}/forms` | POST | Assign forms to role |
| `GET /api/roles/{id}/forms` | GET | Get forms in role |

### User Permissions (Admin Only)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/users/{id}/roles` | GET | Get user's roles |
| `GET /api/users/{id}/forms` | GET | Get forms accessible to user |

---

## 8. E2E Test Coverage

The permissions system has comprehensive E2E tests in `/Users/jack/GitHub/bifrost/api/tests/e2e/api/test_permissions.py`:

### Test Classes

| Class | Description |
|-------|-------------|
| `TestOrgUserRestrictions` | Tests that org users cannot access admin operations |
| `TestOrgUserCapabilities` | Tests what org users CAN do |
| `TestOrgIsolation` | Tests cross-organization isolation |
| `TestPlatformAdminCapabilities` | Tests platform admin permissions |
| `TestRoleBasedFormAccess` | Tests role-based form access control |
| `TestAuthenticatedFormAccess` | Tests forms with authenticated access level |

### Key Test Scenarios

1. **Org user restrictions**: Cannot create roles, forms, users, or access admin endpoints
2. **Org isolation**: Users cannot see other org's resources, scope param ignored for non-superusers
3. **Role-based access**: Users with assigned roles can see forms, users without cannot
4. **Authenticated access**: Any org user can access forms with `authenticated` level

---

## Documentation State

### Existing Documentation

| File | Status |
|------|--------|
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/core-concepts/permissions.md` | Exists but simplified |

### Current Documentation Content

The existing `permissions.md` file covers:
- Platform Admins vs Regular Users (basic distinction)
- Custom Roles concept (creating and assigning roles)
- Using Roles with Forms (high-level workflow)
- Best Practices (start simple, descriptive names)

### Gaps Identified

| Gap | Priority | Description |
|-----|----------|-------------|
| **Missing: Access Levels** | High | No documentation of `authenticated` vs `role_based` access levels |
| **Missing: OrgScopedRepository** | Medium | No technical explanation of how cascade scoping works |
| **Missing: Workflow Role Sync** | Medium | No documentation that roles propagate from forms/agents to workflows |
| **Missing: Entity-Role Tables** | Low | No documentation of FormRole, AgentRole, AppRole, WorkflowRole |
| **Missing: API Reference** | High | No documentation of role management API endpoints |
| **Missing: Global Roles Design** | Medium | No explanation that roles are global, scoping is at entity level |
| **Outdated: User Types** | High | Missing System Account concept (org_id=NULL + is_superuser=True) |
| **Missing: Permission Test Coverage** | Low | No documentation of E2E permission tests for validation |

### Recommended Actions

1. **Update User Types Section**
   - Add System Account concept (org_id=NULL)
   - Document the auth model rules (valid combinations)
   - Add code examples from UserPrincipal

2. **Add Access Levels Section**
   - Document `authenticated` vs `role_based` access levels
   - Explain default behavior (role_based by default)
   - Show how to set access level when creating forms

3. **Add Technical Deep-Dive Section**
   - Document OrgScopedRepository pattern for developers
   - Explain cascade scoping (org-specific + global fallback)
   - Diagram the access control flow

4. **Add API Reference Section**
   - Document all role management endpoints
   - Include request/response examples
   - Note admin-only restrictions

5. **Add Workflow Role Sync Documentation**
   - Explain automatic role propagation
   - Document which entities sync to workflows
   - Note additive-only behavior

6. **Consider Restructuring**
   - Current doc is user-focused (how to use roles)
   - Consider splitting into:
     - User Guide: Creating and assigning roles
     - Developer Guide: Technical implementation details
     - API Reference: Endpoint documentation
