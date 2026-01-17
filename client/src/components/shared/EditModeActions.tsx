import { Loader2, Pencil, X, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EditModeActionsProps {
  isEditing: boolean;
  isSaving: boolean;
  isDirty: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  canEdit?: boolean;
}

/**
 * Action buttons for inline edit mode.
 * Shows "Edit" button in view mode, "Cancel" + "Save" buttons in edit mode.
 */
export function EditModeActions({
  isEditing,
  isSaving,
  isDirty,
  onEdit,
  onSave,
  onCancel,
  canEdit = true,
}: EditModeActionsProps) {
  if (!canEdit) return null;

  if (isEditing) {
    return (
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={onCancel} disabled={isSaving}>
          <X className="mr-2 h-4 w-4" />
          Cancel
        </Button>
        <Button onClick={onSave} disabled={isSaving || !isDirty}>
          {isSaving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Check className="mr-2 h-4 w-4" />
          )}
          Save
        </Button>
      </div>
    );
  }

  return (
    <Button variant="outline" onClick={onEdit}>
      <Pencil className="mr-2 h-4 w-4" />
      Edit
    </Button>
  );
}
