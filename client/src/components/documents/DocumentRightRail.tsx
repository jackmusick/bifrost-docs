import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Link2,
  Plus,
  X,
  Loader2,
  LinkIcon,
  Paperclip,
  Upload,
  Download,
  Trash2,
  FileIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { AddRelationshipDialog } from "@/components/relationships/AddRelationshipDialog";
import { TableOfContents } from "./TableOfContents";
import {
  useRelationships,
  useDeleteRelationship,
  groupRelationshipsByType,
  type ResolvedRelationship,
} from "@/hooks/useRelationships";
import {
  getEntityIcon,
  getEntityLabel,
  getEntityRoute,
  type EntityType,
} from "@/lib/entity-icons";
import api from "@/lib/api-client";
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

interface DocumentRightRailProps {
  orgId: string;
  documentId: string;
  content: string;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function DocumentRightRail({
  orgId,
  documentId,
  content,
}: DocumentRightRailProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Dialog states
  const [isAddRelationshipOpen, setIsAddRelationshipOpen] = useState(false);
  const [deleteAttachmentTarget, setDeleteAttachmentTarget] =
    useState<Attachment | null>(null);
  const [uploading, setUploading] = useState(false);

  // Relationships data
  const {
    data: relationshipsData,
    isLoading: relationshipsLoading,
    error: relationshipsError,
  } = useRelationships(orgId, "document", documentId);
  const deleteRelationship = useDeleteRelationship(orgId);

  const relationships = relationshipsData?.relationships ?? [];
  const groupedRelationships = groupRelationshipsByType(relationships);
  const entityTypes = Object.keys(groupedRelationships) as EntityType[];

  // Attachments data
  const { data: attachmentsData, isLoading: attachmentsLoading } = useQuery({
    queryKey: ["attachments", orgId, "document", documentId],
    queryFn: async () => {
      const response = await api.get<AttachmentListResponse>(
        `/api/organizations/${orgId}/attachments`,
        {
          params: { entity_type: "document", entity_id: documentId },
        }
      );
      return response.data;
    },
    enabled: !!orgId && !!documentId,
  });

  const deleteAttachmentMutation = useMutation({
    mutationFn: async (attachmentId: string) => {
      await api.delete(
        `/api/organizations/${orgId}/attachments/${attachmentId}`
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["attachments", orgId, "document", documentId],
      });
      setDeleteAttachmentTarget(null);
      toast.success("Attachment deleted");
    },
    onError: () => {
      toast.error("Failed to delete attachment");
    },
  });

  // Handlers
  const handleNavigateToRelated = (rel: ResolvedRelationship) => {
    const route = getEntityRoute(rel.entity.entity_type);
    let path: string;

    if (rel.entity.entity_type === "custom_asset" && rel.entity.asset_type_id) {
      path = `/org/${orgId}/${route}/${rel.entity.asset_type_id}/${rel.entity.id}`;
    } else {
      path = `/org/${orgId}/${route}/${rel.entity.id}`;
    }

    navigate(path);
  };

  const handleRemoveRelationship = async (
    rel: ResolvedRelationship,
    e: React.MouseEvent
  ) => {
    e.stopPropagation();
    try {
      await deleteRelationship.mutateAsync(rel.relationship.id);
      toast.success("Relationship removed");
    } catch {
      toast.error("Failed to remove relationship");
    }
  };

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
        entity_type: "document",
        entity_id: documentId,
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
        queryKey: ["attachments", orgId, "document", documentId],
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

  const handleDownloadAttachment = async (attachment: Attachment) => {
    try {
      const response = await api.get<{
        download_url: string;
        filename: string;
      }>(`/api/organizations/${orgId}/attachments/${attachment.id}/download`);

      window.open(response.data.download_url, "_blank");
    } catch (error) {
      console.error("Download error:", error);
      toast.error("Failed to download file");
    }
  };

