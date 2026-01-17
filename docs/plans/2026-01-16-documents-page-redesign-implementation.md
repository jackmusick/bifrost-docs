# Documents Page Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the documents page from a file-manager aesthetic to a Notion/Starlight-inspired documentation experience with section-based navigation and embedded document viewing.

**Architecture:** Replace the folder tree + data table pattern with a section-based sidebar showing documents inline. Document detail becomes two-column with content + right rail (ToC, Related, Attachments). All wrapped with flush, borderless styling.

**Tech Stack:** React, TailwindCSS, TipTap, React Router, TanStack Query, shadcn/ui components (Collapsible, ScrollArea, Input)

---

## Phase 1: Section-Based Sidebar Component

Build the new sidebar navigation that displays L1 sections, L2 subsections, L3+ flattened groups, and documents.

### Task 1.1: Create Section Data Utilities

**Files:**
- Create: `client/src/hooks/useDocumentSections.ts`

**Step 1: Create the hook file with types**

```typescript
import { useMemo } from "react";
import { useFolders, useDocuments, type Document, type FolderCount } from "./useDocuments";

// A section item can be a section header, subsection, flattened group, or document
export type SectionItemType = "section" | "subsection" | "flattened-group" | "document";

export interface SectionItem {
  type: SectionItemType;
  id: string; // path for sections, doc.id for documents
  label: string; // display name
  path: string; // full path
  depth: number; // 0 = L1, 1 = L2, 2+ = flattened
  documentCount?: number; // for sections/subsections
  document?: Document; // for document items
  children?: SectionItem[]; // nested items
}

export interface SectionTree {
  sections: SectionItem[];
  isLoading: boolean;
}

/**
 * Builds a section tree from folder counts and documents.
 * - L1: Top-level paths become sections
 * - L2: Second-level paths become subsections
 * - L3+: Deeper paths are flattened with · separator
 * - Documents appear under their parent section/group
 */
export function buildSectionTree(
  folders: FolderCount[],
  documents: Document[]
): SectionItem[] {
  const result: SectionItem[] = [];

  // Group documents by their immediate parent path
  const docsByPath = new Map<string, Document[]>();
  for (const doc of documents) {
    const existing = docsByPath.get(doc.path) || [];
    existing.push(doc);
    docsByPath.set(doc.path, existing);
  }

  // Build unique paths sorted by depth then alphabetically
  const uniquePaths = [...new Set(folders.map(f => f.path))].sort((a, b) => {
    const depthA = a.split("/").filter(Boolean).length;
    const depthB = b.split("/").filter(Boolean).length;
    if (depthA !== depthB) return depthA - depthB;
    return a.localeCompare(b);
  });

  // Track which paths we've processed
  const processedPaths = new Set<string>();

  for (const path of uniquePaths) {
    if (path === "/") continue; // Skip root, documents at root go into first section or "General"
    if (processedPaths.has(path)) continue;

    const parts = path.split("/").filter(Boolean);
    const depth = parts.length - 1;

    if (depth === 0) {
      // L1 Section
      const section = buildSectionItem(path, parts, depth, folders, docsByPath, processedPaths, uniquePaths);
      result.push(section);
    }
  }

  // Handle root documents - add them to a "General" section if they exist
  const rootDocs = docsByPath.get("/") || [];
  if (rootDocs.length > 0) {
    const generalSection: SectionItem = {
      type: "section",
      id: "/",
      label: "General",
      path: "/",
      depth: 0,
      documentCount: rootDocs.length,
      children: rootDocs.map(doc => ({
        type: "document" as const,
        id: doc.id,
        label: doc.name,
        path: doc.path,
        depth: 1,
        document: doc,
      })),
    };
    result.unshift(generalSection);
  }

  return result;
}

function buildSectionItem(
  path: string,
  parts: string[],
  depth: number,
  folders: FolderCount[],
  docsByPath: Map<string, Document[]>,
  processedPaths: Set<string>,
  allPaths: string[]
): SectionItem {
  processedPaths.add(path);

  const folderCount = folders.find(f => f.path === path)?.count || 0;
  const children: SectionItem[] = [];

  // Add documents directly in this path
  const docsHere = docsByPath.get(path) || [];
  for (const doc of docsHere) {
    children.push({
      type: "document",
      id: doc.id,
      label: doc.name,
      path: doc.path,
      depth: Math.min(depth + 1, 2),
      document: doc,
    });
  }

  // Find child paths
  const childPaths = allPaths.filter(p => {
    if (p === path || processedPaths.has(p)) return false;
    const pParts = p.split("/").filter(Boolean);
    // Check if this is a direct child
    if (pParts.length === parts.length + 1) {
      return p.startsWith(path + "/") || (path === "/" + parts.join("/") && p.startsWith("/" + parts.join("/") + "/"));
    }
    return false;
  });

  for (const childPath of childPaths) {
    const childParts = childPath.split("/").filter(Boolean);
    const childDepth = childParts.length - 1;

    if (childDepth === 1) {
      // L2 Subsection
      const subsection = buildSectionItem(childPath, childParts, childDepth, folders, docsByPath, processedPaths, allPaths);
      subsection.type = "subsection";
      children.push(subsection);
    } else if (childDepth >= 2) {
      // L3+ - flatten these
      const flattenedGroup = buildFlattenedGroup(childPath, childParts, folders, docsByPath, processedPaths, allPaths);
      children.push(flattenedGroup);
    }
  }

  return {
    type: depth === 0 ? "section" : "subsection",
    id: path,
    label: parts[parts.length - 1],
    path,
    depth,
    documentCount: folderCount,
    children: children.length > 0 ? children : undefined,
  };
}

function buildFlattenedGroup(
  path: string,
  parts: string[],
  folders: FolderCount[],
  docsByPath: Map<string, Document[]>,
  processedPaths: Set<string>,
  allPaths: string[]
): SectionItem {
  processedPaths.add(path);

  // Collect all nested paths under this one
  const nestedPaths = allPaths.filter(p => p.startsWith(path + "/") && !processedPaths.has(p));

  // Build flattened label: parts after L2 joined with ·
  const flattenedParts = parts.slice(2); // Skip L1 and L2
  const label = flattenedParts.join(" · ");

  const children: SectionItem[] = [];

  // Add documents at this path
  const docsHere = docsByPath.get(path) || [];
  for (const doc of docsHere) {
    children.push({
      type: "document",
      id: doc.id,
      label: doc.name,
      path: doc.path,
      depth: 2,
      document: doc,
    });
  }

  // Recursively process nested paths
  for (const nestedPath of nestedPaths) {
    processedPaths.add(nestedPath);
    const nestedParts = nestedPath.split("/").filter(Boolean);
    const nestedFlattenedParts = nestedParts.slice(2);
    const nestedLabel = nestedFlattenedParts.join(" · ");

    const nestedDocs = docsByPath.get(nestedPath) || [];
    if (nestedDocs.length > 0) {
      // Add as another flattened group
      children.push({
        type: "flattened-group",
        id: nestedPath,
        label: nestedLabel,
        path: nestedPath,
        depth: 2,
        documentCount: nestedDocs.length,
        children: nestedDocs.map(doc => ({
          type: "document" as const,
          id: doc.id,
          label: doc.name,
          path: doc.path,
          depth: 2,
          document: doc,
        })),
      });
    }
  }

  const folderCount = folders.find(f => f.path === path)?.count || 0;

  return {
    type: "flattened-group",
    id: path,
    label,
    path,
    depth: 2,
    documentCount: folderCount,
    children: children.length > 0 ? children : undefined,
  };
}

/**
 * Hook to get section tree for document sidebar
 */
export function useDocumentSections(orgId: string): SectionTree {
  const { data: foldersData, isLoading: foldersLoading } = useFolders(orgId);
  const { data: documentsData, isLoading: documentsLoading } = useDocuments(orgId, {
    pagination: { limit: 1000, offset: 0 }, // Get all docs for tree
    showDisabled: true,
  });

  const sections = useMemo(() => {
    if (!foldersData?.folders || !documentsData?.items) {
      return [];
    }
    return buildSectionTree(foldersData.folders, documentsData.items);
  }, [foldersData, documentsData]);

  return {
    sections,
    isLoading: foldersLoading || documentsLoading,
  };
}
```

