import { useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import {
  Building2,
  ArrowLeft,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog, EditModeActions } from "@/components/shared";
import { usePermissions } from "@/hooks/usePermissions";
import { useInlineEdit } from "@/hooks/useInlineEdit";
import { useUnsavedChangesWarning } from "@/hooks/useUnsavedChangesWarning";
import {
  useOrganization,
  useUpdateOrganization,
  useDeleteOrganization,
} from "@/hooks/useOrganizations";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const organizationSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  metadata: z.string().optional(),
});

type OrganizationFormValues = z.infer<typeof organizationSchema>;

export function OrganizationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAdmin } = usePermissions();

  const { data: organization, isLoading } = useOrganization(id!);
  const updateOrganization = useUpdateOrganization();
  const deleteOrganization = useDeleteOrganization();

  // Memoize initial data before any early returns
  const initialData = useMemo((): OrganizationFormValues => {
    if (!organization) {
      return {
        name: "",
        metadata: "",
      };
    }
    return {
      name: organization.name,
      metadata: organization.metadata ? JSON.stringify(organization.metadata, null, 2) : "",
    };
  }, [organization]);

  const {
    isEditing,
    isDirty,
    isSaving,
    form,
    startEditing,
    cancelEditing,
    saveChanges,
  } = useInlineEdit<OrganizationFormValues>({
    resolver: zodResolver(organizationSchema),
    initialData,
    onSave: async (data) => {
      // Parse metadata if provided
      let metadata: Record<string, any> | undefined;
      if (data.metadata && data.metadata.trim()) {
        try {
          metadata = JSON.parse(data.metadata);
        } catch (error) {
          form.setError("metadata", {
            type: "manual",
            message: "Invalid JSON format",
          });
          throw new Error("Invalid JSON format");
        }
      }

      await updateOrganization.mutateAsync({
        id: id!,
        data: {
          name: data.name,
          ...(metadata && { metadata }),
        },
      });
      toast.success("Organization updated successfully");
    },
  });

  useUnsavedChangesWarning(isDirty && isEditing);

  // Dialog state for delete
  const [deleteOpen, setDeleteOpen] = useState(false);

  // Redirect non-admin users
  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <Building2 className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Access Denied</h2>
        <p className="text-sm text-muted-foreground mb-4">
          You don't have permission to view this page.
        </p>
        <Button asChild variant="outline">
          <Link to="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Link>
        </Button>
      </div>
    );
  }

  if (!id) {
    return null;
  }

  const handleDelete = async () => {
    try {
      await deleteOrganization.mutateAsync(id);
      toast.success("Organization deleted successfully");
      navigate("/admin/organizations");
    } catch {
      toast.error("Failed to delete organization");
    }
  };

  const handleToggleEnabled = async (checked: boolean) => {
    try {
      await updateOrganization.mutateAsync({
        id: id!,
        data: { is_enabled: checked },
      });
      toast.success(checked ? "Organization enabled" : "Organization disabled");
    } catch {
      toast.error("Failed to update organization");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Card>
          <CardContent className="p-6 space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className="text-center py-12">
        <Building2 className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Organization not found</h2>
        <p className="text-sm text-muted-foreground mb-4">
          The organization you're looking for doesn't exist or has been deleted.
        </p>
        <Button asChild variant="outline">
          <Link to="/admin/organizations">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Organizations
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex-1 min-w-0 overflow-y-auto">
      <div className="max-w-3xl mx-auto pb-8">
        <div className={`space-y-6${organization.is_enabled ? "" : " opacity-60"}`}>
          {/* Header */}
          <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
            <Link
              to="/admin/organizations"
              className="hover:text-foreground transition-colors"
            >
              Organizations
            </Link>
            <span>/</span>
            <span>{organization.name}</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Building2 className="h-5 w-5 text-primary" />
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
                        placeholder="Organization name"
                      />
                      {fieldState.error && (
                        <p className="text-sm text-destructive mt-1">{fieldState.error.message}</p>
                      )}
                    </div>
                  )}
                />
              ) : (
                <h1 className="text-2xl font-bold tracking-tight">
                  {organization.name}
                </h1>
              )}
              <p className="text-sm text-muted-foreground">
                Last updated {new Date(organization.updated_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 mr-2">
            <Switch
              key={organization.updated_at}
              checked={organization.is_enabled}
              onCheckedChange={handleToggleEnabled}
              disabled={updateOrganization.isPending || isEditing}
            />
            <span className="text-sm text-muted-foreground">
              {organization.is_enabled ? "Enabled" : "Disabled"}
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
      </div>

      {/* Disabled Banner */}
      {!organization.is_enabled && (
        <Alert variant="destructive">
          <AlertDescription>
            This organization has been disabled and will not appear in organization lists
          </AlertDescription>
        </Alert>
      )}

      {/* Details */}
      <Card className={cn(isEditing && "ring-2 ring-primary/20")}>
        <CardHeader>
          <CardTitle className="text-base">Organization Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Name */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">
              Name
            </label>
            {isEditing ? (
              <Controller
                control={form.control}
                name="name"
                render={({ field }) => (
                  <Input {...field} placeholder="Organization name" />
                )}
              />
            ) : (
              <p className="text-sm bg-muted px-3 py-2 rounded-md">
                {organization.name}
              </p>
            )}
          </div>

          {/* Metadata */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">
              Metadata (JSON)
            </label>
            {isEditing ? (
              <Controller
                control={form.control}
                name="metadata"
                render={({ field, fieldState }) => (
                  <div>
                    <Textarea
                      {...field}
                      placeholder='{"key": "value"}'
                      className="font-mono text-sm min-h-[120px]"
                    />
                    {fieldState.error && (
                      <p className="text-sm text-destructive mt-1">{fieldState.error.message}</p>
                    )}
                  </div>
                )}
              />
            ) : organization.metadata && Object.keys(organization.metadata).length > 0 ? (
              <pre className="text-sm font-mono bg-muted px-3 py-2 rounded-md overflow-x-auto">
                {JSON.stringify(organization.metadata, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-muted-foreground italic">No metadata</p>
            )}
          </div>

          <Separator />

          {/* Read-only fields */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">
                Created At
              </label>
              <p className="text-sm bg-muted px-3 py-2 rounded-md">
                {new Date(organization.created_at).toLocaleString()}
              </p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">
                Updated At
              </label>
              <p className="text-sm bg-muted px-3 py-2 rounded-md">
                {new Date(organization.updated_at).toLocaleString()}
              </p>
            </div>
          </div>

          {organization.updated_by_user_name && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">
                Updated By
              </label>
              <p className="text-sm bg-muted px-3 py-2 rounded-md">
                {organization.updated_by_user_name}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Organization"
        description={`Are you sure you want to delete "${organization.name}"? This action cannot be undone and will affect all associated data.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteOrganization.isPending}
      />
        </div>
      </div>
    </div>
  );
}
