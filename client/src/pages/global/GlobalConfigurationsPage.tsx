import { useState, useMemo } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { Server, Building2 } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DataTable,
  SortableHeader,
  type PaginationState,
  type ColumnFilter,
} from "@/components/ui/data-table";
import {
  useGlobalConfigurations,
  type GlobalConfiguration,
} from "@/hooks/useGlobalData";
import {
  useConfigurationTypes,
  useConfigurationStatuses,
} from "@/hooks/useConfigurations";

// Column definitions for the global configurations table
const columns: ColumnDef<GlobalConfiguration>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => (
      <SortableHeader column={column}>Name</SortableHeader>
    ),
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <Server className="h-4 w-4 text-muted-foreground" />
        <span className="font-medium">{row.getValue("name")}</span>
      </div>
    ),
    size: 200,
  },
  {
    accessorKey: "organization_name",
    header: ({ column }) => (
      <SortableHeader column={column}>Organization</SortableHeader>
    ),
    cell: ({ row }) => {
      const orgId = row.original.organization_id;
      const orgName = row.getValue("organization_name") as string;
      return (
        <Link
          to={`/org/${orgId}/configurations`}
          onClick={(e) => e.stopPropagation()}
          className="flex items-center gap-2 text-primary hover:underline"
        >
          <Building2 className="h-4 w-4" />
          <span>{orgName}</span>
        </Link>
      );
    },
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
      const statusName = row.getValue("configuration_status_name") as string | null;
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
const pinnedColumns = ["organization_name"];

export function GlobalConfigurationsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [pagination, setPagination] = useState<PaginationState>({
    limit: 25,
    offset: 0,
  });
  const [searchInput, setSearchInput] = useState("");

  const { data: types = [] } = useConfigurationTypes();
  const { data: statuses = [] } = useConfigurationStatuses();

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

  const { data, isLoading, refetch, isRefetching } = useGlobalConfigurations({
    typeId: typeFilter,
    statusId: statusFilter,
    pagination,
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

  // Get the current type name for display in the header
  const currentTypeName = useMemo(() => {
    if (!typeFilter) return null;
    const type = types.find((t) => t.id === typeFilter);
    return type?.name || null;
  }, [typeFilter, types]);

  const hasFilters = typeFilter || statusFilter;

  const handleRowClick = (config: GlobalConfiguration) => {
    navigate(`/org/${config.organization_id}/configurations/${config.id}`);
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
            : "No configurations have been created across any organization"}
        </p>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
            <Link to="/global" className="hover:text-foreground transition-colors">
              Global View
            </Link>
            <span>/</span>
            <span>Configurations</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">
            {currentTypeName ? `All ${currentTypeName}` : "All Configurations"}
          </h1>
          <p className="text-muted-foreground mt-1">
            {currentTypeName
              ? `View ${currentTypeName.toLowerCase()} across all organizations`
              : "View configurations across all organizations"}
          </p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        total={data?.total}
        pagination={pagination}
        onPaginationChange={setPagination}
        pinnedColumns={pinnedColumns}
        onRowClick={handleRowClick}
        isLoading={isLoading}
        emptyContent={emptyContent}
        showColumnToggle
        columnVisibilityStorageKey="column-visibility-global-configurations"
        searchValue={searchInput}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search configurations..."
        filterableColumns={filterableColumns}
        columnFilters={columnFilters}
        onColumnFiltersChange={handleColumnFiltersChange}
        onRefresh={() => { refetch(); }}
        isRefreshing={isRefetching}
      />
    </div>
  );
}
