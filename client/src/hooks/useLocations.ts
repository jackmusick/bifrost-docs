import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import api from "@/lib/api-client";

// =============================================================================
// Pagination Types
// =============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
}

export interface LocationsParams {
  pagination?: PaginationParams;
  search?: string;
  showDisabled?: boolean;
}

// =============================================================================
// Types
// =============================================================================

export interface Location {
  id: string;
  organization_id: string;
  name: string;
  notes: string | null;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface LocationCreate {
  name: string;
  notes?: string;
  is_enabled?: boolean;
}

export interface LocationUpdate {
  name?: string;
  notes?: string;
  is_enabled?: boolean;
}

// =============================================================================
// Hooks
// =============================================================================

export function useLocations(
  orgId: string,
  options?: LocationsParams
) {
  return useQuery({
    queryKey: ["locations", orgId, options],
    queryFn: async () => {
      const params: Record<string, string | number | boolean> = {};
      if (options?.pagination?.limit !== undefined) params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined) params.offset = options.pagination.offset;
      if (options?.search) params.search = options.search;
      if (options?.showDisabled !== undefined) params.show_disabled = options.showDisabled;

      const response = await api.get<PaginatedResponse<Location>>(
        `/api/organizations/${orgId}/locations`,
        { params }
      );
      return response.data;
    },
    enabled: !!orgId,
    placeholderData: keepPreviousData,
  });
}

export function useLocation(orgId: string, id: string) {
  return useQuery({
    queryKey: ["locations", orgId, id],
    queryFn: async () => {
      const response = await api.get<Location>(
        `/api/organizations/${orgId}/locations/${id}`
      );
      return response.data;
    },
    enabled: !!orgId && !!id,
  });
}

export function useCreateLocation(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LocationCreate) => {
      const response = await api.post<Location>(
        `/api/organizations/${orgId}/locations`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["locations", orgId] });
    },
  });
}

export function useUpdateLocation(orgId: string, id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LocationUpdate) => {
      const response = await api.put<Location>(
        `/api/organizations/${orgId}/locations/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["locations", orgId] });
      queryClient.invalidateQueries({ queryKey: ["locations", orgId, id] });
    },
  });
}

export function useDeleteLocation(orgId: string, onDeleted?: (id: string) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/organizations/${orgId}/locations/${id}`);
      return id;
    },
    onSuccess: (_data, id) => {
      // Navigate FIRST (if callback provided) to unmount detail page before cache removal
      // This prevents the detail page query from refetching a deleted resource
      onDeleted?.(id);

      // Remove detail query from cache
      queryClient.removeQueries({ queryKey: ["locations", orgId, id] });
      // Invalidate ONLY list queries (3rd element is object), not detail queries (3rd element is string)
      queryClient.invalidateQueries({
        predicate: (query) => {
          const key = query.queryKey;
          return (
            key[0] === "locations" &&
            key[1] === orgId &&
            (key.length === 2 || typeof key[2] === "object")
          );
        },
      });
      // Invalidate sidebar to update counts
      queryClient.invalidateQueries({ queryKey: ["sidebar", orgId] });
    },
  });
}

export function useBatchToggleLocations(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ids, isEnabled }: { ids: string[]; isEnabled: boolean }) => {
      const response = await api.patch<{ updated_count: number }>(
        `/api/organizations/${orgId}/locations/batch/toggle`,
        { ids, is_enabled: isEnabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["locations", orgId] });
    },
  });
}
