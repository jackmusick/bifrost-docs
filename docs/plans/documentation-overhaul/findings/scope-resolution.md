# Scope Resolution System - Findings

This document provides a comprehensive technical review of the Scope Resolution system in the Bifrost platform.

## Source of Truth

### Overview

The Bifrost platform implements a **two-tier scoping model** that determines resource visibility and access:

1. **Global Scope** - Platform-wide resources accessible to all organizations (organization_id IS NULL)
2. **Organization Scope** - Resources specific to one organization, isolated from others

The key innovation is **cascade scoping**: when a workflow or SDK operation looks for a resource by name/key, it first checks the organization-specific scope, then falls back to global.

---

## 1. Scope Resolution Architecture

### Two-Tier Model

| Scope | Description | Use Case |
|-------|-------------|----------|
| **Global** | `organization_id IS NULL` | Platform defaults, shared services, fallback configurations |
| **Organization** | `organization_id = {uuid}` | Org-specific settings, OAuth connections, custom configurations |

### Cascade Scoping Behavior

When looking up resources by name/key (not by ID), the system follows this resolution order:

```
1. Check: Does this org have "resource_name"?
   └─ YES → Return org-specific resource
   └─ NO  → Continue to step 2

2. Check: Is there a global "resource_name"?
   └─ YES → Return global resource (fallback)
   └─ NO  → Return None / default value
```

**Important**: ID lookups do NOT cascade - IDs are globally unique.

### Key Files - Backend

| File | Purpose |
|------|---------|
| `/Users/jack/GitHub/bifrost/api/src/core/org_filter.py` | Core organization filtering logic - `resolve_org_filter()` and `resolve_target_org()` |
| `/Users/jack/GitHub/bifrost/api/src/repositories/org_scoped.py` | OrgScopedRepository base class with cascade scoping implementation |
| `/Users/jack/GitHub/bifrost/api/bifrost/config.py` | SDK config module - scope resolution for config operations |
| `/Users/jack/GitHub/bifrost/api/bifrost/integrations.py` | SDK integrations module - scope resolution for integration operations |
| `/Users/jack/GitHub/bifrost/api/bifrost/_context.py` | Context module - provides `get_default_scope()` |
| `/Users/jack/GitHub/bifrost/api/src/routers/cli.py` | CLI router - implements `_get_cli_org_id()` for SDK scope resolution |
| `/Users/jack/GitHub/bifrost/api/src/routers/config.py` | Config router with ConfigRepository using OrgScopedRepository |

---

## 2. Organization Filter Types

The `org_filter.py` module defines four filter types for different access patterns:

```python
class OrgFilterType(Enum):
    ALL = "all"           # No filter, show everything (superuser only)
    GLOBAL_ONLY = "global"  # Only org_id IS NULL
    ORG_ONLY = "org_only"   # Only specific org, NO global fallback
    ORG_PLUS_GLOBAL = "org" # Specific org + global records (cascade)
```

### Filter Resolution Rules

| User Type | Scope Parameter | Result |
|-----------|-----------------|--------|
| Superuser | omitted/None | ALL - see everything |
| Superuser | "global" | GLOBAL_ONLY - only global records |
| Superuser | "{uuid}" | ORG_ONLY - only that org (no fallback) |
| Org User | any value | ORG_PLUS_GLOBAL - their org + global (cascade) |
| Org User (no org) | any value | GLOBAL_ONLY - edge case |

---

## 3. SDK Scope Parameter

All SDK modules (config, integrations, tables, knowledge) accept a `scope` parameter:

```python
async def get(key: str, scope: str | None = None) -> Any
```

**Scope parameter values:**
- `None` (default): Use execution context's organization
- Org UUID string: Target specific organization
- `"global"`: Access platform-level resources directly (bypass cascade)

### Scope Resolution in SDK

```python
# From bifrost/config.py
def _resolve_scope(scope: str | None) -> str | None:
    """Resolve effective scope - explicit override or default from context."""
    if scope is not None:
        return scope
    return get_default_scope()  # Returns context org_id or None
```

---

## 4. OrgScopedRepository Pattern

The `OrgScopedRepository` base class provides standardized cascade scoping:

### Cascade Scope Query

```python
def _apply_cascade_scope(self, query):
    """Apply cascade scoping to a query."""
    if self.org_id is not None:
        # WHERE (organization_id = org_id OR organization_id IS NULL)
        return query.where(
            or_(
                model.organization_id == self.org_id,
                model.organization_id.is_(None),
            )
        )
    # Global-only: WHERE organization_id IS NULL
    return query.where(model.organization_id.is_(None))
```

### Get Operation with Cascade

For name/key lookups:
1. Try org-specific lookup first (if org_id is set)
2. If not found, fall back to global (org_id IS NULL)
3. For ID lookups, find directly (no cascade - IDs are unique)

---

## 5. Workflow Execution Scope

Workflows execute in the context of the calling user/organization:

```python
from bifrost import workflow, context

@workflow(name="example")
async def example():
    # context.org_id - The organization context for this execution
    # context.scope - Either org_id string or "GLOBAL"
    # context.is_global_scope - Boolean check

    # SDK operations automatically use context.org_id
    config_value = await config.get("setting")  # Uses context scope
```

### Execution Context Properties

