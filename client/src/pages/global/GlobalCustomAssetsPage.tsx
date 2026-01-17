import { useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Layers, Building2, ArrowLeft } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DataTable,
  SortableHeader,
  type PaginationState,
} from "@/components/ui/data-table";
import {
  useGlobalCustomAssets,
  type GlobalCustomAsset,
} from "@/hooks/useGlobalData";
import {
  useCustomAssetType,
  type CustomAssetType,
} from "@/hooks/useCustomAssets";
import { stripAndTruncate } from "@/lib/text-utils";

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
): ColumnDef<GlobalCustomAsset>[] {
  const listFields = assetType.fields.filter(
    (f) => f.show_in_list && f.type !== "header"
  );

  const columns: ColumnDef<GlobalCustomAsset>[] = [
    {
      accessorKey: "name",
      header: ({ column }) => (
        <SortableHeader column={column}>Name</SortableHeader>
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-muted-foreground" />
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
        const typeId = row.original.custom_asset_type_id;
        return (
          <Link
            to={`/org/${orgId}/assets/${typeId}`}
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-2 text-primary hover:underline"
          >
            <Building2 className="h-4 w-4" />
            <span>{orgName}</span>
          </Link>
        );
      },
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

export function GlobalCustomAssetsPage() {
  const { typeId } = useParams<{ typeId: string }>();
  const navigate = useNavigate();
  const [pagination, setPagination] = useState<PaginationState>({
    limit: 25,
    offset: 0,
  });

  const { data: assetType, isLoading: typeLoading } = useCustomAssetType(typeId!);
  const { data, isLoading: assetsLoading, refetch, isRefetching } = useGlobalCustomAssets(typeId!, pagination);

  // Build columns dynamically based on asset type
  const columns = useMemo(() => {
    if (!assetType) return [];
    return buildColumns(assetType);
  }, [assetType]);

  // Columns to pin - always pin organization_name for global view
  const pinnedColumns = useMemo(() => {
    return ["organization_name"];
  }, []);

  const handleRowClick = (asset: GlobalCustomAsset) => {
    navigate(`/org/${asset.organization_id}/assets/${typeId}/${asset.id}`);
  };

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
          <Link to="/global">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Global View
          </Link>
        </Button>
      </div>
    );
  }

  const emptyContent = (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-20">
        <Layers className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">
          No {assetType.name.toLowerCase()} yet
        </h3>
        <p className="text-sm text-muted-foreground text-center mb-4">
          No {assetType.name.toLowerCase()} have been created across any organization
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
            <span>{assetType.name}</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">All {assetType.name}</h1>
          <p className="text-muted-foreground mt-1">
            View {assetType.name.toLowerCase()} across all organizations
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
        isLoading={assetsLoading}
        emptyContent={emptyContent}
        showColumnToggle
        columnVisibilityStorageKey={`column-visibility-global-custom-assets-${typeId}`}
        onRefresh={() => { refetch(); }}
        isRefreshing={isRefetching}
      />
    </div>
  );
}
