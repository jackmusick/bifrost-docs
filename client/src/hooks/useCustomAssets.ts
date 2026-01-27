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

export interface CustomAssetsParams {
  pagination?: PaginationParams;
  search?: string;
  showDisabled?: boolean;
}

// =============================================================================
// Field Definition Types
// =============================================================================

export type FieldType =
  | "text"
  | "textbox"
  | "number"
  | "date"
  | "checkbox"
  | "select"
  | "header"
  | "password"
  | "totp";

export interface FieldDefinition {
  key: string;
  name: string;
  type: FieldType;
  required: boolean;
  show_in_list: boolean;
  hint: string | null;
  default_value: string | null;
  options: string[] | null;
}

// =============================================================================
// Custom Asset Type Types
// =============================================================================

export interface CustomAssetType {
  id: string;
  name: string;
  fields: FieldDefinition[];
  sort_order: number;
  display_field_key: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  asset_count: number;
}

export interface CustomAssetTypeCreate {
  name: string;
  fields: FieldDefinition[];
  display_field_key?: string | null;
}

export interface CustomAssetTypeUpdate {
  name?: string;
  fields?: FieldDefinition[];
  display_field_key?: string | null;
}

// =============================================================================
// Custom Asset Types Hooks (Global - not org-scoped)
// =============================================================================

export function useCustomAssetTypes(options?: { includeInactive?: boolean }) {
  return useQuery({
    queryKey: ["custom-asset-types", options?.includeInactive],
    queryFn: async () => {
      const response = await api.get<CustomAssetType[]>(
        `/api/custom-asset-types`,
        { params: { include_inactive: options?.includeInactive ?? false } }
      );
      return response.data;
    },
  });
}

export function useCustomAssetType(typeId: string) {
  return useQuery({
    queryKey: ["custom-asset-types", typeId],
    queryFn: async () => {
      const response = await api.get<CustomAssetType>(
        `/api/custom-asset-types/${typeId}`
      );
      return response.data;
    },
    enabled: !!typeId,
  });
}

export function useCreateCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CustomAssetTypeCreate) => {
      const response = await api.post<CustomAssetType>(
        `/api/custom-asset-types`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useUpdateCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: CustomAssetTypeUpdate }) => {
      const response = await api.put<CustomAssetType>(
        `/api/custom-asset-types/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({
        queryKey: ["custom-asset-types", id],
      });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useDeleteCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (typeId: string) => {
      await api.delete(`/api/custom-asset-types/${typeId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useDeactivateCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (typeId: string) => {
      const response = await api.post<CustomAssetType>(
        `/api/custom-asset-types/${typeId}/deactivate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useActivateCustomAssetType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (typeId: string) => {
      const response = await api.post<CustomAssetType>(
        `/api/custom-asset-types/${typeId}/activate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}


export function useReorderCustomAssetTypes() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ids: string[]) => {
      await api.patch("/api/custom-asset-types/reorder", { ids });
    },
    onMutate: async (ids) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: ["custom-asset-types"] });
      await queryClient.cancelQueries({ queryKey: ["sidebar"] });

      // Snapshot previous value
      const previousTypes = queryClient.getQueryData<CustomAssetType[]>([
        "custom-asset-types",
      ]);

      // Optimistically update
      queryClient.setQueryData<CustomAssetType[]>(
        ["custom-asset-types"],
        (old) => {
          if (!old) return old;
          return ids.map((id) => old.find((t) => t.id === id)!).filter(Boolean);
        }
      );

      return { previousTypes };
    },
    onError: (_err, _ids, context) => {
      // Rollback on error
      if (context?.previousTypes) {
        queryClient.setQueryData(["custom-asset-types"], context.previousTypes);
      }
    },
    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: ["custom-asset-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

// =============================================================================
// Custom Asset Instance Types
// =============================================================================

export interface CustomAsset {
  id: string;
  organization_id: string;
  custom_asset_type_id: string;
  values: Record<string, unknown>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export type CustomAssetReveal = CustomAsset & {
  /** values includes decrypted password fields */
  values: Record<string, unknown>;
}

export interface CustomAssetCreate {
  values: Record<string, unknown>;
  is_enabled?: boolean;
}

export interface CustomAssetUpdate {
  values?: Record<string, unknown>;
  is_enabled?: boolean;
}

// =============================================================================
// Custom Asset Instance Hooks
// =============================================================================

export function useCustomAssets(
  orgId: string,
  typeId: string,
  options?: CustomAssetsParams
) {
  return useQuery({
    queryKey: ["custom-assets", orgId, typeId, options],
    queryFn: async () => {
      const params: Record<string, string | number | boolean> = {};
      if (options?.pagination?.limit !== undefined) params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined) params.offset = options.pagination.offset;
      if (options?.search) params.search = options.search;
      if (options?.showDisabled) params.show_disabled = true;

      const response = await api.get<PaginatedResponse<CustomAsset>>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets`,
        { params }
      );
      return response.data;
    },
    enabled: !!orgId && !!typeId,
    placeholderData: keepPreviousData,
  });
}

export function useCustomAsset(orgId: string, typeId: string, assetId: string) {
  return useQuery({
    queryKey: ["custom-assets", orgId, typeId, assetId],
    queryFn: async () => {
      const response = await api.get<CustomAsset>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${assetId}`
      );
      return response.data;
    },
    enabled: !!orgId && !!typeId && !!assetId,
  });
}

