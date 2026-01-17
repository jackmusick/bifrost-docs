import { useEffect, useState, useCallback } from "react";
import { useLocation } from "react-router-dom";
import { useDebounce } from "@/hooks/useDebounce";
import { useSearch, groupSearchResults, type SearchResult } from "@/hooks/useSearch";
import { useOrganizationStore } from "@/stores/organization.store";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
} from "@/components/ui/command";
import { SearchResults } from "./SearchResults";
import { SearchPreview } from "./SearchPreview";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface CommandPaletteProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onOpenChat?: (query: string) => void;
}

export function CommandPalette({
  open,
  onOpenChange,
  onOpenChat,
}: CommandPaletteProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [includeDisabled, setIncludeDisabled] = useState(false);
  const [searchScope, setSearchScope] = useState<"org" | "global">("org");
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const debouncedQuery = useDebounce(query, 300);

  // Get current organization context
  const currentOrg = useOrganizationStore((state) => state.currentOrg);

  // Check if we're on global view
  const location = useLocation();
  const isGlobalView = location.pathname.startsWith("/global");

  // Use props if provided, otherwise use internal state
  const isOpen = open ?? internalOpen;
  const setIsOpen = onOpenChange ?? setInternalOpen;

  // Determine effective org ID for search
  // Force global scope when on global view, otherwise respect searchScope
  const effectiveOrgId = !isGlobalView && currentOrg && searchScope === "org" ? currentOrg.id : undefined;

  // Regular search
  const { data, isLoading, isFetching } = useSearch(debouncedQuery, {
    orgId: effectiveOrgId,
    showDisabled: includeDisabled,
  });

  // Group results by organization, then by entity type
  const groupedResults = data?.results ? groupSearchResults(data.results) : {};

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, [setIsOpen]);

  // Handle Shift+Enter to ask AI
  const handleAskAI = useCallback(() => {
    if (query.length >= 2 && onOpenChat) {
      handleClose();
      onOpenChat(query);
    }
  }, [query, handleClose, onOpenChat]);

  const handleHover = useCallback((result: SearchResult) => {
    setSelectedResult(result);
  }, []);

  // Handle query change - clear selected result when user types
  const handleQueryChange = useCallback((value: string) => {
    setQuery(value);
    // Clear selection when query changes to avoid showing stale preview
    setSelectedResult(null);
  }, []);

  // Listen for Cmd+K / Ctrl+K to open dialog
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsOpen(!isOpen);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [isOpen, setIsOpen]);

  // Listen for Tab to toggle search scope (only when on an org page, not global view)
  useEffect(() => {
    if (!isOpen || isGlobalView || !currentOrg) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Tab") {
        e.preventDefault();
        setSearchScope((prev) => (prev === "org" ? "global" : "org"));
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isGlobalView, currentOrg]);

  // Listen for Shift+Enter to open chat with query
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter" && e.shiftKey) {
        e.preventDefault();
        handleAskAI();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleAskAI]);

  // Reset when dialog closes
  useEffect(() => {
    if (!isOpen) {
      // Delay reset to avoid flash during close animation
      const timer = setTimeout(() => {
        setQuery("");
        setSearchScope("org");
        setSelectedResult(null);
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const showLoading = isLoading || (isFetching && debouncedQuery.length >= 2);
  const showEmpty =
    debouncedQuery.length >= 2 &&
    !showLoading &&
    Object.keys(groupedResults).length === 0;
  const showResults =
    debouncedQuery.length >= 2 &&
    Object.keys(groupedResults).length > 0;
  const showHint = debouncedQuery.length < 2;

  return (
    <CommandDialog
      open={isOpen}
      onOpenChange={setIsOpen}
      title="Search"
      description="Search for passwords, configurations, locations, documents, and assets"
      showCloseButton={false}
    >
      <CommandInput
        placeholder={
          !isGlobalView && currentOrg && searchScope === "org"
            ? `Search in ${currentOrg.name}...`
            : "Search all organizations..."
        }
        value={query}
        onValueChange={handleQueryChange}
      />

      {/* Main content area with vertical split layout */}
      <div className="flex flex-col h-[440px] overflow-hidden">
        {/* Top section: Search results (40%) */}
        <div
          className={cn(
            "flex flex-col overflow-hidden border-b transition-all duration-200 ease-out",
            showResults ? "h-[40%]" : "h-full"
          )}
        >
          <CommandList className="flex-1 max-h-full">
            {showHint && (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Type at least 2 characters to search
              </div>
            )}

            {showLoading && (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">
                  Searching...
                </span>
              </div>
            )}

            {showEmpty && (
              <CommandEmpty>
                No results found for "{debouncedQuery}"
              </CommandEmpty>
            )}

            {showResults && (
              <SearchResults
                groupedResults={groupedResults}
                onSelect={handleClose}
                onHover={handleHover}
                highlightQuery={debouncedQuery}
              />
            )}
          </CommandList>
        </div>

        {/* Bottom section: Preview pane (60%) - only visible when we have results */}
        {showResults && (
          <div className="flex-1 overflow-hidden bg-muted/30">
            <SearchPreview
              entityType={selectedResult?.entity_type ?? null}
              entityId={selectedResult?.entity_id ?? null}
              organizationId={selectedResult?.organization_id ?? null}
              highlightQuery={debouncedQuery}
            />
          </div>
        )}
      </div>

      {/* Footer with keyboard hints */}
      <div className="flex items-center justify-between border-t px-3 py-2">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>
            <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium">
              <span className="text-xs">↑↓</span>
            </kbd>
            <span className="ml-1">Navigate</span>
          </span>
          <span>
            <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium">
              ↵
            </kbd>
            <span className="ml-1">Select</span>
          </span>
          {onOpenChat && (
            <span>
              <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium">
                <span className="text-xs">Shift</span>↵
              </kbd>
              <span className="ml-1">Ask AI</span>
            </span>
          )}
          {!isGlobalView && currentOrg && (
            <span>
              <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium">
                Tab
              </kbd>
              <span className="ml-1">
                {searchScope === "org" ? "All orgs" : currentOrg.name}
              </span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Switch
              id="include-disabled"
              checked={includeDisabled}
              onCheckedChange={setIncludeDisabled}
              className="data-[state=checked]:bg-primary"
            />
            <Label
              htmlFor="include-disabled"
              className="text-xs cursor-pointer select-none"
            >
              Include Disabled
            </Label>
          </div>
          <span className="text-xs text-muted-foreground">
            <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium">
              esc
            </kbd>
            <span className="ml-1">Close</span>
          </span>
        </div>
      </div>
    </CommandDialog>
  );
}
