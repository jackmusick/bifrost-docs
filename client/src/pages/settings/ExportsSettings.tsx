/**
 * ExportsSettings Page
 *
 * Allows administrators to create and manage data exports.
 * Exports are ZIP files containing CSV data for all entity types.
 */

import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  Loader2,
  Download,
  Plus,
  Trash2,
  AlertTriangle,
  FileArchive,
  Clock,
  CheckCircle,
  XCircle,
  RefreshCw,
  Building2,
  Check,
  ChevronsUpDown,
  Globe,
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
import { Progress } from "@/components/ui/progress";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import {
  useExports,
  useCreateExport,
  useRevokeExport,
} from "@/hooks/useExports";
import { useOrganizations } from "@/hooks/useOrganizations";
import { useWebSocketChannel } from "@/hooks/useWebSocket";
import { exportsApi, type Export, type ExportStatus } from "@/lib/api-client";

// Form validation schema
const createExportSchema = z.object({
  expires_in_days: z.string().min(1, "Expiration is required"),
  organization_ids: z.array(z.string()).optional(),
});

type CreateExportFormData = z.infer<typeof createExportSchema>;

// WebSocket progress data type
interface ExportProgress {
  stage: string;
  current?: number;
  total?: number;
  percent?: number;
  entity_type?: string;
  file_size_bytes?: number;
  error?: string;
}

