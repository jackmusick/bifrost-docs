import { useState, useMemo } from "react";
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
  const { sections, isLoading } = useDocumentSections(orgId ?? "");
  const [tocOpen, setTocOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  const handleDocumentClick = (docId: string) => {
    navigate(`/org/${orgId}/documents/${docId}`);
    setNavOpen(false);
  };

  // Flatten sections for mobile dropdown (memoized to avoid recalculation on every render)
  const flattenedDocs = useMemo(() => {
    if (isLoading) return [];
    const docs: { id: string; name: string; path: string }[] = [];
    function collectDocs(items: SectionItem[]) {
      for (const item of items) {
        if (item.type === "document" && item.document) {
          docs.push({
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
    collectDocs(sections);
    return docs;
  }, [sections, isLoading]);

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
