# Polish Items Design

**Date:** 2026-01-14
**Status:** Complete

---

## Overview

Final polish pass before migration. 8 tasks covering UI consolidation, scrolling behavior, custom assets improvements, and AI/indexing controls.

---

## Task 1: DataTable Toolbar Consolidation - COMPLETE

**Goal:** Move "Show Disabled" toggle into DataTable toolbar. Keep Add button in header as icon-only outline variant.

### Design (Updated)

**Toolbar layout:**
```
[Search] [Filters?] ... [Show Disabled toggle] [Columns]
```

**Header layout:**
```
Title                                    [+ outline icon button]
Description
```

- "Show Disabled" toggle: positioned left of column selector in DataTable toolbar
- "Add" button: icon-only outline variant in page header (not in toolbar)

### Completed

#### 1.1 Update DataTable component - DONE
- [x] Add `showDisabled?: boolean` prop to DataTable
- [x] Add `onShowDisabledChange?: (value: boolean) => void` prop
- [x] Add `showDisabledLabel?: string` prop (default: "Show Disabled")
- [x] Render Show Disabled toggle in toolbar, left of column visibility button
- [x] File: `client/src/components/ui/data-table.tsx`

#### 1.2 Update PasswordsPage - DONE
- [x] Remove dedicated "Show Disabled" row/section
- [x] Pass `showDisabled`, `onShowDisabledChange` to DataTable
- [x] Change Add button to icon-only outline variant
- [x] File: `client/src/pages/passwords/PasswordsPage.tsx`

#### 1.3 Update LocationsPage - DONE
- [x] Remove dedicated "Show Disabled" row/section
- [x] Pass `showDisabled`, `onShowDisabledChange` to DataTable
- [x] Change Add button to icon-only outline variant
- [x] File: `client/src/pages/locations/LocationsPage.tsx`

#### 1.4 Update DocumentsPage - DONE
- [x] Remove dedicated "Show Disabled" row/section
- [x] Pass `showDisabled`, `onShowDisabledChange` to DataTable
- [x] Change Add button to icon-only outline variant
- [x] File: `client/src/pages/documents/DocumentsPage.tsx`

#### 1.5 Update ConfigurationsPage - DONE
- [x] Remove dedicated "Show Disabled" row/section
- [x] Pass `showDisabled`, `onShowDisabledChange` to DataTable
- [x] Change Add button to icon-only outline variant
- [x] File: `client/src/pages/configurations/ConfigurationsPage.tsx`

#### 1.6 Update CustomAssetsPage (AssetListView) - DONE
- [x] Add Show Disabled state and toggle (was missing entirely)
- [x] Pass `showDisabled`, `onShowDisabledChange` to DataTable
- [x] Wire up showDisabled to filter assets query (added to useCustomAssets hook)
- [x] Change Add button to icon-only outline variant
- [x] File: `client/src/pages/assets/CustomAssetsPage.tsx`
- [x] File: `client/src/hooks/useCustomAssets.ts` (added showDisabled param)

---

## Task 7: Rich Text Display in Tables - COMPLETE

**Goal:** Strip HTML from rich text fields, show truncated plain text in table cells.

### Completed

#### 7.1 Create text utilities - DONE
- [x] Create `client/src/lib/text-utils.ts`
- [x] Implement `stripHtml(html: string): string`
- [x] Implement `truncateText(text: string, maxLength?: number): string`
- [x] Implement `stripAndTruncate(html: string, maxLength?: number): string`
- [x] Export all functions

#### 7.2 Apply to table cells - DONE
- [x] LocationsPage notes column - uses `stripAndTruncate`
- [x] GlobalLocationsPage notes column - uses `stripAndTruncate`
- [x] CustomAssetsPage textbox fields - uses `stripAndTruncate`
- [x] GlobalCustomAssetsPage textbox fields - uses `stripAndTruncate`

---

## Task 2: Table Height & Internal Scrolling - COMPLETE

**Goal:** Tables use minimum height for content, cap at remaining page height, then scroll internally.

### Design

**Parent container pattern:**
```tsx
<div className="flex flex-col h-full">
  {/* Header/breadcrumbs */}
  <div className="flex-1 min-h-0 flex flex-col">
    <DataTable ... />
  </div>
</div>
```

