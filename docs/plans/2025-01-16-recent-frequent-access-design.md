# Recently Accessed & Frequently Accessed Design

## Overview

Add two access tracking patterns to improve navigation:

- **Recently Accessed** - Per-user, shows the last N entities a user viewed
- **Frequently Accessed** - Per-organization, shows most viewed entities across all users (last 30 days)

## Requirements

### Recently Accessed
- Scoped to individual user
- Tracked via audit log `VIEW` action (server-side)
- All entity types: Organizations, Passwords, Configurations, Locations, Documents, Custom Assets
- Last N items (no time limit)
- 6 items on dashboard, 10 in header dropdown

### Frequently Accessed
- Scoped per organization (all users within that org)
- 30-day rolling window
- 6 items on org home page

## UI Locations

| Location | Type | Count | Content |
|----------|------|-------|---------|
| Header dropdown | Recent | 10 | All entity types, personal to user |
| Dashboard | Recent | 6 | Recent organizations (one row) |
| Dashboard | Recent | 6 | Recent entities (one row) |
| Organizations page | Recent | 6 | Recent orgs above the list |
| Org home page | Frequent | 6 | Popular entities in that org |

## Data Model

### Audit Log Enhancement

No new tables. Extend existing `audit_log` with `VIEW` action tracking.

**Where VIEW is logged (server-side):**
- `GET /api/passwords/{id}`
- `GET /api/configurations/{id}`
- `GET /api/locations/{id}`
- `GET /api/documents/{id}`
- `GET /api/custom-assets/{id}`
- `GET /api/organizations/{id}`

**Deduplication:**
- 60-second dedupe in audit service
- Skip logging if same user+entity viewed within last 60 seconds

**New Index:**
```sql
CREATE INDEX idx_audit_log_user_views
ON audit_log (actor_user_id, action, created_at DESC)
WHERE action = 'view';
```

## API Design

### New Endpoint: Recent Items

```
GET /api/me/recent?limit=10
```

**Response:**
```json
[
  {
    "entity_type": "password",
    "entity_id": "uuid",
    "organization_id": "uuid",
    "org_name": "Acme Corp",
    "name": "Admin Credentials",
    "viewed_at": "2025-01-16T10:30:00Z"
  }
]
```

**Query Logic:**
- Filter audit_log by `actor_user_id = current_user` and `action = 'view'`
- Get latest view per unique `(entity_type, entity_id)`
- Join to entity tables to get current name (excludes deleted entities)
- Filter by user's current permissions
- Order by `viewed_at` descending, limit to N

### Extended Endpoint: Organization with Frequently Accessed

```
GET /api/organizations/{org_id}?include=frequently_accessed
```

**Response (additional field):**
```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "frequently_accessed": [
    {
      "entity_type": "password",
      "entity_id": "uuid",
      "name": "Admin Credentials",
      "view_count": 47
    }
  ]
}
```

**Query Logic:**
- Filter audit_log by `organization_id` and `action = 'view'`
- Filter to last 30 days
- Group by `(entity_type, entity_id)`, count views
- Join to entity tables to get current name
- Order by `view_count` descending, limit to 6

## Backend Implementation

### Audit Service Changes

```python
# services/audit_service.py

class AuditService:
    async def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID,
        *,
        actor: UserPrincipal | None = None,
        # ... existing params
        dedupe_seconds: int = 0,  # New: skip if duplicate within N seconds
    ) -> None:
        if dedupe_seconds > 0:
            # Check for recent duplicate
            recent = await self._find_recent_view(
                actor.user_id, entity_type, entity_id, dedupe_seconds
            )
            if recent:
                return  # Skip duplicate

        # Existing log logic...
```

### Router Changes

Add VIEW logging to each entity GET endpoint:

```python
# Example: routers/passwords.py

@router.get("/{password_id}")
async def get_password(...):
    password = await password_repo.get(password_id)

    # Log view (with dedupe)
    await audit_service.log(
        AuditAction.VIEW,
        "password",
        password.id,
        actor=current_user,
        organization_id=org_id,
        dedupe_seconds=60,
    )

    return password
```

### New Repository: Recent/Frequent Access

```python
# repositories/access_tracking.py

class AccessTrackingRepository:
    async def get_recent_for_user(
        self, user_id: UUID, limit: int = 10
    ) -> list[RecentItem]:
        """Get user's recently viewed entities."""
        # Query with joins to entity tables for names
        # Filter by user permissions
        # Exclude deleted entities

    async def get_frequently_accessed(
        self, org_id: UUID, limit: int = 6, days: int = 30
    ) -> list[FrequentItem]:
        """Get most viewed entities in org over time period."""
        # Aggregate views by entity
        # Join to entity tables for names
```

## Frontend Implementation

### Hooks

```typescript
// hooks/useRecentlyAccessed.ts
export function useRecentlyAccessed(limit = 10) {
  return useQuery({
    queryKey: ["recent", limit],
    queryFn: () => api.get<RecentItem[]>(`/api/me/recent?limit=${limit}`),
  })
}
```

Frequently accessed comes bundled with org response:

```typescript
// Existing org query with include param
const { data: org } = useOrganization(orgId, {
  include: ['frequently_accessed']
})

// Access via org.frequently_accessed
```

### Query Invalidation

After navigation, invalidate recent list:

```typescript
// After navigating to an entity detail page
queryClient.invalidateQueries({ queryKey: ["recent"] })
```

### Components

**RecentEntityCard:**
- Compact card: entity type icon, name, org name (in cross-org contexts)
- Clickable, navigates to entity

**RecentDropdown (header):**
- Trigger: Clock icon left of chat button
- Content: 10 recent items in vertical list
- Empty state: "No recent activity"

**RecentSection (dashboard/org page):**
- Horizontal row of 6 cards
- Hide section entirely if empty (no empty state message)

## Edge Cases

### Empty States

| Location | Condition | Behavior |
|----------|-----------|----------|
| Header dropdown | No recent views | Show "No recent activity" |
| Dashboard | New user | Hide section entirely |
| Org home | No views in 30 days | Hide section entirely |
| Organizations page | No recent orgs | Hide recent cards, show list only |

### Deleted Entities
- Query joins to entity tables, so deleted entities excluded automatically
- No stale/broken links

### Permission Changes
- Query filters by current user permissions
- Losing access removes entity from recent list naturally

### Deduplication
- Same entity appears once (most recent timestamp)
- 60-second server dedupe prevents audit log spam

## Implementation Phases

### Phase 1: Backend
1. Add `VIEW` to `AuditAction` enum (if not present)
2. Add dedupe logic to audit service
3. Add VIEW logging to all entity GET endpoints
4. Create `AccessTrackingRepository`
5. Create `GET /api/me/recent` endpoint
6. Add `frequently_accessed` include to org endpoint
7. Add database index

### Phase 2: Frontend
1. Create `useRecentlyAccessed` hook
2. Update org query to support `include` param
3. Build `RecentEntityCard` component
4. Add `RecentDropdown` to header
5. Add recent sections to dashboard
6. Add recent cards to Organizations page
7. Add frequently accessed to Org home page

## Non-Goals

- No "pin" or "favorite" functionality (separate feature)
- No cross-org frequently accessed (would require different scoping)
- No weighted recency scoring (simple last-N is sufficient)
- No view count display in recent items (only in frequently accessed)
