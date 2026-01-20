# Entity Management

## Source of Truth (Codebase Review)

_Completed by Codebase Agent - January 2026_

### Current Features

#### 1. Entity Management Page (`/dependencies`)

**Location**: `/Users/jack/GitHub/bifrost/client/src/pages/EntityManagement.tsx`

The Entity Management page provides a unified interface for managing all platform entities (workflows, forms, agents, apps) with the following capabilities:

**Core Features**:
- **Unified Entity List**: Displays all entity types in a single, filterable list
- **Multi-select**: Checkbox selection for batch operations on multiple entities
- **Drag-and-Drop Reassignment**: Drag entities to organization or role drop targets to reassign them
- **Search and Filter**: Text search plus filters for entity type, organization, and access level
- **Sorting**: Sort by name, date, or type with ascending/descending toggle
- **Dependency Visualization**: View entity relationships via dependency graph dialog

**UI Components**:
- `EntityCard`: Displays entity with name, type badge, organization, access level, and creation date
- `OrgDropTarget`: Drop target for reassigning entities to organizations (or "Global")
- `RoleDropTarget`: Drop target for setting access levels (Authenticated, Clear Roles, or specific roles)
- `FilterPopover`: Command-based filter UI for type/org/access filtering
- `DependencyGraphDialog`: Modal showing React Flow dependency visualization

**Navigation**: Located in sidebar under "Configuration" > "Entity Management" (route: `/dependencies`)

#### 2. Entity Types

The platform manages four distinct entity types:

| Entity Type | Storage Location | Organization Scoped | File-Based |
|-------------|-----------------|---------------------|------------|
| **Workflow** | `workflows` table | Yes (nullable) | Yes (.py files with decorators) |
| **Form** | `forms` table | Yes (nullable) | Yes (.form.json files) |
| **Agent** | `agents` table | Yes (nullable) | Yes (.agent.json files) |
| **Application** | `applications` table | Yes (nullable) | Yes (TSX/TypeScript code files) |

**Key ORM Models**:
- `/Users/jack/GitHub/bifrost/api/src/models/orm/workflows.py` - Workflow model (also stores data_providers and tools)
- `/Users/jack/GitHub/bifrost/api/src/models/orm/forms.py` - Form and FormField models
- `/Users/jack/GitHub/bifrost/api/src/models/orm/agents.py` - Agent model with tools/delegations
- `/Users/jack/GitHub/bifrost/api/src/models/orm/applications.py` - Application model with versioning

#### 3. Mass Reassignment

**Organization Reassignment** (`handleOrgDrop`):
- Workflows: Updates `organization_id` via `PATCH /api/workflows/{id}`
- Forms: Cannot be changed after creation (shows error toast)
- Agents: Updates via `PUT /api/agents/{id}`
- Apps: Updates via `PATCH /api/applications/{slug}` with `scope` parameter

**Access Level Reassignment** (`handleRoleDrop`):
- Supports setting access to "authenticated" (all authenticated users)
- Supports "clear-roles" action (sets to role_based with no roles assigned)
- Individual role assignment changes access_level to "role_based"

**Hooks Used**:
- `useUpdateWorkflow()` - `/Users/jack/GitHub/bifrost/client/src/hooks/useWorkflows.ts`
- `useUpdateForm()` - `/Users/jack/GitHub/bifrost/client/src/hooks/useForms.ts`
- `useUpdateAgent()` - `/Users/jack/GitHub/bifrost/client/src/hooks/useAgents.ts`
- `useUpdateApplication()` - `/Users/jack/GitHub/bifrost/client/src/hooks/useApplications.ts`

#### 4. Dependency Graph Visualization

**Backend Service**: `/Users/jack/GitHub/bifrost/api/src/services/dependency_graph.py`

The `DependencyGraphService` class builds entity relationship graphs using BFS traversal:

**Data Models**:
- `GraphNode`: Entity node with id, type, name, org_id
- `GraphEdge`: Relationship edge with source, target, relationship type
- `DependencyGraph`: Collection of nodes and edges with root_id

**Relationship Types**:
- Forms USE workflows (main workflow, launch workflow, data providers)
- Apps USE workflows (via `useWorkflow()` hook in code files)
- Agents USE workflows (via agent_tools junction table)
- Workflows are USED BY forms, apps, and agents (reverse lookups)

**API Endpoint**: `GET /api/dependencies/{entity_type}/{entity_id}?depth={1-5}`
- **Router**: `/Users/jack/GitHub/bifrost/api/src/routers/dependencies.py`
- Platform admin only access
- Returns graph with configurable traversal depth (default: 2, max: 5)

**Frontend Components**:
- `/Users/jack/GitHub/bifrost/client/src/hooks/useDependencyGraph.ts` - Query hook
- `/Users/jack/GitHub/bifrost/client/src/components/dependencies/DependencyGraph.tsx` - React Flow visualization
- `/Users/jack/GitHub/bifrost/client/src/components/dependencies/EntityNode.tsx` - Custom node component

