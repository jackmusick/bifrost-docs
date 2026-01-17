# Attachment Upload & Validation Design

## Overview

Add entity attachment uploading to the migration pipeline and attachment validation to preview/dry-run mode.

**Current state:**
- Document embedded images (in HTML) → Working
- Entity attachments (configs, docs, passwords, custom assets) → Code exists (`upload_entity_attachments()`) but never called
- Preview validation → Only shows aggregate counts, no matching validation

## Design Decisions

| Decision | Choice |
|----------|--------|
| When to upload | Inline with entity creation (not separate phase) |
| Entity types | All: configs, docs, passwords, locations, floor plans, custom assets |
| Preview detail | Summary with orphan warnings |
| Failure handling | Track per-attachment for granular retry |

## 1. Attachment Upload Integration

### Where uploads happen

Each entity migration function calls `upload_entity_attachments()` immediately after successfully creating an entity:
- `_migrate_configurations()`
- `_migrate_documents()`
- `_migrate_passwords()`
- `_migrate_locations()` (including floor_plans_photos)
- `_migrate_custom_assets()`

### Flow per entity

```
1. Check if entity already completed → skip if yes
2. Create entity via API → get new UUID
3. Record ID mapping (itglue_id → uuid)
4. Upload attachments for this entity:
   a. Check which attachments already completed → skip those
   b. Upload remaining files
   c. Track success/failure per file
5. Mark entity as completed (regardless of attachment outcome)
```

### Custom asset type mapping

Export stores custom asset attachments by slug (e.g., `attachments/site-summary/12345/`). Use existing slug-based lookup in `upload_entity_attachments()`.

### Floor plans/photos

Live in `floor_plans_photos/{location_id}/`, attach to locations. Handle in `_migrate_locations` after location creation.

## 2. Attachment State Tracking

### New fields in MigrationState

```python
# Track completed attachments: "entity_type:itglue_id" → [filenames]
_attachments_completed: dict[str, set[str]]

# Track failed attachments: "entity_type:itglue_id" → [FailedAttachment]
_attachments_failed: dict[str, dict[str, FailedAttachment]]
```

### New methods

```python
def mark_attachment_completed(entity_type: str, itglue_id: str, filename: str)
def mark_attachment_failed(entity_type: str, itglue_id: str, filename: str, error: str)
def is_attachment_completed(entity_type: str, itglue_id: str, filename: str) -> bool
def get_failed_attachments(entity_type: str, itglue_id: str) -> list[FailedAttachment]
def get_attachment_stats() -> AttachmentUploadStats
```

### Retry behavior

| Scenario | Action |
|----------|--------|
| Entity completed + all attachments completed | Skip entirely |
| Entity completed + some attachments failed | Retry failed attachments only |
| Entity completed + new attachments in export | Upload new ones |

### Serialization

State file gains `attachments_completed` and `attachments_failed` keys. Version bump 1 → 2 with backward compatibility (missing keys = empty).

## 3. Preview Validation

### New function in attachments.py

```python
def validate_attachments(
    export_path: Path,
    entities_to_migrate: dict[str, set[str]]  # entity_type → set of itglue_ids
) -> AttachmentValidationResult
```

### AttachmentValidationResult

```python
@dataclass
class AttachmentValidationResult:
    # Attachments that will be uploaded (matched to migrating entities)
    matched: dict[str, EntityAttachmentStats]  # entity_type → stats

    # Attachment folders with no matching entity in migration
    orphaned: dict[str, list[str]]  # entity_type → list of itglue_ids

    # Summary totals
    total_matched_files: int
    total_matched_bytes: int
    total_orphaned_folders: int
```

### Preview output

```
Attachments:
  configurations: 244 entities, 892 files (2.1 GB)
  documents: 171 entities, 456 files (1.8 GB)
  site-summary: 91 entities, 203 files (890 MB)
  ...
  Total: 1,847 files (5.4 GB)

⚠️  Orphaned attachments (3 folders, no matching entity):
    configurations: 12345, 12346
    site-summary: 98765
```

Orphans typically mean entity deleted in IT Glue after export, or filtered by `--org`. Warning only, not blocking.

## 4. Implementation Changes

### Files to modify

| File | Changes |
|------|---------|
| `state.py` | Add attachment tracking fields, methods, serialization. Bump STATE_VERSION to 2. |
| `attachments.py` | Add `AttachmentValidationResult` dataclass and `validate_attachments()` function. |
| `cli.py` | Call validation in preview. Pass `DocumentProcessor` to migration functions. |
| `document_processor.py` | Update `upload_entity_attachments()` to check/update state, handle floor plans. |

### Migration functions to update

Each needs `doc_processor: DocumentProcessor` parameter:
- `_migrate_configurations()`
- `_migrate_documents()`
- `_migrate_passwords()`
- `_migrate_locations()`
- `_migrate_custom_assets()`

### Tests

- Unit tests for new state tracking methods
- Unit tests for `validate_attachments()`
- Integration test for attachment upload flow with mocked API
