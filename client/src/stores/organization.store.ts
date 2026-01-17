import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { Organization } from "@/lib/api-client";

interface OrganizationState {
  currentOrg: Organization | null;
  organizations: Organization[];
  isValidating: boolean;
  setCurrentOrg: (org: Organization | null) => void;
  setOrganizations: (orgs: Organization[]) => void;
  clearOrganizations: () => void;
  clearCurrentOrg: () => void;
  setIsValidating: (value: boolean) => void;
}

export const useOrganizationStore = create<OrganizationState>()(
  persist(
    (set) => ({
      currentOrg: null,
      organizations: [],
      isValidating: false,

      setCurrentOrg: (org) => {
        set({ currentOrg: org });
      },

      setOrganizations: (orgs) => {
        set({ organizations: orgs });
      },

      clearOrganizations: () => {
        set({ currentOrg: null, organizations: [] });
      },

      clearCurrentOrg: () => {
        set({ currentOrg: null });
      },

      setIsValidating: (value) => {
        set({ isValidating: value });
      },
    }),
    {
      name: "bifrost-docs-organization",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        currentOrg: state.currentOrg,
      }),
    }
  )
);
