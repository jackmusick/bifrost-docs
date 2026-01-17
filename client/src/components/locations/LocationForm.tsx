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
import type { Location, LocationCreate, LocationUpdate } from "@/hooks/useLocations";

const schema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface LocationFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: LocationCreate | LocationUpdate) => void;
  isSubmitting: boolean;
  mode: "create" | "edit";
  initialData?: Location;
  orgId: string;
}

export function LocationForm({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
  mode,
  initialData,
  orgId,
}: LocationFormProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initialData?.name ?? "",
      notes: initialData?.notes ?? "",
    },
  });

  const handleSubmit = (values: FormValues) => {
    const data: LocationCreate | LocationUpdate = {
      name: values.name,
    };

    if (values.notes) data.notes = values.notes;

    onSubmit(data);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? "Create Location" : "Edit Location"}
          </DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? "Add a new location to your organization."
              : "Update the location details."}
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
                    <Input placeholder="e.g., Main Office" {...field} />
                  </FormControl>
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
                    placeholder="Additional notes about this location..."
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
