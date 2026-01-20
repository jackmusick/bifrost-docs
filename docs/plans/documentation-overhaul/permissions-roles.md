# Permissions & Roles

## Source of Truth (Codebase Review)

_Completed by Codebase Agent - 2026-01-20_

### Current Features

#### 1. User Types and Authentication

**File: `/Users/jack/GitHub/bifrost/api/src/core/auth.py`**

The system has three user types:

| User Type | `is_superuser` | `org_id` | Description |
|-----------|----------------|----------|-------------|
| Platform Admin | `true` | UUID | Superuser in an organization, can manage all platform features |
| Regular Org User | `false` | UUID | Standard user scoped to their organization |
| System Account | `true` | `null` | Internal system user for global scope operations |

**Key Classes:**
- `UserPrincipal` (dataclass): Represents authenticated user from JWT claims
  - Properties: `is_platform_admin`, `is_system_account`, `has_role()`, `has_any_role()`
- `ExecutionContext` (dataclass): Contains user, org_id scope, and db session
  - Properties: `scope`, `is_global_scope`, `is_platform_admin`

**Dependency Injection Types:**
```python
CurrentUser = Annotated[UserPrincipal, Depends(get_current_user)]
CurrentActiveUser = Annotated[UserPrincipal, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[UserPrincipal, Depends(get_current_superuser)]
Context = Annotated[ExecutionContext, Depends(get_execution_context)]
```

#### 2. Role System

**ORM Models - File: `/Users/jack/GitHub/bifrost/api/src/models/orm/users.py`**

The `Role` model is a simple entity with:
- `id: UUID` - Primary key
- `name: str` - Role name (max 100 chars)
- `description: str | None` - Optional description
- `is_active: bool` - Soft delete flag
- `created_by: str` - Email of creator

**Important:** Roles are **globally defined** - they exist at the platform level, not per-organization. Organization scoping happens at the entity-role junction level.

**Role Assignment Junction Tables:**

| Junction Table | File | Purpose |
|----------------|------|---------|
| `UserRole` | `/api/src/models/orm/users.py` | Links users to roles |
| `FormRole` | `/api/src/models/orm/forms.py` | Links forms to roles |
| `AgentRole` | `/api/src/models/orm/agents.py` | Links agents to roles |
| `AppRole` | `/api/src/models/orm/app_roles.py` | Links applications to roles |
| `WorkflowRole` | `/api/src/models/orm/workflow_roles.py` | Links workflows to roles |

All junction tables share the pattern:
- Composite primary key: `(entity_id, role_id)`
- `assigned_by: str` - Who made the assignment
- `assigned_at: datetime` - When assigned
- `CASCADE` delete on both foreign keys

#### 3. Access Level Enum

**File: `/Users/jack/GitHub/bifrost/api/src/models/enums.py`**

Three entities support `access_level`:

```python
class FormAccessLevel(str, Enum):
    AUTHENTICATED = "authenticated"
    ROLE_BASED = "role_based"

class AgentAccessLevel(str, Enum):
    AUTHENTICATED = "authenticated"
    ROLE_BASED = "role_based"

class AppAccessLevel(str, Enum):
    AUTHENTICATED = "authenticated"
    ROLE_BASED = "role_based"
```

- `authenticated`: Any logged-in user in scope can access
- `role_based`: User must have a role assigned to the entity

#### 4. OrgScopedRepository Pattern

**File: `/Users/jack/GitHub/bifrost/api/src/repositories/org_scoped.py`**

This is the **primary authorization mechanism** in Bifrost. It replaces the older `AuthorizationService`.

**Constructor:**
```python
def __init__(
    self,
    session: AsyncSession,
    org_id: UUID | None,          # Organization scope
    user_id: UUID | None = None,  # For role checks
    is_superuser: bool = False,   # Bypass role checks
):
```

**Public Methods:**
- `get(**filters)` - Single entity lookup with access check
- `can_access(**filters)` - Same as get, raises `AccessDeniedError` if not found
- `list(**filters)` - Multiple entities with cascade + role filtering

**Access Control Logic:**

```
1. ID Lookups (get(id=...)):
   - IDs are globally unique, no cascade needed
   - Superusers: Can access any entity by ID
   - Regular users: Must be in scope (their org or global) + pass role check

2. Name/Key Lookups (get(name=...), get(key=...)):
   - Names can exist in multiple orgs
   - Step 1: Try org-specific (WHERE organization_id = org_id)
   - Step 2: Fall back to global (WHERE organization_id IS NULL)
   - Cascade applies to ALL users including superusers

3. Role Check (_can_access_entity):
   - Superusers: Always pass
   - No role_table configured: Pass (cascade-only)
   - access_level="authenticated": Pass
   - access_level="role_based": Check role membership
```

**Repository Implementations:**

