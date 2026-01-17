# Archived/Disabled Entities Design

**Date:** 2026-01-14
**Author:** Design review for IT Glue migration gaps
**Status:** Draft

## Overview

This design addresses gaps discovered during IT Glue migration testing, specifically around handling archived/disabled entities and multi-line text fields. The solution adds `is_enabled` flags to major entities, updates API filtering, enhances the IT Glue importer, and updates the frontend UI.

## Requirements

From IT Glue migration testing:

1. IT Glue exports contain `archived` Yes/No columns for most entities
2. IT Glue organizations have `organization_status` (Active/Inactive/etc.)
3. Address fields and multi-line notes need HTML formatting (not markdown)
4. Multi-line text fields need proper detection during field inference
5. Disabled entities should be hidden from search and lists by default
6. Disabled organizations should cascade to hide their related entities

## Section 1: Database Schema Changes

### 1A. New is_enabled Column

Add `is_enabled` column to the following tables:

- `organizations`
- `configurations`
- `documents`
- `locations`
- `passwords`
- `custom_assets`

**Column specification:**
```sql
is_enabled BOOLEAN NOT NULL DEFAULT true
```

**Rationale:**
- `DEFAULT true` ensures existing records are enabled (backward compatible)
- `NOT NULL` prevents ambiguous state
- Using `is_enabled` instead of `is_archived` or `is_active` for consistency across all entities
- Aligns with IT Glue's `organization_status` field (Active = enabled)

### 1B. Indexes

Add a partial index for efficient filtering of enabled/disabled entities:

```sql
CREATE INDEX ix_{table}_is_enabled ON {table}(is_enabled)
WHERE is_enabled = false;
```

**Rationale:**
- Partial index on `false` values is optimal because most queries filter for enabled entities
- PostgreSQL can use a full table scan for `true` (the majority)
- The small index on `false` values makes "show disabled" queries fast
- Smaller index = less disk I/O and better cache efficiency

### 1C. Data Migration

**IMPORTANT: Use Alembic for all migrations.** Do NOT manually generate migration IDs.

Run the following command to create a new migration (Alembic will auto-generate the revision ID):

```bash
alembic revision -m "add_is_enabled_to_entities"
```

Migration is straightforward since `DEFAULT true` handles existing records. The migration file should contain:

```python
def upgrade():
    # Add is_enabled column to all tables
    op.add_column('organizations', sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('configurations', sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('documents', sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('locations', sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('passwords', sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('custom_assets', sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'))

    # Create partial indexes
    op.create_index('ix_organizations_is_enabled', 'organizations', ['is_enabled'], postgresql_where=sa.text('is_enabled = false'))
    op.create_index('ix_configurations_is_enabled', 'configurations', ['is_enabled'], postgresql_where=sa.text('is_enabled = false'))
    op.create_index('ix_documents_is_enabled', 'documents', ['is_enabled'], postgresql_where=sa.text('is_enabled = false'))
    op.create_index('ix_locations_is_enabled', 'locations', ['is_enabled'], postgresql_where=sa.text('is_enabled = false'))
    op.create_index('ix_passwords_is_enabled', 'passwords', ['is_enabled'], postgresql_where=sa.text('is_enabled = false'))
    op.create_index('ix_custom_assets_is_enabled', 'custom_assets', ['is_enabled'], postgresql_where=sa.text('is_enabled = false'))

def downgrade():
    # Drop indexes
    op.drop_index('ix_custom_assets_is_enabled', table_name='custom_assets')
    op.drop_index('ix_passwords_is_enabled', table_name='passwords')
    op.drop_index('ix_locations_is_enabled', table_name='locations')
    op.drop_index('ix_documents_is_enabled', table_name='documents')
    op.drop_index('ix_configurations_is_enabled', table_name='configurations')
    op.drop_index('ix_organizations_is_enabled', table_name='organizations')

    # Drop columns
    op.drop_column('custom_assets', 'is_enabled')
    op.drop_column('passwords', 'is_enabled')
    op.drop_column('locations', 'is_enabled')
    op.drop_column('documents', 'is_enabled')
    op.drop_column('configurations', 'is_enabled')
    op.drop_column('organizations', 'is_enabled')
```

