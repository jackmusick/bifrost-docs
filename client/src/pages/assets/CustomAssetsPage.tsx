import { useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Layers, Plus, Settings2, ArrowLeft } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  DataTable,
  SortableHeader,
  type PaginationState,
  createSelectionColumn,
  type RowSelectionState,
} from "@/components/ui/data-table";
import { AssetTypeForm } from "@/components/assets/AssetTypeForm";
import { CustomAssetForm } from "@/components/assets/CustomAssetForm";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { usePermissions } from "@/hooks/usePermissions";
import {
  useCustomAssetTypes,
  useCustomAssetType,
  useCreateCustomAssetType,
  useDeleteCustomAssetType,
  useCustomAssets,
  useCreateCustomAsset,
  useBatchToggleCustomAssets,
  type CustomAssetType,
  type CustomAssetTypeCreate,
  type CustomAsset,
  type CustomAssetCreate,
} from "@/hooks/useCustomAssets";
import { useDebounce } from "@/hooks/useDebounce";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { stripAndTruncate } from "@/lib/text-utils";
import { getDisplayFieldKey, getDisplayValue } from "@/lib/custom-asset-utils";
import { toast } from "sonner";

export function CustomAssetsPage() {
  const { orgId, typeId } = useParams<{ orgId: string; typeId: string }>();

  // If typeId is provided, show assets for that type
  // Otherwise, show list of asset types
  if (typeId) {
    return <AssetListView orgId={orgId!} typeId={typeId} />;
  }

  return <AssetTypesView orgId={orgId!} />;
}

// =============================================================================
// Asset Types List View
// =============================================================================

