# Data Table Refresh & Org Quick Nav Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add refresh button to all data tables and quick navigation icon to org selector

**Architecture:** Extend existing DataTable and OrgSelector components with optional props; pages pass refetch callbacks from TanStack Query hooks

**Tech Stack:** React, TypeScript, TanStack Query v5, lucide-react icons, shadcn/ui components

---

## Task 1: Add Refresh Button to DataTable Component

**Files:**
- Modify: `client/src/components/ui/data-table.tsx:1-138,906-933`

**Step 1: Add RotateCw import to imports section**

In `client/src/components/ui/data-table.tsx`, add `RotateCw` to the lucide-react imports:

```typescript
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Columns3,
  Filter,
  GripVertical,
  Pin,
  RotateCw,  // ADD THIS
  Search,
  X,
} from "lucide-react";
```

**Step 2: Add new props to DataTableProps interface**

In `client/src/components/ui/data-table.tsx:79-138`, add two new optional props to the interface:

```typescript
export interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  /** Columns to pin to the left (by column id) */
  pinnedColumns?: string[];
  /** Enable row click handling */
  onRowClick?: (row: TData) => void;
  /** Loading state */
  isLoading?: boolean;
  /** Empty state content */
  emptyContent?: React.ReactNode;
  /** Optional className for the container */
  className?: string;
  /** Total number of items for pagination */
  total?: number;
  /** Current pagination state */
  pagination?: PaginationState;
  /** Callback for pagination changes */
  onPaginationChange?: (pagination: PaginationState) => void;
  /** Available page sizes */
  pageSizeOptions?: number[];
  /** Enable column visibility toggle */
  showColumnToggle?: boolean;
  /** Controlled column visibility state */
  columnVisibility?: VisibilityState;
  /** Callback for column visibility changes */
  onColumnVisibilityChange?: (visibility: VisibilityState) => void;
  /** Storage key for persisting column visibility (used only when API persistence is not enabled) */
  columnVisibilityStorageKey?: string;
  /** Search input value */
  searchValue?: string;
  /** Callback for search input changes */
  onSearchChange?: (value: string) => void;
  /** Placeholder text for search input */
  searchPlaceholder?: string;
  /** Column filters configuration - array of {columnId, options} */
  filterableColumns?: Array<{
    columnId: string;
    title: string;
    options: Array<{ label: string; value: string }>;
  }>;
  /** Active column filters */
  columnFilters?: ColumnFilter[];
  /** Callback for column filter changes */
  onColumnFiltersChange?: (filters: ColumnFilter[]) => void;
  /** Column order state */
  columnOrder?: ColumnOrderState;
  /** Callback for column order changes */
  onColumnOrderChange?: (order: ColumnOrderState) => void;
  /** Storage key for persisting column order (used only when API persistence is not enabled) */
  columnOrderStorageKey?: string;
  /** When true, uses API persistence via callbacks and disables localStorage */
  useApiPersistence?: boolean;
  /** Show disabled toggle value */
  showDisabled?: boolean;
  /** Callback for show disabled toggle changes */
  onShowDisabledChange?: (value: boolean) => void;
  /** Label for show disabled toggle (default: "Show Disabled") */
  showDisabledLabel?: string;
  /** Refresh callback - when provided, shows refresh button */
  onRefresh?: () => void | Promise<void>;  // ADD THIS
  /** Refresh loading state */
  isRefreshing?: boolean;  // ADD THIS
}
```

**Step 3: Add Tooltip imports**

Add Tooltip components to imports:

```typescript
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";  // ADD THIS
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
```

**Step 4: Destructure new props in component**

In the DataTable function signature (around line 622), add the new props to destructuring:

```typescript
export function DataTable<TData, TValue>({
  columns,
  data,
  pinnedColumns = [],
  onRowClick,
  isLoading = false,
  emptyContent,
  className,
  total,
  pagination,
  onPaginationChange,
  pageSizeOptions = [10, 25, 50, 100],
  showColumnToggle = false,
  columnVisibility: controlledColumnVisibility,
  onColumnVisibilityChange,
  columnVisibilityStorageKey,
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search...",
  filterableColumns,
  columnFilters = [],
  onColumnFiltersChange,
  columnOrder: controlledColumnOrder,
  onColumnOrderChange,
  columnOrderStorageKey,
  useApiPersistence = false,
  showDisabled,
  onShowDisabledChange,
  showDisabledLabel = "Show Disabled",
  onRefresh,  // ADD THIS
  isRefreshing = false,  // ADD THIS
}: DataTableProps<TData, TValue>) {
```

