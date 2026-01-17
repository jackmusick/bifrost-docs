import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import type { Organization } from "@/lib/api-client";

const createSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  metadata: z.string().optional(),
});

const updateSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  metadata: z.string().optional(),
});

type CreateFormValues = z.infer<typeof createSchema>;
type UpdateFormValues = z.infer<typeof updateSchema>;

interface OrganizationFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: { name: string; metadata?: Record<string, any> }) => void;
  isSubmitting: boolean;
  mode: "create" | "edit";
  initialData?: Organization;
}

export function OrganizationForm({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
  mode,
  initialData,
}: OrganizationFormProps) {
  const form = useForm<CreateFormValues | UpdateFormValues>({
    resolver: zodResolver(mode === "create" ? createSchema : updateSchema),
    defaultValues: {
      name: initialData?.name ?? "",
      metadata: initialData?.metadata ? JSON.stringify(initialData.metadata, null, 2) : "",
    },
  });

  const handleSubmit = (values: CreateFormValues | UpdateFormValues) => {
    // Parse metadata if provided
    let metadata: Record<string, any> | undefined;
    if (values.metadata && values.metadata.trim()) {
      try {
        metadata = JSON.parse(values.metadata);
      } catch (error) {
        form.setError("metadata", {
          type: "manual",
          message: "Invalid JSON format",
        });
        return;
      }
    }

    onSubmit({
      name: values.name,
      ...(metadata && { metadata }),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? "Create Organization" : "Edit Organization"}
          </DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? "Add a new organization to the system."
              : "Update the organization details."}
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
                    <Input placeholder="e.g., Acme Corporation" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="metadata"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Metadata (JSON)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder='{"key": "value"}'
                      className="font-mono text-sm min-h-[120px]"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Optional JSON metadata for additional properties
                  </FormDescription>
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
