import { useState } from "react";
import { CircleCheckBig, Plus, Pencil, Trash2, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import {
  useConfigurationStatuses,
  useCreateConfigurationStatus,
  useUpdateConfigurationStatus,
  useDeleteConfigurationStatus,
  useDeactivateConfigurationStatus,
  useActivateConfigurationStatus,
  type ConfigurationStatus,
} from "@/hooks/useConfigurations";
import { toast } from "sonner";

const formSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
});

type FormValues = z.infer<typeof formSchema>;

export function ConfigurationStatusesSettings() {
  const [formOpen, setFormOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editingStatus, setEditingStatus] = useState<ConfigurationStatus | null>(null);

  const { data: statuses, isLoading } = useConfigurationStatuses({ includeInactive: true });
  const createStatus = useCreateConfigurationStatus();
  const updateStatus = useUpdateConfigurationStatus();
  const deleteStatus = useDeleteConfigurationStatus();
  const deactivateStatus = useDeactivateConfigurationStatus();
  const activateStatus = useActivateConfigurationStatus();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
    },
  });

  const openCreate = () => {
    setEditingStatus(null);
    form.reset({ name: "" });
    setFormOpen(true);
  };

  const openEdit = (status: ConfigurationStatus) => {
    setEditingStatus(status);
    form.reset({ name: status.name });
    setFormOpen(true);
  };

  const handleSubmit = async (values: FormValues) => {
    try {
      if (editingStatus) {
        await updateStatus.mutateAsync({ id: editingStatus.id, data: values });
        toast.success("Configuration status updated successfully");
      } else {
        await createStatus.mutateAsync(values);
        toast.success("Configuration status created successfully");
      }
      setFormOpen(false);
      form.reset();
      setEditingStatus(null);
    } catch {
      toast.error(
        editingStatus
          ? "Failed to update configuration status"
          : "Failed to create configuration status"
      );
    }
  };

  const handleDelete = async () => {
    if (!editingStatus) return;
    try {
      await deleteStatus.mutateAsync(editingStatus.id);
      toast.success("Configuration status deleted successfully");
      setDeleteOpen(false);
      setEditingStatus(null);
    } catch {
      toast.error("Failed to delete configuration status. It may have configurations - try deactivating instead.");
    }
  };

  const handleToggleActive = async (status: ConfigurationStatus, checked: boolean) => {
    try {
      if (checked) {
        await activateStatus.mutateAsync(status.id);
        toast.success(`"${status.name}" activated`);
      } else {
        await deactivateStatus.mutateAsync(status.id);
        toast.success(`"${status.name}" deactivated`);
      }
    } catch {
      toast.error(checked ? "Failed to activate status" : "Failed to deactivate status");
    }
  };

  const isSubmitting = createStatus.isPending || updateStatus.isPending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Configuration Statuses</h2>
          <p className="text-sm text-muted-foreground">
            Manage statuses used to track configuration lifecycle across all organizations
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Add Status
        </Button>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : !statuses?.length ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <CircleCheckBig className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium mb-1">No configuration statuses</h3>
            <p className="text-sm text-muted-foreground text-center mb-4">
              Create statuses to track the lifecycle of your configurations
            </p>
            <Button onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add Status
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">All Configuration Statuses</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Configurations</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {statuses.map((status) => (
                  <TableRow key={status.id} className={!status.is_active ? "opacity-50" : ""}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <CircleCheckBig className="h-4 w-4 text-muted-foreground" />
                        {status.name}
                        {!status.is_active && (
                          <Badge variant="secondary" className="text-xs">
                            Inactive
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {status.configuration_count}
                    </TableCell>
                    <TableCell>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div>
                            <Switch
                              checked={status.is_active}
                              onCheckedChange={(checked) => handleToggleActive(status, checked)}
                              disabled={deactivateStatus.isPending || activateStatus.isPending}
                            />
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          {status.is_active ? "Deactivate (hide from use)" : "Activate"}
                        </TooltipContent>
                      </Tooltip>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(status.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => openEdit(status)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-destructive hover:text-destructive"
                                disabled={status.configuration_count > 0}
                                onClick={() => {
                                  setEditingStatus(status);
                                  setDeleteOpen(true);
                                }}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            {status.configuration_count > 0
                              ? `Cannot delete - ${status.configuration_count} configurations exist. Deactivate instead.`
                              : "Delete permanently"}
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingStatus ? "Edit Configuration Status" : "Add Configuration Status"}
            </DialogTitle>
            <DialogDescription>
              {editingStatus
                ? "Update the name of this configuration status."
                : "Create a new status to track configuration lifecycle."}
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., Active, Retired, Pending" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setFormOpen(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {editingStatus ? "Save Changes" : "Create Status"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Configuration Status"
        description={`Are you sure you want to delete "${editingStatus?.name}"? Configurations using this status will have their status cleared.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteStatus.isPending}
      />
    </div>
  );
}
