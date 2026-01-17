import { useAuthStore } from "@/stores/auth.store";
import { useRecentlyAccessed } from "@/hooks/useRecentlyAccessed";
import { RecentEntityCard } from "@/components/RecentEntityCard";

export function DashboardPage() {
  const { user } = useAuthStore();
  const { data: recentItems, isLoading: recentLoading } = useRecentlyAccessed(12);

  // Separate organizations from other entities
  const recentOrgs =
    recentItems?.filter((item) => item.entity_type === "organization").slice(0, 6) || [];
  const recentEntities =
    recentItems?.filter((item) => item.entity_type !== "organization").slice(0, 6) || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Welcome to Bifrost Docs, {user?.name || "User"}
        </p>
      </div>

      {/* Recent Organizations Section */}
      {!recentLoading && recentOrgs.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent Organizations</h2>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {recentOrgs.map((item) => (
              <RecentEntityCard
                key={`${item.entity_type}-${item.entity_id}`}
                entityType={item.entity_type}
                entityId={item.entity_id}
                organizationId={item.organization_id}
                orgName={item.org_name}
                name={item.name}
                showOrg={false}
              />
            ))}
          </div>
        </div>
      )}

      {/* Recent Entities Section */}
      {!recentLoading && recentEntities.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent Items</h2>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {recentEntities.map((item) => (
              <RecentEntityCard
                key={`${item.entity_type}-${item.entity_id}`}
                entityType={item.entity_type}
                entityId={item.entity_id}
                organizationId={item.organization_id}
                orgName={item.org_name}
                name={item.name}
              />
            ))}
          </div>
        </div>
      )}

      <div className="text-muted-foreground">
        <p>Select an organization from the header to get started, or browse the tabs above.</p>
      </div>
    </div>
  );
}