**Step 2: Verify the file was created correctly**

Run: `cat client/src/hooks/useDocumentSections.ts | head -20`
Expected: First 20 lines of the hook file

**Step 3: Commit**

```bash
git add client/src/hooks/useDocumentSections.ts
git commit -m "feat(docs): add useDocumentSections hook with section tree builder"
```

---

### Task 1.2: Create DocumentSidebar Component

**Files:**
- Create: `client/src/components/documents/DocumentSidebar.tsx`

**Step 1: Create the sidebar component**

```typescript
import { useState, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronDown, ChevronRight, FileText, Search, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { useDocumentSections, type SectionItem } from "@/hooks/useDocumentSections";
import { usePermissions } from "@/hooks/usePermissions";

interface DocumentSidebarProps {
  selectedDocumentId?: string;
  onCreateDocument?: (path: string) => void;
}

export function DocumentSidebar({ selectedDocumentId, onCreateDocument }: DocumentSidebarProps) {
  const { orgId } = useParams<{ orgId: string }>();
  const navigate = useNavigate();
  const [filter, setFilter] = useState("");
  const { sections, isLoading } = useDocumentSections(orgId!);
  const { canEdit } = usePermissions();

  // Filter sections based on search
  const filteredSections = useMemo(() => {
    if (!filter.trim()) return sections;

    const lowerFilter = filter.toLowerCase();

    function filterItem(item: SectionItem): SectionItem | null {
      // Check if this item matches
      const matches = item.label.toLowerCase().includes(lowerFilter);

      // Filter children recursively
      const filteredChildren = item.children
        ?.map(filterItem)
        .filter((child): child is SectionItem => child !== null);

      // Include if matches or has matching children
      if (matches || (filteredChildren && filteredChildren.length > 0)) {
        return {
          ...item,
          children: filteredChildren,
        };
      }

      return null;
    }

    return sections
      .map(filterItem)
      .filter((item): item is SectionItem => item !== null);
  }, [sections, filter]);

  const handleDocumentClick = (docId: string) => {
    navigate(`/org/${orgId}/documents/${docId}`);
  };

  const handleCreateInSection = (path: string) => {
    onCreateDocument?.(path);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-3 border-b">
          <Skeleton className="h-9 w-full" />
        </div>
        <div className="p-3 space-y-2">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-6 w-28 mt-4" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filter Input */}
      <div className="p-3 border-b border-border">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Filter documents..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-8 h-9"
          />
        </div>
      </div>

      {/* Section Tree */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {filteredSections.length === 0 ? (
            <div className="px-3 py-8 text-center">
              <FileText className="h-8 w-8 text-muted-foreground/50 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">
                {filter ? "No matching documents" : "No documents yet"}
              </p>
            </div>
          ) : (
            filteredSections.map((section) => (
              <SectionItemComponent
                key={section.id}
                item={section}
                selectedDocumentId={selectedDocumentId}
                onDocumentClick={handleDocumentClick}
                onCreateInSection={canEdit ? handleCreateInSection : undefined}
                defaultExpanded={!filter}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

interface SectionItemComponentProps {
  item: SectionItem;
  selectedDocumentId?: string;
  onDocumentClick: (docId: string) => void;
  onCreateInSection?: (path: string) => void;
  defaultExpanded?: boolean;
}

function SectionItemComponent({
  item,
  selectedDocumentId,
  onDocumentClick,
  onCreateInSection,
  defaultExpanded = true,
}: SectionItemComponentProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Document item
  if (item.type === "document") {
    const isSelected = selectedDocumentId === item.id;
    return (
      <button
        onClick={() => onDocumentClick(item.id)}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors text-left",
          isSelected
            ? "bg-primary/10 text-primary font-medium"
            : "text-foreground/80 hover:bg-muted"
        )}
        style={{ paddingLeft: `${12 + item.depth * 12}px` }}
      >
        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="truncate">{item.label}</span>
      </button>
    );
  }

  // Section, Subsection, or Flattened Group
  const hasChildren = item.children && item.children.length > 0;
  const isSection = item.type === "section";
  const isFlattenedGroup = item.type === "flattened-group";

  return (
    <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
      <div className="group">
        <CollapsibleTrigger asChild>
          <button
            className={cn(
              "w-full flex items-center justify-between gap-2 rounded-md text-sm transition-colors text-left",
              isSection
                ? "px-3 py-2 font-semibold text-foreground hover:bg-muted"
                : isFlattenedGroup
                ? "px-3 py-1.5 text-muted-foreground hover:bg-muted"
                : "px-3 py-1.5 font-medium text-foreground/90 hover:bg-muted"
            )}
            style={{ paddingLeft: isSection ? "12px" : `${12 + item.depth * 12}px` }}
          >
            <div className="flex items-center gap-1.5 min-w-0">
              {hasChildren && (
                isExpanded ? (
                  <ChevronDown className="h-3.5 w-3.5 shrink-0" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 shrink-0" />
                )
              )}
              {!hasChildren && <span className="w-3.5 shrink-0" />}
              <span className="truncate">{item.label}</span>
            </div>
            {onCreateInSection && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => {
                  e.stopPropagation();
                  onCreateInSection(item.path);
                }}
              >
                <Plus className="h-3.5 w-3.5" />
              </Button>
            )}
          </button>
        </CollapsibleTrigger>
      </div>
      {hasChildren && (
        <CollapsibleContent>
          {item.children!.map((child) => (
            <SectionItemComponent
              key={child.id}
              item={child}
              selectedDocumentId={selectedDocumentId}
              onDocumentClick={onDocumentClick}
              onCreateInSection={onCreateInSection}
              defaultExpanded={defaultExpanded}
            />
          ))}
        </CollapsibleContent>
      )}
    </Collapsible>
  );
}
```

**Step 2: Verify the component was created**

Run: `cat client/src/components/documents/DocumentSidebar.tsx | head -30`
Expected: First 30 lines of the component

**Step 3: Commit**

```bash
git add client/src/components/documents/DocumentSidebar.tsx
git commit -m "feat(docs): add DocumentSidebar component with section tree navigation"
```

---

## Phase 2: Flush Visual Style for Documents Page

Replace the Card wrapper with a flush sidebar layout.

### Task 2.1: Update DocumentsPage Layout

**Files:**
- Modify: `client/src/pages/documents/DocumentsPage.tsx`

**Step 1: Replace the current layout with flush sidebar**

The key changes:
1. Remove Card wrapper around FolderTree
2. Use the new DocumentSidebar
3. Add border-r for thin vertical divider
4. Update flex layout for flush appearance

