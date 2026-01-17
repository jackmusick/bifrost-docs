import { useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";

// =============================================================================
// Types
// =============================================================================

export interface RecentItem {
  entity_type: string;
  entity_id: string;
  organization_id: string | null;
  org_name: string | null;
  name: string;
  viewed_at: string;
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch the current user's recently accessed entities.
 *
 * @param limit - Maximum number of items to return (default: 10)
 */
export function useRecentlyAccessed(limit = 10) {
  return useQuery({
    queryKey: ["recent", limit],
    queryFn: async () => {
      const response = await api.get<RecentItem[]>("/api/me/recent", {
        params: { limit },
      });
      return response.data;
    },
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to invalidate the recent list.
 * Call this after navigating to an entity detail page.
 */
export function useInvalidateRecent() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: ["recent"] });
  };
}
