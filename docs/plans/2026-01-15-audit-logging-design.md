# Audit Logging & Last Updated By - Design

## Overview

Two related features for tracking who did what in the platform:

1. **`last_updated_by`** - Show who last modified each core entity
2. **Audit logging** - Comprehensive trail of all actions for compliance, activity feeds, and debugging

## Scope

### `last_updated_by`

Add `updated_by_user_id` (FK to users) to 6 core business entities:
- Document
- Password
- Configuration
- Location
- CustomAsset
- Organization

### Audit Logging

Track:
- **Mutations** on all core entities (create, update, delete, activate, deactivate)
- **Views** on sensitive entities (Password only)
- **Auth events** (login, logout, login_failed, mfa_setup)
- **User management** (user_create, user_delete, user_update)

Retention: 1 year, cleaned up via daily scheduled job.

---

## Database Schema

### `last_updated_by` Columns

```sql
ALTER TABLE documents ADD COLUMN updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE passwords ADD COLUMN updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE configurations ADD COLUMN updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE locations ADD COLUMN updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE custom_assets ADD COLUMN updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE organizations ADD COLUMN updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
```

### `audit_logs` Table

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,  -- NULL for auth/system events

    -- What happened
    action VARCHAR(50) NOT NULL,  -- 'create', 'update', 'delete', 'view', 'login', 'logout', etc.
    entity_type VARCHAR(50) NOT NULL,  -- 'document', 'password', 'user', 'session', etc.
    entity_id UUID NOT NULL,

    -- Who did it
    actor_type VARCHAR(20) NOT NULL,  -- 'user', 'api_key', 'system'
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    actor_label VARCHAR(100),  -- 'embedding_indexer', 'cleanup_job', or IP address for failed logins

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_actor CHECK (
        (actor_type = 'user' AND actor_user_id IS NOT NULL) OR
        (actor_type = 'api_key' AND actor_api_key_id IS NOT NULL) OR
        (actor_type = 'system')
    )
);

CREATE INDEX idx_audit_logs_org_created ON audit_logs(organization_id, created_at DESC) WHERE organization_id IS NOT NULL;
CREATE INDEX idx_audit_logs_system_created ON audit_logs(created_at DESC) WHERE organization_id IS NULL;
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_actor_user ON audit_logs(actor_user_id) WHERE actor_user_id IS NOT NULL;
```

---

## Backend Implementation

### New Files

| File | Purpose |
|------|---------|
| `models/orm/audit_log.py` | SQLAlchemy model |
| `models/enums.py` | Add `AuditAction`, `ActorType` enums |
| `services/audit_service.py` | Core logging logic |
| `routers/audit.py` | API endpoints for querying |

### Audit Service

```python
class AuditService:
    async def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID,
        actor: UserPrincipal | APIKey | str,  # str for system label
        organization_id: UUID | None = None,
    ) -> None:
        # Fire-and-forget insert (non-blocking)
```

### Integration Points

| Location | Actions |
|----------|---------|
| Entity routers (create/update/delete endpoints) | `create`, `update`, `delete` |
| Password router (GET endpoint) | `view` |
| Auth router | `login`, `logout`, `login_failed`, `mfa_setup` |
| User router | `user_create`, `user_delete`, `user_update` |

---

## API Endpoints

### Query Endpoints

```
GET /api/organizations/{org_id}/audit-logs
    ?page=1
    &page_size=50
    &entity_type=password
    &action=view
    &actor_user_id=uuid
    &start_date=2024-01-01
    &end_date=2024-01-31

GET /api/audit-logs  (global - all orgs user has access to)
    ?organization_id=uuid  (optional filter)
    ...same filters as above
```

### Response Contract

```python
class AuditLogEntry(BaseModel):
    id: UUID
    organization_id: UUID | None
    organization_name: str | None  # Joined for display
    action: str
    entity_type: str
    entity_id: UUID
    entity_name: str | None  # Joined for display (doc title, config name, etc.)
    actor_type: str
    actor_user_id: UUID | None
    actor_display_name: str | None  # Joined: user email/name or API key name
    actor_label: str | None
    created_at: datetime

class AuditLogResponse(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
```

### Extended Entity Responses

Add to existing entity response contracts:

```python
updated_by_user_id: UUID | None
updated_by_user_name: str | None  # Joined for display
```

---

## Frontend Implementation

### New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `AuditLogPage` | `/pages/audit/` | Global audit view |
| `OrgAuditLogPage` | `/pages/organizations/[org]/audit/` | Org-scoped audit view |
| `AuditLogTable` | `/components/audit/` | Shared table component with filters |
| `AuditLogFilters` | `/components/audit/` | Date range, entity type, action, user filters |

### Navigation

- Global nav: "Audit Trail" link (shows all orgs)
- Org sidebar: "Audit Trail" link (shows org-specific)

### Table Columns

| Global View | Org View |
|-------------|----------|
| Timestamp | Timestamp |
| Organization | *(hidden)* |
| Action | Action |
| Entity Type | Entity Type |
| Entity Name | Entity Name |
| Actor | Actor |

### `last_updated_by` Display

Add to entity detail views:

```
Last updated by Jane Smith · 2 hours ago
```

---

## Retention & Cleanup

### Scheduled Job

```python
# jobs/audit_cleanup.py
async def cleanup_old_audit_logs():
    """Delete audit logs older than 1 year. Run daily via arq."""
    cutoff = datetime.utcnow() - timedelta(days=365)
    await db.execute(
        delete(AuditLog).where(AuditLog.created_at < cutoff)
    )
```

Register in arq worker to run at 3am daily.

---

## Implementation Estimate

| Task | Effort |
|------|--------|
| Database migration | 0.5 day |
| ORM model + enums | 0.25 day |
| Audit service | 0.5 day |
| Integration points (wire up routers) | 1 day |
| API endpoints (query + filters) | 0.5 day |
| Frontend (table, filters, pages, nav) | 1.5 days |
| `last_updated_by` display on views | 0.5 day |
| Cleanup job | 0.25 day |
| Testing | 1 day |

**Total: ~6 days**

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `updated_by` data type | User UUID (FK) | Referential integrity, enables joins |
| Entities with `last_updated_by` | 6 core business entities only | Auth/system entities rarely need this |
| View tracking | Passwords only | Balance between compliance and storage |
| Retention | 1 year | Standard compliance without runaway storage |
| Actor identification | Nullable FKs + actor_type enum | Clean FKs for users/API keys, flexibility for system |
| Audit detail level | Action only (no diffs) | Simple, can extend later |
| Organization scoping | Nullable org_id | Single table supports both org-scoped and auth events |
