import { useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import {
  Server,
  ArrowLeft,
  Trash2,
  Building2,
  Network,
  FileText,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TiptapEditor } from "@/components/documents/TiptapEditor";
import { RelatedItemsSidebar } from "@/components/relationships/RelatedItemsSidebar";
import { EntityAttachments, ConfirmDialog, EditModeActions } from "@/components/shared";
import { usePermissions } from "@/hooks/usePermissions";
import { useInlineEdit } from "@/hooks/useInlineEdit";
import { useUnsavedChangesWarning } from "@/hooks/useUnsavedChangesWarning";
import {
  useConfiguration,
  useUpdateConfiguration,
  useDeleteConfiguration,
  useConfigurationTypes,
  useConfigurationStatuses,
  type ConfigurationUpdate,
} from "@/hooks/useConfigurations";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const configSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  configuration_type_id: z.string().optional(),
  configuration_status_id: z.string().optional(),
  serial_number: z.string().max(255).optional(),
  asset_tag: z.string().max(255).optional(),
  manufacturer: z.string().max(255).optional(),
  model: z.string().max(255).optional(),
  ip_address: z.string().max(45).optional(),
  mac_address: z.string().max(17).optional(),
  notes: z.string().optional(),
});

type ConfigFormValues = z.infer<typeof configSchema>;

