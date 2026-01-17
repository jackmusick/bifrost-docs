import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MapPin, Plus } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DataTable,
  SortableHeader,
  type PaginationState,
  createSelectionColumn,
  type RowSelectionState,
} from "@/components/ui/data-table";
import {
  useLocations,
  useCreateLocation,
  useBatchToggleLocations,
  type Location,
  type LocationCreate,
  type LocationUpdate,
} from "@/hooks/useLocations";
import { useDebounce } from "@/hooks/useDebounce";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { usePermissions } from "@/hooks/usePermissions";
import { LocationForm } from "@/components/locations/LocationForm";
import { stripAndTruncate } from "@/lib/text-utils";
import { toast } from "sonner";

// Column definitions for the locations table
const columns: ColumnDef<Location>[] = [
  createSelectionColumn<Location>(),
  {
    accessorKey: "name",
    header: ({ column }) => (
      <SortableHeader column={column}>Name</SortableHeader>
    ),
    cell: ({ row }) => {
      const isEnabled = row.original.is_enabled;
      return (
        <div className={`flex items-center gap-2 ${!isEnabled ? "opacity-60 line-through" : ""}`}>
          <MapPin className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.getValue("name")}</span>
        </div>
      );
    },
    size: 200,
  },
  {
    accessorKey: "notes",
    header: ({ column }) => (
      <SortableHeader column={column}>Notes</SortableHeader>
    ),
    cell: ({ row }) => {
      const notes = row.getValue("notes") as string | null;
      return (
        <span className="text-muted-foreground max-w-md truncate block">
          {notes ? stripAndTruncate(notes, 100) : "-"}
        </span>
      );
    },
  },
  {
    accessorKey: "updated_at",
    header: ({ column }) => (
      <div className="text-right">
        <SortableHeader column={column}>Updated</SortableHeader>
      </div>
    ),
    cell: ({ row }) => (
      <div className="text-right text-muted-foreground">
        {new Date(row.getValue("updated_at")).toLocaleDateString()}
      </div>
    ),
  },
];

// Columns to pin to the left by default
const pinnedColumns = ["select", "name"];

// All column IDs for preferences
const allColumnIds = ["name", "notes", "updated_at"];

export function LocationsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const navigate = useNavigate();
  const [formOpen, setFormOpen] = useState(false);
  const [showDisabled, setShowDisabled] = useState(false);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [pagination, setPagination] = useState<PaginationState>({
    limit: 25,
    offset: 0,
  });
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebounce(searchInput, 300);
  const { canEdit } = usePermissions();

  const batchToggle = useBatchToggleLocations(orgId!);

  // Column preferences with server-side persistence
  const {
    columnVisibility,
    columnOrder,
    onColumnVisibilityChange,
    onColumnOrderChange,
    isLoading: prefsLoading,
  } = useColumnPreferences("locations", allColumnIds);

  const { data, isLoading, refetch, isRefetching } = useLocations(orgId!, {
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });

  // Reset pagination when search changes
  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    setPagination((prev) => ({ ...prev, offset: 0 }));
  };
  const createLocation = useCreateLocation(orgId!);

  const handleCreate = async (formData: LocationCreate | LocationUpdate) => {
    try {
      // In create mode, we know the data will be LocationCreate
      const result = await createLocation.mutateAsync(formData as LocationCreate);
      setFormOpen(false);
      toast.success("Location created successfully");
      navigate(`/org/${orgId}/locations/${result.id}`);
    } catch {
      toast.error("Failed to create location");
    }
  };

  const handleRowClick = (location: Location) => {
    navigate(`/org/${orgId}/locations/${location.id}`);
  };

  const handleBulkActivate = async () => {
    const ids = Object.keys(rowSelection);
    await batchToggle.mutateAsync({ ids, isEnabled: true });
    setRowSelection({});
    toast.success(`Activated ${ids.length} item${ids.length > 1 ? 's' : ''}`);
  };

  const handleBulkDeactivate = async () => {
    const ids = Object.keys(rowSelection);
    await batchToggle.mutateAsync({ ids, isEnabled: false });
    setRowSelection({});
    toast.success(`Deactivated ${ids.length} item${ids.length > 1 ? 's' : ''}`);
  };

  const emptyContent = (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-20">
        <MapPin className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">No locations yet</h3>
        <p className="text-sm text-muted-foreground text-center mb-4">
          {canEdit
            ? "Get started by adding your first location"
            : "No locations have been added yet"}
        </p>
        {canEdit && (
          <Button onClick={() => setFormOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Location
          </Button>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Locations</h1>
          <p className="text-muted-foreground mt-1">
            Track physical and virtual locations
          </p>
        </div>
        {canEdit && (
          <Button variant="outline" size="icon" onClick={() => setFormOpen(true)}>
            <Plus className="h-5 w-5" />
          </Button>
        )}
      </div>

      <DataTable
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
        searchPlaceholder="Search locations..."
        showDisabled={showDisabled}
        onShowDisabledChange={setShowDisabled}
        onRefresh={() => { refetch(); }}
        isRefreshing={isRefetching}
        enableRowSelection
        rowSelection={rowSelection}
        onRowSelectionChange={setRowSelection}
        getRowId={(row) => row.id}
        selectedCount={Object.keys(rowSelection).length}
        bulkActions={{
          onActivate: handleBulkActivate,
          onDeactivate: handleBulkDeactivate,
          isLoading: batchToggle.isPending,
        }}
      />

      <LocationForm
        open={formOpen}
        onOpenChange={setFormOpen}
        onSubmit={handleCreate}
        isSubmitting={createLocation.isPending}
        mode="create"
        orgId={orgId!}
      />
    </div>
  );
}
