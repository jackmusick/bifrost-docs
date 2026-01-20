# GitHub Sync

## Source of Truth (Codebase Review)

_Completed by Codebase Agent - 2026-01-20_

### Current Features

#### 1. GitHub Sync Architecture Overview

The GitHub Sync feature provides bidirectional synchronization between the Bifrost platform database and a GitHub repository. It operates on an **API-based model** with no local git folder required.

**Key Design Principles:**
- Database (DB) is the source of truth for "local" state
- All GitHub operations use the GitHub REST API (no Dulwich/local clone for operations)
- Conflict detection with user resolution support
- Orphan detection for production protection

**Core Files:**
- `/Users/jack/GitHub/bifrost/api/src/services/github_sync.py` - Main sync service (1750 lines)
- `/Users/jack/GitHub/bifrost/api/src/routers/github.py` - API endpoints (817 lines)
- `/Users/jack/GitHub/bifrost/client/src/components/editor/SourceControlPanel.tsx` - Main UI component (971 lines)

#### 2. Sync Preview System

The sync process uses a **preview-then-execute** pattern:

1. **GET /api/github/sync** - Preview changes without executing
2. **POST /api/github/sync** - Execute sync with conflict resolutions (returns job_id)
3. **WebSocket (git:{job_id})** - Stream progress and completion

**Preview Response Structure** (`SyncPreviewResponse`):
- `to_pull: list[SyncAction]` - Files to download from GitHub
- `to_push: list[SyncAction]` - Files to upload to GitHub
- `conflicts: list[SyncConflictInfo]` - Files with conflicts needing resolution
- `will_orphan: list[OrphanInfo]` - Workflows that will become orphaned
- `unresolved_refs: list[SyncUnresolvedRefInfo]` - Portable refs that cannot be resolved
- `serialization_errors: list[SyncSerializationError]` - Entities that failed to serialize
- `is_empty: bool` - True if no changes

**File:** `/Users/jack/GitHub/bifrost/api/src/models/contracts/github.py` (lines 394-549)

#### 3. Virtual File System

Platform entities (forms, agents, apps) are stored in database tables, NOT in `workspace_files`. The `VirtualFileProvider` serializes these entities on-the-fly for GitHub sync.

**Virtual File Paths:**
- Forms: `forms/{uuid}.form.json`
- Agents: `agents/{uuid}.agent.json`
- Apps: `apps/{slug}/app.json` + `apps/{slug}/**/*` (directory-based)

**File:** `/Users/jack/GitHub/bifrost/api/src/services/github_sync_virtual_files.py`

**Key Class: `VirtualFileProvider`**
```python
class VirtualFileProvider:
    async def get_all_virtual_files() -> VirtualFileResult
    async def get_virtual_file_by_id(entity_type, entity_id) -> VirtualFile | None
    @staticmethod is_virtual_file_path(path) -> bool
    @staticmethod get_entity_type_from_path(path) -> str | None
    @staticmethod extract_id_from_filename(filename) -> str | None
```

**VirtualFile dataclass:**
```python
@dataclass
class VirtualFile:
    path: str           # e.g., "forms/{uuid}.form.json"
    entity_type: str    # "form", "agent", "app", "app_file"
    entity_id: str      # UUID string
    content: bytes | None
    computed_sha: str | None  # Git blob SHA
```

#### 4. Entity Indexers

Indexers handle importing virtual files from GitHub back into the database.

**Files:**
- `/Users/jack/GitHub/bifrost/api/src/services/file_storage/indexers/form.py` - `FormIndexer`
- `/Users/jack/GitHub/bifrost/api/src/services/file_storage/indexers/agent.py` - `AgentIndexer`
- `/Users/jack/GitHub/bifrost/api/src/services/file_storage/indexers/app.py` - `AppIndexer`

**FormIndexer Key Methods:**
```python
class FormIndexer:
    async def index_form(path, content, workspace_file) -> bool  # Import form
    async def delete_form_for_file(path) -> int  # Delete form
    async def resolve_workflow_name_to_id(workflow_name) -> str | None
```

**AppIndexer Key Methods:**
```python
class AppIndexer:
    async def index_app_json(path, content) -> bool  # Import app.json
    async def index_app_file(path, content) -> bool  # Import app code file
    async def delete_app(slug) -> int
    async def delete_app_file(path) -> int
```