export function ConfigDetailPage() {
  const { orgId, id } = useParams<{ orgId: string; id: string }>();
  const navigate = useNavigate();
  const { canEdit } = usePermissions();

  const { data: config, isLoading } = useConfiguration(orgId!, id!);
  const { data: types = [] } = useConfigurationTypes();
  const { data: statuses = [] } = useConfigurationStatuses();
  const updateConfiguration = useUpdateConfiguration(orgId!, id!);
  const deleteConfiguration = useDeleteConfiguration(orgId!);

  // Memoize initial data before any early returns
  const initialData = useMemo((): ConfigFormValues => {
    if (!config) {
      return {
        name: "",
        configuration_type_id: undefined,
        configuration_status_id: undefined,
        serial_number: "",
        asset_tag: "",
        manufacturer: "",
        model: "",
        ip_address: "",
        mac_address: "",
        notes: "",
      };
    }
    return {
      name: config.name,
      configuration_type_id: config.configuration_type_id ?? undefined,
      configuration_status_id: config.configuration_status_id ?? undefined,
      serial_number: config.serial_number ?? "",
      asset_tag: config.asset_tag ?? "",
      manufacturer: config.manufacturer ?? "",
      model: config.model ?? "",
      ip_address: config.ip_address ?? "",
      mac_address: config.mac_address ?? "",
      notes: config.notes ?? "",
    };
  }, [config]);

  const {
    isEditing,
    isDirty,
    isSaving,
    form,
    startEditing,
    cancelEditing,
    saveChanges,
  } = useInlineEdit<ConfigFormValues>({
    resolver: zodResolver(configSchema),
    initialData,
    onSave: async (data) => {
      const updateData: ConfigurationUpdate = {
        name: data.name,
      };
      if (data.configuration_type_id) updateData.configuration_type_id = data.configuration_type_id;
      if (data.configuration_status_id) updateData.configuration_status_id = data.configuration_status_id;
      if (data.serial_number) updateData.serial_number = data.serial_number;
      if (data.asset_tag) updateData.asset_tag = data.asset_tag;
      if (data.manufacturer) updateData.manufacturer = data.manufacturer;
      if (data.model) updateData.model = data.model;
      if (data.ip_address) updateData.ip_address = data.ip_address;
      if (data.mac_address) updateData.mac_address = data.mac_address;
      if (data.notes) updateData.notes = data.notes;
      await updateConfiguration.mutateAsync(updateData);
      toast.success("Configuration updated successfully");
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
      await deleteConfiguration.mutateAsync(id);
      toast.success("Configuration deleted successfully");
      navigate(`/org/${orgId}/configurations`);
    } catch {
      toast.error("Failed to delete configuration");
    }
  };

  const handleToggleEnabled = async (checked: boolean) => {
    try {
      await updateConfiguration.mutateAsync({ is_enabled: checked });
      toast.success(checked ? "Configuration enabled" : "Configuration disabled");
    } catch {
      toast.error("Failed to update configuration");
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
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
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

  if (!config) {
    return (
      <div className="text-center py-12">
        <Server className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Configuration not found</h2>
        <p className="text-sm text-muted-foreground mb-4">
          The configuration you're looking for doesn't exist or has been deleted.
        </p>
        <Button asChild variant="outline">
          <Link to={`/org/${orgId}/configurations`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Configurations
          </Link>
        </Button>
      </div>
    );
  }

  // Helper to render field value or "Not set"
  const renderValue = (value: string | null | undefined, mono?: boolean) => {
    if (!value) {
      return <span className="text-muted-foreground italic">Not set</span>;
    }
    return mono ? <span className="font-mono">{value}</span> : value;
  };

  return (
    <div className="flex gap-6">
      <div className={`flex-1 space-y-6${config.is_enabled ? "" : " opacity-60"}`}>
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Link
                to={`/org/${orgId}/configurations`}
                className="hover:text-foreground transition-colors"
              >
                Configurations
              </Link>
              <span>/</span>
              <span>{config.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Server className="h-5 w-5 text-primary" />
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
                          placeholder="Configuration name"
                        />
                        {fieldState.error && (
                          <p className="text-sm text-destructive mt-1">{fieldState.error.message}</p>
                        )}
                      </div>
                    )}
                  />
                ) : (
                  <h1 className="text-2xl font-bold tracking-tight">
                    {config.name}
                  </h1>
                )}
                <div className="flex items-center gap-2 mt-1">
                  {isEditing ? (
                    <>
                      <Controller
                        control={form.control}
                        name="configuration_type_id"
                        render={({ field }) => (
                          <Select
                            onValueChange={field.onChange}
                            value={field.value ?? ""}
                          >
                            <SelectTrigger className="h-7 text-xs w-[140px]">
                              <SelectValue placeholder="Select type..." />
                            </SelectTrigger>
                            <SelectContent>
                              {types.map((type) => (
                                <SelectItem key={type.id} value={type.id}>
                                  {type.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                      />
                      <Controller
                        control={form.control}
                        name="configuration_status_id"
                        render={({ field }) => (
                          <Select
                            onValueChange={field.onChange}
                            value={field.value ?? ""}
                          >
                            <SelectTrigger className="h-7 text-xs w-[140px]">
                              <SelectValue placeholder="Select status..." />
                            </SelectTrigger>
                            <SelectContent>
                              {statuses.map((status) => (
                                <SelectItem key={status.id} value={status.id}>
                                  {status.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                      />
                    </>
                  ) : (
                    <>
                      {config.configuration_type_name && (
                        <Badge variant="outline">
                          {config.configuration_type_name}
                        </Badge>
                      )}
                      {config.configuration_status_name && (
                        <Badge variant="secondary">
                          {config.configuration_status_name}
                        </Badge>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
          {canEdit && (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 mr-2">
                <Switch
                  key={config.updated_at}
                  checked={config.is_enabled}
                  onCheckedChange={handleToggleEnabled}
                  disabled={updateConfiguration.isPending || isEditing}
                />
                <span className="text-sm text-muted-foreground">
                  {config.is_enabled ? "Enabled" : "Disabled"}
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
        {!config.is_enabled && (
          <Alert variant="destructive">
            <AlertDescription>
              This configuration has been disabled and will not appear in search or lists
            </AlertDescription>
          </Alert>
        )}

        {/* Details */}
        <div className="grid gap-6">
          {/* Hardware Info */}
          <Card className={cn(isEditing && "ring-2 ring-primary/20")}>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Hardware Information
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">
                  Manufacturer
                </label>
                {isEditing ? (
                  <Controller
                    control={form.control}
                    name="manufacturer"
                    render={({ field }) => (
                      <Input {...field} placeholder="e.g., Dell" />
                    )}
                  />
                ) : (
                  <p className="text-sm font-medium">
                    {renderValue(config.manufacturer)}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">Model</label>
                {isEditing ? (
                  <Controller
                    control={form.control}
                    name="model"
                    render={({ field }) => (
                      <Input {...field} placeholder="e.g., PowerEdge R750" />
                    )}
                  />
                ) : (
                  <p className="text-sm font-medium">
                    {renderValue(config.model)}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">
                  Serial Number
                </label>
                {isEditing ? (
                  <Controller
                    control={form.control}
                    name="serial_number"
                    render={({ field }) => (
                      <Input {...field} placeholder="e.g., ABC123456" className="font-mono" />
                    )}
                  />
                ) : (
                  <p className="text-sm">
                    {renderValue(config.serial_number, true)}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">
                  Asset Tag
                </label>
                {isEditing ? (
                  <Controller
                    control={form.control}
                    name="asset_tag"
                    render={({ field }) => (
                      <Input {...field} placeholder="e.g., IT-001234" className="font-mono" />
                    )}
                  />
                ) : (
                  <p className="text-sm">
                    {renderValue(config.asset_tag, true)}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Network Info */}
          <Card className={cn(isEditing && "ring-2 ring-primary/20")}>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Network className="h-4 w-4" />
                Network Information
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">
                  IP Address
                </label>
                {isEditing ? (
                  <Controller
                    control={form.control}
                    name="ip_address"
                    render={({ field }) => (
                      <Input {...field} placeholder="e.g., 192.168.1.100" className="font-mono" />
                    )}
                  />
                ) : (
                  <p className="text-sm">
                    {renderValue(config.ip_address, true)}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">
                  MAC Address
                </label>
                {isEditing ? (
                  <Controller
                    control={form.control}
                    name="mac_address"
                    render={({ field }) => (
                      <Input {...field} placeholder="e.g., 00:1A:2B:3C:4D:5E" className="font-mono" />
                    )}
                  />
                ) : (
                  <p className="text-sm">
                    {renderValue(config.mac_address, true)}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

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
                      placeholder="Additional notes..."
                      className="min-h-[120px]"
                    />
                  )}
                />
              ) : config.notes ? (
                <div
                  className="prose prose-sm max-w-none dark:prose-invert"
                  dangerouslySetInnerHTML={{ __html: config.notes }}
                />
              ) : (
                <p className="text-sm text-muted-foreground italic">No notes</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Sidebar */}
      <aside className="w-80 shrink-0 hidden lg:block space-y-4">
        <RelatedItemsSidebar
          orgId={orgId}
          entityType="configuration"
          entityId={id}
        />
        <EntityAttachments entityType="configuration" entityId={id} />
      </aside>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Configuration"
        description={`Are you sure you want to delete "${config.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteConfiguration.isPending}
      />
    </div>
  );
}