No data transformation needed - existing records automatically become enabled due to `server_default='true'`.

### 1D. Field Inference for Multi-line Text

**Enhanced field inference logic:**

The `field_inference.py` module will detect multi-line text fields by analyzing sample values.

**Detection criteria:**
1. Check if any sample value contains newline characters (`\n` or `\r`)
2. Check if any sample value contains HTML tags using regex pattern `<[^>]+>`
3. If either condition is true, mark field as `multiline_text` type

**Sample detection logic:**
```python
import re

HTML_TAG_PATTERN = re.compile(r'<[^>]+>')

def detect_field_type(samples: list[str]) -> str:
    """Detect field type from sample values."""
    for sample in samples:
        if not sample:
            continue
        # Check for newlines
        if '\n' in sample or '\r' in sample:
            return "multiline_text"
        # Check for HTML tags using regex
        if HTML_TAG_PATTERN.search(sample):
            return "multiline_text"
    return "text"  # Default to single-line text
```

**Rationale:**
- Newlines indicate user intentionally created multi-line content
- HTML tags indicate rich text formatting
- Works for IT Glue exports with Notes fields containing HTML
- Catches both explicit `<p>`, `<div>`, etc. and embedded HTML
- Fallback to single-line text for simple values

## Section 2: API Endpoint Changes

### 2A. List Endpoints

**Affected endpoints:**
- `GET /api/organizations`
- `GET /api/organizations/{org_id}/configurations`
- `GET /api/organizations/{org_id}/documents`
- `GET /api/organizations/{org_id}/locations`
- `GET /api/organizations/{org_id}/passwords`
- `GET /api/organizations/{org_id}/custom-assets`
- `GET /api/organizations/{org_id}/custom-assets/{type_id}`

**New query parameter:**
```python
show_disabled: bool = False
```

**Behavior:**
- Default (`show_disabled=false`): Returns only enabled entities (`is_enabled = true`)
- With `show_disabled=true`: Returns all entities regardless of `is_enabled` status

**Organization-scoped endpoints:**
- Organization's `is_enabled` status is NOT considered
- If user explicitly requests by `org_id`, they get that org's content
- This allows viewing content of disabled organizations when navigated to directly

**Organizations list:**
- `show_disabled=false` (default): Returns only enabled organizations
- `show_disabled=true`: Returns all organizations

**Example implementation:**
```python
@app.get("/api/organizations/{org_id}/configurations")
async def list_configurations(
    org_id: str,
    show_disabled: bool = False,
    # ... other params
):
    query = select(Configuration).where(
        Configuration.organization_id == org_id
    )

    if not show_disabled:
        query = query.where(Configuration.is_enabled == True)

    # ... rest of implementation
```

### 2B. Search Endpoints

**Affected endpoints:**
- `GET /api/search` (global search)
- `GET /api/organizations/{org_id}/search` (org-scoped search)

**New query parameter:**
```python
show_disabled: bool = False
```

**Behavior:**
- `show_disabled=false` (default): Excludes disabled entities AND disabled organizations from search results
- `show_disabled=true`: Includes disabled entities, BUT disabled organizations remain hidden
- Organization cascade only applies to global search
- Organization-scoped search does NOT cascade - respects `show_disabled` for entities only

**Implementation:**
```python
# For global search - always filter out disabled orgs
query = base_query.join(Organization).where(Organization.is_enabled == True)

if not show_disabled:
    query = query.where(Entity.is_enabled == True)

# For org-scoped search - no org filter, just entity filter
query = base_query.where(Entity.organization_id == org_id)

if not show_disabled:
    query = query.where(Entity.is_enabled == True)
```

### 2C. Single-Item GET Endpoints

**Affected endpoints:**
- `GET /api/organizations/{id}`
- `GET /api/configurations/{id}`
- `GET /api/documents/{id}`
- `GET /api/locations/{id}`
- `GET /api/passwords/{id}`
- `GET /api/custom-assets/{id}`

