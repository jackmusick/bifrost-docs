"use client";

import * as React from "react";
import {
  type ColumnDef,
  type SortingState,
  type VisibilityState,
  type ColumnPinningState,
  type ColumnOrderState,
  type RowSelectionState,
  type Table as TanStackTable,
  type Column,
  type Row,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  draggable,
  dropTargetForElements,
} from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { reorder } from "@atlaskit/pragmatic-drag-and-drop/reorder";
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
  RotateCw,
  Search,
  X,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
} from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

// =============================================================================
// Types
// =============================================================================

export interface PaginationState {
  limit: number;
  offset: number;
}

export interface ColumnFilter {
  columnId: string;
  value: string;
}

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
  onRefresh?: () => void | Promise<void>;
  /** Refresh loading state */
  isRefreshing?: boolean;
  /** Enable row selection */
  enableRowSelection?: boolean;
  /** Controlled row selection state */
  rowSelection?: RowSelectionState;
  /** Callback for row selection changes */
  onRowSelectionChange?: (selection: RowSelectionState) => void;
  /** Custom function to get row ID (defaults to row.id) */
  getRowId?: (row: TData) => string;
  /** Number of selected items (for bulk actions) */
  selectedCount?: number;
  /** Bulk action configuration */
  bulkActions?: {
    onActivate?: () => void;
    onDeactivate?: () => void;
    isLoading?: boolean;
  };
}

// =============================================================================
// Selection Column Helper
// =============================================================================

/**
 * Creates a selection column definition with checkboxes for row selection.
 * Use this as the first column in your columns array when enableRowSelection is true.
 */
export function createSelectionColumn<TData>(): ColumnDef<TData> {
  return {
    id: "select",
    header: ({ table }) => (
      <div onClick={(e) => e.stopPropagation()}>
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      </div>
    ),
    cell: ({ row }) => (
      <div onClick={(e) => e.stopPropagation()}>
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      </div>
    ),
    enableSorting: false,
    enableHiding: false,
    size: 40,
    minSize: 40,
    maxSize: 40,
  };
}

// =============================================================================
// Sortable Header Helper
// =============================================================================

interface SortableHeaderProps {
  column: {
    getIsSorted: () => false | "asc" | "desc";
    toggleSorting: (desc?: boolean) => void;
    getCanSort: () => boolean;
  };
  children: React.ReactNode;
  className?: string;
}

export const SortableHeader = React.memo(function SortableHeader({
  column,
  children,
  className,
}: SortableHeaderProps) {
  const sorted = column.getIsSorted();
  const canSort = column.getCanSort();

  if (!canSort) {
    return <span className={className}>{children}</span>;
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn("-ml-3 h-8 hover:bg-transparent", className)}
      onClick={() => column.toggleSorting(sorted === "asc")}
    >
      {children}
      {sorted === "asc" ? (
        <ArrowUp className="ml-2 h-4 w-4" />
      ) : sorted === "desc" ? (
        <ArrowDown className="ml-2 h-4 w-4" />
      ) : (
        <ArrowUpDown className="ml-2 h-4 w-4 opacity-50" />
      )}
    </Button>
  );
});

// =============================================================================
// Pinned Column Indicator
// =============================================================================

interface PinnedIndicatorProps {
  isPinned: boolean;
  className?: string;
}

export function PinnedIndicator({ isPinned, className }: PinnedIndicatorProps) {
  if (!isPinned) return null;
  return (
    <Pin
      className={cn("h-3 w-3 text-muted-foreground/50 inline-block", className)}
    />
  );
}

// =============================================================================
// Column Visibility & Order Toggle
// =============================================================================

interface DraggableColumnItemProps {
  columnId: string;
  columnLabel: string;
  index: number;
  isVisible: boolean;
  onVisibilityChange: (visible: boolean) => void;
}

