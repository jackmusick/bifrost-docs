import { useQuery } from "@tanstack/react-query";
import { useState, useCallback, useRef, useEffect } from "react";
import api from "@/lib/api-client";
import type { EntityType } from "@/lib/entity-icons";
import { webSocketService, type SearchChunk } from "@/services/websocket";

export interface SearchResult {
  entity_id: string;
  entity_type: EntityType;
  organization_id: string;
  organization_name: string;
  name: string;
  snippet: string;
  updated_at: string;
  is_enabled: boolean;
  // For custom assets
  asset_type_id?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

export interface GroupedSearchResults {
  [organizationName: string]: {
    organizationId: string;
    byType: {
      [entityType: string]: SearchResult[];
    };
  };
}

export function useSearch(query: string, options?: { orgId?: string; showDisabled?: boolean }) {
  const { orgId, showDisabled = false } = options || {};

  return useQuery({
    queryKey: ["search", query, orgId, showDisabled],
    queryFn: async () => {
      const params: Record<string, string | boolean> = { q: query };
      if (orgId) {
        params.org_id = orgId;
      }
      if (showDisabled) {
        params.show_disabled = true;
      }
      const response = await api.get<SearchResponse>("/api/search", { params });
      return response.data;
    },
    enabled: query.length >= 2,
    staleTime: 30000,
    placeholderData: (previousData) => previousData,
  });
}

export function groupSearchResults(results: SearchResult[]): GroupedSearchResults {
  const grouped: GroupedSearchResults = {};

  for (const result of results) {
    if (!grouped[result.organization_name]) {
      grouped[result.organization_name] = {
        organizationId: result.organization_id,
        byType: {},
      };
    }

    const orgGroup = grouped[result.organization_name];
    if (!orgGroup.byType[result.entity_type]) {
      orgGroup.byType[result.entity_type] = [];
    }

    orgGroup.byType[result.entity_type].push(result);
  }

  return grouped;
}

// =============================================================================
// AI Search (RAG) Hook - WebSocket Streaming
// =============================================================================

export interface AISearchCitation {
  entity_type: EntityType;
  entity_id: string;
  organization_id: string;
  name: string;
}

export interface AISearchState {
  isLoading: boolean;
  isStreaming: boolean;
  response: string;
  citations: AISearchCitation[];
  error: string | null;
}

interface AISearchStartResponse {
  request_id: string;
}

export function useAISearch() {
  const [state, setState] = useState<AISearchState>({
    isLoading: false,
    isStreaming: false,
    response: "",
    citations: [],
    error: null,
  });

  const requestIdRef = useRef<string | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, []);

  const handleSearchChunk = useCallback((chunk: SearchChunk) => {
    switch (chunk.type) {
      case "citations":
        if (chunk.data) {
          setState((prev) => ({
            ...prev,
            citations: chunk.data as AISearchCitation[],
          }));
        }
        break;

      case "delta":
        setState((prev) => ({
          ...prev,
          response: prev.response + (chunk.content || ""),
        }));
        break;

      case "done":
        setState((prev) => ({ ...prev, isStreaming: false }));
        break;

      case "error":
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: chunk.message || "An error occurred",
        }));
        break;
    }
  }, []);

  const search = useCallback(
    async (query: string, orgId?: string) => {
      // Cleanup previous subscription
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }

      setState({
        isLoading: true,
        isStreaming: false,
        response: "",
        citations: [],
        error: null,
      });

      try {
        // Start the AI search and get request_id
        const response = await api.post<AISearchStartResponse>("/api/search/ai", {
          query,
          ...(orgId ? { org_id: orgId } : {}),
        });

        const { request_id } = response.data;
        requestIdRef.current = request_id;

        // Connect to WebSocket and subscribe to search channel
        await webSocketService.connectToSearch(request_id);

        // Register callback for streaming chunks
        unsubscribeRef.current = webSocketService.onSearchChunk(
          request_id,
          handleSearchChunk
        );

        setState((prev) => ({ ...prev, isLoading: false, isStreaming: true }));
      } catch (error) {
        setState((prev) => ({
          ...prev,
          isLoading: false,
          isStreaming: false,
          error: (error as Error).message || "AI search failed",
        }));
      }
    },
    [handleSearchChunk]
  );

  const abort = useCallback(() => {
    // Unsubscribe from WebSocket channel
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }

    if (requestIdRef.current) {
      webSocketService.unsubscribe(`search:${requestIdRef.current}`);
      requestIdRef.current = null;
    }

    setState((prev) => ({
      ...prev,
      isLoading: false,
      isStreaming: false,
    }));
  }, []);

  const reset = useCallback(() => {
    abort();
    setState({
      isLoading: false,
      isStreaming: false,
      response: "",
      citations: [],
      error: null,
    });
  }, [abort]);

  return {
    ...state,
    search,
    abort,
    reset,
  };
}
