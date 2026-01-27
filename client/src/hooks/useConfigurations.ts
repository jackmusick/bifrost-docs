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

// =============================================================================
// Types
// =============================================================================

export interface ConfigurationType {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  configuration_count: number;
}

export interface ConfigurationStatus {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  configuration_count: number;
}

export interface Configuration {
  id: string;
  organization_id: string;
  configuration_type_id: string | null;
  configuration_status_id: string | null;
  name: string;
  serial_number: string | null;
  asset_tag: string | null;
  manufacturer: string | null;
  model: string | null;
  ip_address: string | null;
  mac_address: string | null;
  notes: string | null;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
  configuration_type_name: string | null;
  configuration_status_name: string | null;
}

export interface ConfigurationCreate {
  name: string;
  configuration_type_id?: string;
  configuration_status_id?: string;
  serial_number?: string;
  asset_tag?: string;
  manufacturer?: string;
  model?: string;
  ip_address?: string;
  mac_address?: string;
  notes?: string;
  is_enabled?: boolean;
}

export interface ConfigurationUpdate {
  name?: string;
  configuration_type_id?: string | null;
  configuration_status_id?: string | null;
  serial_number?: string;
  asset_tag?: string;
  manufacturer?: string;
  model?: string;
  ip_address?: string;
  mac_address?: string;
  notes?: string;
  is_enabled?: boolean;
}

// Configuration Types Hooks (Global - not org-scoped)
export function useConfigurationTypes(options?: { includeInactive?: boolean }) {
  return useQuery({
    queryKey: ["configuration-types", options?.includeInactive],
    queryFn: async () => {
      const response = await api.get<ConfigurationType[]>(
        `/api/configuration-types`,
        { params: { include_inactive: options?.includeInactive ?? false } }
      );
      return response.data;
    },
  });
}

export function useCreateConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { name: string }) => {
      const response = await api.post<ConfigurationType>(
        `/api/configuration-types`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useUpdateConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: { name: string } }) => {
      const response = await api.put<ConfigurationType>(
        `/api/configuration-types/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useDeleteConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/configuration-types/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useDeactivateConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ConfigurationType>(
        `/api/configuration-types/${id}/deactivate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

export function useActivateConfigurationType() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ConfigurationType>(
        `/api/configuration-types/${id}/activate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-types"] });
      queryClient.invalidateQueries({ queryKey: ["sidebar"] });
    },
  });
}

// Configuration Statuses Hooks (Global - not org-scoped)
export function useConfigurationStatuses(options?: { includeInactive?: boolean }) {
  return useQuery({
    queryKey: ["configuration-statuses", options?.includeInactive],
    queryFn: async () => {
      const response = await api.get<ConfigurationStatus[]>(
        `/api/configuration-statuses`,
        { params: { include_inactive: options?.includeInactive ?? false } }
      );
      return response.data;
    },
  });
}

export function useCreateConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { name: string }) => {
      const response = await api.post<ConfigurationStatus>(
        `/api/configuration-statuses`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}

export function useUpdateConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: { name: string } }) => {
      const response = await api.put<ConfigurationStatus>(
        `/api/configuration-statuses/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}

export function useDeleteConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/configuration-statuses/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}

export function useDeactivateConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ConfigurationStatus>(
        `/api/configuration-statuses/${id}/deactivate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}

export function useActivateConfigurationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post<ConfigurationStatus>(
        `/api/configuration-statuses/${id}/activate`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration-statuses"] });
    },
  });
}


// Configurations Hooks
export function useConfigurations(
  orgId: string,
  options?: {
    typeId?: string;
    statusId?: string;
    pagination?: PaginationParams;
    search?: string;
    showDisabled?: boolean;
  }
) {
  return useQuery({
    queryKey: ["configurations", orgId, options],
    queryFn: async () => {
      const params: Record<string, string | number | boolean> = {};
      if (options?.typeId) params.configuration_type_id = options.typeId;
      if (options?.statusId) params.configuration_status_id = options.statusId;
      if (options?.pagination?.limit !== undefined) params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined) params.offset = options.pagination.offset;
      if (options?.search) params.search = options.search;
      if (options?.showDisabled !== undefined) params.show_disabled = options.showDisabled;

      const response = await api.get<PaginatedResponse<Configuration>>(
        `/api/organizations/${orgId}/configurations`,
        { params }
      );
      return response.data;
    },
    enabled: !!orgId,
    placeholderData: keepPreviousData,
  });
}

export function useConfiguration(orgId: string, id: string) {
  return useQuery({
    queryKey: ["configurations", orgId, id],
    queryFn: async () => {
      const response = await api.get<Configuration>(
        `/api/organizations/${orgId}/configurations/${id}`
      );
      return response.data;
    },
    enabled: !!orgId && !!id,
  });
}

export function useCreateConfiguration(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ConfigurationCreate) => {
      const response = await api.post<Configuration>(
        `/api/organizations/${orgId}/configurations`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configurations", orgId] });
    },
  });
}

export function useUpdateConfiguration(orgId: string, id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ConfigurationUpdate) => {
      const response = await api.put<Configuration>(
        `/api/organizations/${orgId}/configurations/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configurations", orgId] });
      queryClient.invalidateQueries({ queryKey: ["configurations", orgId, id] });
    },
  });
}

export function useDeleteConfiguration(orgId: string, onDeleted?: (id: string) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/organizations/${orgId}/configurations/${id}`);
      return id;
    },
    onSuccess: (_data, id) => {
      // Navigate FIRST (if callback provided) to unmount detail page before cache removal
      // This prevents the detail page query from refetching a deleted resource
      onDeleted?.(id);

      // Remove detail query from cache
      queryClient.removeQueries({ queryKey: ["configurations", orgId, id] });
      // Invalidate ONLY list queries (3rd element is object), not detail queries (3rd element is string)
      queryClient.invalidateQueries({
        predicate: (query) => {
          const key = query.queryKey;
          return (
            key[0] === "configurations" &&
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

export function useBatchToggleConfigurations(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ids, isEnabled }: { ids: string[]; isEnabled: boolean }) => {
      const response = await api.patch<{ updated_count: number }>(
        `/api/organizations/${orgId}/configurations/batch/toggle`,
        { ids, is_enabled: isEnabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configurations", orgId] });
    },
  });
}
