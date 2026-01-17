# BifrostDocs API Documentation

## Overview

This document describes the BifrostDocs API endpoints, with a focus on the `is_enabled` field and `show_disabled` parameter functionality.

## `is_enabled` Field

### Description

The `is_enabled` field is a boolean field that indicates whether an entity is active/enabled or disabled. When `is_enabled=False`, the entity is considered disabled and is excluded from default API responses.

### Entities with `is_enabled`

The following entities support the `is_enabled` field:

- Organizations
- Locations
- Configurations
- Custom Assets
- Documents
- Passwords

### Default Behavior

- **Creating entities**: If `is_enabled` is not specified during creation, it defaults to `True` (enabled)
- **Listing entities**: By default, only enabled entities (`is_enabled=True`) are returned
- **Updating entities**: The `is_enabled` field can be updated via PATCH/PUT requests

## `show_disabled` Query Parameter

### Description

The `show_disabled` query parameter controls whether disabled entities are included in list and search responses.

### Behavior

- **`show_disabled=false` (default)**: Only returns enabled entities (`is_enabled=True`)
- **`show_disabled=true`**: Returns all entities regardless of `is_enabled` status

### Supported Endpoints

The `show_disabled` parameter is supported on the following list endpoints:

#### Organizations
```
GET /api/organizations?show_disabled=true
```

#### Locations
```
GET /api/organizations/{org_id}/locations?show_disabled=true
```

#### Configurations
```
GET /api/organizations/{org_id}/configurations?show_disabled=true
```

#### Custom Assets
```
GET /api/organizations/{org_id}/custom-assets?show_disabled=true
```

#### Documents
```
GET /api/organizations/{org_id}/documents?show_disabled=true
```

#### Passwords
```
GET /api/organizations/{org_id}/passwords?show_disabled=true
```

### Search Endpoint

The search endpoint also supports the `show_disabled` parameter:

```
GET /api/organizations/{org_id}/search?q={query}&show_disabled=true
```

When `show_disabled=true`, search results include disabled entities across all types (configurations, custom assets, documents, passwords, locations).

## Examples

### List only enabled configurations (default)
```http
GET /api/organizations/{org_id}/configurations
```
```http
GET /api/organizations/{org_id}/configurations?show_disabled=false
```

### List all configurations including disabled
```http
GET /api/organizations/{org_id}/configurations?show_disabled=true
```

### Search across all entities (enabled only)
```http
GET /api/organizations/{org_id}/search?q=server
```

### Search across all entities including disabled
```http
GET /api/organizations/{org_id}/search?q=server&show_disabled=true
```

### Create a disabled configuration
```http
POST /api/organizations/{org_id}/configurations
Content-Type: application/json

{
  "name": "Old Server",
  "configuration_type_id": "...",
  "is_enabled": false
}
```

### Disable an existing configuration
```http
PATCH /api/organizations/{org_id}/configurations/{config_id}
Content-Type: application/json

{
  "is_enabled": false
}
```

## Migration from IT Glue

When importing data from IT Glue, the following mappings are used:

### Configurations & Custom Assets
- IT Glue `archived` field → `is_enabled`
  - `archived="Yes"` → `is_enabled=False`
  - `archived="No"` or missing → `is_enabled=True`

### Organizations
- IT Glue `organization_status` field → `is_enabled`
  - `organization_status="Active"` → `is_enabled=True`
  - Any other status → `is_enabled=False`

## Implementation Details

### Backend (Python/FastAPI)

- **Field Definition**: `is_enabled` is defined as a nullable boolean column in database models
- **Repository Layer**: Repository methods support an optional `is_enabled` filter parameter
- **Router Layer**: Endpoints extract `show_disabled` from query params and convert to appropriate filter

### Frontend (TypeScript/React)

- **Type Definitions**: All entity types include `is_enabled?: boolean` field
- **API Client**: API calls support `show_disabled` parameter for list/search operations
- **UI Components**: Components show disabled entities with visual indicators when `show_disabled=true`

## Database Schema

### Example: Configurations Table

```sql
CREATE TABLE configurations (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    configuration_type_id UUID,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- ... other fields
);
```

### Indexing

For optimal performance, indexes should be created on the `is_enabled` field:

```sql
CREATE INDEX idx_configurations_is_enabled ON configurations(is_enabled);
CREATE INDEX idx_configurations_org_enabled ON configurations(organization_id, is_enabled);
```

## Security Considerations

- **Row-Level Security (RLS)**: The `is_enabled` filter is applied AFTER RLS policies, ensuring users can only see entities they have access to
- **No Data Loss**: Disabling an entity does not delete it; all data is preserved
- **Audit Trail**: Changes to `is_enabled` are tracked in audit logs

## Future Enhancements

Potential future features:

1. **Bulk Toggle Endpoints**: Enable/disable multiple entities at once
   - `POST /api/organizations/{org_id}/configurations/bulk-enable`
   - `POST /api/organizations/{org_id}/configurations/bulk-disable`

2. **Scheduled Disable**: Configure entities to automatically disable at a future date

3. **Disable Reason**: Add a optional text field to document why an entity was disabled

4. **Soft Delete**: Use `is_enabled=False` as a soft delete mechanism with retention policies

## Related Documentation

- [IT Glue Migration Guide](../plans/MIGRATION_TOOL.md)
- [Database Schema](../database/README.md)
- [API Authentication](../docs/authentication.md)
