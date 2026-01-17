import { useNavigate } from "react-router-dom";
import { LogOut, Settings, User } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuthStore } from "@/stores/auth.store";
import { useOrganizationStore } from "@/stores/organization.store";
import { authApi, type UserRole } from "@/lib/api-client";

function getRoleBadgeVariant(role: UserRole): "default" | "secondary" | "destructive" | "outline" {
  switch (role) {
    case "owner":
      return "destructive";
    case "administrator":
      return "default";
    case "contributor":
      return "secondary";
    case "reader":
      return "outline";
    default:
      return "default";
  }
}

function formatRoleName(role: UserRole): string {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

export function UserMenu() {
  const navigate = useNavigate();
  const { user, logout, isAdmin } = useAuthStore();
  const { clearOrganizations } = useOrganizationStore();

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore logout errors - we'll clear local state anyway
    }
    logout();
    clearOrganizations();
    toast.success("Logged out successfully");
    navigate("/login");
  };

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() || "??";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="relative h-9 w-9 rounded-full">
          <Avatar className="h-9 w-9">
            <AvatarFallback className="bg-primary text-primary-foreground">
              {initials}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-2">
            <p className="text-sm font-medium leading-none">{user?.name}</p>
            <p className="text-xs leading-none text-muted-foreground">
              {user?.email}
            </p>
            {user?.role && (
              <Badge variant={getRoleBadgeVariant(user.role)} className="w-fit">
                {formatRoleName(user.role)}
              </Badge>
            )}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate("/settings/profile")}>
          <User className="mr-2 h-4 w-4" />
          Profile
        </DropdownMenuItem>
        {isAdmin() && (
          <DropdownMenuItem onClick={() => navigate("/settings")}>
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout} className="text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
