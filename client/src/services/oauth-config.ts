/**
 * OAuth SSO Configuration API service
 *
 * Manages OAuth SSO provider configurations (Microsoft, Google, OIDC)
 * stored in the database. Platform admin only.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";

// OAuth provider types
export type OAuthProvider = "microsoft" | "google" | "oidc";

export interface OAuthProviderConfig {
  provider: OAuthProvider;
  configured: boolean;
  client_id: string | null;
  client_secret_set: boolean;
  tenant_id?: string | null; // Microsoft only
  discovery_url?: string | null; // OIDC only
  display_name?: string | null; // OIDC only
}

export interface OAuthConfigListResponse {
  providers: OAuthProviderConfig[];
}

export interface OAuthConfigTestResponse {
  success: boolean;
  message: string;
}

export interface MicrosoftOAuthConfigRequest {
  client_id: string;
  client_secret: string;
  tenant_id?: string;
}

export interface GoogleOAuthConfigRequest {
  client_id: string;
  client_secret: string;
}

export interface OIDCConfigRequest {
  discovery_url: string;
  client_id: string;
  client_secret: string;
  display_name?: string;
}

/**
 * Hook to fetch all OAuth provider configurations
 */
export function useOAuthConfigs() {
  return useQuery({
    queryKey: ["oauth-configs"],
    queryFn: async () => {
      const response = await api.get<OAuthConfigListResponse>("/api/settings/oauth");
      return response.data;
    },
  });
}

/**
 * Hook to fetch a single OAuth provider configuration
 */
export function useOAuthConfig(provider: OAuthProvider) {
  return useQuery({
    queryKey: ["oauth-config", provider],
    queryFn: async () => {
      const response = await api.get<OAuthProviderConfig>(`/api/settings/oauth/${provider}`);
      return response.data;
    },
  });
}

/**
 * Hook to update Microsoft OAuth configuration
 */
export function useUpdateMicrosoftConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: MicrosoftOAuthConfigRequest) => {
      const response = await api.put<OAuthProviderConfig>("/api/settings/oauth/microsoft", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oauth-configs"] });
      queryClient.invalidateQueries({ queryKey: ["oauth-config", "microsoft"] });
      queryClient.invalidateQueries({ queryKey: ["oauth-providers"] });
    },
  });
}

/**
 * Hook to update Google OAuth configuration
 */
export function useUpdateGoogleConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: GoogleOAuthConfigRequest) => {
      const response = await api.put<OAuthProviderConfig>("/api/settings/oauth/google", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oauth-configs"] });
      queryClient.invalidateQueries({ queryKey: ["oauth-config", "google"] });
      queryClient.invalidateQueries({ queryKey: ["oauth-providers"] });
    },
  });
}

/**
 * Hook to update OIDC provider configuration
 */
export function useUpdateOIDCConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: OIDCConfigRequest) => {
      const response = await api.put<OAuthProviderConfig>("/api/settings/oauth/oidc", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oauth-configs"] });
      queryClient.invalidateQueries({ queryKey: ["oauth-config", "oidc"] });
      queryClient.invalidateQueries({ queryKey: ["oauth-providers"] });
    },
  });
}

/**
 * Hook to delete an OAuth provider configuration
 */
export function useDeleteOAuthConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (provider: OAuthProvider) => {
      await api.delete(`/api/settings/oauth/${provider}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oauth-configs"] });
      queryClient.invalidateQueries({ queryKey: ["oauth-config"] });
      queryClient.invalidateQueries({ queryKey: ["oauth-providers"] });
    },
  });
}

/**
 * Hook to test OAuth provider configuration
 */
export function useTestOAuthConfig() {
  return useMutation({
    mutationFn: async (provider: OAuthProvider) => {
      const response = await api.post<OAuthConfigTestResponse>(`/api/settings/oauth/${provider}/test`);
      return response.data;
    },
  });
}

// Domain Whitelist

export interface DomainWhitelistResponse {
  allowed_domain: string | null;
}

/**
 * Hook to fetch OAuth domain whitelist
 */
export function useDomainWhitelist() {
  return useQuery({
    queryKey: ["oauth-domain-whitelist"],
    queryFn: async () => {
      const response = await api.get<DomainWhitelistResponse>("/api/settings/oauth/domain-whitelist");
      return response.data;
    },
  });
}

/**
 * Hook to update OAuth domain whitelist
 */
export function useUpdateDomainWhitelist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (domain: string | null) => {
      const response = await api.put<DomainWhitelistResponse>(
        "/api/settings/oauth/domain-whitelist",
        { domain }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oauth-domain-whitelist"] });
    },
  });
}
