# AI Coding / MCP System Findings

**Reviewed:** 2026-01-20
**Reviewer:** Claude Agent
**Status:** Complete

## Executive Summary

The Bifrost AI Coding system provides a comprehensive MCP (Model Context Protocol) server that exposes platform capabilities to AI agents. The system supports building workflows, apps, forms, and agents through MCP tools, with a dedicated code engine that compiles TSX/JSX apps in the browser.

---

## Source of Truth

### File Locations

| Component | Path | Description |
|-----------|------|-------------|
| MCP Server | `/api/src/services/mcp_server/server.py` | Main MCP server implementation |
| Tool Registry | `/api/src/services/mcp_server/tool_registry.py` | Tool categories and registry |
| Tool Decorator | `/api/src/services/mcp_server/tool_decorator.py` | `@system_tool` decorator |
| System Prompt | `/api/src/services/coding_mode/prompts.py` | AI coding system prompt |
| SDK Hooks | `/client/src/lib/app-code-platform/` | Platform hooks for apps |
| Components | `/client/src/lib/app-code-platform/components.ts` | Available UI components |

---

## MCP Tools Reference

### Tool Categories

The system defines the following tool categories in `tool_registry.py`:

```python
class ToolCategory(str, Enum):
    WORKFLOW = "workflow"
    FORM = "form"
    FILE = "file"
    KNOWLEDGE = "knowledge"
    INTEGRATION = "integration"
    DATA_PROVIDER = "data_provider"
    APP_BUILDER = "app_builder"
```

### Complete Tool List

#### Workflow Tools (`workflow.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `execute_workflow` | Execute Workflow | Run a workflow by ID or name with parameters | Yes |
| `list_workflows` | List Workflows | List all workflows with optional type filter | Yes |
| `get_workflow` | Get Workflow | Get detailed workflow metadata and code | Yes |
| `validate_workflow` | Validate Workflow | Validate workflow file syntax | Yes |
| `create_workflow` | Create Workflow | Create workflow/tool/data provider with validation | No (restricted) |
| `get_workflow_schema` | Get Workflow Schema | Documentation about decorators and structure | Yes |
| `get_sdk_schema` | Get SDK Schema | Full SDK documentation from source | Yes |

#### Form Tools (`forms.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `list_forms` | List Forms | List all forms with URLs | Yes |
| `get_form` | Get Form | Get form details with fields | Yes |
| `get_form_schema` | Get Form Schema | Documentation about form structure | Yes |
| `create_form` | Create Form | Create form linked to workflow | No (restricted) |
| `update_form` | Update Form | Update form properties/fields | No (restricted) |

#### App Builder Tools (`apps.py`, `app_files.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `list_apps` | List Apps | List applications | Yes |
| `get_app` | Get App | Get app metadata and page list | Yes |
| `get_app_schema` | Get App Schema | Component/layout documentation | Yes |
| `create_app` | Create App | Create app with scope | No (restricted) |
| `update_app` | Update App | Update app settings | No (restricted) |
| `publish_app` | Publish App | Publish draft to live | No (restricted) |
| `create_page` | Create Page | Add page to app | No (restricted) |
| `update_page` | Update Page | Update page settings | No (restricted) |
| `create_component` | Create Component | Add component to page | No (restricted) |
| `update_component` | Update Component | Update component props | No (restricted) |

##### Code Engine File Tools
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `list_app_files` | List App Files | List TSX/TS files in draft | Yes |
| `get_app_file` | Get App File | Get file content by path | Yes |
| `create_app_file` | Create App File | Create TSX/TS file | Yes (restricted) |
| `update_app_file` | Update App File | Update file source | Yes (restricted) |
| `delete_app_file` | Delete App File | Delete file | Yes (restricted) |

#### Execution Tools (`execution.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `list_executions` | List Executions | View recent workflow executions | Yes |
| `get_execution` | Get Execution | Get execution details and logs | Yes |

#### Knowledge Tools (`knowledge.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `search_knowledge` | Search Knowledge | Search knowledge base | Yes |

#### Integration Tools (`integrations.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `list_integrations` | List Integrations | List available integrations | Yes |

#### Data Provider Tools (`data_providers.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `get_data_provider_schema` | Get Data Provider Schema | Documentation about data providers | Yes |

