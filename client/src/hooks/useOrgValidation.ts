import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useOrganizationStore } from "@/stores/organization.store";
import { useOrganizations } from "./useOrganizations";

/**
 * Hook to validate that the persisted current organization still exists.
 *
 * This hook:
 * 1. Fetches fresh org list on app mount
 * 2. Checks if persisted currentOrg exists in the list
 * 3. If not found:
 *    - Clears current org from store (handled by useOrganizations)
 *    - Redirects to /global if currently on an org route
 *    - Shows a toast notification
 *
 * The validation logic itself is in useOrganizations hook,
 * this hook handles the user-facing consequences.
 */
export function useOrgValidation() {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentOrg, isValidating, setIsValidating } = useOrganizationStore();

  // Track the previous currentOrg to detect when it gets cleared
  const previousOrgIdRef = useRef<string | null>(currentOrg?.id || null);
  const hasShownToastRef = useRef(false);

  // Fetch organizations - this hook includes validation logic
  const { data: organizations, isLoading } = useOrganizations();

  useEffect(() => {
    // Skip if still loading
    if (isLoading) {
      setIsValidating(true);
      return;
    }

    // Mark validation as complete
    setIsValidating(false);

    const currentOrgId = currentOrg?.id || null;
    const previousOrgId = previousOrgIdRef.current;

    // If we had an org before but now it's cleared, it was invalid
    if (previousOrgId && !currentOrgId && organizations && !hasShownToastRef.current) {
      // Check if we're on an org route
      const isOnOrgRoute = location.pathname.startsWith("/org/");

      // Show toast notification
      toast.error("The selected organization is no longer available", {
        description: isOnOrgRoute ? "You've been redirected to the global view." : undefined,
        duration: 5000,
      });

      // Mark that we've shown the toast to prevent duplicates
      hasShownToastRef.current = true;

      // Redirect to global if on org route
      if (isOnOrgRoute) {
        navigate("/global", { replace: true });
      }
    }

    // Update the ref for next render
    previousOrgIdRef.current = currentOrgId;
  }, [
    isLoading,
    currentOrg,
    organizations,
    location.pathname,
    navigate,
    setIsValidating,
  ]);

  return {
    isValidating: isLoading || isValidating,
    organizations,
  };
}
