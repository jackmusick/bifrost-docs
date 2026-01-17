import { useState, useMemo, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Search, Plus, FolderPlus, Check, X } from "lucide-react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  useDroppable,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { SectionRenameDialog } from "./SectionRenameDialog";
import { useDocumentSections, type SectionItem } from "@/hooks/useDocumentSections";
import { usePermissions } from "@/hooks/usePermissions";
import { useMoveDocument } from "@/hooks/useDocuments";

// =============================================================================
// Types
// =============================================================================

interface DocumentSidebarProps {
  selectedDocumentId?: string;
  onCreateDocument?: (path: string) => void;
}

// =============================================================================
// Filtering Logic
// =============================================================================

/**
 * Recursively filters sections based on search query.
 * A section is included if:
 * - Its label matches the query
 * - Any of its children match the query
 * - Any document within it matches the query
 */
function filterSections(
  sections: SectionItem[],
  query: string
): SectionItem[] {
  if (!query.trim()) {
    return sections;
  }

  const lowerQuery = query.toLowerCase();

  const filterItem = (item: SectionItem): SectionItem | null => {
    const labelMatches = item.label.toLowerCase().includes(lowerQuery);

    // For documents, only check label match
    if (item.type === "document") {
      return labelMatches ? item : null;
    }

    // For sections/subsections/groups, also check children
    const filteredChildren = item.children
      ?.map(filterItem)
      .filter((child): child is SectionItem => child !== null);

    // Include if label matches or has matching children
    if (labelMatches || (filteredChildren && filteredChildren.length > 0)) {
      return {
        ...item,
        children: filteredChildren,
      };
    }

    return null;
  };

  return sections
    .map(filterItem)
    .filter((item): item is SectionItem => item !== null);
}

// =============================================================================
// Loading Skeleton
// =============================================================================