**Behavior:**
- Return the entity regardless of `is_enabled` status (NO 404 for disabled items)
- This allows the UI to display disabled entities and provide a re-enable toggle
- No `show_disabled` parameter needed for single-item GETs

**Implementation:**
```python
@app.get("/api/configurations/{config_id}")
async def get_configuration(config_id: str):
    result = await session.execute(
        select(Configuration).where(Configuration.id == config_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Return config even if is_enabled=false
    return config
```

### 2D. POST/PUT/PATCH Endpoints

**Affected endpoints:**
- `POST /api/organizations`
- `POST /api/configurations`
- `POST /api/documents`
- `POST /api/locations`
- `POST /api/passwords`
- `POST /api/custom-assets`
- `PUT/PATCH /api/organizations/{id}`
- `PUT/PATCH /api/configurations/{id}`
- etc.

**New request field:**
```python
is_enabled: Optional[bool] = None
```

**Behavior:**
- If `is_enabled` is provided, use that value
- If omitted during creation, default to `true` (matches database default)
- If omitted during update, don't change the existing value

**Example:**
```python
@app.post("/api/configurations")
async def create_configuration(config: ConfigurationCreate):
    # is_enabled defaults to True if not provided
    db_config = Configuration(**config.model_dump(), is_enabled=True)
    # ... save and return
```

### 2E. Bulk Toggle Endpoint

**New endpoint for quick enable/disable:**

```
PATCH /api/organizations/{org_id}/configurations/batch
PATCH /api/organizations/{org_id}/documents/batch
PATCH /api/organizations/{org_id}/passwords/batch
```

**Request body:**
```json
{
  "ids": ["uuid1", "uuid2", "uuid3"],
  "is_enabled": false
}
```

**Response:**
```json
{
  "updated_count": 3
}
```

This allows users to quickly archive/restore multiple items at once.

## Section 3: IT Glue Importer Changes

### 3A. Mapping `archived` to `is_enabled`

**Affected CSV files:**
- `configurations.csv` - has `archived` column (Yes/No)
- `documents.csv` - has `archived` column (Yes/No)
- `passwords.csv` - has `archived` column (Yes/No)
- `apps-and-services.csv` (custom assets) - has `archived` column (Yes/No)

**Mapping logic:**
```python
# In importers.py
def map_archived_to_is_enabled(archived_value: str) -> bool:
    """
    Convert IT Glue archived Yes/No to is_enabled boolean.

    Args:
        archived_value: "Yes" or "No" from IT Glue export

    Returns:
        False if archived=Yes, True if archived=No or missing
    """
    if not archived_value:
        return True  # Default to enabled if missing
    return archived_value.lower() != "yes"
```

**Application during import:**
```python
# When creating configuration
configuration = Configuration(
    name=row["name"],
    is_enabled=map_archived_to_is_enabled(row.get("archived", "No")),
    # ... other fields
)
```

**Note:** `locations.csv` does NOT have an `archived` column in IT Glue, so all locations will default to `is_enabled=True`.

### 3B. Mapping `organization_status` to `is_enabled`

**Organizations CSV structure:**
```csv
id,name,organization_type,organization_status,short_name,description,...
1774800,"Covi, Inc.",Owner,Active,NetlinkInc,...
1774898,USA Machinery,Client,Inactive,USAMachinery,...
```

**Mapping logic:**
```python
def map_org_status_to_is_enabled(status: str) -> bool:
    """
    Convert IT Glue organization_status to is_enabled boolean.

    Args:
        status: "Active" or other status from IT Glue export

    Returns:
        True if Active, False otherwise
    """
    if not status:
        return True  # Default to enabled if missing
    return status.lower() == "active"
```

**Application during import:**
```python
# When creating organization
organization = Organization(
    name=row["name"],
    is_enabled=map_org_status_to_is_enabled(row.get("organization_status", "Active")),
    # ... other fields
)
```

**Behavior:**
- `organization_status="Active"` → `is_enabled=True`
- `organization_status="Inactive"` → `is_enabled=False`
- `organization_status="Other"` → `is_enabled=False`
- Missing value → `is_enabled=True` (default)

