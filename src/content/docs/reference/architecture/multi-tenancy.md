---
title: Multi-Tenant Architecture
description: How Bifrost implements multi-tenancy with complete organization isolation, data partitioning, and secure resource sharing
---

# Multi-Tenant Architecture

Bifrost is built with multi-tenancy at its core, allowing a single platform instance to serve multiple organizations with complete data isolation and security.

## Table of Contents

- [Multi-Tenancy Model](#multi-tenancy-model)
- [Tenant Isolation](#tenant-isolation)
- [Data Partitioning](#data-partitioning)
- [Access Control](#access-control)
- [Configuration Isolation](#configuration-isolation)
- [Secrets & Credentials](#secrets--credentials)
- [Resource Management](#resource-management)
- [Monitoring & Auditing](#monitoring--auditing)
- [Scaling Considerations](#scaling-considerations)

## Multi-Tenancy Model

Bifrost uses a **shared infrastructure, isolated data** model:

```
┌──────────────────────────────────────────────────────┐
│         Shared Bifrost Platform Instance              │
│                                                       │
│  ┌──────────────────────────────────────────────────┐ │
│  │         Azure Functions Runtime (Shared)          │ │
│  │  • HTTP/Queue/Timer triggers                     │ │
│  │  • Workflow execution engine                     │ │
│  │  • API layer                                     │ │
│  └──────────────────────────────────────────────────┘ │
│                        │                               │
│  ┌─────────────┬───────┼────────┬──────────┐          │
│  │             │       │        │          │          │
│  ↓             ↓       ↓        ↓          ↓          │
│ ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌──────┐      │
│ │Org A │ │Org B │ │ Org C  │ │Org D │ │Org N │ ...  │
│ │Data  │ │Data  │ │ Data   │ │Data  │ │Data  │      │
│ │      │ │      │ │        │ │      │ │      │      │
│ │(Iso- │ │(Iso- │ │(Isola-│ │(Iso- │ │(Iso-│      │
│ │lated)│ │lated)│ │ ted)  │ │lated)│ │lated)│      │
│ └──────┘ └──────┘ └────────┘ └──────┘ └──────┘      │
│                                                       │
│  Shared Data Layer:                                  │
│  • Azure Tables (organization-partitioned)           │
│  • Azure Files (org-specific mounts)                 │
│  • Azure Key Vault (secret isolation)                │
└──────────────────────────────────────────────────────┘
```

**Key characteristics:**

1. **Single Platform** - One Bifrost instance serves all organizations
2. **Isolated Data** - Each organization's data is completely isolated
3. **Shared Infrastructure** - Cost-efficient shared compute and storage
4. **Automatic Scaling** - Handles growth from 1 to 10,000+ organizations
5. **Multi-Region Ready** - Can be deployed across regions

## Tenant Isolation

### Data Isolation Guarantees

Every API request must include the organization ID in headers:

```bash
curl -H "X-Organization-Id: my-org-abc123" \
     -H "x-functions-key: ..." \
     https://api.bifrost.io/api/workflows/hello_world
```

The organization ID is used to **filter all data access**:

```python
# Example: Getting user data
async def get_users(org_id: str, user_id: str):
    """Get user by ID (org-scoped)."""
    # Can ONLY access user if org_id matches
    user = await users_repo.get(
        org_id=org_id,
        row_key=user_id
    )
    # Raises NotFound if org_id doesn't match
    return user
```

### Isolation at Storage Layer

Azure Tables provides natural partitioning by organization:

```
Table: organizations
│
├─ PartitionKey: org-abc123, RowKey: config
├─ PartitionKey: org-abc123, RowKey: user-1
├─ PartitionKey: org-abc123, RowKey: user-2
│
├─ PartitionKey: org-xyz789, RowKey: config
├─ PartitionKey: org-xyz789, RowKey: user-1
├─ PartitionKey: org-xyz789, RowKey: user-2
```

**All queries are scoped:**

```python
# Query respects PartitionKey (org_id)
# Only returns entities for that organization
query = f"PartitionKey eq '{org_id}'"
entities = table.query_entities(query)
```

### Azure Files Isolation

Each organization has isolated file storage:

```
Azure Files Share: /workspace

/workspace/
├─ org-abc123/           # Organization A
│  ├─ workflows/
│  ├─ data/
│  └─ uploads/
│
├─ org-xyz789/           # Organization B
│  ├─ workflows/
│  ├─ data/
│  └─ uploads/
```

Workflows can only access their organization's files:

```python
# In a workflow, file paths are automatically scoped
workspace_path = "/workspace"  # Actually org-abc123/

# Cannot access other org files
# /workspace/../org-xyz789/data  ← BLOCKED (path traversal)
```

## Data Partitioning

### Partition Strategy

Bifrost uses **organization-based partitioning** across all storage:

| Entity Type      | Partition Key | Row Key               | Purpose           |
| ---------------- | ------------- | --------------------- | ----------------- |
| **Organization** | `org-{id}`    | `config`              | Org metadata      |
| **User**         | `org-{id}`    | `user-{user_id}`      | User records      |
| **Execution**    | `org-{id}`    | `exec-{execution_id}` | Execution results |
| **Config**       | `org-{id}`    | `config-{key}`        | Org settings      |
| **OAuth**        | `org-{id}`    | `oauth-{provider}`    | OAuth tokens      |

### Query Patterns

```python
# Get all users in organization
query = f"PartitionKey eq '{org_id}' and RowKey.startswith('user-')"
users = table.query_entities(query)

# Get specific execution
entity = table.get_entity(
    partition_key=org_id,
    row_key=f"exec-{execution_id}"
)

# Get all executions (paginated)
query = f"PartitionKey eq '{org_id}' and RowKey.startswith('exec-')"
# Yields all execution records for this org only
```

## Access Control

### Organization Context

Every function receives the organization ID from headers:

```python
from functions.shared.openapi_decorators import openapi_handler

@openapi_handler(...)
async def get_user(req: func.HttpRequest) -> func.HttpResponse:
    # Extract org_id from headers (mandatory)
    org_id = req.headers.get("X-Organization-Id")
    if not org_id:
        return func.HttpResponse("Missing X-Organization-Id", status_code=400)

    # Get user ID from request
    user_id = req.params.get("user_id")

    # ALL data access is scoped to org_id
    user = await repository.get(org_id=org_id, user_id=user_id)
    return func.JsonResponse(user.dict())
```

### Authorization Patterns

**Pattern 1: Ownership Check**

```python
# Verify resource belongs to organization
async def update_workflow(org_id: str, workflow_name: str, code: str):
    # Check if workflow exists in this org
    existing = await workflows_repo.get(org_id, workflow_name)
    if not existing:
        raise WorkflowNotFound(f"Workflow {workflow_name} not found")

    # If found, it MUST belong to this org (by design)
    # Update it
    await workflows_repo.update(org_id, workflow_name, code)
```

**Pattern 2: Implicit Scoping**

```python
# Retrieve is automatically scoped
# If org_id doesn't match, returns NotFound (not forbidden)
async def get_execution(org_id: str, execution_id: str):
    result = await executions_repo.get(org_id, execution_id)
    # Returns None if:
    # 1. Execution doesn't exist, OR
    # 2. Execution belongs to different org
    return result
```

**Pattern 3: Bulk Operations**

```python
# All bulk operations scoped to org
async def list_users(org_id: str, skip: int = 0, limit: int = 50):
    # ONLY returns users from this org
    users = await users_repo.list(
        org_id=org_id,
        skip=skip,
        limit=limit
    )
    return users
```

## Configuration Isolation

### Organization Settings

Each organization has isolated configuration:

```python
# Configuration is per-organization
class OrganizationConfig(BaseModel):
    id: str                    # org-abc123
    name: str                  # "My Company"
    created_at: datetime       # Org creation time
    settings: Dict[str, Any]   # Org-specific settings
    roles: List[Role]          # Org-specific roles
```

**Settings example:**

```json
{
  "id": "org-abc123",
  "name": "Acme Corp",
  "settings": {
    "workflow_timeout_seconds": 300,
    "max_concurrent_executions": 10,
    "enable_oauth_auto_refresh": true,
    "custom_domain": "api.acmecorp.io"
  },
  "roles": [
    { "name": "admin", "permissions": ["*"] },
    { "name": "user", "permissions": ["workflows:read", "workflows:execute"] },
    { "name": "viewer", "permissions": ["workflows:read"] }
  ]
}
```

### Per-Organization Workflows

Each organization can have custom workflows:

```
/workspace/
├─ org-abc123/
│  └─ workflows/
│     ├─ onboard_user.py           # Custom for Acme
│     ├─ provision_license.py
│     └─ sync_ad.py
│
├─ org-xyz789/
│  └─ workflows/
│     ├─ hello_world.py            # Different for ExampleCo
│     └─ custom_automation.py
```

Workflows are loaded per-organization:

```python
async def load_workflow(org_id: str, workflow_name: str) -> str:
    """Load workflow code for organization."""
    # Path is org-specific
    path = f"/workspace/{org_id}/workflows/{workflow_name}.py"
    return read_file(path)

# Different orgs can have different implementations
# of the same workflow name
```

## Secrets & Credentials

### OAuth Token Isolation

OAuth tokens are stored per-organization in Key Vault:

```
Key Vault Structure:

org-abc123-graph-access-token       # Token for Acme
org-abc123-graph-refresh-token
org-abc123-halopsa-api-key

org-xyz789-graph-access-token       # Token for ExampleCo
org-xyz789-graph-refresh-token
org-xyz789-halopsa-api-key
```

Token access is scoped:

```python
async def get_oauth_token(org_id: str, provider: str) -> str:
    """Get OAuth token (org-scoped)."""
    # Token name includes org_id
    token_name = f"{org_id}-{provider}-access-token"
    token = await key_vault.get_secret(token_name)
    return token
```

### API Key Management

Each organization can have custom API keys:

```json
{
  "org-abc123": {
    "external_api_keys": {
      "zendesk": "abc123...",
      "slack": "xoxb-...",
      "stripe": "sk_live_..."
    }
  }
}
```

**Org-scoped access:**

```python
async def get_api_key(org_id: str, service: str) -> str:
    """Get service API key for organization."""
    # Only accessible to that org
    entity = await config_repo.get(
        org_id=org_id,
        config_key=f"api-key-{service}"
    )
    return entity.value
```

## Resource Management

### Quota Management

Organizations have configurable quotas:

```json
{
  "org-abc123": {
    "quotas": {
      "workflows": 100,
      "workspace_quota_gb": 100,
      "tmp_quota_gb": 50,
      "concurrent_executions": 10,
      "api_calls_per_minute": 1000
    }
  }
}
```

**Enforced at execution time:**

```python
async def execute_workflow(org_id: str, workflow_name: str):
    """Execute with quota enforcement."""
    org_config = await get_org_config(org_id)
    quotas = org_config.quotas

    # Check concurrent executions
    running = await count_running_executions(org_id)
    if running >= quotas.concurrent_executions:
        raise QuotaExceeded(f"Max {quotas.concurrent_executions} concurrent")

    # Execute workflow...
```

### Storage Quotas

Azure Files quotas are set per-organization:

```bash
# Each org's share has its own quota
az storage share create \
  --name "org-abc123" \
  --quota 100  # 100 GB

az storage share create \
  --name "org-xyz789" \
  --quota 50   # 50 GB
```

Files are mounted at execution time with the organization's quota enforced.

## Monitoring & Auditing

### Per-Organization Logging

All events are logged with organization context:

```python
# Execution log includes org_id
{
    "timestamp": "2024-10-24T10:30:00Z",
    "org_id": "org-abc123",
    "execution_id": "exec-123",
    "user_id": "user-456",
    "workflow_name": "onboard_user",
    "status": "success",
    "duration_ms": 1234,
    "input": {...},
    "output": {...}
}
```

**Query per-organization logs:**

```bash
# Get Application Insights logs for specific org
az monitor app-insights query \
  --app <app-insights-name> \
  --analytics-query "
    customEvents
    | where tostring(customDimensions.org_id) == 'org-abc123'
    | order by timestamp desc
  "
```

### Organization Audit Trail

All modifications are audited:

```python
{
    "timestamp": "2024-10-24T10:30:00Z",
    "org_id": "org-abc123",
    "user_id": "user-456",
    "action": "workflow.updated",
    "resource": "workflow:onboard_user",
    "changes": {
        "code": "... diff ...",
        "description": "Added validation"
    }
}
```

## Scaling Considerations

### Storage Scaling

As organizations grow, the platform automatically handles:

```
┌─────────────────────────────────────────┐
│  Single Azure Tables Account             │
│                                          │
│  Automatic scaling based on:             │
│  • Partition size (org has too much data)│
│  • Request rate (too many queries)       │
│  • Storage size (total data too large)   │
│                                          │
│  Results in:                             │
│  • More partitions                       │
│  • Better distribution                   │
│  • Improved latency                      │
└─────────────────────────────────────────┘
```

### Organization Count Scaling

**Small scale (1-100 orgs):**

- Single Azure Functions instance
- Single Azure Tables account
- Shared Key Vault

**Medium scale (100-1000 orgs):**

- Auto-scaling Azure Functions (10+ instances)
- Single Azure Tables account (handles easily)
- Shared Key Vault with appropriate access policies

**Large scale (1000+ orgs):**

- Multi-region Azure Functions
- Azure Tables with geo-replication
- Multi-region Key Vault or separate vaults per region

### Cost Implications

Multi-tenancy reduces per-organization costs:

**Single-tenant model:**

- Function App per org: $5/month × 1000 orgs = $5,000/month
- Storage per org: $2/month × 1000 orgs = $2,000/month
- **Total: $7,000+/month**

**Multi-tenant model:**

- Shared Function App: $50/month (multiple instances)
- Shared Storage: $5/month (scales to thousands of orgs)
- **Total: $55/month** for same scale

## Best Practices

1. **Always require org_id in headers**

   ```bash
   # Must include in every API call
   -H "X-Organization-Id: org-abc123"
   ```

2. **Never hardcode organization data**

   ```python
   # Bad: assumes org
   ORG_ID = "org-abc123"

   # Good: from headers
   org_id = req.headers.get("X-Organization-Id")
   ```

3. **Scope all data access**

   ```python
   # Every query filters by org_id
   users = await repo.list(org_id=org_id)
   ```

4. **Audit sensitive operations**

   ```python
   # Log when org data is accessed or modified
   logger.info(f"Accessed config for {org_id}")
   ```

5. **Test isolation**
   ```python
   # Tests verify org isolation
   def test_user_cannot_access_other_org_data():
       # Ensure org A can't see org B's data
   ```

## Related Documentation

- [Platform Architecture](./overview.md) - System design overview
- [Security Model](/reference/architecture/security/) - Authentication and authorization

---

**For managing multiple organizations**, see [Organization Management](/reference/api/organizations/) documentation.