export function ExportsSettings() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [activeExportId, setActiveExportId] = useState<string | null>(null);
  const [selectedOrgIds, setSelectedOrgIds] = useState<string[]>([]);
  const [exportAllOrgs, setExportAllOrgs] = useState(true);
  const [orgSelectorOpen, setOrgSelectorOpen] = useState(false);

  const { data: exports, isLoading, error, refetch } = useExports();
  const { data: organizations } = useOrganizations();
  const createExportMutation = useCreateExport();
  const revokeExportMutation = useRevokeExport();

  const form = useForm<CreateExportFormData>({
    resolver: zodResolver(createExportSchema),
    defaultValues: {
      expires_in_days: "7",
      organization_ids: [],
    },
  });

  // WebSocket channel for active export progress
  const { latestMessage, clearMessages } = useWebSocketChannel<ExportProgress>(
    activeExportId ? `export:${activeExportId}` : "",
    {
      enabled: !!activeExportId,
      autoConnect: true,
    }
  );

  // Handle export completion or failure via callback instead of effect
  const handleExportMessage = useCallback((message: { type: string; data: ExportProgress }) => {
    if (message.type === "completed" || message.type === "failed") {
      const isSuccess = message.type === "completed";
      if (isSuccess) {
        toast.success("Export completed successfully");
      } else {
        toast.error(`Export failed: ${message.data.error || "Unknown error"}`);
      }
      // Use setTimeout to avoid setState during render
      setTimeout(() => {
        setActiveExportId(null);
        clearMessages();
        refetch();
      }, 0);
    }
  }, [clearMessages, refetch]);

  // Trigger message handler when new message arrives
  useEffect(() => {
    if (latestMessage) {
      handleExportMessage(latestMessage);
    }
  }, [latestMessage, handleExportMessage]);

  const onSubmit = useCallback(async (data: CreateExportFormData) => {
    try {
      const result = await createExportMutation.mutateAsync({
        expires_in_days: parseInt(data.expires_in_days, 10),
        organization_ids: exportAllOrgs ? undefined : selectedOrgIds.length > 0 ? selectedOrgIds : undefined,
      });
      setActiveExportId(result.id);
      setCreateDialogOpen(false);
      form.reset();
      setSelectedOrgIds([]);
      setExportAllOrgs(true);
      toast.info("Export started. This may take a few minutes.");
    } catch {
      toast.error("Failed to start export");
    }
  }, [createExportMutation, form, exportAllOrgs, selectedOrgIds]);

  const handleDownload = useCallback(async (exportItem: Export) => {
    try {
      const response = await exportsApi.getDownloadUrl(exportItem.id);
      window.open(response.data.download_url, "_blank");
    } catch {
      toast.error("Failed to get download URL");
    }
  }, []);

  const handleRevoke = useCallback(async (id: string) => {
    try {
      await revokeExportMutation.mutateAsync(id);
      toast.success("Export revoked");
    } catch {
      toast.error("Failed to revoke export");
    }
  }, [revokeExportMutation]);

  const formatDate = useCallback((dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }, []);

  const formatFileSize = useCallback((bytes: number | null) => {
    if (!bytes) return "-";
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  }, []);

  const isExpired = useCallback((expiresAt: string) => {
    return new Date(expiresAt) < new Date();
  }, []);

  const getStatusBadge = useCallback((status: ExportStatus, revoked: boolean, expired: boolean) => {
    if (revoked) {
      return <Badge variant="secondary">Revoked</Badge>;
    }
    if (expired) {
      return <Badge variant="destructive">Expired</Badge>;
    }
    switch (status) {
      case "pending":
        return (
          <Badge variant="outline" className="gap-1">
            <Clock className="h-3 w-3" />
            Pending
          </Badge>
        );
      case "processing":
        return (
          <Badge variant="default" className="gap-1 bg-blue-500">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Processing
          </Badge>
        );
      case "completed":
        return (
          <Badge variant="default" className="gap-1 bg-green-500">
            <CheckCircle className="h-3 w-3" />
            Completed
          </Badge>
        );
      case "failed":
        return (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  }, []);

  if (error) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
          <p className="text-lg font-medium mb-1">Failed to load exports</p>
          <p className="text-sm text-muted-foreground">Please try again later</p>
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
                  <FileArchive className="h-5 w-5" />
                  Data Exports
                </CardTitle>
                <CardDescription>
                  Export your organization data as downloadable ZIP files
                </CardDescription>
              </div>
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                New Export
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {/* Active export progress */}
            {activeExportId && latestMessage && latestMessage.type === "progress" && (
              <div className="mb-6 p-4 border rounded-lg bg-muted/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Generating Export...</span>
                  <span className="text-sm text-muted-foreground">
                    {latestMessage.data.stage}
                    {latestMessage.data.entity_type && ` (${latestMessage.data.entity_type})`}
                  </span>
                </div>
                <Progress value={latestMessage.data.percent || 0} className="h-2" />
                <div className="flex justify-between mt-1 text-xs text-muted-foreground">
                  <span>
                    {latestMessage.data.current || 0} / {latestMessage.data.total || 0}
                  </span>
                  <span>{Math.round(latestMessage.data.percent || 0)}%</span>
                </div>
              </div>
            )}

            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : exports && exports.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Created</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Organizations</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead className="w-[120px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {exports.map((exportItem: Export) => {
                    const expired = isExpired(exportItem.expires_at);
                    const revoked = !!exportItem.revoked_at;
                    const canDownload =
                      exportItem.status === "completed" && !revoked && !expired;

                    return (
                      <TableRow key={exportItem.id}>
                        <TableCell>{formatDate(exportItem.created_at)}</TableCell>
                        <TableCell>
                          {getStatusBadge(exportItem.status, revoked, expired)}
                        </TableCell>
                        <TableCell>
                          {exportItem.organization_ids
                            ? `${exportItem.organization_ids.length} orgs`
                            : "All"}
                        </TableCell>
                        <TableCell>{formatFileSize(exportItem.file_size_bytes)}</TableCell>
                        <TableCell>
                          <span className={expired ? "text-destructive" : ""}>
                            {formatDate(exportItem.expires_at)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            {canDownload && (
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleDownload(exportItem)}
                                title="Download"
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                            )}
                            {!revoked && (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    disabled={revokeExportMutation.isPending}
                                    title="Revoke"
                                  >
                                    <Trash2 className="h-4 w-4 text-destructive" />
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Revoke Export</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Are you sure you want to revoke this export? The
                                      download link will no longer work.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction
                                      onClick={() => handleRevoke(exportItem.id)}
                                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                    >
                                      Revoke
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileArchive className="h-12 w-12 text-muted-foreground/50 mb-4" />
                <p className="text-lg font-medium mb-1">No exports yet</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Create an export to download your organization data
                </p>
                <Button onClick={() => setCreateDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Your First Export
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Export information */}
        <Card>
          <CardHeader>
            <CardTitle>About Data Exports</CardTitle>
            <CardDescription>
              What is included in your export
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Exports include all your organization data in CSV format, packaged as a ZIP file:
              </p>
              <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                <li>Passwords (without decrypted values for security)</li>
                <li>Configurations</li>
                <li>Locations</li>
                <li>Documents</li>
                <li>Custom Assets</li>
              </ul>
              <p className="text-sm text-muted-foreground">
                Exports are available for download until their expiration date. Revoked exports
                cannot be downloaded.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Create Export Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create Data Export</DialogTitle>
            <DialogDescription>
              Create a new export of your organization data. This may take a few minutes
              depending on the amount of data.
            </DialogDescription>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {/* Organization Selection */}
              <div className="space-y-2">
                <FormLabel>Organizations</FormLabel>
                <Popover open={orgSelectorOpen} onOpenChange={setOrgSelectorOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={orgSelectorOpen}
                      className="w-full justify-between font-normal"
                    >
                      <span className="flex items-center gap-2 truncate">
                        {exportAllOrgs ? (
                          <>
                            <Globe className="h-4 w-4 shrink-0" />
                            <span>All Organizations</span>
                          </>
                        ) : selectedOrgIds.length > 0 ? (
                          <>
                            <Building2 className="h-4 w-4 shrink-0" />
                            <span>{selectedOrgIds.length} organization{selectedOrgIds.length !== 1 ? "s" : ""} selected</span>
                          </>
                        ) : (
                          <span className="text-muted-foreground">Select organizations...</span>
                        )}
                      </span>
                      <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
                    <Command>
                      <CommandInput placeholder="Search organizations..." />
                      <CommandList>
                        <CommandEmpty>No organization found.</CommandEmpty>
                        <CommandGroup>
                          <CommandItem
                            value="all-organizations"
                            onSelect={() => {
                              setExportAllOrgs(true);
                              setSelectedOrgIds([]);
                              setOrgSelectorOpen(false);
                            }}
                            className="cursor-pointer"
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4 shrink-0",
                                exportAllOrgs ? "opacity-100" : "opacity-0"
                              )}
                            />
                            <Globe className="mr-2 h-4 w-4 shrink-0" />
                            <span>All Organizations</span>
                          </CommandItem>
                        </CommandGroup>
                        <CommandSeparator />
                        <CommandGroup heading="Select specific organizations">
                          {organizations?.map((org) => {
                            const isSelected = selectedOrgIds.includes(org.id);
                            return (
                              <CommandItem
                                key={org.id}
                                value={org.name}
                                onSelect={() => {
                                  setExportAllOrgs(false);
                                  if (isSelected) {
                                    setSelectedOrgIds((prev) =>
                                      prev.filter((id) => id !== org.id)
                                    );
                                  } else {
                                    setSelectedOrgIds((prev) => [...prev, org.id]);
                                  }
                                }}
                                className="cursor-pointer"
                              >
                                <Check
                                  className={cn(
                                    "mr-2 h-4 w-4 shrink-0",
                                    isSelected ? "opacity-100" : "opacity-0"
                                  )}
                                />
                                <Building2 className="mr-2 h-4 w-4 shrink-0" />
                                <span className="truncate">{org.name}</span>
                              </CommandItem>
                            );
                          })}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
                <FormDescription>
                  Choose to export all organizations or select specific ones.
                </FormDescription>
              </div>

              <FormField
                control={form.control}
                name="expires_in_days"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Expiration</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        max={30}
                        placeholder="Days until expiration"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      The export will be available for download for this many days (1-30).
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
                  disabled={createExportMutation.isPending || (!exportAllOrgs && selectedOrgIds.length === 0)}
                >
                  {createExportMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Start Export
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </>
  );
}
