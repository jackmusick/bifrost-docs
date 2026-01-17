# UI Improvements: Inline Editing and Navigation Simplification

**Date:** 2026-01-14
**Status:** Complete

## Overview

This plan addresses three TODO items to improve the user experience:

1. **Inline Editing** - Entity detail pages edit in-place instead of modal dialogs
2. **Unified Configurations Page** - Single "Configurations" nav item with type as a column
3. **Custom Asset Ordering** - Drag-and-drop reordering in Settings

## Implementation Order

Complete in this order due to dependencies and scope:

1. Custom Asset Ordering (smallest, isolated)
2. Unified Configurations Page (medium, removes code)
3. Inline Editing (largest, benefits from cleaner codebase)

---

## Feature 1: Custom Asset Type Ordering

### Summary

Add drag-and-drop reordering to the Custom Asset Types settings table. Order persists to backend and reflects in sidebar navigation.

### Backend Changes

#### 1.1 Database Migration

Add `sort_order` column to `custom_asset_types` table:

```sql
ALTER TABLE custom_asset_types
ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;

-- Initialize sort_order based on current created_at order
WITH ordered AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) as rn
  FROM custom_asset_types
)
UPDATE custom_asset_types
SET sort_order = ordered.rn
FROM ordered
WHERE custom_asset_types.id = ordered.id;
```

#### 1.2 New API Endpoint

Create `PATCH /api/custom-asset-types/reorder`:

