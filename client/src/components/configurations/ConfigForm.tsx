import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { Loader2 } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  Configuration,
  ConfigurationCreate,
  ConfigurationUpdate,
  ConfigurationType,
  ConfigurationStatus,
} from "@/hooks/useConfigurations";

const schema = z.object({
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

type FormValues = z.infer<typeof schema>;

interface ConfigFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: ConfigurationCreate | ConfigurationUpdate) => void;
  isSubmitting: boolean;
  mode: "create" | "edit";
  initialData?: Configuration;
  types: ConfigurationType[];
  statuses: ConfigurationStatus[];
  orgId: string;
}

export function ConfigForm({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
  mode,
  initialData,
  types,
  statuses,
  orgId,
}: ConfigFormProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initialData?.name ?? "",
      configuration_type_id: initialData?.configuration_type_id ?? undefined,
      configuration_status_id: initialData?.configuration_status_id ?? undefined,
      serial_number: initialData?.serial_number ?? "",
      asset_tag: initialData?.asset_tag ?? "",
      manufacturer: initialData?.manufacturer ?? "",
      model: initialData?.model ?? "",
      ip_address: initialData?.ip_address ?? "",
      mac_address: initialData?.mac_address ?? "",
      notes: initialData?.notes ?? "",
    },
  });

  const handleSubmit = (values: FormValues) => {
    const data: ConfigurationCreate | ConfigurationUpdate = {
      name: values.name,
    };

    if (values.configuration_type_id) data.configuration_type_id = values.configuration_type_id;
    if (values.configuration_status_id) data.configuration_status_id = values.configuration_status_id;
    if (values.serial_number) data.serial_number = values.serial_number;
    if (values.asset_tag) data.asset_tag = values.asset_tag;
    if (values.manufacturer) data.manufacturer = values.manufacturer;
    if (values.model) data.model = values.model;
    if (values.ip_address) data.ip_address = values.ip_address;
    if (values.mac_address) data.mac_address = values.mac_address;
    if (values.notes) data.notes = values.notes;

    onSubmit(data);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? "Create Configuration" : "Edit Configuration"}
          </DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? "Add a new configuration item."
              : "Update the configuration details."}
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
                    <Input placeholder="e.g., Web Server 01" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="configuration_type_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Type</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select type..." />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {types.map((type) => (
                          <SelectItem key={type.id} value={type.id}>
                            {type.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="configuration_status_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Status</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      defaultValue={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select status..." />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {statuses.map((status) => (
                          <SelectItem key={status.id} value={status.id}>
                            {status.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="manufacturer"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Manufacturer</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., Dell" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="model"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Model</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., PowerEdge R750" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="serial_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Serial Number</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., ABC123456" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="asset_tag"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Asset Tag</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., IT-001234" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="ip_address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>IP Address</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., 192.168.1.100" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="mac_address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>MAC Address</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., 00:1A:2B:3C:4D:5E" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

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