**Step 5: Add refresh button to toolbar**

In the toolbar section (around line 891-933), add the refresh button before the column toggle button:

```typescript
      {/* Toolbar - search and filters outside the table (fixed, does not scroll) */}
      {(hasSearch || hasFilters || showColumnToggle || hasShowDisabled || onRefresh) && (
        <div className="flex items-center justify-between gap-4 shrink-0">
          <div className="flex items-center gap-4 flex-1">
            {hasSearch && (
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder={searchPlaceholder}
                  value={searchValue}
                  onChange={(e) => onSearchChange(e.target.value)}
                  className="pl-9 bg-transparent border-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
                />
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {onRefresh && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 w-8 p-0"
                      onClick={onRefresh}
                      disabled={isRefreshing}
                    >
                      <RotateCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Refresh data</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            {hasFilters && (
              <ColumnFiltersDropdown
                filterableColumns={filterableColumns}
                columnFilters={columnFilters}
                onColumnFiltersChange={onColumnFiltersChange}
              />
            )}
            {hasShowDisabled && (
              <div className="flex items-center gap-2">
                <Switch
                  id="show-disabled"
                  checked={showDisabled}
                  onCheckedChange={onShowDisabledChange}
                />
                <Label htmlFor="show-disabled" className="cursor-pointer text-sm">
                  {showDisabledLabel}
                </Label>
              </div>
            )}
            {showColumnToggle && (
              <ColumnVisibilityToggle
                table={table}
                onColumnOrderChange={handleColumnOrderChange}
              />
            )}
          </div>
        </div>
      )}
```

**Step 6: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors related to data-table.tsx

---

## Task 2: Add Quick Nav Icon to OrgSelector Component

**Files:**
- Modify: `client/src/components/layout/OrgSelector.tsx:1-255`

**Step 1: Add ArrowRight import**

In `client/src/components/layout/OrgSelector.tsx`, add `ArrowRight` to lucide-react imports:

```typescript
import {
    ArrowRight,  // ADD THIS
    Building2,
    Check,
    ChevronsUpDown,
    Globe,
    Loader2,
    Plus,
} from "lucide-react";
```

**Step 2: Add Tooltip imports**

Add Tooltip components to imports section:

```typescript
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";  // ADD THIS
import { Input } from "@/components/ui/input";
```

**Step 3: Add quick nav button next to org selector**

In the return statement (around line 113-209), wrap the Popover in a flex container and add the nav button:

```typescript
    return (
        <>
            <div className="flex items-center gap-1">
                <Popover open={open} onOpenChange={setOpen}>
                    <PopoverTrigger asChild>
                        <Button
                            variant="outline"
                            role="combobox"
                            aria-expanded={open}
                            className="w-[280px] justify-between"
                        >
                            <span className="flex items-center gap-2 truncate">
                                {isGlobalView ? (
                                    <Globe className="h-4 w-4 shrink-0" />
                                ) : (
                                    <Building2 className="h-4 w-4 shrink-0" />
                                )}
                                <span className="truncate">
                                    {isGlobalView
                                        ? "Global View"
                                        : selectedOrg?.name ||
                                          "Select organization"}
                                </span>
                            </span>
                            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[280px] p-0" align="start">
                        <Command>
                            <CommandInput placeholder="Search organizations..." />
                            <CommandList>
                                <CommandEmpty>No organization found.</CommandEmpty>
                                <CommandGroup>
                                    <CommandItem
                                        value="global-view"
                                        onSelect={handleGlobalView}
                                        className="cursor-pointer flex items-center"
                                    >
                                        <Check
                                            className={cn(
                                                "mr-2 h-4 w-4 shrink-0",
                                                isGlobalView
                                                    ? "opacity-100"
                                                    : "opacity-0"
                                            )}
                                        />
                                        <Globe className="mr-2 h-4 w-4 shrink-0" />
                                        <span>Global</span>
                                    </CommandItem>
                                </CommandGroup>
                                <CommandSeparator />
                                <CommandGroup heading="Organizations">
                                    {organizations && organizations.length > 0 ? (
                                        organizations.map((org) => (
                                            <CommandItem
                                                key={org.id}
                                                value={org.name}
                                                onSelect={() =>
                                                    handleOrgSelect(org)
                                                }
                                                className="cursor-pointer flex items-center"
                                            >
                                                <Check
                                                    className={cn(
                                                        "mr-2 h-4 w-4 shrink-0",
                                                        !isGlobalView &&
                                                            selectedOrg?.id ===
                                                                org.id
                                                            ? "opacity-100"
                                                            : "opacity-0"
                                                    )}
                                                />
                                                <Building2 className="mr-2 h-4 w-4 shrink-0" />
                                                <span className="truncate">
                                                    {org.name}
                                                </span>
                                            </CommandItem>
                                        ))
                                    ) : (
                                        <CommandItem disabled>
                                            No organizations
                                        </CommandItem>
                                    )}
                                </CommandGroup>
                            </CommandList>
                            <CommandSeparator />
                            <CommandGroup>
                                <CommandItem
                                    onSelect={handleCreateOrg}
                                    className="cursor-pointer"
                                >
                                    <Plus className="mr-2 h-4 w-4" />
                                    Create organization
                                </CommandItem>
                            </CommandGroup>
                        </Command>
                    </PopoverContent>
                </Popover>

                {/* Quick nav button - only show when org is selected */}
                {currentOrg && !isGlobalView && (
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-9 w-9"
                                    onClick={() => navigate(`/org/${currentOrg.id}`)}
                                >
                                    <ArrowRight className="h-4 w-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                                <p>Go to {currentOrg.name}</p>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                )}
            </div>

            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
                {/* ... rest of Dialog component unchanged ... */}
```

