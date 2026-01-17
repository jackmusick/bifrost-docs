import { useMemo } from "react";
import { useFolders, useDocuments } from "./useDocuments";
import type { Document, FolderCount } from "./useDocuments";

// =============================================================================
// Types
// =============================================================================

export type SectionItemType = "section" | "subsection" | "flattened-group" | "document";

export interface SectionItem {
  type: SectionItemType;
  id: string;
  label: string;
  path: string;
  depth: number;
  documentCount?: number;
  document?: Document;
  children?: SectionItem[];
}

export interface SectionTree {
  sections: SectionItem[];
  isLoading: boolean;
}

// =============================================================================
// Section Tree Builder
// =============================================================================

/**
 * Builds a section tree from folder counts and documents.
 *
 * Structure:
 * - L1: Top-level paths become sections (bold)
 * - L2: Second-level paths become subsections (indented)
 * - L3+: Deeper paths are flattened with " · " separator as group labels
 * - Documents appear under their parent section/group
 * - Root documents go into a "General" section
 *
 * Example:
 * ```
 * Archive                              ← L1 Section (depth: 0)
 *   Tech                               ← L2 Subsection (depth: 1)
 *     Overview doc                     ← Document at depth 1
 *     Microsoft · Office 365 · Teams   ← L3+ flattened (depth: 2)
 *       Setting up Teams channels      ← Document at depth 2
 * ```
 */
export function buildSectionTree(
  folders: FolderCount[],
  documents: Document[]
): SectionItem[] {
  const sections: SectionItem[] = [];

  // Build a map of path -> folder count for quick lookup
  const folderCountMap = new Map(folders.map((f) => [f.path, f.count]));

  // Group documents by their path
  const documentsByPath = new Map<string, Document[]>();
  for (const doc of documents) {
    const path = doc.path || "/";
    const existing = documentsByPath.get(path) || [];
    existing.push(doc);
    documentsByPath.set(path, existing);
  }

  // Get all unique paths (from both folders and documents)
  const allPaths = new Set<string>();
  for (const folder of folders) {
    allPaths.add(folder.path);
  }
  for (const doc of documents) {
    if (doc.path) {
      allPaths.add(doc.path);
    }
  }

  // Build intermediate tree structure to organize paths hierarchically
  interface TreeNode {
    name: string;
    path: string;
    count: number;
    children: Map<string, TreeNode>;
    documents: Document[];
  }

  const root: Map<string, TreeNode> = new Map();

  // Insert all paths into the tree
  for (const folderPath of allPaths) {
    const parts = folderPath.split("/").filter(Boolean);
    let currentLevel = root;
    let currentPath = "";

    for (const part of parts) {
      currentPath = currentPath ? `${currentPath}/${part}` : `/${part}`;
      let existing = currentLevel.get(part);

      if (!existing) {
        existing = {
          name: part,
          path: currentPath,
          count: folderCountMap.get(currentPath) ?? 0,
          children: new Map(),
          documents: [],
        };
        currentLevel.set(part, existing);
      }

      currentLevel = existing.children;
    }
  }

  // Attach documents to their respective nodes
  const attachDocuments = (node: TreeNode, path: string) => {
    const docs = documentsByPath.get(path);
    if (docs) {
      node.documents = docs;
    }
    for (const child of node.children.values()) {
      attachDocuments(child, child.path);
    }
  };

  for (const node of root.values()) {
    attachDocuments(node, node.path);
  }

  // Convert tree node to section items with flattening logic for L3+
  const convertToSectionItems = (
    node: TreeNode,
    depth: number,
    flattenedPrefix: string[] = []
  ): SectionItem[] => {
    const items: SectionItem[] = [];

    // Determine the type based on depth
    let type: SectionItemType;
    if (depth === 0) {
      type = "section";
    } else if (depth === 1) {
      type = "subsection";
    } else {
      type = "flattened-group";
    }

    // For L3+ paths, we flatten the label with " · " separator
    const labelParts = depth >= 2 ? [...flattenedPrefix, node.name] : [node.name];
    const label = labelParts.join(" · ");

    // Create the section item
    const sectionItem: SectionItem = {
      type,
      id: `section-${node.path}`,
      label,
      path: node.path,
      depth: Math.min(depth, 2), // Cap display depth at 2 for visual consistency
      documentCount: node.count,
      children: [],
    };

    // Add documents as children
    for (const doc of node.documents) {
      sectionItem.children!.push({
        type: "document",
        id: doc.id,
        label: doc.name,
        path: doc.path,
        depth: sectionItem.depth,
        document: doc,
      });
    }

    // Process child nodes
    if (depth < 2) {
      // L1 and L2: children become separate items
      for (const child of node.children.values()) {
        const childItems = convertToSectionItems(child, depth + 1);
        sectionItem.children!.push(...childItems);
      }
    } else {
      // L3+: flatten children with " · " separator
      for (const child of node.children.values()) {
        const childItems = convertToSectionItems(child, depth + 1, labelParts);
        // At L3+, each child becomes a separate flattened-group item
        items.push(...childItems);
      }
    }

    items.unshift(sectionItem);
    return items;
  };

  // Process all top-level sections
  for (const node of root.values()) {
    const sectionItems = convertToSectionItems(node, 0);
    sections.push(...sectionItems);
  }

  // Handle root-level documents (documents with path "/" or "")
  const rootDocs = documentsByPath.get("/") || [];
  const emptyPathDocs = documentsByPath.get("") || [];
  const allRootDocs = [...rootDocs, ...emptyPathDocs];

  if (allRootDocs.length > 0) {
    const generalSection: SectionItem = {
      type: "section",
      id: "section-general",
      label: "General",
      path: "/",
      depth: 0,
      documentCount: allRootDocs.length,
      children: allRootDocs.map((doc) => ({
        type: "document" as const,
        id: doc.id,
        label: doc.name,
        path: doc.path,
        depth: 0,
        document: doc,
      })),
    };
    // Add General section at the beginning
    sections.unshift(generalSection);
  }

  return sections;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook that builds a section tree from folders and documents.
 *
 * @param orgId - The organization ID to fetch documents for
 * @returns SectionTree with sections array and loading state
 */
export function useDocumentSections(orgId: string): SectionTree {
  const { data: foldersData, isLoading: foldersLoading } = useFolders(orgId);
  const { data: documentsData, isLoading: documentsLoading } = useDocuments(orgId, {
    pagination: { limit: 1000 }, // Fetch all documents for section tree
  });

  const isLoading = foldersLoading || documentsLoading;

  const sections = useMemo(() => {
    if (!foldersData || !documentsData) {
      return [];
    }

    return buildSectionTree(foldersData.folders, documentsData.items);
  }, [foldersData, documentsData]);

  return {
    sections,
    isLoading,
  };
}
