import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

/**
 * Invalidates the recent items query when navigating to entity detail pages.
 * This ensures the recent list stays up-to-date as views are logged server-side.
 */
export function useTrackNavigation() {
  const location = useLocation();
  const queryClient = useQueryClient();

  useEffect(() => {
    // Match entity detail page patterns
    const entityPatterns = [
      /\/org\/[^/]+\/passwords\/[^/]+$/,
      /\/org\/[^/]+\/configurations\/[^/]+$/,
      /\/org\/[^/]+\/locations\/[^/]+$/,
      /\/org\/[^/]+\/documents\/[^/]+$/,
      /\/org\/[^/]+\/assets\/[^/]+$/,
      /\/org\/[^/]+$/, // Org home page
    ];

    const isEntityDetailPage = entityPatterns.some((pattern) =>
      pattern.test(location.pathname)
    );

    if (isEntityDetailPage) {
      // Invalidate recent list after a short delay to allow the view to be logged
      const timeout = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["recent"] });
      }, 500);

      return () => clearTimeout(timeout);
    }
  }, [location.pathname, queryClient]);
}
