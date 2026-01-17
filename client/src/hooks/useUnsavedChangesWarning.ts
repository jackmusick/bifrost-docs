import { useEffect } from "react";

/**
 * Warns the user before closing/refreshing the browser tab with unsaved changes.
 * Uses the beforeunload event to prompt the user.
 *
 * Note: In-app navigation blocking requires a data router (createBrowserRouter).
 * This hook only handles browser close/refresh.
 */
export function useUnsavedChangesWarning(
  isDirty: boolean,
  message?: string
): void {
  const defaultMessage =
    "You have unsaved changes. Are you sure you want to leave?";

  // Block browser refresh/close with beforeunload event
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        // Modern browsers ignore custom messages, but returnValue is still required
        e.returnValue = message || defaultMessage;
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty, message]);
}