### 3C. HTML Formatting for Address Fields

**Current behavior (markdown):**
```python
# Current implementation in importers.py - creates markdown like:
# "**Address 1**: 3103 N. Pennsylvania Street **City**: Indianapolis **Region**: Indiana **Country**: United States"
```

**New behavior (HTML with line breaks):**
```python
def format_location_notes_html(row: dict) -> str:
    """
    Format location address fields as HTML with proper line breaks.

    Args:
        row: Dict containing location fields from CSV

    Returns:
        HTML string with address fields on separate lines
    """
    parts = []

    if row.get("address_1"):
        parts.append(f'<strong>Address 1:</strong> {row["address_1"]}')
    if row.get("address_2"):
        parts.append(f'<strong>Address 2:</strong> {row["address_2"]}')
    if row.get("city"):
        parts.append(f'<strong>City:</strong> {row["city"]}')
    if row.get("region"):
        parts.append(f'<strong>Region:</strong> {row["region"]}')
    if row.get("country"):
        parts.append(f'<strong>Country:</strong> {row["country"]}')
    if row.get("postal_code"):
        parts.append(f'<strong>Postal Code:</strong> {row["postal_code"]}')

    # Join with <br> tags for line breaks
    return "<br>".join(parts)
```

**Example output:**
```html
<strong>Address 1:</strong> 3103 N Pennsylvania St<br>
<strong>City:</strong> Indianapolis<br>
<strong>Region:</strong> Indiana<br>
<strong>Country:</strong> United States<br>
<strong>Postal Code:</strong> 46205-3926
```

This HTML renders properly in tiptap editor and view mode.

### 3D. Field Inference Enhancement

**Update to `field_inference.py`:**

Add multi-line text detection using the regex and newline checking defined in Section 1D:

```python
import re

HTML_TAG_PATTERN = re.compile(r'<[^>]+>')

def detect_field_type(samples: list[str]) -> str:
    """Detect field type from sample values."""
    for sample in samples:
        if not sample:
            continue
        # Check for newlines
        if '\n' in sample or '\r' in sample:
            return "multiline_text"
        # Check for HTML tags using regex
        if HTML_TAG_PATTERN.search(sample):
            return "multiline_text"
    return "text"  # Default to single-line text
```

**Apply during custom asset type inference:**
```python
# When inferring field types from IT Glue data
for field_name, samples in field_samples.items():
    field_type = detect_field_type(samples)
    field_definition = {
        "name": field_name,
        "type": field_type,
        # ... other properties
    }
```

This ensures that fields like "Notes" in `apps-and-services.csv` (which may contain HTML or newlines) are correctly created as multi-line text fields with tiptap support.

## Section 4: Frontend UI Changes

### 4A. Organization Detail Page

**Location:** `/organizations/{org_id}`

**Enable/Disable Toggle:**
- Position: Top-right of the page header, near organization name
- Component: shadcn/ui Switch
- Label: "Enabled" / "Disabled" (text changes based on state)
- Behavior: When toggled, immediately calls `PATCH /api/organizations/{org_id}` with `is_enabled` value
- Visual feedback: Show toast notification on success

**Visual indicator when disabled:**
- Add a subtle badge or banner at top of page: "This organization is disabled"
- Badge style: Yellow/amber colored to indicate caution state
- Badge position: Below the org name, above the main content

**Example layout:**
```
┌─────────────────────────────────────────────────────┐
│ Covi, Inc.                              [Enabled ●] │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ This organization is disabled                    │ │ ← Hidden when enabled
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ [Organization content...]                          │
└─────────────────────────────────────────────────────┘
```

### 4B. List Pages (All Entity Types)

**Affected pages:**
- Configurations list
- Documents list
- Locations list
- Passwords list
- Custom Assets list

**"Show Disabled" Toggle:**
- Position: Top-right corner of the page, near filter/search controls
- Component: shadcn/ui Switch with label "Show Disabled"
- Default: Off (only showing enabled items)
- Behavior: When toggled, refetches list with `show_disabled=true` query parameter
- Persistent: Store in localStorage or URL param so preference persists across navigation

