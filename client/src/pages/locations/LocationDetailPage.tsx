import { useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { MapPin, ArrowLeft, Trash2, FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { TiptapEditor } from "@/components/documents/TiptapEditor";
import { RelatedItemsSidebar } from "@/components/relationships/RelatedItemsSidebar";
import { EntityAttachments, ConfirmDialog, EditModeActions } from "@/components/shared";
import { usePermissions } from "@/hooks/usePermissions";
import { useInlineEdit } from "@/hooks/useInlineEdit";
import { useUnsavedChangesWarning } from "@/hooks/useUnsavedChangesWarning";
import {
  useLocation,
  useUpdateLocation,
  useDeleteLocation,
  type LocationUpdate,
} from "@/hooks/useLocations";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const locationSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  notes: z.string().optional(),
});

type LocationFormValues = z.infer<typeof locationSchema>;

export function LocationDetailPage() {
  const { orgId, id } = useParams<{ orgId: string; id: string }>();
  const navigate = useNavigate();
  const { canEdit } = usePermissions();

  const { data: location, isLoading } = useLocation(orgId!, id!);
  const updateLocation = useUpdateLocation(orgId!, id!);
  const deleteLocation = useDeleteLocation(orgId!, () => {
    // Navigate in onSuccess callback BEFORE cache removal to prevent stale query refetch
    navigate(`/org/${orgId}/locations`);
  });

  // Memoize initial data before any early returns
  const initialData = useMemo((): LocationFormValues => {
    if (!location) {
      return {
        name: "",
        notes: "",
      };
    }
    return {
      name: location.name,
      notes: location.notes ?? "",
    };
  }, [location]);

  const {
    isEditing,
    isDirty,
    isSaving,
    form,
    startEditing,
    cancelEditing,
    saveChanges,
  } = useInlineEdit<LocationFormValues>({
    resolver: zodResolver(locationSchema),
    initialData,
    onSave: async (data) => {
      const updateData: LocationUpdate = {
        name: data.name,
      };
      if (data.notes) updateData.notes = data.notes;
      await updateLocation.mutateAsync(updateData);
      toast.success("Location updated successfully");
    },
  });

  useUnsavedChangesWarning(isDirty && isEditing);

  // Dialog state for delete
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (!orgId || !id) {
    return null;
  }

  const handleDelete = async () => {
    try {
      await deleteLocation.mutateAsync(id);
      toast.success("Location deleted successfully");
      // Navigation already happened in onSuccess callback
    } catch {
      toast.error("Failed to delete location");
    }
  };

  const handleToggleEnabled = async (checked: boolean) => {
    try {
      await updateLocation.mutateAsync({ is_enabled: checked });
      toast.success(checked ? "Location enabled" : "Location disabled");
    } catch {
      toast.error("Failed to update location");
    }
  };

  if (isLoading) {
    return (
      <div className="flex gap-6">
        <div className="flex-1 space-y-6">
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Card>
            <CardContent className="p-6 space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-20 w-full" />
            </CardContent>
          </Card>
        </div>
        <aside className="w-80 shrink-0 hidden lg:block space-y-4">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </aside>
      </div>
    );
  }

  if (!location) {
    return (
      <div className="text-center py-12">
        <MapPin className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Location not found</h2>
        <p className="text-sm text-muted-foreground mb-4">
          The location you're looking for doesn't exist or has been deleted.
        </p>
        <Button asChild variant="outline">
          <Link to={`/org/${orgId}/locations`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Locations
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      <div className={`flex-1 space-y-6${location.is_enabled ? "" : " opacity-60"}`}>
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Link
                to={`/org/${orgId}/locations`}
                className="hover:text-foreground transition-colors"
              >
                Locations
              </Link>
              <span>/</span>
              <span>{location.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <MapPin className="h-5 w-5 text-primary" />
              </div>
              <div>
                {isEditing ? (
                  <Controller
                    control={form.control}
                    name="name"
                    render={({ field, fieldState }) => (
                      <div>
                        <Input
                          {...field}
                          className="text-2xl font-bold h-auto py-1"
                          placeholder="Location name"
                        />
                        {fieldState.error && (
                          <p className="text-sm text-destructive mt-1">{fieldState.error.message}</p>
                        )}
                      </div>
                    )}
                  />
                ) : (
                  <h1 className="text-2xl font-bold tracking-tight">
                    {location.name}
                  </h1>
                )}
                <p className="text-sm text-muted-foreground">
                  Last updated {new Date(location.updated_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
          {canEdit && (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 mr-2">
                <Switch
                  key={location.updated_at}
                  checked={location.is_enabled}
                  onCheckedChange={handleToggleEnabled}
                  disabled={updateLocation.isPending || isEditing}
                />
                <span className="text-sm text-muted-foreground">
                  {location.is_enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <EditModeActions
                isEditing={isEditing}
                isSaving={isSaving}
                isDirty={isDirty}
                onEdit={startEditing}
                onSave={saveChanges}
                onCancel={cancelEditing}
              />
              {!isEditing && (
                <Button
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setDeleteOpen(true)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Disabled Banner */}
        {!location.is_enabled && (
          <Alert variant="destructive">
            <AlertDescription>
              This location has been disabled and will not appear in search or lists
            </AlertDescription>
          </Alert>
        )}

        {/* Notes */}
        <Card className={cn(isEditing && "ring-2 ring-primary/20")}>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Notes
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <Controller
                control={form.control}
                name="notes"
                render={({ field }) => (
                  <TiptapEditor
                    content={field.value ?? ""}
                    onChange={field.onChange}
                    orgId={orgId}
                    placeholder="Additional notes about this location..."
                    className="min-h-[120px]"
                  />
                )}
              />
            ) : location.notes ? (
              <div
                className="prose prose-sm max-w-none dark:prose-invert"
                dangerouslySetInnerHTML={{ __html: location.notes }}
              />
            ) : (
              <p className="text-sm text-muted-foreground italic">No notes</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Sidebar */}
      <aside className="w-80 shrink-0 hidden lg:block space-y-4">
        <RelatedItemsSidebar orgId={orgId} entityType="location" entityId={id} />
        <EntityAttachments entityType="location" entityId={id} />
      </aside>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Location"
        description={`Are you sure you want to delete "${location.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteLocation.isPending}
      />
    </div>
  );
}
