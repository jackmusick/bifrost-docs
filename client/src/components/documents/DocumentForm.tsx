import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { TiptapEditor } from "./TiptapEditor";
import type { Document, DocumentCreate, DocumentUpdate } from "@/hooks/useDocuments";

const schema = z.object({
  path: z.string().min(1, "Path is required"),
  name: z.string().min(1, "Name is required").max(255),
  content: z.string(),
});

type FormValues = z.infer<typeof schema>;

interface DocumentFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: DocumentCreate | DocumentUpdate) => void;
  isSubmitting: boolean;
  mode: "create" | "edit";
  initialData?: Document;
  defaultPath?: string;
  orgId: string;
}

export function DocumentForm({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
  mode,
  initialData,
  defaultPath = "/",
  orgId,
}: DocumentFormProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      path: initialData?.path ?? defaultPath,
      name: initialData?.name ?? "",
      content: initialData?.content ?? "",
    },
  });

  const handleSubmit = (values: FormValues) => {
    onSubmit(values);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? "Create Document" : "Edit Document"}
          </DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? "Create a new document with Markdown content."
              : "Update the document details and content."}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="path"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Path *</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., /guides" {...field} />
                    </FormControl>
                    <FormDescription>
                      Folder path for organizing documents
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., Getting Started" {...field} />
                    </FormControl>
                    <FormDescription>Document title</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="content"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Content</FormLabel>
                  <FormControl>
                    <TiptapEditor
                      content={field.value}
                      onChange={field.onChange}
                      orgId={orgId}
                      placeholder="Write your content here..."
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