**Visual indicator for disabled items:**
- When "Show Disabled" is on, disabled items appear in list with visual distinction:
  - Row opacity: 60% (slightly dimmed)
  - Strikethrough on name/identifier
  - Small "Disabled" badge in status column

**Example list row (disabled):**
```
┌──────────────────────────────────────────────────────┐
│ [COVI-DC01]  ~~Server~~  [Disabled]  Inactive       │ ← Dimmed, strikethrough
└──────────────────────────────────────────────────────┘
```

### 4C. Entity Detail Pages (Configurations, Documents, etc.)

**Location:** `/organizations/{org_id}/{entity_type}/{id}`

**Enable/Disable Toggle:**
- Position: Top-right, near entity name
- Component: shadcn/ui Switch (consistent with organizations)
- Label: "Enabled" / "Disabled"
- Behavior: Calls `PATCH` endpoint to toggle `is_enabled`

**Visual state when disabled:**
- Dim the entire page content (opacity 60%)
- Show banner at top: "This item has been disabled and will not appear in search or lists"
- Actions like Edit, Delete remain accessible (user may want to restore or permanently delete)

### 4D. Search UI

**Location:** Global search bar and search results page

**"Include Disabled" Toggle:**
- Position: Within the search dropdown/filter panel
- Component: shadcn/ui Switch labeled "Include disabled items"
- Default: Off (excludes disabled items)
- Behavior: Passes `show_disabled=true` to search API when enabled

**Search results visual indicator:**
- Disabled organizations: Never appear in results (per API design)
- Disabled entities (when enabled via toggle): Show with visual distinction:
  - Dimmed appearance
  - "Disabled" badge
  - Grayed out text

### 4E. Organizations List Page

**Location:** `/organizations`

**"Show Disabled" Toggle:**
- Position: Top-right corner
- Component: shadcn/ui Switch with label "Show Disabled Organizations"
- Default: Off (only showing enabled organizations)
- Behavior: Refetches with `show_disabled=true`

**Visual distinction for disabled orgs:**
- Same as other entities: dimmed row, strikethrough name, "Disabled" badge

### 4F. Multi-Line Text Field Rendering

**For built-in Notes fields:**
- Continue using existing tiptap editor implementation
- View mode: Renders HTML directly
- Edit mode: tiptap editor for rich text editing

**For custom multi-line text fields:**
- Edit mode: Use tiptap editor (same as built-in Notes)
- View mode: Render HTML directly (not as plain text)
- Field type detection: Automatically use tiptap for fields detected as `multiline_text` during import

**Implementation:**
```typescript
// In custom asset field rendering component
if (field.type === 'multiline_text') {
  return (
    <div className="prose prose-sm max-w-none">
      <TiptapEditor
        content={value}
        readOnly={viewMode}
        onChange={handleChange}
      />
    </div>
  )
}
```

## Summary

This design provides a consistent approach to handling disabled/archived entities across the entire stack:

1. **Database:** Add `is_enabled` column with proper indexing
2. **API:** Filter disabled entities by default, allow opt-in via query parameters
3. **Importer:** Map IT Glue's `archived` and `organization_status` to `is_enabled`
4. **UI:** Provide toggles for showing/disabling items with clear visual feedback

The solution handles organization cascading appropriately while still allowing users to view disabled organization contents when navigating directly.

## Implementation Checklist

Use this checklist to track progress. Each item should be completed and verified before moving to the next.

### Phase 1: Database Schema (Alembic Migration)