**Step 4: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors related to OrgSelector.tsx

---

## Task 3: Update PasswordsPage with Refresh

**Files:**
- Modify: `client/src/pages/passwords/PasswordsPage.tsx:131-218`

**Step 1: Update usePasswords destructuring**

Modify line 131 to include refetch and isRefetching:

```typescript
  const { data, isLoading, refetch, isRefetching } = usePasswords(orgId!, {
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable**

Update the DataTable component (around line 196-218) to include refresh props:

```typescript
      <DataTable
        className="flex-1 min-h-0"
        columns={columns}
        data={data?.items ?? []}
        total={data?.total}
        pagination={pagination}
        onPaginationChange={setPagination}
        pinnedColumns={pinnedColumns}
        onRowClick={handleRowClick}
        isLoading={isLoading || prefsLoading}
        emptyContent={emptyContent}
        showColumnToggle
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={onColumnVisibilityChange}
        columnOrder={columnOrder}
        onColumnOrderChange={onColumnOrderChange}
        useApiPersistence
        searchValue={searchInput}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search passwords..."
        showDisabled={showDisabled}
        onShowDisabledChange={setShowDisabled}
        onRefresh={refetch}
        isRefreshing={isRefetching}
      />
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 4: Update ConfigurationsPage with Refresh

**Files:**
- Modify: `client/src/pages/configurations/ConfigurationsPage.tsx`

**Step 1: Update useConfigurations destructuring to include refetch**

Find the `useConfigurations` hook call and add `refetch, isRefetching`:

```typescript
  const { data, isLoading, refetch, isRefetching } = useConfigurations(orgId!, {
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable component**

Add these two props to the DataTable:

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 5: Update LocationsPage with Refresh

**Files:**
- Modify: `client/src/pages/locations/LocationsPage.tsx`

**Step 1: Update useLocations destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useLocations(orgId!, {
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 6: Update DocumentsPage with Refresh

**Files:**
- Modify: `client/src/pages/documents/DocumentsPage.tsx`

**Step 1: Update useDocuments destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useDocuments(orgId!, {
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 7: Update CustomAssetsPage with Refresh

**Files:**
- Modify: `client/src/pages/assets/CustomAssetsPage.tsx`

**Step 1: Update useCustomAssets destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useCustomAssets(orgId!, typeId!, {
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 8: Update GlobalPasswordsPage with Refresh

**Files:**
- Modify: `client/src/pages/global/GlobalPasswordsPage.tsx`

**Step 1: Update hook destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useGlobalPasswords({
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 9: Update GlobalConfigurationsPage with Refresh

**Files:**
- Modify: `client/src/pages/global/GlobalConfigurationsPage.tsx`

**Step 1: Update hook destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useGlobalConfigurations({
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 10: Update GlobalLocationsPage with Refresh

**Files:**
- Modify: `client/src/pages/global/GlobalLocationsPage.tsx`

**Step 1: Update hook destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useGlobalLocations({
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 11: Update GlobalDocumentsPage with Refresh

**Files:**
- Modify: `client/src/pages/global/GlobalDocumentsPage.tsx`

**Step 1: Update hook destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useGlobalDocuments({
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 12: Update GlobalCustomAssetsPage with Refresh

**Files:**
- Modify: `client/src/pages/global/GlobalCustomAssetsPage.tsx`

**Step 1: Update hook destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useGlobalCustomAssets(typeId!, {
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 13: Update AuditTrailPage with Refresh (Org-scoped)

**Files:**
- Modify: `client/src/pages/audit/AuditTrailPage.tsx`

**Step 1: Update hook destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useAuditTrail(orgId!, {
    pagination,
    search: debouncedSearch || undefined,
    // ... other params
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 14: Update GlobalAuditTrailPage with Refresh

**Files:**
- Modify: `client/src/pages/audit/GlobalAuditTrailPage.tsx`

**Step 1: Update hook destructuring to include refetch**

```typescript
  const { data, isLoading, refetch, isRefetching } = useGlobalAuditTrail({
    pagination,
    search: debouncedSearch || undefined,
    // ... other params
  });
