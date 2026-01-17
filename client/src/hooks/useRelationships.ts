import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { EntityType } from "@/lib/entity-icons";

export interface RelatedEntity {
  id: string;
  entity_type: EntityType;
  name: string;
  description?: string;
  // For custom assets
  asset_type_id?: string;
}

export interface Relationship {
  id: string;
  source_entity_type: EntityType;
  source_entity_id: string;
  target_entity_type: EntityType;
  target_entity_id: string;
  relationship_type: string;
  created_at: string;
}

export interface ResolvedRelationship {
  relationship: Relationship;
  entity: RelatedEntity;
  direction: "source" | "target";
}

export interface ResolvedRelationshipsResponse {
  relationships: ResolvedRelationship[];
}

export interface CreateRelationshipRequest {
  source_entity_type: EntityType;
  source_entity_id: string;
  target_entity_type: EntityType;
  target_entity_id: string;
  relationship_type?: string;
}

export function useRelationships(
  orgId: string,
  entityType: string,
  entityId: string
) {
  return useQuery({
    queryKey: ["relationships", orgId, entityType, entityId],
    queryFn: async () => {
      const response = await api.get<ResolvedRelationshipsResponse>(
        `/api/organizations/${orgId}/relationships/resolved`,
        {
          params: {
            entity_type: entityType,
            entity_id: entityId,
          },
        }
      );
      return response.data;
    },
    enabled: Boolean(orgId && entityType && entityId),
    staleTime: 30000,
  });
}

export function useCreateRelationship(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateRelationshipRequest) => {
      const response = await api.post<Relationship>(
        `/api/organizations/${orgId}/relationships`,
        data
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate both source and target entity relationship queries
      queryClient.invalidateQueries({
        queryKey: [
          "relationships",
          orgId,
          variables.source_entity_type,
          variables.source_entity_id,
        ],
      });
      queryClient.invalidateQueries({
        queryKey: [
          "relationships",
          orgId,
          variables.target_entity_type,
          variables.target_entity_id,
        ],
      });
    },
  });
}

export function useDeleteRelationship(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (relationshipId: string) => {
      await api.delete(`/api/organizations/${orgId}/relationships/${relationshipId}`);
    },
    onSuccess: () => {
      // Invalidate all relationship queries for this org
      queryClient.invalidateQueries({
        queryKey: ["relationships", orgId],
      });
    },
  });
}

export function groupRelationshipsByType(
  relationships: ResolvedRelationship[]
): Record<EntityType, ResolvedRelationship[]> {
  const grouped: Record<string, ResolvedRelationship[]> = {};

  for (const rel of relationships) {
    const type = rel.entity.entity_type;
    if (!grouped[type]) {
      grouped[type] = [];
    }
    grouped[type].push(rel);
  }

  return grouped as Record<EntityType, ResolvedRelationship[]>;
}