- [ ] **1.1** Create Alembic migration: `alembic revision -m "add_is_enabled_to_entities"`
- [ ] **1.2** Add `is_enabled` column to `organizations` table (Boolean, NOT NULL, DEFAULT true)
- [ ] **1.3** Add `is_enabled` column to `configurations` table (Boolean, NOT NULL, DEFAULT true)
- [ ] **1.4** Add `is_enabled` column to `documents` table (Boolean, NOT NULL, DEFAULT true)
- [ ] **1.5** Add `is_enabled` column to `locations` table (Boolean, NOT NULL, DEFAULT true)
- [ ] **1.6** Add `is_enabled` column to `passwords` table (Boolean, NOT NULL, DEFAULT true)
- [ ] **1.7** Add `is_enabled` column to `custom_assets` table (Boolean, NOT NULL, DEFAULT true)
- [ ] **1.8** Create partial index `ix_organizations_is_enabled` WHERE is_enabled = false
- [ ] **1.9** Create partial index `ix_configurations_is_enabled` WHERE is_enabled = false
- [ ] **1.10** Create partial index `ix_documents_is_enabled` WHERE is_enabled = false
- [ ] **1.11** Create partial index `ix_locations_is_enabled` WHERE is_enabled = false
- [ ] **1.12** Create partial index `ix_passwords_is_enabled` WHERE is_enabled = false
- [ ] **1.13** Create partial index `ix_custom_assets_is_enabled` WHERE is_enabled = false
- [ ] **1.14** Add `downgrade()` function to migration (drop indexes, then columns)
- [ ] **1.15** Run migration: `alembic upgrade head`
- [ ] **1.16** Verify: Check that all 6 tables have `is_enabled` column with value `true` for existing records
- [ ] **1.17** Verify: Check that all 6 partial indexes exist in database

### Phase 2: SQLAlchemy Models

- [ ] **2.1** Add `is_enabled: bool = True` to `Organization` model
- [ ] **2.2** Add `is_enabled: bool = True` to `Configuration` model
- [ ] **2.3** Add `is_enabled: bool = True` to `Document` model
- [ ] **2.4** Add `is_enabled: bool = True` to `Location` model
- [ ] **2.5** Add `is_enabled: bool = True` to `Password` model
- [ ] **2.6** Add `is_enabled: bool = True` to `CustomAsset` model
- [ ] **2.7** Verify: Run type checker (`pyright`) - should pass with no errors
- [ ] **2.8** Verify: Run tests (`pytest`) - should all pass

### Phase 3: API Endpoints - List Views

- [ ] **3.1** Add `show_disabled: bool = False` query parameter to organizations list endpoint
- [ ] **3.2** Add `show_disabled: bool = False` query parameter to configurations list endpoint
- [ ] **3.3** Add `show_disabled: bool = False` query parameter to documents list endpoint
- [ ] **3.4** Add `show_disabled: bool = False` query parameter to locations list endpoint
- [ ] **3.5** Add `show_disabled: bool = False` query parameter to passwords list endpoint
- [ ] **3.6** Add `show_disabled: bool = False` query parameter to custom-assets list endpoints
- [ ] **3.7** Implement filtering logic: `WHERE is_enabled = true` when `show_disabled=False`
- [ ] **3.8** Verify: Test organizations list with and without `show_disabled=true`
- [ ] **3.9** Verify: Test that org-scoped lists return content even when org is disabled

### Phase 4: API Endpoints - Search

- [ ] **4.1** Add `show_disabled: bool = False` query parameter to global search endpoint
- [ ] **4.2** Add `show_disabled: bool = False` query parameter to org-scoped search endpoint
- [ ] **4.3** Implement global search: Always filter `WHERE organizations.is_enabled = true`
- [ ] **4.4** Implement global search: Filter entities by `is_enabled` when `show_disabled=False`
- [ ] **4.5** Implement org-scoped search: Filter entities by `is_enabled` when `show_disabled=False` (no org filter)
- [ ] **4.6** Verify: Test global search excludes disabled orgs even with `show_disabled=true`
- [ ] **4.7** Verify: Test global search includes disabled entities with `show_disabled=true`

### Phase 5: API Endpoints - Single Item GET

- [ ] **5.1** Verify: Single-item GETs return entities regardless of `is_enabled` status (no changes needed)
- [ ] **5.2** Verify: Test GET organization that is disabled returns 200 with entity
- [ ] **5.3** Verify: Test GET configuration that is disabled returns 200 with entity

