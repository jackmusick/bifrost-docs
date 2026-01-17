import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { useBatchUpdatePaths } from "@/hooks/useDocuments";
import { toast } from "sonner";

interface SectionRenameDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orgId: string;
  currentPath: string;
  currentName: string;
  documentCount: number;
}

export function SectionRenameDialog({
  open,
  onOpenChange,
  orgId,
  currentPath,
  currentName,
  documentCount,
}: SectionRenameDialogProps) {
  const [newName, setNewName] = useState(currentName);
  const [conflicts, setConflicts] = useState<string[]>([]);
  const [showMergeConfirm, setShowMergeConfirm] = useState(false);
  const batchUpdatePaths = useBatchUpdatePaths(orgId);

  // Handle open state changes - reset state when dialog opens
  const handleOpenChange = (isOpen: boolean) => {
    if (isOpen) {
      // Reset state when opening
      setNewName(currentName);
      setConflicts([]);
      setShowMergeConfirm(false);
    }
    onOpenChange(isOpen);
  };

  const parentPath = currentPath.split("/").slice(0, -1).join("/") || "/";
  const trimmedName = newName.trim();
  const newPath = parentPath === "/" ? `/${trimmedName}` : `${parentPath}/${trimmedName}`;
  const isNameValid = trimmedName.length > 0 && trimmedName !== currentName;

  const handleRename = async (mergeIfExists = false) => {
    if (!isNameValid) return;

    try {
      const result = await batchUpdatePaths.mutateAsync({
        old_path_prefix: currentPath,
        new_path_prefix: newPath,
        merge_if_exists: mergeIfExists,
      });

      if (result.conflicts.length > 0 && !mergeIfExists) {
        setConflicts(result.conflicts);
        setShowMergeConfirm(true);
        return;
      }

      const count = result.updated_count;
      toast.success(
        count > 0
          ? `Renamed section and updated ${count} document${count !== 1 ? "s" : ""}`
          : "Section renamed"
      );
      onOpenChange(false);
      setShowMergeConfirm(false);
      setConflicts([]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to rename section";
      toast.error(message);
    }
  };

  const handleClose = () => {
    handleOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {showMergeConfirm ? "Merge Sections?" : "Rename Section"}
          </DialogTitle>
          <DialogDescription>
            {showMergeConfirm
              ? "The target section already exists. Would you like to merge?"
              : `This will update ${documentCount} document${documentCount !== 1 ? "s" : ""}.`}
          </DialogDescription>
        </DialogHeader>

        {showMergeConfirm ? (
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Conflicting Documents</AlertTitle>
              <AlertDescription>
                The following documents have the same name in both sections:
                <ul className="mt-2 list-disc list-inside">
                  {conflicts.map((name) => (
                    <li key={name} className="text-sm">{name}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
            <p className="text-sm text-muted-foreground">
              Merging will keep the existing documents and move the non-conflicting ones.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="section-name">Section Name</Label>
              <Input
                id="section-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Section name"
                autoFocus
              />
              {newName && !isNameValid && (
                <p className="text-xs text-muted-foreground">
                  {trimmedName === currentName
                    ? "Name is the same as current"
                    : "Enter a valid section name"}
                </p>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              Current path: <code className="text-xs bg-muted px-1 rounded">{currentPath}</code>
              <br />
              New path: <code className="text-xs bg-muted px-1 rounded">{newPath}</code>
            </p>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          {showMergeConfirm ? (
            <Button
              onClick={() => handleRename(true)}
              disabled={batchUpdatePaths.isPending}
            >
              {batchUpdatePaths.isPending ? "Merging..." : "Merge Sections"}
            </Button>
          ) : (
            <Button
              onClick={() => handleRename(false)}
              disabled={batchUpdatePaths.isPending || !isNameValid}
            >
              {batchUpdatePaths.isPending ? "Renaming..." : "Rename"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
