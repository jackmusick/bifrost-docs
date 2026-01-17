import { keepPreviousData, useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";

// =============================================================================
// Types
// =============================================================================

export interface AuditLogEntry {
  id: string;
  organization_id: string | null;
  organization_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  entity_name: string | null;
  actor_type: string;
  actor_user_id: string | null;
  actor_display_name: string | null;
  actor_label: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogFilters {
  organization_id?: string;
  entity_type?: string;
  entity_id?: string;
  action?: string;
  actor_user_id?: string;
  start_date?: string;
  end_date?: string;
}

export interface AuditLogsParams {
  page?: number;
  page_size?: number;
  search?: string;
  filters?: AuditLogFilters;
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch audit logs for a specific organization.
 */
export function useOrgAuditLogs(orgId: string, options?: AuditLogsParams) {
  return useQuery({
    queryKey: ["audit-logs", "org", orgId, options],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (options?.page !== undefined) params.page = options.page;
      if (options?.page_size !== undefined) params.page_size = options.page_size;
      if (options?.search) params.search = options.search;
      if (options?.filters?.entity_type) params.entity_type = options.filters.entity_type;
      if (options?.filters?.entity_id) params.entity_id = options.filters.entity_id;
      if (options?.filters?.action) params.action = options.filters.action;
      if (options?.filters?.actor_user_id) params.actor_user_id = options.filters.actor_user_id;
      if (options?.filters?.start_date) params.start_date = options.filters.start_date;
      if (options?.filters?.end_date) params.end_date = options.filters.end_date;

      const response = await api.get<AuditLogListResponse>(
        `/api/organizations/${orgId}/audit-logs`,
        { params }
      );
      return response.data;
    },
    enabled: !!orgId,
    placeholderData: keepPreviousData,
  });
}

/**
 * Fetch global audit logs (across all organizations user has access to).
 */
export function useGlobalAuditLogs(options?: AuditLogsParams) {
  return useQuery({
    queryKey: ["audit-logs", "global", options],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (options?.page !== undefined) params.page = options.page;
      if (options?.page_size !== undefined) params.page_size = options.page_size;
      if (options?.search) params.search = options.search;
      if (options?.filters?.organization_id) params.organization_id = options.filters.organization_id;
      if (options?.filters?.entity_type) params.entity_type = options.filters.entity_type;
      if (options?.filters?.entity_id) params.entity_id = options.filters.entity_id;
      if (options?.filters?.action) params.action = options.filters.action;
      if (options?.filters?.actor_user_id) params.actor_user_id = options.filters.actor_user_id;
      if (options?.filters?.start_date) params.start_date = options.filters.start_date;
      if (options?.filters?.end_date) params.end_date = options.filters.end_date;

      const response = await api.get<AuditLogListResponse>("/api/audit-logs", { params });
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format action for display (capitalize, replace underscores).
 */
export function formatAction(action: string): string {
  return action
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Format entity type for display.
 */
export function formatEntityType(entityType: string): string {
  return entityType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Get color class for action type.
 */
export function getActionColor(action: string): string {
  switch (action) {
    case "create":
      return "text-green-600 dark:text-green-400";
    case "update":
      return "text-blue-600 dark:text-blue-400";
    case "delete":
      return "text-red-600 dark:text-red-400";
    case "view":
      return "text-amber-600 dark:text-amber-400";
    case "login":
    case "logout":
      return "text-purple-600 dark:text-purple-400";
    case "login_failed":
      return "text-red-600 dark:text-red-400";
    default:
      return "text-muted-foreground";
  }
}
