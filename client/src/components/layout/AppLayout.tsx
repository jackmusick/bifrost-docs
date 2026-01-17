import { useState, useCallback, useMemo } from "react";
import { Outlet, useLocation, useParams } from "react-router-dom";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { CommandPalette } from "@/components/search/CommandPalette";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { useOrgValidation } from "@/hooks/useOrgValidation";
import { useTrackNavigation } from "@/hooks/useTrackNavigation";

export function AppLayout() {
  const location = useLocation();
  const params = useParams();

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInitialMessage, setChatInitialMessage] = useState<
    string | undefined
  >();

  // Detect current entity from URL
  const currentEntity = useMemo(() => {
    const path = location.pathname;

    // Match /org/:orgId/documents/:id or /global/documents/:id
    if (path.includes("/documents/") && params.id && params.id !== "new") {
      return {
        id: params.id,
        type: "document" as const,
      };
    }

    // Match /org/:orgId/custom-assets/:id or /global/custom-assets/:id
    if (path.includes("/custom-assets/") && params.id && params.id !== "new") {
      return {
        id: params.id,
        type: "custom_asset" as const,
      };
    }

    return null;
  }, [location.pathname, params.id]);

  // Validate that persisted organization still exists
  useOrgValidation();

  // Invalidate recent items query when navigating to entity detail pages
  useTrackNavigation();

  const handleOpenChatWithMessage = useCallback((message: string) => {
    setChatInitialMessage(message);
    setChatOpen(true);
  }, []);

  return (
    <div className="h-screen flex bg-background overflow-hidden">
      {/* Sidebar - full height with logo */}
      <Sidebar
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      {/* Main content area with header */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          onMobileMenuToggle={() => setIsMobileMenuOpen(true)}
          onSearchClick={() => setIsSearchOpen(true)}
          onChatClick={() => setChatOpen(true)}
        />
        <main className="flex-1 overflow-auto p-6 lg:p-8">
          <Outlet />
        </main>
      </div>

      {/* Global search command palette */}
      <CommandPalette
        open={isSearchOpen}
        onOpenChange={setIsSearchOpen}
        onOpenChat={handleOpenChatWithMessage}
      />

      {/* Chat window */}
      <ChatWindow
        open={chatOpen}
        onOpenChange={(open) => {
          setChatOpen(open);
          if (!open) setChatInitialMessage(undefined);
        }}
        initialMessage={chatInitialMessage}
        currentEntityId={currentEntity?.id}
        currentEntityType={currentEntity?.type}
      />
    </div>
  );
}