**AgentIndexer Key Methods:**
```python
class AgentIndexer:
    async def index_agent(path, content, workspace_file) -> bool
    async def delete_agent_for_file(path) -> int
```

#### 5. Portable Workflow References

Entities (forms, agents) reference workflows by UUID. For portability across environments, these are transformed to `path::function_name` format during export.

**File:** `/Users/jack/GitHub/bifrost/api/src/services/file_storage/ref_translation.py`

**Key Functions:**
```python
# Export: UUID -> path::function_name
async def build_workflow_ref_map(db) -> dict[str, str]

# Import: path::function_name -> UUID
async def build_ref_to_uuid_map(db) -> dict[str, str]

# Transform functions
def transform_workflow_refs(data, workflow_map) -> list[str]
def transform_path_refs_to_uuids(data, workflow_ref_fields, ref_to_uuid) -> list[UnresolvedRef]
```

**Export Metadata:**
When serializing, entities include `_export` metadata:
```json
{
  "_export": {
    "workflow_refs": ["workflow_id", "launch_workflow_id", "form_schema.fields.*.data_provider_id"],
    "version": "1.0"
  }
}
```

#### 6. Entity Metadata for UI Display

The sync preview enriches actions with entity metadata for human-readable display.

**File:** `/Users/jack/GitHub/bifrost/api/src/services/github_sync_entity_metadata.py`

```python
@dataclass
class EntityMetadata:
    entity_type: str | None  # "form", "agent", "app", "app_file", "workflow"
    display_name: str
    parent_slug: str | None  # For app_file: parent app slug

def extract_entity_metadata(path, content=None) -> EntityMetadata
```

**Path Patterns Detected:**
- `forms/*.form.json` -> form
- `agents/*.agent.json` -> agent
- `apps/{slug}/app.json` -> app
- `apps/{slug}/**/*` -> app_file
- `workflows/*.py` or `data_providers/*.py` -> workflow

#### 7. Entity-Centric UI Display

The frontend groups sync actions by entity for cleaner display.

**Files:**
- `/Users/jack/GitHub/bifrost/client/src/components/editor/EntitySyncItem.tsx`
- `/Users/jack/GitHub/bifrost/client/src/components/editor/groupSyncActions.ts`

**groupSyncActions Function:**
- Apps are grouped with their files as children
- Forms, agents, workflows remain as individual items
- Groups sorted alphabetically by display name

**EntitySyncItem Component:**
- Shows entity with appropriate icon (form=FileText, agent=Bot, app=AppWindow, workflow=Workflow)
- Action icons (add=Plus, modify=Edit3, delete=Minus)
- Expandable file list for apps
- Conflict resolution buttons (Keep Local / Keep Remote)

#### 8. Conflict Resolution

When local and remote differ, users must resolve conflicts before sync.

**Conflict Resolution Options:**
- `keep_local` - Push local version to GitHub
- `keep_remote` - Pull remote version from GitHub
- `skip` - Exclude entity from sync

**UI Location:** `ConflictList` component in SourceControlPanel.tsx (lines 727-795)

#### 9. Orphan Detection

Detects workflows that will become orphaned after sync (file deleted or function removed).

**OrphanInfo Structure:**
```python
class OrphanInfo(BaseModel):
    workflow_id: str
    workflow_name: str
    function_name: str
    last_path: str
    used_by: list[WorkflowReference]  # Forms, apps, agents using this workflow
```

Users must confirm orphans before sync proceeds.

#### 10. GitHub API Client

**File:** `/Users/jack/GitHub/bifrost/api/src/services/github_sync.py` (lines 236-493)

**GitHubAPIClient Methods:**
- `get_tree(repo, sha, recursive)` - List files in repo
- `get_blob_content(repo, sha)` - Read file content
- `create_blob(repo, content)` - Create new blob
- `create_tree(repo, tree_items, base_tree)` - Create new tree
- `create_commit(repo, message, tree, parents)` - Create commit
- `get_ref(repo, ref)` / `update_ref(repo, ref, sha)` - Manage branch refs
- `get_commit(repo, sha)` - Get commit details

#### 11. Frontend Hooks

