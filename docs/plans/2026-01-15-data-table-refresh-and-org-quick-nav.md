# Data Table Refresh Button and Org Quick Navigation

**Date**: 2026-01-15
**Status**: Design Approved

## Overview

This design addresses two UX improvements:
1. Adding a refresh button to all data tables for manual data refresh
2. Adding a quick navigation icon to the org selector for one-click access to selected org

## Problem Statement

### Data Table Refresh
Users currently have no way to manually refresh data tables without reloading the page or changing filters. When data may have changed externally (e.g., by another user or background process), users need a simple way to get the latest data.

### Org Navigation Friction
When an org is already selected in the org selector, users must click through the dropdown again to navigate to that org's home page. This creates unnecessary friction: "I'm already selected, why do I have to do this to get to documentation?"

## Design

### Feature 1: Data Table Refresh Button

#### Component Architecture

Extend the existing `DataTable` component (`/client/src/components/ui/data-table.tsx`) with optional refresh functionality.

**New Props**:
```typescript
interface DataTableProps<TData, TValue> {
  // ... existing props
  onRefresh?: () => void | Promise<void>;  // Optional refresh handler
  isRefreshing?: boolean;                   // Optional loading state
}
```

**Visual Design**:
- **Icon**: `RotateCw` from lucide-react (rotating arrow)
- **Variant**: `outline` button
- **Size**: Icon-only button (~40px), matching existing controls
- **Position**: Top-right toolbar, just before column toggle button
- **Loading State**: Spin animation on icon when `isRefreshing={true}`
- **Tooltip**: "Refresh data"

**Behavior**:
- Clicking the button calls `onRefresh()` callback
- During refresh, button shows spinning animation
- All current table state preserved: filters, sorting, pagination, search
- Works with existing TanStack Query data fetching patterns

#### Implementation Pattern

Each page using DataTable will pass its refetch method:

```typescript
// Example: PasswordsPage.tsx
const { data, refetch, isRefetching } = usePasswords({
  orgId,
  page: pagination.pageIndex,
  pageSize: pagination.pageSize,
  sortBy: sorting[0]?.id,
  sortOrder: sorting[0]?.desc ? 'desc' : 'asc',
  search: debouncedSearch,
  filters: activeFilters,
});

<DataTable
  columns={columns}
  data={data?.items ?? []}
  // ... other props
  onRefresh={refetch}
  isRefreshing={isRefetching}
/>
```

#### Pages to Update

All 12 pages currently using DataTable:
1. `/client/src/pages/passwords/PasswordsPage.tsx`
2. `/client/src/pages/configurations/ConfigurationsPage.tsx`
3. `/client/src/pages/locations/LocationsPage.tsx`
4. `/client/src/pages/documents/DocumentsPage.tsx`
5. `/client/src/pages/assets/CustomAssetsPage.tsx`
6. `/client/src/pages/global/GlobalPasswordsPage.tsx`
7. `/client/src/pages/global/GlobalConfigurationsPage.tsx`
8. `/client/src/pages/global/GlobalLocationsPage.tsx`
9. `/client/src/pages/global/GlobalDocumentsPage.tsx`
10. `/client/src/pages/global/GlobalCustomAssetsPage.tsx`
11. `/client/src/pages/audit/AuditTrailPage.tsx` (org-scoped)
12. `/client/src/pages/audit/GlobalAuditTrailPage.tsx`

### Feature 2: Org Selector Quick Navigation Icon

#### Component Architecture

Enhance `OrgSelector` component (`/client/src/components/layout/OrgSelector.tsx`) with a quick navigation button.

**Visual Design**:
- **Icon**: `ArrowRight` from lucide-react
- **Variant**: `ghost` button (subtle, less prominent than selector)
- **Size**: Small icon button (~32px)
- **Position**: Immediately to the right of org selector dropdown
- **Conditional**: Only visible when `currentOrg !== null`
- **Tooltip**: "Go to [Org Name]"

**Behavior**:
- Clicking navigates to `/org/:currentOrg.id` (org home page)
- If already on that route, becomes a no-op or scrolls to top
- Uses existing `useNavigate()` from React Router
- Uses existing `currentOrg` from Zustand store

