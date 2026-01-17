import { useState, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import {
  KeyRound,
  ArrowLeft,
  Trash2,
  ExternalLink,
  User,
  Link2,
  FileText,
  Shield,
  Eye,
  EyeOff,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { TiptapEditor } from "@/components/documents/TiptapEditor";
import { RelatedItemsSidebar } from "@/components/relationships/RelatedItemsSidebar";
import { EntityAttachments, ConfirmDialog, EditModeActions } from "@/components/shared";
import { PasswordReveal } from "@/components/passwords/PasswordReveal";
import { TOTPReveal } from "@/components/passwords/TOTPReveal";
import { usePermissions } from "@/hooks/usePermissions";
import { useInlineEdit } from "@/hooks/useInlineEdit";
import { useUnsavedChangesWarning } from "@/hooks/useUnsavedChangesWarning";
import {
  usePassword,
  useUpdatePassword,
  useDeletePassword,
  type PasswordUpdate,
} from "@/hooks/usePasswords";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const passwordSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  username: z.string().max(255).optional(),
  // Password is optional in edit mode - leave blank to keep current
  password: z.string().optional(),
  url: z.string().max(2048).optional(),
  notes: z.string().optional(),
  // TOTP is optional in edit mode - leave blank to keep current
  totp_secret: z.string().optional(),
});

type PasswordFormValues = z.infer<typeof passwordSchema>;

