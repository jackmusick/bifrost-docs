import React, { useState } from 'react';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
import { DocumentPreview } from './DocumentPreview';
import { AssetFieldDiff } from './AssetFieldDiff';
import { Button } from '@/components/ui/button';
import api from '@/lib/api-client';

interface MutationPreviewData {
  entity_type: 'document' | 'custom_asset';
  entity_id: string;
  organization_id: string;
  mutation: {
    content?: string;
    field_updates?: Record<string, string>;
    summary: string;
  };
}

interface MutationPreviewProps {
  data: MutationPreviewData;
  conversationId: string;
  requestId: string;
  onApply: (success: boolean, link?: string) => void;
}

export const MutationPreview: React.FC<MutationPreviewProps> = ({
  data,
  conversationId,
  requestId,
  onApply,
}) => {
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultLink, setResultLink] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const location = useLocation();

  const handleApply = async () => {
    setApplying(true);
    setError(null);

    try {
      const response = await api.post('/api/search/chat/apply', {
        conversation_id: conversationId,
        request_id: requestId,
        entity_type: data.entity_type,
        entity_id: data.entity_id,
        organization_id: data.organization_id,
        mutation: data.mutation,
      });

      setApplied(true);
      setResultLink(response.data.link);

      // Check if we're currently on the mutated entity's page
      const entityPath = `/org/${data.organization_id}/${
        data.entity_type === 'document' ? 'documents' : 'custom-assets'
      }/${data.entity_id}`;
      const isOnEntityPage = location.pathname === entityPath;

      if (isOnEntityPage) {
        // Invalidate the query to trigger a refetch
        if (data.entity_type === 'document') {
          await queryClient.invalidateQueries({
            queryKey: ['documents', data.organization_id, 'detail', data.entity_id],
          });
        } else {
          // For custom assets, invalidate all queries for this org since we don't have typeId
          await queryClient.invalidateQueries({
            queryKey: ['custom-assets', data.organization_id],
          });
        }
      }

      onApply(true, response.data.link);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      onApply(false);
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="mutation-preview space-y-3">
      {data.entity_type === 'document' && data.mutation.content && (
        <DocumentPreview
          content={data.mutation.content}
          summary={data.mutation.summary}
        />
      )}

      {data.entity_type === 'custom_asset' && data.mutation.field_updates && (
        <AssetFieldDiff
          fieldUpdates={data.mutation.field_updates}
          summary={data.mutation.summary}
        />
      )}

      <div className="mutation-actions flex items-center gap-2">
        {!applied && !error && (
          <Button
            onClick={handleApply}
            disabled={applying}
            size="sm"
            className="btn-apply"
          >
            {applying ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Applying...
              </>
            ) : (
              'Apply Changes'
            )}
          </Button>
        )}

        {applied && resultLink && (
          <div className="applied-success flex items-center gap-2 text-sm text-green-600 dark:text-green-500">
            <CheckCircle2 className="h-4 w-4" />
            <span>
              {location.pathname === `/org/${data.organization_id}/${
                data.entity_type === 'document' ? 'documents' : 'custom-assets'
              }/${data.entity_id}`
                ? 'Applied and reloaded'
                : 'Applied'}
            </span>
            {location.pathname !== `/org/${data.organization_id}/${
              data.entity_type === 'document' ? 'documents' : 'custom-assets'
            }/${data.entity_id}` && (
              <a
                href={resultLink}
                className="entity-link text-primary hover:underline font-medium"
              >
                View updated entity
              </a>
            )}
          </div>
        )}

        {error && (
          <div className="apply-error flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            <span>Error: {error}</span>
          </div>
        )}
      </div>
    </div>
  );
};
