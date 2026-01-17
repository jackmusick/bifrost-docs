import { useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Paperclip,
  Download,
  Trash2,
  Upload,
  Loader2,
  FileIcon,
} from "lucide-react";
import api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ConfirmDialog } from "./ConfirmDialog";
import { toast } from "sonner";

interface Attachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

interface AttachmentListResponse {
  items: Attachment[];
  total: number;
}

interface EntityAttachmentsProps {
  entityType: string;
  entityId: string;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function EntityAttachments({
  entityType,
  entityId,
}: EntityAttachmentsProps) {
  const { orgId } = useParams<{ orgId: string }>();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Attachment | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["attachments", orgId, entityType, entityId],
    queryFn: async () => {
      const response = await api.get<AttachmentListResponse>(
        `/api/organizations/${orgId}/attachments`,
        {
          params: { entity_type: entityType, entity_id: entityId },
        }
      );
      return response.data;
    },
    enabled: !!orgId && !!entityId,
  });

  const deleteAttachment = useMutation({
    mutationFn: async (attachmentId: string) => {
      await api.delete(
        `/api/organizations/${orgId}/attachments/${attachmentId}`
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["attachments", orgId, entityType, entityId],
      });
      setDeleteTarget(null);
      toast.success("Attachment deleted");
    },
    onError: () => {
      toast.error("Failed to delete attachment");
    },
  });

  const handleFileSelect = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      // 1. Create attachment record and get presigned URL
      const createResponse = await api.post<{
        id: string;
        upload_url: string;
      }>(`/api/organizations/${orgId}/attachments`, {
        entity_type: entityType,
        entity_id: entityId,
        filename: file.name,
        content_type: file.type || "application/octet-stream",
        size_bytes: file.size,
      });

      // 2. Upload file to presigned URL
      await fetch(createResponse.data.upload_url, {
        method: "PUT",
        body: file,
        headers: {
          "Content-Type": file.type || "application/octet-stream",
        },
      });

      queryClient.invalidateQueries({
        queryKey: ["attachments", orgId, entityType, entityId],
      });
      toast.success("File uploaded successfully");
    } catch (error) {
      console.error("Upload error:", error);
      toast.error("Failed to upload file");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDownload = async (attachment: Attachment) => {
    try {
      const response = await api.get<{
        download_url: string;
        filename: string;
      }>(`/api/organizations/${orgId}/attachments/${attachment.id}/download`);

      // Open download URL in new tab
      window.open(response.data.download_url, "_blank");
    } catch (error) {
      console.error("Download error:", error);
      toast.error("Failed to download file");
    }
  };

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Paperclip className="h-4 w-4" />
              Attachments
            </CardTitle>
            <div>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileSelect}
                disabled={uploading}
              />
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : !data?.items.length ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No attachments
            </p>
          ) : (
            <ScrollArea className="h-[200px]">
              <div className="space-y-2">
                {data.items.map((attachment) => (
                  <div
                    key={attachment.id}
                    className="flex items-center gap-2 p-2 rounded-md hover:bg-muted transition-colors group"
                  >
                    <FileIcon className="h-4 w-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">{attachment.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatFileSize(attachment.size_bytes)}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleDownload(attachment)}
                      >
                        <Download className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive"
                        onClick={() => setDeleteTarget(attachment)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete Attachment"
        description={`Are you sure you want to delete "${deleteTarget?.filename}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => deleteTarget && deleteAttachment.mutate(deleteTarget.id)}
        loading={deleteAttachment.isPending}
      />
    </>
  );
}
