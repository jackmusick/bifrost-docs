import { useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import { History, User, Key, Bot, Globe } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DataTable,
  SortableHeader,
  type PaginationState,
} from "@/components/ui/data-table";
import {
  useOrgAuditLogs,
  useGlobalAuditLogs,
  type AuditLogEntry,
  formatAction,
  formatEntityType,
  getActionColor,
} from "@/hooks/useAuditLogs";
import { useDebounce } from "@/hooks/useDebounce";
import { formatDateTime, formatRelativeTime } from "@/lib/date-utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// Stable empty array to prevent infinite re-renders in DataTable
const EMPTY_PINNED_COLUMNS: string[] = [];

// =============================================================================
// Helper Components
// =============================================================================

function ActorIcon({ actorType }: { actorType: string }) {
  switch (actorType) {
    case "user":
      return <User className="h-3.5 w-3.5" />;
    case "api_key":
      return <Key className="h-3.5 w-3.5" />;
    case "system":
      return <Bot className="h-3.5 w-3.5" />;
    default:
      return <User className="h-3.5 w-3.5" />;
  }
}

function ActionBadge({ action }: { action: string }) {
  const colorClass = getActionColor(action);
  return (
    <Badge variant="outline" className={`font-medium ${colorClass}`}>
      {formatAction(action)}
    </Badge>
  );
}

// =============================================================================
// Column Definitions
// =============================================================================

const getColumns = (isGlobal: boolean): ColumnDef<AuditLogEntry>[] => {
  const columns: ColumnDef<AuditLogEntry>[] = [];

  // Organization column (for global view, or placeholder for org view)
  if (isGlobal) {
    columns.push({
      accessorKey: "organization_name",
      header: ({ column }) => (
        <SortableHeader column={column}>Organization</SortableHeader>
      ),
      cell: ({ row }) => {
        const orgName = row.original.organization_name;
        return (
          <div className="flex items-center gap-2">
            {!orgName && <Globe className="h-3.5 w-3.5 text-muted-foreground" />}
            <span className={orgName ? "" : "text-muted-foreground italic"}>
              {orgName || "Global"}
            </span>
          </div>
        );
      },
      size: 180,
    });
  }

  // Entity Type column
  columns.push({
    accessorKey: "entity_type",
    header: ({ column }) => (
      <SortableHeader column={column}>Entity Type</SortableHeader>
    ),
    cell: ({ row }) => (
      <span className="font-medium">
        {formatEntityType(row.getValue("entity_type"))}
      </span>
    ),
    size: 130,
  });

  // Name column (actor who performed the action)
  columns.push({
    accessorKey: "actor_display_name",
    header: ({ column }) => (
      <SortableHeader column={column}>Name</SortableHeader>
    ),
    cell: ({ row }) => {
      const actorType = row.original.actor_type;
      const displayName = row.original.actor_display_name;
      const actorLabel = row.original.actor_label;

      return (
        <div className="flex items-center gap-2">
          <ActorIcon actorType={actorType} />
          <span className="truncate max-w-[200px]">
            {displayName || actorLabel || "System"}
          </span>
        </div>
      );
    },
    size: 200,
  });

  // Action column
  columns.push({
    accessorKey: "action",
    header: ({ column }) => (
      <SortableHeader column={column}>Action</SortableHeader>
    ),
    cell: ({ row }) => <ActionBadge action={row.getValue("action")} />,
    size: 120,
  });

  // Date column
  columns.push({
    accessorKey: "created_at",
    header: ({ column }) => (
      <SortableHeader column={column}>Date</SortableHeader>
    ),
    cell: ({ row }) => {
      const createdAt = row.getValue("created_at") as string;
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="text-muted-foreground whitespace-nowrap cursor-help">
              {formatRelativeTime(createdAt)}
            </span>
          </TooltipTrigger>
          <TooltipContent>{formatDateTime(createdAt)}</TooltipContent>
        </Tooltip>
      );
    },
    size: 140,
  });

  return columns;
};

// =============================================================================
// Org-scoped Audit Trail Page
// =============================================================================

export function OrgAuditTrailPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const [pagination, setPagination] = useState<PaginationState>({
    limit: 50,
    offset: 0,
  });
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebounce(searchInput, 300);

  // Convert offset-based pagination to page-based for API
  const page = Math.floor(pagination.offset / pagination.limit) + 1;

  const { data, isLoading, refetch, isRefetching } = useOrgAuditLogs(orgId!, {
    page,
    page_size: pagination.limit,
    search: debouncedSearch || undefined,
  });

  const columns = useMemo(() => getColumns(false), []);

  // Reset pagination when search changes
  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    setPagination((prev) => ({ ...prev, offset: 0 }));
  };

  const emptyContent = (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-20">
        <History className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">No audit events yet</h3>
        <p className="text-sm text-muted-foreground text-center">
          Activity in this organization will appear here
        </p>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Audit Trail</h1>
          <p className="text-muted-foreground mt-1">
            View activity history for this organization
          </p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        total={data?.total}
        pagination={pagination}
        onPaginationChange={setPagination}
        pinnedColumns={EMPTY_PINNED_COLUMNS}
        isLoading={isLoading}
        emptyContent={emptyContent}
        searchValue={searchInput}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search audit logs..."
        onRefresh={() => { refetch(); }}
        isRefreshing={isRefetching}
      />
    </div>
  );
}

// =============================================================================
// Global Audit Trail Page
// =============================================================================

export function GlobalAuditTrailPage() {
  const [pagination, setPagination] = useState<PaginationState>({
    limit: 50,
    offset: 0,
  });
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebounce(searchInput, 300);

  // Convert offset-based pagination to page-based for API
  const page = Math.floor(pagination.offset / pagination.limit) + 1;

  const { data, isLoading, refetch, isRefetching } = useGlobalAuditLogs({
    page,
    page_size: pagination.limit,
    search: debouncedSearch || undefined,
  });

  const columns = useMemo(() => getColumns(true), []);

  // Reset pagination when search changes
  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    setPagination((prev) => ({ ...prev, offset: 0 }));
  };

  const emptyContent = (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-20">
        <History className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">No audit events yet</h3>
        <p className="text-sm text-muted-foreground text-center">
          Activity across all organizations will appear here
        </p>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Audit Trail</h1>
          <p className="text-muted-foreground mt-1">
            View activity history across all organizations
          </p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        total={data?.total}
        pagination={pagination}
        onPaginationChange={setPagination}
        pinnedColumns={EMPTY_PINNED_COLUMNS}
        isLoading={isLoading}
        emptyContent={emptyContent}
        searchValue={searchInput}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search audit logs..."
        onRefresh={() => { refetch(); }}
        isRefreshing={isRefetching}
      />
    </div>
  );
}