**DataTable internal pattern:**
```tsx
<div className="flex flex-col min-h-0 max-h-full">
  {/* Toolbar */}
  <div className="overflow-auto flex-1 min-h-0">
    <Table>...</Table>
  </div>
  {/* Pagination - stays visible */}
</div>
```

**Key classes:**
- `flex-1` - grow to fill available space
- `min-h-0` - allow shrinking below content size (enables scroll)
- `overflow-auto` - scroll when content exceeds container

### Completed

#### 2.1 Update DataTable component - DONE
- [x] Wrap table in flex container with `min-h-0 flex-1 overflow-auto`
- [x] Ensure pagination stays outside scroll area
- [x] Ensure toolbar stays outside scroll area
- [x] File: `client/src/components/ui/data-table.tsx`

#### 2.2 Update page layouts - DONE
- [x] PasswordsPage: uses `flex flex-col h-full` and `flex-1 min-h-0`
- [x] LocationsPage: same pattern
- [x] DocumentsPage: same pattern
- [x] ConfigurationsPage: same pattern
- [x] CustomAssetsPage: same pattern

---

## Task 3: Folder Tree Scrolling - COMPLETE

**Goal:** Folder tree uses minimum height, caps at remaining space, scrolls internally. Supports infinite depth.

### Design

```tsx
<Card className="w-64 flex flex-col min-h-0 flex-1">
  <CardHeader>Folders</CardHeader>
  <ScrollArea className="flex-1 min-h-0">
    <FolderTree ... />
  </ScrollArea>
</Card>
```

### Completed

#### 3.1 Update DocumentsPage folder sidebar - DONE
- [x] Card uses `flex flex-col min-h-0` with proper flex layout
- [x] ScrollArea uses dynamic height via flex container
- [x] File: `client/src/pages/documents/DocumentsPage.tsx`

#### 3.2 Verify FolderTree supports infinite depth - DONE
- [x] Verified no artificial depth limits in FolderTree.tsx
- [x] Recursive rendering supports any depth
- [x] File: `client/src/components/documents/FolderTree.tsx`

---

## Task 4: Custom Assets - Drop Name Field & Add Display Field Selection - COMPLETE

**Goal:** Remove hardcoded "name" field from custom assets. Add configurable display field per asset type.

### Design

**Model change:**
- Custom assets no longer have a required `name` field
- CustomAssetType gets `display_field_key: string | null`
- When null, use first text-type field as display

**Import auto-selection priority:**
1. Field named "name" (case-insensitive)
2. Field named "title" (case-insensitive)
3. First text-type field

### Completed

#### 4.1 Backend: Update CustomAssetType model - DONE
- [x] Add `display_field_key: string | null` column to ORM model
- [x] Add field to contract/schema
- [x] Create migration for new column
- [x] Update API to accept/return display_field_key
- [x] Added validation that display_field_key references valid field
- [x] Files:
  - `api/src/models/orm/custom_asset_type.py`
  - `api/src/models/contracts/custom_asset.py`
  - `api/src/routers/custom_asset_types.py`
  - `api/alembic/versions/20260114_160000_custom_assets_display_field.py`

#### 4.2 Backend: Remove name from CustomAsset model - DONE
- [x] Remove `name` field entirely
- [x] Migrate existing name values into `values` JSON field
- [x] Update queries to use JSONB search with display_field_key
- [x] Files:
  - `api/src/models/orm/custom_asset.py`
  - `api/src/models/contracts/custom_asset.py`
  - `api/src/repositories/custom_asset.py`

#### 4.3 Frontend: Update AssetTypeForm - DONE
- [x] Add dropdown to select display field per type
- [x] Options: all text/textbox fields defined on type
- [x] Save selection via API
- [x] File: `client/src/components/assets/AssetTypeForm.tsx`

#### 4.4 Frontend: Update CustomAssetsPage - DONE
- [x] Remove hardcoded "name" column
- [x] Get display_field_key from selected asset type
- [x] Use display field for primary column
- [x] Fallback to first text field if display_field_key is null
- [x] Created shared utility: `client/src/lib/custom-asset-utils.ts`
- [x] File: `client/src/pages/assets/CustomAssetsPage.tsx`

#### 4.5 Frontend: Update CustomAssetForm - DONE
- [x] Remove "name" input field
- [x] File: `client/src/components/assets/CustomAssetForm.tsx`

