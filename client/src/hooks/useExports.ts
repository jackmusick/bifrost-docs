/**
 * useExports Hook
 *
 * React Query hooks for managing data exports.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { exportsApi, type CreateExportRequest } from "@/lib/api-client";

/**
 * Fetch list of exports for the current user
 */
export function useExports() {
  return useQuery({
    queryKey: ["exports"],
    queryFn: () => exportsApi.list().then((r) => r.data),
  });
}

/**
 * Fetch a single export by ID
 */
export function useExport(id: string | null) {
  return useQuery({
    queryKey: ["exports", id],
    queryFn: () => exportsApi.get(id!).then((r) => r.data),
    enabled: !!id,
  });
}

/**
 * Create a new export
 */
export function useCreateExport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateExportRequest) =>
      exportsApi.create(data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["exports"] });
    },
  });
}

/**
 * Get presigned download URL for an export
 */
export function useExportDownloadUrl(id: string | null) {
  return useQuery({
    queryKey: ["exports", id, "download"],
    queryFn: () => exportsApi.getDownloadUrl(id!).then((r) => r.data),
    enabled: false, // Only fetch when explicitly requested
  });
}

/**
 * Revoke an export
 */
export function useRevokeExport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => exportsApi.revoke(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["exports"] });
    },
  });
}