  return (
    <aside className="hidden xl:block w-64 border-l border-border shrink-0">
      <div className="sticky top-0 p-4 space-y-6 max-h-screen overflow-y-auto">
        {/* Table of Contents */}
        <TableOfContents content={content} />

        {/* Related Items Section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Link2 className="h-4 w-4" />
              Related
            </h3>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setIsAddRelationshipOpen(true)}
            >
              <Plus className="h-4 w-4" />
              <span className="sr-only">Add relationship</span>
            </Button>
          </div>

          {relationshipsLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : relationshipsError ? (
            <p className="text-sm text-destructive">Failed to load</p>
          ) : relationships.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-4 text-center">
              <LinkIcon className="h-6 w-6 text-muted-foreground/50 mb-2" />
              <p className="text-xs text-muted-foreground">No related items</p>
            </div>
          ) : (
            <div className="space-y-3">
              {entityTypes.map((type) => {
                const Icon = getEntityIcon(type);
                const label = getEntityLabel(type);
                const rels = groupedRelationships[type];

                return (
                  <div key={type}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <Icon className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        {label}s
                      </span>
                      <Badge variant="secondary" className="ml-auto text-[10px] h-4 px-1">
                        {rels.length}
                      </Badge>
                    </div>
                    <div className="space-y-0.5">
                      {rels.map((rel) => (
                        <div
                          key={rel.relationship.id}
                          className="group flex items-center gap-2 rounded px-2 py-1 hover:bg-muted cursor-pointer transition-colors"
                          onClick={() => handleNavigateToRelated(rel)}
                        >
                          <span className="text-sm truncate flex-1">
                            {rel.entity.name}
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => handleRemoveRelationship(rel, e)}
                            disabled={deleteRelationship.isPending}
                          >
                            {deleteRelationship.isPending ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <X className="h-3 w-3" />
                            )}
                            <span className="sr-only">Remove</span>
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Attachments Section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Paperclip className="h-4 w-4" />
              Attachments
            </h3>
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
                size="sm"
                className="h-7 w-7 p-0"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                <span className="sr-only">Upload attachment</span>
              </Button>
            </div>
          </div>

          {attachmentsLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : !attachmentsData?.items.length ? (
            <div className="flex flex-col items-center justify-center py-4 text-center">
              <Paperclip className="h-6 w-6 text-muted-foreground/50 mb-2" />
              <p className="text-xs text-muted-foreground">No attachments</p>
            </div>
          ) : (
            <ScrollArea className="max-h-[200px]">
              <div className="space-y-1">
                {attachmentsData.items.map((attachment) => (
                  <div
                    key={attachment.id}
                    className="flex items-center gap-2 p-2 rounded hover:bg-muted transition-colors group"
                  >
                    <FileIcon className="h-4 w-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">{attachment.filename}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {formatFileSize(attachment.size_bytes)}
                      </p>
                    </div>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0"
                        onClick={() => handleDownloadAttachment(attachment)}
                      >
                        <Download className="h-3 w-3" />
                        <span className="sr-only">Download</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                        onClick={() => setDeleteAttachmentTarget(attachment)}
                      >
                        <Trash2 className="h-3 w-3" />
                        <span className="sr-only">Delete</span>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>
      </div>

      {/* Dialogs */}
      <AddRelationshipDialog
        open={isAddRelationshipOpen}
        onOpenChange={setIsAddRelationshipOpen}
        orgId={orgId}
        sourceEntityType="document"
        sourceEntityId={documentId}
      />

      <ConfirmDialog
        open={!!deleteAttachmentTarget}
        onOpenChange={(open) => !open && setDeleteAttachmentTarget(null)}
        title="Delete Attachment"
        description={`Are you sure you want to delete "${deleteAttachmentTarget?.filename}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() =>
          deleteAttachmentTarget &&
          deleteAttachmentMutation.mutate(deleteAttachmentTarget.id)
        }
        loading={deleteAttachmentMutation.isPending}
      />
    </aside>
  );
}