**File:** `/Users/jack/GitHub/bifrost/client/src/hooks/useGitHub.ts`

**Query Hooks:**
- `useGitStatus()` - Current Git/GitHub status
- `useGitHubConfig()` - Configuration status
- `useGitHubRepositories()` - List accessible repos
- `useGitCommits(limit, offset)` - Commit history
- `useGitHubBranches(repoFullName)` - List branches

**Mutation Hooks:**
- `useValidateGitHubToken()` - Validate and save token
- `useConfigureGitHub()` - Configure repo/branch
- `useCreateGitHubRepository()` - Create new repo
- `useDisconnectGitHub()` - Remove integration
- `useSyncPreview()` - Get sync preview
- `useSyncExecute()` - Execute sync (queues job)

### Recent Changes

Based on the codebase structure and patterns observed:

1. **App Indexing (AppIndexer)** - Apps are now synced as directories with:
   - `apps/{slug}/app.json` for metadata
   - `apps/{slug}/**/*` for code files (pages, components, modules)
   - Dependencies parsed and stored in `app_file_dependencies` table

2. **Entity-Centric Sync Display** - UI groups changes by entity type:
   - Apps shown with expandable file lists
   - Entity icons (form, agent, app, workflow)
   - Parent-child relationship for app files

3. **Virtual File System** - Platform entities serialize on-demand:
   - No workspace_files entry for forms/agents/apps
   - Computed git blob SHA for fast comparison
   - Portable workflow refs in export metadata

4. **Serialization Error Handling** - Graceful handling when entities fail to serialize:
   - Errors surfaced in sync preview
   - Users can acknowledge and continue

5. **WebSocket Progress Streaming** - Real-time sync progress via WebSocket:
   - Phase, current/total counts, file path
   - Completion message with success/error status

### Key Concepts to Document

1. **GitHub Sync Architecture**
   - API-based sync (no local git folder)
   - Preview-then-execute pattern
   - WebSocket progress streaming

2. **Virtual Files vs Workspace Files**
   - When entities become virtual files
   - Path patterns and naming conventions
   - SHA computation for comparison

3. **Portable Workflow References**
   - UUID to path::function_name transformation
   - Export metadata (_export field)
   - Unresolved reference handling

4. **Entity Indexers**
   - How forms/agents/apps are imported
   - ID alignment and preservation
   - Environment-specific fields (org_id, access_level)

5. **Conflict Resolution**
   - What triggers a conflict
   - Resolution options
   - Orphan workflow handling

6. **App Directory Structure**
   - app.json metadata format
   - Code file organization
   - Dependency tracking

7. **GitHub Configuration Flow**
   - Token validation
   - Repository selection
   - Branch configuration

8. **Source Control Panel UI**
   - Entity-centric display
   - Sync preview sections (incoming/outgoing)
   - Commit history display

---

## Documentation State (Docs Review)

_Completed by Docs Review Agent - 2026-01-20_

### Existing Documentation

**No dedicated GitHub Sync documentation exists.** The feature is only mentioned in passing:

| File | Content Related to Git/GitHub |
|------|------------------------------|
| `/src/content/docs/core-concepts/platform-overview.mdx` | Brief mention: "Use VS Code, Claude Code, and Git for version control" in capabilities list |
| `/src/content/docs/getting-started/installation.mdx` | Only mentions `git clone` for installing Bifrost itself |
| `/src/content/docs/how-to-guides/local-dev/setup.mdx` | Mentions Git as a prerequisite tool, no sync documentation |
| `/src/content/docs/about/index.mdx` | Marketing mention: "Use VS Code, Claude Code, and Git for version control" |
| `/src/content/docs/getting-started/for-non-developers.mdx` | Lists Git as a tool to install, no functional documentation |
| `/src/content/docs/index.mdx` | No GitHub sync mentions |

**Key Finding**: There are **zero pages** documenting how to actually use GitHub sync, configure it, or understand the virtual file system.

### Gaps Identified

#### Critical Gaps (Feature is completely undocumented)

1. **No Getting Started Guide for GitHub Sync**
   - How to connect a GitHub account (token setup)
   - How to select/create a repository
   - How to configure branch settings
   - Initial sync workflow