**Visualization Features**:
- Uses dagre for hierarchical auto-layout
- Color-coded nodes by entity type (blue=workflow, green=form, purple=app, orange=agent)
- Animated edges with directional arrows
- MiniMap for navigation
- Legend panel
- Root node highlighting

#### 5. Entity Virtualization

Forms and Agents are "virtual" entities - they exist only in the database but are serialized on-the-fly for Git sync:

**Entity Detection Service**: `/Users/jack/GitHub/bifrost/api/src/services/file_storage/entity_detector.py`

The `detect_platform_entity_type()` function determines storage location:
- `.form.json` files -> Form (database storage)
- `.agent.json` files -> Agent (database storage)
- `.py` files with `@workflow`, `@tool`, `@data_provider` decorators -> Workflow (database storage)
- `.py` files without decorators -> Module (workspace_files content)
- Other files -> S3 storage

**Entity Resolution Service**: `/Users/jack/GitHub/bifrost/api/src/services/file_storage/entity_resolution.py`

Handles resolving entity references by ID or name, with legacy name-based lookup fallback.

#### 6. Entity-Organization Relationships

**Scoping Pattern**:
- `organization_id = NULL` -> Global entity (platform-wide)
- `organization_id = UUID` -> Organization-scoped entity

**Access Control**:
- `access_level = "authenticated"` -> Any authenticated user can access
- `access_level = "role_based"` -> Only users with assigned roles can access

**Role Junction Tables**:
- `form_roles` - Associates forms with roles
- `agent_roles` - Associates agents with roles
- `workflow_roles` - Associates workflows with roles
- `app_roles` - Associates applications with roles

**API Routers**:
- `/Users/jack/GitHub/bifrost/api/src/routers/workflows.py` - Workflow CRUD with org scoping
- `/Users/jack/GitHub/bifrost/api/src/routers/forms.py` - Form CRUD with org scoping
- `/Users/jack/GitHub/bifrost/api/src/routers/agents.py` - Agent CRUD with role-based access
- `/Users/jack/GitHub/bifrost/api/src/routers/applications.py` - Application CRUD with cascading scope
- `/Users/jack/GitHub/bifrost/api/src/routers/roles.py` - Role management and assignments

### Recent Changes

Based on commit history and code analysis:

1. **Entity Management Page**: Replaced former "Dependencies" page with comprehensive entity management
2. **Mass Reassignment**: Added drag-and-drop for bulk organization and role changes
3. **Dependency Graph**: Integrated React Flow visualization with relationship filtering
4. **Clear Roles Action**: Added ability to remove all role assignments from entities
5. **App File Dependencies**: Uses `app_file_dependencies` table for tracking workflow references in code

### Key Concepts to Document

1. **Entity Types Overview**
   - Four entity types: Workflows, Forms, Agents, Applications
   - Storage mechanisms (database vs file-based)
   - Type discriminators in workflows table (workflow, tool, data_provider)

2. **Organization Scoping**
   - Global vs org-scoped entities
   - Cascade scoping pattern (org-specific + global fallback)
   - Filter types: ALL, GLOBAL_ONLY, ORG_ONLY, ORG_PLUS_GLOBAL

3. **Access Control**
   - Access levels: authenticated vs role_based
   - Role assignment via junction tables
   - Clear roles operation

4. **Mass Reassignment Operations**
   - Drag-and-drop interface
   - Organization reassignment limitations (forms cannot be changed)
   - Batch operations on selected entities

5. **Dependency Graph**
   - Relationship types (uses/used_by)
   - BFS traversal algorithm
   - Visualization with React Flow/dagre

6. **Entity Virtualization**
   - Forms and agents as database-only entities
   - Git sync serialization
   - Entity detection from file extensions and decorators

7. **API Endpoints Reference**
   - CRUD operations for each entity type
   - Dependency graph endpoint
   - Role assignment endpoints

---

## Documentation State (Docs Review)

_Completed by Docs Review Agent - January 2026_

### Existing Docs

The following documentation files touch on concepts related to Entity Management:

| File | Coverage | Relevance |
|------|----------|-----------|
| `/src/content/docs/core-concepts/scopes.mdx` | Global vs organization scoping | Partial - explains scope concept but not how to change entity scope |
| `/src/content/docs/core-concepts/permissions.md` | Roles and access levels | Partial - explains role-based access but not how to bulk assign |
| `/src/content/docs/core-concepts/workflows.mdx` | Workflow concepts | Minimal - mentions org-scoping but not entity management |
| `/src/content/docs/core-concepts/forms.mdx` | Form concepts | Minimal - security section mentions scoping |
| `/src/content/docs/core-concepts/app-builder.mdx` | Application concepts | Minimal - mentions permissions but not entity management |
| `/src/content/docs/how-to-guides/ai/agents-and-chat.mdx` | Agent concepts | Minimal - covers access levels but not bulk management |

