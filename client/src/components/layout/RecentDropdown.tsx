import {
  Clock,
  Key,
  Server,
  MapPin,
  FileText,
  Package,
  Building2,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useRecentlyAccessed, type RecentItem } from "@/hooks/useRecentlyAccessed";
import { Skeleton } from "@/components/ui/skeleton";

const entityIcons: Record<string, React.ComponentType<{ className?: string }>> =
  {
    password: Key,
    configuration: Server,
    location: MapPin,
    document: FileText,
    custom_asset: Package,
    organization: Building2,
  };

function getEntityPath(item: RecentItem): string {
  if (item.entity_type === "organization") {
    return `/org/${item.entity_id}`;
  }
  return `/org/${item.organization_id}/${item.entity_type}s/${item.entity_id}`;
}

export function RecentDropdown() {
  const navigate = useNavigate();
  const { data: recentItems, isLoading } = useRecentlyAccessed(10);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Clock className="h-4 w-4" />
          <span className="sr-only">Recent items</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel>Recently Accessed</DropdownMenuLabel>
        <DropdownMenuSeparator />

        {isLoading ? (
          <div className="p-2 space-y-2">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : recentItems && recentItems.length > 0 ? (
          recentItems.map((item) => {
            const Icon = entityIcons[item.entity_type] || Package;
            return (
              <DropdownMenuItem
                key={`${item.entity_type}-${item.entity_id}`}
                onClick={() => navigate(getEntityPath(item))}
                className="cursor-pointer"
              >
                <Icon className="h-4 w-4 mr-3 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{item.name}</p>
                  {item.org_name && item.entity_type !== "organization" && (
                    <p className="text-xs text-muted-foreground truncate">
                      {item.org_name}
                    </p>
                  )}
                </div>
              </DropdownMenuItem>
            );
          })
        ) : (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No recent activity
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
