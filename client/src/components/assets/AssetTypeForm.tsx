import { useState, useEffect } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import {
  Loader2,
  Plus,
  Trash2,
  GripVertical,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Card, CardContent } from "@/components/ui/card";
import type {
  CustomAssetType,
  CustomAssetTypeCreate,
  CustomAssetTypeUpdate,
  FieldType,
} from "@/hooks/useCustomAssets";

const FIELD_TYPES: { value: FieldType; label: string }[] = [
  { value: "text", label: "Text (single line)" },
  { value: "textbox", label: "Text (multiline)" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
  { value: "checkbox", label: "Checkbox" },
  { value: "select", label: "Dropdown" },
  { value: "header", label: "Section Header" },
  { value: "password", label: "Password (encrypted)" },
  { value: "totp", label: "TOTP Secret (encrypted)" },
];

const fieldSchema = z.object({
  key: z.string().min(1, "Key is required").regex(/^[a-z0-9_]+$/, "Key must be lowercase letters, numbers, and underscores only"),
  name: z.string().min(1, "Name is required").max(100),
  type: z.enum(["text", "textbox", "number", "date", "checkbox", "select", "header", "password", "totp"]),
  required: z.boolean(),
  show_in_list: z.boolean(),
  hint: z.string().nullable(),
  default_value: z.string().nullable(),
  options: z.array(z.string()).nullable(),
});

const schema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  fields: z.array(fieldSchema).min(1, "At least one field is required"),
  display_field_key: z.string().nullable(),
});

type FormValues = z.infer<typeof schema>;

interface AssetTypeFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: CustomAssetTypeCreate | CustomAssetTypeUpdate) => void;
  isSubmitting: boolean;
  mode: "create" | "edit";
  initialData?: CustomAssetType;
}