**No dedicated Entity Management documentation exists.**

### Gaps Identified

#### Critical Gaps (Feature Completely Undocumented)

1. **Entity Management Page Not Documented**
   - The `/dependencies` route and Entity Management UI are not mentioned anywhere
   - Users have no guidance on how to find or use this feature
   - The unified entity list view is not explained

2. **Mass Reassignment Operations Not Documented**
   - Drag-and-drop interface for changing entity organization is not explained
   - Batch selection and multi-entity operations are not documented
   - Limitations (e.g., forms cannot change organization after creation) are not communicated
   - Access level bulk changes are not documented

3. **Dependency Graph Visualization Not Documented**
   - The dependency graph feature is completely undocumented
   - Relationship types (forms USE workflows, apps USE workflows, etc.) are not explained
   - The visualization controls and navigation are not covered
   - The API endpoint `GET /api/dependencies/{entity_type}/{entity_id}` is not referenced

4. **Entity Virtualization Concept Not Documented**
   - How forms and agents are "virtual" (database-only) entities is not explained
   - File extension conventions (.form.json, .agent.json) are not documented
   - The entity detection logic for Git sync is not covered

#### Moderate Gaps (Partially Covered Elsewhere)

5. **Entity-Organization Relationship Model Incomplete**
   - `scopes.mdx` explains the concept of global vs organization scoping
   - Missing: How to change an entity's organization assignment
   - Missing: The filter types (ALL, GLOBAL_ONLY, ORG_ONLY, ORG_PLUS_GLOBAL)
   - Missing: Cascade scoping behavior in detail

6. **Access Control Documentation Fragmented**
   - `permissions.md` explains roles conceptually
   - Missing: How access_level affects entity visibility
   - Missing: The "Clear Roles" operation
   - Missing: Role junction tables and their implications

7. **Entity Types Overview Missing**
   - Each entity type (workflow, form, agent, app) has its own conceptual doc
   - Missing: Unified comparison showing how all entity types share common patterns
   - Missing: The type discriminator system (workflow, tool, data_provider in workflows table)

#### Minor Gaps

8. **API Reference for Entity Operations**
   - CRUD endpoints for each entity type are not comprehensively documented
   - The dependency graph API is undocumented
   - Batch update patterns are not explained

### Recommended Actions

#### Priority 1: Create Core Entity Management Documentation

1. **Create `/src/content/docs/core-concepts/entity-management.mdx`**
   - Overview of the four entity types (Workflows, Forms, Agents, Applications)
   - Common properties across entities (organization_id, access_level, roles)
   - Entity lifecycle (creation, update, deletion)
   - Link to Entity Management UI guide

2. **Create `/src/content/docs/how-to-guides/admin/entity-management.mdx`**
   - How to access the Entity Management page
   - Filtering and searching entities
   - Selecting multiple entities
   - Drag-and-drop reassignment to organizations
   - Drag-and-drop access level changes
   - Viewing dependency graphs
   - Common administrative tasks

#### Priority 2: Document Dependency Graph Feature

3. **Create `/src/content/docs/how-to-guides/admin/dependency-graph.mdx`**
   - What the dependency graph shows
   - How to access it (from Entity Management or directly)
   - Relationship types explained (forms USE workflows, etc.)
   - Using the visualization (zoom, pan, minimap)
   - Use cases (impact analysis, cleanup planning)

#### Priority 3: Enhance Existing Documentation

4. **Update `/src/content/docs/core-concepts/scopes.mdx`**
   - Add section on changing entity scope via Entity Management
   - Document the filter types (ALL, GLOBAL_ONLY, ORG_ONLY, ORG_PLUS_GLOBAL)
   - Link to Entity Management how-to guide

5. **Update `/src/content/docs/core-concepts/permissions.md`**
   - Add section on bulk role assignment via Entity Management
   - Document the "Clear Roles" action
   - Explain access_level values (authenticated vs role_based)

6. **Update entity-specific concept pages**
   - Add "Entity Management" section to workflows.mdx, forms.mdx, app-builder.mdx
   - Cross-link to the unified Entity Management documentation
   - Note entity-specific limitations (e.g., forms cannot change org after creation)

#### Priority 4: API Documentation

7. **Create API Reference section (if not exists)**
   - Document `GET /api/dependencies/{entity_type}/{entity_id}` endpoint
   - Document batch update patterns for each entity type
   - Include request/response examples

#### Suggested Documentation Structure

```
docs/
├── core-concepts/
│   ├── entity-management.mdx        # NEW - Core concepts
│   ├── scopes.mdx                   # UPDATE - Add entity management section
│   └── permissions.md               # UPDATE - Add bulk assignment section
└── how-to-guides/
    └── admin/
        ├── entity-management.mdx    # NEW - UI guide
        └── dependency-graph.mdx     # NEW - Visualization guide
```
