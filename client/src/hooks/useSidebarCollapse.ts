import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "sidebar-collapsed";

export function useSidebarCollapse() {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored === "true";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(isCollapsed));
    } catch {
      // Silently fail - state still works in memory
    }
  }, [isCollapsed]);

  const toggle = useCallback(() => setIsCollapsed((prev) => !prev), []);

  return { isCollapsed, setIsCollapsed, toggle };
}
