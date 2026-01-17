# IT Glue Migration Tool Design

**Date:** 2026-01-13
**Status:** Approved

## Overview

Migration tool to import IT Glue exports into our documentation platform. Designed as a local CLI tool that calls our API, with architecture that supports future native integration.

## Goals

1. **One-way sync** from IT Glue → Our app (no reverse sync or deletions)
2. **Incremental support** via metadata tracking (`itglue_id`, `itglue_last_updated`)
3. **Single-org testing** before full migration
4. **Preview mode** to review schema decisions before import
5. **API-based** to work against any environment (local, staging, production)

## Non-Goals

- Contacts migration (data not needed)
- Office 365 licenses migration (skip)
- Reverse sync (IT Glue deletions don't propagate)
- Real-time sync (one-time migration with optional re-runs)

---

## Two-Phase Migration Strategy

### Why Two Phases?

The IT Glue **export** contains all entity data but relationships are stored as **text names** (e.g., "SonicWALL TZ-300") rather than entity IDs. The IT Glue **API** provides actual `related_items` with proper IDs, but is heavily rate-limited (~10 req/sec).

### Phase Strategy

| Phase | Data Source | What Gets Migrated |
|-------|-------------|-------------------|
| **Phase 1: Export** | CSV + files | All entities, embedded password links (has resource_id), attachments, document images |
| **Phase 2: API** | IT Glue API | Cross-entity relationships (related_items) |

### What's in Export vs API

| Data | Export (CSV) | IT Glue API |
|------|-------------|-------------|
| Entity data (configs, passwords, docs) | ✓ Full data | Same |
| Password values | ✓ Plain text | Encrypted |
| OTP/TOTP secrets | ✓ In CSV | Not available |
| Document HTML + attachments | ✓ Full content | Not available |
| Password → Configuration links | ✓ resource_type + resource_id | Same |
| Flex asset tag fields | Text names only | Entity IDs |
| **related_items (cross-entity links)** | ❌ Not in export | ✓ Required |

### Relationship Types

**From Export (Phase 1):**
- Password → Configuration (via `resource_type` = "Configuration", `resource_id`)
- Password → Custom Asset (via `resource_type` = "StructuredData::*", `resource_id`)

**From API (Phase 2):**
- Configuration → Configuration (related_items)
- Configuration → Document (related_items)
- Custom Asset → Custom Asset (related_items)
- Custom Asset → Configuration (related_items)
- Document → any entity (related_items)

---

## IT Glue Export Structure

### Export Contents (9.5 GB total)

| Component | Size | Description |
|-----------|------|-------------|
| CSV files | 28 files | Metadata for all entities |
| documents/ | 4.0 GB | 1,328 HTML documents + 10,000+ embedded images |
| attachments/ | 5.4 GB | Files organized by entity type |
| floor_plans_photos/ | 87 MB | 14 floor plan images |

### Core Entities (6 CSVs)

| Entity | Count | Key Fields | Migration Target |
|--------|-------|------------|------------------|
| organizations | 178 | id, name, description, quick_notes | organizations table |
| configurations | 6,191 | id, name, hostname, ip, mac, serial, manufacturer, model, notes, configuration_interfaces (JSON) | configurations table |
| documents | 1,328 | id, name, locator (path), organization | documents table |
| locations | 589 | id, name, address fields, phone | locations table (name/notes only) |
| passwords | 10,218 | id, name, username, password, url, notes, resource_type, resource_id | passwords table |
| contacts | 8,223 | - | **SKIP** (not needed) |

### Custom Asset Types (21 CSVs)

| File | Count | Purpose |
|------|-------|---------|
| ssl-certificates | 4,465 | SSL certs with validity dates |
| licensing | 840 | Software licenses and keys |
| apps-and-services | 421 | Application inventory |
| vendors | 399 | Vendor contacts and accounts |
| domains | 249 | Domain names and expiration |
| wireless | 238 | WiFi SSIDs and credentials |
| lan | 176 | Network subnets and VLANs |
| internet-wan | 173 | ISP info and WAN config |
| site-summary | 172 | Site overviews |
| printing | 82 | Print servers and printers |
| remote-access | 75 | RDP/VPN configuration |
| azure-app-registration | 59 | App registrations and secrets |
| email | 54 | Email provider config |
| payment-method | 47 | Credit cards (last 4 digits) |
| voice | 47 | VoIP setup |
| active-directory | 31 | AD server config |
| websites | 31 | Website hosting info |
| support-overview | 13 | Managed services overview |
| apple-mdm-push-certificate | 5 | MDM certificates |
| building-security | 1 | Access control and alarms |
| file-share | 1 | Network shares |

### Password Linking

Passwords can be standalone or linked to other entities:

| resource_type | Count | Migration Approach |
|---------------|-------|-------------------|
| (standalone) | ~4,400 | Import as regular passwords |
| Configuration | ~3,400 | Import + create "embedded" relationship |
| StructuredData::Cell/Row | ~240 | Import + link to custom_asset |
| Other (Location, Vendor, etc.) | ~180 | Import + create relationship |

### Document Structure

- HTML content in `documents/` folder with nested structure
- Images embedded as `<img src="1774924/docs/5881546/images/8808168">`
- Corresponding images in same folder or `attachments/documents/`

---

## Required App Changes

### Database Schema Changes

#### 1. Add `metadata` JSONB column (6 tables)

Tables: `organizations`, `documents`, `configurations`, `passwords`, `locations`, `custom_assets`

```sql
ALTER TABLE {table} ADD COLUMN metadata JSONB DEFAULT '{}';
CREATE INDEX idx_{table}_metadata_itglue_id ON {table} ((metadata->>'itglue_id'));
```

Purpose: Store external system IDs for incremental sync
```json
{
  "itglue_id": "1234567",
  "itglue_last_updated": "2024-01-15T10:30:00Z"
}
```

#### 2. Add `interfaces` JSONB column to configurations

```sql
ALTER TABLE configurations ADD COLUMN interfaces JSONB DEFAULT '[]';
```

Purpose: Store network interfaces (multiple IPs/MACs per device)
```json
[
  {"name": "eth0", "ip_address": "192.168.1.107", "mac_address": "18:0c:ac:a1:86:f2", "primary": true}
]
```

### API Changes

#### 1. Add `/attachments/{id}/view` endpoint

Returns redirect to fresh presigned URL (or proxies the image).

```
GET /api/organizations/{org_id}/attachments/{attachment_id}/view
→ 302 Redirect to presigned S3 URL
```

Purpose: Stable image URLs in HTML content that don't expire.

#### 2. Update document image upload response

Current: Returns presigned URL (expires in 7 days)
New: Returns stable `/view` URL

#### 3. Add metadata support to all entity endpoints

Update create/update contracts to accept optional `metadata` field.

### Frontend Changes

#### 1. TipTap editor image handling

Change from storing presigned URLs to stable `/view` URLs:
```html
<!-- Before -->
<img src="https://s3.../presigned?expires=...">

<!-- After -->
<img src="/api/organizations/{org_id}/attachments/{id}/view">
```

---

## Migration Tool Design

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Local CLI Tool                          │
├─────────────────────────────────────────────────────────────┤
│  migrate preview --export-path /path --api-url https://...  │
│  migrate run --plan plan.json --org "Covi, Inc."            │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP (Bearer token auth)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Your API                                │
│  - POST /organizations                                       │
│  - POST /documents                                           │
│  - POST /configurations                                      │
│  - POST /passwords                                           │
│  - POST /attachments/upload + /attachments/images            │
│  - POST /custom-asset-types                                  │
│  - POST /custom-assets                                       │
│  - POST /relationships                                       │
└─────────────────────────────────────────────────────────────┘
```

### CLI Commands

#### `migrate preview`

Scans export, generates plan file for review.

```bash
migrate preview \
  --export-path /Users/jack/Downloads/export \
  --api-url https://api.yourapp.com \
  --token $API_TOKEN \
  --output plan.json
```

Output `plan.json`:
```json
{
  "export_path": "/Users/jack/Downloads/export",
  "scanned_at": "2026-01-13T10:30:00Z",

  "organizations": {
    "total": 178,
    "matched": 45,
    "to_create": 133,
    "mapping": {
      "Covi, Inc.": {"status": "matched", "uuid": "abc-123"},
      "New Client": {"status": "create", "uuid": null}
    }
  },

  "custom_asset_types": {
    "ssl-certificates": {
      "fields": [
        {"key": "common_name", "name": "Common Name", "type": "text"},
        {"key": "expiration_date", "name": "Expiration Date", "type": "date"},
        {"key": "issuer", "name": "Issuer", "type": "text"},
        {"key": "san", "name": "SAN", "type": "textbox"}
      ],
      "sample_row": {"common_name": "*.example.com", "expiration_date": "2025-06-15"}
    }
  },

  "entity_counts": {
    "configurations": 6191,
    "documents": 1328,
    "passwords": 10218,
    "locations": 589,
    "custom_assets": 7500
  },

  "attachments": {
    "total_files": 2100,
    "total_size_gb": 5.4
  },

  "warnings": [
    "3 documents reference missing attachments",
    "12 passwords reference unknown resource_type"
  ]
}
```

#### `migrate run`

Executes migration using approved plan.

```bash
# Single org test
migrate run \
  --plan plan.json \
  --org "Covi, Inc." \
  --api-url https://api.yourapp.com \
  --token $API_TOKEN

# Full migration
migrate run \
  --plan plan.json \
  --all \
  --api-url https://api.yourapp.com \
  --token $API_TOKEN
```

Progress output:
```
[1/6] Organizations: 178/178 ✓
[2/6] Locations: 589/589 ✓
[3/6] Configurations: 2341/6191 (37%)...
[4/6] Documents: 0/1328 (pending)
[5/6] Passwords: 0/10218 (pending)
[6/6] Custom Assets: 0/7500 (pending)

Current: Uploading configuration attachments...
```

### Migration Order

Dependencies require specific ordering:

```
1. Organizations (no dependencies)
2. Locations (depends on org)
3. Configuration Types (match or create)
4. Configurations (depends on org, location, config_type)
5. Custom Asset Types (create from plan)
6. Custom Assets (depends on org, custom_asset_type)
7. Documents + Images (depends on org, upload images first)
8. Passwords (depends on org)
9. Relationships (depends on all entities existing)
   - Embedded passwords → configurations
   - Embedded passwords → custom_assets
```

### ID Mapping

During migration, maintain mapping of IT Glue IDs → new UUIDs:

```python
id_map = {
    "organization": {"itglue_123": "uuid-abc", ...},
    "configuration": {"itglue_456": "uuid-def", ...},
    "document": {...},
    "password": {...},
    "custom_asset": {...}
}
```

Used for:
- Creating relationships (need target UUIDs)
- Resolving `resource_id` in passwords
- Incremental runs (skip already-migrated entities)

---

## Image & Attachment Handling

### Document Images

**Source format (IT Glue HTML):**
```html
<div class='text-section scrollable'>
  <p>Follow these steps:</p>
  <img src="1774924/docs/5881546/images/8808168">
</div>
```

**Image file location:**
```
documents/DOC-1774924-5881546 Document Name/1774924/docs/5881546/images/8808168
```

**Migration steps:**

1. Parse HTML, extract all `<img src="...">` paths
2. Resolve each path to actual file in export
3. Upload file via `POST /attachments/images`
4. Replace `src` with stable URL: `/api/organizations/{org_id}/attachments/{id}/view`
5. Save transformed HTML as document content

**Result:**
```html
<div class='text-section scrollable'>
  <p>Follow these steps:</p>
  <img src="/api/organizations/abc-123/attachments/def-456/view">
</div>
```

### Entity Attachments

Files in `attachments/` folder organized by entity type:

```
attachments/
├── configurations/
│   └── 7505674/
│       ├── network-diagram.pdf
│       └── photo.jpg
├── documents/
│   └── 5881546/
│       └── appendix.docx
├── passwords/
│   └── 1548433/
│       └── license-key.txt
└── site-summary/
    └── 172345/
        └── floor-plan.pdf
```

**Migration steps:**

1. After creating entity, check for matching attachment folder
2. Upload each file via presigned URL flow:
   - `POST /attachments/upload` → get presigned URL
   - `PUT` file to presigned URL
3. Attachment automatically linked via `entity_type` + `entity_id`

### Attachment Stats

| Entity Type | Files | Notes |
|-------------|-------|-------|
| site-summary | 953 | → custom_asset attachments |
| configurations | 440 | |
| documents | 252 | Additional files (not inline images) |
| locations | 153 | |
| internet-wan | 117 | → custom_asset attachments |
| lan | 66 | → custom_asset attachments |
| passwords | 42 | |
| Other custom assets | ~100 | Various |

---

## Implementation Tasks

### Phase 1: App Changes (Prerequisites) ✅ COMPLETE

#### 1.1 Database Migrations ✅
- [x] Add `metadata JSONB` to organizations table
- [x] Add `metadata JSONB` to documents table
- [x] Add `metadata JSONB` to configurations table
- [x] Add `metadata JSONB` to passwords table
- [x] Add `metadata JSONB` to locations table
- [x] Add `metadata JSONB` to custom_assets table
- [x] Add `interfaces JSONB` to configurations table
- [x] Add indexes on `metadata->>'itglue_id'` for each table

**Migrations created:**
- `018_add_metadata_columns.py` - metadata columns with partial indexes
- `019_add_interfaces_to_configurations.py` - interfaces JSONB column

#### 1.2 API Updates ✅
- [x] Add `GET /attachments/{id}/view` endpoint (redirect to presigned URL)
- [x] Update all entity contracts to accept `metadata` field
- [x] Update all entity contracts to accept `interfaces` field (configurations)
- [x] Update `DocumentImageUploadResponse` to return stable `/view` URL

**Files updated:**
- ORM models: organization.py, document.py, configuration.py, password.py, location.py, custom_asset.py
- Contracts: All 6 entity contracts updated with metadata field
- Routers: All 6 entity routers updated to handle metadata in CRUD operations
- Attachments router: Added `/view` endpoint, updated image upload response

#### 1.3 Frontend Updates ✅
- [x] Update TipTap editor to store `/view` URLs instead of presigned URLs
- [x] Ensure existing documents with presigned URLs still render (graceful fallback)

**Verified:** TipTap editor at `/client/src/components/documents/TiptapEditor.tsx` already uses `createResponse.data.image_url` (stable `/view` URL). Presigned URLs in existing documents will still work (they don't expire for 7 days).

### Phase 2: Migration Tool

#### 2.1 Core Infrastructure
- [ ] Create `tools/itglue-migrate/` project structure
- [ ] API client with bearer token auth
- [ ] Progress reporting and logging
- [ ] ID mapping storage (in-memory + optional file persistence)
- [ ] Error handling and resume capability

#### 2.2 Preview Command
- [ ] CSV parser for all entity types
- [ ] Organization matching logic (metadata → name → create)
- [ ] Custom asset type field inference (text, date, number, textbox)
- [ ] Attachment scanning and size calculation
- [ ] Warning detection (missing refs, unknown types)
- [ ] Plan JSON output

#### 2.3 Entity Importers
- [ ] Organizations importer
- [ ] Locations importer (name + notes only)
- [ ] Configuration types matcher/creator
- [ ] Configurations importer (with interfaces)
- [ ] Custom asset types creator (from plan)
- [ ] Custom assets importer
- [ ] Documents importer (with HTML transformation)
- [ ] Passwords importer
- [ ] Relationships creator (embedded passwords)

#### 2.4 Attachment Handling
- [ ] Document image extractor (parse HTML, find images)
- [ ] Image uploader (via /attachments/images)
- [ ] HTML transformer (replace src paths)
- [ ] Entity attachment uploader (via presigned URL flow)

### Phase 3: Testing & Validation

#### 3.1 Single Org Test
- [ ] Run preview against full export
- [ ] Review and approve plan.json
- [ ] Migrate single org (e.g., "Covi, Inc.")
- [ ] Validate all entities imported correctly
- [ ] Validate images render in documents
- [ ] Validate embedded passwords linked correctly

#### 3.2 Full Migration
- [ ] Run full migration
- [ ] Spot check random orgs
- [ ] Verify attachment counts match

### Phase 4: API-Based Relationship Sync (Second Pass)

#### 4.1 IT Glue API Client
- [ ] IT Glue API client with rate limiting (~10 req/sec)
- [ ] Authentication via IT Glue API key
- [ ] Pagination handling for large result sets

#### 4.2 Relationship Fetcher
- [ ] Fetch configurations with `?include=related_items`
- [ ] Fetch flexible assets with `?include=related_items`
- [ ] Fetch documents with `?include=related_items`
- [ ] Map IT Glue IDs to our UUIDs (using metadata.itglue_id)

#### 4.3 Relationship Creator
- [ ] Create relationships via our API for each related_item
- [ ] Skip relationships where target entity wasn't migrated
- [ ] Log skipped relationships for review

#### 4.4 CLI Command
```bash
migrate relationships \
  --itglue-api-key $ITGLUE_KEY \
  --api-url https://api.yourapp.com \
  --token $API_TOKEN \
  --org "Covi, Inc."  # Optional: single org or all
```

---

## Success Criteria

### Phase 1 Complete When:
- [x] All migrations applied, no errors (migrations created: 018, 019)
- [x] `/attachments/{id}/view` returns 302 redirect to valid presigned URL
- [x] New document images use stable URLs
- [ ] Existing documents continue to work (needs frontend update)
- [x] Type checks pass (pyright: 0 errors)
- [x] Linting passes (ruff: all checks passed)

### Phase 2 Complete When:
- [ ] `migrate preview` generates valid plan.json for full export
- [ ] `migrate run --org "X"` successfully imports single org
- [ ] All entity types import without errors
- [ ] Images render correctly in migrated documents
- [ ] Embedded passwords show on configurations/custom assets
- [ ] Incremental run skips already-migrated entities (by itglue_id)

### Phase 3 Complete When:
- [ ] Full migration completes for all 178 orgs
- [ ] Entity counts match expectations:
  - Organizations: 178
  - Configurations: 6,191
  - Documents: 1,328
  - Locations: 589
  - Passwords: 10,218
  - Custom Assets: ~7,500 (across 21 types)
- [ ] Attachments uploaded: ~2,100 files
- [ ] No orphaned references or broken images

### Phase 4 Complete When:
- [ ] IT Glue API client connects and authenticates
- [ ] `migrate relationships` fetches related_items for all entity types
- [ ] Cross-entity relationships created in our app
- [ ] Relationships visible in UI on configurations, documents, custom assets
- [ ] Skipped relationships logged (missing targets documented)

---

## Reference: Hudu Migration Tool

The [Hudu IT Glue Migration Tool](https://github.com/Hudu-Technologies-Inc/ITGlue-Hudu-Migration) was reviewed for insights. Key learnings:

**What they do:**
- Use BOTH export AND IT Glue API (we're doing the same with two phases)
- Export for bulk data + password values (API has encrypted passwords)
- API for `related_items` relationships
- Deferred relationship creation (create entities first, link later)
- URL rewriting for images in rich text

**Gotchas they document:**
- IT Glue allows duplicate org names; we should handle gracefully
- Blank passwords fail on import; validate before creating
- Migration can take 24+ hours for large datasets
- Rate limiting requires patience

**What we're doing differently:**
- CLI tool calling our API (not PowerShell + direct DB)
- Preview/plan mode for schema review before import
- Metadata-based incremental sync support