#### Implementation Structure

```typescript
// In OrgSelector.tsx
const { currentOrg } = useOrganizationStore();
const navigate = useNavigate();

return (
  <div className="flex items-center gap-1">
    {/* Existing org selector dropdown */}
    <DropdownMenu>
      {/* ... existing selector code ... */}
    </DropdownMenu>

    {/* NEW: Quick nav button */}
    {currentOrg && (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
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
);
```

#### Edge Cases

1. **Already on target route**: Navigation is safe (no-op or scroll to top)
2. **Permissions**: Button appears regardless of permissions; navigation handles auth
3. **No org selected**: Button hidden (conditional rendering)
4. **Layout impact**: Minimal; button is small and only appears when relevant

## Data Flow

### Refresh Button Flow
```
User clicks refresh
  → Component calls onRefresh()
  → Page-level refetch() triggered
  → TanStack Query re-executes query with current params
  → isRefetching becomes true
  → Button shows spinning animation
  → New data arrives
  → Table re-renders with fresh data
  → isRefetching becomes false
  → Animation stops
```

### Quick Nav Flow
```
User sees org selector with selected org
  → Quick nav icon appears
  → User clicks icon
  → navigate(`/org/${currentOrg.id}`) called
  → React Router navigates to org home
  → Layout re-renders with org-specific content
```

## Testing Considerations

### Refresh Button Testing
1. Verify refresh preserves all table state (filters, sort, pagination, search)
2. Test loading animation appears/disappears correctly
3. Verify works with all data fetching hooks across 12 pages
4. Test error handling if refetch fails
5. Verify button disabled/loading state during refresh
6. Test accessibility (keyboard navigation, screen reader)

### Quick Nav Testing
1. Verify button only appears when org selected
2. Test navigation to org home page
3. Verify tooltip displays correct org name
4. Test behavior when already on target route
5. Test with multiple orgs (switching selection)
6. Verify button disappears when org deselected
7. Test accessibility (keyboard navigation, screen reader)

## Error Handling

### Refresh Button
- If `refetch()` fails, TanStack Query error handling applies
- Existing error toasts/messages will display
- Button returns to non-loading state
- User can retry

### Quick Nav
- If navigation fails, React Router error handling applies
- If org doesn't exist, 404 page shown
- If no permissions, protected route redirects
- Standard error boundary handling

## Accessibility

### Refresh Button
- Semantic button element
- ARIA label: "Refresh data"
- Tooltip for context
- Keyboard accessible (Tab + Enter)
- Loading state announced to screen readers

### Quick Nav Icon
- Semantic button element
- ARIA label: "Go to [Org Name]"
- Tooltip for context
- Keyboard accessible (Tab + Enter)
- Icon with semantic meaning (arrow indicates navigation)

## Implementation Notes

1. **No breaking changes**: Both features are purely additive
2. **Consistent with existing patterns**: Uses same UI components, state management, and routing as rest of app
3. **Minimal code changes**:
   - DataTable: ~20 lines added
   - OrgSelector: ~15 lines added
   - Pages: 2-3 lines per page (pass refetch prop)
4. **Type safety**: All new props properly typed
5. **Performance**: Negligible impact; no new subscriptions or queries

## Future Enhancements

### Refresh Button
- Auto-refresh option (e.g., every 30 seconds)
- Badge showing data age ("Updated 2m ago")
- Keyboard shortcut (e.g., Cmd+R)

### Quick Nav
- Dropdown showing recent org pages instead of just home
- Breadcrumb integration showing current location
- Quick switcher between orgs (Cmd+K integration)

## Decision Log

1. **Refresh preserves state vs. resets**: Chose preserve because users typically want fresh data with their current view/filters
2. **Button placement**: Chose top-right to group with other controls; most discoverable location
3. **Quick nav target**: Chose org home page as safe default; could be enhanced later to remember last visited page
4. **Icon choice**: ArrowRight is clearest indicator of navigation action; considered ExternalLink but implies new window
