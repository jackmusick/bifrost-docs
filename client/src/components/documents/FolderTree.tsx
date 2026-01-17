import { useState } from "react";
import {
  Folder,
  FolderOpen,
  ChevronRight,
  ChevronDown,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { type FolderNode } from "@/hooks/useDocuments";

interface FolderTreeProps {
  folders: FolderNode[];
  selectedPath: string | null;
  onSelectPath: (path: string | null) => void;
  totalCount?: number;
  rootCount?: number;
}

export function FolderTree({
  folders,
  selectedPath,
  onSelectPath,
  totalCount,
  rootCount,
}: FolderTreeProps) {
  return (
    <div className="space-y-1">
      <button
        onClick={() => onSelectPath(null)}
        className={cn(
          "w-full flex items-center justify-between gap-2 px-2 py-1.5 rounded-md text-sm transition-colors",
          selectedPath === null
            ? "bg-primary/10 text-primary"
            : "hover:bg-muted"
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="h-4 w-4 shrink-0" />
          <span className="truncate">All Documents</span>
        </div>
        {totalCount !== undefined && totalCount > 0 && (
          <Badge
            variant="secondary"
            className="shrink-0 h-5 min-w-5 justify-center px-1.5 text-xs font-normal"
          >
            {totalCount}
          </Badge>
        )}
      </button>
      <button
        onClick={() => onSelectPath("/")}
        className={cn(
          "w-full flex items-center justify-between gap-2 px-2 py-1.5 rounded-md text-sm transition-colors",
          selectedPath === "/"
            ? "bg-primary/10 text-primary"
            : "hover:bg-muted"
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Folder className="h-4 w-4 shrink-0" />
          <span className="truncate">Root</span>
        </div>
        {rootCount !== undefined && rootCount > 0 && (
          <Badge
            variant="secondary"
            className="shrink-0 h-5 min-w-5 justify-center px-1.5 text-xs font-normal"
          >
            {rootCount}
          </Badge>
        )}
      </button>
      {folders.map((folder) => (
        <FolderItem
          key={folder.path}
          folder={folder}
          selectedPath={selectedPath}
          onSelectPath={onSelectPath}
          depth={0}
        />
      ))}
    </div>
  );
}

interface FolderItemProps {
  folder: FolderNode;
  selectedPath: string | null;
  onSelectPath: (path: string | null) => void;
  depth: number;
}

function FolderItem({
  folder,
  selectedPath,
  onSelectPath,
  depth,
}: FolderItemProps) {
  const [expanded, setExpanded] = useState(
    selectedPath?.startsWith(folder.path) || false
  );
  const hasChildren = folder.children.length > 0;
  const isSelected = selectedPath === folder.path;

  return (
    <div>
      <button
        onClick={() => {
          onSelectPath(folder.path);
          if (hasChildren) setExpanded(!expanded);
        }}
        className={cn(
          "w-full flex items-center justify-between gap-2 px-2 py-1.5 rounded-md text-sm transition-colors",
          isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted"
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <div className="flex items-center gap-1 min-w-0">
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 shrink-0" />
            )
          ) : (
            <span className="w-3.5 shrink-0" />
          )}
          {expanded ? (
            <FolderOpen className="h-4 w-4 shrink-0" />
          ) : (
            <Folder className="h-4 w-4 shrink-0" />
          )}
          <span className="truncate">{folder.name}</span>
        </div>
        {folder.count > 0 && (
          <Badge
            variant="secondary"
            className="shrink-0 h-5 min-w-5 justify-center px-1.5 text-xs font-normal"
          >
            {folder.count}
          </Badge>
        )}
      </button>
      {expanded && hasChildren && (
        <div>
          {folder.children.map((child) => (
            <FolderItem
              key={child.path}
              folder={child}
              selectedPath={selectedPath}
              onSelectPath={onSelectPath}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
