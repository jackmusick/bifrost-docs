# IT Glue Migration Tool - Feature Documentation

## Overview

This document describes the key features of the IT Glue to BifrostDocs migration tool, with emphasis on how IT Glue data fields are mapped to BifrostDocs entities.

## Key Features

### 1. Field Type Inference

The migration tool automatically infers field types for custom asset types based on the data in your IT Glue export.

#### Supported Field Types

- **text**: Single-line text input
- **textbox**: Multi-line text area (detected when values contain newlines or HTML)
- **number**: Numeric values
- **date**: Date values
- **checkbox**: Boolean/true-false values
- **select**: Dropdown with predefined options
- **password**: Password fields (detected from column names)
- **totp**: TOTP/2FA secret fields (detected from column names)

#### Detection Logic

The tool analyzes sample values from each column to determine the appropriate field type:

- **Textbox Detection**: Triggers when values contain newlines (`\n`, `\r`) or HTML tags (`<tag>`)
- **Select Detection**: Triggers when there are few unique values with high repetition
- **Password/TOTP Detection**: Based on column name patterns

### 2. Entity Status Mapping

#### Configurations & Custom Assets

IT Glue's `archived` field is mapped to `is_enabled`:

```python
def map_archived_to_is_enabled(archived_value: str | None) -> bool:
    """
    Convert IT Glue archived Yes/No to is_enabled boolean.

    - archived="Yes" → is_enabled=False (disabled)
    - archived="No" or missing → is_enabled=True (enabled)
    """
```

#### Organizations

IT Glue's `organization_status` field is mapped to `is_enabled`:

```python
def map_org_status_to_is_enabled(status: str | None) -> bool:
    """
    Convert IT Glue organization_status to is_enabled boolean.

    - organization_status="Active" → is_enabled=True (enabled)
    - Any other status → is_enabled=False (disabled)
    """
```

### 3. Location Notes Formatting

Location address fields are formatted as HTML for display in BifrostDocs:

```python
def format_location_notes_html(row: dict[str, Any]) -> str:
    """
    Format location address fields as HTML with proper line breaks.

    Creates formatted HTML with labels:
    - Address 1
    - Address 2
    - City
    - Region
    - Country
    - Postal Code
    - Phone
    """
```

Example output:
```html
<p>
  <strong>Address 1:</strong> 123 Main St<br>
  <strong>City:</strong> Springfield<br>
  <strong>Region:</strong> IL<br>
  <strong>Postal Code:</strong> 62701
</p>
```

### 4. Document Content Migration

The tool preserves document content from IT Glue exports:

- **HTML Extraction**: Reads HTML files from IT Glue export structure
- **Folder Mapping**: Preserves document folder hierarchy
- **Encoding Handling**: Handles UTF-8 and fallback to Latin-1 encoding

#### IT Glue Export Structure

The tool handles two document folder structures:

1. **Root Level**: `documents/DOC-{org}-{doc_id} {name}/{name}.html`
2. **Nested**: `documents/{FolderName}/DOC-{org}-{doc_id} {name}/{name}.html`

## Migration Workflow

### Phase 1: Analysis

1. **CSV Parsing**: Parse IT Glue CSV exports
2. **Organization Matching**: Match IT Glue orgs to BifrostDocs orgs
3. **Schema Inference**: Analyze custom asset types and infer schemas
4. **Review**: Review and approve the migration plan

### Phase 2: Import

1. **Organizations**: Create/match organizations
2. **Locations**: Import locations with formatted notes
3. **Configuration Types**: Create configuration types
4. **Configurations**: Import configurations with archived→enabled mapping
5. **Custom Asset Types**: Create custom asset types with inferred schemas
6. **Custom Assets**: Import custom assets with archived→enabled mapping
7. **Documents**: Import documents with HTML content and archived→enabled mapping
8. **Passwords**: Import passwords with archived→enabled mapping

### Phase 3: Verification

1. **Count Verification**: Compare entity counts
2. **Data Validation**: Spot-check critical data
3. **Enable/Disable Verification**: Verify disabled entities are correctly marked

## Configuration

### Environment Variables