| Repository | File | Role Table | Entity ID Column |
|------------|------|------------|------------------|
| `FormRepository` | `/api/src/repositories/forms.py` | `FormRole` | `form_id` |
| `WorkflowRepository` | `/api/src/repositories/workflows.py` | `WorkflowRole` | `workflow_id` |
| `AgentRepository` | `/api/src/repositories/agents.py` | `AgentRole` | `agent_id` |
| `DataProviderRepository` | `/api/src/repositories/data_providers.py` | None | - |
| `IntegrationRepository` | `/api/src/repositories/integrations.py` | None | - |
| `KnowledgeRepository` | `/api/src/repositories/knowledge.py` | None | - |

#### 5. API Endpoint Authorization

**Pattern 1: Platform Admin Only (CurrentSuperuser)**

Used for administrative operations:
```python
@router.get("")
async def list_roles(user: CurrentSuperuser, db: DbSession):
    # Only platform admins can access
```

**File: `/Users/jack/GitHub/bifrost/api/src/routers/roles.py`** - All role CRUD is superuser-only
**File: `/Users/jack/GitHub/bifrost/api/src/routers/users.py`** - All user management is superuser-only

**Pattern 2: Context-Based with Repository**

Used for entity access with org scoping:
```python
@router.get("/{slug}")
async def get_application(slug: str, ctx: Context, user: CurrentUser):
    repo = ApplicationRepository(
        ctx.db,
        org_id=ctx.org_id,
        user_id=ctx.user.user_id,
        is_superuser=ctx.user.is_superuser,
    )
    return await repo.can_access(slug=slug)
```

#### 6. Workflow Role Auto-Sync

**File: `/Users/jack/GitHub/bifrost/api/src/services/workflow_role_service.py`**

When forms/agents are saved with role-based access, their roles are automatically synced to referenced workflows:

**Form Workflows Extracted:**
- `form.workflow_id` - Main execution workflow
- `form.launch_workflow_id` - Pre-execution workflow
- `form_fields.data_provider_id` - Dynamic field data providers

**Agent Workflows Extracted:**
- `agent.tools` - Workflow IDs used as tools

**Sync Functions:**
```python
async def sync_form_roles_to_workflows(db, form, fields, assigned_by)
async def sync_agent_roles_to_workflows(db, agent, assigned_by)
async def sync_app_roles_to_workflows(db, app_id, assigned_by)  # Now a no-op
```

#### 7. Organization Model

**File: `/Users/jack/GitHub/bifrost/api/src/models/orm/organizations.py`**

Organizations are flat (no hierarchy):
- `id: UUID` - Primary key
- `name: str` - Organization name
- `domain: str | None` - Optional domain
- `is_active: bool` - Active status
- `is_provider: bool` - Whether this is the MSP provider org
- `settings: dict` - JSONB configuration

**Key Relationship:** Users belong to exactly one organization via `User.organization_id`.

### Recent Changes

#### Repository Pattern Authorization (Major Refactor)

The codebase recently underwent a significant refactor to consolidate authorization:

**Deleted Services (now absorbed into `OrgScopedRepository`):**
- `api/src/services/authorization.py` - `AuthorizationService`
- `api/src/services/execution_auth.py` - `ExecutionAuthService`

**Key Design Decisions:**
1. Authorization logic moved into repository layer
2. `can_access()` method provides consistent access check pattern
3. `AccessDeniedError` exception for authorization failures
4. Superuser bypass at repository level, not endpoint level
5. Cascade scoping for name lookups (org-specific > global)

**File: `/Users/jack/GitHub/bifrost/api/src/core/exceptions.py`**
```python
class AccessDeniedError(Exception):
    """Raised when a user does not have access to an entity."""
```

### Key Concepts to Document

1. **User Types**
   - Platform Admin vs Regular User vs System Account
   - JWT claims and token structure
   - Organization membership model

2. **Role System**
   - Global role definitions
   - Role assignment to users
   - Role assignment to entities (forms, agents, apps, workflows)
   - The `access_level` enum (authenticated vs role_based)

3. **OrgScopedRepository Pattern**
   - How to use `get()`, `can_access()`, `list()`
   - Cascade scoping behavior (org-specific > global)
   - Role-based access control configuration
   - When superusers bypass checks

4. **Entity Access Control**
   - Forms: `FormAccessLevel` + `FormRole`
   - Agents: `AgentAccessLevel` + `AgentRole`
   - Applications: `AppAccessLevel` + `AppRole`
   - Workflows: `access_level` + `WorkflowRole`
   - Tables/Configs/Knowledge: Cascade-only (no RBAC)

5. **Workflow Role Sync**
   - Automatic role propagation from forms/agents to workflows
   - Why this exists (workflows are execution implementation details)

6. **API Authorization Patterns**
   - `CurrentSuperuser` for admin-only endpoints
   - `Context` + Repository for entity access
   - When to use which pattern

7. **Request Flow Diagrams**
   - Direct user access flow
   - SDK/Workflow execution flow
   - System account execution flow

---

## Documentation State (Docs Review)

_To be completed by Docs Agent_

### Existing Docs
<!-- What docs currently exist, file paths -->

### Gaps Identified
<!-- What's missing, outdated, or inaccurate -->

### Recommended Actions
<!-- Specific actions to take -->