#### Table Tools (`tables.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `list_tables` | List Tables | List tables (filtered by org) | Yes |
| `get_table` | Get Table | Get table details and schema | Yes |
| `get_table_schema` | Get Table Schema | Documentation about tables | Yes |
| `create_table` | Create Table | Create table with scope | Yes (restricted) |
| `update_table` | Update Table | Update table properties | Yes (restricted) |

#### Organization Tools (`organizations.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `list_organizations` | List Organizations | List organizations (platform admin) | Yes |
| `get_organization` | Get Organization | Get org by ID or domain | Yes |
| `create_organization` | Create Organization | Create new org (platform admin) | No (restricted) |

#### Agent Tools (`agents.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `list_agents` | List Agents | List accessible agents | Yes |
| `get_agent` | Get Agent | Get agent details | Yes |
| `create_agent` | Create Agent | Create AI agent | No (restricted) |
| `update_agent` | Update Agent | Update agent properties | No (restricted) |
| `delete_agent` | Delete Agent | Soft-delete agent | No (restricted) |
| `get_agent_schema` | Get Agent Schema | Documentation about agents | Yes |

#### File Tools (`files.py`)
| Tool ID | Name | Description | Default Enabled |
|---------|------|-------------|-----------------|
| `read_file` | Read File | Read workspace file | No (restricted) |
| `write_file` | Write File | Write workspace file | No (restricted) |
| `list_files` | List Files | List workspace directory | No (restricted) |
| `delete_file` | Delete File | Delete workspace file | No (restricted) |
| `search_files` | Search Files | Search text in files | No (restricted) |
| `create_folder` | Create Folder | Create folder | No (restricted) |

---

## App Code Platform SDK

### Overview

The App Code Platform provides hooks and functions that are automatically available in TSX/JSX apps without imports. Located in `/client/src/lib/app-code-platform/`.

### SDK Hooks and Functions

#### `runWorkflow<T>(workflowId: string, params?: Record<string, unknown>): Promise<T>`

**File:** `/client/src/lib/app-code-platform/runWorkflow.ts`

Executes a workflow and returns the result. Used for mutations or one-off calls.

```tsx
// In a button click handler
const handleSave = async () => {
  try {
    await runWorkflow('update_client', { id: clientId, name: newName });
    toast.success('Saved!');
  } catch (error) {
    toast.error('Failed to save');
  }
};
```

#### `useWorkflow<T>(workflowId: string): UseWorkflowResult<T>`

**File:** `/client/src/lib/app-code-platform/useWorkflow.ts`

React hook for executing workflows with real-time streaming updates.

**Returns:**
```typescript
interface UseWorkflowResult<T> {
  execute: (params?: Record<string, unknown>) => Promise<string>;
  executionId: string | null;
  status: ExecutionStatus | null;
  loading: boolean;
  completed: boolean;
  failed: boolean;
  result: T | null;
  error: string | null;
  logs: StreamingLog[];
}
```

**Example:**
```tsx
const workflow = useWorkflow<Customer[]>('list-customers');

useEffect(() => {
  workflow.execute({ limit: 10 });
}, []);

if (workflow.loading) return <Skeleton />;
if (workflow.failed) return <Alert>{workflow.error}</Alert>;
return <CustomerList data={workflow.result} />;
```

#### `useParams(): Record<string, string>`

**File:** `/client/src/lib/app-code-platform/useParams.ts`

Returns URL path parameters from the current route.

```tsx
// URL: /clients/123/contacts
// Route: /clients/:clientId/contacts
const params = useParams();
// params = { clientId: "123" }
```

#### `useSearchParams(): URLSearchParams`

**File:** `/client/src/lib/app-code-platform/useSearchParams.ts`

Returns query string parameters from the current URL.

```tsx
// URL: /clients?status=active&page=2
const searchParams = useSearchParams();
const status = searchParams.get('status'); // "active"
const page = searchParams.get('page'); // "2"
```

#### `useUser(): JsxUser`

**File:** `/client/src/lib/app-code-platform/useUser.ts`

Returns the current authenticated user.

```typescript
interface JsxUser {
  id: string;
  email: string;
  name: string;
  roles: string[];
  hasRole: (role: string) => boolean;
  organizationId: string;
}
```

**Example:**
```tsx
const user = useUser();
return (
  <div>
    <Text>Welcome, {user.name}</Text>
    {user.hasRole('Admin') && <Button>Settings</Button>}
  </div>
);
```

#### `navigate(path: string): void` and `useNavigate(): (path: string) => void`