const DraggableColumnItem = React.memo(function DraggableColumnItem({
  columnId,
  columnLabel,
  index,
  isVisible,
  onVisibilityChange,
}: DraggableColumnItemProps) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = React.useState(false);
  const [isDraggedOver, setIsDraggedOver] = React.useState(false);
  const [dropPosition, setDropPosition] = React.useState<"none" | "before" | "after">("none");

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;

    return combine(
      draggable({
        element: el,
        getInitialData: () => ({ type: "column", index, columnId }),
        onDragStart: () => setDragging(true),
        onDrop: () => setDragging(false),
      }),
      dropTargetForElements({
        element: el,
        getData: ({ input, element }) => {
          const rect = element.getBoundingClientRect();
          const midpoint = rect.top + rect.height / 2;
          const position = input.clientY < midpoint ? "before" : "after";
          return { index, position };
        },
        canDrop: ({ source }) => source.data["type"] === "column",
        onDragEnter: () => setIsDraggedOver(true),
        onDrag: ({ self }) => {
          const position = self.data["position"] as "before" | "after";
          setDropPosition(position);
        },
        onDragLeave: () => {
          setIsDraggedOver(false);
          setDropPosition("none");
        },
        onDrop: () => {
          setIsDraggedOver(false);
          setDropPosition("none");
        },
      })
    );
  }, [index, columnId]);

  return (
    <div className="relative">
      {dropPosition === "before" && (
        <div className="absolute -top-0.5 left-0 right-0 h-0.5 bg-primary z-10" />
      )}
      <div
        ref={ref}
        className={cn(
          "flex items-center gap-2 px-2 py-1.5 cursor-grab active:cursor-grabbing rounded-sm transition-all",
          dragging && "opacity-50 scale-95",
          isDraggedOver && "bg-accent",
          !dragging && !isDraggedOver && "hover:bg-accent"
        )}
      >
        <GripVertical className="h-4 w-4 text-muted-foreground shrink-0" />
        <label className="flex items-center gap-2 flex-1 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={isVisible}
            onChange={(e) => onVisibilityChange(e.target.checked)}
            className="h-4 w-4 rounded border-input"
          />
          <span className="capitalize text-sm">{columnLabel}</span>
        </label>
      </div>
      {dropPosition === "after" && (
        <div className="absolute -bottom-0.5 left-0 right-0 h-0.5 bg-primary z-10" />
      )}
    </div>
  );
});

interface ColumnVisibilityToggleProps<TData> {
  table: TanStackTable<TData>;
  onColumnOrderChange?: (order: ColumnOrderState) => void;
}

