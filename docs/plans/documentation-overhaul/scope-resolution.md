# Scope Resolution

## Source of Truth (Codebase Review)

### Current Features

#### 1. Organization Scoping Model (Two-Tier)

Bifrost uses a two-tier scoping model where resources exist at either:
- **Global scope** (`organization_id = NULL`): Available to all organizations on the platform
- **Organization scope** (`organization_id = UUID`): Specific to one organization, isolated from others

**File References:**
- `/Users/jack/GitHub/bifrost/api/shared/docs/core-concepts/scopes.txt` - User-facing documentation
- `/Users/jack/GitHub/bifrost/api/src/models/orm/organizations.py` - Organization ORM model

#### 2. OrgScopedRepository Pattern (Core Mechanism)

The `OrgScopedRepository` is the foundational pattern for all organization-scoped data access. It provides:

**File:** `/Users/jack/GitHub/bifrost/api/src/repositories/org_scoped.py`

**Key Features:**
- **Cascade scoping**: Organization-specific entities take priority over global entities
- **Role-based access control (RBAC)**: For entities with role tables (forms, apps, agents, workflows)
- **Access level support**: `authenticated` (any user in scope) vs `role_based` (requires role assignment)

**Cascade Scoping Logic:**
```python
# For name/key lookups:
# 1. Try org-specific first (WHERE organization_id = org_id)
# 2. Fall back to global (WHERE organization_id IS NULL)
# 3. Check access permissions on found entity
```

**ID vs Name Lookup Behavior:**
- **ID lookups** (`get(id=...)`): IDs are globally unique, no cascade needed. Find entity directly and check access.
- **Name/key lookups** (`get(name=...)`, `get(key=...)`): Cascade scoping required since names can exist in multiple orgs.

**Superuser Behavior:**
- Superusers bypass role checks but **NOT** cascade scoping for name lookups
- This ensures correct entity resolution when the same name exists in multiple orgs

#### 3. Entity-Specific Repository Implementations

**With Role-Based Access Control:**
- `/Users/jack/GitHub/bifrost/api/src/repositories/forms.py` - `FormRepository` with `FormRole` table
- `/Users/jack/GitHub/bifrost/api/src/repositories/agents.py` - `AgentRepository` with `AgentRole` table
- `/Users/jack/GitHub/bifrost/api/src/repositories/workflows.py` - `WorkflowRepository` with `WorkflowRole` table

**Cascade-Only (No RBAC):**
- `TableRepository` - SDK-only, no direct user access
- `ConfigRepository` - SDK-only, no direct user access
- `IntegrationMappingRepository` - SDK-only, no direct user access

**Entity Configuration Table:**
| Entity | Role Table | Direct User Access | Notes |
|--------|------------|-------------------|-------|
| Form | `FormRole` | Yes | RBAC via roles, has `access_level` |
| Application | `AppRole` | Yes | RBAC via roles, has `access_level` |
| Agent | `AgentRole` | Yes | RBAC via roles, has `access_level` |
| Workflow | `WorkflowRole` | No (SDK only) | RBAC checked at execution start |
| Table | None | No (SDK only) | Cascade only, no RBAC |
| Config | None | No (SDK only) | Cascade only, no RBAC |
| IntegrationMapping | None | No (SDK only) | Cascade only, no RBAC |

#### 4. Organization Filter Helper

**File:** `/Users/jack/GitHub/bifrost/api/src/core/org_filter.py`

Provides consistent organization filtering logic for API endpoints.

**Filter Types (OrgFilterType enum):**
- `ALL`: No filter, show everything (superuser only)
- `GLOBAL_ONLY`: Only `organization_id IS NULL`
- `ORG_ONLY`: Only specific org, NO global fallback (platform admin selecting org)
- `ORG_PLUS_GLOBAL`: Specific org + global records (standard org users)

**Key Functions:**
- `resolve_org_filter()`: For list queries - determines how to filter based on user type
- `resolve_target_org()`: For write operations - determines target organization

#### 5. Workflow Execution Scope Resolution

