import { useState } from "react";
import { NavLink, useParams, useLocation } from "react-router-dom";
import {
  KeyRound,
  Server,
  MapPin,
  FileText,
  Layers,
  X,
  ChevronDown,
  Home,
  Globe,
  History,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { Logo } from "@/components/branding/Logo";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useSidebarData, type SidebarItemCount } from "@/hooks/useSidebar";
import { useGlobalSidebarData, type GlobalSidebarItemCount } from "@/hooks/useGlobalData";
import { useSidebarCollapse } from "@/hooks/useSidebarCollapse";

interface SidebarProps {
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (open: boolean) => void;
}

interface NavItemProps {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  count?: number;
  onClick?: () => void;
  isCollapsed?: boolean;
}

function NavItem({ name, href, icon: Icon, count, onClick, isCollapsed }: NavItemProps) {
  const linkContent = (
    <NavLink
      to={href}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          "flex items-center rounded-md text-sm font-medium transition-colors",
          isCollapsed ? "justify-center px-2 py-2" : "justify-between gap-3 px-3 py-2",
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

  if (isCollapsed) {
    return (
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          <div className="flex items-center gap-2">
            <span>{name}</span>
            {count !== undefined && (
              <Badge variant="secondary" className="tabular-nums text-xs">
                {count.toLocaleString()}
              </Badge>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    );
  }

  return linkContent;
}

interface NavSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  isCollapsed?: boolean;
}

function NavSection({ title, children, defaultOpen = true, isCollapsed }: NavSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  // When collapsed, always show content and hide title
  if (isCollapsed) {
    return (
      <div className="space-y-0.5">
        {children}
      </div>
    );
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-sidebar-foreground transition-colors">
        <span>{title}</span>
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 transition-transform duration-200",
            isOpen ? "rotate-0" : "-rotate-90"
          )}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-0.5 mt-1">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}

function SidebarSkeleton() {
  return (
    <div className="space-y-6">
      {/* Home */}
      <Skeleton className="h-9 w-full rounded-md" />

      {/* Core section */}
      <div className="space-y-2">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-9 w-full rounded-md" />
        <Skeleton className="h-9 w-full rounded-md" />
        <Skeleton className="h-9 w-full rounded-md" />
        <Skeleton className="h-9 w-full rounded-md" />
      </div>

      {/* Custom section */}
      <div className="space-y-2">
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-9 w-full rounded-md" />
        <Skeleton className="h-9 w-full rounded-md" />
      </div>
    </div>
  );
}

function CustomAssetTypeItem({
  item,
  orgId,
  onClick,
  isCollapsed,
}: {
  item: SidebarItemCount;
  orgId: string;
  onClick?: () => void;
  isCollapsed?: boolean;
}) {
  const linkContent = (
    <NavLink
      to={`/org/${orgId}/assets/${item.id}`}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          "flex items-center rounded-md text-sm font-medium transition-colors",
          isCollapsed ? "justify-center px-2 py-2" : "justify-between gap-3 px-3 py-2",
          isActive
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        )
      }
    >
      <div className={cn("flex items-center", isCollapsed ? "" : "gap-3")}>
        <Layers className="h-4 w-4" />
        {!isCollapsed && <span>{item.name}</span>}
      </div>
      {!isCollapsed && (
        <Badge variant="secondary" className="tabular-nums">
          {item.count.toLocaleString()}
        </Badge>
      )}
    </NavLink>
  );

  if (isCollapsed) {
    return (
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          <div className="flex items-center gap-2">
            <span>{item.name}</span>
            <Badge variant="secondary" className="tabular-nums text-xs">
              {item.count.toLocaleString()}
            </Badge>
          </div>
        </TooltipContent>
      </Tooltip>
    );
  }

  return linkContent;
}

function GlobalCustomAssetTypeItem({
  item,
  onClick,
  isCollapsed,
}: {
  item: GlobalSidebarItemCount;
  onClick?: () => void;
  isCollapsed?: boolean;
}) {
  const linkContent = (
    <NavLink
      to={`/global/assets/${item.id}`}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          "flex items-center rounded-md text-sm font-medium transition-colors",
          isCollapsed ? "justify-center px-2 py-2" : "justify-between gap-3 px-3 py-2",
          isActive
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        )
      }
    >
      <div className={cn("flex items-center", isCollapsed ? "" : "gap-3")}>
        <Layers className="h-4 w-4" />
        {!isCollapsed && <span>{item.name}</span>}
      </div>
      {!isCollapsed && (
        <Badge variant="secondary" className="tabular-nums">
          {item.count.toLocaleString()}
        </Badge>
      )}
    </NavLink>
  );

  if (isCollapsed) {
    return (
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          <div className="flex items-center gap-2">
            <span>{item.name}</span>
            <Badge variant="secondary" className="tabular-nums text-xs">
              {item.count.toLocaleString()}
            </Badge>
          </div>
        </TooltipContent>
      </Tooltip>
    );
  }

  return linkContent;
}

