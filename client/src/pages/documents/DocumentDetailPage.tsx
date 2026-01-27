import { useState, useEffect } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { FileText, Pencil, Trash2, Check, Sparkles } from "lucide-react";
import { formatRelativeTime } from "@/lib/date-utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { TiptapEditor } from "@/components/documents/TiptapEditor";
import { DocumentRightRail } from "@/components/documents/DocumentRightRail";
import { useHeadingIds } from "@/hooks/useHeadingIds";
import { SectionPicker } from "@/components/documents/SectionPicker";
import { usePermissions } from "@/hooks/usePermissions";
import {
  useDocument,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  useCleanDocument,
} from "@/hooks/useDocuments";
import { toast } from "sonner";

interface EditState {
  name: string;
  path: string;
  content: string;
}

export function DocumentDetailPage() {
  const { orgId, id } = useParams<{ orgId: string; id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const isNewDocument = id === "new";
  const defaultPath = searchParams.get("path") || "/";

  // Edit state is null when not editing, or contains edited values when editing
  const [editState, setEditState] = useState<EditState | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const { canEdit } = usePermissions();

  // Initialize edit state when navigating to new document
  // This handles both initial mount and navigation from existing document to new
  // Safe: setEditState doesn't modify isNewDocument or defaultPath, so no infinite loop
  /* eslint-disable react-compiler/react-compiler */
  useEffect(() => {
    if (isNewDocument) {
      setEditState({ name: "", path: defaultPath, content: "" });
    } else {
      setEditState(null);
    }
  }, [isNewDocument, defaultPath]);
  /* eslint-enable react-compiler/react-compiler */

  const { data: document, isLoading } = useDocument(orgId!, id!, {
    enabled: !isNewDocument,
  });
  const createDocument = useCreateDocument(orgId!);
  const updateDocument = useUpdateDocument(orgId!, id!);
  const deleteDocument = useDeleteDocument(orgId!, () => {
    // Navigate in onSuccess callback BEFORE cache removal to prevent stale query refetch
    navigate(`/org/${orgId}/documents`);
  });
  const cleanDocument = useCleanDocument(orgId!, id!);

  // Determine display content early for hook - must be before any early returns
  const displayContent = editState?.content ?? document?.content ?? "";

  // Inject heading IDs for table of contents - must be called unconditionally
  useHeadingIds(displayContent);

  if (!orgId || !id) {
    return null;
  }

  const isEditing = editState !== null;

  const handleStartEdit = () => {
    if (document) {
      setEditState({
        name: document.name,
        path: document.path,
        content: document.content || "",
      });
    }
  };

  const handleCancelEdit = () => {
    if (isNewDocument) {
      navigate(`/org/${orgId}/documents`);
    } else {
      setEditState(null);
    }
  };

  const handleSave = async () => {
    if (!editState) return;

    if (!editState.name.trim()) {
      toast.error("Document name is required");
      return;
    }

    try {
      if (isNewDocument) {
        const result = await createDocument.mutateAsync({
          name: editState.name.trim(),
          path: editState.path || "/",
          content: editState.content,
        });
        toast.success("Document created successfully");
        navigate(`/org/${orgId}/documents/${result.id}`, { replace: true });
      } else {
        await updateDocument.mutateAsync({
          name: editState.name.trim(),
          path: editState.path || "/",
          content: editState.content,
        });
        setEditState(null);
        toast.success("Document saved successfully");
      }
    } catch {
      toast.error(isNewDocument ? "Failed to create document" : "Failed to save document");
    }
  };

  const handleDelete = async () => {
    try {
      await deleteDocument.mutateAsync(id);
      toast.success("Document deleted successfully");
      // Navigation already happened in onSuccess callback
    } catch {
      toast.error("Failed to delete document");
    }
  };

  const handleToggleEnabled = async (checked: boolean) => {
    try {
      await updateDocument.mutateAsync({ is_enabled: checked });
      toast.success(checked ? "Document enabled" : "Document disabled");
    } catch {
      toast.error("Failed to update document");
    }
  };

  const handleClean = async () => {
    try {
      const result = await cleanDocument.mutateAsync();
      // Enter edit mode with cleaned content and suggested name
      setEditState({
        name: result.suggested_name ?? document?.name ?? "",
        path: document?.path ?? "/",
        content: result.cleaned_content,
      });
      toast.success(`Document cleaned: ${result.summary}`);
    } catch {
      toast.error("Failed to clean document");
    }
  };

  const isSaving = createDocument.isPending || updateDocument.isPending;

  if (isLoading && !isNewDocument) {
    return (
      <div className="flex h-full">
        <div className="flex-1 px-6 py-4">
          <div className="space-y-4">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
        <aside className="w-64 shrink-0 hidden lg:block border-l p-4 space-y-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </aside>
      </div>
    );
  }

  if (!document && !isNewDocument) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <FileText className="h-10 w-10 text-muted-foreground/50 mx-auto mb-3" />
          <h2 className="text-lg font-medium mb-1">Document not found</h2>
          <p className="text-sm text-muted-foreground">
            The document may have been deleted.
          </p>
        </div>
      </div>
    );
  }

  // Display values: use edit state when editing, otherwise use document data
  const displayName = isEditing ? editState.name : document?.name || "";

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main Content Column - independent scroll */}
      <div className="flex-1 overflow-auto">
        {/* Top bar with actions */}
        <div className="flex items-center justify-between px-6 py-3 border-b">
          <div className="min-w-0 flex-1 mr-4">
            {isEditing ? (
              <Input
                value={editState.name}
                onChange={(e) => setEditState({ ...editState, name: e.target.value })}
                placeholder="Document name"
                className="text-lg font-semibold h-8 w-full"
                autoFocus={isNewDocument}
              />
            ) : (
              <>
                <h1 className="text-lg font-semibold truncate">{displayName}</h1>
                {document?.updated_at && (
                  <p className="text-xs text-muted-foreground">
                    Last updated{document.updated_by_user_name ? ` by ${document.updated_by_user_name}` : ""} {formatRelativeTime(document.updated_at)}
                  </p>
                )}
              </>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {isEditing ? (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={isSaving}
                >
                  <Check className="mr-1 h-4 w-4" />
                  {isSaving ? "Saving..." : "Save"}
                </Button>
              </>
            ) : canEdit ? (
              <>
                {!isNewDocument && (
                  <div className="flex items-center gap-2">
                    <Switch
                      key={document?.updated_at}
                      checked={document?.is_enabled ?? true}
                      onCheckedChange={handleToggleEnabled}
                      disabled={updateDocument.isPending}
                    />
                    <span className="text-xs text-muted-foreground">
                      {document?.is_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                )}
                {!isNewDocument && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleClean}
                    disabled={cleanDocument.isPending}
                  >
                    <Sparkles className="mr-1 h-3.5 w-3.5" />
                    {cleanDocument.isPending ? "Cleaning..." : "Clean"}
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleStartEdit}
                >
                  <Pencil className="mr-1 h-3.5 w-3.5" />
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setDeleteOpen(true)}
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                  Delete
                </Button>
              </>
            ) : null}
          </div>
        </div>

        {/* Document content */}
        <div className="px-6 py-4">
          {/* Disabled Banner */}
          {!isNewDocument && !isEditing && document && !document.is_enabled && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>
                This document is disabled and won't appear in search
              </AlertDescription>
            </Alert>
          )}

          {/* Section picker when editing */}
          {isEditing && (
            <div className="mb-4">
              <SectionPicker
                orgId={orgId!}
                value={editState.path}
                onChange={(path) => setEditState({ ...editState, path })}
                className="h-8 text-sm max-w-xs"
              />
            </div>
          )}

          {/* Content section with data-document-content for heading ID injection */}
          <div
            data-document-content
            className={document && !document.is_enabled && !isEditing ? "opacity-60" : ""}
          >
            {isEditing ? (
              <TiptapEditor
                content={editState.content}
                onChange={(content) => setEditState({ ...editState, content })}
                readOnly={false}
                orgId={orgId}
              />
            ) : displayContent ? (
              <TiptapEditor
                content={displayContent}
                readOnly
                orgId={orgId}
                className="border-none"
              />
            ) : (
              <div className="py-8 text-center">
                <p className="text-sm text-muted-foreground italic">
                  No content yet
                </p>
                {canEdit && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={handleStartEdit}
                  >
                    <Pencil className="mr-1 h-3.5 w-3.5" />
                    Add Content
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Rail - only for existing documents */}
      {!isNewDocument && id && (
        <DocumentRightRail
          orgId={orgId}
          documentId={id}
          content={displayContent}
        />
      )}

      {/* Delete Confirmation */}
      {!isNewDocument && document && (
        <ConfirmDialog
          open={deleteOpen}
          onOpenChange={setDeleteOpen}
          title="Delete Document"
          description={`Are you sure you want to delete "${document.name}"? This action cannot be undone.`}
          confirmLabel="Delete"
          variant="destructive"
          onConfirm={handleDelete}
          loading={deleteDocument.isPending}
        />
      )}
    </div>
  );
}
