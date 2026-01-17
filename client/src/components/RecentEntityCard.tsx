// client/src/components/RecentEntityCard.tsx

import { useNavigate } from "react-router-dom";
import {
  Key,
  Server,
  MapPin,
  FileText,
  Package,
  Building2,
  type LucideIcon,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface RecentEntityCardProps {
  entityType: string;
  entityId: string;
  organizationId: string | null;
  orgName: string | null;
  name: string;
  showOrg?: boolean;
  className?: string;
}

const entityConfig: Record<
  string,
  { icon: LucideIcon; label: string; path: (orgId: string, id: string) => string }
> = {
  password: {
    icon: Key,
    label: "Password",
    path: (orgId, id) => `/org/${orgId}/passwords/${id}`,
  },
  configuration: {
    icon: Server,
    label: "Configuration",
    path: (orgId, id) => `/org/${orgId}/configurations/${id}`,
  },
  location: {
    icon: MapPin,
    label: "Location",
    path: (orgId, id) => `/org/${orgId}/locations/${id}`,
  },
  document: {
    icon: FileText,
    label: "Document",
    path: (orgId, id) => `/org/${orgId}/documents/${id}`,
  },
  custom_asset: {
    icon: Package,
    label: "Asset",
    path: (orgId, id) => `/org/${orgId}/assets/${id}`,
  },
  organization: {
    icon: Building2,
    label: "Organization",
    path: (_, id) => `/org/${id}`,
  },
};

export function RecentEntityCard({
  entityType,
  entityId,
  organizationId,
  orgName,
  name,
  showOrg = true,
  className,
}: RecentEntityCardProps) {
  const navigate = useNavigate();
  const config = entityConfig[entityType] || {
    icon: Package,
    label: entityType,
    path: () => "#",
  };
  const Icon = config.icon;

  const handleClick = () => {
    const orgId = organizationId || entityId; // For organizations, use entityId
    navigate(config.path(orgId, entityId));
  };

  return (
    <Card
      className={cn(
        "hover:border-primary/50 transition-colors cursor-pointer group min-w-[180px]",
        className
      )}
      onClick={handleClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Icon className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium truncate">{name}</p>
            {showOrg && orgName && entityType !== "organization" && (
              <p className="text-xs text-muted-foreground truncate">{orgName}</p>
            )}
            {!showOrg && (
              <p className="text-xs text-muted-foreground">{config.label}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
