import { NavLink, useParams } from "react-router-dom";
import { Menu, Search, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { OrgSelector } from "./OrgSelector";
import { UserMenu } from "./UserMenu";
import { RecentDropdown } from "./RecentDropdown";
import { useAuthStore } from "@/stores/auth.store";

interface HeaderProps {
  onMobileMenuToggle: () => void;
  onSearchClick: () => void;
  onChatClick?: () => void;
}

const baseNavItems = [{ label: "Dashboard", path: "/" }];

export function Header({
  onMobileMenuToggle,
  onSearchClick,
  onChatClick,
}: HeaderProps) {
  const { orgId } = useParams();
  const isAdmin = useAuthStore((state) => state.isAdmin());

  // Build nav items list, conditionally including Organizations and Settings for admins
  const navItems = [
    ...baseNavItems,
    ...(isAdmin ? [
      { label: "Organizations", path: "/admin/organizations" },
      { label: "Settings", path: "/settings" },
    ] : []),
  ];

  return (
    <header className="h-16 border-b border-border bg-background flex items-center justify-between px-4 lg:px-6">
      <div className="flex items-center gap-4">
        {/* Only show mobile menu toggle when an org is selected (sidebar visible) */}
        {orgId && (
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={onMobileMenuToggle}
          >
            <Menu className="h-5 w-5" />
          </Button>
        )}
        <OrgSelector />

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-1 ml-4">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                cn(
                  "px-3 py-2 text-sm font-medium rounded-md transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="hidden sm:flex items-center gap-2 text-muted-foreground hover:text-foreground"
          onClick={onSearchClick}
        >
          <Search className="h-4 w-4" />
          <span>Search...</span>
          <kbd className="pointer-events-none ml-2 inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="sm:hidden"
          onClick={onSearchClick}
        >
          <Search className="h-5 w-5" />
        </Button>
        <RecentDropdown />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onChatClick?.()}
          className="h-9 w-9"
          title="Open Chat"
        >
          <MessageSquare className="h-5 w-5" />
        </Button>
        <UserMenu />
      </div>
    </header>
  );
}
