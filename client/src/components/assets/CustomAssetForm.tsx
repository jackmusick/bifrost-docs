import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Form, FormField, FormItem } from "@/components/ui/form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { CustomFieldInput } from "./CustomFieldInput";
import type {
  CustomAsset,
  CustomAssetCreate,
  CustomAssetUpdate,
  CustomAssetType,
  FieldDefinition,
} from "@/hooks/useCustomAssets";

interface CustomAssetFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: CustomAssetCreate | CustomAssetUpdate) => void;
  isSubmitting: boolean;
  mode: "create" | "edit";
  assetType: CustomAssetType;
  initialData?: CustomAsset;
}

export function CustomAssetForm({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
  mode,
  assetType,
  initialData,
}: CustomAssetFormProps) {
  // Build dynamic schema based on field definitions
  const { schema, defaultValues } = useMemo(() => {
    const fieldSchemas: Record<string, z.ZodTypeAny> = {};
    const defaults: Record<string, unknown> = {};

    for (const field of assetType.fields) {
      // Skip header fields
      if (field.type === "header") continue;

      let fieldSchema: z.ZodTypeAny;

      switch (field.type) {
        case "text":
        case "textbox":
          fieldSchema = z.string();
          if (field.required) {
            fieldSchema = (fieldSchema as z.ZodString).min(1, `${field.name} is required`);
          }
          break;

        case "password":
        case "totp":
          // Password/TOTP fields are optional in edit mode (leave blank to keep current)
          fieldSchema = z.string();
          if (field.required && mode === "create") {
            fieldSchema = (fieldSchema as z.ZodString).min(1, `${field.name} is required`);
          }
          break;

        case "number":
          if (field.required) {
            fieldSchema = z.number({ message: `${field.name} is required` });
          } else {
            fieldSchema = z.union([z.number(), z.null()]);
          }
          break;

        case "date":
          fieldSchema = z.string();
          if (field.required) {
            fieldSchema = (fieldSchema as z.ZodString).min(1, `${field.name} is required`);
          }
          break;

        case "checkbox":
          fieldSchema = z.boolean();
          break;

        case "select":
          fieldSchema = z.string();
          if (field.required) {
            fieldSchema = (fieldSchema as z.ZodString).min(1, `${field.name} is required`);
          }
          break;

        default:
          fieldSchema = z.string();
      }

      fieldSchemas[field.key] = fieldSchema;

      // Set default values
      if (initialData?.values[field.key] !== undefined) {
        defaults[field.key] = initialData.values[field.key];
      } else if (field.default_value !== null) {
        if (field.type === "checkbox") {
          defaults[field.key] = field.default_value === "true";
        } else if (field.type === "number") {
          defaults[field.key] = Number(field.default_value);
        } else {
          defaults[field.key] = field.default_value;
        }
      } else {
        // Set empty defaults based on type
        switch (field.type) {
          case "checkbox":
            defaults[field.key] = false;
            break;
          case "number":
            defaults[field.key] = null;
            break;
          default:
            defaults[field.key] = "";
        }
      }
    }

    const formSchema = z.object({
      values: z.object(fieldSchemas),
    });

    return {
      schema: formSchema,
      defaultValues: {
        values: defaults,
      },
    };
  }, [assetType.fields, initialData, mode]);

  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues,
  });

  // Reset form when dialog opens or data changes
  useEffect(() => {
    if (open) {
      form.reset(defaultValues);
    }
  }, [open, defaultValues, form]);

  const handleSubmit = (data: { values: Record<string, unknown> }) => {
    // Clean up values - remove empty strings and nulls for non-required fields
    const cleanedValues: Record<string, unknown> = {};
    for (const field of assetType.fields) {
      if (field.type === "header") continue;
      const value = data.values[field.key];
      if (value !== undefined && value !== "" && value !== null) {
        cleanedValues[field.key] = value;
      }
    }
    onSubmit({ values: cleanedValues });
  };

  // Group fields by headers
  const groupedFields = useMemo(() => {
    const groups: { header: string | null; fields: FieldDefinition[] }[] = [];
    let currentGroup: { header: string | null; fields: FieldDefinition[] } = {
      header: null,
      fields: [],
    };

    for (const field of assetType.fields) {
      if (field.type === "header") {
        if (currentGroup.fields.length > 0 || currentGroup.header !== null) {
          groups.push(currentGroup);
        }
        currentGroup = { header: field.name, fields: [] };
      } else {
        currentGroup.fields.push(field);
      }
    }

    if (currentGroup.fields.length > 0 || currentGroup.header !== null) {
      groups.push(currentGroup);
    }

    return groups;
  }, [assetType.fields]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === "create" ? `Add ${assetType.name}` : `Edit ${assetType.name}`}
          </DialogTitle>
          <DialogDescription>
            {mode === "create"
              ? `Create a new ${assetType.name.toLowerCase()} asset.`
              : `Update the ${assetType.name.toLowerCase()} details.`}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {groupedFields.map((group, groupIndex) => (
              <div key={groupIndex} className="space-y-4">
                {group.header && (
                  <div className="border-b pb-2 pt-2">
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                      {group.header}
                    </h4>
                  </div>
                )}
                <div className="grid gap-4">
                  {group.fields.map((field) => (
                    <FormField
                      key={field.key}
                      control={form.control}
                      name={`values.${field.key}`}
                      render={({ field: formField, fieldState }) => (
                        <FormItem>
                          <CustomFieldInput
                            field={field}
                            value={formField.value}
                            onChange={formField.onChange}
                            error={fieldState.error?.message}
                            mode={mode}
                          />
                        </FormItem>
                      )}
                    />
                  ))}
                </div>
              </div>
            ))}

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
