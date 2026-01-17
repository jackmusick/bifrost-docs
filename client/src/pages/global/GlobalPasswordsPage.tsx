import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { KeyRound, ExternalLink, Building2 } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { Card, CardContent } from "@/components/ui/card";
import {
  DataTable,
  SortableHeader,
  type PaginationState,
} from "@/components/ui/data-table";
import {
  useGlobalPasswords,
  type GlobalPassword,
} from "@/hooks/useGlobalData";

// Column definitions for the global passwords table
const columns: ColumnDef<GlobalPassword>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => (
      <SortableHeader column={column}>Name</SortableHeader>
    ),
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <KeyRound className="h-4 w-4 text-muted-foreground" />
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
          to={`/org/${orgId}/passwords`}
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
    accessorKey: "username",
    header: ({ column }) => (
      <SortableHeader column={column}>Username</SortableHeader>
    ),
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.getValue("username") || "-"}
      </span>
    ),
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
            <ExternalLink className="h-3 w-3" />
            <span className="truncate max-w-[200px]">
              {new URL(url).hostname}
            </span>
          </a>
        );
      } catch {
        return <span className="text-muted-foreground">{url}</span>;
      }
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
const pinnedColumns = ["organization_name"];

export function GlobalPasswordsPage() {
  const navigate = useNavigate();
  const [pagination, setPagination] = useState<PaginationState>({
    limit: 25,
    offset: 0,
  });

  const { data, isLoading, refetch, isRefetching } = useGlobalPasswords(pagination);

  const handleRowClick = (password: GlobalPassword) => {
    // Navigate to the password detail page in the organization context
    navigate(`/org/${password.organization_id}/passwords/${password.id}`);
  };

  const emptyContent = (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-20">
        <KeyRound className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">No passwords yet</h3>
        <p className="text-sm text-muted-foreground text-center mb-4">
          No passwords have been created across any organization
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
            <span>Passwords</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">All Passwords</h1>
          <p className="text-muted-foreground mt-1">
            View credentials across all organizations
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
        columnVisibilityStorageKey="column-visibility-global-passwords"
        onRefresh={() => { refetch(); }}
        isRefreshing={isRefetching}
      />
    </div>
  );
}
