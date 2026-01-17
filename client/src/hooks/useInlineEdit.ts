import { useState, useCallback, useEffect } from "react";
import { useForm, type UseFormReturn, type DefaultValues, type FieldValues, type Resolver } from "react-hook-form";

interface UseInlineEditOptions<TFormValues extends FieldValues> {
  resolver: Resolver<TFormValues>;
  initialData: TFormValues;
  onSave: (data: TFormValues) => Promise<void>;
}

interface UseInlineEditReturn<TFormValues extends FieldValues> {
  isEditing: boolean;
  isDirty: boolean;
  isSaving: boolean;
  form: UseFormReturn<TFormValues>;
  startEditing: () => void;
  cancelEditing: () => void;
  saveChanges: () => Promise<void>;
}

/**
 * Hook for managing inline edit mode on detail pages.
 *
 * @example
 * const schema = z.object({ name: z.string() });
 * type FormValues = z.infer<typeof schema>;
 *
 * const { isEditing, form, startEditing, saveChanges } = useInlineEdit<FormValues>({
 *   resolver: zodResolver(schema),
 *   initialData: { name: entity.name },
 *   onSave: async (data) => await updateMutation.mutateAsync(data),
 * });
 */
export function useInlineEdit<TFormValues extends FieldValues>({
  resolver,
  initialData,
  onSave,
}: UseInlineEditOptions<TFormValues>): UseInlineEditReturn<TFormValues> {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const form = useForm<TFormValues>({
    resolver,
    defaultValues: initialData as DefaultValues<TFormValues>,
  });

  const isDirty = form.formState.isDirty;

  // Reset form when initialData changes (e.g., after save or external update)
  useEffect(() => {
    if (!isEditing) {
      form.reset(initialData as DefaultValues<TFormValues>);
    }
  }, [initialData, isEditing, form]);

  const startEditing = useCallback(() => {
    setIsEditing(true);
  }, []);

  const cancelEditing = useCallback(() => {
    form.reset(initialData as DefaultValues<TFormValues>);
    setIsEditing(false);
  }, [form, initialData]);

  const saveChanges = useCallback(async () => {
    const isValid = await form.trigger();
    if (!isValid) return;

    setIsSaving(true);
    try {
      await onSave(form.getValues());
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  }, [form, onSave]);

  return {
    isEditing,
    isDirty,
    isSaving,
    form,
    startEditing,
    cancelEditing,
    saveChanges,
  };
}
