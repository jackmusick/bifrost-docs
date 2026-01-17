import * as React from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";

// =============================================================================
// BulkActionToolbar Component
// =============================================================================

export interface BulkActionToolbarProps {
  /** Number of selected items */
  selectedCount: number;
  /** Callback to clear selection */
  onClearSelection: () => void;
  /** Action buttons to display */
  actions?: React.ReactNode;
  /** Optional className */
  className?: string;
}

export function BulkActionToolbar({
  selectedCount,
  onClearSelection,
  actions,
  className,
}: BulkActionToolbarProps) {
  if (selectedCount === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 px-4 py-3 bg-accent/50 border border-accent rounded-lg",
        className
      )}
    >
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium">
          {selectedCount} {selectedCount === 1 ? "item" : "items"} selected
        </span>
        {actions}
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={onClearSelection}
        className="h-8"
      >
        <X className="mr-2 h-4 w-4" />
        Clear Selection
      </Button>
    </div>
  );
}

// =============================================================================
// ConfirmBulkActionDialog Component
// =============================================================================

export interface ConfirmBulkActionDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Dialog title */
  title: string;
  /** Dialog description */
  description: string;
  /** Confirm button label (default: "Confirm") */
  confirmLabel?: string;
  /** Callback when confirmed */
  onConfirm: () => void | Promise<void>;
  /** Loading state */
  loading?: boolean;
  /** Button variant (default: "default") */
  variant?: "default" | "destructive";
}

export function ConfirmBulkActionDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  onConfirm,
  loading = false,
  variant = "default",
}: ConfirmBulkActionDialogProps) {
  const handleConfirm = async () => {
    await onConfirm();
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={loading}
            className={
              variant === "destructive"
                ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                : undefined
            }
          >
            {loading ? "Processing..." : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
