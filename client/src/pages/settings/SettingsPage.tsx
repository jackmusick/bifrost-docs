import { NavLink, Outlet, Navigate } from "react-router-dom";
import { User, Shield, Key, Server, CircleCheckBig, Layers, Users, Brain, FileArchive, KeyRound } from "lucide-react";
import { cn } from "@/lib/utils";
import { usePermissions } from "@/hooks/usePermissions";

const accountNav = [
  { label: "Profile", path: "/settings/profile", icon: User },
  { label: "Security", path: "/settings/security", icon: Shield },
];

const systemNav = [
  { label: "API Keys", path: "/settings/api-keys", icon: Key },
  { label: "Configuration Types", path: "/settings/configuration-types", icon: Server },
  { label: "Configuration Statuses", path: "/settings/configuration-statuses", icon: CircleCheckBig },
  { label: "Custom Asset Types", path: "/settings/custom-asset-types", icon: Layers },
];

const adminNav = [
  { label: "Users", path: "/settings/users", icon: Users },
  { label: "AI Configuration", path: "/settings/ai", icon: Brain },
  { label: "Data Exports", path: "/settings/exports", icon: FileArchive },
  { label: "Single Sign-On", path: "/settings/oauth", icon: KeyRound },
];

export function SettingsPage() {
  const { canAccessSettings, isAdmin } = usePermissions();

  // Redirect non-admins to organizations page
  if (!canAccessSettings) {
    return <Navigate to="/organizations" replace />;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Fixed Header */}
      <div className="shrink-0 pb-6">
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage your account, system configuration, and administration
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-8 flex-1 min-h-0">
        {/* Sidebar Navigation - Fixed */}
        <nav className="w-full md:w-56 shrink-0 space-y-6 md:overflow-y-auto">
          {/* Account Section */}
          <div>
            <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Account
            </h3>
            <ul className="space-y-1">
              {accountNav.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      )
                    }
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>

          {/* System Section */}
          <div>
            <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              System
            </h3>
            <ul className="space-y-1">
              {systemNav.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      )
                    }
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>

          {/* Administration Section (superuser only) */}
          {isAdmin && (
            <div>
              <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Administration
              </h3>
              <ul className="space-y-1">
                {adminNav.map((item) => (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                          isActive
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        )
                      }
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </nav>

        {/* Content Area - Scrollable */}
        <div className="flex-1 min-w-0 overflow-y-auto">
          <div className="max-w-3xl mx-auto pb-8">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
}