export function useRevealCustomAsset(
  orgId: string,
  typeId: string,
  assetId: string
) {
  return useQuery({
    queryKey: ["custom-assets", orgId, typeId, assetId, "reveal"],
    queryFn: async () => {
      const response = await api.get<CustomAssetReveal>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${assetId}/reveal`
      );
      return response.data;
    },
    enabled: false, // Only fetch when explicitly requested
  });
}

export function useCreateCustomAsset(orgId: string, typeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CustomAssetCreate) => {
      const response = await api.post<CustomAsset>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["custom-assets", orgId, typeId],
      });
    },
  });
}

export function useUpdateCustomAsset(
  orgId: string,
  typeId: string,
  assetId: string
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CustomAssetUpdate) => {
      const response = await api.put<CustomAsset>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${assetId}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["custom-assets", orgId, typeId],
      });
      queryClient.invalidateQueries({
        queryKey: ["custom-assets", orgId, typeId, assetId],
      });
    },
  });
}

export function useDeleteCustomAsset(orgId: string, typeId: string, onDeleted?: (id: string) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (assetId: string) => {
      await api.delete(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/${assetId}`
      );
      return assetId;
    },
    onSuccess: (_data, assetId) => {
      // Navigate FIRST (if callback provided) to unmount detail page before cache removal
      // This prevents the detail page query from refetching a deleted resource
      onDeleted?.(assetId);

      // Remove detail query from cache
      queryClient.removeQueries({
        queryKey: ["custom-assets", orgId, typeId, assetId],
      });
      // Invalidate ONLY list queries (4th element is object), not detail queries (4th element is string)
      queryClient.invalidateQueries({
        predicate: (query) => {
          const key = query.queryKey;
          return (
            key[0] === "custom-assets" &&
            key[1] === orgId &&
            key[2] === typeId &&
            (key.length === 3 || typeof key[3] === "object")
          );
        },
      });
      // Invalidate sidebar to update counts
      queryClient.invalidateQueries({ queryKey: ["sidebar", orgId] });
    },
  });
}

export function useBatchToggleCustomAssets(orgId: string, typeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ids, isEnabled }: { ids: string[]; isEnabled: boolean }) => {
      const response = await api.patch<{ updated_count: number }>(
        `/api/organizations/${orgId}/custom-asset-types/${typeId}/assets/batch/toggle`,
        { ids, is_enabled: isEnabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["custom-assets", orgId, typeId],
      });
    },
  });
}