**Files:**
- `/Users/jack/GitHub/bifrost/api/src/services/execution/engine.py` - Execution engine
- `/Users/jack/GitHub/bifrost/api/src/jobs/consumers/workflow_execution.py` - Consumer scope resolution
- `/Users/jack/GitHub/bifrost/api/src/routers/workflows.py` - API endpoint scope resolution
- `/Users/jack/GitHub/bifrost/api/tests/integration/engine/test_sdk_scoping.py` - Comprehensive tests

**Scope Resolution Rule (Critical):**
```python
# Rule: Org-scoped workflow uses workflow's org
# Rule: Global workflow uses caller's org
def resolve_execution_scope(workflow_org_id, caller_org_id):
    if workflow_org_id is not None:
        return workflow_org_id  # Org-scoped workflow
    return caller_org_id  # Global workflow or GLOBAL scope
```

**Scenarios:**
| Workflow Type | Caller Type | Execution Scope |
|---------------|-------------|-----------------|
| Org-scoped (org_id set) | Any caller | Workflow's organization |
| Global (org_id NULL) | Org user | Caller's organization |
| Global (org_id NULL) | Platform admin (no org) | GLOBAL scope |

This ensures data isolation - an org-scoped workflow always operates within its organization's context, regardless of who triggers it.

#### 6. ExecutionContext

**Files:**
- `/Users/jack/GitHub/bifrost/api/src/sdk/context.py` - ExecutionContext dataclass
- `/Users/jack/GitHub/bifrost/api/bifrost/_context.py` - ContextVar-based context propagation

**Key Properties:**
- `scope`: Either "GLOBAL" or organization UUID string
- `organization`: Organization object or None for GLOBAL scope
- `org_id`: Property that returns organization.id or None
- `is_global_scope`: Boolean property checking if scope == "GLOBAL"

**SDK Access:**
```python
from bifrost import context

@workflow
async def my_workflow():
    user = context.user_id
    org = context.org_id  # Returns None for GLOBAL scope
    config_value = await context.get_config("my_key")
```

#### 7. Config Resolution with Cascade

**File:** `/Users/jack/GitHub/bifrost/api/src/sdk/context.py` (get_config method)

The config system implements cascade scoping:
1. Check organization-specific config first
2. Fall back to global config if not found
3. Return default or raise KeyError

**Integration Config Cascade:**
**File:** `/Users/jack/GitHub/bifrost/api/src/repositories/integrations.py`

Integration mappings use cascade scoping where org-specific mappings override global mappings. The `get_config_for_mapping()` method merges integration defaults with org overrides.

### Recent Changes

Based on codebase analysis, the key recent implementations include:

1. **OrgScopedRepository consolidation**: Replaced separate `AuthorizationService` and `ExecutionAuthService` with unified repository pattern
2. **Superuser cascade behavior**: Superusers now use cascade scoping for name lookups (previously bypassed)
3. **Workflow execution scope resolution**: Org-scoped workflows now consistently use workflow's org regardless of caller
4. **OrgFilterType enum**: Standardized filtering options for admin interfaces

### Key Concepts to Document

1. **Two-Tier Scope Model**
   - Global vs Organization scope
   - When to use each scope
   - How entities inherit scope behavior

2. **Cascade Scoping Pattern**
   - Priority: org-specific > global
   - ID lookups vs name/key lookups
   - Superuser behavior (bypasses role checks, not cascade)

3. **Workflow Execution Scoping**
   - Org-scoped workflow behavior
   - Global workflow behavior
   - Data isolation guarantees
   - How SDK operations inherit execution scope

4. **Access Control Layers**
   - `access_level`: authenticated vs role_based
   - Role tables and junction tables
   - How repositories enforce access

5. **Organization Filter Types**
   - ALL, GLOBAL_ONLY, ORG_ONLY, ORG_PLUS_GLOBAL
   - When each is used
   - Superuser vs org user behavior

6. **SDK Context Propagation**
   - ContextVar mechanism
   - How workflows access scope
   - Config resolution with cascade

7. **Integration Mapping Scoping**
   - How integrations resolve for an org
   - Config merging (defaults + overrides)
   - OAuth token scoping

---

## Documentation State (Docs Review)

_To be completed by Docs Agent_

### Existing Docs
<!-- What docs currently exist, file paths -->

### Gaps Identified
<!-- What's missing, outdated, or inaccurate -->

### Recommended Actions
<!-- Specific actions to take -->
