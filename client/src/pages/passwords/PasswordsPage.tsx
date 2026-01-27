import { useState, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { KeyRound, Plus, ExternalLink } from "lucide-react";
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
  usePasswords,
  useCreatePassword,
  useBatchTogglePasswords,
  type Password,
  type PasswordCreate,
  type PasswordUpdate,
} from "@/hooks/usePasswords";
import { useDebounce } from "@/hooks/useDebounce";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { PasswordForm } from "@/components/passwords/PasswordForm";
import { PasswordListActions } from "@/components/passwords/PasswordListActions";
import { usePermissions } from "@/hooks/usePermissions";
import { toast } from "sonner";

// Column definitions for the passwords table
const createColumns = (orgId: string): ColumnDef<Password>[] => [
  createSelectionColumn<Password>(),
  {
    accessorKey: "name",
    header: ({ column }) => (
      <SortableHeader column={column}>Name</SortableHeader>
    ),
    cell: ({ row }) => {
      const isEnabled = row.original.is_enabled;
      return (
        <div className={`flex items-center gap-2 min-w-0 ${!isEnabled ? "opacity-60 line-through" : ""}`}>
          <KeyRound className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="font-medium truncate">{row.getValue("name")}</span>
        </div>
      );
    },
    minSize: 150,
    size: 250,
  },
  {
    accessorKey: "username",
    header: ({ column }) => (
      <SortableHeader column={column}>Username</SortableHeader>
    ),
    cell: ({ row }) => (
      <span className="text-muted-foreground truncate block">
        {row.getValue("username") || "-"}
      </span>
    ),
    size: 180,
  },
  {
    accessorKey: "url",
    header: ({ column }) => (
      <SortableHeader column={column}>URL</SortableHeader>
    ),
    cell: ({ row }) => {
      const url = row.getValue("url") as string | null;
      if (!url) {
        return <span className="text-muted-foreground">-</span>;
      }
      try {
        return (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-primary hover:underline"
          >
            <ExternalLink className="h-3 w-3 shrink-0" />
            <span className="truncate">
              {new URL(url).hostname}
            </span>
          </a>
        );
      } catch {
        return <span className="text-muted-foreground truncate block">{url}</span>;
      }
    },
    size: 200,
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
    id: "actions",
    header: () => null,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <PasswordListActions password={row.original} orgId={orgId} />
      </div>
    ),
    size: 130,
    enableSorting: false,
    enableHiding: false,
  },
];

// Columns to pin to the left by default
const pinnedColumns = ["select", "name"];

// All column IDs for preferences
const allColumnIds = ["name", "username", "url", "updated_at"];

export function PasswordsPage() {
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

  const columns = useMemo(() => createColumns(orgId!), [orgId]);

  const batchToggle = useBatchTogglePasswords(orgId!);

  // Column preferences with server-side persistence
  const {
    columnVisibility,
    columnOrder,
    onColumnVisibilityChange,
    onColumnOrderChange,
    isLoading: prefsLoading,
  } = useColumnPreferences("passwords", allColumnIds);

  const { data, isLoading, refetch, isRefetching } = usePasswords(orgId!, {
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });

  // Reset pagination when search changes
  const handleSearchChange = useCallback((value: string) => {
    setSearchInput(value);
    setPagination((prev) => ({ ...prev, offset: 0 }));
  }, []);

  const createPassword = useCreatePassword(orgId!);

  const handleCreate = useCallback(async (formData: PasswordCreate | PasswordUpdate) => {
    try {
      // In create mode, we know the data will be PasswordCreate
      const result = await createPassword.mutateAsync(formData as PasswordCreate);
      setFormOpen(false);
      toast.success("Password created successfully");
      navigate(`/org/${orgId}/passwords/${result.id}`);
    } catch {
      toast.error("Failed to create password");
    }
  }, [createPassword, navigate, orgId]);

  const handleRowClick = useCallback((password: Password) => {
    navigate(`/org/${orgId}/passwords/${password.id}`);
  }, [navigate, orgId]);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleOpenForm = useCallback(() => {
    setFormOpen(true);
  }, []);

  const handleBulkActivate = useCallback(async () => {
    const ids = Object.keys(rowSelection);
    await batchToggle.mutateAsync({ ids, isEnabled: true });
    setRowSelection({});
    toast.success(`Activated ${ids.length} item${ids.length > 1 ? 's' : ''}`);
  }, [rowSelection, batchToggle]);

  const handleBulkDeactivate = useCallback(async () => {
    const ids = Object.keys(rowSelection);
    await batchToggle.mutateAsync({ ids, isEnabled: false });
    setRowSelection({});
    toast.success(`Deactivated ${ids.length} item${ids.length > 1 ? 's' : ''}`);
  }, [rowSelection, batchToggle]);

  const emptyContent = useMemo(() => (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-20">
        <KeyRound className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">No passwords yet</h3>
        <p className="text-sm text-muted-foreground text-center mb-4">
          {canEdit
            ? "Get started by adding your first password entry"
            : "No password entries have been added yet"}
        </p>
        {canEdit && (
          <Button onClick={handleOpenForm}>
            <Plus className="mr-2 h-4 w-4" />
            Add Password
          </Button>
        )}
      </CardContent>
    </Card>
  ), [canEdit, handleOpenForm]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Passwords</h1>
          <p className="text-muted-foreground mt-1">
            Securely store and manage credentials
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
        searchPlaceholder="Search passwords..."
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
          isLoading: batchToggle.isPending,
        }}
      />

      <PasswordForm
        open={formOpen}
        onOpenChange={setFormOpen}
        onSubmit={handleCreate}
        isSubmitting={createPassword.isPending}
        mode="create"
        orgId={orgId!}
      />
    </div>
  );
}
