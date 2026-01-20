# Admin Features - Codebase Review Findings

## Source of Truth

This document captures the current state of admin features in the Bifrost platform based on codebase analysis conducted on 2026-01-20.

---

## 1. Overview

The Bifrost platform provides comprehensive admin features for platform administrators (superusers) to monitor and manage workflow executions, view logs, and perform cleanup operations. Admin access is determined by the `is_superuser` flag in the JWT token claims.

### Key Admin Capabilities
- View all executions across all organizations
- Access cross-organization log aggregation (Logs View)
- View DEBUG/TRACEBACK log levels (filtered for regular users)
- View execution variables and resource metrics
- Access stuck execution cleanup tools
- Filter executions by organization

---

## 2. Backend Architecture

### 2.1 Authentication and Authorization

**File:** `/Users/jack/GitHub/bifrost/api/src/core/auth.py`

The `UserPrincipal` dataclass defines user identity:
```python
@dataclass
class UserPrincipal:
    user_id: UUID
    email: str
    organization_id: UUID | None  # None for system accounts
    is_superuser: bool = False    # Platform admin flag

    @property
    def is_platform_admin(self) -> bool:
        return self.is_superuser
```

Auth model rules:
- `is_superuser=true, org_id=UUID`: Platform admin in an org
- `is_superuser=false, org_id=UUID`: Regular org user
- `is_superuser=true, org_id=None`: System account (global scope)
- `is_superuser=false, org_id=None`: INVALID (rejected at token parsing)

---

### 2.2 Executions Router

**File:** `/Users/jack/GitHub/bifrost/api/src/routers/executions.py`

#### API Endpoints

| Endpoint | Method | Description | Admin Only |
|----------|--------|-------------|------------|
| `GET /api/executions` | GET | List workflow executions with filtering | No (filtered by user) |
| `GET /api/executions/logs` | GET | List logs across all executions | Yes |
| `GET /api/executions/{execution_id}` | GET | Get execution details | No (owner or admin) |
| `GET /api/executions/{execution_id}/result` | GET | Get execution result only | No (owner or admin) |
| `GET /api/executions/{execution_id}/logs` | GET | Get execution logs | No (owner or admin) |
| `GET /api/executions/{execution_id}/variables` | GET | Get execution variables | Yes |
| `POST /api/executions/{execution_id}/cancel` | POST | Cancel execution | No (owner or admin) |
| `GET /api/executions/cleanup/stuck` | GET | Get stuck executions | Yes |
| `POST /api/executions/cleanup/trigger` | POST | Cleanup stuck executions | Yes |
| `POST /api/executions/cleanup/redis-orphans` | POST | Cleanup Redis orphans | Yes |

#### Admin Logs Endpoint (`GET /api/executions/logs`)

This endpoint provides cross-organization log aggregation for platform admins:

```python
@router.get("/logs")
async def list_logs(
    ctx: Context,
    organization_id: UUID | None = Query(None),
    workflow_name: str | None = Query(None),
    levels: str | None = Query(None),           # Comma-separated: "ERROR,WARNING"
    message_search: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    continuation_token: str | None = Query(None),
) -> LogsListResponse:
```

**Filter Parameters:**
- `organization_id`: Filter by specific organization UUID
- `workflow_name`: Partial match on workflow name
- `levels`: Comma-separated log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message_search`: Full-text search in log messages
- `start_date` / `end_date`: Date range filter (ISO format)
- `limit`: Results per page (max 500)
- `continuation_token`: Pagination token

#### Execution Variables (Admin Only)

```python
@router.get("/{execution_id}/variables")
async def get_execution_variables(execution_id: UUID, ctx: Context) -> dict:
    if not ctx.user.is_superuser:
        raise HTTPException(status_code=403, detail="Platform admin privileges required")
```

#### Log Level Filtering for Non-Admins

In `ExecutionRepository.get_execution()`:
```python
# Filter debug logs for non-superusers
if not user.is_superuser:
    logs_query = logs_query.where(
        ExecutionLogORM.level.notin_(["DEBUG", "TRACEBACK"])
    )