```bash
# BifrostDocs API Configuration
BIFROST_DOCS_BASE_URL=https://your-bifrostdocs-instance.com
BIFROST_DOCS_API_KEY=your-api-key

# Export Configuration
ITGLUE_EXPORT_PATH=/path/to/itglue/export
```

### Plan File

The migration uses a `plan.json` file to track migration configuration:

```json
{
  "version": "1.0",
  "organizations": {
    "mappings": [
      {
        "itglue_id": "123",
        "itglue_name": "Acme Corp",
        "status": "matched",
        "bifrost_id": "uuid-here",
        "bifrost_name": "Acme Corp"
      }
    ]
  },
  "custom_asset_schemas": {
    "ssl-certificates": {
      "display_name": "SSL Certificates",
      "fields": [
        {
          "name": "Domain",
          "field_type": "text",
          "required": true
        }
      ]
    }
  }
}
```

## Testing

### Unit Tests

The migration tool includes comprehensive unit tests:

- **Field Mapping Tests**: Test `archived` and `organization_status` mapping
- **Field Type Detection Tests**: Test field type inference logic
- **Location Formatting Tests**: Test HTML note generation

Run tests:
```bash
cd /path/to/itglue-migrate
pytest tests/unit/
```

### Integration Tests

Integration tests verify the complete migration workflow:

```bash
pytest tests/integration/
```

## Troubleshooting

### Common Issues

#### Issue: Disabled entities appearing in search

**Solution**: Use the `show_disabled=false` parameter (default) to exclude disabled entities from search results.

#### Issue: Custom asset fields not matching expected types

**Solution**: Review the inferred schema in `plan.json` and manually adjust field types if needed before running the migration.

#### Issue: Document content not importing

**Solution**: Verify the IT Glue export structure matches the expected pattern. Check that HTML files exist in the `documents/` folder with matching document IDs.

## Best Practices

1. **Test Migration**: Run a test migration with a small subset of data first
2. **Backup**: Always backup your BifrostDocs instance before running a migration
3. **Validation**: After migration, verify counts and spot-check critical data
4. **Disabled Entities**: Review disabled entities separately to ensure correct mapping
5. **Custom Asset Types**: Review inferred schemas before creating types in production

## Data Mapping Reference

### IT Glue → BifrostDocs Field Mappings

#### Organizations

| IT Glue Field | BifrostDocs Field | Notes |
|--------------|------------------|-------|
| id | metadata.itglue_id | Stored in metadata |
| name | name | Direct mapping |
| organization_status | is_enabled | "Active" → True, else False |
| description | metadata.description | Stored in metadata |
| quick_notes | metadata.quick_notes | Stored in metadata |

#### Configurations

| IT Glue Field | BifrostDocs Field | Notes |
|--------------|------------------|-------|
| id | metadata.itglue_id | Stored in metadata |
| name | name | Direct mapping |
| archived | is_enabled | "Yes" → False, "No"/missing → True |
| configuration_type | configuration_type_id | Matched by name |
| serial | serial_number | Direct mapping |
| ip | ip_address | Direct mapping |
| mac | mac_address | Direct mapping |

#### Custom Assets

| IT Glue Field | BifrostDocs Field | Notes |
|--------------|------------------|-------|
| id | metadata.itglue_id | Stored in metadata |
| archived | is_enabled | "Yes" → False, "No"/missing → True |
| fields | values | Column name → field key mapping |

#### Documents

| IT Glue Field | BifrostDocs Field | Notes |
|--------------|------------------|-------|
| id | metadata.itglue_id | Stored in metadata |
| name | name | Direct mapping |
| archived | is_enabled | "Yes" → False, "No"/missing → True |
| HTML content | content | Read from export folder |

#### Passwords

| IT Glue Field | BifrostDocs Field | Notes |
|--------------|------------------|-------|
| id | metadata.itglue_id | Stored in metadata |
| name | name | Direct mapping |
| archived | is_enabled | "Yes" → False, "No"/missing → True |
| otp_secret | totp_secret | Direct mapping |
| password | password | Direct mapping |

## Support

For issues or questions about the migration tool:

1. Check this documentation
2. Review the test files for usage examples
3. Check the main project README
4. Open an issue on the project repository