```

**Step 2: Add refresh props to DataTable component**

```typescript
        onRefresh={refetch}
        isRefreshing={isRefetching}
```

**Step 3: Verify TypeScript compiles**

Run: `cd client && npm run tsc`
Expected: No errors

---

## Task 15: Manual Testing

**Step 1: Start dev server**

Run: `cd client && npm run dev`
Expected: Server starts on http://localhost:5173

**Step 2: Test refresh button on PasswordsPage**

1. Navigate to any org's Passwords page (e.g., `/org/abc123/passwords`)
2. Verify refresh button appears in top-right toolbar (outline style, rotating arrow icon)
3. Hover over button - tooltip should say "Refresh data"
4. Click refresh button
5. Verify icon spins during refresh
6. Verify table data refreshes
7. Verify all filters, sorting, and pagination state is preserved

**Step 3: Test quick nav button on OrgSelector**

1. From dashboard, select an organization using the org selector
2. Verify small ghost button with arrow icon appears next to org selector
3. Hover over button - tooltip should say "Go to [Org Name]"
4. Click the arrow button
5. Verify navigation to `/org/:orgId` (org home page)
6. Navigate to dashboard
7. Verify button still appears (org is still selected)
8. Click it again to navigate back to org

**Step 4: Test refresh on all pages**

Test refresh button works correctly on all these pages:
- Org-scoped: Passwords, Configurations, Locations, Documents, Custom Assets, Audit Trail
- Global: Global Passwords, Global Configurations, Global Locations, Global Documents, Global Custom Assets, Global Audit Trail

For each page:
1. Apply some filters/sorting/search
2. Click refresh button
3. Verify data refreshes
4. Verify all state is preserved

**Step 5: Test edge cases**

1. Test quick nav button when already on org home page (should be no-op)
2. Test quick nav button doesn't appear on global view
3. Test quick nav button doesn't appear when no org selected
4. Test refresh button disabled state while refreshing (can't click twice)
5. Test keyboard navigation (Tab to button, Enter to activate)

**Step 6: Visual regression check**

1. Check that refresh button aligns properly with other toolbar controls
2. Verify spacing is consistent
3. Check mobile responsive behavior (if applicable)
4. Verify dark mode appearance (if applicable)

---

## Final Verification

**Step 1: Run full type check**

Run: `cd client && npm run tsc`
Expected: 0 errors

**Step 2: Run linting**

Run: `cd client && npm run lint`
Expected: 0 errors or warnings

**Step 3: Build for production**

Run: `cd client && npm run build`
Expected: Build succeeds with no errors

---

## Summary

This implementation adds:

1. **DataTable Refresh Button**:
   - Icon-only button with RotateCw icon
   - Outline variant, positioned in top-right toolbar
   - Shows spinning animation during refresh
   - Tooltip for accessibility
   - Only appears when `onRefresh` prop provided

2. **OrgSelector Quick Nav**:
   - Small ghost button with ArrowRight icon
   - Positioned immediately after org selector
   - Only visible when org is selected and not on global view
   - One-click navigation to org home page
   - Tooltip showing org name

3. **12 Pages Updated**:
   - All pages using DataTable now have refresh functionality
   - Preserves all table state during refresh (filters, sorting, pagination, search)
   - Consistent UX across all data tables

**Total Changes**:
- 2 components modified (DataTable, OrgSelector)
- 12 pages updated (simple prop additions)
- ~50 lines of new code
- 0 breaking changes
- Fully type-safe
