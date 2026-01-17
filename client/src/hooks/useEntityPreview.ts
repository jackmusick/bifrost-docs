import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { EntityType } from "@/lib/entity-icons";

export interface EntityPreviewData {
  id: string;
  name: string;
  content: string;
  entity_type: EntityType;
  organization_id: string;
}

export function useEntityPreview(
  entityType: EntityType | null,
  entityId: string | null,
  organizationId: string | null
) {
  return useQuery({
    queryKey: ["entity-preview", entityType, entityId, organizationId],
    queryFn: async () => {
      if (!entityType || !entityId || !organizationId) return null;

      const endpointMap: Record<EntityType, string> = {
        password: "passwords",
        configuration: "configurations",
        location: "locations",
        document: "documents",
        custom_asset: "custom-assets",
      };

      const endpoint = endpointMap[entityType];
      if (!endpoint) return null;

      const response = await api.get<EntityPreviewData>(
        `/api/org/${organizationId}/${endpoint}/${entityId}/preview`
      );
      return response.data;
    },
    enabled: !!entityType && !!entityId && !!organizationId,
    staleTime: 60000,
  });
}