```typescript
// In DocumentsPage.tsx, replace the entire component with:

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { FileText, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DocumentSidebar } from "@/components/documents/DocumentSidebar";
import { usePermissions } from "@/hooks/usePermissions";

export function DocumentsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const navigate = useNavigate();
  const { canEdit } = usePermissions();

  const handleCreateNew = (path?: string) => {
    const params = new URLSearchParams();
    if (path) {
      params.set("path", path);
    }
    const queryString = params.toString();
    navigate(`/org/${orgId}/documents/new${queryString ? `?${queryString}` : ""}`);
  };

  const emptyContent = (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-20">
        <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-1">No documents yet</h3>
        <p className="text-sm text-muted-foreground text-center mb-4">
          {canEdit
            ? "Get started by creating your first document"
            : "No documents have been added yet"}
        </p>
        {canEdit && (
          <Button onClick={() => handleCreateNew()}>
            <Plus className="mr-2 h-4 w-4" />
            Add Document
          </Button>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Document Sidebar - flush, no card */}
      <aside className="w-64 shrink-0 border-r border-border hidden md:block">
        <DocumentSidebar onCreateDocument={handleCreateNew} />
      </aside>

      {/* Main Content - placeholder for now, will show selected doc */}
      <main className="flex-1 p-6 overflow-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
            <p className="text-muted-foreground mt-1">
              Browse and manage documentation
            </p>
          </div>
          {canEdit && (
            <Button onClick={() => handleCreateNew()}>
              <Plus className="mr-2 h-4 w-4" />
              New Document
            </Button>
          )}
        </div>

        {/* Empty state or selected document preview */}
        {emptyContent}
      </main>
    </div>
  );
}
```

**Step 2: Verify the changes compile**

Run: `cd client && npm run tsc 2>&1 | head -20`
Expected: No errors related to DocumentsPage

**Step 3: Commit**

```bash
git add client/src/pages/documents/DocumentsPage.tsx
git commit -m "feat(docs): update DocumentsPage with flush sidebar layout"
```

---

## Phase 3: Document Detail Two-Column Layout

Update the document detail page with centered content and right rail.

### Task 3.1: Create TableOfContents Component

**Files:**
- Create: `client/src/components/documents/TableOfContents.tsx`

**Step 1: Create the ToC component that parses HTML headings**

```typescript
import { useMemo, useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface TocHeading {
  id: string;
  text: string;
  level: number;
}

interface TableOfContentsProps {
  content: string;
  className?: string;
}

/**
 * Parses HTML content and extracts h1, h2, h3 headings for table of contents.
 * Creates IDs for headings if they don't exist.
 */
function parseHeadings(html: string): TocHeading[] {
  if (!html) return [];

  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const headings: TocHeading[] = [];

  doc.querySelectorAll("h1, h2, h3").forEach((heading, index) => {
    const text = heading.textContent?.trim() || "";
    if (!text) return;

    // Generate ID from text if not present
    const id = heading.id || `heading-${index}-${text.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
    const level = parseInt(heading.tagName[1], 10);

    headings.push({ id, text, level });
  });

  return headings;
}

export function TableOfContents({ content, className }: TableOfContentsProps) {
  const headings = useMemo(() => parseHeadings(content), [content]);
  const [activeId, setActiveId] = useState<string>("");

  // Track active heading on scroll
  useEffect(() => {
    if (headings.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      { rootMargin: "-80px 0px -80% 0px" }
    );

    // Observe all headings
    headings.forEach(({ id }) => {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    });

    return () => observer.disconnect();
  }, [headings]);

  const handleClick = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveId(id);
    }
  };

  if (headings.length === 0) {
    return null;
  }

  return (
    <nav className={cn("space-y-1", className)}>
      <h3 className="text-sm font-semibold text-foreground mb-3">On this page</h3>
      {headings.map((heading) => (
        <button
          key={heading.id}
          onClick={() => handleClick(heading.id)}
          className={cn(
            "block w-full text-left text-sm py-1 transition-colors hover:text-foreground",
            heading.level === 1 && "font-medium",
            heading.level === 2 && "pl-3",
            heading.level === 3 && "pl-6 text-xs",
            activeId === heading.id
              ? "text-primary font-medium"
              : "text-muted-foreground"
          )}
        >
          {heading.text}
        </button>
      ))}
    </nav>
  );
}

/**
 * Hook to inject IDs into headings in rendered content.
 * Call this effect in the document detail page after content renders.
 */
