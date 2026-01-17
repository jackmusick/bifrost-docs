import { useState, useRef, useEffect } from "react";
import { Layers, Plus, Pencil, Trash2, GripVertical } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AssetTypeForm } from "@/components/assets/AssetTypeForm";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import {
  useCustomAssetTypes,
  useCreateCustomAssetType,
  useUpdateCustomAssetType,
  useDeleteCustomAssetType,
  useDeactivateCustomAssetType,
  useActivateCustomAssetType,
  useReorderCustomAssetTypes,
  type CustomAssetType,
  type CustomAssetTypeCreate,
  type CustomAssetTypeUpdate,
} from "@/hooks/useCustomAssets";
import { toast } from "sonner";
import {
  draggable,
  dropTargetForElements,
} from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { disableNativeDragPreview } from "@atlaskit/pragmatic-drag-and-drop/element/disable-native-drag-preview";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { reorder } from "@atlaskit/pragmatic-drag-and-drop/reorder";
import { cn } from "@/lib/utils";

// =============================================================================
// Draggable Item Component
// =============================================================================

interface DraggableItemProps {
  type: CustomAssetType;
  index: number;
  onEdit: (type: CustomAssetType) => void;
  onToggleActive: (type: CustomAssetType, checked: boolean) => void;
  onDeleteClick: (type: CustomAssetType) => void;
  onDrop: (startIndex: number, finishIndex: number) => void;
  isPending: boolean;
}

function DraggableItem({
  type,
  index,
  onEdit,
  onToggleActive,
  onDeleteClick,
  onDrop,
  isPending,
}: DraggableItemProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const [isDraggedOver, setIsDraggedOver] = useState(false);
  const [dropPosition, setDropPosition] = useState<"none" | "before" | "after">("none");

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    return combine(
      draggable({
        element: el,
        getInitialData: () => ({ type: "custom-asset-type", index, id: type.id }),
        onGenerateDragPreview: ({ nativeSetDragImage }) => {
          disableNativeDragPreview({ nativeSetDragImage });
        },
        onDragStart: () => setDragging(true),
        onDrop: () => setDragging(false),
      }),
      dropTargetForElements({
        element: el,
        getData: ({ input, element }) => {
          const rect = element.getBoundingClientRect();
          const midpoint = rect.top + rect.height / 2;
          const position = input.clientY < midpoint ? "before" : "after";
          return { index, position };
        },
        canDrop: ({ source }) => source.data["type"] === "custom-asset-type",
        onDragEnter: () => setIsDraggedOver(true),
        onDrag: ({ self }) => {
          const position = self.data["position"] as "before" | "after";
          setDropPosition(position);
        },
        onDragLeave: () => {
          setIsDraggedOver(false);
          setDropPosition("none");
        },
        onDrop: ({ source, location }) => {
          setIsDraggedOver(false);
          setDropPosition("none");

          const startIndex = source.data["index"] as number;
          const target = location.current.dropTargets.find(
            (t) => t.data["index"] !== undefined
          );

          if (target?.data["index"] !== undefined) {
            const targetIndex = target.data["index"] as number;
            const position = target.data["position"] as "before" | "after";

            // Calculate finish index
            let finishIndex = position === "before" ? targetIndex : targetIndex + 1;
            if (startIndex < finishIndex) {
              finishIndex -= 1;
            }

            if (startIndex !== finishIndex) {
              onDrop(startIndex, finishIndex);
            }
          }
        },
      })
    );
  }, [index, type.id, onDrop]);

  return (
    <div
      ref={ref}
      className={cn(
        "relative flex items-center gap-4 px-4 py-3 border-b last:border-b-0 transition-colors",
        !type.is_active && "opacity-50",
        dragging && "opacity-50 bg-muted",
        isDraggedOver && "bg-accent"
      )}
    >
      {/* Drop indicator line */}
      {dropPosition === "before" && (
        <div className="absolute -top-0.5 left-0 right-0 h-0.5 bg-primary z-10 pointer-events-none" />
      )}
      {dropPosition === "after" && (
        <div className="absolute -bottom-0.5 left-0 right-0 h-0.5 bg-primary z-10 pointer-events-none" />
      )}

      {/* Drag handle */}
      <div className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground shrink-0">
        <GripVertical className="h-4 w-4" />
      </div>

      {/* Name */}
      <div className="flex items-center gap-2 min-w-[180px] flex-1">
        <Layers className="h-4 w-4 text-muted-foreground shrink-0" />
        <span className="font-medium truncate">{type.name}</span>
        {!type.is_active && (
          <Badge variant="secondary" className="text-xs shrink-0">
            Inactive
          </Badge>
        )}
      </div>

      {/* Assets count */}
      <div className="text-sm text-muted-foreground whitespace-nowrap shrink-0">
        {type.asset_count} {type.asset_count === 1 ? "asset" : "assets"}
      </div>

      {/* Active toggle */}
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="shrink-0">
            <Switch
              checked={type.is_active}
              onCheckedChange={(checked) => onToggleActive(type, checked)}
              disabled={isPending}
            />
          </div>
        </TooltipTrigger>
        <TooltipContent>
          {type.is_active ? "Deactivate (hide from use)" : "Activate"}
        </TooltipContent>
      </Tooltip>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => onEdit(type)}
        >
          <Pencil className="h-4 w-4" />
        </Button>
        <Tooltip>
          <TooltipTrigger asChild>
            <span>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                disabled={type.asset_count > 0}
                onClick={() => onDeleteClick(type)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </span>
          </TooltipTrigger>
          <TooltipContent>
            {type.asset_count > 0
              ? `Cannot delete - ${type.asset_count} assets exist. Deactivate instead.`
              : "Delete permanently"}
          </TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}

