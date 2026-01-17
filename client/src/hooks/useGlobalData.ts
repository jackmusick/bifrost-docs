import { useQuery } from "@tanstack/react-query";
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
// Global Types (include organization_name)
// =============================================================================

export interface GlobalPassword {
  id: string;
  organization_id: string;
  organization_name: string;
  name: string;
  username: string | null;
  url: string | null;
  notes: string | null;
  has_totp: boolean;
  created_at: string;
  updated_at: string;
}

export interface GlobalConfiguration {
  id: string;
  organization_id: string;
  organization_name: string;
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
  created_at: string;
  updated_at: string;
  configuration_type_name: string | null;
  configuration_status_name: string | null;
}

export interface GlobalLocation {
  id: string;
  organization_id: string;
  organization_name: string;
  name: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface GlobalDocument {
  id: string;
  organization_id: string;
  organization_name: string;
  path: string;
  name: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface GlobalCustomAsset {
  id: string;
  organization_id: string;
  organization_name: string;
  custom_asset_type_id: string;
  name: string;
  values: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface GlobalSidebarItemCount {
  id: string;
  name: string;
  count: number;
}

export interface GlobalSidebarData {
  passwords_count: number;
  locations_count: number;
  documents_count: number;
  configuration_types: GlobalSidebarItemCount[];
  custom_asset_types: GlobalSidebarItemCount[];
}

// =============================================================================
// Global Passwords Hook
// =============================================================================

export function useGlobalPasswords(pagination?: PaginationParams) {
  return useQuery({
    queryKey: ["global", "passwords", pagination],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (pagination?.limit !== undefined) params.limit = pagination.limit;
      if (pagination?.offset !== undefined) params.offset = pagination.offset;

      const response = await api.get<PaginatedResponse<GlobalPassword>>(
        `/api/global/passwords`,
        { params }
      );
      return response.data;
    },
  });
}

// =============================================================================
// Global Configurations Hook
// =============================================================================

export function useGlobalConfigurations(options?: {
  typeId?: string;
  statusId?: string;
  pagination?: PaginationParams;
}) {
  return useQuery({
    queryKey: ["global", "configurations", options],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (options?.typeId) params.configuration_type_id = options.typeId;
      if (options?.statusId) params.configuration_status_id = options.statusId;
      if (options?.pagination?.limit !== undefined)
        params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined)
        params.offset = options.pagination.offset;

      const response = await api.get<PaginatedResponse<GlobalConfiguration>>(
        `/api/global/configurations`,
        { params }
      );
      return response.data;
    },
  });
}

// =============================================================================
// Global Locations Hook
// =============================================================================

export function useGlobalLocations(pagination?: PaginationParams) {
  return useQuery({
    queryKey: ["global", "locations", pagination],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (pagination?.limit !== undefined) params.limit = pagination.limit;
      if (pagination?.offset !== undefined) params.offset = pagination.offset;

      const response = await api.get<PaginatedResponse<GlobalLocation>>(
        `/api/global/locations`,
        { params }
      );
      return response.data;
    },
  });
}

// =============================================================================
// Global Documents Hook
// =============================================================================

export function useGlobalDocuments(options?: {
  path?: string;
  pagination?: PaginationParams;
}) {
  return useQuery({
    queryKey: ["global", "documents", options?.path, options?.pagination],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (options?.path !== undefined) params.path = options.path;
      if (options?.pagination?.limit !== undefined)
        params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined)
        params.offset = options.pagination.offset;

      const response = await api.get<PaginatedResponse<GlobalDocument>>(
        `/api/global/documents`,
        { params }
      );
      return response.data;
    },
  });
}

// =============================================================================
// Global Custom Assets Hook
// =============================================================================

export function useGlobalCustomAssets(
  typeId: string,
  pagination?: PaginationParams
) {
  return useQuery({
    queryKey: ["global", "custom-assets", typeId, pagination],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        type_id: typeId,
      };
      if (pagination?.limit !== undefined) params.limit = pagination.limit;
      if (pagination?.offset !== undefined) params.offset = pagination.offset;

      const response = await api.get<PaginatedResponse<GlobalCustomAsset>>(
        `/api/global/custom-assets`,
        { params }
      );
      return response.data;
    },
    enabled: !!typeId,
  });
}

// =============================================================================
// Global Sidebar Data Hook
// =============================================================================

export function useGlobalSidebarData() {
  return useQuery({
    queryKey: ["global", "sidebar"],
    queryFn: async () => {
      const response = await api.get<GlobalSidebarData>(`/api/global/sidebar`);
      return response.data;
    },
    // Sidebar data doesn't change frequently, so we can cache it longer
    staleTime: 30 * 1000, // 30 seconds
    // Refetch when window regains focus (to catch changes from other tabs)
    refetchOnWindowFocus: true,
  });
}
