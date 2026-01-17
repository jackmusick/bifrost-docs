# Bifrost Docs Implementation Plan

Open-source MSP documentation platform built on bifrost-api patterns.

## Architecture Summary

**Stack:** FastAPI + async SQLAlchemy + PostgreSQL (pgvector) + Vite/React/shadcn
**Auth:** Standalone (SSO, passkeys, password fallback, MFA) + API keys
**Storage:** S3 (MinIO locally) for attachments and embedded images
**Users:** MSP staff only (V1) - all users see all organizations

## Data Model

### Core Entities

-   **Organization** - client containers (MSP manages multiple clients)
-   **Password** - encrypted credentials
-   **Configuration** - devices with Type/Status references (free-text manufacturer/model)
-   **Location** - name + notes only
-   **Document** - markdown with virtual path (S3-style, no folder table)

### Flexible Assets

-   **CustomAssetType** - schema definitions (JSONB fields array)
-   **CustomAsset** - instances with JSONB values

### Supporting

-   **Relationship** - universal junction (any entity ↔ any entity, bidirectional)
-   **Attachment** - S3-backed files on any entity
-   **EmbeddingIndex** - vector search (pgvector)

### Auth

-   **User**, **Session**, **Passkey**, **UserMFAMethod**, **MFARecoveryCode**, **APIKey**
-   Note: UserOrganization junction table exists but not used for V1 (all users see all orgs)

---

## Phase 1: Project Foundation ✅ COMPLETE

### 1.1 Project Scaffolding

**Reference:** `../bifrost-api/` structure

-   [x] Create project structure:
    ```
    bifrost-docs/
    ├── api/
    │   ├── src/
    │   │   ├── core/          # config, database, auth
    │   │   ├── models/
    │   │   │   ├── orm/       # SQLAlchemy models
    │   │   │   └── contracts/ # Pydantic schemas
    │   │   ├── repositories/  # data access
    │   │   ├── services/      # business logic
    │   │   └── routers/       # API endpoints
    │   ├── alembic/           # migrations
    │   └── tests/
    │       ├── unit/
    │       ├── integration/
    │       └── conftest.py
    ├── client/                # React frontend
    └── docker-compose.yml
    ```
-   [x] Copy and adapt from bifrost:
    -   `docker-compose.yml` (Postgres+pgvector, PgBouncer, Redis, RabbitMQ, MinIO)
    -   `api/src/core/config.py` (settings pattern)
    -   `api/src/core/database.py` (async SQLAlchemy setup)
    -   `api/pyproject.toml` (dependencies)
-   [x] Configure Alembic for migrations
-   [x] Create `api/src/main.py` FastAPI app shell

**Test:** `docker-compose up -d` starts all services, API returns health check

### 1.2 Auth System ✅ COMPLETE

**Reference:** `../bifrost-api/api/src/core/auth.py`, `../bifrost-api/api/src/routers/auth.py`

-   [x] Create User ORM model + Pydantic contracts
-   [x] Create UserOrganization junction model
-   [x] Create Session model (refresh tokens)
-   [x] Create Passkey model (WebAuthn)
-   [x] Create UserMFAMethod + MFARecoveryCode models
-   [x] Create APIKey model
-   [x] Fork auth.py (UserPrincipal, ExecutionContext, JWT handling)
-   [x] Fork auth dependencies (get_current_user, etc.)
-   [x] Implement auth router:
    -   POST /api/auth/register
    -   POST /api/auth/login
    -   POST /api/auth/logout
    -   POST /api/auth/refresh
    -   POST /api/auth/passkey/register
    -   POST /api/auth/passkey/authenticate
    -   POST /api/auth/mfa/setup
    -   POST /api/auth/mfa/verify
-   [x] Implement API key authentication (check Bearer token against APIKey table)
-   [x] Write migrations

**Tests:**

-   [ ] Unit: JWT encoding/decoding, password hashing
-   [ ] Integration: register → login → access protected route
-   [ ] Integration: API key authentication flow

### 1.3 Organization CRUD ✅ COMPLETE

**Reference:** `../bifrost-api/api/src/models/orm/organization.py`