**File:** `/client/src/lib/app-code-platform/navigate.ts`

Navigation functions that automatically transform absolute paths to include the app's base path.

```tsx
// Hook version (preferred in components)
const nav = useNavigate();
<Button onClick={() => nav('/clients/new')}>Add Client</Button>

// Imperative version (for callbacks)
const handleSuccess = async () => {
  await runWorkflow('save_client', data);
  navigate('/clients');
};
```

**Path Transformation:**
- `/customers` -> `/apps/my-app/preview/customers` (preview mode)
- `/customers` -> `/apps/my-app/customers` (published mode)

#### `useAppState<T>(key: string, initialValue: T): [T, (value: T) => void]`

**File:** `/client/src/lib/app-code-platform/useAppState.ts`

Cross-page state that persists during the app session.

```tsx
// Page 1: Set state
const [cart, setCart] = useAppState('cart', []);
setCart([...cart, newItem]);

// Page 2: Read same state
const [cart] = useAppState('cart', []);
// cart contains items from Page 1
```

---

## Available UI Components

**File:** `/client/src/lib/app-code-platform/components.ts`

All components are available globally in app code without imports.

### Layout Components
- `Card`, `CardHeader`, `CardFooter`, `CardTitle`, `CardAction`, `CardDescription`, `CardContent`

### Form Components
- `Button`
- `Input`
- `Select`, `SelectContent`, `SelectGroup`, `SelectItem`, `SelectLabel`, `SelectTrigger`, `SelectValue`, `SelectSeparator`
- `Checkbox`
- `Textarea`
- `Label`
- `Switch`
- `RadioGroup`, `RadioGroupItem`

### Display Components
- `Badge`
- `Avatar`, `AvatarImage`, `AvatarFallback`
- `Alert`, `AlertTitle`, `AlertDescription`
- `Skeleton`
- `Progress`

### Navigation Components
- `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`
- `Link`, `NavLink`, `Navigate` (path-transforming versions)

### Feedback Components
- `Dialog`, `DialogClose`, `DialogContent`, `DialogDescription`, `DialogFooter`, `DialogHeader`, `DialogTitle`, `DialogTrigger`
- `AlertDialog`, `AlertDialogTrigger`, `AlertDialogContent`, `AlertDialogHeader`, `AlertDialogFooter`, `AlertDialogTitle`, `AlertDialogDescription`, `AlertDialogAction`, `AlertDialogCancel`
- `Tooltip`, `TooltipContent`, `TooltipProvider`, `TooltipTrigger`
- `Popover`, `PopoverContent`, `PopoverTrigger`, `PopoverAnchor`
- `toast` (from Sonner)

### Data Display Components
- `Table`, `TableHeader`, `TableBody`, `TableFooter`, `TableHead`, `TableRow`, `TableCell`, `TableCaption`

---

## App File Structure

### Allowed File Paths

Files must follow strict path conventions validated by the `create_app_file` tool:

| Location | Allowed | Description |
|----------|---------|-------------|
| Root level | `_layout.tsx`, `_providers.tsx` only | Special app-level files |
| `pages/` | Any `.ts`/`.tsx` files, dynamic segments `[param].tsx` | Page components |
| `components/` | Any `.ts`/`.tsx` files | Shared components |
| `modules/` | Any `.ts`/`.tsx` files | Shared modules/utilities |

**Dynamic Routes:**
- `pages/clients/[clientId].tsx` creates route `/clients/:clientId`
- Dynamic segments only allowed in `pages/`

**Naming Rules:**
- Files must have `.ts` or `.tsx` extension
- Use alphanumeric, underscores, hyphens only
- `_layout.tsx` files only in `pages/`

---

## Tailwind 4 Configuration

**File:** `/client/package.json` and `/client/tailwind.config.js`

The platform uses **Tailwind CSS 4.0** with the following setup:

```json
{
  "dependencies": {
    "@tailwindcss/postcss": "^4.0.0",
    "@tailwindcss/vite": "^4.1.14",
    "tailwindcss": "^4.0.0"
  }
}
```

**Safelisted Classes (for dynamic usage):**
- `gap-*`, `p-*` patterns
- `grid-cols-*` pattern

**Typography Plugin:** `@tailwindcss/typography` included

---

## System Prompt

**File:** `/api/src/services/coding_mode/prompts.py`

