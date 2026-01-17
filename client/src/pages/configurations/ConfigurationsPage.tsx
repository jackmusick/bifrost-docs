import { useState, useMemo } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Server, Plus } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DataTable,
  SortableHeader,
  type PaginationState,
  type ColumnFilter,
  createSelectionColumn,
  type RowSelectionState,
} from "@/components/ui/data-table";
import {
  useConfigurations,
  useCreateConfiguration,
  useConfigurationTypes,
  useConfigurationStatuses,
  useBatchToggleConfigurations,
  type Configuration,
  type ConfigurationCreate,
  type ConfigurationUpdate,
} from "@/hooks/useConfigurations";
import { useDebounce } from "@/hooks/useDebounce";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { usePermissions } from "@/hooks/usePermissions";
import { ConfigForm } from "@/components/configurations/ConfigForm";
import { toast } from "sonner";

// Column definitions for the configurations table
const columns: ColumnDef<Configuration>[] = [
  createSelectionColumn<Configuration>(),
  {
    accessorKey: "name",
    header: ({ column }) => (
      <SortableHeader column={column}>Name</SortableHeader>
    ),
    cell: ({ row }) => {
      const isEnabled = row.original.is_enabled;
      return (
        <div className={`flex items-center gap-2 ${!isEnabled ? "opacity-60 line-through" : ""}`}>
          <Server className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.getValue("name")}</span>
          {!isEnabled && (
            <Badge variant="secondary" className="text-xs">
              Disabled
            </Badge>
          )}
        </div>
      );
    },
    size: 200,
  },
  {
    accessorKey: "configuration_type_name",
    header: ({ column }) => (
      <SortableHeader column={column}>Type</SortableHeader>
    ),
    cell: ({ row }) => {
      const typeName = row.getValue("configuration_type_name") as string | null;
      return typeName ? (
        <Badge variant="outline">{typeName}</Badge>
      ) : (
        <span className="text-muted-foreground">-</span>
      );
    },
  },
  {
    accessorKey: "configuration_status_name",
    header: ({ column }) => (
      <SortableHeader column={column}>Status</SortableHeader>
    ),
    cell: ({ row }) => {
      const statusName = row.getValue("configuration_status_name") as
        | string
        | null;
      return statusName ? (
        <Badge variant="secondary">{statusName}</Badge>
      ) : (
        <span className="text-muted-foreground">-</span>
      );
    },
  },
  {
    accessorKey: "manufacturer",
    header: ({ column }) => (
      <SortableHeader column={column}>Manufacturer</SortableHeader>
    ),
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.getValue("manufacturer") || "-"}
      </span>
    ),
  },
  {
    accessorKey: "ip_address",
    header: ({ column }) => (
      <SortableHeader column={column}>IP Address</SortableHeader>
    ),
    cell: ({ row }) => (
      <span className="text-muted-foreground font-mono text-sm">
        {row.getValue("ip_address") || "-"}
      </span>
    ),
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
const allColumnIds = [
  "name",
  "configuration_type_name",
  "configuration_status_name",
  "manufacturer",
  "ip_address",
  "updated_at",
];

export function ConfigurationsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
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

  const batchToggle = useBatchToggleConfigurations(orgId!);

  // Column preferences with server-side persistence
  const {
    columnVisibility,
    columnOrder,
    onColumnVisibilityChange,
    onColumnOrderChange,
    isLoading: prefsLoading,
  } = useColumnPreferences("configurations", allColumnIds);

  const { data: types = [] } = useConfigurationTypes();
  const { data: statuses = [] } = useConfigurationStatuses();
  const createConfiguration = useCreateConfiguration(orgId!);

  // Build column filters from URL params
  const columnFilters = useMemo(() => {
    const filters: ColumnFilter[] = [];
    const typeId = searchParams.get("type");
    const statusId = searchParams.get("status");
    if (typeId) {
      filters.push({ columnId: "configuration_type_name", value: typeId });
    }
    if (statusId) {
      filters.push({ columnId: "configuration_status_name", value: statusId });
    }
    return filters;
  }, [searchParams]);

  // Extract filter values for API call
  const typeFilter = columnFilters.find(
    (f) => f.columnId === "configuration_type_name"
  )?.value;
  const statusFilter = columnFilters.find(
    (f) => f.columnId === "configuration_status_name"
  )?.value;

  const { data, isLoading, refetch, isRefetching } = useConfigurations(orgId!, {
    typeId: typeFilter,
    statusId: statusFilter,
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });

  // Reset pagination when search changes
  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    setPagination((prev) => ({ ...prev, offset: 0 }));
  };

  // Handle column filter changes - sync to URL
  const handleColumnFiltersChange = (filters: ColumnFilter[]) => {
    const params = new URLSearchParams();
    const typeId = filters.find(
      (f) => f.columnId === "configuration_type_name"
    )?.value;
    const statusId = filters.find(
      (f) => f.columnId === "configuration_status_name"
    )?.value;
    if (typeId) params.set("type", typeId);
    if (statusId) params.set("status", statusId);
    setSearchParams(params);
    // Reset pagination when filter changes
    setPagination({ limit: pagination.limit, offset: 0 });
  };

  // Build filterable columns configuration
  const filterableColumns = useMemo(
    () => [
      {
        columnId: "configuration_type_name",
        title: "Type",
        options: types.map((t) => ({ label: t.name, value: t.id })),
      },
      {
        columnId: "configuration_status_name",
        title: "Status",
        options: statuses.map((s) => ({ label: s.name, value: s.id })),
      },
    ],
    [types, statuses]
  );

  const hasFilters = typeFilter || statusFilter;

  const handleCreate = async (
    formData: ConfigurationCreate | ConfigurationUpdate
  ) => {
    try {
      // In create mode, we know the data will be ConfigurationCreate
      const result = await createConfiguration.mutateAsync(
        formData as ConfigurationCreate
      );
      setFormOpen(false);
      toast.success("Configuration created successfully");
      navigate(`/org/${orgId}/configurations/${result.id}`);
    } catch {
      toast.error("Failed to create configuration");
    }
  };

  const handleRowClick = (config: Configuration) => {
    navigate(`/org/${orgId}/configurations/${config.id}`);
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
        <Server className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">
          {hasFilters
            ? "No configurations match filters"
            : "No configurations yet"}
        </h3>
        <p className="text-sm text-muted-foreground text-center mb-4">
          {hasFilters
            ? "Try adjusting your filters or clearing them"
            : "Get started by adding your first configuration"}
        </p>
        {!hasFilters && canEdit && (
          <Button onClick={() => setFormOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Configuration
          </Button>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Configurations
          </h1>
          <p className="text-muted-foreground mt-1">
            Document system configurations and assets
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
        searchPlaceholder="Search configurations..."
        filterableColumns={filterableColumns}
        columnFilters={columnFilters}
        onColumnFiltersChange={handleColumnFiltersChange}
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

      <ConfigForm
        open={formOpen}
        onOpenChange={setFormOpen}
        onSubmit={handleCreate}
        isSubmitting={createConfiguration.isPending}
        mode="create"
        types={types}
        statuses={statuses}
        orgId={orgId!}
      />
    </div>
  );
}