#### 4.6 Update IT Glue importer - DONE
- [x] Set `display_field_key` on asset types using priority: name > title > first text field
- [x] Remove logic that creates/populates "name" field on custom assets
- [x] Files:
  - `tools/itglue-migrate/src/itglue_migrate/importers.py`
  - `tools/itglue-migrate/src/itglue_migrate/api_client.py`

---

## Task 5: Indexing Toggle in AI Settings - COMPLETE

**Goal:** Add toggle to disable automatic indexing during migrations.

### Design

**UI:**
```
┌─────────────────────────────────────┐
│ Indexing Control                    │
│ ─────────────────────────────────── │
│ [Toggle] Enable automatic indexing  │
│                                     │
│ ⚠ Indexing is disabled. Changes     │
│ will not be searchable until you    │
│ reindex.                            │
└─────────────────────────────────────┘
```

### Completed

#### 5.1 Backend: Add indexing_enabled setting - DONE
- [x] Add `indexing_enabled: boolean` to AI settings model (default: true)
- [x] Update API to accept/return indexing_enabled
- [x] Create migration for new column
- [x] Added `is_indexing_enabled()` repository method
- [x] Files:
  - `api/src/models/orm/ai_settings.py`
  - `api/src/models/contracts/ai_settings.py`
  - `api/src/repositories/ai_settings.py`
  - `api/alembic/versions/20260114_150000_add_indexing_enabled_to_ai_settings.py`

#### 5.2 Backend: Check flag before indexing - DONE
- [x] Update `index_entity_for_search()` to check `indexing_enabled` setting
- [x] If disabled, skip indexing with debug log
- [x] File: `api/src/services/search_indexing.py`

#### 5.3 Frontend: Add Indexing Control card - DONE
- [x] Add new `IndexingControlSection` component in AISettings.tsx
- [x] Add Switch for indexing_enabled
- [x] Show warning message when disabled
- [x] File: `client/src/pages/settings/AISettings.tsx`

#### 5.4 Frontend: Update useAISettings hook - DONE
- [x] Added `useAIConfig()` hook exposing `isIndexingEnabled`
- [x] File: `client/src/hooks/useAISettings.ts`

---

## Task 6: AI Button Disabled State - COMPLETE

**Goal:** Show AI button as disabled with tooltip when AI not configured or indexing disabled.

### Design

- Button visible but greyed out
- Tooltip explains why: "Configure AI in Settings" or "Indexing is disabled"

### Completed

#### 6.1 Create/update AI config hook - DONE
- [x] Created `useAIConfig()` hook exposing:
  - `isConfigured: boolean` (API key configured)
  - `isIndexingEnabled: boolean`
  - `isLoading: boolean`
- [x] File: `client/src/hooks/useAISettings.ts`

#### 6.2 Update CommandPalette - DONE
- [x] Import AI config hook
- [x] Conditionally disable "Ask AI" button
- [x] Add Tooltip wrapper with appropriate message
- [x] Show "Loading..." during initial load
- [x] Show "Configure AI in Settings" when not configured
- [x] Show "Indexing is disabled" when indexing disabled
- [x] Keyboard shortcut (Shift+Enter) disabled when AI unavailable
- [x] File: `client/src/components/search/CommandPalette.tsx`

---

## Skipped Items

- **Grey card input contrast**: Revisit later if needed. Inputs on grey card backgrounds may need explicit `bg-background` class.

---

## Implementation Order

**Completed sequence:**

1. ~~**Task 7** (Rich text) - No dependencies, quick win~~ DONE
2. ~~**Task 1** (Toolbar consolidation) - Foundation for other pages~~ DONE
3. ~~**Task 2** (Table scrolling) - Builds on DataTable changes~~ DONE
4. ~~**Task 3** (Folder tree) - Similar pattern, quick~~ DONE
5. ~~**Task 6** (AI button) - Small, standalone~~ DONE
6. ~~**Task 5** (Indexing toggle) - Backend + frontend~~ DONE
7. ~~**Task 4** (Custom assets display field) - Largest, do last~~ DONE

---

## Testing Checklist

After each task:
- [x] `npm run tsc` passes
- [x] `npm run lint` passes
- [x] `pyright` passes (0 errors)
- [x] `pytest` unit tests pass
- [ ] Manual testing in browser
- [ ] No regressions in related functionality