function AssetTypesView({ orgId }: { orgId: string }) {
  const navigate = useNavigate();
  const [formOpen, setFormOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const { canEdit } = usePermissions();

  const { data: assetTypes, isLoading } = useCustomAssetTypes();
  const createAssetType = useCreateCustomAssetType();
  const deleteAssetType = useDeleteCustomAssetType();

  const handleCreate = async (data: CustomAssetTypeCreate) => {
    try {
      const result = await createAssetType.mutateAsync(data);
      setFormOpen(false);
      toast.success("Asset type created successfully");
      navigate(`/org/${orgId}/assets/${result.id}`);
    } catch {
      toast.error("Failed to create asset type");
    }
  };

  const handleDelete = async () => {
    if (!selectedTypeId) return;
    try {
      await deleteAssetType.mutateAsync(selectedTypeId);
      toast.success("Asset type deleted successfully");
      setDeleteOpen(false);
      setSelectedTypeId(null);
    } catch {
      toast.error("Failed to delete asset type");
    }
  };

  const selectedType = assetTypes?.find((t) => t.id === selectedTypeId);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Custom Assets</h1>
          <p className="text-muted-foreground mt-1">
            Create and manage custom asset types
          </p>
        </div>
        {canEdit && (
          <Button variant="outline" size="icon" onClick={() => setFormOpen(true)}>
            <Plus className="h-5 w-5" />
          </Button>
        )}
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : !assetTypes?.length ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-20">
            <Layers className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium mb-1">No asset types yet</h3>
            <p className="text-sm text-muted-foreground text-center mb-4">
              {canEdit
                ? "Create custom asset types to organize specialized assets"
                : "No custom asset types have been created yet"}
            </p>
            {canEdit && (
              <Button onClick={() => setFormOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Asset Type
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {assetTypes.map((type) => (
            <Card
              key={type.id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => navigate(`/org/${orgId}/assets/${type.id}`)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Layers className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{type.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        {type.fields.filter((f) => f.type !== "header").length} fields
                      </p>
                    </div>
                  </div>
                  {canEdit && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTypeId(type.id);
                        setDeleteOpen(true);
                      }}
                    >
                      <Settings2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex flex-wrap gap-1">
                  {type.fields
                    .filter((f) => f.show_in_list && f.type !== "header")
                    .slice(0, 4)
                    .map((field) => (
                      <Badge key={field.key} variant="secondary" className="text-xs">
                        {field.name}
                      </Badge>
                    ))}
                  {type.fields.filter((f) => f.show_in_list && f.type !== "header").length > 4 && (
                    <Badge variant="outline" className="text-xs">
                      +{type.fields.filter((f) => f.show_in_list && f.type !== "header").length - 4} more
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AssetTypeForm
        open={formOpen}
        onOpenChange={setFormOpen}
        onSubmit={(data) => handleCreate(data as CustomAssetTypeCreate)}
        isSubmitting={createAssetType.isPending}
        mode="create"
      />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Asset Type"
        description={`Are you sure you want to delete "${selectedType?.name}"? This will also delete all assets of this type. This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteAssetType.isPending}
      />
    </div>
  );
}

// =============================================================================
// Asset List View (for a specific type)
// =============================================================================

// Helper function to format values for list display
function formatListValue(
  field: { type: string },
  value: unknown
): string {
  if (value === undefined || value === null || value === "") {
    return "-";
  }

  switch (field.type) {
    case "checkbox":
      return value === true || value === "true" ? "Yes" : "No";
    case "date":
      try {
        return new Date(String(value)).toLocaleDateString();
      } catch {
        return String(value);
      }
    case "number":
      return typeof value === "number" ? value.toLocaleString() : String(value);
    case "password":
      return "********";
    case "textbox":
      // Rich text fields may contain HTML - strip it and truncate
      return stripAndTruncate(String(value), 50);
    default: {
      const strValue = String(value);
      return strValue.length > 50 ? strValue.slice(0, 47) + "..." : strValue;
    }
  }
}

// Build dynamic columns based on asset type fields
function buildColumns(
  assetType: CustomAssetType
): ColumnDef<CustomAsset>[] {
  const displayFieldKey = getDisplayFieldKey(assetType);
  const displayField = displayFieldKey
    ? assetType.fields.find(f => f.key === displayFieldKey)
    : null;
  const displayFieldName = displayField?.name || "Name";

  // Get list fields, excluding the display field if it would be duplicated
  const listFields = assetType.fields.filter(
    (f) => f.show_in_list && f.type !== "header" && f.key !== displayFieldKey
  );

  const columns: ColumnDef<CustomAsset>[] = [
    createSelectionColumn<CustomAsset>(),
    {
      id: "display_name",
      accessorFn: (row) => displayFieldKey ? row.values[displayFieldKey] : null,
      header: ({ column }) => (
        <SortableHeader column={column}>{displayFieldName}</SortableHeader>
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">
            {getDisplayValue(row.original, displayFieldKey)}
          </span>
        </div>
      ),
      size: 200,
    },
  ];

  // Add dynamic columns for each list field
  for (const field of listFields) {
    columns.push({
      id: field.key,
      accessorFn: (row) => row.values[field.key],
      header: ({ column }) => (
        <SortableHeader column={column}>{field.name}</SortableHeader>
      ),
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {formatListValue(field, row.original.values[field.key])}
        </span>
      ),
    });
  }

  // Add updated_at column at the end
  columns.push({
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
  });

  return columns;
}

function AssetListView({ orgId, typeId }: { orgId: string; typeId: string }) {
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

  const batchToggle = useBatchToggleCustomAssets(orgId, typeId);

  const { data: assetType, isLoading: typeLoading } = useCustomAssetType(typeId);
  const { data, isLoading: assetsLoading, refetch, isRefetching } = useCustomAssets(orgId, typeId, {
    pagination,
    search: debouncedSearch || undefined,
    showDisabled,
  });
  const createAsset = useCreateCustomAsset(orgId, typeId);

  // Reset pagination when search changes
  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    setPagination((prev) => ({ ...prev, offset: 0 }));
  };

  const handleCreate = async (formData: CustomAssetCreate) => {
    try {
      const result = await createAsset.mutateAsync(formData);
      setFormOpen(false);
      toast.success("Asset created successfully");
      navigate(`/org/${orgId}/assets/${typeId}/${result.id}`);
    } catch {
      toast.error("Failed to create asset");
    }
  };

  const handleRowClick = (asset: CustomAsset) => {
    navigate(`/org/${orgId}/assets/${typeId}/${asset.id}`);
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

  // Build columns dynamically based on asset type
  const columns = useMemo(() => {
    if (!assetType) return [];
    return buildColumns(assetType);
  }, [assetType]);

  // Pin display name column to the left (keeps it visible when scrolling horizontally)
  const pinnedColumns = ["select", "display_name"];

  // Get display field key for this asset type
  const displayFieldKey = useMemo(() => {
    if (!assetType) return null;
    return getDisplayFieldKey(assetType);
  }, [assetType]);

  // All column IDs for preferences (dynamically computed from asset type)
  const allColumnIds = useMemo(() => {
    if (!assetType) return ["display_name", "updated_at"];
    const listFields = assetType.fields.filter(
      (f) => f.show_in_list && f.type !== "header" && f.key !== displayFieldKey
    );
    return ["display_name", ...listFields.map((f) => f.key), "updated_at"];
  }, [assetType, displayFieldKey]);

  // Default visible columns based on show_in_list field setting
  const defaultVisibleColumns = useMemo(() => {
    if (!assetType) return ["display_name", "updated_at"];
    const showInListFields = assetType.fields
      .filter((f) => f.show_in_list && f.type !== "header" && f.key !== displayFieldKey)
      .map((f) => f.key);
    return ["display_name", ...showInListFields, "updated_at"];
  }, [assetType, displayFieldKey]);

  // Column preferences with server-side persistence
  // Use custom_asset_{typeId} as entity type for per-asset-type preferences
  const {
    columnVisibility,
    columnOrder,
    onColumnVisibilityChange,
    onColumnOrderChange,
    isLoading: prefsLoading,
  } = useColumnPreferences(`custom_asset_${typeId}`, allColumnIds, {
    // Default to fields with show_in_list enabled
    visible: defaultVisibleColumns,
  });

  if (typeLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Card>
          <CardContent className="p-6">
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!assetType) {
    return (
      <div className="text-center py-12">
        <Layers className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Asset type not found</h2>
        <p className="text-sm text-muted-foreground mb-4">
          The asset type you're looking for doesn't exist or has been deleted.
        </p>
        <Button asChild variant="outline">
          <Link to={`/org/${orgId}/assets`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Asset Types
          </Link>
        </Button>
      </div>
    );
  }

  const emptyContent = (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-20">
        <Layers className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">No {assetType.name.toLowerCase()} yet</h3>
        <p className="text-sm text-muted-foreground text-center mb-4">
          {canEdit
            ? `Get started by creating your first ${assetType.name.toLowerCase()}`
            : `No ${assetType.name.toLowerCase()} have been added yet`}
        </p>
        {canEdit && (
          <Button onClick={() => setFormOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add {assetType.name}
          </Button>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
            <Link
              to={`/org/${orgId}/assets`}
              className="hover:text-foreground transition-colors"
            >
              Asset Types
            </Link>
            <span>/</span>
            <span>{assetType.name}</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{assetType.name}</h1>
          <p className="text-muted-foreground mt-1">
            Manage {assetType.name.toLowerCase()} assets
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
        isLoading={assetsLoading || prefsLoading}
        emptyContent={emptyContent}
        showColumnToggle
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={onColumnVisibilityChange}
        columnOrder={columnOrder}
        onColumnOrderChange={onColumnOrderChange}
        useApiPersistence
        searchValue={searchInput}
        onSearchChange={handleSearchChange}
        searchPlaceholder={`Search ${assetType.name.toLowerCase()}...`}
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

      <CustomAssetForm
        open={formOpen}
        onOpenChange={setFormOpen}
        onSubmit={(formData) => handleCreate(formData as CustomAssetCreate)}
        isSubmitting={createAsset.isPending}
        mode="create"
        assetType={assetType}
      />
    </div>
  );
}
