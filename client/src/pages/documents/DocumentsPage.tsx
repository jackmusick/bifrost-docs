import { useState, useRef, useCallback, useEffect } from "react";
import { useParams, useNavigate, Outlet, useMatch } from "react-router-dom";
import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { DocumentSidebar } from "@/components/documents/DocumentSidebar";
import { usePermissions } from "@/hooks/usePermissions";

const SIDEBAR_MIN_WIDTH = 180;
const SIDEBAR_MAX_WIDTH = 480;
const SIDEBAR_DEFAULT_WIDTH = 256;
const SIDEBAR_WIDTH_KEY = "documents-sidebar-width";

function useSidebarWidth() {
  const [width, setWidth] = useState(() => {
    if (typeof window === "undefined") return SIDEBAR_DEFAULT_WIDTH;
    const stored = localStorage.getItem(SIDEBAR_WIDTH_KEY);
    const parsed = stored ? parseInt(stored, 10) : SIDEBAR_DEFAULT_WIDTH;
    return Math.max(SIDEBAR_MIN_WIDTH, Math.min(SIDEBAR_MAX_WIDTH, parsed));
  });

  useEffect(() => {
    localStorage.setItem(SIDEBAR_WIDTH_KEY, String(width));
  }, [width]);

  return [width, setWidth] as const;
}

export function DocumentsPage() {
  const { orgId, id } = useParams<{ orgId: string; id?: string }>();
  const navigate = useNavigate();
  const { canEdit } = usePermissions();
  const [sidebarWidth, setSidebarWidth] = useSidebarWidth();
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);

  // Check if we're on the documents index (no document selected)
  const isIndex = useMatch("/org/:orgId/documents");

  const handleCreateNew = (path?: string) => {
    const params = new URLSearchParams();
    if (path) {
      params.set("path", path);
    }
    const queryString = params.toString();
    navigate(`/org/${orgId}/documents/new${queryString ? `?${queryString}` : ""}`);
  };

  // Resize handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isResizing || !sidebarRef.current) return;
      const sidebarRect = sidebarRef.current.getBoundingClientRect();
      const newWidth = e.clientX - sidebarRect.left;
      setSidebarWidth(Math.max(SIDEBAR_MIN_WIDTH, Math.min(SIDEBAR_MAX_WIDTH, newWidth)));
    },
    [isResizing, setSidebarWidth]
  );

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    }
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  // Calculate height: viewport minus header (4rem), accounts for AppLayout padding via negative margins
  return (
    <div className="flex h-[calc(100vh-4rem)] -m-6 lg:-m-8">
      {/* Document Sidebar - resizable */}
      <aside
        ref={sidebarRef}
        style={{ width: sidebarWidth }}
        className="shrink-0 border-r border-border hidden md:flex flex-col overflow-hidden relative"
      >
        <DocumentSidebar
          selectedDocumentId={id}
          onCreateDocument={handleCreateNew}
        />
        {/* Resize handle */}
        <div
          onMouseDown={handleMouseDown}
          className={cn(
            "absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-primary/20 transition-colors",
            isResizing && "bg-primary/30"
          )}
        />
      </aside>

      {/* Main Content - independent scroll */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {isIndex ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <p className="text-muted-foreground mb-4">
              Select a document from the sidebar to view it
            </p>
            {canEdit && (
              <Button onClick={() => handleCreateNew()}>
                <Plus className="mr-2 h-4 w-4" />
                New Document
              </Button>
            )}
          </div>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
}
