import { useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { Layers, ArrowLeft, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RelatedItemsSidebar } from "@/components/relationships/RelatedItemsSidebar";
import { EntityAttachments, ConfirmDialog, EditModeActions } from "@/components/shared";
import { CustomFieldList } from "@/components/assets/CustomFieldRenderer";
import { CustomFieldInput } from "@/components/assets/CustomFieldInput";
import { useUnsavedChangesWarning } from "@/hooks/useUnsavedChangesWarning";
import { usePermissions } from "@/hooks/usePermissions";
import {
  useCustomAssetType,
  useCustomAsset,
  useRevealCustomAsset,
  useUpdateCustomAsset,
  useDeleteCustomAsset,
  type FieldDefinition,
} from "@/hooks/useCustomAssets";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { getDisplayFieldKey, getDisplayValue } from "@/lib/custom-asset-utils";

// Build dynamic schema based on field definitions
function buildSchema(fields: FieldDefinition[], mode: "create" | "edit") {
  const fieldSchemas: Record<string, z.ZodTypeAny> = {};

  for (const field of fields) {
    if (field.type === "header") continue;

    let fieldSchema: z.ZodTypeAny;

    switch (field.type) {
      case "text":
      case "textbox":
        fieldSchema = z.string();
        if (field.required) {
          fieldSchema = (fieldSchema as z.ZodString).min(1, `${field.name} is required`);
        }
        break;

      case "password":
      case "totp":
        fieldSchema = z.string();
        if (field.required && mode === "create") {
          fieldSchema = (fieldSchema as z.ZodString).min(1, `${field.name} is required`);
        }
        break;

      case "number":
        if (field.required) {
          fieldSchema = z.number({ message: `${field.name} is required` });
        } else {
          fieldSchema = z.union([z.number(), z.null()]);
        }
        break;

      case "date":
        fieldSchema = z.string();
        if (field.required) {
          fieldSchema = (fieldSchema as z.ZodString).min(1, `${field.name} is required`);
        }
        break;

      case "checkbox":
        fieldSchema = z.boolean();
        break;

      case "select":
        fieldSchema = z.string();
        if (field.required) {
          fieldSchema = (fieldSchema as z.ZodString).min(1, `${field.name} is required`);
        }
        break;

      default:
        fieldSchema = z.string();
    }

    fieldSchemas[field.key] = fieldSchema;
  }

  return z.object({
    values: z.object(fieldSchemas),
  });
}

// Build default values from asset data
function buildDefaultValues(
  fields: FieldDefinition[],
  asset: { values: Record<string, unknown> }
) {
  const defaults: Record<string, unknown> = {};

  for (const field of fields) {
    if (field.type === "header") continue;

    if (asset.values[field.key] !== undefined) {
      defaults[field.key] = asset.values[field.key];
    } else if (field.default_value !== null) {
      if (field.type === "checkbox") {
        defaults[field.key] = field.default_value === "true";
      } else if (field.type === "number") {
        defaults[field.key] = Number(field.default_value);
      } else {
        defaults[field.key] = field.default_value;
      }
    } else {
      switch (field.type) {
        case "checkbox":
          defaults[field.key] = false;
          break;
        case "number":
          defaults[field.key] = null;
          break;
        default:
          defaults[field.key] = "";
      }
    }
  }

  return { values: defaults };
}

type FormValues = { values: Record<string, unknown> };

export function CustomAssetDetailPage() {
  const { orgId, typeId, id } = useParams<{
    orgId: string;
    typeId: string;
    id: string;
  }>();
  const navigate = useNavigate();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const { canEdit } = usePermissions();

  const { data: assetType, isLoading: typeLoading } = useCustomAssetType(typeId!);
  const { data: asset, isLoading: assetLoading } = useCustomAsset(orgId!, typeId!, id!);
  const revealQuery = useRevealCustomAsset(orgId!, typeId!, id!);
  const updateAsset = useUpdateCustomAsset(orgId!, typeId!, id!);
  const deleteAsset = useDeleteCustomAsset(orgId!, typeId!, () => {
    // Navigate in onSuccess callback BEFORE cache removal to prevent stale query refetch
    navigate(`/org/${orgId}/assets/${typeId}`);
  });

  const isLoading = typeLoading || assetLoading;

  // Build schema and default values when asset type and asset are loaded
  const { schema, defaultValues } = useMemo(() => {
    if (!assetType || !asset) {
      return { schema: null, defaultValues: null };
    }
    return {
      schema: buildSchema(assetType.fields, "edit"),
      defaultValues: buildDefaultValues(assetType.fields, asset),
    };
  }, [assetType, asset]);

  // Get display field key for this asset type
  const displayFieldKey = useMemo(() => {
    if (!assetType) return null;
    return getDisplayFieldKey(assetType);
  }, [assetType]);

  // Get display name for this asset
  const displayName = useMemo(() => {
    if (!asset) return "Unnamed";
    return getDisplayValue(asset, displayFieldKey);
  }, [asset, displayFieldKey]);

  // Initialize form
  const form = useForm<FormValues>({
    resolver: schema ? zodResolver(schema) : undefined,
    defaultValues: defaultValues ?? { values: {} },
  });

  // Reset form when asset data changes
  useMemo(() => {
    if (defaultValues && !isEditing) {
      form.reset(defaultValues);
    }
  }, [defaultValues, isEditing, form]);

  const isDirty = form.formState.isDirty;

  // Warn before leaving with unsaved changes
  useUnsavedChangesWarning(isDirty && isEditing);

  // Group fields by headers for organized display
  const groupedFields = useMemo(() => {
    if (!assetType?.fields) return [];

    const groups: { header: string | null; fields: FieldDefinition[] }[] = [];
    let currentGroup: { header: string | null; fields: FieldDefinition[] } = {
      header: null,
      fields: [],
    };

    for (const field of assetType.fields) {
      if (field.type === "header") {
        if (currentGroup.fields.length > 0 || currentGroup.header !== null) {
          groups.push(currentGroup);
        }
        currentGroup = { header: field.name, fields: [] };
      } else {
        currentGroup.fields.push(field);
      }
    }

    if (currentGroup.fields.length > 0 || currentGroup.header !== null) {
      groups.push(currentGroup);
    }

    return groups;
  }, [assetType?.fields]);

  if (!orgId || !typeId || !id) {
    return null;
  }

  const handleSave = async () => {
    const isValid = await form.trigger();
    if (!isValid) return;

    setIsSaving(true);
    try {
      const data = form.getValues();
      // Clean up values - remove empty strings and nulls for non-required fields
      const cleanedValues: Record<string, unknown> = {};
      for (const field of assetType!.fields) {
        if (field.type === "header") continue;
        const value = data.values[field.key];
        if (value !== undefined && value !== "" && value !== null) {
          cleanedValues[field.key] = value;
        }
      }
      await updateAsset.mutateAsync({ values: cleanedValues });
      setIsEditing(false);
      toast.success("Asset updated successfully");
    } catch {
      toast.error("Failed to update asset");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    form.reset(defaultValues ?? { values: {} });
    setIsEditing(false);
  };

  const handleDelete = async () => {
    try {
      await deleteAsset.mutateAsync(id);
      toast.success("Asset deleted successfully");
      // Navigation already happened in onSuccess callback
    } catch {
      toast.error("Failed to delete asset");
    }
  };

  const handleToggleEnabled = async (checked: boolean) => {
    try {
      await updateAsset.mutateAsync({ is_enabled: checked });
      toast.success(checked ? "Asset enabled" : "Asset disabled");
    } catch {
      toast.error("Failed to update asset");
    }
  };

  const handleReveal = () => {
    revealQuery.refetch();
  };

  // Check if this type has password or totp fields
  const hasSecretFields = assetType?.fields.some(
    (f) => f.type === "password" || f.type === "totp"
  );

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
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-24 w-full" />
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

  if (!assetType) {
    return (
      <div className="text-center py-12">
        <Layers className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Asset type not found</h2>
        <p className="text-sm text-muted-foreground mb-4">
          The asset type you're looking for doesn't exist or has been deleted.
        </p>
        <Button asChild variant="outline">
          <Link to={`/org/${orgId}/assets`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Asset Types
          </Link>
        </Button>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="text-center py-12">
        <Layers className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Asset not found</h2>
        <p className="text-sm text-muted-foreground mb-4">
          The asset you're looking for doesn't exist or has been deleted.
        </p>
        <Button asChild variant="outline">
          <Link to={`/org/${orgId}/assets/${typeId}`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to {assetType.name}
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      <div className={`flex-1 space-y-6${asset.is_enabled ? "" : " opacity-60"}`}>
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Link
                to={`/org/${orgId}/assets`}
                className="hover:text-foreground transition-colors"
              >
                Asset Types
              </Link>
              <span>/</span>
              <Link
                to={`/org/${orgId}/assets/${typeId}`}
                className="hover:text-foreground transition-colors"
              >
                {assetType.name}
              </Link>
              <span>/</span>
              <span>{displayName}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Layers className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">{displayName}</h1>
                <p className="text-sm text-muted-foreground">{assetType.name}</p>
              </div>
            </div>
          </div>
          {canEdit && (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 mr-2">
                <Switch
                  key={asset.updated_at}
                  checked={asset.is_enabled}
                  onCheckedChange={handleToggleEnabled}
                  disabled={updateAsset.isPending || isEditing}
                />
                <span className="text-sm text-muted-foreground">
                  {asset.is_enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <EditModeActions
                isEditing={isEditing}
                isSaving={isSaving}
                isDirty={isDirty}
                onEdit={() => setIsEditing(true)}
                onSave={handleSave}
                onCancel={handleCancel}
                canEdit={canEdit}
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
        {!asset.is_enabled && (
          <Alert variant="destructive">
            <AlertDescription>
              This asset has been disabled and will not appear in search or lists
            </AlertDescription>
          </Alert>
        )}

        {/* Field Values */}
        <Card className={cn(isEditing && "ring-2 ring-primary/20")}>
          <CardHeader>
            <CardTitle className="text-base">Details</CardTitle>
          </CardHeader>
          <CardContent>
            {isEditing ? (
              <div className="space-y-6">
                {/* Custom fields */}
                {groupedFields.map((group, groupIndex) => (
                  <div key={groupIndex} className="space-y-4">
                    {group.header && (
                      <div className="border-b pb-2 pt-2">
                        <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                          {group.header}
                        </h4>
                      </div>
                    )}
                    <div className="grid gap-4">
                      {group.fields.map((field) => (
                        <Controller
                          key={field.key}
                          name={`values.${field.key}`}
                          control={form.control}
                          render={({ field: formField, fieldState }) => (
                            <CustomFieldInput
                              field={field}
                              value={formField.value}
                              onChange={formField.onChange}
                              error={fieldState.error?.message}
                              mode="edit"
                            />
                          )}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <CustomFieldList
                fields={assetType.fields}
                values={asset.values}
                revealedValues={revealQuery.data?.values}
                onReveal={hasSecretFields ? handleReveal : undefined}
                isRevealing={revealQuery.isFetching}
              />
            )}
          </CardContent>
        </Card>

        {/* Metadata */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Information</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Created</dt>
                <dd className="text-sm">
                  {new Date(asset.created_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Updated</dt>
                <dd className="text-sm">
                  {new Date(asset.updated_at).toLocaleString()}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>

      {/* Sidebar */}
      <aside className="w-80 shrink-0 hidden lg:block space-y-4">
        <RelatedItemsSidebar orgId={orgId} entityType="custom_asset" entityId={id} />
        <EntityAttachments entityType="custom_asset" entityId={id} />
      </aside>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Asset"
        description={`Are you sure you want to delete "${displayName}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteAsset.isPending}
      />
    </div>
  );
}