The coding mode system prompt defines:
1. Available MCP tools and their purposes
2. Multi-tenancy awareness (scope options)
3. Workflow-first development approach
4. Integration-first development requirement
5. Required testing workflow
6. Best practices

Key principles from the prompt:
- Always check integrations exist before writing workflows that use them
- Use MCP tools for platform entities, not file operations
- Verify registration with `list_workflows` before proceeding
- Test all artifacts before declaring complete

---

## Recent Changes

Based on git history for MCP and app platform:

| Commit | Change |
|--------|--------|
| `e7206bc7` | Enforce .ts/.tsx file extension in code editor paths |
| `4f236053` | Add WebSocket real-time updates for code files |
| `e39ac73b` | Add code file tools for code engine apps |
| `1c8d8203` | Rename jsx -> code for App Builder code engine |
| `8f2df17b` | Validate component props through Pydantic |
| `de0483dd` | Add agent and SDK schema tools |
| `15928a99` | Add multi-tenancy and restricted tool support |

---

## Key Documentation Needs

Based on this review, the following areas need documentation:

### For AI Agents Building Apps
1. **Complete SDK hook reference** with type signatures and examples
2. **Component library documentation** with prop interfaces
3. **File structure requirements** with path validation rules
4. **Navigation system** - how path transformation works
5. **State management** - `useAppState` vs React state

### For AI Agents Building Workflows
1. **MCP tool reference** - each tool's parameters and return values
2. **Testing workflow** - required verification steps
3. **Multi-tenancy** - scope options and organization context
4. **Integration checking** - why and how to verify integrations

### For Platform Developers
1. **Tool decorator API** - how to add new MCP tools
2. **Tool categories** - when to use each category
3. **Restricted vs default-enabled** tools
4. **Context object** - what's available in tool context

---

## Code Examples

### Minimal App Example

```tsx
// pages/index.tsx
const user = useUser();
const workflow = useWorkflow('list-items');

useEffect(() => {
  workflow.execute();
}, []);

return (
  <Card>
    <CardHeader>
      <CardTitle>Welcome, {user.name}</CardTitle>
    </CardHeader>
    <CardContent>
      {workflow.loading && <Skeleton className="h-20" />}
      {workflow.result && (
        <ul>
          {workflow.result.map(item => (
            <li key={item.id}>{item.name}</li>
          ))}
        </ul>
      )}
    </CardContent>
  </Card>
);
```

### Form with Navigation

```tsx
// pages/clients/new.tsx
const [name, setName] = useState('');
const nav = useNavigate();

const handleSubmit = async () => {
  await runWorkflow('create_client', { name });
  toast.success('Client created!');
  nav('/clients');
};

return (
  <Card>
    <CardHeader>
      <CardTitle>New Client</CardTitle>
    </CardHeader>
    <CardContent>
      <Label htmlFor="name">Name</Label>
      <Input
        id="name"
        value={name}
        onChange={e => setName(e.target.value)}
      />
    </CardContent>
    <CardFooter>
      <Button onClick={handleSubmit}>Create</Button>
    </CardFooter>
  </Card>
);
```

---

## Recommendations

1. **Create a dedicated SDK reference page** with complete TypeScript signatures
2. **Add component showcase** with visual examples
3. **Document path conventions** with explicit examples of valid/invalid paths
4. **Create MCP tool quick reference** card for AI agents
5. **Add troubleshooting guide** for common issues (path validation errors, workflow not found, etc.)

---

## Documentation State

### Existing Documentation Files

| File Path | Description | Status |
|-----------|-------------|--------|
| `/src/content/docs/how-to-guides/local-dev/ai-coding.md` | AI system instructions for external MCP and coding agent | Partial coverage |
| `/src/content/docs/how-to-guides/integrations/mcp-server.mdx` | MCP server overview and tool availability | Partial coverage |
| `/src/content/docs/core-concepts/app-builder.mdx` | App Builder overview and architecture | Good coverage |
| `/src/content/docs/sdk-reference/app-builder/components.mdx` | JSON App Builder component reference | Good coverage |
| `/src/content/docs/sdk-reference/app-builder/schema.mdx` | JSON App Builder schema reference | Good coverage |
| `/src/content/docs/sdk-reference/app-builder/expressions.mdx` | JSON App Builder expression syntax | Good coverage |
| `/src/content/docs/sdk-reference/app-builder/actions.mdx` | JSON App Builder action system | Good coverage |

### Gaps Identified

#### Critical Gaps (Missing Entirely)