export function AssetTypeForm({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
  mode,
  initialData,
}: AssetTypeFormProps) {
  const [expandedFields, setExpandedFields] = useState<number[]>([0]);

  const getInitialFields = () => {
    if (!initialData?.fields) {
      return [
        {
          key: "",
          name: "",
          type: "text" as FieldType,
          required: false,
          show_in_list: false,
          hint: null,
          default_value: null,
          options: null,
        },
      ];
    }
    return initialData.fields.map((field) => ({
      ...field,
    }));
  };

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initialData?.name ?? "",
      fields: getInitialFields(),
      display_field_key: initialData?.display_field_key ?? null,
    },
  });

  const { fields, append, remove, move } = useFieldArray({
    control: form.control,
    name: "fields",
  });

  const toggleExpanded = (index: number) => {
    setExpandedFields((prev) =>
      prev.includes(index)
        ? prev.filter((i) => i !== index)
        : [...prev, index]
    );
  };

  const handleSubmit = (values: FormValues) => {
    onSubmit({
      name: values.name,
      fields: values.fields,
      display_field_key: values.display_field_key,
    });
  };

  // Watch all fields to build display field options
  const watchedFields = form.watch("fields");

  // Get fields that can be used as display field
  const getDisplayFieldOptions = () => {
    if (!watchedFields) return [];

    // Prefer text/textbox fields
    const textFields = watchedFields
      .filter(f => (f.type === "text" || f.type === "textbox") && f.key)
      .map(f => ({ key: f.key, name: f.name || f.key }));

    if (textFields.length > 0) return textFields;

    // Fallback to any non-header field
    return watchedFields
      .filter(f => f.type !== "header" && f.key)
      .map(f => ({ key: f.key, name: f.name || f.key }));
  };

  const addField = () => {
    const newIndex = fields.length;
    append({
      key: "",
      name: "",
      type: "text" as FieldType,
      required: false,
      show_in_list: false,
      hint: null,
      default_value: null,
      options: null,
    });
    setExpandedFields((prev) => [...prev, newIndex]);
  };

  const moveField = (index: number, direction: "up" | "down") => {
    const newIndex = direction === "up" ? index - 1 : index + 1;
    if (newIndex >= 0 && newIndex < fields.length) {
      move(index, newIndex);
      setExpandedFields((prev) =>
        prev.map((i) => {
          if (i === index) return newIndex;
          if (i === newIndex) return index;
          return i;
        })
      );
    }
  };

  const watchFieldType = (index: number) => form.watch(`fields.${index}.type`);

  // Reset form when dialog opens with new data
  useEffect(() => {
    if (open) {
      const initialFields = initialData?.fields
        ? initialData.fields.map((field) => ({ ...field }))
        : [
            {
              key: "",
              name: "",
              type: "text" as FieldType,
              required: false,
              show_in_list: false,
              hint: null,
              default_value: null,
              options: null,
            },
          ];

      form.reset({
        name: initialData?.name ?? "",
        fields: initialFields,
        display_field_key: initialData?.display_field_key ?? null,
      });
    }
  }, [open, initialData, form]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? "Create Asset Type" : "Edit Asset Type"}
          </DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? "Define a new custom asset type with fields."
              : "Update the asset type name and field schema."}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Type Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g., Servers, Network Devices" {...field} />
                  </FormControl>
                  <FormDescription>
                    The name for this category of assets
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="display_field_key"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Display Field</FormLabel>
                  <Select
                    value={field.value || ""}
                    onValueChange={(v) => field.onChange(v || null)}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Auto-detect (first text field)" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="">Auto-detect (first text field)</SelectItem>
                      {getDisplayFieldOptions().map((opt) => (
                        <SelectItem key={opt.key} value={opt.key}>
                          {opt.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    The field used to identify assets in lists and search results
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <FormLabel>Fields *</FormLabel>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addField}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Field
                </Button>
              </div>

              <div className="space-y-2">
                {fields.map((field, index) => (
                  <Card key={field.id}>
                    <Collapsible
                      open={expandedFields.includes(index)}
                      onOpenChange={() => toggleExpanded(index)}
                    >
                      <div className="flex items-center gap-2 p-3 border-b">
                        <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                        <CollapsibleTrigger asChild>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="flex-1 justify-start h-auto py-1"
                          >
                            {expandedFields.includes(index) ? (
                              <ChevronDown className="h-4 w-4 mr-2" />
                            ) : (
                              <ChevronUp className="h-4 w-4 mr-2" />
                            )}
                            <span className="font-medium">
                              {form.watch(`fields.${index}.name`) || `Field ${index + 1}`}
                            </span>
                            <span className="text-muted-foreground text-xs ml-2">
                              ({form.watch(`fields.${index}.type`)})
                            </span>
                          </Button>
                        </CollapsibleTrigger>
                        <div className="flex items-center gap-1">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            disabled={index === 0}
                            onClick={() => moveField(index, "up")}
                          >
                            <ChevronUp className="h-4 w-4" />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            disabled={index === fields.length - 1}
                            onClick={() => moveField(index, "down")}
                          >
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            disabled={fields.length === 1}
                            onClick={() => remove(index)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      <CollapsibleContent>
                        <CardContent className="pt-4 space-y-4">
                          <div className="grid grid-cols-2 gap-4">
                            <FormField
                              control={form.control}
                              name={`fields.${index}.name`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Display Name *</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="e.g., IP Address"
                                      {...field}
                                      onChange={(e) => {
                                        field.onChange(e);
                                        // Auto-generate key from name
                                        const key = e.target.value
                                          .toLowerCase()
                                          .replace(/[^a-z0-9]+/g, "_")
                                          .replace(/^_+|_+$/g, "");
                                        form.setValue(`fields.${index}.key`, key);
                                      }}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />

                            <FormField
                              control={form.control}
                              name={`fields.${index}.key`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Field Key *</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="e.g., ip_address"
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            <FormField
                              control={form.control}
                              name={`fields.${index}.type`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Field Type *</FormLabel>
                                  <Select
                                    value={field.value}
                                    onValueChange={field.onChange}
                                  >
                                    <FormControl>
                                      <SelectTrigger>
                                        <SelectValue />
                                      </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                      {FIELD_TYPES.map((type) => (
                                        <SelectItem key={type.value} value={type.value}>
                                          {type.label}
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
                              name={`fields.${index}.hint`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Hint Text</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="Help text for users"
                                      value={field.value || ""}
                                      onChange={(e) =>
                                        field.onChange(e.target.value || null)
                                      }
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>

                          {watchFieldType(index) === "select" && (
                            <FormField
                              control={form.control}
                              name={`fields.${index}.options`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Options *</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="Option 1, Option 2, Option 3"
                                      value={(field.value || []).join(", ")}
                                      onChange={(e) => {
                                        const options = e.target.value
                                          .split(",")
                                          .map((o) => o.trim())
                                          .filter((o) => o);
                                        field.onChange(options.length > 0 ? options : null);
                                      }}
                                    />
                                  </FormControl>
                                  <FormDescription>
                                    Comma-separated list of dropdown options
                                  </FormDescription>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          )}

                          {watchFieldType(index) !== "header" && (
                            <FormField
                              control={form.control}
                              name={`fields.${index}.default_value`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Default Value</FormLabel>
                                  <FormControl>
                                    <Input
                                      placeholder="Default value (optional)"
                                      value={field.value || ""}
                                      onChange={(e) =>
                                        field.onChange(e.target.value || null)
                                      }
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          )}

                          {watchFieldType(index) !== "header" && (
                            <div className="flex flex-wrap gap-6">
                              <FormField
                                control={form.control}
                                name={`fields.${index}.required`}
                                render={({ field }) => (
                                  <FormItem className="flex items-center gap-2 space-y-0">
                                    <FormControl>
                                      <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                      />
                                    </FormControl>
                                    <FormLabel className="font-normal cursor-pointer">
                                      Required field
                                    </FormLabel>
                                  </FormItem>
                                )}
                              />

                              <FormField
                                control={form.control}
                                name={`fields.${index}.show_in_list`}
                                render={({ field }) => (
                                  <FormItem className="flex items-center gap-2 space-y-0">
                                    <FormControl>
                                      <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                      />
                                    </FormControl>
                                    <FormLabel className="font-normal cursor-pointer">
                                      Show in list view
                                    </FormLabel>
                                  </FormItem>
                                )}
                              />
                            </div>
                          )}
                        </CardContent>
                      </CollapsibleContent>
                    </Collapsible>
                  </Card>
                ))}
              </div>

              {form.formState.errors.fields?.message && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.fields.message}
                </p>
              )}
            </div>

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
                {mode === "create" ? "Create Type" : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
