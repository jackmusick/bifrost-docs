# App Builder - Codebase Review Findings

## Executive Summary

The App Builder is Bifrost's visual/code-based application development platform. It uses a **Code Engine** architecture with **JSX/TypeScript** compilation via Babel, **file-based routing** similar to Next.js, and a comprehensive platform scope that provides UI components, workflow execution, and navigation hooks.

---

## Architecture Overview

### Core Concepts

1. **Applications** - Top-level container with metadata, access control, and versioning
2. **App Versions** - Snapshots of app state (draft for editing, active for published)
3. **App Files** - TSX/TypeScript source files organized by convention
4. **Code Engine** - Browser-based JSX compilation and runtime execution
5. **Platform Scope** - Injected APIs available to user code (workflows, navigation, UI)

### Technology Stack

- **Compilation**: Babel standalone (`@babel/standalone`) for browser-based JSX/TSX transformation
- **Routing**: React Router v6 with file-based route generation
- **State**: Zustand for cross-page app state
- **Components**: shadcn/ui + Radix primitives exposed to user code
- **Icons**: Lucide React (full library available)
- **Real-time**: WebSocket pub/sub via Redis for live updates

---

## Backend Implementation

### API Routers

#### Applications Router
**File**: `/Users/jack/GitHub/bifrost/api/src/routers/applications.py`

Endpoints:
- `POST /api/applications` - Create application
- `GET /api/applications` - List applications (with org scoping)
- `GET /api/applications/{slug}` - Get by slug
- `PATCH /api/applications/{slug}` - Update metadata
- `DELETE /api/applications/{slug}` - Delete application
- `GET /api/applications/{app_id}/draft` - Get draft definition
- `PUT /api/applications/{app_id}/draft` - Save draft definition
- `POST /api/applications/{app_id}/publish` - Publish draft to live
- `GET /api/applications/{app_id}/export` - Export full app as JSON
- `POST /api/applications/{app_id}/rollback` - Rollback to previous version

Key features:
- Uses `OrgScopedRepository` pattern for organization-based access control
- Role-based access: `access_level` can be "authenticated" (any user) or "role_based" (specific roles via `AppRole` table)
- Cascade scoping: org-specific apps + global (NULL org_id) apps visible
- Auto-scaffolds initial files on app creation (`_layout.tsx`, `pages/index.tsx`)

#### App Code Files Router
**File**: `/Users/jack/GitHub/bifrost/api/src/routers/app_code_files.py`

Endpoints:
- `GET /api/applications/{app_id}/versions/{version_id}/files` - List files
- `GET /api/applications/{app_id}/versions/{version_id}/files/{file_path:path}` - Get file by path
- `POST /api/applications/{app_id}/versions/{version_id}/files` - Create file
- `PATCH /api/applications/{app_id}/versions/{version_id}/files/{file_path:path}` - Update file
- `DELETE /api/applications/{app_id}/versions/{version_id}/files/{file_path:path}` - Delete file

Path validation enforces conventions:
- **Root level**: Only `_layout.tsx` and `_providers.tsx` allowed
- **Directories**: `pages/`, `components/`, `modules/` only
- **Dynamic segments**: `[param]` syntax only in `pages/`
- **Extensions**: `.ts` or `.tsx` required

### SQLAlchemy Models

**File**: `/Users/jack/GitHub/bifrost/api/src/models/orm/applications.py`

```python
class Application(Base):
    __tablename__ = "applications"
    id: UUID
    name: str
    slug: str
    organization_id: UUID | None  # NULL = global
    active_version_id: UUID | None  # Published version
    draft_version_id: UUID | None   # Working version
    published_at: datetime | None
    navigation: dict  # JSONB - sidebar config
    permissions: dict  # JSONB - access rules
    access_level: str  # "authenticated" | "role_based"

class AppVersion(Base):
    __tablename__ = "app_versions"
    id: UUID
    application_id: UUID
    files: relationship("AppFile")

class AppFile(Base):
    __tablename__ = "app_files"
    id: UUID
    app_version_id: UUID
    path: str  # e.g., "pages/clients/[id].tsx"
    source: str  # Original TSX source
    compiled: str | None  # Pre-compiled JS (optional)
```

