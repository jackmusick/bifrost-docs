import { useState } from "react";
import { Server, Plus, Pencil, Trash2, Loader2 } from "lucide-react";
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
  useConfigurationTypes,
  useCreateConfigurationType,
  useUpdateConfigurationType,
  useDeleteConfigurationType,
  useDeactivateConfigurationType,
  useActivateConfigurationType,
  type ConfigurationType,
} from "@/hooks/useConfigurations";
import { toast } from "sonner";

const formSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
});

type FormValues = z.infer<typeof formSchema>;

export function ConfigurationTypesSettings() {
  const [formOpen, setFormOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editingType, setEditingType] = useState<ConfigurationType | null>(null);

  const { data: types, isLoading } = useConfigurationTypes({ includeInactive: true });
  const createType = useCreateConfigurationType();
  const updateType = useUpdateConfigurationType();
  const deleteType = useDeleteConfigurationType();
  const deactivateType = useDeactivateConfigurationType();
  const activateType = useActivateConfigurationType();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
    },
  });

  const openCreate = () => {
    setEditingType(null);
    form.reset({ name: "" });
    setFormOpen(true);
  };

  const openEdit = (type: ConfigurationType) => {
    setEditingType(type);
    form.reset({ name: type.name });
    setFormOpen(true);
  };

  const handleSubmit = async (values: FormValues) => {
    try {
      if (editingType) {
        await updateType.mutateAsync({ id: editingType.id, data: values });
        toast.success("Configuration type updated successfully");
      } else {
        await createType.mutateAsync(values);
        toast.success("Configuration type created successfully");
      }
      setFormOpen(false);
      form.reset();
      setEditingType(null);
    } catch {
      toast.error(
        editingType
          ? "Failed to update configuration type"
          : "Failed to create configuration type"
      );
    }
  };

  const handleDelete = async () => {
    if (!editingType) return;
    try {
      await deleteType.mutateAsync(editingType.id);
      toast.success("Configuration type deleted successfully");
      setDeleteOpen(false);
      setEditingType(null);
    } catch {
      toast.error("Failed to delete configuration type. It may have configurations - try deactivating instead.");
    }
  };

  const handleToggleActive = async (type: ConfigurationType, checked: boolean) => {
    try {
      if (checked) {
        await activateType.mutateAsync(type.id);
        toast.success(`"${type.name}" activated`);
      } else {
        await deactivateType.mutateAsync(type.id);
        toast.success(`"${type.name}" deactivated`);
      }
    } catch {
      toast.error(checked ? "Failed to activate type" : "Failed to deactivate type");
    }
  };

  const isSubmitting = createType.isPending || updateType.isPending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Configuration Types</h2>
          <p className="text-sm text-muted-foreground">
            Manage types used to categorize configurations across all organizations
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Add Type
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
      ) : !types?.length ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Server className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium mb-1">No configuration types</h3>
            <p className="text-sm text-muted-foreground text-center mb-4">
              Create configuration types to categorize your configurations
            </p>
            <Button onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add Type
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">All Configuration Types</CardTitle>
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
                {types.map((type) => (
                  <TableRow key={type.id} className={!type.is_active ? "opacity-50" : ""}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Server className="h-4 w-4 text-muted-foreground" />
                        {type.name}
                        {!type.is_active && (
                          <Badge variant="secondary" className="text-xs">
                            Inactive
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {type.configuration_count}
                    </TableCell>
                    <TableCell>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div>
                            <Switch
                              checked={type.is_active}
                              onCheckedChange={(checked) => handleToggleActive(type, checked)}
                              disabled={deactivateType.isPending || activateType.isPending}
                            />
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          {type.is_active ? "Deactivate (hide from use)" : "Activate"}
                        </TooltipContent>
                      </Tooltip>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(type.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => openEdit(type)}
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
                                disabled={type.configuration_count > 0}
                                onClick={() => {
                                  setEditingType(type);
                                  setDeleteOpen(true);
                                }}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            {type.configuration_count > 0
                              ? `Cannot delete - ${type.configuration_count} configurations exist. Deactivate instead.`
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
              {editingType ? "Edit Configuration Type" : "Add Configuration Type"}
            </DialogTitle>
            <DialogDescription>
              {editingType
                ? "Update the name of this configuration type."
                : "Create a new configuration type to categorize configurations."}
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
                      <Input placeholder="e.g., Servers, Workstations" {...field} />
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
                  {editingType ? "Save Changes" : "Create Type"}
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
        title="Delete Configuration Type"
        description={`Are you sure you want to delete "${editingType?.name}"? Configurations using this type will have their type cleared.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteType.isPending}
      />
    </div>
  );
}
