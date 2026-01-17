import React from 'react';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';

interface DocumentPreviewProps {
  content: string;
  summary: string;
}

export const DocumentPreview: React.FC<DocumentPreviewProps> = ({ content, summary }) => {
  return (
    <div className="document-preview border rounded-lg p-4 space-y-4 bg-muted/30">
      <div className="preview-summary">
        <strong className="text-sm font-semibold">Changes Summary:</strong>
        <p className="text-sm text-muted-foreground mt-1">{summary}</p>
      </div>

      <div className="preview-content">
        <strong className="text-sm font-semibold">Preview:</strong>
        <div className="markdown-preview mt-2 border rounded-md bg-background p-3 max-h-[400px] overflow-y-auto">
          <MarkdownRenderer content={content} />
        </div>
      </div>
    </div>
  );
};