```

#### Admin-Only Fields in Execution Response

When returning execution details, certain fields are null for non-admins:
```python
return WorkflowExecution(
    # ...
    variables=execution.variables if user.is_superuser else None,
    peak_memory_bytes=execution.peak_memory_bytes if user.is_superuser else None,
    cpu_total_seconds=execution.cpu_total_seconds if user.is_superuser else None,
)
```

---

### 2.3 Stuck Execution Cleanup

**Endpoint:** `GET /api/executions/cleanup/stuck`

Finds executions stuck in Pending/Running status beyond a configurable threshold:

```python
@router.get("/cleanup/stuck")
async def get_stuck_executions(
    ctx: Context,
    hours: int = Query(24, description="Hours since start to consider stuck"),
) -> StuckExecutionsResponse:
```

**Endpoint:** `POST /api/executions/cleanup/trigger`

Marks stuck executions as FAILED with timeout message:

```python
@router.post("/cleanup/trigger")
async def trigger_cleanup(ctx: Context, hours: int = Query(24)) -> CleanupTriggeredResponse:
    # Finds stuck executions
    # Updates status to FAILED with error_message "Execution timed out after {hours} hours"
```

Response model:
```python
class CleanupTriggeredResponse(BaseModel):
    cleaned: int   # Total cleaned up
    pending: int   # Pending executions timed out
    running: int   # Running executions timed out
    failed: int    # Failed to clean up
```

---

### 2.4 Execution Logs Repository

**File:** `/Users/jack/GitHub/bifrost/api/src/repositories/execution_logs.py`

The `ExecutionLogRepository` provides:
- `append_log()` / `append_logs_batch()`: Add log entries
- `get_logs()`: Get logs for a single execution
- `list_logs()`: Cross-execution log aggregation with filtering

#### List Logs Implementation

```python
async def list_logs(
    self,
    organization_id: UUID | None = None,
    workflow_name: str | None = None,
    levels: list[str] | None = None,
    message_search: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], str | None]:
```

Returns log entries with joined data:
```python
{
    "id": log.id,
    "execution_id": str(log.execution_id),
    "organization_name": log.execution.organization.name if log.execution.organization else None,
    "workflow_name": log.execution.workflow_name,
    "level": log.level,
    "message": log.message,
    "timestamp": log.timestamp,
}
```

---

### 2.5 System Logs (Stub)

**File:** `/Users/jack/GitHub/bifrost/api/src/routers/logs.py`

The `/api/logs` endpoint is a stub implementation:
```python
@router.get("")
async def list_logs(ctx: Context, user: CurrentSuperuser, ...) -> SystemLogsListResponse:
    # Stub implementation - returns empty list
    return SystemLogsListResponse(logs=[], continuation_token=None)
```

**Note:** This is marked for future PostgreSQL implementation. It's separate from execution logs.

---

## 3. Frontend Architecture

### 3.1 Execution History Page

**File:** `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionHistory.tsx`

The main execution history page provides:
- Execution list with filtering
- Status filter tabs (All, Completed, Running, Failed, Pending)
- Date range picker
- Organization filter (admin only)
- Search by workflow name, user, or execution ID
- "Show Local Executions" toggle
- "Logs View" toggle (admin only)
- Stuck execution cleanup dialog

#### Admin-Only Features

```tsx
{isPlatformAdmin && (
    <div className="flex items-center gap-2">
        <Switch
            id="view-mode"
            checked={viewMode === "logs"}
            onCheckedChange={(checked) => setViewMode(checked ? "logs" : "executions")}
        />
        <Label>Logs View</Label>
    </div>
)}

{isPlatformAdmin && (
    <OrganizationSelect
        value={filterOrgId}
        onChange={setFilterOrgId}
        showAll={true}
        showGlobal={true}
    />
)}
```

#### Cleanup Dialog

```tsx
<Dialog open={cleanupDialogOpen}>
    <DialogTitle>Cleanup Stuck Executions</DialogTitle>
    <DialogDescription>
        Stuck executions are workflows that have been in Pending status
        for 10+ minutes or Running status for 30+ minutes.
    </DialogDescription>
    {/* Shows table of stuck executions */}
    <Button onClick={handleTriggerCleanup}>
        Cleanup {stuckExecutions.length} Execution{s}
    </Button>
</Dialog>
```

---

### 3.2 Logs View Component

**File:** `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionHistory/components/LogsView.tsx`

A dedicated view for admin log aggregation:

```tsx
interface LogsViewProps {
    filterOrgId?: string | null;    // Organization filter
    dateRange?: DateRange;           // Date range filter
    searchTerm?: string;             // Message/workflow search
    logLevel?: string;               // Log level filter
}
```

Uses key-based remounting to reset pagination when filters change:
```tsx
export function LogsView(props: LogsViewProps) {
    const filterKey = `${filterOrgId ?? "all"}-${searchTerm ?? ""}-${dateRange?.from?.toISOString() ?? "none"}-${logLevel ?? "all"}`;
    return <LogsViewInner key={filterKey} {...props} />;
}
```

---

### 3.3 Logs Table Component

**File:** `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionHistory/components/LogsTable.tsx`

Displays log entries in a data table:

| Column | Description |
|--------|-------------|
| Organization | Organization name or em-dash |
| Workflow | Workflow name |
| Level | Badge with color (DEBUG=outline, INFO=default, WARNING=warning, ERROR/CRITICAL=destructive) |
| Message | Truncated message text |
| Timestamp | Formatted datetime |

Clicking a row opens the ExecutionDrawer.

---

### 3.4 Execution Drawer Component

**File:** `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionHistory/components/ExecutionDrawer.tsx`

A slide-over panel showing execution details:

```tsx
interface ExecutionDrawerProps {
    executionId: string | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}