-   [x] Create Organization ORM model (id, name, created_at, updated_at)
-   [x] Create Organization Pydantic contracts (Create, Update, Public)
-   [x] Create OrganizationRepository
-   [x] Implement router:
    -   GET /api/organizations (list user's orgs)
    -   POST /api/organizations
    -   GET /api/organizations/:id
    -   PUT /api/organizations/:id
    -   DELETE /api/organizations/:id
-   [x] Add user to org on create (UserOrganization)
-   [x] Write migration

**Tests:**

-   [ ] Unit: repository methods
-   [ ] Integration: full CRUD cycle via API

---

## Phase 2: Core Entities ✅ COMPLETE

### 2.1 Password Entity ✅

-   [x] Create Password ORM model:
    -   id, organization_id, name, username, password_encrypted, url, notes, created_at, updated_at
-   [x] Create Pydantic contracts (Create, Update, Public - Public excludes password_encrypted)
-   [x] Create PasswordRepository (org-scoped)
-   [x] Implement encryption service (Fernet, reuse bifrost pattern)
-   [x] Implement router:
    -   GET /api/organizations/:org_id/passwords
    -   POST /api/organizations/:org_id/passwords
    -   GET /api/organizations/:org_id/passwords/:id
    -   GET /api/organizations/:org_id/passwords/:id/reveal (returns decrypted password)
    -   PUT /api/organizations/:org_id/passwords/:id
    -   DELETE /api/organizations/:org_id/passwords/:id
-   [x] Write migration

**Tests:**

-   [ ] Unit: encryption/decryption round-trip
-   [ ] Integration: create password, retrieve (without value), reveal (with value)
-   [ ] Integration: org isolation (can't access other org's passwords)

### 2.2 Configuration Entity ✅

-   [x] Create ConfigurationType ORM model (id, organization_id, name, created_at)
-   [x] Create ConfigurationStatus ORM model (id, organization_id, name, created_at)
-   [x] Create Configuration ORM model:
    -   id, organization_id, configuration_type_id, configuration_status_id
    -   name, serial_number, asset_tag, manufacturer, model
    -   ip_address, mac_address, notes, created_at, updated_at
-   [x] Create Pydantic contracts for all three
-   [x] Create repositories (org-scoped)
-   [x] Implement routers:
    -   CRUD for /api/organizations/:org_id/configuration-types
    -   CRUD for /api/organizations/:org_id/configuration-statuses
    -   CRUD for /api/organizations/:org_id/configurations
-   [x] Write migrations

**Tests:**

-   [ ] Integration: create type/status, create configuration referencing them
-   [ ] Integration: filter configurations by type/status

### 2.3 Location Entity ✅

-   [x] Create Location ORM model (id, organization_id, name, notes, created_at, updated_at)
-   [x] Create Pydantic contracts
-   [x] Create LocationRepository (org-scoped)
-   [x] Implement router: CRUD for /api/organizations/:org_id/locations
-   [x] Write migration

**Tests:**

-   [ ] Integration: full CRUD cycle

### 2.4 Document Entity ✅

-   [x] Create Document ORM model:
    -   id, organization_id, path, name, content, created_at, updated_at
-   [x] Create Pydantic contracts
-   [x] Create DocumentRepository (org-scoped)
    -   Add method: get_distinct_paths(org_id) for folder tree
-   [x] Implement router:
    -   GET /api/organizations/:org_id/documents (with optional path filter)
    -   GET /api/organizations/:org_id/documents/folders (distinct paths for tree)
    -   POST /api/organizations/:org_id/documents
    -   GET /api/organizations/:org_id/documents/:id
    -   PUT /api/organizations/:org_id/documents/:id
    -   DELETE /api/organizations/:org_id/documents/:id
-   [x] Write migration

**Tests:**

-   [ ] Integration: create docs at different paths, verify folder tree endpoint
-   [ ] Integration: move document (update path)

### 2.5 Attachments System ✅

**Reference:** `../bifrost-api/api/src/services/file_storage/`

-   [x] Create Attachment ORM model:
    -   id, organization_id, entity_type, entity_id, filename, s3_key, content_type, size_bytes, created_at
-   [x] Create Pydantic contracts
-   [x] Fork file_storage service (S3 upload/download/delete)
-   [x] Create AttachmentRepository
-   [x] Implement router:
    -   GET /api/organizations/:org_id/attachments?entity_type=X&entity_id=Y
    -   POST /api/organizations/:org_id/attachments (multipart upload)
    -   GET /api/organizations/:org_id/attachments/:id/download (presigned URL or stream)
    -   DELETE /api/organizations/:org_id/attachments/:id
-   [x] Implement embedded image upload for documents:
    -   POST /api/organizations/:org_id/documents/images (returns URL for markdown)
-   [x] Write migration

**Tests:**

-   [ ] Integration: upload file, list attachments, download, delete
-   [ ] Integration: upload image, get URL, verify accessible

---

## Phase 3: Custom Assets ✅ COMPLETE

### 3.1 CustomAssetType (Schema Builder) ✅

-   [x] Create CustomAssetType ORM model:
    -   id, organization_id, name, fields (JSONB), created_at, updated_at
-   [x] Define field schema structure:
    ```python
    class FieldDefinition(BaseModel):
        key: str
        name: str
        type: Literal["text", "textbox", "number", "date", "checkbox", "select", "header", "password"]
        required: bool = False
        show_in_list: bool = False
        hint: str | None = None
        default_value: str | None = None
        options: list[str] | None = None  # for select type
    ```
-   [x] Create Pydantic contracts with field validation
-   [x] Create CustomAssetTypeRepository (org-scoped)
-   [x] Implement router: CRUD for /api/organizations/:org_id/custom-asset-types
-   [x] Write migration

**Tests:**

-   [ ] Unit: field definition validation (select requires options, etc.)
-   [ ] Integration: create type with various field types, update fields

### 3.2 CustomAsset (Instances) ✅

-   [x] Create CustomAsset ORM model:
    -   id, organization_id, custom_asset_type_id, name, values (JSONB), created_at, updated_at
-   [x] Implement value encryption for password-type fields
-   [x] Create Pydantic contracts:
    -   Validate values against type's field definitions
    -   Exclude encrypted values from Public response (like Password entity)
-   [x] Create CustomAssetRepository (org-scoped)
-   [x] Implement router:
    -   GET /api/organizations/:org_id/custom-asset-types/:type_id/assets
    -   POST /api/organizations/:org_id/custom-asset-types/:type_id/assets
    -   GET /api/organizations/:org_id/custom-asset-types/:type_id/assets/:id
    -   GET /api/organizations/:org_id/custom-asset-types/:type_id/assets/:id/reveal (password fields)
    -   PUT /api/organizations/:org_id/custom-asset-types/:type_id/assets/:id
    -   DELETE /api/organizations/:org_id/custom-asset-types/:type_id/assets/:id
-   [x] Write migration

**Tests:**

-   [ ] Integration: create asset with all field types
-   [ ] Integration: password field encryption/reveal
-   [ ] Integration: validation against type schema

---

## Phase 4: Relationships ✅ COMPLETE

### 4.1 Relationship Entity ✅

-   [x] Create Relationship ORM model:
    -   id, organization_id, source_type, source_id, target_type, target_id, created_at
    -   Unique constraint on (source_type, source_id, target_type, target_id)
-   [x] Create Pydantic contracts
-   [x] Create RelationshipRepository:
    -   get_for_entity(org_id, entity_type, entity_id) - bidirectional query
    -   Prevent duplicate relationships (A→B same as B→A)
-   [x] Implement router:
    -   GET /api/organizations/:org_id/relationships?entity_type=X&entity_id=Y
    -   POST /api/organizations/:org_id/relationships
    -   DELETE /api/organizations/:org_id/relationships/:id
-   [x] Add endpoint to resolve related entities (return actual entity data, not just IDs):
    -   GET /api/organizations/:org_id/relationships/resolved?entity_type=X&entity_id=Y
-   [x] Write migration

**Tests:**

-   [ ] Integration: create relationship, query from both sides
-   [ ] Integration: prevent duplicate (A→B then B→A should fail or be idempotent)
-   [ ] Integration: resolved endpoint returns entity names/details

---

## Phase 5: Vector Search ✅ COMPLETE

### 5.1 Embedding Infrastructure ✅

**Reference:** `../bifrost-api/api/src/services/embeddings/`

-   [x] Create EmbeddingIndex ORM model:
    -   id, organization_id, entity_type, entity_id, content_hash, embedding (vector), searchable_text, created_at, updated_at
-   [x] Fork embeddings service (OpenAI ada-002 or compatible)
-   [x] Create search indexing worker:
    -   Listen to `search.index` queue
    -   Extract searchable text based on entity type
    -   Generate embedding
    -   Upsert to EmbeddingIndex
-   [x] Add message publishing on entity create/update/delete:
    -   Password: name + username + notes
    -   Configuration: name + serial + asset_tag + manufacturer + model + ip + notes
    -   Location: name + notes
    -   Document: name + path + content
    -   CustomAsset: name + non-password field values
-   [x] Write migration (ensure pgvector extension)

**Tests:**

-   [ ] Unit: searchable text extraction for each entity type
-   [ ] Integration: create entity → verify embedding indexed (may need to poll/wait)

### 5.2 Search API ✅

-   [x] Implement search endpoint:
    -   GET /api/search?q=...&org_id=... (org_id optional)
-   [x] Query flow:
    1. Get user's org IDs (or filter to specific org_id)
    2. Generate embedding for query
    3. Vector similarity search with org filter
    4. Return ranked results with entity_type, entity_id, organization_id, name, snippet
-   [x] Add text fallback search (ILIKE on searchable_text) if embedding service unavailable

**Tests:**

-   [ ] Integration: index multiple entities, search, verify relevance
-   [ ] Integration: cross-org search returns results from multiple orgs
-   [ ] Integration: org_id filter restricts results

---

## Phase 6: Frontend Foundation ✅ COMPLETE

### 6.1 Project Setup ✅

**Reference:** `../bifrost-api/client/`

-   [x] Initialize Vite + React + TypeScript project in `client/`
-   [x] Install and configure:
    -   shadcn/ui + TailwindCSS
    -   React Router
    -   TanStack Query
    -   Zustand (auth store)
-   [x] Set up path aliases (@/\*)
-   [x] Create API client with auth header injection
-   [x] Create auth store (user, tokens, login/logout actions)

**Test:** Dev server runs, renders hello world

### 6.2 Auth Pages ✅ (Partial - see Phase 11)

-   [x] Login page (email/password only - passkey UI pending Phase 11)
-   [x] Register page
-   [x] Setup page (first-time admin with passkey OR password)
-   [ ] MFA setup/verify flow (backend exists, UI not integrated)
-   [x] Protected route wrapper (redirect to login if unauthenticated)

**Test:** Manual - complete auth flow

### 6.3 Layout & Navigation ✅ (Needs redesign - see Phase 11)

-   [x] App shell with sidebar navigation
-   [x] Organization selector (dropdown or list)
-   [x] Sidebar nav items (Passwords, Configurations, Locations, Documents, Custom Assets)
-   [x] User menu (settings, logout)

**Test:** Manual - navigation works, org context persists

---

## Phase 7: Frontend - Entity Pages ✅ COMPLETE

### 7.1 Passwords UI ✅

-   [x] Password list page with search/filter
-   [x] Password detail page:
    -   Show name, username, URL, notes
    -   Click-to-reveal password with copy button
    -   Related items sidebar
    -   Attachments section
-   [x] Password create/edit modal or page

### 7.2 Configurations UI ✅

-   [x] Configuration list page with type/status filters
-   [x] Configuration detail page with all fields
-   [x] Related items sidebar
-   [x] Attachments section
-   [x] Create/edit form

### 7.3 Locations UI ✅

-   [x] Location list page
-   [x] Location detail page (simple - name, notes, related items, attachments)
-   [x] Create/edit form

### 7.4 Documents UI ✅

-   [x] Virtual folder tree sidebar
-   [x] Document list within folder
-   [x] Document detail/edit page:
    -   Markdown editor with preview
    -   Image upload (paste or button)
    -   Related items sidebar
    -   Attachments section
-   [x] Create document modal (select path)

### 7.5 Custom Assets UI ✅

-   [x] Asset type list (admin section)
-   [x] Asset type schema builder (drag-drop field ordering, field type config)
-   [x] Asset list page (per type)
-   [x] Asset detail page:
    -   Dynamic field rendering based on type schema
    -   Password field reveal
    -   Related items sidebar
    -   Attachments section
-   [x] Create/edit form with dynamic fields

---

## Phase 8: Frontend - Relationships & Search ✅ COMPLETE

### 8.1 Related Items Sidebar ✅

-   [x] Component showing all related entities for current item
-   [x] Grouped by entity type with icons
-   [x] Click navigates to related item
-   [x] "Add Related Item" button → modal to search and link

### 8.2 Command Palette (CMD+K) ✅

-   [x] Global keyboard shortcut listener
-   [x] Search input with debounce (300ms)
-   [x] Results grouped by type and organization
-   [x] Keyboard navigation (arrow keys, enter to select)
-   [x] Click/enter navigates to entity

---

## Phase 9: API Keys & Settings ✅ COMPLETE

### 9.1 API Key Management ✅

-   [x] Settings page with API keys section
-   [x] List existing keys (name, created, last used, expiry)
-   [x] Create new key modal (show key once, never again)
-   [x] Delete key with confirmation

### 9.2 User Settings ✅

-   [x] Profile settings (email, password change)
-   [x] Passkey management (add/remove)
-   [x] MFA management (enable/disable)

---

## Phase 10: Polish & Migration Prep ⚠️ PARTIAL

### 10.1 Migration Support

-   [ ] Document API endpoints for IT Glue migration scripts
-   [x] Ensure bulk create endpoints exist or work efficiently
-   [x] Test API key access to all endpoints

### 10.2 Final Testing

-   [ ] End-to-end test: create org, add all entity types, create relationships, search
-   [ ] Cross-browser testing (Chrome, Firefox, Safari)
-   [ ] Mobile responsiveness check

---

## Phase 11: V1 Fixes & UX Improvements ✅ COMPLETE

### 11.1 Organization Visibility Fix ✅

**Problem:** MSP users must be "in" an org to see it. Should see ALL orgs.

-   [x] Update `GET /api/organizations` to return all orgs for MSP users (not just linked via UserOrganization)
-   [x] Remove org membership check from GET/PUT endpoints
-   [x] Dashboard shows all client organizations
-   [x] UserOrganization table remains but isn't required for V1 access

### 11.2 Passkey Login ✅

**Problem:** Login page only has email/password. Passkey endpoints exist but no UI.

-   [x] Add "Login with Passkey" button to LoginPage
-   [x] Auto-trigger WebAuthn on page load (500ms delay)
-   [x] Fallback to email/password if passkey fails or user cancels
-   [x] Added passkey helper functions in `lib/passkeys.ts`

### 11.3 Sidebar Redesign ✅

**Problem:** Current sidebar is flat list. Should show config types as nav items with counts.

-   [x] Hide sidebar completely when no org selected (dashboard/org picker view)
-   [x] Show sidebar only after selecting an org
-   [x] Fetch configuration types and custom asset types (now global)
-   [x] Display as nav items with counts (via `/api/organizations/{org_id}/sidebar` endpoint)
-   [x] Group into sections: CORE (Passwords, Locations, Documents) and CUSTOM (config types + custom asset types)
-   [x] Remove generic "Configurations" and "Custom Assets" nav items
-   [x] Clicking a config type navigates to `/org/{orgId}/configurations?type={typeId}`
-   [x] Clicking a custom asset type navigates to `/org/{orgId}/assets/{typeId}`

### 11.4 Header & Navigation Restructure ✅

**Problem:** Navigation was confusing. Personal/Admin/Global tabs were unclear.

**Final header structure:** Dashboard | Organizations | Global | Settings

-   [x] **Dashboard** (`/`) - Placeholder welcome page
-   [x] **Organizations** (`/organizations`) - List of client orgs to select
-   [x] **Global** (`/global`) - Placeholder for viewing all data across orgs
-   [x] **Settings** (`/settings`) - Unified settings page with sidebar:
    -   Account: Profile, Security
    -   System: API Keys, Configuration Types, Configuration Statuses, Custom Asset Types
    -   Administration (superuser only): Users, Organizations
-   [x] Removed redundant Personal/Admin tabs
-   [x] Legacy redirects from `/personal/*` and `/admin/*` to `/settings`

### 11.5 Configuration Type/Status Management ✅

**Problem:** Can only create config types/statuses via API. No UI.

-   [x] Add management pages under Settings:
    -   `/settings/configuration-types` - CRUD for Configuration Types
    -   `/settings/configuration-statuses` - CRUD for Configuration Statuses
    -   `/settings/custom-asset-types` - CRUD for Custom Asset Types
-   [x] Types created here appear in sidebar nav

### 11.6 Make Types Global (Not Org-Scoped) ✅

**Problem:** ConfigurationType, ConfigurationStatus, CustomAssetType were per-org but should be global.

-   [x] Remove `organization_id` from ConfigurationType, ConfigurationStatus, CustomAssetType ORM models
-   [x] Add unique constraint on `name` for each type
-   [x] Move API endpoints to global paths:
    -   `/api/configuration-types`
    -   `/api/configuration-statuses`
    -   `/api/custom-asset-types`
-   [x] Read: any authenticated user; Write: superusers only
-   [x] Update frontend hooks to use global endpoints
-   [x] Update sidebar to fetch global types with per-org counts
-   [x] Created Alembic migration `20260112_009000_make_types_global.py`

---

## Phase 12: UX Polish & Data Tables ✅ COMPLETE

### 12.1 Searchable Organizations ✅

-   [x] Add search input to Organizations page (`/organizations`)
-   [x] Filter orgs by name as user types (debounced 300ms)
-   [x] OrgSelector converted to searchable Combobox using Command + Popover

### 12.2 Advanced Data Table ✅

-   [x] Created DataTable component using @tanstack/react-table
-   [x] Sortable columns (click header to sort asc/desc)
-   [x] Pinned/frozen columns (CSS sticky positioning)
-   [x] Added `pinned_columns` field to CustomAssetType schema
-   [x] Integrated DataTable into ConfigurationsPage

### 12.3 Document Folder Counts ✅

-   [x] API returns `{path: string, count: number}[]` from folders endpoint
-   [x] FolderTree displays count badges next to each folder
-   [x] Shows total count on "All Documents" and root folder count

### 12.4 Global Data View

-   [ ] Implement `/global` page to show data across ALL organizations
-   [ ] Aggregate view of configurations, documents, passwords, etc.
-   [ ] Filter by entity type
-   [ ] Show which org each item belongs to

### 12.5 OpenAI Configuration ✅

-   [x] AISettings ORM model for storing config in database
-   [x] API endpoints: GET/PUT `/api/settings/ai`, `/api/settings/ai/models`, `/api/settings/ai/test`
-   [x] Settings UI with API key input (masked), model selection dropdowns
-   [x] Connection status indicator and test button
-   [x] Migration: `20260112_010000_add_ai_settings_table.py`

### 12.6 Reindexing Capability ✅

-   [x] "Reindex" button in AI Settings page
-   [x] API endpoints: `POST /api/admin/reindex`, `GET /api/admin/reindex/status`, `GET /api/admin/index/stats`
-   [x] Filter by entity type or organization
-   [x] Real-time progress tracking with polling
-   [x] Index statistics display (total, by type, by org)

### 12.7 Hybrid Search (Text + Semantic) ✅

-   [x] Text search using PostgreSQL ILIKE across all entity types
-   [x] Semantic search using OpenAI embeddings (existing)
-   [x] New `mode` parameter: `auto`, `text`, `semantic`, `hybrid`
-   [x] Hybrid combines results, ranks semantic higher
-   [x] Graceful fallback to text search if OpenAI not configured

### 12.8 AI-Powered Search with RAG ✅

-   [x] New `POST /api/search/ai` endpoint with SSE streaming
-   [x] AIChatService for RAG-based responses
-   [x] Context built from top 30 search results
-   [x] CommandPalette "Ask AI" button with streaming response UI
-   [x] Citations with clickable links to source entities
-   [x] Simple markdown rendering for AI responses
-   [x] Graceful fallback if OpenAI not configured

---

## Phase 13: WebSocket Infrastructure & AI Config Overhaul ✅ COMPLETE

### 13.1 Port Searchable Combobox from bifrost-api ✅

-   [x] Ported Combobox component with:
    -   Search input for filtering
    -   Optional description per item
    -   Loading state with spinner
    -   Checkmark for selected item
-   [x] Used in model selection dropdowns in AISettings
-   [x] OrgSelector already uses Popover + Command pattern

### 13.2 WebSocket Infrastructure ✅

**Backend:**

-   [x] Created `api/src/core/pubsub.py` - ConnectionManager with Redis pub/sub
-   [x] Created `api/src/routers/websocket.py` - WebSocket endpoint
-   [x] Channel types: `reindex:{job_id}`, `search:{request_id}`, `user:{user_id}`
-   [x] Authentication via cookies/JWT
-   [x] Ping/pong keepalive (15s interval)
-   [x] Helper functions: `publish_reindex_progress()`, `publish_search_delta()`, etc.

**Frontend:**

-   [x] Created `client/src/services/websocket.ts` - WebSocketService singleton
-   [x] Created `client/src/hooks/useWebSocket.ts` - React hooks for subscriptions
-   [x] Reconnection with exponential backoff
-   [x] Typed message handlers

### 13.3 AI Configuration Overhaul ✅

-   [x] Renamed "Chat Model" to "Completions Model"
-   [x] Flow: Enter API key → Test → Fetch models from OpenAI API → Select → Save
-   [x] API key encrypted with Fernet before storage
-   [x] `POST /api/settings/ai/test` validates key and returns available models
-   [x] Model dropdowns hidden until AI is configured
-   [x] Combobox for model selection with descriptions
-   [x] Model display names: `gpt-4o-2024-11-20` → `GPT-4o`

### 13.4 Streaming via WebSocket ✅

-   [x] AI Search streaming via WebSocket
    -   `POST /api/search/ai` returns `request_id`
    -   Client subscribes to `search:{request_id}` channel
    -   Chunks: citations → delta → done
-   [x] Reindex progress via WebSocket
    -   Subscribe to `reindex:{job_id}` channel
    -   Real-time progress updates
    -   Removed polling-based approach

### 13.5 Embeddings Model Configuration ✅

-   [x] Added "Embeddings Model" dropdown
-   [x] Options fetched from OpenAI API (text-embedding-3-small, etc.)
-   [x] Stored in AI settings table
-   [x] Used for vector indexing

---

## Phase 14: Integrated Search & AI UX

### 14.1 Search Dialog Redesign ✅

**Goal:** Wider dialog with side-by-side results + AI panel

-   [x] Increase CommandDialog width to 768px (`sm:max-w-3xl`)
-   [x] Increase height to ~500px for more content
-   [x] Pre-AI state: results use full width
-   [x] Post-AI state: two-column layout (60% results, 40% AI panel)
-   [x] AI panel slides in from right (200ms ease-out animation)
-   [x] Both panels scroll independently

### 14.2 AI Trigger Improvements ✅

-   [x] Add Shift+Enter keyboard shortcut to trigger AI search
-   [x] Keep existing "Ask AI" button in footer
-   [x] Update footer hint: `Shift+↵ Ask AI`
-   [x] AI panel header: simple "AI Answer" with sparkle icon (no truncating title)

### 14.3 Markdown Rendering Overhaul ✅

**Reference:** `../bifrost-api/client/src/components/chat/ChatMessage.tsx`

Install dependencies:

```bash
npm install react-markdown remark-gfm rehype-raw react-syntax-highlighter
npm install -D @types/react-syntax-highlighter
```

-   [x] Replace custom MarkdownRenderer with react-markdown
-   [x] Add remark-gfm for GitHub Flavored Markdown (tables, strikethrough, task lists)
-   [x] Add rehype-raw for HTML support
-   [x] Add react-syntax-highlighter with Prism + oneDark theme
-   [x] Custom components for: code blocks, tables, blockquotes, links, lists

### 14.4 Citations Display ✅

-   [x] Keep citations visible (not collapsed) in AI panel
-   [x] Citations scroll with AI response content
-   [x] Clickable citation chips navigate to source entity

---

## Phase 15: Branding & OIDC Configuration ✅ COMPLETE

### 15.1 Rebrand to Bifrost Docs ✅

**Reference:** `../bifrost-api/client/`

Port branding from bifrost-api (brand family consistency):

-   [x] Update page title from "client" to "Bifrost Docs" in `client/index.html`
-   [x] Port `logo.svg` from `../bifrost-api/client/public/logo.svg`
-   [x] Port `Logo.tsx` component from `../bifrost-api/client/src/components/branding/`
-   [x] Update favicon with Bifrost icon
-   [x] Port primary color scheme from `../bifrost-api/client/src/index.css`:
    -   Primary: `oklch(0.38 0.09 220)` (teal/cyan)
    -   Dark mode primary: `oklch(0.6 0.13 220)`
-   [x] Update any "BifrostDocs" references in codebase to "Bifrost Docs"
-   [x] Update logo in header and login screen

### 15.2 OIDC/OAuth Configuration ✅

**Reference:** `../bifrost-api/api/src/routers/oauth_config.py`, `../bifrost-api/api/src/services/oauth_config_service.py`

**Backend:**

-   [x] Create SystemConfig ORM model for storing OAuth provider configs
    -   Category: `oauth_sso`
    -   Keys: `{provider}_client_id`, `{provider}_client_secret`, `{provider}_tenant_id`, etc.
    -   Secrets encrypted with Fernet
-   [x] Create UserOAuthAccount ORM model for linking OAuth accounts to users
-   [x] Port OAuth config service from bifrost-api:
    -   `OAuthConfigService` - CRUD for provider configs
    -   Microsoft, Google, generic OIDC support
-   [x] Port OAuth config router:
    -   `GET /api/settings/oauth` - List all provider configs with status
    -   `GET /api/settings/oauth/{provider}` - Get specific provider config
    -   `PUT /api/settings/oauth/microsoft` - Configure Microsoft Entra ID
    -   `PUT /api/settings/oauth/google` - Configure Google
    -   `PUT /api/settings/oauth/oidc` - Configure generic OIDC
    -   `DELETE /api/settings/oauth/{provider}` - Remove provider config
    -   `POST /api/settings/oauth/{provider}/test` - Test provider connectivity
-   [x] Port OAuth SSO router (login flow):
    -   `GET /auth/oauth/providers` - Get available configured providers
    -   `GET /auth/oauth/init/{provider}` - Initialize OAuth flow
    -   `POST /auth/oauth/callback` - Handle OAuth callback
    -   `GET /auth/oauth/accounts` - Get linked accounts
    -   `DELETE /auth/oauth/accounts/{provider}` - Unlink account
-   [x] Create migration for SystemConfig and UserOAuthAccount tables

**Frontend:**

-   [x] Port OAuth settings page from `../bifrost-api/client/src/pages/settings/OAuth.tsx`
    -   Provider cards (Microsoft, Google, OIDC)
    -   Configuration status badges
    -   Callback URL display with copy button
    -   Client ID/secret fields
    -   Test connectivity button
    -   Delete provider button
-   [x] Add "Single Sign-On" section to Settings sidebar
-   [x] Update Login page to show OAuth provider buttons:
    -   Fetch available providers from `/auth/oauth/providers`
    -   Display buttons for each configured provider (Microsoft, Google, OIDC)
    -   Provider icons/styling from bifrost-api
-   [x] Create OAuthCallback page for handling redirects

**Microsoft Entra ID Support:**

-   [x] Pre-configured provider option
-   [x] Tenant ID field (defaults to "common" for multi-tenant)
-   [x] Standard scopes: `openid profile email User.Read`
-   [x] Discovery URL: `https://login.microsoftonline.com/{tenant}/v2.0`

---

## Phase 16: User Roles & Permissions ✅ COMPLETE

### 16.1 Role System Migration ✅ COMPLETE

**Goal:** Replace `is_superuser` and `user_type` with single `role` enum.

-   [x] Create `UserRole` enum: `owner`, `administrator`, `contributor`, `reader`
-   [x] Add `role` column to User model (default: `contributor`)
-   [x] Remove `is_superuser` column from User model
-   [x] Remove `user_type` column and `UserType` enum
-   [x] Update setup flow: first user gets `owner` role automatically
-   [x] Add constraint: at least one owner must exist
-   [x] Write Alembic migration (`20260113_000000_add_user_role.py`)

**Tests:**

-   [x] Integration: role access tests (37 tests)
-   [x] Integration: cannot remove last owner

### 16.2 API Role Enforcement ✅ COMPLETE

**Goal:** Middleware checks role before allowing mutations.

-   [x] Auth dependencies include role in `ExecutionContext`
-   [x] Update `/api/admin/users` endpoints with role management
-   [x] Prevent owner deletion (can only change role)
-   [x] Create role-checking middleware: `require_role(min_role: UserRole)`
-   [x] Apply to routes:
    -   Reader: GET only (except `/api/preferences/*`)
    -   Contributor: all data CRUD, no settings
    -   Administrator: settings, user management (except owner changes)
    -   Owner: all actions including owner role changes

### 16.3 Frontend Role Enforcement ✅ COMPLETE

-   [x] Add `role` to auth store user object
-   [x] `isAdmin()`, `isOwner()` methods in auth store
-   [x] Add role selector to user management (with owner warning dialog)
-   [x] Create `usePermissions()` hook: `canEdit`, `canAccessSettings`, `canManageOwners`
-   [x] Hide edit/delete buttons for readers
-   [x] Hide Settings nav items for contributors/readers (redirect to /organizations)
-   [x] Disable form submissions based on role
-   [x] Show role badge on user menu

---

## Phase 17: DataTable Overhaul ✅ COMPLETE

### 17.1 Port DataTable from bifrost-api ✅ COMPLETE

**Reference:** `../bifrost-api/client/src/components/ui/data-table.tsx`

-   [x] Port DataTable component with:
    -   Column sorting (click headers) ✅
    -   Column visibility dropdown ✅
    -   Page number pagination (bottom) ✅
    -   Loading skeleton state ✅
    -   Column pinning support ✅
    -   Borderless search input (top of table) ✅
    -   Grey card background with sticky header + backdrop blur ✅
-   [x] Port supporting components:
    -   `TablePagination` with page numbers, prev/next, page size selector ✅
    -   `ColumnVisibilityDropdown` for showing/hiding columns ✅

### 17.2 Server-Side Pagination & Search ✅ COMPLETE

**Goal:** All list endpoints support pagination, search, sorting.

**API Changes (all list endpoints):**

-   [x] Add query params: `search`, `sort_by`, `sort_dir`, `limit`, `offset`
-   [x] Return response format: `{items: [...], total: int, limit: int, offset: int}`
-   [x] Implement search across relevant text fields per entity
-   [x] Apply to endpoints:
    -   `GET /api/organizations/{org_id}/passwords`
    -   `GET /api/organizations/{org_id}/configurations`
    -   `GET /api/organizations/{org_id}/locations`
    -   `GET /api/organizations/{org_id}/documents`
    -   `GET /api/organizations/{org_id}/custom-asset-types/{type_id}/assets`
-   [ ] Add global variants (org_id optional) - see Phase 18

**Frontend Changes:**

-   [ ] Create `useServerTable` hook (optional - current hooks work)
-   [x] List pages connected to paginated APIs

### 17.3 Column Filters ⚠️ PARTIAL

-   [x] Add filter popover to filterable columns
-   [x] Filter types:
    -   Dropdown for enum fields (configuration type, status)
    -   (Date range and text input can be added per-page as needed)
-   [x] DataTable accepts `filterableColumns` prop with options
-   [x] Column reordering UI (drag-drop in Columns dropdown)
-   [x] Column order persistence (localStorage, per-page key)
-   [ ] Wire filter params to API endpoints on list pages
-   [ ] Update API endpoints to accept filter params (some already do)

### 17.4 User Column Preferences ✅ COMPLETE

**New Table: `user_preferences`**

-   [x] Create ORM model:
    ```
    id: UUID
    user_id: UUID (FK)
    entity_type: str (e.g., "passwords", "configurations", "custom_asset_{type_id}")
    preferences: JSONB {columns: {visible: [], order: [], widths: {}}}
    created_at, updated_at
    UNIQUE(user_id, entity_type)
    ```
-   [x] Create Pydantic contracts
-   [x] Create repository
-   [x] Implement endpoints:
    -   `GET /api/preferences/{entity_type}` - returns user prefs or defaults
    -   `PUT /api/preferences/{entity_type}` - saves column selection
-   [x] Write migration (`20260113_003000_add_user_preferences_table.py`)

**Frontend:**

-   [x] Create `useColumnPreferences` hook with debounced saves
-   [x] Load preferences on table mount
-   [x] Column visibility changes update via API
-   [x] Column reordering UI (drag columns to reorder)
-   [x] Auto-save preferences on change (debounced 300ms)
-   [x] Default columns per entity type (hardcoded fallbacks)
-   [x] Custom assets use `pinned_columns` from type as defaults

---

## Phase 18: Global View ✅ COMPLETE

### 18.1 Global API Endpoints ✅ COMPLETE

**Goal:** All entities accessible without org_id filter.

-   [x] Add global variants:
    -   `GET /api/global/passwords` (all orgs)
    -   `GET /api/global/configurations` (all orgs)
    -   `GET /api/global/locations` (all orgs)
    -   `GET /api/global/documents` (all orgs)
    -   `GET /api/global/custom-assets?type_id=X` (with `type_id` filter)
-   [x] All responses include `organization_id` and `organization_name`
-   [x] `GET /api/global/sidebar` returns aggregate counts across all orgs

### 18.2 Global Page Implementation ✅ COMPLETE

-   [x] GlobalPage shows dashboard with entity cards and counts
-   [x] Add Organization column to all tables
-   [x] Organization column clickable → navigates to org view
-   [x] Global hooks (`useGlobalData.ts`) for all entity types
-   [x] Header "Global" link navigates to `/global`

### 18.3 Global Routes ✅ COMPLETE

-   [x] Add routes:
    ```
    /global
    /global/passwords
    /global/configurations
    /global/locations
    /global/documents
    /global/assets/:typeId
    ```

---

## Phase 19: Soft Delete for Types ✅ COMPLETE

### 19.1 Custom Asset Type Soft Delete ✅ COMPLETE

-   [x] Add `is_active: bool = True` to `custom_asset_types` table
-   [x] Write migration (`20260113_002000_add_is_active_to_types.py`)
-   [x] Update repository:
    -   `get_all()` excludes inactive by default
    -   `get_all(include_inactive=True)` for settings page
-   [x] Update delete endpoint:
    -   Check asset count before delete
    -   Return error if assets exist
-   [x] Add activate/deactivate endpoints:
    -   `POST /api/custom-asset-types/{id}/deactivate`
    -   `POST /api/custom-asset-types/{id}/activate`

### 19.2 Configuration Type/Status Soft Delete ✅ COMPLETE

-   [x] Add `is_active: bool = True` to `configuration_types` table
-   [x] Add `is_active: bool = True` to `configuration_statuses` table
-   [x] Write migration
-   [x] Activate/deactivate endpoints for both

### 19.3 Settings UI for Inactive Types ✅ COMPLETE

-   [x] Custom Asset Types page:
    -   Active types: normal styling, toggle ON
    -   Inactive types: muted/greyed (`opacity-50`), toggle OFF, badge "X assets"
    -   Delete button: disabled with tooltip when assets exist
-   [x] Configuration Types page: same pattern
-   [x] Configuration Statuses page: same pattern

---

## Phase 20: Tiptap Editor ✅ COMPLETE

### 20.1 Install & Configure Tiptap ✅ COMPLETE

-   [x] Install dependencies (@tiptap/react, starter-kit, image, link, placeholder)
-   [x] Create `TiptapEditor` component with full toolbar
-   [x] Create `TiptapToolbar` component
-   [x] Read-only mode support

### 20.2 Image Paste & Upload ✅ COMPLETE

-   [x] Intercept paste events (Ctrl+V with image data)
-   [x] Intercept drop events (drag image into editor)
-   [x] Upload to S3 via attachments API
-   [x] Error handling with toast notifications

### 20.3 Document Page Updates ✅ COMPLETE

-   [x] DocumentDetailPage uses TiptapEditor
-   [x] DocumentForm uses TiptapEditor
-   [x] **Inline editing toggle** - edit button toggles editable mode on page (not modal)
-   [x] **Editable title/path** - when editing, title and path are Input fields
-   [x] **Clean display view** - no border around content in display mode
-   [x] **H1/H2/H3 styling fixed** - CSS moved after Tailwind layers for proper cascade
-   [x] MarkdownEditor.tsx already cleaned up (doesn't exist)

---

## Phase 21: Data Export ✅ COMPLETE

### 21.1 Export Table & API ✅ COMPLETE

-   [x] Export ORM model with all fields
-   [x] Pydantic contracts
-   [x] Repository
-   [x] Migration (`20260113_001000_add_exports_table.py`)
-   [x] All API endpoints implemented

### 21.2 Export Worker ✅ COMPLETE

-   [x] Export service creates ZIP with all entity types
-   [x] Password decryption for export
-   [x] Custom asset password fields handled
-   [x] Document images as base64
-   [x] Attachments included
-   [x] Upload to S3

### 21.3 WebSocket Progress ✅ COMPLETE

-   [x] Progress publishing to `export:{export_id}` channel
### 21.4 Export Settings UI ✅ COMPLETE

-   [x] Add "Exports" to Settings sidebar (under Administration)
-   [x] Export list page with all features
-   [x] New Export modal with org selection and expiration
-   [x] Progress display with WebSocket updates
-   [x] useExports hooks

---

## Phase 22: Cleanup & Polish ✅ COMPLETE

### 22.1 Remove IT Glue References ✅ COMPLETE

-   [x] No active code references to IT Glue (only in PLAN.md history)
-   [x] Described as "open-source MSP documentation platform"

### 22.2 Custom Asset Pinned Columns UI ✅ COMPLETE

-   [x] `pinned_columns` field exists on CustomAssetType
-   [x] Pinned columns appear first (sticky left) in DataTable
-   [x] "Pin to table" checkbox per field in schema builder

### 22.3 Branding Consistency ✅ COMPLETE

-   [x] "Bifrost Docs" branding throughout
-   [x] Logo in header and login
-   [x] Page titles use "Bifrost Docs"

---

## REMAINING WORK (Consolidated)

### All Major Work Complete! ✅

**17.1 Built-in Search in DataTable** ✅ DONE
-   [x] Borderless search input at top of DataTable
-   [x] Already wired to `search` query param on list pages

**17.3 Column Filters** ✅ DONE
-   [x] Filter popover dropdowns added to DataTable
-   [x] Column reordering drag-drop in Columns dropdown

**17.4 User Column Preferences** ✅ DONE
-   [x] Created `user_preferences` table and API
-   [x] Column visibility persistence per user via API
-   [x] `useColumnPreferences` hook with debounced saves

**Phase 18: Global View** ✅ DONE
-   [x] Global API endpoints (`/api/global/*`)
-   [x] GlobalPage with entity cards and counts
-   [x] Organization column in all tables
-   [x] Routes: /global/passwords, /global/configurations, etc.

**Phase 20: Document Editor** ✅ DONE
-   [x] Inline editing toggle
-   [x] Editable title/path
-   [x] Clean display view
-   [x] H1/H2/H3 styling fixed (CSS cascade issue)

**Phase 19: Inactive Types UI** ✅ DONE
-   [x] Toggle/badge for inactive types in settings
-   [x] Greyed styling for deactivated types
-   [x] "X assets" count badge

**Phase 16: Role Enforcement** ✅ DONE
-   [x] `require_role` middleware on all routes
-   [x] `usePermissions()` hook
-   [x] Hide edit buttons for readers
-   [x] Role badge in user menu

### Minor Items Remaining

-   [x] Wire column filter params to API on configuration pages (Type/Status filters)
-   [x] Pin Organization column to left on all Global View pages

---

## Phase 23: OTP/TOTP Support

### 23.1 Password TOTP Field

**Goal:** Add TOTP secret storage to passwords with live code generation.

**Backend:**

-   [ ] Add `totp_secret_encrypted: str | None` column to Password ORM model
-   [ ] Update Password Pydantic contracts:
    -   `PasswordCreate` / `PasswordUpdate`: add optional `totp_secret: str | None`
    -   `PasswordPublic`: exclude `totp_secret_encrypted` (never expose)
    -   `PasswordReveal`: include decrypted `totp_secret` if present
-   [ ] Encrypt/decrypt TOTP secret using existing Fernet encryption
-   [ ] Write Alembic migration (`20260113_004000_add_totp_to_passwords.py`)

**Frontend:**

-   [ ] Add "OTP Secret" field to password create/edit form
    -   Text input for pasting TOTP secret (base32 encoded)
    -   Hint text: "Paste your TOTP secret (base32 format)"
-   [ ] Password reveal view shows TOTP code:
    -   Generate TOTP code client-side using `otpauth` library
    -   Display 6-digit code with circular countdown indicator (30s period)
    -   Code auto-refreshes when period expires
    -   Copy button for current code
-   [ ] Install `otpauth` npm package for TOTP generation

**Tests:**

-   [ ] Unit: TOTP secret encryption/decryption round-trip
-   [ ] Integration: create password with TOTP, reveal, verify secret returned

### 23.2 Custom Asset TOTP Field Type

**Goal:** Add `"totp"` as a custom asset field type.

**Backend:**

-   [ ] Add `"totp"` to `FieldDefinition.type` Literal in `api/src/models/contracts/custom_asset.py`
-   [ ] Update `custom_asset_validation.py`:
    -   Add `"totp"` case to `_validate_field_value()` (same as password - string)
    -   Add `"totp"` case to `encrypt_password_fields()` (encrypt with `_encrypted` suffix)
    -   Add `"totp"` case to `decrypt_password_fields()` (decrypt for reveal)
    -   Add `"totp"` case to `filter_password_fields()` (exclude from public response)

**Frontend:**

-   [ ] Add `"totp"` option to field type selector in schema builder
-   [ ] Custom asset form renders TOTP fields same as password fields (masked input)
-   [ ] Custom asset reveal view shows TOTP code with countdown and copy button
-   [ ] Share `TOTPDisplay` component between passwords and custom assets

### 23.3 TOTP Display Component

**Goal:** Reusable component for displaying live TOTP codes.

-   [ ] Create `TOTPDisplay` component (`client/src/components/ui/totp-display.tsx`):
    -   Props: `secret: string` (base32 TOTP secret)
    -   Generates 6-digit TOTP code using `otpauth` library
    -   Circular progress ring showing seconds until next code (30s period)
    -   Code updates automatically when period expires
    -   Copy button with toast notification
    -   Loading state while generating
    -   Error state for invalid secrets
-   [ ] Styling:
    -   Large monospace font for 6-digit code
    -   Circular countdown ring (primary color, 30px diameter)
    -   Ring empties as time progresses, refills on new code
    -   Smooth animation between codes

---

## Verification

After each phase:

1. `pytest` - all tests pass
2. `pyright` - zero type errors
3. `ruff check` - zero lint errors
4. Manual smoke test of new functionality

Final verification:

1. Fresh `docker-compose up` starts cleanly
2. Register user → see all orgs → select org → add password/config/location/doc/custom asset
3. Create relationships between entities
4. CMD+K search finds entities across orgs
5. API key can access all endpoints
6. Attachments upload/download works
7. Config types appear in sidebar with counts

---

## Key Files Reference (bifrost-api)

Copy/adapt these patterns:

-   `api/src/core/config.py` - settings
-   `api/src/core/database.py` - async SQLAlchemy
-   `api/src/core/auth.py` - JWT + UserPrincipal
-   `api/src/models/orm/*.py` - model patterns
-   `api/src/repositories/base.py` - generic repository
-   `api/src/services/file_storage/` - S3 abstraction
-   `api/src/services/embeddings/` - vector search
-   `api/tests/conftest.py` - test fixtures
-   `docker-compose.yml` - infrastructure

**OAuth/OIDC (Phase 15):**

-   `api/src/services/oauth_config_service.py` - OAuth provider config CRUD
-   `api/src/services/oauth_sso.py` - OAuth SSO flow logic
-   `api/src/routers/oauth_config.py` - Admin config endpoints
-   `api/src/routers/oauth_sso.py` - Login flow endpoints
-   `api/src/models/contracts/oauth_config.py` - Request/response contracts
-   `client/src/pages/settings/OAuth.tsx` - Admin config UI
-   `client/src/pages/Login.tsx` - OAuth login buttons
-   `client/src/components/branding/Logo.tsx` - Logo component
