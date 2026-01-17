import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Loader2,
  Shield,
  Smartphone,
  Key,
  Copy,
  Check,
  Trash2,
  Plus,
  Eye,
  EyeOff,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { settingsApi, type Passkey } from "@/lib/api-client";

// Password change schema
const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
        "Password must contain at least one uppercase letter, one lowercase letter, and one number"
      ),
    confirm_password: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type PasswordFormData = z.infer<typeof passwordSchema>;

// MFA verification schema
const mfaSchema = z.object({
  code: z.string().length(6, "Code must be 6 digits"),
});

type MfaFormData = z.infer<typeof mfaSchema>;

export function SecuritySettings() {
  return (
    <div className="space-y-6">
      <ChangePasswordSection />
      <MfaSection />
      <PasskeysSection />
    </div>
  );
}

// --- Change Password Section ---
function ChangePasswordSection() {
  const [isLoading, setIsLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  const form = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  async function onSubmit(data: PasswordFormData) {
    setIsLoading(true);
    try {
      await settingsApi.changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
      });
      toast.success("Password changed successfully");
      form.reset();
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(
        axiosError.response?.data?.detail || "Failed to change password"
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Change Password
        </CardTitle>
        <CardDescription>
          Update your password to keep your account secure
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="current_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Current Password</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showCurrentPassword ? "text" : "password"}
                        placeholder="Enter current password"
                        autoComplete="current-password"
                        {...field}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                        onClick={() =>
                          setShowCurrentPassword(!showCurrentPassword)
                        }
                      >
                        {showCurrentPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="new_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New Password</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showNewPassword ? "text" : "password"}
                        placeholder="Enter new password"
                        autoComplete="new-password"
                        {...field}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                      >
                        {showNewPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="confirm_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirm New Password</FormLabel>
                  <FormControl>
                    <Input
                      type="password"
                      placeholder="Confirm new password"
                      autoComplete="new-password"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex justify-end">
              <Button type="submit" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Change Password
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

// --- MFA Section ---
function MfaSection() {
  const queryClient = useQueryClient();
  const [setupDialogOpen, setSetupDialogOpen] = useState(false);
  const [disableDialogOpen, setDisableDialogOpen] = useState(false);
  const [backupCodesDialogOpen, setBackupCodesDialogOpen] = useState(false);
  const [setupData, setSetupData] = useState<{
    secret: string;
    qr_code: string;
    backup_codes: string[];
  } | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const { data: mfaStatus, isLoading } = useQuery({
    queryKey: ["mfa-status"],
    queryFn: () => settingsApi.getMfaStatus().then((r) => r.data),
  });

  const setupMfaMutation = useMutation({
    mutationFn: () => settingsApi.setupMfa().then((r) => r.data),
    onSuccess: (data) => {
      setSetupData(data);
      setSetupDialogOpen(true);
    },
    onError: () => {
      toast.error("Failed to set up MFA");
    },
  });

  const enableMfaMutation = useMutation({
    mutationFn: (code: string) => settingsApi.enableMfa({ code }),
    onSuccess: () => {
      toast.success("MFA enabled successfully");
      setSetupDialogOpen(false);
      setSetupData(null);
      queryClient.invalidateQueries({ queryKey: ["mfa-status"] });
    },
    onError: () => {
      toast.error("Invalid verification code");
    },
  });

  const disableMfaMutation = useMutation({
    mutationFn: (code: string) => settingsApi.disableMfa({ code }),
    onSuccess: () => {
      toast.success("MFA disabled successfully");
      setDisableDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["mfa-status"] });
    },
    onError: () => {
      toast.error("Invalid verification code");
    },
  });

  const regenerateBackupCodesMutation = useMutation({
    mutationFn: () => settingsApi.regenerateBackupCodes().then((r) => r.data),
    onSuccess: (data) => {
      setSetupData({ secret: "", qr_code: "", backup_codes: data.backup_codes });
      setBackupCodesDialogOpen(true);
    },
    onError: () => {
      toast.error("Failed to regenerate backup codes");
    },
  });

  const mfaForm = useForm<MfaFormData>({
    resolver: zodResolver(mfaSchema),
    defaultValues: { code: "" },
  });

  const disableForm = useForm<MfaFormData>({
    resolver: zodResolver(mfaSchema),
    defaultValues: { code: "" },
  });

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopiedCode(text);
    setTimeout(() => setCopiedCode(null), 2000);
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-10 w-32" />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Smartphone className="h-5 w-5" />
            Two-Factor Authentication (MFA)
          </CardTitle>
          <CardDescription>
            Add an extra layer of security to your account using a TOTP
            authenticator app
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant={mfaStatus?.enabled ? "default" : "secondary"}>
                {mfaStatus?.enabled ? "Enabled" : "Disabled"}
              </Badge>
              {mfaStatus?.enabled && mfaStatus.backup_codes_remaining > 0 && (
                <span className="text-sm text-muted-foreground">
                  {mfaStatus.backup_codes_remaining} backup codes remaining
                </span>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            {mfaStatus?.enabled ? (
              <>
                <Button
                  variant="outline"
                  onClick={() => regenerateBackupCodesMutation.mutate()}
                  disabled={regenerateBackupCodesMutation.isPending}
                >
                  {regenerateBackupCodesMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Regenerate Backup Codes
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => setDisableDialogOpen(true)}
                >
                  Disable MFA
                </Button>
              </>
            ) : (
              <Button
                onClick={() => setupMfaMutation.mutate()}
                disabled={setupMfaMutation.isPending}
              >
                {setupMfaMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Set Up MFA
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* MFA Setup Dialog */}
      <Dialog open={setupDialogOpen} onOpenChange={setSetupDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Set Up Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              Scan the QR code with your authenticator app, then enter the
              verification code below.
            </DialogDescription>
          </DialogHeader>

          {setupData && (
            <div className="space-y-4">
              {/* QR Code */}
              <div className="flex justify-center">
                <img
                  src={setupData.qr_code}
                  alt="MFA QR Code"
                  className="w-48 h-48 border rounded-lg"
                />
              </div>

              {/* Manual entry secret */}
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Or enter this code manually:
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-muted px-3 py-2 rounded text-sm font-mono">
                    {setupData.secret}
                  </code>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => copyToClipboard(setupData.secret)}
                  >
                    {copiedCode === setupData.secret ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* Backup Codes */}
              <div className="space-y-2">
                <p className="text-sm font-medium">Save these backup codes:</p>
                <div className="bg-muted p-3 rounded-lg grid grid-cols-2 gap-2">
                  {setupData.backup_codes.map((code, i) => (
                    <code key={i} className="text-sm font-mono">
                      {code}
                    </code>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  Store these codes safely. Each code can only be used once.
                </p>
              </div>

              {/* Verification Form */}
              <Form {...mfaForm}>
                <form
                  onSubmit={mfaForm.handleSubmit((data) =>
                    enableMfaMutation.mutate(data.code)
                  )}
                  className="space-y-4"
                >
                  <FormField
                    control={mfaForm.control}
                    name="code"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Verification Code</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Enter 6-digit code"
                            maxLength={6}
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <DialogFooter>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setSetupDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      disabled={enableMfaMutation.isPending}
                    >
                      {enableMfaMutation.isPending && (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      )}
                      Enable MFA
                    </Button>
                  </DialogFooter>
                </form>
              </Form>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Disable MFA Dialog */}
      <Dialog open={disableDialogOpen} onOpenChange={setDisableDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disable Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              Enter your verification code to disable MFA. This will make your
              account less secure.
            </DialogDescription>
          </DialogHeader>

          <Form {...disableForm}>
            <form
              onSubmit={disableForm.handleSubmit((data) =>
                disableMfaMutation.mutate(data.code)
              )}
              className="space-y-4"
            >
              <FormField
                control={disableForm.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Verification Code</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter 6-digit code"
                        maxLength={6}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setDisableDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="destructive"
                  disabled={disableMfaMutation.isPending}
                >
                  {disableMfaMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Disable MFA
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Backup Codes Dialog */}
      <Dialog open={backupCodesDialogOpen} onOpenChange={setBackupCodesDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Backup Codes</DialogTitle>
            <DialogDescription>
              Your old backup codes have been invalidated. Save these new codes
              securely.
            </DialogDescription>
          </DialogHeader>

          {setupData?.backup_codes && (
            <div className="bg-muted p-4 rounded-lg grid grid-cols-2 gap-2">
              {setupData.backup_codes.map((code, i) => (
                <code key={i} className="text-sm font-mono">
                  {code}
                </code>
              ))}
            </div>
          )}

          <DialogFooter>
            <Button onClick={() => setBackupCodesDialogOpen(false)}>
              I've Saved These Codes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// --- Passkeys Section ---
function PasskeysSection() {
  const queryClient = useQueryClient();
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [newPasskeyName, setNewPasskeyName] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);

  const { data: passkeys, isLoading } = useQuery({
    queryKey: ["passkeys"],
    queryFn: () => settingsApi.listPasskeys().then((r) => r.data),
  });

  const deletePasskeyMutation = useMutation({
    mutationFn: (id: string) => settingsApi.deletePasskey(id),
    onSuccess: () => {
      toast.success("Passkey removed");
      queryClient.invalidateQueries({ queryKey: ["passkeys"] });
    },
    onError: () => {
      toast.error("Failed to remove passkey");
    },
  });

  async function handleAddPasskey() {
    if (!newPasskeyName.trim()) {
      toast.error("Please enter a name for this passkey");
      return;
    }

    setIsRegistering(true);
    try {
      // Get registration options from server
      const optionsResponse = await settingsApi.registerPasskeyOptions();
      const options = optionsResponse.data;

      // Create credential using WebAuthn API
      const credential = await navigator.credentials.create({
        publicKey: options,
      });

      if (!credential) {
        toast.error("Failed to create passkey");
        return;
      }

      // Send credential to server
      await settingsApi.registerPasskey({
        name: newPasskeyName,
        credential: credential,
      });

      toast.success("Passkey added successfully");
      setAddDialogOpen(false);
      setNewPasskeyName("");
      queryClient.invalidateQueries({ queryKey: ["passkeys"] });
    } catch (error) {
      console.error("Passkey registration error:", error);
      toast.error("Failed to add passkey. Make sure your device supports WebAuthn.");
    } finally {
      setIsRegistering(false);
    }
  }

  function formatDate(dateString: string | null) {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Passkeys
          </CardTitle>
          <CardDescription>
            Use passkeys for passwordless sign-in using your device's biometrics
            or security key
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {passkeys && passkeys.length > 0 ? (
            <div className="space-y-2">
              {passkeys.map((passkey: Passkey) => (
                <div
                  key={passkey.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div>
                    <p className="font-medium">{passkey.name}</p>
                    <p className="text-sm text-muted-foreground">
                      Created {formatDate(passkey.created_at)}
                      {passkey.last_used_at &&
                        ` • Last used ${formatDate(passkey.last_used_at)}`}
                    </p>
                  </div>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Remove Passkey</AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to remove "{passkey.name}"? You
                          won't be able to use this passkey for sign-in anymore.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => deletePasskeyMutation.mutate(passkey.id)}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          Remove
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No passkeys registered. Add a passkey to sign in without a
              password.
            </p>
          )}

          <Button variant="outline" onClick={() => setAddDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Passkey
          </Button>
        </CardContent>
      </Card>

      {/* Add Passkey Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Passkey</DialogTitle>
            <DialogDescription>
              Give this passkey a name to help you identify it later.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Passkey Name</label>
              <Input
                placeholder="e.g., MacBook Pro Touch ID"
                value={newPasskeyName}
                onChange={(e) => setNewPasskeyName(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setAddDialogOpen(false);
                setNewPasskeyName("");
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleAddPasskey} disabled={isRegistering}>
              {isRegistering && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Register Passkey
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