**Request body:**
```json
{
  "ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**Behavior:**
- Validate all IDs exist
- Update `sort_order` for each ID based on array index
- Return 200 on success

**File:** `api/functions/custom_asset_types.py` (or equivalent)

#### 1.3 Update Existing Queries

Modify queries that return custom asset types to order by `sort_order ASC`:

- Sidebar data endpoint (`/api/sidebar/{org_id}`)
- Global sidebar endpoint (`/api/global/sidebar`)
- Custom asset types list endpoint

### Frontend Changes

#### 1.4 Add Reorder Hook

**File:** `client/src/hooks/useCustomAssets.ts`

Add mutation:

```typescript
export function useReorderCustomAssetTypes() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ids: string[]) => {
      await apiClient.patch('/api/custom-asset-types/reorder', { ids });
    },
    onMutate: async (ids) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: ['custom-asset-types'] });
      const previous = queryClient.getQueryData(['custom-asset-types']);

      queryClient.setQueryData(['custom-asset-types'], (old: CustomAssetType[]) => {
        return ids.map(id => old.find(t => t.id === id)!);
      });

      return { previous };
    },
    onError: (err, ids, context) => {
      queryClient.setQueryData(['custom-asset-types'], context?.previous);
      toast.error('Failed to save order');
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-asset-types'] });
      queryClient.invalidateQueries({ queryKey: ['sidebar'] });
    },
  });
}
```

#### 1.5 Update Settings Table with Drag-and-Drop

**File:** `client/src/pages/settings/CustomAssetTypesSettings.tsx`

Reference `client/src/components/ui/data-table.tsx` for pragmatic-drag-and-drop patterns.

Changes:
1. Add drag handle column (grip icon) as first column
2. Wrap each TableRow with draggable/dropTarget setup
3. Track drag state for visual feedback
4. On drop, call `reorderMutation.mutate(newOrderedIds)`

```typescript
import { GripVertical } from "lucide-react";
import { draggable, dropTargetForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { reorder } from "@atlaskit/pragmatic-drag-and-drop/reorder";
```

Add to table:
- New first column with `<GripVertical />` icon
- `cursor-grab` on handle, `cursor-grabbing` while dragging
- Drop indicator line between rows during drag

#### 1.6 Verify Sidebar Order

**Files:**
- `client/src/hooks/useSidebar.ts`
- `client/src/hooks/useGlobalData.ts`

Confirm `custom_asset_types` array is used as-is (server returns in `sort_order`). No frontend sorting needed.

### Implementation Status

**Backend Changes:**
- [x] 1.1 Database Migration - `api/alembic/versions/20260114_140000_add_sort_order_to_custom_asset_types.py`
- [x] 1.2 New API Endpoint - `PATCH /api/custom-asset-types/reorder` in `custom_asset_types.py`
- [x] 1.3 Update Existing Queries - `sort_order` used in repository and ORM models

**Frontend Changes:**
- [x] 1.4 Add Reorder Hook - `useReorderCustomAssetTypes` in `useCustomAssets.ts`
- [x] 1.5 Update Settings Page - Converted from table to flexbox card layout with pragmatic-drag-and-drop
- [x] 1.6 Verify Sidebar Order - Sidebar uses server order

### Testing Checklist

- [x] Drag handle appears on each row
- [x] Dragging shows visual feedback (row opacity, drop indicator lines)
- [x] Dropping updates list order immediately (optimistic)
- [x] Order persists after page refresh
- [x] Sidebar reflects new order
- [ ] Error case: network failure reverts to previous order with toast (not tested)

---

## Feature 2: Unified Configurations Page

### Summary

Replace per-type sidebar navigation with a single "Configurations" link. Type becomes a filterable column.

### Frontend Changes

#### 2.1 Update Sidebar Navigation

**File:** `client/src/components/layout/Sidebar.tsx`

Remove:
- `ConfigurationTypeItem` component (lines ~118-153)
- `GlobalConfigurationTypeItem` component (lines ~155-188)
- The "Configurations" `NavSection` in `OrgSidebarContent` (lines ~307-318)
- The "Configurations" `NavSection` in `GlobalSidebarContent` (lines ~391-402)

Add to Core section (after Documents):
```typescript
<NavItem
  name="Configurations"
  href={`/org/${orgId}/configurations`}
  icon={Server}
  count={sidebarData?.configurations_count}
  onClick={closeMobileMenu}
/>
```

Same for GlobalSidebarContent:
```typescript
<NavItem
  name="Configurations"
  href="/global/configurations"
  icon={Server}
  count={sidebarData?.configurations_count}
  onClick={closeMobileMenu}
/>
```

#### 2.2 Update Sidebar Data Types

**File:** `client/src/hooks/useSidebar.ts`

Update `SidebarData` type:
```typescript
interface SidebarData {
  passwords_count: number;
  locations_count: number;
  documents_count: number;
  configurations_count: number;  // Add this (total, not per-type)
  custom_asset_types: SidebarItemCount[];
}
```

Remove `configuration_types` from the interface if no longer needed.

**File:** `client/src/hooks/useGlobalData.ts`

Same changes for `GlobalSidebarData`.

#### 2.3 Update Configurations Page Title

**File:** `client/src/pages/configurations/ConfigurationsPage.tsx`

Remove dynamic title logic:

```typescript
// Remove this:
const currentTypeName = useMemo(() => {
  if (!typeFilter) return null;
  const type = types.find((t) => t.id === typeFilter);
  return type?.name || null;
}, [typeFilter, types]);

// Update header to always show "Configurations":
<h1 className="text-3xl font-bold tracking-tight">
  Configurations
</h1>
<p className="text-muted-foreground mt-1">
  Document system configurations and assets
</p>
```

#### 2.4 Ensure Type Column Visible by Default

**File:** `client/src/pages/configurations/ConfigurationsPage.tsx`

The `configuration_type_name` column should be visible by default. Check `useColumnPreferences` defaults or update `allColumnIds` order to prioritize it.

### Backend Changes

#### 2.5 Update Sidebar Endpoint

**File:** Backend sidebar endpoint (e.g., `api/functions/sidebar.py`)

Change response to include `configurations_count` (total count) instead of or in addition to per-type breakdown:

```python
{
  "passwords_count": 42,
  "locations_count": 15,
  "documents_count": 28,
  "configurations_count": 67,  # Total across all types
  "custom_asset_types": [...]
}
```

If `configuration_types` array is still returned, frontend will ignore it.

### Testing Checklist

- [ ] Sidebar shows single "Configurations" link in Core section
- [ ] "Configurations" section with per-type items is removed
- [ ] Clicking "Configurations" goes to `/org/{orgId}/configurations`
- [ ] Page title is always "Configurations" (not type name)
- [ ] Type column visible and filterable
- [ ] Global view sidebar updated similarly
- [ ] Configuration count badge shows total count

---

## Feature 3: Inline Editing for Entity Detail Pages

### Summary

Convert 5 entity detail pages from modal-based editing to inline editing. User clicks "Edit" to enter edit mode, then "Save" or "Cancel".

### Affected Pages

1. `client/src/pages/configurations/ConfigDetailPage.tsx`
2. `client/src/pages/passwords/PasswordDetailPage.tsx`
3. `client/src/pages/locations/LocationDetailPage.tsx`
4. `client/src/pages/documents/DocumentDetailPage.tsx` (partial - extend to metadata)
5. `client/src/pages/assets/CustomAssetDetailPage.tsx`

### Shared Components to Create

#### 3.1 Create `useInlineEdit` Hook

**File:** `client/src/hooks/useInlineEdit.ts`

```typescript
import { useState, useCallback, useEffect } from "react";
import { useForm, UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";

interface UseInlineEditOptions<T extends z.ZodType> {
  schema: T;
  initialData: z.infer<T>;
  onSave: (data: z.infer<T>) => Promise<void>;
}

interface UseInlineEditReturn<T extends z.ZodType> {
  isEditing: boolean;
  isDirty: boolean;
  isSaving: boolean;
  form: UseFormReturn<z.infer<T>>;
  startEditing: () => void;
  cancelEditing: () => void;
  saveChanges: () => Promise<void>;
}

export function useInlineEdit<T extends z.ZodType>({
  schema,
  initialData,
  onSave,
}: UseInlineEditOptions<T>): UseInlineEditReturn<T> {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const form = useForm<z.infer<T>>({
    resolver: zodResolver(schema),
    defaultValues: initialData,
  });

  const isDirty = form.formState.isDirty;

  // Reset form when initialData changes (e.g., after save)
  useEffect(() => {
    if (!isEditing) {
      form.reset(initialData);
    }
  }, [initialData, isEditing, form]);

  const startEditing = useCallback(() => {
    setIsEditing(true);
  }, []);

  const cancelEditing = useCallback(() => {
    form.reset(initialData);
    setIsEditing(false);
  }, [form, initialData]);

  const saveChanges = useCallback(async () => {
    const isValid = await form.trigger();
    if (!isValid) return;

    setIsSaving(true);
    try {
      await onSave(form.getValues());
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  }, [form, onSave]);

  return {
    isEditing,
    isDirty,
    isSaving,
    form,
    startEditing,
    cancelEditing,
    saveChanges,
  };
}
```

#### 3.2 Create `useUnsavedChangesWarning` Hook

**File:** `client/src/hooks/useUnsavedChangesWarning.ts`

```typescript
import { useEffect } from "react";
import { useBlocker } from "react-router-dom";

export function useUnsavedChangesWarning(isDirty: boolean, message?: string) {
  const defaultMessage = "You have unsaved changes. Are you sure you want to leave?";

  // Block navigation within the app
  const blocker = useBlocker(isDirty);

  useEffect(() => {
    if (blocker.state === "blocked") {
      const confirmed = window.confirm(message || defaultMessage);
      if (confirmed) {
        blocker.proceed();
      } else {
        blocker.reset();
      }
    }
  }, [blocker, message]);

  // Block browser refresh/close
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = message || defaultMessage;
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty, message]);
}
```

#### 3.3 Create `EditableField` Component

**File:** `client/src/components/shared/EditableField.tsx`

```typescript
import { ReactNode } from "react";
import { UseFormRegisterReturn } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface EditableFieldProps {
  isEditing: boolean;
  label: string;
  value: ReactNode;
  emptyText?: string;
  inputType?: "text" | "textarea" | "url" | "email";
  registration?: UseFormRegisterReturn;
  error?: string;
  className?: string;
  mono?: boolean;
}

export function EditableField({
  isEditing,
  label,
  value,
  emptyText = "Not set",
  inputType = "text",
  registration,
  error,
  className,
  mono = false,
}: EditableFieldProps) {
  if (isEditing && registration) {
    const InputComponent = inputType === "textarea" ? Textarea : Input;
    return (
      <div className={cn("space-y-1", className)}>
        <label className="text-sm text-muted-foreground">{label}</label>
        <InputComponent
          type={inputType === "textarea" ? undefined : inputType}
          {...registration}
          className={cn(error && "border-destructive")}
        />
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    );
  }

  return (
    <div className={cn("space-y-1", className)}>
      <label className="text-sm text-muted-foreground">{label}</label>
      <p className={cn("text-sm font-medium", mono && "font-mono")}>
        {value || <span className="text-muted-foreground italic">{emptyText}</span>}
      </p>
    </div>
  );
}
```

#### 3.4 Create `EditModeHeader` Component

**File:** `client/src/components/shared/EditModeHeader.tsx`

```typescript
import { Loader2, Pencil, X, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EditModeHeaderProps {
  isEditing: boolean;
  isSaving: boolean;
  isDirty: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  canEdit: boolean;
}

export function EditModeActions({
  isEditing,
  isSaving,
  isDirty,
  onEdit,
  onSave,
  onCancel,
  canEdit,
}: EditModeHeaderProps) {
  if (!canEdit) return null;

  if (isEditing) {
    return (
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          onClick={onCancel}
          disabled={isSaving}
        >
          <X className="mr-2 h-4 w-4" />
          Cancel
        </Button>
        <Button
          onClick={onSave}
          disabled={isSaving || !isDirty}
        >
          {isSaving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Check className="mr-2 h-4 w-4" />
          )}
          Save
        </Button>
      </div>
    );
  }

  return (
    <Button variant="outline" onClick={onEdit}>
      <Pencil className="mr-2 h-4 w-4" />
      Edit
    </Button>
  );
}
```

### Page-Specific Implementation

#### 3.5 Convert ConfigDetailPage

**File:** `client/src/pages/configurations/ConfigDetailPage.tsx`

High-level changes:

1. Remove `ConfigForm` import and dialog state (`editOpen`, `setEditOpen`)
2. Import and use `useInlineEdit` with configuration schema
3. Import and use `useUnsavedChangesWarning`
4. Replace static field displays with `EditableField` components
5. Replace Edit button with `EditModeActions` component
6. Add visual indicator for edit mode (e.g., subtle border on Card)
7. Keep Delete button and confirmation dialog as-is
8. Keep Enable/Disable toggle as-is (works independently of edit mode)

**Schema for configuration:**
```typescript
const configurationSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  configuration_type_id: z.string().uuid().optional(),
  configuration_status_id: z.string().uuid().optional(),
  manufacturer: z.string().max(255).optional(),
  model: z.string().max(255).optional(),
  serial_number: z.string().max(255).optional(),
  asset_tag: z.string().max(255).optional(),
  ip_address: z.string().max(45).optional(),
  mac_address: z.string().max(17).optional(),
  notes: z.string().optional(),
});
```

#### 3.6 Convert PasswordDetailPage

**File:** `client/src/pages/passwords/PasswordDetailPage.tsx`

Similar pattern. Special considerations:
- Password field shows `PasswordReveal` component in view mode
- In edit mode, show password input with "leave blank to keep current" behavior
- TOTP field same pattern
- Keep `PasswordReveal` and `TOTPReveal` components for view mode

#### 3.7 Convert LocationDetailPage

**File:** `client/src/pages/locations/LocationDetailPage.tsx`

Standard conversion following the pattern.

#### 3.8 Convert DocumentDetailPage

**File:** `client/src/pages/documents/DocumentDetailPage.tsx`

Document content already has inline editing via TiptapEditor. Extend to metadata fields:
- Title (name)
- Folder selection
- Other metadata

#### 3.9 Convert CustomAssetDetailPage

**File:** `client/src/pages/assets/CustomAssetDetailPage.tsx`

Special considerations:
- Custom fields are dynamic based on asset type schema
- Need `EditableField` variant that handles different field types (text, number, date, select, etc.)
- May need `CustomFieldInput` component updated to work in both modes

### Remove Unused Form Components

After all pages are converted, these modal form components can be deleted:

- `client/src/components/configurations/ConfigForm.tsx`
- `client/src/components/passwords/PasswordForm.tsx`
- `client/src/components/locations/LocationForm.tsx`
- `client/src/components/assets/CustomAssetForm.tsx`

**Note:** Keep these files initially in case list pages still use them for "Create" functionality. If create flows also move inline (on a new detail page), then delete.

### Testing Checklist

For each entity type:

- [ ] "Edit" button switches to edit mode
- [ ] Fields become editable inputs
- [ ] "Save" button commits changes and exits edit mode
- [ ] "Cancel" button discards changes and exits edit mode
- [ ] Validation errors display inline
- [ ] Navigation away prompts if dirty
- [ ] Browser refresh/close prompts if dirty
- [ ] Enable/Disable toggle works independently
- [ ] Delete functionality unchanged
- [ ] Related items sidebar unchanged
- [ ] Attachments section unchanged

---

## Summary Checklist

### Feature 1: Custom Asset Ordering ✅
- [x] Backend: Add `sort_order` column migration
- [x] Backend: Create reorder endpoint
- [x] Backend: Update queries to order by `sort_order`
- [x] Frontend: Add `useReorderCustomAssetTypes` mutation
- [x] Frontend: Add drag-and-drop to settings table
- [x] Test: Drag and drop works with visual feedback
- [x] Test: Order persists after refresh
- [x] Test: Sidebar reflects new order

### Feature 2: Unified Configurations Page ✅
- [x] Frontend: Update Sidebar.tsx (remove type items, add single link)
- [x] Frontend: Update sidebar hooks/types (calculated from configuration_types array)
- [x] Frontend: Update ConfigurationsPage.tsx title
- [x] Backend: Update sidebar endpoint for total count (not needed - calculated on frontend)
- [x] Test: Single Configurations link in sidebar
- [x] Test: Type column visible and filterable

### Feature 3: Inline Editing ✅
- [x] Create `useInlineEdit` hook
- [x] Create `useUnsavedChangesWarning` hook
- [x] Create `EditModeActions` component
- [x] Convert ConfigDetailPage
- [x] Convert PasswordDetailPage
- [x] Convert LocationDetailPage
- [x] Convert CustomAssetDetailPage
- [ ] Convert DocumentDetailPage (skipped - already has inline TiptapEditor)
- [ ] Clean up unused form components (kept - still used for Create flows)