### Pydantic Contracts

**File**: `/Users/jack/GitHub/bifrost/api/src/models/contracts/applications.py`

Key models:
- `ApplicationCreate` - slug validation, access_level, role_ids
- `ApplicationUpdate` - name, description, icon, scope, navigation, role_ids
- `ApplicationPublic` - Full response model with version IDs, timestamps
- `AppFileCreate/Update/Response` - File CRUD models
- `NavigationConfig` - Sidebar items, show_sidebar, show_header, logo_url, brand_color, page_transition
- `NavItem` - id, label, icon, path, visible expression, children (nested)

---

## Frontend Implementation

### Entry Points

#### App Router (Published Apps)
**File**: `/Users/jack/GitHub/bifrost/client/src/pages/AppRouter.tsx`

Routes:
- `/apps/:slug` - Published app landing
- `/apps/:slug/*` - Published app with nested routes

Fetches app metadata by slug, loads active version, renders via `JsxAppShell`.

#### App Code Editor Page
**File**: `/Users/jack/GitHub/bifrost/client/src/pages/AppCodeEditorPage.tsx`

Routes:
- `/apps/:slug/code` - Editor for draft version
- `/apps/:slug/code/*` - Editor with app preview routing

Provides full IDE experience with file tree, Monaco editor, live preview.

### JSX App Shell

**File**: `/Users/jack/GitHub/bifrost/client/src/components/jsx-app/JsxAppShell.tsx`

Core rendering component that:
1. Fetches all files for app version
2. Identifies `_providers.tsx` for context wrapping
3. Identifies `_layout.tsx` for root layout
4. Builds React Router configuration from file structure
5. Renders pages with component resolution

Key components:
- `ProvidersWrapper` - Wraps app with custom providers
- `LayoutWrapper` - Wraps routes with layout component (renders `<Outlet />`)
- `renderRoutes()` - Recursively builds Route elements

### Page Renderer

**File**: `/Users/jack/GitHub/bifrost/client/src/components/jsx-app/JsxPageRenderer.tsx`

Renders individual page files:
1. Extracts component names from source
2. Resolves custom components from `components/` directory
3. Creates component via runtime
4. Renders within error boundary

### Code Compiler

**File**: `/Users/jack/GitHub/bifrost/client/src/lib/app-code-compiler.ts`

Browser-based JSX compilation using Babel standalone:

```typescript
function compileAppCode(source: string): CompileResult {
  // 1. Transform "bifrost" imports to $ destructuring
  //    import { Button } from "bifrost" -> const { Button } = $;

  // 2. Compile with Babel (react + typescript presets)

  // 3. Transform exports to capture default export
  //    export default function X -> function X; __defaultExport__ = X;

  return { success, compiled, defaultExport, namedExports, error };
}
```

### Code Runtime

**File**: `/Users/jack/GitHub/bifrost/client/src/lib/app-code-runtime.ts`

Creates React components from compiled code:

```typescript
// The $ registry - everything available to user code
export const $: Record<string, unknown> = {
  React,           // React and all hooks
  ...reactRouterExports,  // Router (except Link/NavLink/Navigate)
  ...LucideIcons,  // All Lucide icons
  ...createPlatformScope(),  // Platform APIs
  ...utils,        // cn(), clsx, twMerge
  ...UIComponents, // All shadcn/ui components
};

function createComponent(source, customComponents, useCompiled): React.ComponentType
```

### File-Based Router

**File**: `/Users/jack/GitHub/bifrost/client/src/lib/app-code-router.ts`

Converts file paths to React Router configuration:

| File Path | Route Path |
|-----------|------------|
| `pages/index.tsx` | `/` |
| `pages/clients.tsx` | `/clients` |
| `pages/clients/[id].tsx` | `/clients/:id` |
| `pages/clients/[id]/contacts.tsx` | `/clients/:id/contacts` |
| `pages/settings/_layout.tsx` | `/settings` (layout wrapper) |
| `pages/settings/billing.tsx` | `/settings/billing` |

Special files:
- `_layout.tsx` - Parent route with `<Outlet />` for nested routes
- `index.tsx` - Index route (default for directory)
- `[param].tsx` - Dynamic route segment

---

