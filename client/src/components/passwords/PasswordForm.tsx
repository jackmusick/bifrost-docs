import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TiptapEditor } from "@/components/documents/TiptapEditor";
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
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import type { Password, PasswordCreate, PasswordUpdate } from "@/hooks/usePasswords";

const createSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  username: z.string().max(255).optional(),
  password: z.string().min(1, "Password is required"),
  url: z.string().max(2048).optional(),
  notes: z.string().optional(),
  totp_secret: z.string().max(255).optional(),
});

const updateSchema = z.object({
  name: z.string().min(1, "Name is required").max(255).optional(),
  username: z.string().max(255).optional(),
  // Allow empty string for "leave blank to keep current" behavior
  password: z.string().optional(),
  url: z.string().max(2048).optional(),
  notes: z.string().optional(),
  // Allow empty string for "leave blank to keep current" behavior
  totp_secret: z.string().optional(),
});

type CreateFormValues = z.infer<typeof createSchema>;
type UpdateFormValues = z.infer<typeof updateSchema>;

interface PasswordFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: PasswordCreate | PasswordUpdate) => void;
  isSubmitting: boolean;
  mode: "create" | "edit";
  initialData?: Password;
  orgId: string;
}

export function PasswordForm({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
  mode,
  initialData,
  orgId,
}: PasswordFormProps) {
  const [showPassword, setShowPassword] = useState(false);

  const form = useForm<CreateFormValues | UpdateFormValues>({
    resolver: zodResolver(mode === "create" ? createSchema : updateSchema),
    defaultValues: {
      name: initialData?.name ?? "",
      username: initialData?.username ?? "",
      password: "",
      url: initialData?.url ?? "",
      notes: initialData?.notes ?? "",
      totp_secret: "",
    },
  });

  const handleSubmit = (values: CreateFormValues | UpdateFormValues) => {
    // Filter out empty strings for optional fields
    const data: PasswordCreate | PasswordUpdate = {
      name: values.name,
    };

    if (values.username) data.username = values.username;
    if (values.password) data.password = values.password;
    if (values.url) data.url = values.url;
    if (values.notes) data.notes = values.notes;
    if (values.totp_secret) data.totp_secret = values.totp_secret;

    onSubmit(data);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? "Create Password" : "Edit Password"}
          </DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? "Add a new password entry to your organization."
              : "Update the password entry details."}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g., Production Database" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g., admin" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Password {mode === "create" && "*"}
                    {mode === "edit" && "(leave blank to keep current)"}
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showPassword ? "text" : "password"}
                        placeholder={
                          mode === "edit"
                            ? "Leave blank to keep current"
                            : "Enter password"
                        }
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
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>URL</FormLabel>
                  <FormControl>
                    <Input
                      type="url"
                      placeholder="e.g., https://example.com"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="totp_secret"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    TOTP Secret
                    {mode === "edit" && " (leave blank to keep current)"}
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="text"
                      placeholder={
                        mode === "edit"
                          ? "Leave blank to keep current"
                          : "Paste your TOTP secret (base32 format)"
                      }
                      {...field}
                    />
                  </FormControl>
                  <p className="text-xs text-muted-foreground">
                    Paste your TOTP secret (base32 format) to enable one-time password generation
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Controller
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes</FormLabel>
                  <TiptapEditor
                    content={field.value ?? ""}
                    onChange={field.onChange}
                    orgId={orgId}
                    placeholder="Additional notes..."
                    className="min-h-[120px]"
                  />
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {mode === "create" ? "Create" : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
