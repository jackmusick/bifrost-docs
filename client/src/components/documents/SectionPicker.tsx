import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import {
  Folder,
  FolderOpen,
  FolderPlus,
  ChevronRight,
  ChevronDown,
  Check,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  useFolders,
  buildFolderTree,
  type FolderNode,
} from "@/hooks/useDocuments";

interface SectionPickerProps {
  orgId: string;
  value: string;
  onChange: (path: string) => void;
  className?: string;
  disabled?: boolean;
}

export function SectionPicker({
  orgId,
  value,
  onChange,
  className,
  disabled,
}: SectionPickerProps) {
  const [open, setOpen] = useState(false);
  // Track manually toggled folders (user expand/collapse actions)
  const [manuallyExpanded, setManuallyExpanded] = useState<Set<string>>(
    new Set()
  );
  const [newSectionParent, setNewSectionParent] = useState<string | null>(null);
  const [newSectionName, setNewSectionName] = useState("");

  const { data: foldersData, isLoading, isError } = useFolders(orgId);

  const folderTree = useMemo(() => {
    const folders = foldersData?.folders ?? [];
    return buildFolderTree(folders);
  }, [foldersData?.folders]);

  // Derive expanded folders: manually expanded + auto-expanded for current value path
  const expandedFolders = useMemo(() => {
    const expanded = new Set(manuallyExpanded);
    // Auto-expand parent folders of current value
    if (value && value !== "/") {
      const parts = value.split("/").filter(Boolean);
      let currentPath = "";
      for (const part of parts.slice(0, -1)) {
        currentPath = currentPath ? `${currentPath}/${part}` : `/${part}`;
        expanded.add(currentPath);
      }
    }
    return expanded;
  }, [manuallyExpanded, value]);

  const toggleExpanded = useCallback((path: string) => {
    setManuallyExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const handleSelect = useCallback((path: string) => {
    onChange(path);
    setOpen(false);
  }, [onChange]);

  const handleCreateSection = useCallback((parentPath: string) => {
    if (!newSectionName.trim()) return;

    const sanitized = newSectionName.trim().toLowerCase().replace(/\s+/g, "-");
    const newPath =
      parentPath === "/" ? `/${sanitized}` : `${parentPath}/${sanitized}`;

    onChange(newPath);
    setNewSectionParent(null);
    setNewSectionName("");
    setOpen(false);
  }, [newSectionName, onChange]);

  const startCreatingSection = useCallback((parentPath: string) => {
    setNewSectionParent(parentPath);
    setNewSectionName("");
  }, []);

  const cancelCreatingSection = useCallback(() => {
    setNewSectionParent(null);
    setNewSectionName("");
  }, []);

  // Display the current path nicely
  const displayPath = () => {
    if (!value || value === "/") return "Root";
    const parts = value.split("/").filter(Boolean);
    return parts.join(" / ");
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled || isLoading}
          className={cn(
            "w-full justify-between font-normal",
            !value && "text-muted-foreground",
            className
          )}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Folder className="h-4 w-4 shrink-0" />
            <span className="truncate">{displayPath()}</span>
          </div>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[300px] p-0" align="start">
        {isError ? (
          <div className="p-4 text-sm text-destructive text-center">
            Failed to load sections
          </div>
        ) : (
        <ScrollArea className="h-[300px]">
          <div className="p-2 space-y-1">
            {/* Root option */}
            <FolderPickerItem
              name="Root"
              path="/"
              isSelected={value === "/"}
              isExpanded={false}
              hasChildren={false}
              depth={0}
              onSelect={() => handleSelect("/")}
              onToggleExpand={() => {}}
              onCreateSubsection={() => startCreatingSection("/")}
              showCreateOption
            />

            {/* New section at root level */}
            {newSectionParent === "/" && (
              <NewSectionInput
                value={newSectionName}
                onChange={setNewSectionName}
                onSubmit={() => handleCreateSection("/")}
                onCancel={cancelCreatingSection}
                depth={0}
              />
            )}

            {/* Create new section button at root */}
            {newSectionParent !== "/" && (
              <button
                onClick={() => startCreatingSection("/")}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                <FolderPlus className="h-4 w-4" />
                <span>New section</span>
              </button>
            )}

            {/* Folder tree */}
            {folderTree.map((folder) => (
              <FolderPickerItemRecursive
                key={folder.path}
                folder={folder}
                selectedPath={value}
                expandedFolders={expandedFolders}
                onSelect={handleSelect}
                onToggleExpand={toggleExpanded}
                onStartCreating={startCreatingSection}
                newSectionParent={newSectionParent}
                newSectionName={newSectionName}
                onNewSectionNameChange={setNewSectionName}
                onCreateSection={handleCreateSection}
                onCancelCreating={cancelCreatingSection}
                depth={0}
              />
            ))}
          </div>
        </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  );
}

interface FolderPickerItemProps {
  name: string;
  path: string;
  isSelected: boolean;
  isExpanded: boolean;
  hasChildren: boolean;
  depth: number;
  onSelect: () => void;
  onToggleExpand: () => void;
  onCreateSubsection?: () => void;
  showCreateOption?: boolean;
}

function FolderPickerItem({
  name,
  path,
  isSelected,
  isExpanded,
  hasChildren,
  depth,
  onSelect,
  onToggleExpand,
  onCreateSubsection,
  showCreateOption,
}: FolderPickerItemProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      role="option"
      aria-selected={isSelected}
      tabIndex={0}
      className={cn(
        "group flex items-center justify-between rounded-md text-sm transition-colors cursor-pointer",
        isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted"
      )}
      style={{ paddingLeft: `${depth * 12 + 8}px` }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <div className="flex-1 flex items-center gap-1 py-1.5 min-w-0">
        {hasChildren ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand();
            }}
            className="p-0.5 hover:bg-muted-foreground/20 rounded"
            aria-label={isExpanded ? "Collapse folder" : "Expand folder"}
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 shrink-0" />
            )}
          </button>
        ) : (
          <span className="w-4 shrink-0" />
        )}
        {path === "/" ? (
          <Folder className="h-4 w-4 shrink-0" />
        ) : isExpanded ? (
          <FolderOpen className="h-4 w-4 shrink-0" />
        ) : (
          <Folder className="h-4 w-4 shrink-0" />
        )}
        <span className="truncate">{name}</span>
        {isSelected && <Check className="h-4 w-4 shrink-0 ml-auto" />}
      </div>
      {showCreateOption && hovered && !isSelected && onCreateSubsection && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onCreateSubsection();
          }}
          className="p-1 mr-1 rounded hover:bg-muted-foreground/20 text-muted-foreground hover:text-foreground"
          title={path === "/" ? "New section" : "New subsection"}
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

