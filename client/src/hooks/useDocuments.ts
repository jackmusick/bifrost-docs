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

export interface Document {
  id: string;
  organization_id: string;
  path: string;
  name: string;
  content: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
  updated_by_user_id: string | null;
  updated_by_user_name: string | null;
}

export interface FolderCount {
  path: string;
  count: number;
}

export interface FolderList {
  folders: FolderCount[];
}

export interface DocumentCreate {
  path: string;
  name: string;
  content: string;
  is_enabled?: boolean;
}

export interface DocumentUpdate {
  path?: string;
  name?: string;
  content?: string;
  is_enabled?: boolean;
}

export interface BatchPathUpdateRequest {
  old_path_prefix: string;
  new_path_prefix: string;
  merge_if_exists?: boolean;
}

export interface BatchPathUpdateResponse {
  updated_count: number;
  conflicts: string[];
}

// =============================================================================
// Hooks
// =============================================================================

export function useDocuments(
  orgId: string,
  options?: {
    path?: string;
    pagination?: PaginationParams;
    search?: string;
    showDisabled?: boolean;
  }
) {
  return useQuery({
    queryKey: ["documents", orgId, options],
    queryFn: async () => {
      const params: Record<string, string | number | boolean> = {};
      if (options?.path !== undefined) params.path = options.path;
      if (options?.pagination?.limit !== undefined) params.limit = options.pagination.limit;
      if (options?.pagination?.offset !== undefined) params.offset = options.pagination.offset;
      if (options?.search) params.search = options.search;
      if (options?.showDisabled !== undefined) params.show_disabled = options.showDisabled;

      const response = await api.get<PaginatedResponse<Document>>(
        `/api/organizations/${orgId}/documents`,
        { params }
      );
      return response.data;
    },
    enabled: !!orgId,
    placeholderData: keepPreviousData,
  });
}

export function useFolders(orgId: string) {
  return useQuery({
    queryKey: ["documents", "folders", orgId],
    queryFn: async () => {
      const response = await api.get<FolderList>(
        `/api/organizations/${orgId}/documents/folders`
      );
      return response.data;
    },
    enabled: !!orgId,
  });
}

export function useDocument(
  orgId: string,
  id: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: ["documents", orgId, "detail", id],
    queryFn: async () => {
      const response = await api.get<Document>(
        `/api/organizations/${orgId}/documents/${id}`
      );
      return response.data;
    },
    enabled: (options?.enabled ?? true) && !!orgId && !!id,
  });
}

export function useCreateDocument(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DocumentCreate) => {
      const response = await api.post<Document>(
        `/api/organizations/${orgId}/documents`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useUpdateDocument(orgId: string, id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DocumentUpdate) => {
      const response = await api.put<Document>(
        `/api/organizations/${orgId}/documents/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useDeleteDocument(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/organizations/${orgId}/documents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useBatchToggleDocuments(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ids, isEnabled }: { ids: string[]; isEnabled: boolean }) => {
      const response = await api.patch<{ updated_count: number }>(
        `/api/organizations/${orgId}/documents/batch/toggle`,
        { ids, is_enabled: isEnabled }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useBatchUpdatePaths(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BatchPathUpdateRequest) => {
      const response = await api.patch<BatchPathUpdateResponse>(
        `/api/organizations/${orgId}/documents/batch/paths`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

export function useMoveDocument(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      documentId,
      newPath,
    }: {
      documentId: string;
      newPath: string;
    }) => {
      const response = await api.put<Document>(
        `/api/organizations/${orgId}/documents/${documentId}`,
        { path: newPath }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}

// Build folder tree from flat list of paths with counts
export interface FolderNode {
  name: string;
  path: string;
  count: number;
  children: FolderNode[];
}

export function buildFolderTree(folders: FolderCount[]): FolderNode[] {
  const root: FolderNode[] = [];
  // Map for quick lookup of counts by path
  const countMap = new Map(folders.map((f) => [f.path, f.count]));

  for (const folder of folders) {
    const parts = folder.path.split("/").filter(Boolean);
    let currentLevel = root;
    let currentPath = "";

    for (const part of parts) {
      currentPath = currentPath ? `${currentPath}/${part}` : `/${part}`;
      let existing = currentLevel.find((n) => n.name === part);

      if (!existing) {
        existing = {
          name: part,
          path: currentPath,
          count: countMap.get(currentPath) ?? 0,
          children: [],
        };
        currentLevel.push(existing);
      }

      currentLevel = existing.children;
    }
  }

  return root;
}