### Phase 6: API Endpoints - POST/PUT/PATCH

- [ ] **6.1** Add `is_enabled: Optional[bool]` to organization create/update schemas
- [ ] **6.2** Add `is_enabled: Optional[bool]` to configuration create/update schemas
- [ ] **6.3** Add `is_enabled: Optional[bool]` to document create/update schemas
- [ ] **6.4** Add `is_enabled: Optional[bool]` to location create/update schemas
- [ ] **6.5** Add `is_enabled: Optional[bool]` to password create/update schemas
- [ ] **6.6** Add `is_enabled: Optional[bool]` to custom_asset create/update schemas
- [ ] **6.7** Implement default `is_enabled=True` on creation when omitted
- [ ] **6.8** Implement: Don't change `is_enabled` on update when omitted
- [ ] **6.9** Verify: Test creating entity without `is_enabled` defaults to `true`
- [ ] **6.10** Verify: Test updating entity without `is_enabled` preserves existing value

### Phase 7: API Endpoints - Bulk Toggle

- [ ] **7.1** Create `PATCH /api/organizations/{org_id}/configurations/batch` endpoint
- [ ] **7.2** Create `PATCH /api/organizations/{org_id}/documents/batch` endpoint
- [ ] **7.3** Create `PATCH /api/organizations/{org_id}/passwords/batch` endpoint
- [ ] **7.4** Implement bulk update logic: Accept `{ids: [], is_enabled: bool}`
- [ ] **7.5** Return `{updated_count: n}` response
- [ ] **7.6** Verify: Test bulk disable multiple configurations
- [ ] **7.7** Verify: Test bulk enable multiple configurations

### Phase 8: IT Glue Importer - Mapping Functions

- [ ] **8.1** Create `map_archived_to_is_enabled()` function in `importers.py`
- [ ] **8.2** Create `map_org_status_to_is_enabled()` function in `importers.py`
- [ ] **8.3** Map `archived` column to `is_enabled` for configurations import
- [ ] **8.4** Map `archived` column to `is_enabled` for documents import
- [ ] **8.5** Map `archived` column to `is_enabled` for passwords import
- [ ] **8.6** Map `archived` column to `is_enabled` for custom assets (apps-and-services) import
- [ ] **8.7** Map `organization_status` to `is_enabled` for organizations import
- [ ] **8.8** Verify: Run importer against test export, check `is_enabled` values

### Phase 9: IT Glue Importer - HTML Formatting

- [ ] **9.1** Create `format_location_notes_html()` function in `importers.py`
- [ ] **9.2** Update location import to use HTML formatting instead of markdown
- [ ] **9.3** Verify: Location notes render as HTML with `<br>` line breaks
- [ ] **9.4** Verify: HTML displays properly in tiptap editor/view mode

### Phase 10: IT Glue Importer - Field Inference

- [ ] **10.1** Add `HTML_TAG_PATTERN = re.compile(r'<[^>]+>')` to `field_inference.py`
- [ ] **10.2** Create `detect_field_type(samples)` function in `field_inference.py`
- [ ] **10.3** Update field inference to call `detect_field_type()` for each field
- [ ] **10.4** Handle `multiline_text` type in custom asset type creation
- [ ] **10.5** Verify: Fields with newlines are detected as `multiline_text`
- [ ] **10.6** Verify: Fields with HTML tags are detected as `multiline_text`
- [ ] **10.7** Verify: Test importer creates correct field types for apps-and-services

### Phase 11: Frontend - API Client Types

- [ ] **11.1** Regenerate TypeScript types from updated API schemas
- [ ] **11.2** Verify: `is_enabled` field appears on all entity types

### Phase 12: Frontend - List Pages