export function CustomAssetTypesSettings() {
  const [formOpen, setFormOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editingType, setEditingType] = useState<CustomAssetType | null>(null);

  const { data: types, isLoading } = useCustomAssetTypes({ includeInactive: true });
  const createType = useCreateCustomAssetType();
  const updateType = useUpdateCustomAssetType();
  const deleteType = useDeleteCustomAssetType();
  const deactivateType = useDeactivateCustomAssetType();
  const activateType = useActivateCustomAssetType();
  const reorderTypes = useReorderCustomAssetTypes();

  const openCreate = () => {
    setEditingType(null);
    setFormOpen(true);
  };

  const openEdit = (type: CustomAssetType) => {
    setEditingType(type);
    setFormOpen(true);
  };

  const handleSubmit = async (data: CustomAssetTypeCreate | CustomAssetTypeUpdate) => {
    try {
      if (editingType) {
        await updateType.mutateAsync({ id: editingType.id, data: data as CustomAssetTypeUpdate });
        toast.success("Asset type updated successfully");
      } else {
        await createType.mutateAsync(data as CustomAssetTypeCreate);
        toast.success("Asset type created successfully");
      }
      setFormOpen(false);
      setEditingType(null);
    } catch {
      toast.error(
        editingType
          ? "Failed to update asset type"
          : "Failed to create asset type"
      );
    }
  };

  const handleDelete = async () => {
    if (!editingType) return;
    try {
      await deleteType.mutateAsync(editingType.id);
      toast.success("Asset type deleted successfully");
      setDeleteOpen(false);
      setEditingType(null);
    } catch {
      toast.error("Failed to delete asset type. It may have assets - try deactivating instead.");
    }
  };

  const handleToggleActive = async (type: CustomAssetType, checked: boolean) => {
    try {
      if (checked) {
        await activateType.mutateAsync(type.id);
        toast.success(`"${type.name}" activated`);
      } else {
        await deactivateType.mutateAsync(type.id);
        toast.success(`"${type.name}" deactivated`);
      }
    } catch {
      toast.error(checked ? "Failed to activate type" : "Failed to deactivate type");
    }
  };

  const handleDrop = async (startIndex: number, finishIndex: number) => {
    if (!types) return;
    const newOrderedIds = reorder({
      list: types.map((t) => t.id),
      startIndex,
      finishIndex,
    });
    await reorderTypes.mutateAsync(newOrderedIds);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Custom Asset Types</h2>
          <p className="text-sm text-muted-foreground">
            Define custom asset types with flexible field schemas for all organizations
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Add Asset Type
        </Button>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : !types?.length ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Layers className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium mb-1">No custom asset types</h3>
            <p className="text-sm text-muted-foreground text-center mb-4">
              Create custom asset types to organize specialized assets with custom fields
            </p>
            <Button onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add Asset Type
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">All Custom Asset Types</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div>
              {types.map((type, index) => (
                <DraggableItem
                  key={type.id}
                  type={type}
                  index={index}
                  onEdit={openEdit}
                  onToggleActive={handleToggleActive}
                  onDeleteClick={(type) => {
                    setEditingType(type);
                    setDeleteOpen(true);
                  }}
                  onDrop={handleDrop}
                  isPending={deactivateType.isPending || activateType.isPending}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Dialog */}
      <AssetTypeForm
        open={formOpen}
        onOpenChange={(open) => {
          setFormOpen(open);
          if (!open) setEditingType(null);
        }}
        onSubmit={handleSubmit}
        isSubmitting={createType.isPending || updateType.isPending}
        mode={editingType ? "edit" : "create"}
        initialData={editingType ?? undefined}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Custom Asset Type"
        description={`Are you sure you want to delete "${editingType?.name}"? This will also delete all assets of this type. This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteType.isPending}
      />
    </div>
  );
}