1. **Code Engine / TSX App Documentation**
   - **Missing**: No documentation for the TSX/JSX code engine introduced in recent commits
   - **Missing**: SDK hooks reference (`runWorkflow`, `useWorkflow`, `useParams`, `useSearchParams`, `useUser`, `navigate`, `useNavigate`, `useAppState`)
   - **Missing**: File structure conventions (`pages/`, `components/`, `modules/`, `_layout.tsx`, `_providers.tsx`)
   - **Missing**: Path validation rules and dynamic route segments
   - **Impact**: AI agents cannot build TSX apps, only JSON apps

2. **shadcn/ui Component Library for Code Engine**
   - **Missing**: Available global components list (50+ components without imports)
   - **Missing**: Component usage examples in TSX context
   - **Impact**: AI agents don't know what UI components are available for TSX apps

3. **Tailwind 4 Configuration**
   - **Missing**: No documentation that Tailwind 4 is available
   - **Missing**: Safelisted class patterns for dynamic usage
   - **Impact**: AI agents may not use modern Tailwind features

4. **MCP Code File Tools**
   - **Missing**: `list_app_files`, `get_app_file`, `create_app_file`, `update_app_file`, `delete_app_file` tools
   - **Impact**: AI agents can't manage TSX files in code engine apps

#### Partial Gaps (Incomplete or Outdated)

1. **MCP Tool Reference**
   - **Issue**: `ai-coding.md` lists ~25 tools; codebase has 40+ tools
   - **Missing tools**: Agent tools, Table tools, Organization tools, Execution tools
   - **Missing**: Tool parameter schemas and return types
   - **Missing**: Restricted vs default-enabled tool distinction

2. **Multi-tenancy Documentation**
   - **Issue**: Briefly mentioned in `ai-coding.md` but incomplete
   - **Missing**: Detailed scope options explanation
   - **Missing**: How organization context affects tool availability

3. **App Builder vs Code Engine Distinction**
   - **Issue**: All current docs focus on JSON-based App Builder
   - **Missing**: Clear explanation of two app modes (JSON vs Code Engine)
   - **Missing**: When to use each approach

#### Inaccuracies

1. **Tool Names**
   - `list_data_providers` documented but codebase shows data providers accessed via `list_workflows` with type filter

2. **App Builder Tools**
   - Docs show `get_page`, `delete_page`, `list_components`, `get_component`, `delete_component`, `move_component`
   - Codebase findings show fewer page/component-level MCP tools (more granular tools may exist but need verification)

### Recommended Actions

#### High Priority (Critical for AI Agent Success)

1. **Create `/sdk-reference/app-builder/code-engine.mdx`**
   - Document TSX/JSX code engine architecture
   - Include SDK hooks with TypeScript signatures
   - Add file structure requirements
   - Provide minimal and advanced code examples

2. **Create `/sdk-reference/app-builder/code-engine-components.mdx`**
   - List all globally available shadcn/ui components
   - Group by category (Layout, Form, Display, Navigation, Feedback, Data Display)
   - Include usage patterns specific to code engine

3. **Update `/how-to-guides/integrations/mcp-server.mdx`**
   - Add complete tool reference table with all 40+ tools
   - Document tool categories from `tool_registry.py`
   - Add parameter schemas for each tool
   - Document restricted vs default-enabled tools
   - Add code file tools section

#### Medium Priority

4. **Update `/how-to-guides/local-dev/ai-coding.md`**
   - Expand MCP tool list to match codebase
   - Add section for code engine app development
   - Add SDK hooks quick reference
   - Add troubleshooting section

5. **Create `/sdk-reference/app-builder/sdk-hooks.mdx`**
   - Complete TypeScript interfaces for all hooks
   - `runWorkflow<T>` - mutation pattern
   - `useWorkflow<T>` - streaming execution pattern
   - `useParams`, `useSearchParams` - routing
   - `useUser` - authentication
   - `navigate`, `useNavigate` - navigation with path transformation
   - `useAppState` - cross-page state

6. **Document Tailwind 4 availability**
   - Add to code engine docs
   - Note safelisted patterns
   - Reference typography plugin

#### Low Priority

7. **Add troubleshooting guide for common AI coding issues**
   - Path validation errors
   - Workflow not found
   - Integration not configured
   - Scope/permission issues

8. **Create visual component showcase**
   - Interactive examples for both JSON and TSX modes
   - Screenshot gallery