const ColumnVisibilityToggle = React.memo(function ColumnVisibilityToggle<TData>({
  table,
  onColumnOrderChange,
}: ColumnVisibilityToggleProps<TData>) {
  const dropZoneRef = React.useRef<HTMLDivElement>(null);

  // Get columns that can be toggled, sorted by current order
  const allColumns = table.getAllLeafColumns();
  const currentOrder = table.getState().columnOrder;

  // Get sortable columns
  const sortableColumns = allColumns.filter(
    (column) => typeof column.accessorFn !== "undefined" && column.getCanHide()
  );

  // Sort by current order if available
  const orderedColumns = React.useMemo(() => {
    if (!currentOrder || currentOrder.length === 0) {
      return sortableColumns;
    }
    return [...sortableColumns].sort((a, b) => {
      const aIndex = currentOrder.indexOf(a.id);
      const bIndex = currentOrder.indexOf(b.id);
      if (aIndex === -1 && bIndex === -1) return 0;
      if (aIndex === -1) return 1;
      if (bIndex === -1) return -1;
      return aIndex - bIndex;
    });
  }, [sortableColumns, currentOrder]);

  // Set up drop zone for reordering
  React.useEffect(() => {
    const el = dropZoneRef.current;
    if (!el) return;

    return dropTargetForElements({
      element: el,
      getData: () => ({ type: "dropzone" }),
      canDrop: ({ source }) => source.data["type"] === "column",
      onDrop: ({ source, location }) => {
        const startIndex = source.data["index"] as number;
        const target = location.current.dropTargets.find(
          (t) => t.data["index"] !== undefined
        );

        if (target?.data["index"] !== undefined) {
          const targetIndex = target.data["index"] as number;
          const position = target.data["position"] as "before" | "after";

          // Calculate finish index
          let finishIndex = position === "before" ? targetIndex : targetIndex + 1;
          if (startIndex < finishIndex) {
            finishIndex -= 1;
          }

          if (startIndex !== finishIndex) {
            // Get current column IDs in order
            const columnIds = orderedColumns.map((c) => c.id);
            const newOrder = reorder({
              list: columnIds,
              startIndex,
              finishIndex,
            });

            table.setColumnOrder(newOrder);
            onColumnOrderChange?.(newOrder);
          }
        }
      },
    });
  }, [orderedColumns, table, onColumnOrderChange]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="h-8">
          <Columns3 className="mr-2 h-4 w-4" />
          Columns
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[220px]">
        <DropdownMenuLabel>Toggle & reorder columns</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div ref={dropZoneRef} className="max-h-[300px] overflow-y-auto py-1">
          {orderedColumns.map((column, index) => (
            <DraggableColumnItem
              key={column.id}
              columnId={column.id}
              columnLabel={column.id.replace(/_/g, " ")}
              index={index}
              isVisible={column.getIsVisible()}
              onVisibilityChange={(visible) => column.toggleVisibility(visible)}
            />
          ))}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}) as <TData>(props: ColumnVisibilityToggleProps<TData>) => React.ReactElement;

// =============================================================================
// Column Filters Dropdown
// =============================================================================

interface ColumnFiltersDropdownProps {
  filterableColumns: Array<{
    columnId: string;
    title: string;
    options: Array<{ label: string; value: string }>;
  }>;
  columnFilters: ColumnFilter[];
  onColumnFiltersChange: (filters: ColumnFilter[]) => void;
}

const ColumnFiltersDropdown = React.memo(function ColumnFiltersDropdown({
  filterableColumns,
  columnFilters,
  onColumnFiltersChange,
}: ColumnFiltersDropdownProps) {
  const activeFilterCount = columnFilters.length;

  const getFilterValue = (columnId: string) => {
    return columnFilters.find((f) => f.columnId === columnId)?.value;
  };

  const handleFilterChange = (columnId: string, value: string | undefined) => {
    const newFilters = columnFilters.filter((f) => f.columnId !== columnId);
    if (value) {
      newFilters.push({ columnId, value });
    }
    onColumnFiltersChange(newFilters);
  };

  const getSelectedLabel = (columnId: string) => {
    const value = getFilterValue(columnId);
    if (!value) return null;
    const column = filterableColumns.find((c) => c.columnId === columnId);
    return column?.options.find((o) => o.value === value)?.label;
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-8">
          <Filter className="mr-2 h-4 w-4" />
          Filters
          {activeFilterCount > 0 && (
            <Badge variant="secondary" className="ml-2 h-5 px-1.5">
              {activeFilterCount}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[280px] p-0" align="end">
        <div className="p-3 border-b">
          <h4 className="font-medium text-sm">Filter by</h4>
        </div>
        <div className="p-2 space-y-3">
          {filterableColumns.map((column) => {
            const selectedValue = getFilterValue(column.columnId);
            const selectedLabel = getSelectedLabel(column.columnId);
            return (
              <div key={column.columnId} className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  {column.title}
                </label>
                <Select
                  value={selectedValue || ""}
                  onValueChange={(value) =>
                    handleFilterChange(column.columnId, value || undefined)
                  }
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder={`All ${column.title.toLowerCase()}`}>
                      {selectedLabel || `All ${column.title.toLowerCase()}`}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All {column.title.toLowerCase()}</SelectItem>
                    {column.options.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            );
          })}
        </div>
        {activeFilterCount > 0 && (
          <div className="border-t p-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-center"
              onClick={() => onColumnFiltersChange([])}
            >
              <X className="mr-2 h-4 w-4" />
              Clear all filters
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
});

// =============================================================================
// Pagination Controls
// =============================================================================

interface PaginationControlsProps {
  total: number;
  pagination: PaginationState;
  onPaginationChange: (pagination: PaginationState) => void;
  pageSizeOptions: number[];
}

const PaginationControls = React.memo(function PaginationControls({
  total,
  pagination,
  onPaginationChange,
  pageSizeOptions,
}: PaginationControlsProps) {
  const { limit, offset } = pagination;
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const startItem = offset + 1;
  const endItem = Math.min(offset + limit, total);

  const canGoPrevious = offset > 0;
  const canGoNext = offset + limit < total;

  const goToPage = (page: number) => {
    const newOffset = (page - 1) * limit;
    onPaginationChange({ limit, offset: newOffset });
  };

  const setPageSize = (newLimit: number) => {
    onPaginationChange({ limit: newLimit, offset: 0 });
  };

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t bg-muted/30">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>
          Showing {startItem}-{endItem} of {total}
        </span>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Rows per page</span>
          <Select
            value={String(limit)}
            onValueChange={(value) => setPageSize(Number(value))}
          >
            <SelectTrigger className="h-8 w-[70px]">
              <SelectValue placeholder={limit} />
            </SelectTrigger>
            <SelectContent side="top">
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-sm text-muted-foreground">
            Page {currentPage} of {totalPages}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => goToPage(1)}
            disabled={!canGoPrevious}
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => goToPage(currentPage - 1)}
            disabled={!canGoPrevious}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => goToPage(currentPage + 1)}
            disabled={!canGoNext}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => goToPage(totalPages)}
            disabled={!canGoNext}
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
});

// =============================================================================
// Memoized Search Input Component
// =============================================================================

interface SearchInputProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder: string;
}

const MemoizedSearchInput = React.memo(function MemoizedSearchInput({
  searchValue,
  onSearchChange,
  searchPlaceholder,
}: SearchInputProps) {
  return (
    <div className="relative flex-1 max-w-sm">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder={searchPlaceholder}
        value={searchValue}
        onChange={(e) => onSearchChange(e.target.value)}
        className="pl-9"
      />
    </div>
  );
});

// =============================================================================
// Memoized Toolbar Component
// =============================================================================

interface ToolbarProps<TData> {
  hasSearch: boolean;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder: string;
  hasFilters: boolean;
  filterableColumns?: Array<{
    columnId: string;
    title: string;
    options: Array<{ label: string; value: string }>;
  }>;
  columnFilters?: ColumnFilter[];
  onColumnFiltersChange?: (filters: ColumnFilter[]) => void;
  hasShowDisabled: boolean;
  showDisabled?: boolean;
  onShowDisabledChange?: (value: boolean) => void;
  showDisabledLabel: string;
  showColumnToggle: boolean;
  table: TanStackTable<TData>;
  onColumnOrderChange?: (order: ColumnOrderState) => void;
  onRefresh?: () => void | Promise<void>;
  isRefreshing: boolean;
  selectedCount?: number;
  bulkActions?: {
    onActivate?: () => void;
    onDeactivate?: () => void;
    isLoading?: boolean;
  };
}

const DataTableToolbar = React.memo(function DataTableToolbar<TData>({
  hasSearch,
  searchValue,
  onSearchChange,
  searchPlaceholder,
  hasFilters,
  filterableColumns,
  columnFilters,
  onColumnFiltersChange,
  hasShowDisabled,
  showDisabled,
  onShowDisabledChange,
  showDisabledLabel,
  showColumnToggle,
  table,
  onColumnOrderChange,
  onRefresh,
  isRefreshing,
  selectedCount,
  bulkActions,
}: ToolbarProps<TData>) {
  return (
    <div className="flex items-center justify-between gap-4 shrink-0">
      <div className="flex items-center gap-4 flex-1">
        {hasSearch && (
          <MemoizedSearchInput
            searchValue={searchValue!}
            onSearchChange={onSearchChange!}
            searchPlaceholder={searchPlaceholder}
          />
        )}
        {/* Bulk Actions */}
        {selectedCount !== undefined && selectedCount > 0 && bulkActions && (
          <>
            <div className="h-6 w-px bg-border" />
            {bulkActions.onActivate && (
              <Button
                variant="outline"
                size="sm"
                onClick={bulkActions.onActivate}
                disabled={bulkActions.isLoading}
              >
                Activate ({selectedCount})
              </Button>
            )}
            {bulkActions.onDeactivate && (
              <Button
                variant="outline"
                size="sm"
                onClick={bulkActions.onDeactivate}
                disabled={bulkActions.isLoading}
              >
                Deactivate ({selectedCount})
              </Button>
            )}
          </>
        )}
      </div>
      <div className="flex items-center gap-2">
        {hasFilters && filterableColumns && onColumnFiltersChange && (
          <ColumnFiltersDropdown
            filterableColumns={filterableColumns}
            columnFilters={columnFilters || []}
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
            onColumnOrderChange={onColumnOrderChange}
          />
        )}
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
                  aria-label={isRefreshing ? "Refreshing data" : "Refresh data"}
                >
                  <RotateCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Refresh data</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Return true to SKIP re-render (props are equal)
  // Return false to RE-RENDER (props changed)
  //
  // ONLY check primitive data values, NOT arrays/objects/callbacks
  const shouldSkipRender = (
    prevProps.searchValue === nextProps.searchValue &&
    prevProps.showDisabled === nextProps.showDisabled &&
    prevProps.isRefreshing === nextProps.isRefreshing &&
    prevProps.searchPlaceholder === nextProps.searchPlaceholder &&
    prevProps.showDisabledLabel === nextProps.showDisabledLabel &&
    prevProps.selectedCount === nextProps.selectedCount &&
    // These boolean flags control visibility
    prevProps.hasSearch === nextProps.hasSearch &&
    prevProps.hasFilters === nextProps.hasFilters &&
    prevProps.hasShowDisabled === nextProps.hasShowDisabled &&
    prevProps.showColumnToggle === nextProps.showColumnToggle
    // Intentionally IGNORE all arrays, objects, and callbacks:
    // - columnFilters (array reference changes but ColumnFiltersDropdown is memoized)
    // - filterableColumns (array reference changes)
    // - onSearchChange, onRefresh, onColumnOrderChange (callbacks)
    // - bulkActions (object reference changes)
    // - table (object changes every render)
  );

  return shouldSkipRender;
}) as <TData>(props: ToolbarProps<TData>) => React.ReactElement;

// =============================================================================
// Memoized Table Row Component
// =============================================================================

interface MemoizedTableRowProps<TData> {
  row: Row<TData>;
  isSelected: boolean;
  onRowClick?: (row: TData) => void;
  getPinnedCellStyles: (columnId: string, isPinned: false | "left" | "right") => React.CSSProperties;
}

const MemoizedTableRow = React.memo(function MemoizedTableRow<TData>({
  row,
  isSelected,
  onRowClick,
  getPinnedCellStyles,
}: MemoizedTableRowProps<TData>) {
  const handleClick = React.useCallback(() => {
    if (onRowClick) {
      onRowClick(row.original);
    }
  }, [onRowClick, row.original]);

  return (
    <tr
      key={row.id}
      data-state={isSelected && "selected"}
      className={cn(
        "border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted",
        onRowClick && "cursor-pointer"
      )}
      onClick={handleClick}
    >
      {row.getVisibleCells().map((cell) => {
        const isPinned = cell.column.getIsPinned();
        return (
          <td
            key={cell.id}
            style={{
              ...getPinnedCellStyles(cell.column.id, isPinned),
              width: cell.column.getSize(),
              minWidth: cell.column.columnDef.minSize,
              maxWidth: cell.column.columnDef.maxSize,
            }}
            className={cn(
              "p-4 align-middle [&:has([role=checkbox])]:pr-0 overflow-hidden",
              isPinned &&
                "after:absolute after:right-0 after:top-0 after:bottom-0 after:w-px after:bg-border"
            )}
          >
            {flexRender(
              cell.column.columnDef.cell,
              cell.getContext()
            )}
          </td>
        );
      })}
    </tr>
  );
}, (prevProps, nextProps) => {
  // Re-render if row ID changes or selection state changes
  return (
    prevProps.row.id === nextProps.row.id &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.onRowClick === nextProps.onRowClick &&
    prevProps.getPinnedCellStyles === nextProps.getPinnedCellStyles
  );
}) as <TData>(props: MemoizedTableRowProps<TData>) => React.ReactElement;

// =============================================================================
// DataTable Component
// =============================================================================

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
  onRefresh,
  isRefreshing = false,
  enableRowSelection = false,
  rowSelection: controlledRowSelection,
  onRowSelectionChange,
  getRowId,
  selectedCount,
  bulkActions,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [internalColumnVisibility, setInternalColumnVisibility] =
    React.useState<VisibilityState>({});
  const [internalColumnOrder, setInternalColumnOrder] =
    React.useState<ColumnOrderState>([]);
  const [columnPinning, setColumnPinning] = React.useState<ColumnPinningState>({
    left: pinnedColumns,
    right: [],
  });
  const [internalRowSelection, setInternalRowSelection] =
    React.useState<RowSelectionState>({});

  // Use controlled or internal visibility state
  const columnVisibility =
    controlledColumnVisibility ?? internalColumnVisibility;

  // Use controlled or internal column order
  const columnOrder = controlledColumnOrder ?? internalColumnOrder;

  // Use controlled or internal row selection
  const rowSelection = controlledRowSelection ?? internalRowSelection;

  // Load column visibility from localStorage on mount (skip if using API persistence)
  React.useEffect(() => {
    if (
      columnVisibilityStorageKey &&
      !controlledColumnVisibility &&
      !useApiPersistence
    ) {
      try {
        const stored = localStorage.getItem(columnVisibilityStorageKey);
        if (stored) {
          const parsed = JSON.parse(stored) as VisibilityState;
          setInternalColumnVisibility(parsed);
        }
      } catch {
        // Ignore parse errors
      }
    }
  }, [columnVisibilityStorageKey, controlledColumnVisibility, useApiPersistence]);

  // Load column order from localStorage on mount (skip if using API persistence)
  React.useEffect(() => {
    if (columnOrderStorageKey && !controlledColumnOrder && !useApiPersistence) {
      try {
        const stored = localStorage.getItem(columnOrderStorageKey);
        if (stored) {
          const parsed = JSON.parse(stored) as ColumnOrderState;
          setInternalColumnOrder(parsed);
        }
      } catch {
        // Ignore parse errors
      }
    }
  }, [columnOrderStorageKey, controlledColumnOrder, useApiPersistence]);

  // Handle visibility change
  const handleColumnVisibilityChange = React.useCallback(
    (
      updaterOrValue:
        | VisibilityState
        | ((prev: VisibilityState) => VisibilityState)
    ) => {
      const newVisibility =
        typeof updaterOrValue === "function"
          ? updaterOrValue(columnVisibility)
          : updaterOrValue;

      if (onColumnVisibilityChange) {
        onColumnVisibilityChange(newVisibility);
      } else {
        setInternalColumnVisibility(newVisibility);
      }

      // Only save to localStorage if not using API persistence
      if (columnVisibilityStorageKey && !useApiPersistence) {
        try {
          localStorage.setItem(
            columnVisibilityStorageKey,
            JSON.stringify(newVisibility)
          );
        } catch {
          // Ignore storage errors
        }
      }
    },
    [
      columnVisibility,
      onColumnVisibilityChange,
      columnVisibilityStorageKey,
      useApiPersistence,
    ]
  );

  // Handle column order change
  const handleColumnOrderChange = React.useCallback(
    (
      updaterOrValue:
        | ColumnOrderState
        | ((prev: ColumnOrderState) => ColumnOrderState)
    ) => {
      const newOrder =
        typeof updaterOrValue === "function"
          ? updaterOrValue(columnOrder)
          : updaterOrValue;

      if (onColumnOrderChange) {
        onColumnOrderChange(newOrder);
      } else {
        setInternalColumnOrder(newOrder);
      }

      // Only save to localStorage if not using API persistence
      if (columnOrderStorageKey && !useApiPersistence) {
        try {
          localStorage.setItem(columnOrderStorageKey, JSON.stringify(newOrder));
        } catch {
          // Ignore storage errors
        }
      }
    },
    [columnOrder, onColumnOrderChange, columnOrderStorageKey, useApiPersistence]
  );

  // Handle row selection change
  const handleRowSelectionChange = React.useCallback(
    (
      updaterOrValue:
        | RowSelectionState
        | ((prev: RowSelectionState) => RowSelectionState)
    ) => {
      const newSelection =
        typeof updaterOrValue === "function"
          ? updaterOrValue(rowSelection)
          : updaterOrValue;

      if (onRowSelectionChange) {
        onRowSelectionChange(newSelection);
      } else {
        setInternalRowSelection(newSelection);
      }
    },
    [rowSelection, onRowSelectionChange]
  );

  // Update pinning when pinnedColumns prop changes
  React.useEffect(() => {
    setColumnPinning({
      left: pinnedColumns,
      right: [],
    });
  }, [pinnedColumns]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    onColumnVisibilityChange: handleColumnVisibilityChange,
    onColumnOrderChange: handleColumnOrderChange,
    onColumnPinningChange: setColumnPinning,
    onRowSelectionChange: handleRowSelectionChange,
    enableRowSelection: enableRowSelection,
    getRowId: getRowId ? (row) => getRowId(row) : undefined,
    state: {
      sorting,
      columnVisibility,
      columnOrder,
      columnPinning,
      rowSelection,
    },
  });

  // Calculate sticky positions for pinned columns (memoized)
  const getLeftOffset = React.useCallback((columnId: string): number => {
    const pinnedLeft = table.getLeftLeafColumns();
    const index = pinnedLeft.findIndex((col) => col.id === columnId);
    if (index <= 0) return 0;

    let offset = 0;
    for (let i = 0; i < index; i++) {
      offset += pinnedLeft[i].getSize() || 150;
    }
    return offset;
  }, [table]);

  const getPinnedCellStyles = React.useCallback((
    columnId: string,
    isPinned: false | "left" | "right"
  ): React.CSSProperties => {
    if (!isPinned) return {};

    if (isPinned === "left") {
      return {
        position: "sticky",
        left: getLeftOffset(columnId),
        zIndex: 1,
        backgroundColor: "hsl(var(--card))",
      };
    }

    return {};
  }, [getLeftOffset]);

  const hasPagination = !!(
    total !== undefined && pagination !== undefined && onPaginationChange
  );
  const hasSearch = !!(searchValue !== undefined && onSearchChange !== undefined);
  const hasFilters = !!(
    filterableColumns && filterableColumns.length > 0 && onColumnFiltersChange
  );
  const hasShowDisabled = !!(
    showDisabled !== undefined && onShowDisabledChange !== undefined
  );

  // Show empty state only when there's no search active
  const isSearching = hasSearch && !!(searchValue && searchValue.trim().length > 0);
  const showToolbar = !!(
    hasSearch ||
    hasFilters ||
    showColumnToggle ||
    hasShowDisabled ||
    onRefresh
  );
  const showStandaloneEmptyContent =
    !isLoading && data.length === 0 && !!emptyContent && !isSearching;

  return (
    <div className={cn("flex flex-col min-h-0 gap-4", className)}>
      {/* Toolbar - search and filters outside the table (fixed, does not scroll) */}
      {showToolbar && (
        <DataTableToolbar
          hasSearch={hasSearch}
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          searchPlaceholder={searchPlaceholder}
          hasFilters={hasFilters}
          filterableColumns={filterableColumns}
          columnFilters={columnFilters}
          onColumnFiltersChange={onColumnFiltersChange}
          hasShowDisabled={hasShowDisabled}
          showDisabled={showDisabled}
          onShowDisabledChange={onShowDisabledChange}
          showDisabledLabel={showDisabledLabel}
          showColumnToggle={showColumnToggle}
          table={table}
          onColumnOrderChange={handleColumnOrderChange}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
          selectedCount={selectedCount}
          bulkActions={bulkActions}
        />
      )}

      {showStandaloneEmptyContent ? (
        <>{emptyContent}</>
      ) : (
        /* Table container - grows to fill available space, scrolls internally */
        <div className="rounded-lg border bg-card overflow-hidden flex flex-col min-h-0 flex-1">
          {/* Scrollable table area */}
          <div className="overflow-auto flex-1 min-h-0">
            <table className="w-full caption-bottom text-sm">
              <thead className="sticky top-0 bg-muted/50 backdrop-blur-sm z-10">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id} className="border-b">
                    {headerGroup.headers.map((header) => {
                      const isPinned = header.column.getIsPinned();
                      return (
                        <th
                          key={header.id}
                          style={{
                            ...getPinnedCellStyles(header.column.id, isPinned),
                            width: header.getSize(),
                            minWidth: header.column.columnDef.minSize,
                            maxWidth: header.column.columnDef.maxSize,
                          }}
                          className={cn(
                            "h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0",
                            isPinned &&
                              "after:absolute after:right-0 after:top-0 after:bottom-0 after:w-px after:bg-border"
                          )}
                        >
                          {header.isPlaceholder
                            ? null
                            : flexRender(
                                header.column.columnDef.header,
                                header.getContext()
                              )}
                        </th>
                      );
                    })}
                  </tr>
                ))}
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                {isLoading ? (
                  [...Array(5)].map((_, rowIndex) => (
                    <tr key={rowIndex} className="border-b last:border-0">
                      {columns.map((_, cellIndex) => (
                        <td key={cellIndex} className="p-4">
                          <div className="h-4 w-full bg-muted animate-pulse rounded" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : table.getRowModel().rows.length ? (
                  table.getRowModel().rows.map((row) => (
                    <MemoizedTableRow
                      key={row.id}
                      row={row}
                      isSelected={row.getIsSelected()}
                      onRowClick={onRowClick}
                      getPinnedCellStyles={getPinnedCellStyles}
                    />
                  ))
                ) : (
                  <tr>
                    <td
                      colSpan={columns.length}
                      className="h-24 text-center text-muted-foreground"
                    >
                      {isSearching ? "No results found" : "No results."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {/* Pagination - stays visible outside scroll area */}
          {!isLoading && hasPagination && total > 0 && (
            <PaginationControls
              total={total}
              pagination={pagination}
              onPaginationChange={onPaginationChange}
              pageSizeOptions={pageSizeOptions}
            />
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Column Definition Helpers
// =============================================================================

/**
 * Creates a sortable column definition with a header that shows sort indicators.
 */
export function createSortableColumn<TData, TValue>(
  accessorKey: keyof TData & string,
  header: string,
  options?: Partial<ColumnDef<TData, TValue>>
): ColumnDef<TData, TValue> {
  return {
    accessorKey,
    header: ({ column }) => (
      <SortableHeader column={column}>{header}</SortableHeader>
    ),
    ...options,
  } as ColumnDef<TData, TValue>;
}

/**
 * Creates a non-sortable column definition.
 */
export function createColumn<TData, TValue>(
  accessorKey: keyof TData & string,
  header: string,
  options?: Partial<ColumnDef<TData, TValue>>
): ColumnDef<TData, TValue> {
  return {
    accessorKey,
    header,
    enableSorting: false,
    ...options,
  } as ColumnDef<TData, TValue>;
}

// Re-export types for convenience
export type { ColumnDef, SortingState, VisibilityState, ColumnOrderState, RowSelectionState, Column };