2. **No Architecture/Concepts Documentation**
   - API-based sync model (no local git folder)
   - Preview-then-execute pattern
   - Database as source of truth for "local" state
   - Virtual file system concept

3. **No Virtual Files Documentation**
   - What entities become virtual files (forms, agents, apps)
   - Path patterns (`forms/*.form.json`, `agents/*.agent.json`, `apps/{slug}/`)
   - Difference between workspace files and virtual files
   - How SHA computation works for comparison

4. **No Portable Workflow References Documentation**
   - UUID to `path::function_name` transformation
   - Export metadata (`_export` field)
   - How references resolve on import
   - Handling unresolved references

5. **No Conflict Resolution Documentation**
   - What triggers a conflict
   - Resolution options (keep_local, keep_remote, skip)
   - Orphan workflow detection and handling
   - UI workflow for resolving conflicts

6. **No App Directory Structure Documentation**
   - `app.json` metadata format
   - Code file organization within app directories
   - Dependency tracking between app files

7. **No Source Control Panel UI Documentation**
   - Entity-centric display (grouped by form/agent/app/workflow)
   - Sync preview sections (incoming/outgoing)
   - Commit history display
   - Icons and status indicators

8. **No Troubleshooting Documentation**
   - Serialization errors
   - Authentication issues
   - Common sync failure scenarios

#### Secondary Gaps

9. **Entity Indexers Not Documented**
   - How forms/agents/apps are imported from GitHub
   - ID preservation and alignment
   - Environment-specific field handling (org_id, access_level)

10. **WebSocket Progress Streaming Not Documented**
    - Real-time sync progress via WebSocket
    - Phase, current/total counts, file path indicators

11. **Frontend Hooks Not Documented**
    - `useGitStatus()`, `useGitHubConfig()`, etc.
    - Available for custom integrations

### Recommended Actions

#### Phase 1: Core Documentation (High Priority)

1. **Create `/how-to-guides/source-control/github-setup.mdx`**
   - Connect GitHub account
   - Create or select repository
   - Configure branch
   - First sync walkthrough
   - Screenshots of UI

2. **Create `/core-concepts/github-sync.mdx`**
   - Architecture overview (API-based, no local git)
   - Preview-then-execute pattern
   - Virtual file system explained
   - Entity serialization
   - Portable workflow references

3. **Create `/how-to-guides/source-control/syncing-changes.mdx`**
   - Pull/push workflow
   - Understanding the sync preview
   - Entity-centric display
   - Executing sync

4. **Create `/how-to-guides/source-control/conflict-resolution.mdx`**
   - What causes conflicts
   - Resolution options with screenshots
   - Orphan workflows
   - Best practices

#### Phase 2: Reference Documentation (Medium Priority)

5. **Create `/reference/virtual-files.mdx`**
   - Complete path patterns
   - Entity types and their file formats
   - Export metadata structure
   - SHA computation

6. **Create `/reference/app-directory-structure.mdx`**
   - app.json schema
   - File organization conventions
   - Dependency tracking

7. **Add to `/troubleshooting/github-sync.md`** (create new)
   - Common errors and solutions
   - Authentication issues
   - Serialization failures
   - Unresolved references

#### Phase 3: Update Existing Docs (Low Priority)

8. **Update `/core-concepts/platform-overview.mdx`**
   - Add section on version control integration
   - Link to GitHub sync docs

9. **Update `/how-to-guides/local-dev/setup.mdx`**
   - Add section on syncing local changes via GitHub
   - Workflow for local development with sync

10. **Update `/getting-started/` section**
    - Consider adding GitHub sync to the getting started flow
    - Or create optional "Set up version control" step

#### Documentation Structure Recommendation

```
src/content/docs/
├── core-concepts/
│   └── github-sync.mdx               # NEW: Architecture & concepts
├── how-to-guides/
│   └── source-control/               # NEW: Directory
│       ├── github-setup.mdx          # NEW: Initial setup
│       ├── syncing-changes.mdx       # NEW: Daily workflow
│       └── conflict-resolution.mdx   # NEW: Handling conflicts
├── reference/
│   ├── virtual-files.mdx             # NEW: Virtual file reference
│   └── app-directory-structure.mdx   # NEW: App file structure
└── troubleshooting/
    └── github-sync.md                # NEW: Troubleshooting guide
```
