import { useAuthStore } from "@/stores/auth.store";
import type { UserRole } from "@/lib/api-client";

export interface Permissions {
  /** The user's current role */
  role: UserRole | undefined;
  /** Whether the user can edit/create/delete data (owner, administrator, contributor) */
  canEdit: boolean;
  /** Whether the user can access settings pages (owner, administrator) */
  canAccessSettings: boolean;
  /** Whether the user can manage owners and perform ownership transfer (owner only) */
  canManageOwners: boolean;
  /** Whether the user is a reader (view-only access) */
  isReader: boolean;
  /** Whether the user is a contributor */
  isContributor: boolean;
  /** Whether the user is an admin (owner or administrator) */
  isAdmin: boolean;
  /** Whether the user is the owner */
  isOwner: boolean;
}

/**
 * Hook to get the current user's permissions.
 * Centralizes permission logic for consistent role-based access control across the app.
 */
export function usePermissions(): Permissions {
  const user = useAuthStore((state) => state.user);
  const role = user?.role;

  return {
    role,
    canEdit: role === "owner" || role === "administrator" || role === "contributor",
    canAccessSettings: role === "owner" || role === "administrator",
    canManageOwners: role === "owner",
    isReader: role === "reader",
    isContributor: role === "contributor",
    isAdmin: role === "owner" || role === "administrator",
    isOwner: role === "owner",
  };
}
