import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";

// Types matching the API response
export interface SidebarItemCount {
  id: string;
  name: string;
  count: number;
}

export interface SidebarData {
  passwords_count: number;
  locations_count: number;
  documents_count: number;
  configuration_types: SidebarItemCount[];
  custom_asset_types: SidebarItemCount[];
}

/**
 * Fetch sidebar navigation data for an organization.
 *
 * Returns counts for core entities (passwords, locations, documents)
 * and dynamic types (configuration types, custom asset types) with their counts.
 *
 * Note: Types are now fetched globally, but counts are still per-org.
 * The API endpoint combines global types with org-specific counts.
 */
export function useSidebarData(orgId: string | undefined) {
  return useQuery({
    queryKey: ["sidebar", orgId],
    queryFn: async () => {
      const response = await api.get<SidebarData>(
        `/api/organizations/${orgId}/sidebar`
      );
      return response.data;
    },
    enabled: !!orgId,
    // Sidebar data doesn't change frequently, so we can cache it longer
    staleTime: 30 * 1000, // 30 seconds
    // Refetch when window regains focus (to catch changes from other tabs)
    refetchOnWindowFocus: true,
  });
}