// Organization-scoped sidebar content
function OrgSidebarContent({
  orgId,
  closeMobileMenu,
  isCollapsed,
}: {
  orgId: string;
  closeMobileMenu: () => void;
  isCollapsed?: boolean;
}) {
  const { data: sidebarData, isLoading } = useSidebarData(orgId);

  // Calculate total configurations count from all types
  const configurationsCount = sidebarData?.configuration_types.reduce(
    (sum, type) => sum + type.count,
    0
  );

  if (isLoading) {
    return <SidebarSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Home Link */}
      <NavItem
        name="Home"
        href={`/org/${orgId}`}
        icon={Home}
        onClick={closeMobileMenu}
        isCollapsed={isCollapsed}
      />

      {/* Core Section */}
      <NavSection title="Core" isCollapsed={isCollapsed}>
        <NavItem
          name="Passwords"
          href={`/org/${orgId}/passwords`}
          icon={KeyRound}
          count={sidebarData?.passwords_count}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
        <NavItem
          name="Locations"
          href={`/org/${orgId}/locations`}
          icon={MapPin}
          count={sidebarData?.locations_count}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
        <NavItem
          name="Documents"
          href={`/org/${orgId}/documents`}
          icon={FileText}
          count={sidebarData?.documents_count}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
        <NavItem
          name="Configurations"
          href={`/org/${orgId}/configurations`}
          icon={Server}
          count={configurationsCount}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
        <NavItem
          name="Audit Trail"
          href={`/org/${orgId}/audit-trail`}
          icon={History}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
      </NavSection>

      {/* Custom Asset Types Section - always show */}
      <NavSection title="Custom Assets" isCollapsed={isCollapsed}>
        {sidebarData?.custom_asset_types.length === 0 ? (
          !isCollapsed && (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              No custom asset types
            </div>
          )
        ) : (
          sidebarData?.custom_asset_types.map((item) => (
            <CustomAssetTypeItem
              key={item.id}
              item={item}
              orgId={orgId}
              onClick={closeMobileMenu}
              isCollapsed={isCollapsed}
            />
          ))
        )}
      </NavSection>
    </div>
  );
}

// Global view sidebar content
function GlobalSidebarContent({
  closeMobileMenu,
  isCollapsed,
}: {
  closeMobileMenu: () => void;
  isCollapsed?: boolean;
}) {
  const { data: sidebarData, isLoading } = useGlobalSidebarData();

  // Calculate total configurations count from all types
  const configurationsCount = sidebarData?.configuration_types.reduce(
    (sum, type) => sum + type.count,
    0
  );

  if (isLoading) {
    return <SidebarSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Home Link */}
      <NavItem
        name="Global Home"
        href="/global"
        icon={Globe}
        onClick={closeMobileMenu}
        isCollapsed={isCollapsed}
      />

      {/* Core Section */}
      <NavSection title="Core" isCollapsed={isCollapsed}>
        <NavItem
          name="Passwords"
          href="/global/passwords"
          icon={KeyRound}
          count={sidebarData?.passwords_count}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
        <NavItem
          name="Locations"
          href="/global/locations"
          icon={MapPin}
          count={sidebarData?.locations_count}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
        <NavItem
          name="Documents"
          href="/global/documents"
          icon={FileText}
          count={sidebarData?.documents_count}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
        <NavItem
          name="Configurations"
          href="/global/configurations"
          icon={Server}
          count={configurationsCount}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
        <NavItem
          name="Audit Trail"
          href="/global/audit-trail"
          icon={History}
          onClick={closeMobileMenu}
          isCollapsed={isCollapsed}
        />
      </NavSection>

      {/* Custom Asset Types Section - always show */}
      <NavSection title="Custom Assets" isCollapsed={isCollapsed}>
        {sidebarData?.custom_asset_types.length === 0 ? (
          !isCollapsed && (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              No custom asset types
            </div>
          )
        ) : (
          sidebarData?.custom_asset_types.map((item) => (
            <GlobalCustomAssetTypeItem
              key={item.id}
              item={item}
              onClick={closeMobileMenu}
              isCollapsed={isCollapsed}
            />
          ))
        )}
      </NavSection>
    </div>
  );
}

export function Sidebar({
  isMobileMenuOpen,
  setIsMobileMenuOpen,
}: SidebarProps) {
  const { orgId } = useParams();
  const location = useLocation();
  const isGlobalView = location.pathname.startsWith("/global");
  const { isCollapsed, toggle } = useSidebarCollapse();

  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  // Show sidebar for org views or global views
  if (!orgId && !isGlobalView) {
    return null;
  }

  return (
    <>
      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={closeMobileMenu}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed lg:static inset-y-0 left-0 z-50 bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300 lg:translate-x-0",
          isMobileMenuOpen ? "translate-x-0 w-64" : "-translate-x-full w-64",
          // Desktop collapsed state
          isCollapsed ? "lg:w-16" : "lg:w-64"
        )}
      >
        {/* Logo */}
        <div className={cn(
          "h-16 flex items-center border-b border-sidebar-border",
          isCollapsed ? "justify-center px-2" : "justify-between px-4"
        )}>
          {!isCollapsed && (
            <NavLink to="/" className="flex items-center gap-2 text-sidebar-foreground">
              <Logo type="rectangle" />
            </NavLink>
          )}
          {/* Mobile close button */}
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={closeMobileMenu}
          >
            <X className="h-5 w-5" />
          </Button>
          {/* Desktop collapse toggle */}
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="hidden lg:flex h-8 w-8"
                onClick={toggle}
                aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                aria-expanded={!isCollapsed}
              >
                {isCollapsed ? (
                  <PanelLeft className="h-4 w-4" />
                ) : (
                  <PanelLeftClose className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={8}>
              {isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Navigation */}
        <nav className={cn(
          "flex-1 overflow-y-auto",
          isCollapsed ? "p-2" : "p-4"
        )}>
          {isGlobalView ? (
            <GlobalSidebarContent closeMobileMenu={closeMobileMenu} isCollapsed={isCollapsed} />
          ) : (
            <OrgSidebarContent orgId={orgId!} closeMobileMenu={closeMobileMenu} isCollapsed={isCollapsed} />
          )}
        </nav>
      </aside>
    </>
  );
}
