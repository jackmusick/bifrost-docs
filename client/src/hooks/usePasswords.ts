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

export interface PasswordsParams {
  pagination?: PaginationParams;
  search?: string;
  showDisabled?: boolean;
}

// =============================================================================
// Types
// =============================================================================

export interface Password {
  id: string;
  organization_id: string;
  name: string;
  username: string | null;
  url: string | null;
  notes: string | null;
  has_totp: boolean;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface PasswordReveal extends Password {
  password: string;
  totp_secret: string | null;
}

export interface PasswordCreate {
  name: string;
  username?: string;
  password: string;
  url?: string;
  notes?: string;
  totp_secret?: string;
  is_enabled?: boolean;
}

export interface PasswordUpdate {
  name?: string;
  username?: string;
  password?: string;
  url?: string;
  notes?: string;
  totp_secret?: string;
  is_enabled?: boolean;
}

// =============================================================================
// Hooks
// =============================================================================

export function usePasswords(
  orgId: string,
  options?: PasswordsParams
) {
  return useQuery({
    // Use specific values in query key instead of entire object for better caching
    queryKey: [
      "passwords",
      orgId,
      {
        search: options?.search,
        limit: options?.pagination?.limit,
        offset: options?.pagination?.offset,
        showDisabled: options?.showDisabled,
      },
    ],
    queryFn: async () => {
      const params: Record<string, string | number | boolean> = {};
      if (options?.pagination?.limit !== undefined) params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined) params.offset = options.pagination.offset;
      if (options?.search) params.search = options.search;
      if (options?.showDisabled !== undefined) params.show_disabled = options.showDisabled;

      const response = await api.get<PaginatedResponse<Password>>(
        `/api/organizations/${orgId}/passwords`,
        { params }
      );
      return response.data;
    },
    enabled: !!orgId,
    placeholderData: keepPreviousData,
  });
}

export function usePassword(orgId: string, id: string) {
  return useQuery({
    queryKey: ["passwords", orgId, id],
    queryFn: async () => {
      const response = await api.get<Password>(
        `/api/organizations/${orgId}/passwords/${id}`
      );
      return response.data;
    },
    enabled: !!orgId && !!id,
  });
}

export function useRevealPassword(orgId: string, id: string) {
  return useQuery({
    queryKey: ["passwords", orgId, id, "reveal"],
    queryFn: async () => {
      const response = await api.get<PasswordReveal>(
        `/api/organizations/${orgId}/passwords/${id}/reveal`
      );
      return response.data;
    },
    enabled: false, // Only fetch when explicitly requested
  });
}

export function useCreatePassword(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PasswordCreate) => {
      const response = await api.post<Password>(
        `/api/organizations/${orgId}/passwords`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["passwords", orgId] });
    },
  });
}

export function useUpdatePassword(orgId: string, id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PasswordUpdate) => {
      const response = await api.put<Password>(
        `/api/organizations/${orgId}/passwords/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["passwords", orgId] });
      queryClient.invalidateQueries({ queryKey: ["passwords", orgId, id] });
    },
  });
}

export function useDeletePassword(orgId: string, onDeleted?: (id: string) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/organizations/${orgId}/passwords/${id}`);
      return id;
    },
    onSuccess: (_data, id) => {
      // Navigate FIRST (if callback provided) to unmount detail page before cache removal
      // This prevents the detail page query from refetching a deleted resource
      onDeleted?.(id);

      // Remove detail query from cache
      queryClient.removeQueries({ queryKey: ["passwords", orgId, id] });
      // Invalidate ONLY list queries (3rd element is object), not detail queries (3rd element is string)
      queryClient.invalidateQueries({
        predicate: (query) => {
          const key = query.queryKey;
          return (
            key[0] === "passwords" &&
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

export function useBatchTogglePasswords(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ids, isEnabled }: { ids: string[]; isEnabled: boolean }) => {
      const response = await api.patch<{ updated_count: number }>(
        `/api/organizations/${orgId}/passwords/batch/toggle`,
        { ids, is_enabled: isEnabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["passwords", orgId] });
    },
  });
}
