import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useEffect, useMemo } from "react";
import type { VisibilityState, ColumnOrderState } from "@tanstack/react-table";
import api from "@/lib/api-client";

// =============================================================================
// Types
// =============================================================================

export interface ColumnPreferences {
  visible: string[];
  order: string[];
  widths: Record<string, number>;
}

export interface UserPreferences {
  columns: ColumnPreferences;
}

export interface PreferencesResponse {
  entity_type: string;
  preferences: UserPreferences;
}

// =============================================================================
// Conversion Utilities
// =============================================================================

/**
 * Convert array of visible column IDs to TanStack Table VisibilityState.
 * If no explicit visibility is set, returns empty object (all visible).
 */
export function toVisibilityState(
  visible: string[] | undefined,
  allColumnIds: string[]
): VisibilityState {
  if (!visible || visible.length === 0) {
    return {}; // Empty object means all columns visible
  }

  const visibilityState: VisibilityState = {};
  for (const columnId of allColumnIds) {
    visibilityState[columnId] = visible.includes(columnId);
  }
  return visibilityState;
}

/**
 * Convert TanStack Table VisibilityState to array of visible column IDs.
 */
export function fromVisibilityState(
  visibility: VisibilityState,
  allColumnIds: string[]
): string[] {
  // If visibility is empty, all columns are visible
  if (Object.keys(visibility).length === 0) {
    return allColumnIds;
  }

  return allColumnIds.filter((id) => visibility[id] !== false);
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for managing column preferences with server-side persistence.
 * Provides debounced saves (300ms) to avoid excessive API calls.
 *
 * @param entityType - The entity type key (e.g., "passwords", "configurations")
 * @param allColumnIds - All column IDs in the table (used for visibility conversion)
 * @param defaultPreferences - Default preferences to use if none exist on server
 */
export function useColumnPreferences(
  entityType: string,
  allColumnIds: string[],
  defaultPreferences?: Partial<ColumnPreferences>
) {
  const queryClient = useQueryClient();
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingPreferencesRef = useRef<ColumnPreferences | null>(null);

  // Fetch preferences from server
  const { data, isLoading, error } = useQuery({
    queryKey: ["preferences", entityType],
    queryFn: async () => {
      const response = await api.get<PreferencesResponse>(
        `/api/preferences/${entityType}`
      );
      return response.data;
    },
    // Don't fail if preferences don't exist yet
    retry: false,
  });

  // Mutation for saving preferences
  const saveMutation = useMutation({
    mutationFn: async (preferences: UserPreferences) => {
      const response = await api.put<PreferencesResponse>(
        `/api/preferences/${entityType}`,
        { preferences }
      );
      return response.data;
    },
    onSuccess: (newData) => {
      // Update the cache with the saved data
      queryClient.setQueryData(["preferences", entityType], newData);
    },
  });

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
        // Save any pending preferences immediately on unmount
        if (pendingPreferencesRef.current) {
          saveMutation.mutate({ columns: pendingPreferencesRef.current });
        }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Get current preferences, falling back to defaults
  const preferences = useMemo(
    () =>
      data?.preferences?.columns ?? {
        visible: defaultPreferences?.visible ?? [],
        order: defaultPreferences?.order ?? [],
        widths: defaultPreferences?.widths ?? {},
      },
    [data?.preferences?.columns, defaultPreferences]
  );

  // Debounced save function
  const savePreferences = useCallback(
    (updates: Partial<ColumnPreferences>) => {
      // Merge updates with current preferences
      const newPreferences: ColumnPreferences = {
        visible: updates.visible ?? preferences.visible,
        order: updates.order ?? preferences.order,
        widths: updates.widths ?? preferences.widths,
      };

      // Store pending preferences
      pendingPreferencesRef.current = newPreferences;

      // Optimistically update the cache
      queryClient.setQueryData(["preferences", entityType], {
        entity_type: entityType,
        preferences: { columns: newPreferences },
      });

      // Clear existing timeout
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }

      // Set new debounced save
      saveTimeoutRef.current = setTimeout(() => {
        pendingPreferencesRef.current = null;
        saveMutation.mutate({ columns: newPreferences });
      }, 300);
    },
    [preferences, entityType, queryClient, saveMutation]
  );

  // Helper to update visible columns
  const setVisibleColumns = useCallback(
    (visible: string[]) => {
      savePreferences({ visible });
    },
    [savePreferences]
  );

  // Helper to update column order
  const setColumnOrder = useCallback(
    (order: string[]) => {
      savePreferences({ order });
    },
    [savePreferences]
  );

  // Helper to update column widths
  const setColumnWidths = useCallback(
    (widths: Record<string, number>) => {
      savePreferences({ widths });
    },
    [savePreferences]
  );

  // Convert to TanStack Table VisibilityState format
  const columnVisibility = useMemo(
    () => toVisibilityState(preferences.visible, allColumnIds),
    [preferences.visible, allColumnIds]
  );

  // Column order in TanStack format (already compatible)
  const columnOrder: ColumnOrderState = useMemo(
    () => preferences.order,
    [preferences.order]
  );

  // Handler for TanStack Table onColumnVisibilityChange
  const onColumnVisibilityChange = useCallback(
    (visibility: VisibilityState) => {
      const visibleColumns = fromVisibilityState(visibility, allColumnIds);
      setVisibleColumns(visibleColumns);
    },
    [allColumnIds, setVisibleColumns]
  );

  // Handler for TanStack Table onColumnOrderChange
  const onColumnOrderChange = useCallback(
    (order: ColumnOrderState) => {
      setColumnOrder(order);
    },
    [setColumnOrder]
  );

  return {
    // Raw preferences
    preferences,
    isLoading,
    error,
    isSaving: saveMutation.isPending,

    // Raw setters (array-based)
    savePreferences,
    setVisibleColumns,
    setColumnOrder,
    setColumnWidths,

    // TanStack Table compatible props (ready to spread into DataTable)
    columnVisibility,
    columnOrder,
    onColumnVisibilityChange,
    onColumnOrderChange,
  };
}
