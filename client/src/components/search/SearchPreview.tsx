import { Loader2, FileSearch } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { MarkdownRenderer } from "@/components/ui/markdown-renderer";
import { useEntityPreview } from "@/hooks/useEntityPreview";
import { entityIcons, getEntityLabel, type EntityType } from "@/lib/entity-icons";
import { cn } from "@/lib/utils";
import { HighlightedText } from "./HighlightedText";

interface SearchPreviewProps {
  entityType: EntityType | null;
  entityId: string | null;
  organizationId: string | null;
  highlightQuery?: string;
}

export function SearchPreview({
  entityType,
  entityId,
  organizationId,
  highlightQuery,
}: SearchPreviewProps) {
  const { data: preview, isLoading, error } = useEntityPreview(
    entityType,
    entityId,
    organizationId
  );

  // Empty state - nothing selected
  if (!entityType || !entityId || !organizationId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground py-8">
        <FileSearch className="h-10 w-10 mb-3 opacity-50" />
        <p className="text-sm">Select a result to preview</p>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading preview...</span>
      </div>
    );
  }

  // Error state
  if (error || !preview) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground py-8">
        <FileSearch className="h-10 w-10 mb-3 opacity-50" />
        <p className="text-sm">Preview not available</p>
      </div>
    );
  }

  return (
    <PreviewContent
      preview={preview}
      highlightQuery={highlightQuery}
    />
  );
}

interface PreviewContentProps {
  preview: {
    id: string;
    name: string;
    content: string;
    entity_type: EntityType;
    organization_id: string;
  };
  highlightQuery?: string;
}

function PreviewContent({ preview, highlightQuery }: PreviewContentProps) {
  const IconComponent = entityIcons[preview.entity_type];
  const label = getEntityLabel(preview.entity_type);

  return (
    <div className="flex flex-col h-full">
      {/* Preview header */}
      <div className="flex items-center gap-3 border-b px-4 py-3 shrink-0">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
          <IconComponent className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium truncate">
            <HighlightedText text={preview.name} highlight={highlightQuery} />
          </h3>
        </div>
        <Badge variant="secondary" className="shrink-0">
          {label}
        </Badge>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <div
          className={cn(
            "prose prose-sm dark:prose-invert max-w-none",
            "prose-p:my-2 prose-headings:my-3 prose-ul:my-2 prose-li:my-0.5",
            "[&_ul]:list-disc [&_ol]:list-decimal [&_ul]:pl-4 [&_ol]:pl-4"
          )}
        >
          <MarkdownRenderer content={preview.content} />
        </div>
      </div>
    </div>
  );
}