## Platform Scope (APIs Available to User Code)

### Location
**Directory**: `/Users/jack/GitHub/bifrost/client/src/lib/app-code-platform/`

### Exported Functions/Hooks

#### `runWorkflow(workflowId, params?)`
**File**: `runWorkflow.ts`

Imperative workflow execution. Returns promise with result.

```jsx
const handleSave = async () => {
  const result = await runWorkflow('update_client', { id: clientId, name });
};
```

#### `useWorkflow<T>(workflowId)`
**File**: `useWorkflow.ts`

React hook for workflow execution with streaming updates:

```jsx
const { execute, status, loading, completed, failed, result, error, logs } = useWorkflow('list_clients');

useEffect(() => {
  execute({ limit: 10 });
}, []);
```

Features:
- WebSocket-based status updates
- Streaming logs array
- Auto-fetches result on completion

#### `useParams()`
**File**: `useParams.ts`

Wrapper around React Router's useParams:

```jsx
// Route: /clients/:clientId
const { clientId } = useParams();
```

#### `useSearchParams()`
**File**: `useSearchParams.ts`

Access URL query parameters:

```jsx
const searchParams = useSearchParams();
const status = searchParams.get('status');
```

#### `navigate(to)` / `useNavigate()`
**File**: `navigate.ts`

Navigation with automatic path transformation for app context:

```jsx
navigate('/clients');  // Transforms to /apps/{slug}/clients
```

#### `Link`, `NavLink`, `Navigate`
**File**: `navigation.ts`

React Router navigation components with path transformation.

#### `useUser()`
**File**: `useUser.ts`

Current authenticated user info:

```jsx
const user = useUser();
// { id, email, name, roles, hasRole(role), organizationId }
```

#### `useAppState(key, initialValue)`
**File**: `useAppState.ts`

Cross-page state (persists during app session):

```jsx
const [selectedClient, setSelectedClient] = useAppState('selectedClient', null);
// Persists when navigating between pages
```

### UI Components Available

All shadcn/ui components are available without imports:

- Button, Input, Label, Textarea
- Card, CardHeader, CardTitle, CardContent, CardFooter
- Badge, Avatar, Checkbox, Switch
- Select, SelectTrigger, SelectContent, SelectItem
- Table, TableHeader, TableBody, TableRow, TableCell
- Tabs, TabsList, TabsTrigger, TabsContent
- Dialog, DropdownMenu, Tooltip, Popover
- Alert, Accordion, Collapsible
- Sheet, Separator, RadioGroup, Slider, Toggle
- Command, AlertDialog, ContextMenu, HoverCard
- Progress, Skeleton

Also available:
- All Lucide React icons
- `cn()` utility for class merging
- `clsx` and `twMerge`

---

## Code Editor UI

### Editor Layout
**File**: `/Users/jack/GitHub/bifrost/client/src/components/app-code-editor/AppCodeEditorLayout.tsx`

Features:
- File tree sidebar (collapsible)
- Monaco code editor
- View modes: code, split (code + file preview), preview, app (full app preview)
- Save/Run toolbar buttons
- Unsaved changes indicator
- Error display in status bar

### Editor Hook
**File**: `/Users/jack/GitHub/bifrost/client/src/components/app-code-editor/useAppCodeEditor.ts`

Manages:
- Source state
- Auto-compilation (debounced)
- Error tracking
- Save operations

### Preview Component
**File**: `/Users/jack/GitHub/bifrost/client/src/components/app-code-editor/AppCodePreview.tsx`

Live preview of compiled component with error boundary.

---

## Real-Time Updates

### WebSocket PubSub
**File**: `/Users/jack/GitHub/bifrost/api/src/core/pubsub.py`

Channels:
- `app:draft:{app_id}` - Draft changes (file create/update/delete)
- `app:live:{app_id}` - Publish events (new version available)

Functions:
- `publish_app_draft_update()` - App metadata changes
- `publish_app_code_file_update()` - File changes with full content
- `publish_app_published()` - New version published

### Client Hook
**File**: `/Users/jack/GitHub/bifrost/client/src/hooks/useAppCodeUpdates.ts`

Subscribes to draft channel, provides callback for updates.

---

## MCP Tools for AI Coding