```

Features:
- Workflow name and status badge
- Metadata grid (executed by, organization, started, duration)
- Error message display (if present)
- Result panel (if present)
- Logs panel with admin-aware filtering
- "Open in new tab" button linking to `/history/{executionId}`

---

### 3.5 Execution Details Page

**File:** `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionDetails.tsx`

Full-page execution details view at `/history/:executionId`:

#### Admin-Only Sections

```tsx
{/* Runtime Variables - Platform admins only */}
{isPlatformAdmin && isComplete && (
    <Card>
        <CardTitle>Runtime Variables</CardTitle>
        <CardDescription>
            Variables captured from script namespace (admin only)
        </CardDescription>
        <VariablesTreeView data={variablesData} />
    </Card>
)}

{/* Usage Card - Compute resources (admin) + AI usage (all users) */}
{isPlatformAdmin && (execution?.peak_memory_bytes || execution?.cpu_total_seconds) && (
    <div>Peak Memory: {formatBytes(execution.peak_memory_bytes)}</div>
    <div>CPU Time: {execution.cpu_total_seconds.toFixed(3)}s</div>
)}
```

#### Log Level Display

Non-admin users see message: "INFO, WARNING, ERROR only"
```tsx
<CardDescription>
    Python logger output from workflow execution
    {!isPlatformAdmin && " (INFO, WARNING, ERROR only)"}
</CardDescription>
```

---

### 3.6 System Logs Page

**File:** `/Users/jack/GitHub/bifrost/client/src/pages/SystemLogs.tsx`

A separate page for system-level logs (platform events, not workflow executions):

- Requires platform admin access (checks `isPlatformAdmin`)
- Category filter: discovery, organization, user, role, config, secret, form, oauth, system, error
- Level filter tabs: All, error, warning, info, critical
- Date range filters
- Message search
- Pagination

**Note:** Currently returns empty data (backend is stub implementation).

---

### 3.7 React Hooks

#### useLogs Hook

**File:** `/Users/jack/GitHub/bifrost/client/src/hooks/useLogs.ts`

```typescript
export function useLogs(
    filters?: LogFilters,
    continuationToken?: string,
    enabled: boolean = true,
)
```

Calls `GET /api/executions/logs` with filter parameters.

#### useExecutions Hook

**File:** `/Users/jack/GitHub/bifrost/client/src/hooks/useExecutions.ts`

```typescript
export function useExecutions(
    filterScope?: string | null,  // undefined=all, null=global, string=org UUID
    filters?: ExecutionFilters,
    continuationToken?: string,
)

export function useExecution(executionId: string | undefined, disablePolling = false)
export function useExecutionLogs(executionId: string | undefined, enabled = true)
export function useExecutionVariables(executionId: string | undefined, enabled = true)
```

---

## 4. Data Models

### 4.1 Execution Response Model

**File:** `/Users/jack/GitHub/bifrost/api/src/models/contracts/executions.py`

```python
class WorkflowExecution(BaseModel):
    execution_id: str
    workflow_name: str
    org_id: str | None              # Organization ID
    org_name: str | None            # Organization name (effective scope)
    form_id: str | None
    executed_by: str
    executed_by_name: str
    status: ExecutionStatus
    input_data: dict[str, Any]
    result: dict | list | str | None
    result_type: str | None         # json, html, text
    error_message: str | None
    duration_ms: int | None
    started_at: datetime | None
    completed_at: datetime | None
    logs: list[dict] | None         # Logger output
    variables: dict | None          # Runtime variables (admin only)
    session_id: str | None          # CLI session ID
    # Resource metrics (admin only, null for non-admins)
    peak_memory_bytes: int | None
    cpu_total_seconds: float | None
    execution_model: str | None     # 'process' or 'thread'
    # AI usage tracking
    ai_usage: list[AIUsagePublicSimple] | None
    ai_totals: AIUsageTotalsSimple | None