| Property | Type | Description |
|----------|------|-------------|
| `context.org_id` | str \| None | Organization UUID or None |
| `context.scope` | str | "GLOBAL" or org UUID |
| `context.is_global_scope` | bool | True if scope == "GLOBAL" |
| `context.organization` | Organization \| None | Full org object |

---

## 6. Per-Module Scoping Behavior

### Config Module

- Cascade scoping: org-specific configs shadow global configs
- `config.get("key")` checks org first, then global
- `config.list()` returns merged view (org + global)

### Integrations Module

- Cascade with **config merging**: defaults + org overrides
- `integrations.get("name")` returns merged configuration
- OAuth tokens can be org-specific or shared

### Tables Module

- Three-level scoping: Organization, Application, Global
- Tables can be scoped to apps within orgs
- `scope="global"` creates platform-wide tables

### Knowledge Module

- Organization-scoped documents by default
- `fallback=True` (default) searches both org and global
- Global documents visible to all organizations

---

## 7. Organization Hierarchy (Not Implemented)

**Note**: The current codebase does NOT implement organization hierarchy (parent/child relationships). Each organization is a flat, isolated tenant.

---

## Documentation State

### Existing Docs

| File | Status |
|------|--------|
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/core-concepts/scopes.mdx` | **Exists** - Basic conceptual overview |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/sdk-reference/sdk/config-module.mdx` | **Exists** - Has scope parameter docs |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/sdk-reference/sdk/integrations-module.mdx` | **Exists** - Has scope parameter docs |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/sdk-reference/sdk/context-api.mdx` | **Exists** - Documents context.org_id, is_global_scope |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/sdk-reference/sdk/tables-module.mdx` | **Exists** - Documents three-level scoping |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/sdk-reference/sdk/knowledge-module.mdx` | **Exists** - Documents fallback parameter |

### Gaps Identified

1. **Cascade Scoping Not Explained**: The core concept of "org-specific first, then global fallback" is mentioned briefly but not explained in detail. The scopes.mdx file shows the resolution order but doesn't explain:
   - Why cascade scoping exists (avoid duplicating global resources per-org)
   - When cascade applies (name/key lookups) vs when it doesn't (ID lookups)
   - How superusers vs org users experience different filter types

2. **OrgFilterType Not Documented**: The four filter types (ALL, GLOBAL_ONLY, ORG_ONLY, ORG_PLUS_GLOBAL) are not documented. This is important for understanding API behavior:
   - Why superusers with scope="{uuid}" don't see global fallback
   - Why org users always get cascade regardless of scope parameter

3. **Config Merging Not Documented**: The integrations module does **config merging** (defaults + org overrides), not just cascade scoping. This is different from config module's shadowing behavior.

4. **Tables Three-Level Scoping Underdocumented**: Tables have Organization, Application, and Global scopes. The documentation mentions this but doesn't explain:
   - How app scoping interacts with org scoping
   - When to use app-scoped vs org-scoped tables

5. **SDK `scope` Parameter Inconsistency**: Different modules document the scope parameter differently:
   - config-module.mdx: Clear three options documented
   - integrations-module.mdx: Clear three options documented
   - tables-module.mdx: Uses different wording (`None=context org, "global"=global, UUID=specific org`)
   - knowledge-module.mdx: Uses same pattern

6. **No Practical Examples**: The scopes.mdx core concepts doc lacks practical examples showing:
   - Setting up global defaults with org overrides
   - When to use `scope="global"` explicitly
   - Common patterns for multi-tenant workflows

7. **context.scope vs SDK scope**: The relationship between `context.scope` (in workflow execution) and SDK scope parameter is not clearly explained. They serve different purposes:
   - `context.scope` is read-only execution context
   - SDK `scope` parameter is for explicit override

8. **Typo in scopes.mdx**: Line 21 has "oranization" instead of "organization"

### Recommended Actions

1. **Rewrite core-concepts/scopes.mdx** with:
   - Clear explanation of cascade scoping concept
   - Diagram showing resolution order
   - Table of OrgFilterType values and when each applies
   - Practical examples for common patterns
   - Fix typo

2. **Add "Scoping Deep Dive" how-to guide**:
   - Setting up global defaults
   - Creating org-specific overrides
   - Understanding when cascade applies
   - Superuser vs org user behavior differences

3. **Standardize SDK module scope documentation**:
   - Use consistent wording across all modules
   - Add note about cascade behavior to each module
   - Clarify config merging vs shadowing for integrations

4. **Add Tables Scoping Section**:
   - Explain three-level hierarchy (org > app > global)
   - Document app scoping use cases
   - Show examples of app-scoped tables

5. **Clarify context.scope vs SDK scope**:
   - Add section to context-api.mdx explaining the difference
   - Show examples of when to use each

---

## 8. Testing References

### Unit Tests

- `/Users/jack/GitHub/bifrost/api/tests/unit/routers/test_scoped_lookups.py` - Scoped lookup behavior
- `/Users/jack/GitHub/bifrost/api/tests/integration/engine/test_sdk_scoping.py` - SDK scoping tests

### Integration Tests

- `/Users/jack/GitHub/bifrost/api/tests/integration/api/test_tables.py` - Tables scoping
- `/Users/jack/GitHub/bifrost/api/tests/e2e/api/test_scope_execution.py` - Scope execution tests