function SidebarSkeleton() {
  return (
    <div className="px-3 py-2 space-y-3">
      {/* Search skeleton */}
      <Skeleton className="h-8 w-full" />

      {/* Section skeletons */}
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-1">
          <Skeleton className="h-5 w-3/4" />
          <div className="pl-3 space-y-1">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Empty State
// =============================================================================

function EmptyState({ hasFilter }: { hasFilter: boolean }) {
  return (
    <div className="py-4 px-2 text-center">
      <p className="text-sm text-muted-foreground">
        {hasFilter
          ? "No documents match your search"
          : "No documents yet"}
      </p>
    </div>
  );
}

// =============================================================================
// Document Item (Draggable)
// =============================================================================

interface DocumentItemProps {
  item: SectionItem;
  isSelected: boolean;
  onClick: () => void;
  canDrag: boolean;
}

function DocumentItem({ item, isSelected, onClick, canDrag }: DocumentItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    isDragging,
  } = useDraggable({
    id: item.id,
    data: { type: "document", item },
    disabled: !canDrag,
  });

  const style = transform
    ? { transform: CSS.Translate.toString(transform) }
    : undefined;

  return (
    <button
      ref={setNodeRef}
      style={style}
      onClick={onClick}
      {...(canDrag ? { ...attributes, ...listeners } : {})}
      className={cn(
        "w-full text-left text-sm py-0.5 px-1 rounded truncate transition-colors",
        canDrag && "cursor-grab active:cursor-grabbing",
        isDragging && "opacity-50",
        isSelected
          ? "bg-primary/15 text-primary font-medium"
          : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
      )}
    >
      {item.label}
    </button>
  );
}

// =============================================================================
// Drag Overlay Document
// =============================================================================

function DragOverlayDocument({ item }: { item: SectionItem }) {
  return (
    <div className="px-2 py-1 rounded text-sm bg-background border shadow-lg">
      {item.label}
    </div>
  );
}

// =============================================================================
// Section Item (Droppable)
// =============================================================================

interface SectionItemComponentProps {
  item: SectionItem;
  orgId: string;
  selectedDocumentId?: string;
  onDocumentClick: (documentId: string) => void;
  onCreateDocument?: (path: string) => void;
  canEdit: boolean;
  defaultExpanded?: boolean;
}

function SectionItemComponent({
  item,
  orgId,
  selectedDocumentId,
  onDocumentClick,
  onCreateDocument,
  canEdit,
  defaultExpanded = true,
}: SectionItemComponentProps) {
  const [isOpen, setIsOpen] = useState(defaultExpanded);
  const [isHovered, setIsHovered] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);

  // Make sections droppable
  const { isOver, setNodeRef } = useDroppable({
    id: item.path,
    data: { type: "section", path: item.path },
  });

  // Determine styling based on type
  // Sections: bold, Subsections: normal weight but foreground color
  const isSection = item.type === "section";
  const isSubsection = item.type === "subsection" || item.type === "flattened-group";

  // Separate documents from subsections/groups
  const documents = item.children?.filter((child) => child.type === "document") ?? [];
  const nestedSections = item.children?.filter((child) => child.type !== "document") ?? [];

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div
        ref={setNodeRef}
        className={cn(
          "relative transition-colors",
          isOver && "bg-primary/10 ring-1 ring-primary/30 rounded"
        )}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <ContextMenu>
          <ContextMenuTrigger asChild>
            <div className="flex items-center group">
              <CollapsibleTrigger asChild>
                <button
                  className={cn(
                    "flex-1 py-0.5 px-1 text-sm transition-colors text-left truncate rounded",
                    "hover:text-foreground hover:bg-muted/50",
                    isSection && "font-semibold text-foreground",
                    isSubsection && "text-foreground",
                  )}
                >
                  {item.label}
                </button>
              </CollapsibleTrigger>

              {/* Plus button on hover */}
              {canEdit && onCreateDocument && (
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-5 w-5 shrink-0 transition-opacity ml-1",
                    isHovered ? "opacity-100" : "opacity-0"
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    onCreateDocument(item.path);
                  }}
                  title={`Create document in ${item.label}`}
                >
                  <Plus className="h-3 w-3" />
                </Button>
              )}
            </div>
          </ContextMenuTrigger>
          <ContextMenuContent>
            {canEdit && (
              <ContextMenuItem onClick={() => setRenameOpen(true)}>
                Rename section
              </ContextMenuItem>
            )}
            {canEdit && onCreateDocument && (
              <ContextMenuItem onClick={() => onCreateDocument(item.path)}>
                New document here
              </ContextMenuItem>
            )}
          </ContextMenuContent>
        </ContextMenu>
      </div>

      {/* Section Rename Dialog */}
      <SectionRenameDialog
        open={renameOpen}
        onOpenChange={setRenameOpen}
        orgId={orgId}
        currentPath={item.path}
        currentName={item.label}
        documentCount={item.documentCount ?? 0}
      />

      <CollapsibleContent>
        <div className="pl-3">
          {/* Render documents first */}
          {documents.map((doc) => (
            <DocumentItem
              key={doc.id}
              item={doc}
              isSelected={doc.id === selectedDocumentId}
              onClick={() => onDocumentClick(doc.id)}
              canDrag={canEdit}
            />
          ))}

          {/* Render nested sections */}
          {nestedSections.map((section) => (
            <SectionItemComponent
              key={section.id}
              item={section}
              orgId={orgId}
              selectedDocumentId={selectedDocumentId}
              onDocumentClick={onDocumentClick}
              onCreateDocument={onCreateDocument}
              canEdit={canEdit}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

// =============================================================================
// Helper: Find document by ID in section tree
// =============================================================================

function findDocumentInSections(
  sections: SectionItem[],
  documentId: string
): SectionItem | null {
  for (const section of sections) {
    if (section.type === "document" && section.id === documentId) {
      return section;
    }
    if (section.children) {
      const found = findDocumentInSections(section.children, documentId);
      if (found) return found;
    }
  }
  return null;
}

// =============================================================================
// Main Component
// =============================================================================

export function DocumentSidebar({
  selectedDocumentId,
  onCreateDocument,
}: DocumentSidebarProps) {
  const { orgId } = useParams<{ orgId: string }>();
  const navigate = useNavigate();
  const { canEdit } = usePermissions();

  const [filterQuery, setFilterQuery] = useState("");
  const [activeItem, setActiveItem] = useState<SectionItem | null>(null);
  const [isAddingSection, setIsAddingSection] = useState(false);
  const [newSectionName, setNewSectionName] = useState("");
  const newSectionInputRef = useRef<HTMLInputElement>(null);

  const { sections, isLoading } = useDocumentSections(orgId ?? "");
  const moveDocument = useMoveDocument(orgId ?? "");

  // Focus input when adding section
  useEffect(() => {
    if (isAddingSection && newSectionInputRef.current) {
      newSectionInputRef.current.focus();
    }
  }, [isAddingSection]);

  // Handle creating a new section (navigates to new document with that path)
  const handleCreateSection = () => {
    if (!newSectionName.trim()) {
      setIsAddingSection(false);
      return;
    }
    const sectionPath = `/${newSectionName.trim()}`;
    onCreateDocument?.(sectionPath);
    setNewSectionName("");
    setIsAddingSection(false);
  };

  const handleCancelAddSection = () => {
    setNewSectionName("");
    setIsAddingSection(false);
  };

  // Configure drag sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor)
  );

  // Filter sections based on search query
  const filteredSections = useMemo(
    () => filterSections(sections, filterQuery),
    [sections, filterQuery]
  );

  // Handle document click - navigate to document
  const handleDocumentClick = (documentId: string) => {
    if (orgId) {
      navigate(`/org/${orgId}/documents/${documentId}`);
    }
  };

  // Drag handlers
  const handleDragStart = (event: DragStartEvent) => {
    const documentId = event.active.id as string;
    const item = findDocumentInSections(sections, documentId);
    setActiveItem(item);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveItem(null);

    if (!over || active.id === over.id) return;

    // Get target path from droppable
    const targetPath = over.id as string;

    // Only allow dropping on sections (paths start with /)
    if (!targetPath.startsWith("/")) return;

    // Find the document being dragged
    const documentId = active.id as string;
    const draggedDoc = findDocumentInSections(sections, documentId);

    // Don't move if already in the same folder
    if (draggedDoc && draggedDoc.path === targetPath) return;

    try {
      await moveDocument.mutateAsync({
        documentId,
        newPath: targetPath,
      });
      toast.success("Document moved successfully");
    } catch {
      toast.error("Failed to move document");
    }
  };

  const handleDragCancel = () => {
    setActiveItem(null);
  };

  // Loading state
  if (isLoading) {
    return <SidebarSkeleton />;
  }

  const hasDocuments = sections.length > 0;
  const hasFilteredResults = filteredSections.length > 0;

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div className="flex flex-col h-full">
        {/* Search filter - embedded style */}
        <div className="px-2 py-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
            <Input
              placeholder="Filter documents..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="pl-7 h-7 text-xs bg-transparent border-0 shadow-none focus-visible:ring-0 placeholder:text-muted-foreground/50"
            />
          </div>
        </div>

        {/* Section tree - use overflow-y-auto like main Sidebar */}
        <div className="flex-1 overflow-y-auto px-2 py-1 space-y-2">
          {!hasDocuments && <EmptyState hasFilter={false} />}
          {hasDocuments && !hasFilteredResults && <EmptyState hasFilter={true} />}
          {hasFilteredResults &&
            filteredSections.map((section) => (
              <SectionItemComponent
                key={section.id}
                item={section}
                orgId={orgId ?? ""}
                selectedDocumentId={selectedDocumentId}
                onDocumentClick={handleDocumentClick}
                onCreateDocument={onCreateDocument}
                canEdit={canEdit}
                defaultExpanded={filterQuery.length > 0 ? true : undefined}
              />
            ))}

          {/* Add Section inline form or button */}
          {canEdit && (
            <div className="pt-2">
              {isAddingSection ? (
                <div className="flex items-center gap-1 px-1">
                  <Input
                    ref={newSectionInputRef}
                    value={newSectionName}
                    onChange={(e) => setNewSectionName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleCreateSection();
                      if (e.key === "Escape") handleCancelAddSection();
                    }}
                    placeholder="Section name..."
                    className="h-6 text-sm flex-1"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 shrink-0"
                    onClick={handleCreateSection}
                  >
                    <Check className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 shrink-0"
                    onClick={handleCancelAddSection}
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ) : (
                <button
                  onClick={() => setIsAddingSection(true)}
                  className="w-full flex items-center gap-2 px-1 py-1 text-sm text-muted-foreground hover:text-foreground transition-colors rounded"
                >
                  <FolderPlus className="h-3.5 w-3.5" />
                  <span>Add Section</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Drag overlay - shows the item being dragged */}
      <DragOverlay>
        {activeItem ? <DragOverlayDocument item={activeItem} /> : null}
      </DragOverlay>
    </DndContext>
  );
}