**File**: `/Users/jack/GitHub/bifrost/api/src/services/mcp_server/tools/app_files.py`

Tools available to AI coding agent:

| Tool | Description |
|------|-------------|
| `list_app_files` | List all files in app's draft version |
| `get_app_file` | Get file content by path |
| `create_app_file` | Create new file (validates path conventions) |
| `update_app_file` | Update file source code |
| `delete_app_file` | Delete file |

All tools:
- Require `app_id` parameter
- Operate on draft version only
- Publish real-time updates on modification
- Validate paths against conventions

---

## App Scaffolding

When a new app is created, the repository auto-scaffolds:

**`_layout.tsx`** (root layout):
```tsx
import { Outlet } from "bifrost";

export default function RootLayout() {
  return (
    <div className="min-h-screen bg-background">
      <Outlet />
    </div>
  );
}
```

**`pages/index.tsx`** (home page):
```tsx
export default function HomePage() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">Welcome</h1>
      <p className="text-muted-foreground">
        Start building your app...
      </p>
    </div>
  );
}
```

---

## Recent Changes / Migration History

Based on migration files:

1. **JSX App Builder Schema** (`20260117_230000`)
   - Initial app_versions and app_files tables

2. **Rename JSX to Code** (`20260117_235000`)
   - Renamed "JSX" terminology to "Code Engine"
   - `app_jsx_files` -> `app_files`

3. **AppCodeFile to AppFile** (recent)
   - Simplified naming throughout codebase

---

## Key Concepts to Document

### For End Users (App Builders)

1. **File Structure Conventions**
   - pages/, components/, modules/ directories
   - _layout.tsx, _providers.tsx special files
   - Dynamic routes with [param] syntax

2. **Platform API Reference**
   - useWorkflow / runWorkflow
   - useParams / useSearchParams
   - navigate / Link / NavLink
   - useUser
   - useAppState

3. **Available Components**
   - Complete list of UI components
   - How to use without imports
   - Tailwind CSS classes available

4. **Workflow Integration**
   - Calling workflows from app code
   - Handling loading/error states
   - Streaming logs

5. **Navigation and Routing**
   - File-based routing explained
   - Dynamic routes
   - Nested layouts

### For Developers (Platform)

1. **Architecture Overview**
   - Compilation pipeline
   - Runtime scope injection
   - Component resolution

2. **Real-Time Updates**
   - WebSocket channels
   - Redis pub/sub
   - Client subscription patterns

3. **Access Control**
   - Org scoping
   - Role-based access
   - Cascade scoping rules

4. **MCP Tools**
   - Available tools
   - Path validation
   - File operations

---

## File Paths Reference

### Backend (API)
- `/Users/jack/GitHub/bifrost/api/src/routers/applications.py`
- `/Users/jack/GitHub/bifrost/api/src/routers/app_code_files.py`
- `/Users/jack/GitHub/bifrost/api/src/models/orm/applications.py`
- `/Users/jack/GitHub/bifrost/api/src/models/contracts/applications.py`
- `/Users/jack/GitHub/bifrost/api/src/core/pubsub.py`
- `/Users/jack/GitHub/bifrost/api/src/services/mcp_server/tools/app_files.py`

### Frontend (Client)
- `/Users/jack/GitHub/bifrost/client/src/pages/AppRouter.tsx`
- `/Users/jack/GitHub/bifrost/client/src/pages/AppCodeEditorPage.tsx`
- `/Users/jack/GitHub/bifrost/client/src/components/jsx-app/JsxAppShell.tsx`
- `/Users/jack/GitHub/bifrost/client/src/components/jsx-app/JsxPageRenderer.tsx`
- `/Users/jack/GitHub/bifrost/client/src/components/app-code-editor/AppCodeEditorLayout.tsx`
- `/Users/jack/GitHub/bifrost/client/src/lib/app-code-compiler.ts`
- `/Users/jack/GitHub/bifrost/client/src/lib/app-code-runtime.ts`
- `/Users/jack/GitHub/bifrost/client/src/lib/app-code-router.ts`
- `/Users/jack/GitHub/bifrost/client/src/lib/app-code-resolver.ts`
- `/Users/jack/GitHub/bifrost/client/src/lib/app-code-platform/` (directory)

