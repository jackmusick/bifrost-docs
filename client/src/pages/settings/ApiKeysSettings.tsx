import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  Loader2,
  Key,
  Plus,
  Copy,
  Check,
  Trash2,
  AlertTriangle,
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
  FormDescription,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useApiKeys, useCreateApiKey, useDeleteApiKey } from "@/hooks/useApiKeys";
import type { ApiKey, CreateApiKeyResponse } from "@/lib/api-client";

const createKeySchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name is too long"),
  expires_days: z.string().optional(),
});

type CreateKeyFormData = z.infer<typeof createKeySchema>;

export function ApiKeysSettings() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newKeyDialogOpen, setNewKeyDialogOpen] = useState(false);
  const [newKey, setNewKey] = useState<CreateApiKeyResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: apiKeys, isLoading, error } = useApiKeys();
  const createApiKeyMutation = useCreateApiKey();
  const deleteApiKeyMutation = useDeleteApiKey();

  const form = useForm<CreateKeyFormData>({
    resolver: zodResolver(createKeySchema),
    defaultValues: {
      name: "",
      expires_days: undefined,
    },
  });

  async function onSubmit(data: CreateKeyFormData) {
    try {
      const days = data.expires_days ? parseInt(data.expires_days, 10) : undefined;
      let expires_at: string | undefined;
      if (days && !isNaN(days) && days > 0) {
        // eslint-disable-next-line react-hooks/purity -- This is inside an event handler, not during render
        const now = Date.now();
        expires_at = new Date(now + days * 24 * 60 * 60 * 1000).toISOString();
      }

      const result = await createApiKeyMutation.mutateAsync({
        name: data.name,
        expires_at,
      });

      setNewKey(result);
      setCreateDialogOpen(false);
      setNewKeyDialogOpen(true);
      form.reset();
    } catch {
      toast.error("Failed to create API key");
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("API key copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  }

  function formatDate(dateString: string | null) {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function isExpired(expiresAt: string | null) {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
          <p className="text-lg font-medium mb-1">Failed to load API keys</p>
          <p className="text-sm text-muted-foreground">
            Please try again later
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-5 w-5" />
                  API Keys
                </CardTitle>
                <CardDescription>
                  Manage API keys for programmatic access to your account
                </CardDescription>
              </div>
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Key
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : apiKeys && apiKeys.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Key</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead>Last Used</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {apiKeys.map((key: ApiKey) => (
                    <TableRow key={key.id}>
                      <TableCell className="font-medium">{key.name}</TableCell>
                      <TableCell>
                        <code className="bg-muted px-2 py-1 rounded text-sm">
                          {key.key_prefix}...
                        </code>
                      </TableCell>
                      <TableCell>{formatDate(key.created_at)}</TableCell>
                      <TableCell>
                        {key.expires_at ? formatDate(key.expires_at) : "Never"}
                      </TableCell>
                      <TableCell>{formatDate(key.last_used_at)}</TableCell>
                      <TableCell>
                        {!key.is_active ? (
                          <Badge variant="secondary">Inactive</Badge>
                        ) : isExpired(key.expires_at) ? (
                          <Badge variant="destructive">Expired</Badge>
                        ) : (
                          <Badge variant="default">Active</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              disabled={deleteApiKeyMutation.isPending}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete API Key</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete "{key.name}"?
                                This action cannot be undone and any applications
                                using this key will lose access.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() =>
                                  deleteApiKeyMutation.mutate(key.id)
                                }
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              >
                                Delete
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Key className="h-12 w-12 text-muted-foreground/50 mb-4" />
                <p className="text-lg font-medium mb-1">No API keys yet</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Create an API key to access your account programmatically
                </p>
                <Button onClick={() => setCreateDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Your First Key
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Usage Information */}
        <Card>
          <CardHeader>
            <CardTitle>Using API Keys</CardTitle>
            <CardDescription>
              Include your API key in the Authorization header
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-muted p-4 rounded-lg">
              <code className="text-sm">
                Authorization: Bearer YOUR_API_KEY
              </code>
            </div>
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">API Documentation</p>
              <div className="flex gap-3">
                <a
                  href="/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline"
                >
                  Interactive API Reference →
                </a>
                <a
                  href="/openapi.json"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline"
                >
                  OpenAPI Schema (JSON) →
                </a>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Keep your API keys secure. Never share them publicly or commit
              them to version control.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Create Key Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>
              Create a new API key for programmatic access. You'll only see the
              key once after creation.
            </DialogDescription>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g., Production Server"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      A descriptive name to help you identify this key
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="expires_days"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Expiration (Optional)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="Days until expiration"
                        min={0}
                        max={365}
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Leave empty for no expiration. Maximum 365 days.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={createApiKeyMutation.isPending}
                >
                  {createApiKeyMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Create Key
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* New Key Created Dialog */}
      <Dialog open={newKeyDialogOpen} onOpenChange={setNewKeyDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>API Key Created</DialogTitle>
            <DialogDescription>
              Copy your API key now. You won't be able to see it again.
            </DialogDescription>
          </DialogHeader>

          {newKey && (
            <div className="space-y-4">
              <div className="bg-muted p-4 rounded-lg">
                <div className="flex items-center justify-between gap-2">
                  <code className="text-sm font-mono break-all flex-1">
                    {newKey.key}
                  </code>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => copyToClipboard(newKey.key)}
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="flex items-center gap-2 text-amber-600 bg-amber-50 dark:bg-amber-950/20 p-3 rounded-lg">
                <AlertTriangle className="h-5 w-5 shrink-0" />
                <p className="text-sm">
                  Make sure to copy your API key now. You won't be able to see
                  it again!
                </p>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              onClick={() => {
                setNewKeyDialogOpen(false);
                setNewKey(null);
              }}
            >
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