export function PasswordDetailPage() {
  const { orgId, id } = useParams<{ orgId: string; id: string }>();
  const navigate = useNavigate();
  const { canEdit } = usePermissions();
  const [showPassword, setShowPassword] = useState(false);

  const { data: password, isLoading } = usePassword(orgId!, id!);
  const updatePassword = useUpdatePassword(orgId!, id!);
  const deletePassword = useDeletePassword(orgId!);

  // Memoize initial data before any early returns
  // Note: password and totp_secret are intentionally NOT pre-filled for security
  const initialData = useMemo((): PasswordFormValues => {
    if (!password) {
      return {
        name: "",
        username: "",
        password: "",
        url: "",
        notes: "",
        totp_secret: "",
      };
    }
    return {
      name: password.name,
      username: password.username ?? "",
      password: "", // Don't pre-fill - leave blank to keep current
      url: password.url ?? "",
      notes: password.notes ?? "",
      totp_secret: "", // Don't pre-fill - leave blank to keep current
    };
  }, [password]);

  const {
    isEditing,
    isDirty,
    isSaving,
    form,
    startEditing,
    cancelEditing,
    saveChanges,
  } = useInlineEdit<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    initialData,
    onSave: async (data) => {
      const updateData: PasswordUpdate = {
        name: data.name,
      };
      if (data.username) updateData.username = data.username;
      if (data.password) updateData.password = data.password;
      if (data.url) updateData.url = data.url;
      if (data.notes) updateData.notes = data.notes;
      if (data.totp_secret) updateData.totp_secret = data.totp_secret;
      await updatePassword.mutateAsync(updateData);
      toast.success("Password updated successfully");
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
      await deletePassword.mutateAsync(id);
      toast.success("Password deleted successfully");
      navigate(`/org/${orgId}/passwords`);
    } catch {
      toast.error("Failed to delete password");
    }
  };

  const handleToggleEnabled = async (checked: boolean) => {
    try {
      await updatePassword.mutateAsync({ is_enabled: checked });
      toast.success(checked ? "Password enabled" : "Password disabled");
    } catch {
      toast.error("Failed to update password");
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

  if (!password) {
    return (
      <div className="text-center py-12">
        <KeyRound className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
        <h2 className="text-lg font-medium mb-1">Password not found</h2>
        <p className="text-sm text-muted-foreground mb-4">
          The password you're looking for doesn't exist or has been deleted.
        </p>
        <Button asChild variant="outline">
          <Link to={`/org/${orgId}/passwords`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Passwords
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      <div className={`flex-1 space-y-6${password.is_enabled ? "" : " opacity-60"}`}>
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Link
                to={`/org/${orgId}/passwords`}
                className="hover:text-foreground transition-colors"
              >
                Passwords
              </Link>
              <span>/</span>
              <span>{password.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <KeyRound className="h-5 w-5 text-primary" />
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
                          placeholder="Password name"
                        />
                        {fieldState.error && (
                          <p className="text-sm text-destructive mt-1">{fieldState.error.message}</p>
                        )}
                      </div>
                    )}
                  />
                ) : (
                  <h1 className="text-2xl font-bold tracking-tight">
                    {password.name}
                  </h1>
                )}
                <p className="text-sm text-muted-foreground">
                  Last updated {new Date(password.updated_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
          {canEdit && (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 mr-2">
                <Switch
                  key={password.updated_at}
                  checked={password.is_enabled}
                  onCheckedChange={handleToggleEnabled}
                  disabled={updatePassword.isPending || isEditing}
                />
                <span className="text-sm text-muted-foreground">
                  {password.is_enabled ? "Enabled" : "Disabled"}
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
        {!password.is_enabled && (
          <Alert variant="destructive">
            <AlertDescription>
              This password has been disabled and will not appear in search or lists
            </AlertDescription>
          </Alert>
        )}

        {/* Details */}
        <Card className={cn(isEditing && "ring-2 ring-primary/20")}>
          <CardHeader>
            <CardTitle className="text-base">Credentials</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Username */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <User className="h-4 w-4" />
                Username
              </label>
              {isEditing ? (
                <Controller
                  control={form.control}
                  name="username"
                  render={({ field }) => (
                    <Input {...field} placeholder="e.g., admin" className="font-mono" />
                  )}
                />
              ) : password.username ? (
                <p className="text-sm font-mono bg-muted px-3 py-2 rounded-md">
                  {password.username}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground italic">Not set</p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <KeyRound className="h-4 w-4" />
                Password
                {isEditing && (
                  <span className="font-normal">(leave blank to keep current)</span>
                )}
              </label>
              {isEditing ? (
                <Controller
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <div className="relative">
                      <Input
                        type={showPassword ? "text" : "password"}
                        placeholder="Leave blank to keep current"
                        className="font-mono pr-10"
                        {...field}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </div>
                  )}
                />
              ) : (
                <PasswordReveal key={password.updated_at} orgId={orgId} passwordId={id} />
              )}
            </div>

            {/* TOTP */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Shield className="h-4 w-4" />
                TOTP Code
                {isEditing && (
                  <span className="font-normal">(leave blank to keep current)</span>
                )}
              </label>
              {isEditing ? (
                <div className="space-y-2">
                  <Controller
                    control={form.control}
                    name="totp_secret"
                    render={({ field }) => (
                      <Input
                        {...field}
                        placeholder="Paste new TOTP secret (base32 format)"
                        className="font-mono"
                      />
                    )}
                  />
                  <p className="text-xs text-muted-foreground">
                    Paste your TOTP secret (base32 format) to enable one-time password generation
                  </p>
                </div>
              ) : password.has_totp ? (
                <TOTPReveal key={password.updated_at} orgId={orgId} passwordId={id} />
              ) : (
                <p className="text-sm text-muted-foreground italic">Not configured</p>
              )}
            </div>

            <Separator />

            {/* URL */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Link2 className="h-4 w-4" />
                URL
              </label>
              {isEditing ? (
                <Controller
                  control={form.control}
                  name="url"
                  render={({ field }) => (
                    <Input
                      type="url"
                      placeholder="e.g., https://example.com"
                      {...field}
                    />
                  )}
                />
              ) : password.url ? (
                <a
                  href={password.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-primary hover:underline text-sm"
                >
                  <ExternalLink className="h-4 w-4" />
                  {password.url}
                </a>
              ) : (
                <p className="text-sm text-muted-foreground italic">Not set</p>
              )}
            </div>

            {/* Notes */}
            <Separator />
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Notes
              </label>
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
              ) : password.notes ? (
                <div
                  className="prose prose-sm max-w-none dark:prose-invert bg-muted px-3 py-2 rounded-md"
                  dangerouslySetInnerHTML={{ __html: password.notes }}
                />
              ) : (
                <p className="text-sm text-muted-foreground italic">No notes</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sidebar */}
      <aside className="w-80 shrink-0 hidden lg:block space-y-4">
        <RelatedItemsSidebar
          orgId={orgId}
          entityType="password"
          entityId={id}
        />
        <EntityAttachments entityType="password" entityId={id} />
      </aside>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Password"
        description={`Are you sure you want to delete "${password.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deletePassword.isPending}
      />
    </div>
  );
}
