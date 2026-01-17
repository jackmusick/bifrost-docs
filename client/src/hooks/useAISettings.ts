import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  aiSettingsApi,
  type AITestRequest,
  type CompletionsConfigUpdate,
  type EmbeddingsConfigUpdate,
} from "@/lib/api-client";

export function useAISettings() {
  return useQuery({
    queryKey: ["ai-settings"],
    queryFn: () => aiSettingsApi.get().then((r) => r.data),
  });
}

/**
 * Hook to check AI configuration status.
 * Returns whether AI is configured (completions API key is set)
 * and whether indexing is enabled (embeddings API key is set).
 */
export function useAIConfig() {
  const { data: settings, isLoading } = useAISettings();

  // AI is configured if completions API key is set
  const isConfigured = settings?.completions?.api_key_set === true;

  // Indexing is enabled if embeddings API key is set
  const isIndexingEnabled = settings?.embeddings?.api_key_set === true;

  return {
    isConfigured,
    isIndexingEnabled,
    isLoading,
  };
}

export function useUpdateCompletionsConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CompletionsConfigUpdate) =>
      aiSettingsApi.updateCompletions(data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
    },
  });
}

export function useUpdateEmbeddingsConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: EmbeddingsConfigUpdate) =>
      aiSettingsApi.updateEmbeddings(data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
    },
  });
}

export function useTestAIConnection() {
  return useMutation({
    mutationFn: (data: AITestRequest) =>
      aiSettingsApi.testConnection(data).then((r) => r.data),
  });
}