export function useHeadingIds(content: string) {
  useEffect(() => {
    if (!content) return;

    // Find all headings in the document content area
    const container = document.querySelector("[data-document-content]");
    if (!container) return;

    container.querySelectorAll("h1, h2, h3").forEach((heading, index) => {
      if (!heading.id) {
        const text = heading.textContent?.trim() || "";
        heading.id = `heading-${index}-${text.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
      }
    });
  }, [content]);
}
```

**Step 2: Verify the file compiles**

Run: `cd client && npm run tsc 2>&1 | grep -i "tableofcontents" || echo "No errors"`
Expected: No errors

**Step 3: Commit**

```bash
git add client/src/components/documents/TableOfContents.tsx
git commit -m "feat(docs): add TableOfContents component with heading parsing and smooth scroll"
```

---

### Task 3.2: Create DocumentRightRail Component

**Files:**
- Create: `client/src/components/documents/DocumentRightRail.tsx`

**Step 1: Create the right rail component**

```typescript
import { TableOfContents } from "./TableOfContents";
import { RelatedItemsSidebar } from "@/components/relationships/RelatedItemsSidebar";
import { EntityAttachments } from "@/components/shared/EntityAttachments";
import { type EntityType } from "@/lib/entity-icons";

interface DocumentRightRailProps {
  orgId: string;
  documentId: string;
  content: string;
}

export function DocumentRightRail({ orgId, documentId, content }: DocumentRightRailProps) {
  return (
    <aside className="w-64 shrink-0 hidden xl:block border-l border-border">
      <div className="sticky top-0 p-4 space-y-6 max-h-screen overflow-y-auto">
        {/* Table of Contents */}
        <TableOfContents content={content} />

        {/* Related Items - simplified, no card wrapper */}
        <div className="pt-4 border-t border-border">
          <RelatedItemsRail orgId={orgId} entityType="document" entityId={documentId} />
        </div>

        {/* Attachments - simplified, no card wrapper */}
        <div className="pt-4 border-t border-border">
          <AttachmentsRail entityType="document" entityId={documentId} />
        </div>
      </div>
    </aside>
  );
}

// Simplified versions without Card wrappers
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Link2, Plus, X, Loader2, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useRelationships,
  useDeleteRelationship,
  groupRelationshipsByType,
  type ResolvedRelationship,
} from "@/hooks/useRelationships";
import {
  getEntityIcon,
  getEntityLabel,
  getEntityRoute,
} from "@/lib/entity-icons";
import { AddRelationshipDialog } from "@/components/relationships/AddRelationshipDialog";
import { useAttachments, useDeleteAttachment } from "@/hooks/useAttachments";
import { toast } from "sonner";

interface RelatedItemsRailProps {
  orgId: string;
  entityType: EntityType;
  entityId: string;
}

function RelatedItemsRail({ orgId, entityType, entityId }: RelatedItemsRailProps) {
  const navigate = useNavigate();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  const { data, isLoading } = useRelationships(orgId, entityType, entityId);
  const deleteRelationship = useDeleteRelationship(orgId);

  const relationships = data?.relationships ?? [];
  const groupedRelationships = groupRelationshipsByType(relationships);
  const entityTypes = Object.keys(groupedRelationships) as EntityType[];

  const handleNavigate = (rel: ResolvedRelationship) => {
    const route = getEntityRoute(rel.entity.entity_type);
    let path: string;
    if (rel.entity.entity_type === "custom_asset" && rel.entity.asset_type_id) {
      path = `/org/${orgId}/${route}/${rel.entity.asset_type_id}/${rel.entity.id}`;
    } else {
      path = `/org/${orgId}/${route}/${rel.entity.id}`;
    }
    navigate(path);
  };

  const handleRemove = async (rel: ResolvedRelationship, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteRelationship.mutateAsync(rel.relationship.id);
      toast.success("Relationship removed");
    } catch {
      toast.error("Failed to remove relationship");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Link2 className="h-4 w-4" />
          Related
        </h3>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={() => setIsAddDialogOpen(true)}
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {relationships.length === 0 ? (
        <p className="text-xs text-muted-foreground">No related items</p>
      ) : (
        <div className="space-y-2">
          {entityTypes.map((type) => {
            const Icon = getEntityIcon(type);
            const rels = groupedRelationships[type];
            return (
              <div key={type} className="space-y-1">
                {rels.map((rel) => (
                  <div
                    key={rel.relationship.id}
                    className="group flex items-center gap-2 text-sm hover:text-foreground cursor-pointer text-muted-foreground"
                    onClick={() => handleNavigate(rel)}
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate flex-1">{rel.entity.name}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100"
                      onClick={(e) => handleRemove(rel, e)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}

      <AddRelationshipDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        orgId={orgId}
        sourceEntityType={entityType}
        sourceEntityId={entityId}
      />
    </>
  );
}

interface AttachmentsRailProps {
  entityType: string;
  entityId: string;
}

function AttachmentsRail({ entityType, entityId }: AttachmentsRailProps) {
  const { data, isLoading } = useAttachments(entityType, entityId);
  const deleteAttachment = useDeleteAttachment(entityType, entityId);

  const handleDelete = async (attachmentId: string) => {
    try {
      await deleteAttachment.mutateAsync(attachmentId);
      toast.success("Attachment removed");
    } catch {
      toast.error("Failed to remove attachment");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  }

  const attachments = data?.attachments ?? [];

  return (
    <>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Paperclip className="h-4 w-4" />
          Attachments
        </h3>
      </div>

      {attachments.length === 0 ? (
        <p className="text-xs text-muted-foreground">No attachments</p>
      ) : (
        <div className="space-y-1">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="group flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            >
              <Paperclip className="h-3.5 w-3.5 shrink-0" />
              <a
                href={attachment.url}
                target="_blank"
                rel="noopener noreferrer"
                className="truncate flex-1 hover:underline"
              >
                {attachment.filename}
              </a>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100"
                onClick={() => handleDelete(attachment.id)}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
```

**Step 2: Verify the file compiles**

Run: `cd client && npm run tsc 2>&1 | grep -i "rightrail\|error" | head -10`
Expected: No errors (may need to adjust imports based on actual codebase)

**Step 3: Commit**

```bash
git add client/src/components/documents/DocumentRightRail.tsx
git commit -m "feat(docs): add DocumentRightRail component with ToC, Related, and Attachments"
```

---

### Task 3.3: Update DocumentDetailPage with Two-Column Layout

**Files:**
- Modify: `client/src/pages/documents/DocumentDetailPage.tsx`

**Step 1: Update the layout to two-column with right rail**

Key changes:
1. Remove card wrappers
2. Add centered content column with max-width
3. Add DocumentRightRail on the right
4. Add data-document-content attribute for heading ID injection
5. Use useHeadingIds hook

```typescript
// Replace the return statement in DocumentDetailPage with the new layout
// Add these imports at the top:
import { DocumentRightRail } from "@/components/documents/DocumentRightRail";
import { useHeadingIds } from "@/components/documents/TableOfContents";

// Inside the component, add this hook call after other hooks:
useHeadingIds(displayContent);

// Replace the return JSX with:
return (
  <div className="flex h-full">
    {/* Main Content Column */}
    <div className="flex-1 overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-6">
        {/* Header */}
        <div className="space-y-4 mb-8">
          {/* Breadcrumb and Actions */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Link
                to={`/org/${orgId}/documents`}
                className="hover:text-foreground transition-colors"
              >
                Documents
              </Link>
              <span>/</span>
              <span>{displayName || "New Document"}</span>
            </div>
            <div className="flex items-center gap-2">
              {/* ... keep existing action buttons ... */}
            </div>
          </div>

          {/* Disabled Banner */}
          {!isNewDocument && !isEditing && document && !document.is_enabled && (
            <Alert variant="destructive">
              <AlertDescription>
                This document has been disabled and will not appear in search or lists
              </AlertDescription>
            </Alert>
          )}

          {/* Title */}
          {isEditing ? (
            <div className="space-y-3">
              <Input
                value={editState.name}
                onChange={(e) => setEditState({ ...editState, name: e.target.value })}
                placeholder="Document title"
                className="text-3xl font-bold h-auto py-2 border-none shadow-none focus-visible:ring-0 px-0"
                autoFocus={isNewDocument}
              />
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Folder className="h-4 w-4" />
                <Input
                  value={editState.path}
                  onChange={(e) => setEditState({ ...editState, path: e.target.value })}
                  placeholder="/"
                  className="h-7 text-sm font-mono max-w-xs"
                />
              </div>
            </div>
          ) : (
            <div className={document && !document.is_enabled ? "opacity-60" : ""}>
              <h1 className="text-3xl font-bold tracking-tight">{displayName}</h1>
              <div className="flex items-center gap-2 mt-2 text-sm text-muted-foreground">
                <Folder className="h-4 w-4" />
                <span className="font-mono">{displayPath}</span>
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        <div
          data-document-content
          className={document && !document.is_enabled && !isEditing ? "opacity-60" : ""}
        >
          {isEditing ? (
            <TiptapEditor
              content={editState.content}
              onChange={(content) => setEditState({ ...editState, content })}
              readOnly={false}
              orgId={orgId}
              className="border-none shadow-none"
            />
          ) : displayContent ? (
            <TiptapEditor
              content={displayContent}
              readOnly
              orgId={orgId}
              className="border-none shadow-none"
            />
          ) : (
            <div className="py-12 text-center">
              <p className="text-sm text-muted-foreground italic">No content yet</p>
              {canEdit && (
                <Button variant="outline" className="mt-4" onClick={handleStartEdit}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Add Content
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>

    {/* Right Rail - only for existing documents, not in edit mode */}
    {!isNewDocument && !isEditing && (
      <DocumentRightRail
        orgId={orgId}
        documentId={id}
        content={displayContent}
      />
    )}

    {/* Delete Confirmation */}
    {/* ... keep existing ConfirmDialog ... */}
  </div>
);
```

**Step 2: Verify the changes compile**

Run: `cd client && npm run tsc 2>&1 | grep -i "documentdetail\|error" | head -10`
Expected: No errors

**Step 3: Commit**

```bash
git add client/src/pages/documents/DocumentDetailPage.tsx
git commit -m "feat(docs): update DocumentDetailPage with two-column layout and right rail"
```

---

## Phase 4: TipTap Styling Updates

Remove borders from TipTap to make content feel embedded.

### Task 4.1: Update TiptapEditor for Borderless Display

**Files:**
- Modify: `client/src/components/documents/TiptapEditor.tsx`

**Step 1: Add support for borderless mode via className**

Update the wrapper div to conditionally remove border:

```typescript
// In TiptapEditor.tsx, update the return statement:
return (
  <div className={cn(
    "overflow-hidden",
    // Only add border/rounded if className doesn't include border-none
    !className?.includes("border-none") && "border rounded-md",
    className
  )}>
    {!readOnly && (
      <TiptapToolbar editor={editor} onImageUpload={handleImageUpload} />
    )}
    <EditorContent editor={editor} />
  </div>
);
```

**Step 2: Verify the changes compile**

Run: `cd client && npm run tsc 2>&1 | grep -i "tiptap\|error" | head -5`
Expected: No errors

**Step 3: Commit**

```bash
git add client/src/components/documents/TiptapEditor.tsx
git commit -m "feat(docs): allow borderless TipTap editor via className"
```

---

## Phase 5: Mobile Responsive Dropdowns

Add mobile navigation dropdowns.

### Task 5.1: Create MobileDocNav Component

**Files:**
- Create: `client/src/components/documents/MobileDocNav.tsx`

**Step 1: Create mobile navigation with dropdowns**

```typescript
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ChevronDown, FileText, Menu, List } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TableOfContents } from "./TableOfContents";
import { useDocumentSections, type SectionItem } from "@/hooks/useDocumentSections";

interface MobileDocNavProps {
  currentDocumentName?: string;
  documentContent?: string;
  selectedDocumentId?: string;
}

export function MobileDocNav({
  currentDocumentName,
  documentContent,
  selectedDocumentId,
}: MobileDocNavProps) {
  const { orgId } = useParams<{ orgId: string }>();
  const navigate = useNavigate();
  const { sections, isLoading } = useDocumentSections(orgId!);
  const [tocOpen, setTocOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  const handleDocumentClick = (docId: string) => {
    navigate(`/org/${orgId}/documents/${docId}`);
    setNavOpen(false);
  };

  // Flatten sections for mobile dropdown
  const flattenedDocs: { id: string; name: string; path: string }[] = [];

  function collectDocs(items: SectionItem[]) {
    for (const item of items) {
      if (item.type === "document" && item.document) {
        flattenedDocs.push({
          id: item.document.id,
          name: item.document.name,
          path: item.path,
        });
      }
      if (item.children) {
        collectDocs(item.children);
      }
    }
  }

  if (!isLoading) {
    collectDocs(sections);
  }

  return (
    <div className="flex items-center gap-2 md:hidden border-b border-border p-3 bg-background sticky top-0 z-10">
      {/* Document Navigation Dropdown */}
      <DropdownMenu open={navOpen} onOpenChange={setNavOpen}>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-2">
            <Menu className="h-4 w-4" />
            <span className="truncate max-w-32">{currentDocumentName || "Documents"}</span>
            <ChevronDown className="h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-72">
          <DropdownMenuLabel>Documents</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <ScrollArea className="h-64">
            {flattenedDocs.map((doc) => (
              <DropdownMenuItem
                key={doc.id}
                onClick={() => handleDocumentClick(doc.id)}
                className={cn(
                  "cursor-pointer",
                  selectedDocumentId === doc.id && "bg-primary/10"
                )}
              >
                <FileText className="h-4 w-4 mr-2 shrink-0" />
                <span className="truncate">{doc.name}</span>
              </DropdownMenuItem>
            ))}
          </ScrollArea>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Table of Contents Dropdown - only show if document has content */}
      {documentContent && (
        <DropdownMenu open={tocOpen} onOpenChange={setTocOpen}>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <List className="h-4 w-4" />
              <span>On this page</span>
              <ChevronDown className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-64 p-3">
            <TableOfContents content={documentContent} />
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
```

**Step 2: Verify the component compiles**

Run: `cd client && npm run tsc 2>&1 | grep -i "mobiledocnav\|error" | head -5`
Expected: No errors

**Step 3: Commit**

```bash
git add client/src/components/documents/MobileDocNav.tsx
git commit -m "feat(docs): add MobileDocNav component with dropdown navigation"
```

---

## Phase 6: Backend - Section Rename/Batch Path Update

Add API endpoint for batch path updates when renaming sections.

### Task 6.1: Add Batch Path Update Endpoint

**Files:**
- Modify: `api/src/routers/documents.py`
- Modify: `api/src/repositories/document.py`

**Step 1: Add request/response models and endpoint to documents.py**

Add after the existing imports and models:

```python
class BatchPathUpdateRequest(BaseModel):
    """Request to update paths for section rename."""
    old_path_prefix: str
    new_path_prefix: str
    merge_if_exists: bool = False

class BatchPathUpdateResponse(BaseModel):
    """Response for batch path update."""
    updated_count: int
    conflicts: list[str] = []  # Document names that would conflict

# Add this endpoint after batch_toggle_documents:

@router.patch("/batch/paths", response_model=BatchPathUpdateResponse)
async def batch_update_paths(
    org_id: UUID,
    request: BatchPathUpdateRequest,
    current_user: RequireContributor,
    db: DbSession,
) -> BatchPathUpdateResponse:
    """
    Batch update document paths for section rename/merge.

    This endpoint allows renaming a section (path prefix) which updates
    all documents under that path.

    Args:
        org_id: Organization UUID
        request: Batch path update request with old and new prefixes
        current_user: Current authenticated user
        db: Database session

    Returns:
        Number of documents updated and any conflicts
    """
    doc_repo = DocumentRepository(db)

    # Check for conflicts if not merging
    if not request.merge_if_exists:
        conflicts = await doc_repo.check_path_conflicts(
            org_id,
            request.old_path_prefix,
            request.new_path_prefix,
        )
        if conflicts:
            return BatchPathUpdateResponse(
                updated_count=0,
                conflicts=conflicts,
            )

    # Perform the batch update
    updated_count = await doc_repo.batch_update_paths(
        org_id,
        request.old_path_prefix,
        request.new_path_prefix,
    )

    logger.info(
        f"Batch path update: {updated_count} docs from '{request.old_path_prefix}' to '{request.new_path_prefix}'",
        extra={
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
            "updated_count": updated_count,
        },
    )

    return BatchPathUpdateResponse(updated_count=updated_count)
```

**Step 2: Add repository methods**

Add to `api/src/repositories/document.py`:

```python
async def check_path_conflicts(
    self,
    org_id: UUID,
    old_prefix: str,
    new_prefix: str,
) -> list[str]:
    """
    Check if renaming paths would create conflicts.
    Returns list of document names that would conflict.
    """
    from sqlalchemy import select, func, and_

    # Find documents that would move to paths that already have docs with same name
    # Get docs to be moved
    docs_to_move = await self.session.execute(
        select(Document.name, Document.path)
        .where(
            and_(
                Document.organization_id == org_id,
                Document.path.startswith(old_prefix),
            )
        )
    )
    moving_docs = docs_to_move.all()

    conflicts = []
    for name, old_path in moving_docs:
        new_path = new_prefix + old_path[len(old_prefix):]
        # Check if a doc with same name exists at new path
        existing = await self.session.execute(
            select(Document.id)
            .where(
                and_(
                    Document.organization_id == org_id,
                    Document.path == new_path,
                    Document.name == name,
                )
            )
        )
        if existing.first():
            conflicts.append(name)

    return conflicts

async def batch_update_paths(
    self,
    org_id: UUID,
    old_prefix: str,
    new_prefix: str,
) -> int:
    """
    Update all document paths from old prefix to new prefix.
    """
    from sqlalchemy import update, func

    # Use SQL REPLACE to update path prefix
    result = await self.session.execute(
        update(Document)
        .where(
            and_(
                Document.organization_id == org_id,
                Document.path.startswith(old_prefix),
            )
        )
        .values(
            path=func.replace(Document.path, old_prefix, new_prefix)
        )
    )
    await self.session.commit()

    return result.rowcount
```

**Step 3: Run type checker**

Run: `cd api && pyright src/routers/documents.py 2>&1 | head -10`
Expected: No errors

**Step 4: Commit**

```bash
git add api/src/routers/documents.py api/src/repositories/document.py
git commit -m "feat(api): add batch path update endpoint for section rename"
```

---

### Task 6.2: Add Frontend Hook for Section Rename

**Files:**
- Modify: `client/src/hooks/useDocuments.ts`

**Step 1: Add the mutation hook**

Add to useDocuments.ts:

```typescript
export interface BatchPathUpdateRequest {
  old_path_prefix: string;
  new_path_prefix: string;
  merge_if_exists?: boolean;
}

export interface BatchPathUpdateResponse {
  updated_count: number;
  conflicts: string[];
}

export function useBatchUpdatePaths(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BatchPathUpdateRequest) => {
      const response = await api.patch<BatchPathUpdateResponse>(
        `/api/organizations/${orgId}/documents/batch/paths`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}
```

**Step 2: Verify the changes compile**

Run: `cd client && npm run tsc 2>&1 | grep -i "usedocuments\|error" | head -5`
Expected: No errors

**Step 3: Commit**

```bash
git add client/src/hooks/useDocuments.ts
git commit -m "feat(docs): add useBatchUpdatePaths hook for section rename"
```

---

## Phase 7: Integration and Polish

Wire everything together and add final polish.

### Task 7.1: Update Route Configuration

**Files:**
- Check: `client/src/App.tsx` or routes file

Verify the documents routes are correctly set up. The existing routes should work, but verify:
- `/org/:orgId/documents` → DocumentsPage
- `/org/:orgId/documents/:id` → DocumentDetailPage
- `/org/:orgId/documents/new` → DocumentDetailPage (with isNewDocument=true)

**Step 1: Verify routes exist**

Run: `grep -n "documents" client/src/App.tsx 2>/dev/null || grep -rn "documents" client/src/routes/ 2>/dev/null | head -10`

**Step 2: No changes needed if routes exist, otherwise add them**

---

### Task 7.2: Final Type Check and Lint

**Files:** All modified files

**Step 1: Run full type check**

Run: `cd client && npm run tsc`
Expected: No errors

**Step 2: Run lint**

Run: `cd client && npm run lint`
Expected: No errors (fix any that appear)

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors from documents redesign"
```

---

## Phase 8: Drag-and-Drop Document Reordering

Add drag-and-drop to move documents between sections in the sidebar.

### Task 8.1: Install dnd-kit Library

**Files:**
- Modify: `client/package.json`

**Step 1: Install dnd-kit**

```bash
cd client && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

**Step 2: Verify installation**

Run: `grep dnd-kit client/package.json`
Expected: Shows @dnd-kit packages in dependencies

**Step 3: Commit**

```bash
git add client/package.json client/package-lock.json
git commit -m "chore: add dnd-kit for drag-and-drop support"
```

---

### Task 8.2: Add Drag-and-Drop to DocumentSidebar

**Files:**
- Modify: `client/src/components/documents/DocumentSidebar.tsx`
- Modify: `client/src/hooks/useDocuments.ts`

**Step 1: Add useUpdateDocument hook if not exists**

In useDocuments.ts, ensure there's a mutation for updating a single document's path:

```typescript
export function useMoveDocument(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ documentId, newPath }: { documentId: string; newPath: string }) => {
      const response = await api.put<Document>(
        `/api/organizations/${orgId}/documents/${documentId}`,
        { path: newPath }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
    },
  });
}
```

**Step 2: Update DocumentSidebar with drag-and-drop**

Add to DocumentSidebar.tsx:

```typescript
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useDraggable, useDroppable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { useMoveDocument } from "@/hooks/useDocuments";
import { toast } from "sonner";

// In the DocumentSidebar component, add:
const [activeId, setActiveId] = useState<string | null>(null);
const moveDocument = useMoveDocument(orgId!);

const sensors = useSensors(
  useSensor(PointerSensor, {
    activationConstraint: {
      distance: 8,
    },
  }),
  useSensor(KeyboardSensor)
);

const handleDragStart = (event: DragStartEvent) => {
  setActiveId(event.active.id as string);
};

const handleDragEnd = async (event: DragEndEvent) => {
  const { active, over } = event;
  setActiveId(null);

  if (!over || active.id === over.id) return;

  // Find the document being dragged
  const draggedDocId = active.id as string;
  const targetPath = over.id as string;

  // Only allow dropping on sections/subsections, not on other documents
  if (!targetPath.startsWith("/")) return;

  try {
    await moveDocument.mutateAsync({
      documentId: draggedDocId,
      newPath: targetPath,
    });
    toast.success("Document moved");
  } catch {
    toast.error("Failed to move document");
  }
};

// Wrap the section tree in DndContext:
<DndContext
  sensors={sensors}
  collisionDetection={closestCenter}
  onDragStart={handleDragStart}
  onDragEnd={handleDragEnd}
>
  {/* existing section tree */}
  <DragOverlay>
    {activeId ? (
      <div className="bg-background border rounded-md px-3 py-1.5 text-sm shadow-lg">
        {/* Find and show the dragged document name */}
      </div>
    ) : null}
  </DragOverlay>
</DndContext>
```

**Step 3: Make document items draggable and sections droppable**

Update SectionItemComponent to use useDraggable for documents and useDroppable for sections:

```typescript
// For document items:
function DraggableDocumentItem({ item, selectedDocumentId, onDocumentClick }: {...}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: item.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <button
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      onClick={() => onDocumentClick(item.id)}
      className={cn(
        "w-full flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors text-left cursor-grab active:cursor-grabbing",
        selectedDocumentId === item.id
          ? "bg-primary/10 text-primary font-medium"
          : "text-foreground/80 hover:bg-muted"
      )}
    >
      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="truncate">{item.label}</span>
    </button>
  );
}

// For section/subsection headers:
function DroppableSectionHeader({ item, isExpanded, onToggle, onCreateInSection }: {...}) {
  const { setNodeRef, isOver } = useDroppable({
    id: item.path,
  });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "transition-colors",
        isOver && "bg-primary/5 ring-1 ring-primary/20 rounded-md"
      )}
    >
      {/* existing section header content */}
    </div>
  );
}
```

**Step 4: Verify the changes compile**

Run: `cd client && npm run tsc 2>&1 | head -20`
Expected: No errors

**Step 5: Commit**

```bash
git add client/src/components/documents/DocumentSidebar.tsx client/src/hooks/useDocuments.ts
git commit -m "feat(docs): add drag-and-drop to move documents between sections"
```

---

## Phase 9: Section Picker Cascading Combobox

Replace the path text input with a cascading section picker.

### Task 9.1: Create SectionPicker Component

**Files:**
- Create: `client/src/components/documents/SectionPicker.tsx`

**Step 1: Create the cascading combobox component**

```typescript
import { useState, useMemo } from "react";
import { ChevronRight, Plus, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useFolders, buildFolderTree, type FolderNode } from "@/hooks/useDocuments";

interface SectionPickerProps {
  orgId: string;
  value: string;
  onChange: (path: string) => void;
  className?: string;
}

export function SectionPicker({ orgId, value, onChange, className }: SectionPickerProps) {
  const { data: foldersData } = useFolders(orgId);
  const [open, setOpen] = useState(false);
  const [newSectionName, setNewSectionName] = useState("");
  const [creatingAt, setCreatingAt] = useState<string | null>(null);

  const folderTree = useMemo(() => {
    if (!foldersData?.folders) return [];
    return buildFolderTree(foldersData.folders);
  }, [foldersData]);

  // Parse current value into path segments
  const pathParts = value.split("/").filter(Boolean);

  const handleSelect = (path: string) => {
    onChange(path);
    setOpen(false);
  };

  const handleCreateSection = (parentPath: string) => {
    if (!newSectionName.trim()) return;
    const newPath = parentPath === "/"
      ? `/${newSectionName.trim()}`
      : `${parentPath}/${newSectionName.trim()}`;
    onChange(newPath);
    setNewSectionName("");
    setCreatingAt(null);
    setOpen(false);
  };

  const displayValue = value === "/" ? "Root" : pathParts.join(" / ");

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn("justify-between font-normal", className)}
        >
          <span className="truncate">{displayValue || "Select section..."}</span>
          <ChevronRight className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="start">
        <ScrollArea className="h-72">
          <div className="p-2">
            {/* Root option */}
            <button
              onClick={() => handleSelect("/")}
              className={cn(
                "w-full flex items-center justify-between px-3 py-2 rounded-md text-sm hover:bg-muted",
                value === "/" && "bg-primary/10"
              )}
            >
              <span>Root</span>
              {value === "/" && <Check className="h-4 w-4" />}
            </button>

            {/* Folder tree */}
            {folderTree.map((folder) => (
              <FolderPickerItem
                key={folder.path}
                folder={folder}
                selectedPath={value}
                onSelect={handleSelect}
                depth={0}
                creatingAt={creatingAt}
                onStartCreate={setCreatingAt}
                newSectionName={newSectionName}
                onNewSectionNameChange={setNewSectionName}
                onCreateSection={handleCreateSection}
              />
            ))}

            {/* Create new top-level section */}
            {creatingAt === "/" ? (
              <div className="flex items-center gap-2 px-3 py-2">
                <Input
                  value={newSectionName}
                  onChange={(e) => setNewSectionName(e.target.value)}
                  placeholder="New section name"
                  className="h-8 text-sm"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleCreateSection("/");
                    if (e.key === "Escape") setCreatingAt(null);
                  }}
                />
                <Button size="sm" onClick={() => handleCreateSection("/")}>
                  Add
                </Button>
              </div>
            ) : (
              <button
                onClick={() => setCreatingAt("/")}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <Plus className="h-4 w-4" />
                <span>New section</span>
              </button>
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}

interface FolderPickerItemProps {
  folder: FolderNode;
  selectedPath: string;
  onSelect: (path: string) => void;
  depth: number;
  creatingAt: string | null;
  onStartCreate: (path: string | null) => void;
  newSectionName: string;
  onNewSectionNameChange: (name: string) => void;
  onCreateSection: (parentPath: string) => void;
}

function FolderPickerItem({
  folder,
  selectedPath,
  onSelect,
  depth,
  creatingAt,
  onStartCreate,
  newSectionName,
  onNewSectionNameChange,
  onCreateSection,
}: FolderPickerItemProps) {
  const [expanded, setExpanded] = useState(selectedPath.startsWith(folder.path));
  const isSelected = selectedPath === folder.path;
  const hasChildren = folder.children.length > 0;

  return (
    <div>
      <div className="group flex items-center">
        <button
          onClick={() => onSelect(folder.path)}
          className={cn(
            "flex-1 flex items-center justify-between px-3 py-2 rounded-md text-sm hover:bg-muted text-left",
            isSelected && "bg-primary/10"
          )}
          style={{ paddingLeft: `${12 + depth * 16}px` }}
        >
          <span className="truncate">{folder.name}</span>
          {isSelected && <Check className="h-4 w-4 shrink-0" />}
        </button>
        {hasChildren && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => setExpanded(!expanded)}
          >
            <ChevronRight className={cn("h-3 w-3 transition-transform", expanded && "rotate-90")} />
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
          onClick={() => onStartCreate(folder.path)}
        >
          <Plus className="h-3 w-3" />
        </Button>
      </div>

      {/* Create new subsection */}
      {creatingAt === folder.path && (
        <div className="flex items-center gap-2 py-2" style={{ paddingLeft: `${28 + depth * 16}px` }}>
          <Input
            value={newSectionName}
            onChange={(e) => onNewSectionNameChange(e.target.value)}
            placeholder="New subsection"
            className="h-7 text-sm"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") onCreateSection(folder.path);
              if (e.key === "Escape") onStartCreate(null);
            }}
          />
          <Button size="sm" className="h-7" onClick={() => onCreateSection(folder.path)}>
            Add
          </Button>
        </div>
      )}

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {folder.children.map((child) => (
            <FolderPickerItem
              key={child.path}
              folder={child}
              selectedPath={selectedPath}
              onSelect={onSelect}
              depth={depth + 1}
              creatingAt={creatingAt}
              onStartCreate={onStartCreate}
              newSectionName={newSectionName}
              onNewSectionNameChange={onNewSectionNameChange}
              onCreateSection={onCreateSection}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Verify the component compiles**

Run: `cd client && npm run tsc 2>&1 | grep -i "sectionpicker\|error" | head -5`
Expected: No errors

**Step 3: Commit**

```bash
git add client/src/components/documents/SectionPicker.tsx
git commit -m "feat(docs): add SectionPicker cascading combobox component"
```

---

### Task 9.2: Integrate SectionPicker in DocumentDetailPage

**Files:**
- Modify: `client/src/pages/documents/DocumentDetailPage.tsx`

**Step 1: Replace path input with SectionPicker**

In the edit mode section, replace:

```typescript
<Input
  value={editState.path}
  onChange={(e) => setEditState({ ...editState, path: e.target.value })}
  placeholder="/"
  className="h-7 text-sm font-mono max-w-xs"
/>
```

With:

```typescript
import { SectionPicker } from "@/components/documents/SectionPicker";

// In the JSX:
<SectionPicker
  orgId={orgId}
  value={editState.path}
  onChange={(path) => setEditState({ ...editState, path })}
  className="h-7 text-sm max-w-xs"
/>
```

**Step 2: Verify the changes compile**

Run: `cd client && npm run tsc 2>&1 | grep -i "documentdetail\|error" | head -5`
Expected: No errors

**Step 3: Commit**

```bash
git add client/src/pages/documents/DocumentDetailPage.tsx
git commit -m "feat(docs): use SectionPicker in document edit form"
```

---

## Phase 10: Merge Confirmation Dialog

Add dialog for confirming section merges when renaming creates conflicts.

### Task 10.1: Create SectionRenameDialog Component

**Files:**
- Create: `client/src/components/documents/SectionRenameDialog.tsx`

**Step 1: Create the rename dialog with merge option**

```typescript
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

  const parentPath = currentPath.split("/").slice(0, -1).join("/") || "/";
  const newPath = parentPath === "/" ? `/${newName}` : `${parentPath}/${newName}`;

  const handleRename = async (mergeIfExists = false) => {
    if (!newName.trim() || newName === currentName) {
      onOpenChange(false);
      return;
    }

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

      toast.success(`Renamed section and updated ${result.updated_count} documents`);
      onOpenChange(false);
      setShowMergeConfirm(false);
      setConflicts([]);
    } catch {
      toast.error("Failed to rename section");
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    setShowMergeConfirm(false);
    setConflicts([]);
    setNewName(currentName);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
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
              disabled={batchUpdatePaths.isPending || !newName.trim() || newName === currentName}
            >
              {batchUpdatePaths.isPending ? "Renaming..." : "Rename"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**Step 2: Verify the component compiles**

Run: `cd client && npm run tsc 2>&1 | grep -i "sectionrename\|error" | head -5`
Expected: No errors

**Step 3: Commit**

```bash
git add client/src/components/documents/SectionRenameDialog.tsx
git commit -m "feat(docs): add SectionRenameDialog with merge confirmation"
```

---

### Task 10.2: Add Context Menu to Sections

**Files:**
- Modify: `client/src/components/documents/DocumentSidebar.tsx`

**Step 1: Add context menu with rename option**

```typescript
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { SectionRenameDialog } from "./SectionRenameDialog";

// In the SectionItemComponent, add state for rename dialog:
const [renameOpen, setRenameOpen] = useState(false);

// Wrap section headers with ContextMenu:
{(item.type === "section" || item.type === "subsection") && (
  <>
    <ContextMenu>
      <ContextMenuTrigger asChild>
        {/* existing section header button */}
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onClick={() => setRenameOpen(true)}>
          Rename section
        </ContextMenuItem>
        {onCreateInSection && (
          <ContextMenuItem onClick={() => onCreateInSection(item.path)}>
            New document here
          </ContextMenuItem>
        )}
      </ContextMenuContent>
    </ContextMenu>

    <SectionRenameDialog
      open={renameOpen}
      onOpenChange={setRenameOpen}
      orgId={orgId}
      currentPath={item.path}
      currentName={item.label}
      documentCount={item.documentCount || 0}
    />
  </>
)}
```

**Step 2: Verify the changes compile**

Run: `cd client && npm run tsc 2>&1 | head -10`
Expected: No errors

**Step 3: Commit**

```bash
git add client/src/components/documents/DocumentSidebar.tsx
git commit -m "feat(docs): add context menu with rename option to sections"
```

---

## Phase 11: Main Sidebar Collapse Button

Add collapse functionality to the main navigation sidebar.

### Task 11.1: Add Sidebar Collapse State

**Files:**
- Create: `client/src/hooks/useSidebarCollapse.ts`
- Modify: `client/src/components/layout/Sidebar.tsx`
- Modify: `client/src/components/layout/AppLayout.tsx` (or wherever layout is defined)

**Step 1: Create collapse state hook with localStorage persistence**

```typescript
// client/src/hooks/useSidebarCollapse.ts
import { useState, useEffect } from "react";

const STORAGE_KEY = "sidebar-collapsed";

export function useSidebarCollapse() {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "true";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(isCollapsed));
  }, [isCollapsed]);

  const toggle = () => setIsCollapsed((prev) => !prev);

  return { isCollapsed, setIsCollapsed, toggle };
}
```

**Step 2: Update Sidebar component with collapse support**

In Sidebar.tsx, add:

```typescript
import { PanelLeftClose, PanelLeft } from "lucide-react";
import { useSidebarCollapse } from "@/hooks/useSidebarCollapse";

// Inside the Sidebar component:
const { isCollapsed, toggle } = useSidebarCollapse();

// Update the aside className:
<aside
  className={cn(
    "fixed lg:static inset-y-0 left-0 z-50 bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300 lg:translate-x-0",
    isMobileMenuOpen ? "translate-x-0" : "-translate-x-full",
    isCollapsed ? "lg:w-16" : "lg:w-64"
  )}
>

// Add collapse button in the logo section:
<div className="h-16 flex items-center justify-between px-4 border-b border-sidebar-border">
  <NavLink to="/" className={cn("flex items-center gap-2 text-sidebar-foreground", isCollapsed && "lg:hidden")}>
    <Logo type="rectangle" />
  </NavLink>
  {isCollapsed && (
    <NavLink to="/" className="hidden lg:flex items-center text-sidebar-foreground">
      <Logo type="icon" />
    </NavLink>
  )}
  <div className="flex items-center gap-1">
    <Button
      variant="ghost"
      size="icon"
      className="hidden lg:flex"
      onClick={toggle}
    >
      {isCollapsed ? (
        <PanelLeft className="h-5 w-5" />
      ) : (
        <PanelLeftClose className="h-5 w-5" />
      )}
    </Button>
    <Button
      variant="ghost"
      size="icon"
      className="lg:hidden"
      onClick={closeMobileMenu}
    >
      <X className="h-5 w-5" />
    </Button>
  </div>
</div>

// Update NavItem to show only icons when collapsed:
function NavItem({ name, href, icon: Icon, count, onClick, isCollapsed }: NavItemProps & { isCollapsed?: boolean }) {
  return (
    <NavLink
      to={href}
      onClick={onClick}
      title={isCollapsed ? name : undefined}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-md text-sm font-medium transition-colors",
          isCollapsed ? "justify-center px-2 py-2" : "justify-between px-3 py-2",
          isActive
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        )
      }
    >
      <div className={cn("flex items-center", isCollapsed ? "" : "gap-3")}>
        <Icon className="h-4 w-4" />
        {!isCollapsed && <span>{name}</span>}
      </div>
      {!isCollapsed && count !== undefined && (
        <Badge variant="secondary" className="tabular-nums">
          {count.toLocaleString()}
        </Badge>
      )}
    </NavLink>
  );
}
```

**Step 3: Verify the changes compile**

Run: `cd client && npm run tsc 2>&1 | head -10`
Expected: No errors

**Step 4: Commit**

```bash
git add client/src/hooks/useSidebarCollapse.ts client/src/components/layout/Sidebar.tsx
git commit -m "feat(layout): add collapsible main sidebar with icon-only mode"
```

---

## Summary

This plan implements the documents page redesign in 11 phases:

1. **Phase 1**: Section-based sidebar with L1/L2/flattened hierarchy
2. **Phase 2**: Flush visual style (no card wrappers)
3. **Phase 3**: Two-column document detail with ToC right rail
4. **Phase 4**: Borderless TipTap styling
5. **Phase 5**: Mobile responsive dropdowns
6. **Phase 6**: Backend batch path updates for section rename
7. **Phase 7**: Integration and polish
8. **Phase 8**: Drag-and-drop document reordering
9. **Phase 9**: Section picker cascading combobox
10. **Phase 10**: Merge confirmation dialog UI
11. **Phase 11**: Main sidebar collapse button

Each phase builds on the previous, creating a complete Notion/Starlight-inspired documentation experience.