---

## Documentation State

### Existing Documentation Files

| File Path | Description | Status |
|-----------|-------------|--------|
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/core-concepts/app-builder.mdx` | Core concepts overview | **COMPLETELY OUTDATED** |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/sdk-reference/app-builder/actions.mdx` | Action system reference | **COMPLETELY OUTDATED** |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/sdk-reference/app-builder/components.mdx` | Component reference | **COMPLETELY OUTDATED** |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/sdk-reference/app-builder/expressions.mdx` | Expression syntax | **PARTIALLY RELEVANT** (expressions still used in some contexts) |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/sdk-reference/app-builder/schema.mdx` | JSON schema reference | **COMPLETELY OUTDATED** |

### Critical Gap Analysis

**The existing documentation describes a completely different architecture.** The current docs cover:
- JSON-based declarative app definitions
- Visual drag-and-drop editor
- Component schemas with props objects
- JSON page layouts with nested children
- MCP tools for JSON manipulation (create_app, create_page, create_component, etc.)

**The actual codebase implements:**
- **Code Engine** with JSX/TypeScript source files
- Browser-based Babel compilation
- File-based routing similar to Next.js
- React components with direct imports from "bifrost"
- Platform scope injection (hooks, components, utilities)

### Gaps Identified

#### 1. Architecture Mismatch (CRITICAL)
- **Gap**: Docs describe JSON-based declarative apps; codebase implements TSX/JSX Code Engine
- **Impact**: Users following current docs will not understand how the system actually works
- **Evidence**:
  - Docs show `{ "type": "heading", "props": { "text": "..." } }`
  - Codebase shows `<Heading level={1}>Welcome</Heading>` in TSX files

#### 2. File Structure Not Documented
- **Gap**: No documentation for file-based routing conventions
- **Missing**:
  - `pages/` directory and route generation
  - `components/` directory for custom components
  - `modules/` directory for shared code
  - `_layout.tsx` and `_providers.tsx` special files
  - Dynamic route segments with `[param].tsx` syntax
  - Nested layouts via `pages/*/index.tsx`

#### 3. Platform Scope Undocumented
- **Gap**: No reference for the `$` registry and "bifrost" imports
- **Missing**:
  - `import { ... } from "bifrost"` pattern
  - `useWorkflow(workflowId)` hook - streaming workflow execution
  - `runWorkflow(workflowId, params)` - imperative workflow calls
  - `useParams()` - route parameter access
  - `useSearchParams()` - query parameter access
  - `navigate(to)` / `useNavigate()` - programmatic navigation
  - `Link`, `NavLink`, `Navigate` - navigation components
  - `useUser()` - current user info with `hasRole()` method
  - `useAppState(key, initialValue)` - cross-page state persistence

#### 4. Available Components Not Listed
- **Gap**: Component list references JSON component types, not actual React components
- **Missing**:
  - Full list of shadcn/ui components available (Button, Input, Card, Table, Tabs, Dialog, etc.)
  - All Lucide React icons available
  - Utility functions (`cn()`, `clsx`, `twMerge`)
  - How to use components without explicit imports

#### 5. Code Editor Not Documented
- **Gap**: No documentation for the in-browser IDE experience
- **Missing**:
  - File tree sidebar
  - Monaco editor integration
  - View modes (code, split, preview, app)
  - Live preview with hot reload
  - Error display and debugging
  - Save/publish workflow

#### 6. WebSocket Real-Time Updates Not Documented
- **Gap**: No mention of real-time collaboration features
- **Missing**:
  - Draft channel for file changes
  - Live channel for publish events
  - How multiple editors see updates

#### 7. MCP Tools Incorrectly Documented
- **Gap**: Docs show JSON-based MCP tools; actual tools work with files
- **Actual tools**:
  - `list_app_files` - List files in draft version
  - `get_app_file` - Get file content by path
  - `create_app_file` - Create new file (path validated)
  - `update_app_file` - Update file source
  - `delete_app_file` - Delete file

#### 8. App Versioning Not Documented
- **Gap**: No explanation of draft vs active versions
- **Missing**:
  - Draft version for editing
  - Active version for published apps
  - Publishing workflow
  - Rollback capabilities

#### 9. Access Control Partially Documented
- **Gap**: Permission model described but implementation differs
- **Missing**:
  - `access_level: "authenticated" | "role_based"`
  - `AppRole` table for role-based access
  - Org scoping with cascade rules
  - Global apps (NULL org_id)

### Recommended Actions

#### Immediate (Complete Rewrite Required)

1. **Rewrite core-concepts/app-builder.mdx**
   - Remove all JSON-based architecture content
   - Document Code Engine architecture
   - Explain file-based routing model
   - Add migration notes from legacy JSON apps (if applicable)

2. **Create New Reference Pages**
   - `sdk-reference/app-builder/file-structure.mdx` - File conventions and routing
   - `sdk-reference/app-builder/platform-hooks.mdx` - useWorkflow, useParams, navigate, etc.
   - `sdk-reference/app-builder/ui-components.mdx` - Available shadcn/ui components
   - `sdk-reference/app-builder/code-editor.mdx` - IDE features and workflow

3. **Update sdk-reference/app-builder/actions.mdx**
   - Remove JSON action definitions
   - Document hook-based workflow execution
   - Show TSX examples for form handling

4. **Update sdk-reference/app-builder/components.mdx**
   - Replace JSON component schemas with React component usage
   - Document available shadcn/ui components
   - Show how to create custom components in `components/` directory

5. **Archive or Remove sdk-reference/app-builder/schema.mdx**
   - JSON schema no longer applies to Code Engine apps
   - Consider keeping only if legacy JSON apps still supported

6. **Keep sdk-reference/app-builder/expressions.mdx** (with updates)
   - Expression syntax still relevant for navigation config
   - Update examples to show TSX context

#### Documentation Structure Recommendation

```
sdk-reference/app-builder/
├── index.mdx              # Overview + quick start
├── file-structure.mdx     # NEW: File conventions, routing
├── platform-hooks.mdx     # NEW: useWorkflow, navigate, etc.
├── ui-components.mdx      # REWRITE: shadcn/ui components available
├── code-editor.mdx        # NEW: IDE features
├── versioning.mdx         # NEW: Draft/publish workflow
├── access-control.mdx     # REWRITE: Permissions model
└── mcp-tools.mdx          # REWRITE: File-based MCP tools
```

#### Example Content to Add

**File Structure Example:**
```
my-app/
├── _layout.tsx           # Root layout (wraps all pages)
├── _providers.tsx        # Custom context providers
├── pages/
│   ├── index.tsx         # / route
│   ├── clients.tsx       # /clients route
│   └── clients/
│       ├── [id].tsx      # /clients/:id route
│       └── [id]/
│           └── contacts.tsx  # /clients/:id/contacts
├── components/
│   └── ClientCard.tsx    # Custom reusable component
└── modules/
    └── utils.ts          # Shared utilities
```

**Platform Hook Example:**
```tsx
import { useWorkflow, useParams, navigate, Button, Card } from "bifrost";

export default function ClientDetailPage() {
  const { id } = useParams();
  const { execute, loading, result, error } = useWorkflow('get_client');

  useEffect(() => {
    execute({ clientId: id });
  }, [id]);

  if (loading) return <Skeleton />;
  if (error) return <Alert variant="destructive">{error}</Alert>;

  return (
    <Card>
      <h1>{result.name}</h1>
      <Button onClick={() => navigate(`/clients/${id}/edit`)}>
        Edit
      </Button>
    </Card>
  );
}
```

### Priority Matrix

| Action | Priority | Effort | Impact |
|--------|----------|--------|--------|
| Rewrite core-concepts/app-builder.mdx | P0 | High | Critical - users completely misled |
| Create file-structure.mdx | P0 | Medium | Critical - fundamental concept |
| Create platform-hooks.mdx | P0 | Medium | Critical - core API |
| Rewrite components.mdx | P1 | High | High - daily usage reference |
| Create code-editor.mdx | P1 | Medium | Medium - discoverability |
| Create versioning.mdx | P2 | Low | Medium - operational knowledge |
| Update MCP tools docs | P2 | Medium | Medium - AI coding use case |
| Update expressions.mdx | P3 | Low | Low - still partially accurate |