interface FolderPickerItemRecursiveProps {
  folder: FolderNode;
  selectedPath: string;
  expandedFolders: Set<string>;
  onSelect: (path: string) => void;
  onToggleExpand: (path: string) => void;
  onStartCreating: (parentPath: string) => void;
  newSectionParent: string | null;
  newSectionName: string;
  onNewSectionNameChange: (name: string) => void;
  onCreateSection: (parentPath: string) => void;
  onCancelCreating: () => void;
  depth: number;
}

function FolderPickerItemRecursive({
  folder,
  selectedPath,
  expandedFolders,
  onSelect,
  onToggleExpand,
  onStartCreating,
  newSectionParent,
  newSectionName,
  onNewSectionNameChange,
  onCreateSection,
  onCancelCreating,
  depth,
}: FolderPickerItemRecursiveProps) {
  const hasChildren = folder.children.length > 0;
  const isExpanded = expandedFolders.has(folder.path);
  const isSelected = selectedPath === folder.path;

  return (
    <div>
      <FolderPickerItem
        name={folder.name}
        path={folder.path}
        isSelected={isSelected}
        isExpanded={isExpanded}
        hasChildren={hasChildren}
        depth={depth}
        onSelect={() => onSelect(folder.path)}
        onToggleExpand={() => onToggleExpand(folder.path)}
        onCreateSubsection={() => onStartCreating(folder.path)}
        showCreateOption
      />

      {/* New subsection input for this folder */}
      {newSectionParent === folder.path && (
        <NewSectionInput
          value={newSectionName}
          onChange={onNewSectionNameChange}
          onSubmit={() => onCreateSection(folder.path)}
          onCancel={onCancelCreating}
          depth={depth + 1}
        />
      )}

      {/* Children */}
      {isExpanded && hasChildren && (
        <div>
          {folder.children.map((child) => (
            <FolderPickerItemRecursive
              key={child.path}
              folder={child}
              selectedPath={selectedPath}
              expandedFolders={expandedFolders}
              onSelect={onSelect}
              onToggleExpand={onToggleExpand}
              onStartCreating={onStartCreating}
              newSectionParent={newSectionParent}
              newSectionName={newSectionName}
              onNewSectionNameChange={onNewSectionNameChange}
              onCreateSection={onCreateSection}
              onCancelCreating={onCancelCreating}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface NewSectionInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  depth: number;
}

function NewSectionInput({
  value,
  onChange,
  onSubmit,
  onCancel,
  depth,
}: NewSectionInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      onSubmit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    }
  };

  return (
    <div
      className="flex items-center gap-1 py-1"
      style={{ paddingLeft: `${depth * 12 + 8 + 16}px` }}
    >
      <FolderPlus className="h-4 w-4 shrink-0 text-muted-foreground" />
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          if (!value.trim()) {
            onCancel();
          }
        }}
        placeholder="Section name"
        className="h-7 text-sm flex-1"
      />
      <Button
        size="sm"
        variant="ghost"
        className="h-7 w-7 p-0"
        onClick={onSubmit}
        disabled={!value.trim()}
      >
        <Check className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