- [ ] **12.1** Create `ShowDisabledSwitch` component (shadcn/ui Switch wrapper)
- [ ] **12.2** Add "Show Disabled" toggle to organizations list page
- [ ] **12.3** Add "Show Disabled" toggle to configurations list page
- [ ] **12.4** Add "Show Disabled" toggle to documents list page
- [ ] **12.5** Add "Show Disabled" toggle to locations list page
- [ ] **12.6** Add "Show Disabled" toggle to passwords list page
- [ ] **12.7** Add "Show Disabled" toggle to custom assets list page
- [ ] **12.8** Implement query param passing: `show_disabled=true` when toggle is on
- [ ] **12.9** Implement localStorage/URL persistence for toggle state
- [ ] **12.10** Add visual styling for disabled rows (60% opacity, strikethrough)
- [ ] **12.11** Add "Disabled" badge to disabled items in lists
- [ ] **12.12** Verify: Toggle persists across page navigation
- [ ] **12.13** Verify: Disabled items appear with visual distinction when toggle is on

### Phase 13: Frontend - Detail Pages

- [ ] **13.1** Create `EnabledSwitch` component (shadcn/ui Switch with label)
- [ ] **13.2** Add enable/disable toggle to organization detail page
- [ ] **13.3** Add enable/disable toggle to configuration detail page
- [ ] **13.4** Add enable/disable toggle to document detail page
- [ ] **13.5** Add enable/disable toggle to location detail page
- [ ] **13.6** Add enable/disable toggle to password detail page
- [ ] **13.7** Add enable/disable toggle to custom asset detail page
- [ ] **13.8** Implement PATCH call on toggle change
- [ ] **13.9** Add toast notification on successful toggle
- [ ] **13.10** Add "This organization/entity is disabled" banner when `is_enabled=false`
- [ ] **13.11** Implement dimmed page state when disabled (60% opacity)
- [ ] **13.12** Verify: Toggle immediately updates entity state
- [ ] **13.13** Verify: Banner appears/disappears based on entity state

### Phase 14: Frontend - Search

- [ ] **14.1** Add "Include disabled items" toggle to global search
- [ ] **14.2** Add "Include disabled items" toggle to org-scoped search
- [ ] **14.3** Implement `show_disabled=true` query param when toggle is on
- [ ] **14.4** Add visual distinction for disabled entities in search results
- [ ] **14.5** Verify: Disabled orgs never appear in search results
- [ ] **14.6** Verify: Disabled entities appear when toggle is on

### Phase 15: Frontend - Multi-line Text Fields

- [ ] **15.1** Update custom asset field renderer to detect `multiline_text` type
- [ ] **15.2** Implement tiptap editor for `multiline_text` fields in edit mode
- [ ] **15.3** Implement HTML rendering for `multiline_text` fields in view mode
- [ ] **15.4** Verify: Imported HTML content displays correctly
- [ ] **15.5** Verify: tiptap editor loads and saves HTML content

### Phase 16: Testing

- [ ] **16.1** Write unit tests for `map_archived_to_is_enabled()` function
- [ ] **16.2** Write unit tests for `map_org_status_to_is_enabled()` function
- [ ] **16.3** Write unit tests for `format_location_notes_html()` function
- [ ] **16.4** Write unit tests for `detect_field_type()` function
- [ ] **16.5** Write integration tests for list endpoints with `show_disabled` param
- [ ] **16.6** Write integration tests for search endpoints with `show_disabled` param
- [ ] **16.7** Write integration tests for bulk toggle endpoints
- [ ] **16.8] Verify: All tests pass (`pytest`)

### Phase 17: Type Checking and Linting

- [ ] **17.1** Run `pyright` - verify zero errors
- [ ] **17.2** Run `ruff check` - verify zero errors
- [ ] **17.3** Run `npm run tsc` - verify zero errors (frontend)
- [ ] **17.4** Run `npm run lint` - verify zero errors (frontend)

### Phase 18: Documentation

- [ ] **18.1** Update API documentation with `show_disabled` parameter
- [ ] **18.2** Update API documentation with `is_enabled` field
- [ ] **18.3** Update API documentation with bulk toggle endpoints
- [ ] **18.4** Document `is_enabled` behavior in README

## Next Steps

After design approval:

1. Set up isolated git worktree for implementation
2. Work through Implementation Checklist phase by phase
3. Mark items as complete as you go
4. Run verification steps after each phase
5. Run full test suite before merging