```

### 4.2 Log List Entry Model

```python
class LogListEntry(BaseModel):
    id: int
    execution_id: str
    organization_name: str | None
    workflow_name: str
    level: str
    message: str
    timestamp: datetime
```

### 4.3 Execution Status Enum

```python
class ExecutionStatus(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCESS = "Success"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    CANCELLING = "Cancelling"
    TIMEOUT = "Timeout"
    COMPLETED_WITH_ERRORS = "CompletedWithErrors"
```

---

## 5. Key Concepts to Document

### 5.1 Platform Admin Access
- How `is_superuser` is determined (JWT claims)
- What additional capabilities admins have
- Organization scope vs global scope

### 5.2 Execution Log Filtering
- DEBUG/TRACEBACK logs hidden from non-admins
- Cross-organization log aggregation (Logs View)
- Available filter parameters

### 5.3 Stuck Execution Management
- What constitutes a "stuck" execution
- Cleanup process and timeouts
- Redis orphan cleanup

### 5.4 Admin-Only Execution Data
- Runtime variables
- Resource metrics (peak memory, CPU time)
- Execution model information

### 5.5 Real-time Updates
- WebSocket/PubSub for live execution updates
- Streaming logs during execution
- Auto-refresh behavior

---

## 6. File Paths Summary

### Backend
| Path | Description |
|------|-------------|
| `/Users/jack/GitHub/bifrost/api/src/core/auth.py` | Authentication and authorization |
| `/Users/jack/GitHub/bifrost/api/src/routers/executions.py` | Execution endpoints including admin logs |
| `/Users/jack/GitHub/bifrost/api/src/routers/logs.py` | System logs endpoint (stub) |
| `/Users/jack/GitHub/bifrost/api/src/repositories/execution_logs.py` | Log repository with aggregation |
| `/Users/jack/GitHub/bifrost/api/src/models/contracts/executions.py` | Pydantic models |

### Frontend
| Path | Description |
|------|-------------|
| `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionHistory.tsx` | Main history page |
| `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionHistory/components/LogsView.tsx` | Admin logs aggregation view |
| `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionHistory/components/LogsTable.tsx` | Logs data table |
| `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionHistory/components/ExecutionDrawer.tsx` | Execution details drawer |
| `/Users/jack/GitHub/bifrost/client/src/pages/ExecutionDetails.tsx` | Full execution details page |
| `/Users/jack/GitHub/bifrost/client/src/pages/SystemLogs.tsx` | System logs page |
| `/Users/jack/GitHub/bifrost/client/src/hooks/useLogs.ts` | Logs fetching hook |
| `/Users/jack/GitHub/bifrost/client/src/hooks/useExecutions.ts` | Executions fetching hooks |

---

## 7. Recent Changes

Based on git history:
- `79240a07` - Remove app viewer overlay and related state management
- `d5ac6058` - fix(logs-view): remove duplicate filter UI, reuse parent filters
- `f596a36a` - refactor(client): simplify LogsView to reuse parent filters
- `5a617279` - fix(client): fix ExecutionDrawer URL path and improve padding
- `ce7f84a3` - fix(client): replace useEffect with handler-based pagination reset in LogsView

These indicate recent work on simplifying the LogsView component to share filter state with the parent ExecutionHistory page, reducing duplication.

---

## 8. Documentation State

### 8.1 Existing Documentation

| File Path | Description | Admin Coverage |
|-----------|-------------|----------------|
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/core-concepts/permissions.md` | Basic permissions & roles overview | Minimal - mentions "Platform Admins" but no details on admin-specific features |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/core-concepts/error-handling.mdx` | Error handling and execution statuses | Partial - mentions platform admins see full details, references "debugging errors" section |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/core-concepts/platform-overview.mdx` | Platform architecture overview | Minimal - architecture diagram shows "Admin" in client layer but no explanation |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/core-concepts/workflows.mdx` | Workflow concepts | Minimal - mentions `context.is_platform_admin` check in example |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/core-concepts/scopes.mdx` | Global vs organization scopes | Mentions platform admins managing global resources but no admin feature docs |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/troubleshooting/workflow-engine.md` | Troubleshooting guide | No admin-specific content; mentions execution logs but not admin features |

### 8.2 Gaps Identified

#### Critical Gaps (No Documentation Exists)

1. **Admin Execution Logs Page**
   - No documentation for the cross-organization log aggregation feature (Logs View)
   - No explanation of the `/api/executions/logs` endpoint and its filter parameters
   - Missing: organization_id, workflow_name, levels, message_search, date range filters

2. **Stuck Execution Cleanup**
   - No documentation for stuck execution detection and cleanup feature
   - Missing: API endpoints (`GET /api/executions/cleanup/stuck`, `POST /api/executions/cleanup/trigger`)
   - No explanation of what constitutes a "stuck" execution (Pending 10+ min, Running 30+ min)
   - Redis orphan cleanup (`POST /api/executions/cleanup/redis-orphans`) undocumented

3. **Execution Variables Viewing**
   - No documentation for admin-only runtime variables feature
   - Missing: `/api/executions/{execution_id}/variables` endpoint
   - No explanation of VariablesTreeView component and its purpose

4. **Resource Metrics**
   - No documentation for admin-only resource metrics (peak_memory_bytes, cpu_total_seconds)
   - No explanation of when/why these metrics are captured
   - No UI documentation for viewing metrics in ExecutionDetails page

5. **Log Level Filtering**
   - No documentation explaining DEBUG/TRACEBACK logs are hidden from non-admins
   - Not mentioned in error-handling.mdx despite discussing error visibility
   - Missing explanation of why this filtering exists

6. **System Logs Page**
   - `/Users/jack/GitHub/bifrost/client/src/pages/SystemLogs.tsx` exists but has no documentation
   - Separate from execution logs - covers platform events
   - Backend is stub implementation, but UI exists

#### Partial Gaps (Incomplete Coverage)

1. **Platform Admin Permissions** (`permissions.md`)
   - Lists capabilities ("Manage all users", "Access all workflows") but no specifics
   - Doesn't explain how `is_superuser` flag works
   - Doesn't mention execution monitoring capabilities
   - Missing: what makes someone a platform admin, how it's assigned

2. **Error Visibility** (`error-handling.mdx`)
   - Good coverage of UserError vs standard exceptions
   - Missing: explicit documentation that platform admins see DEBUG/TRACEBACK logs
   - Missing: screenshots or examples of admin vs user view

3. **Organization Filter**
   - Scopes documentation covers global vs org-scoped resources
   - Missing: admin ability to filter executions by organization
   - Missing: OrganizationSelect component for admins

### 8.3 Recommended Actions

#### Priority 1: Create New Documentation

1. **Create `/how-to-guides/admin/execution-monitoring.mdx`**
   - Document Logs View feature for cross-org log aggregation
   - Explain filter options (organization, workflow name, log levels, date range, message search)
   - Include screenshots of the LogsView component
   - Reference API endpoint details

2. **Create `/how-to-guides/admin/stuck-execution-cleanup.mdx`**
   - Explain what stuck executions are and thresholds
   - Document cleanup dialog workflow
   - Include API endpoint reference
   - Add troubleshooting guidance

3. **Create `/how-to-guides/admin/execution-debugging.mdx`**
   - Document runtime variables feature
   - Explain resource metrics (memory, CPU)
   - Show ExecutionDetails admin-only sections
   - Compare admin vs user view of execution details

#### Priority 2: Update Existing Documentation

4. **Update `permissions.md`**
   - Add section: "Platform Admin Capabilities" with specific features:
     - Cross-org execution viewing
     - Logs View access
     - Variables and metrics viewing
     - Stuck execution cleanup
     - DEBUG/TRACEBACK log access
   - Add section: "How Platform Admin Access is Determined"
   - Reference new admin guides

5. **Update `error-handling.mdx`**
   - Add explicit note about DEBUG/TRACEBACK filtering for non-admins
   - Add comparison table showing what each user type sees in logs
   - Cross-reference to new admin debugging guide

6. **Update `workflows.mdx`**
   - Expand "State & Logging" section to mention admin-only runtime variables capture
   - Add note about resource metrics being captured

#### Priority 3: Navigation and Structure

7. **Add admin section to documentation structure**
   - Create `/how-to-guides/admin/` directory
   - Add to navigation in astro.config.mjs or equivalent
   - Consider sidebar grouping for admin topics

8. **Add cross-references**
   - Link from troubleshooting to admin cleanup guide
   - Link from permissions to specific admin features
   - Link from error handling to admin debugging

### 8.4 Content Accuracy Notes

The existing documentation that touches on admin features is generally accurate but incomplete:

- `permissions.md`: Accurate but high-level; needs expansion
- `error-handling.mdx`: Accurate table of error visibility; missing log level filtering detail
- `workflows.mdx`: Code example using `context.is_platform_admin` is accurate
- `platform-overview.mdx`: Architecture diagram is accurate

No inaccuracies were found, only gaps in coverage.
