import { useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Building2, Plus } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DataTable,
  SortableHeader,
  type PaginationState,
  createSelectionColumn,
  type RowSelectionState,
} from "@/components/ui/data-table";
import {
  useOrganizations,
  useCreateOrganization,
  useUpdateOrganization,
} from "@/hooks/useOrganizations";
import { useDebounce } from "@/hooks/useDebounce";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { OrganizationForm } from "@/components/organizations/OrganizationForm";
import { usePermissions } from "@/hooks/usePermissions";
import { toast } from "sonner";
import type { Organization } from "@/lib/api-client";

// Column definitions for the organizations table
const columns: ColumnDef<Organization>[] = [
  createSelectionColumn<Organization>(),
  {
    accessorKey: "name",
    header: ({ column }) => (
      <SortableHeader column={column}>Name</SortableHeader>
    ),
    cell: ({ row }) => {
      const isEnabled = row.original.is_enabled;
      return (
        <div className={`flex items-center gap-2 min-w-0 ${!isEnabled ? "opacity-60 line-through" : ""}`}>
          <Building2 className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="font-medium truncate">{row.getValue("name")}</span>
        </div>
      );
    },
    minSize: 200,
    size: 300,
  },
  {
    accessorKey: "is_enabled",
    header: ({ column }) => (
      <SortableHeader column={column}>Status</SortableHeader>
    ),
    cell: ({ row }) => {
      const isEnabled = row.getValue("is_enabled") as boolean;
      return (
        <Badge variant={isEnabled ? "default" : "secondary"}>
          {isEnabled ? "Enabled" : "Disabled"}
        </Badge>
      );
    },
    size: 100,
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => (
      <div className="text-right">
        <SortableHeader column={column}>Created</SortableHeader>
      </div>
    ),
    cell: ({ row }) => (
      <div className="text-right text-muted-foreground">
        {new Date(row.getValue("created_at")).toLocaleDateString()}
      </div>
    ),
    size: 110,
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
    size: 110,
  },
  {
    accessorKey: "updated_by_user_name",
    header: ({ column }) => (
      <SortableHeader column={column}>Updated By</SortableHeader>
    ),
    cell: ({ row }) => (
      <span className="text-muted-foreground truncate block">
        {row.getValue("updated_by_user_name") || "-"}
      </span>
    ),
    size: 180,
  },
];

// Columns to pin to the left by default
const pinnedColumns = ["select", "name"];

// All column IDs for preferences
const allColumnIds = ["name", "is_enabled", "created_at", "updated_at", "updated_by_user_name"];

export function OrganizationsPage() {
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
  const { isAdmin } = usePermissions();

  const updateOrganization = useUpdateOrganization();

  // Column preferences with server-side persistence
  const {
    columnVisibility,
    columnOrder,
    onColumnVisibilityChange,
    onColumnOrderChange,
    isLoading: prefsLoading,
  } = useColumnPreferences("organizations", allColumnIds);

  const { data: allOrganizations, isLoading, refetch, isRefetching } = useOrganizations({ showDisabled });

  // Client-side filtering and pagination
  const filteredOrganizations = useMemo(() => {
    if (!allOrganizations) return [];
    if (!debouncedSearch.trim()) return allOrganizations;

    const query = debouncedSearch.toLowerCase();
    return allOrganizations.filter((org) =>
      org.name.toLowerCase().includes(query)
    );
  }, [allOrganizations, debouncedSearch]);

  const paginatedData = useMemo(() => {
    const start = pagination.offset;
    const end = start + pagination.limit;
    return filteredOrganizations.slice(start, end);
  }, [filteredOrganizations, pagination]);

  // Reset pagination when search changes
  const handleSearchChange = useCallback((value: string) => {
    setSearchInput(value);
    setPagination((prev) => ({ ...prev, offset: 0 }));
  }, []);

  const createOrganization = useCreateOrganization();

  const handleCreate = useCallback(async (formData: { name: string; metadata?: Record<string, any> }) => {
    try {
      const result = await createOrganization.mutateAsync({ name: formData.name });
      setFormOpen(false);
      toast.success("Organization created successfully");
      navigate(`/admin/organizations/${result.data.id}`);
    } catch {
      toast.error("Failed to create organization");
    }
  }, [createOrganization, navigate]);

  const handleRowClick = useCallback((organization: Organization) => {
    navigate(`/admin/organizations/${organization.id}`);
  }, [navigate]);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleOpenForm = useCallback(() => {
    setFormOpen(true);
  }, []);

  const handleBulkActivate = useCallback(async () => {
    const ids = Object.keys(rowSelection);
    try {
      await Promise.all(
        ids.map((id) => updateOrganization.mutateAsync({ id, data: { is_enabled: true } }))
      );
      setRowSelection({});
      toast.success(`Enabled ${ids.length} organization${ids.length > 1 ? 's' : ''}`);
    } catch {
      toast.error("Failed to enable organizations");
    }
  }, [rowSelection, updateOrganization]);

  const handleBulkDeactivate = useCallback(async () => {
    const ids = Object.keys(rowSelection);
    try {
      await Promise.all(
        ids.map((id) => updateOrganization.mutateAsync({ id, data: { is_enabled: false } }))
      );
      setRowSelection({});
      toast.success(`Disabled ${ids.length} organization${ids.length > 1 ? 's' : ''}`);
    } catch {
      toast.error("Failed to disable organizations");
    }
  }, [rowSelection, updateOrganization]);

  const emptyContent = useMemo(() => (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-20">
        <Building2 className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">No organizations yet</h3>
        <p className="text-sm text-muted-foreground text-center mb-4">
          {isAdmin
            ? "Get started by creating your first organization"
            : "No organizations have been created yet"}
        </p>
        {isAdmin && (
          <Button onClick={handleOpenForm}>
            <Plus className="mr-2 h-4 w-4" />
            Create Organization
          </Button>
        )}
      </CardContent>
    </Card>
  ), [isAdmin, handleOpenForm]);

  // Redirect non-admin users
  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <Building2 className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Access Denied</h2>
        <p className="text-sm text-muted-foreground mb-4">
          You don't have permission to view this page.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Organizations</h1>
          <p className="text-muted-foreground mt-1">
            Manage organizations and their settings
          </p>
        </div>
        {isAdmin && (
          <Button variant="outline" size="icon" onClick={() => setFormOpen(true)}>
            <Plus className="h-5 w-5" />
          </Button>
        )}
      </div>

      <DataTable
        columns={columns}
        data={paginatedData}
        total={filteredOrganizations.length}
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
        searchPlaceholder="Search organizations..."
        showDisabled={showDisabled}
        onShowDisabledChange={setShowDisabled}
        onRefresh={handleRefresh}
        isRefreshing={isRefetching}
        enableRowSelection
        rowSelection={rowSelection}
        onRowSelectionChange={setRowSelection}
        getRowId={(row) => row.id}
        selectedCount={Object.keys(rowSelection).length}
        bulkActions={{
          onActivate: handleBulkActivate,
          onDeactivate: handleBulkDeactivate,
          isLoading: updateOrganization.isPending,
        }}
      />

      <OrganizationForm
        open={formOpen}
        onOpenChange={setFormOpen}
        onSubmit={handleCreate}
        isSubmitting={createOrganization.isPending}
        mode="create"
      />
    </div>
  );
}
