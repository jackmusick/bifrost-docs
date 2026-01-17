import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { User, UserRole } from "@/lib/api-client";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  needsSetup: boolean | null; // null = not checked yet
  login: (user: User, accessToken: string, refreshToken: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
  setNeedsSetup: (needsSetup: boolean) => void;
  // Permission helpers
  isAdmin: () => boolean;
  isOwner: () => boolean;
  hasRole: (role: UserRole) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      needsSetup: null,

      login: (user, accessToken, refreshToken) => {
        // Also store in localStorage for axios interceptor
        localStorage.setItem("access_token", accessToken);
        localStorage.setItem("refresh_token", refreshToken);
        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
          needsSetup: false, // Once logged in, setup is complete
        });
      },

      logout: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      setUser: (user) => {
        set({ user });
      },

      setNeedsSetup: (needsSetup) => {
        set({ needsSetup });
      },

      // Permission helpers
      isAdmin: () => {
        const user = get().user;
        return user?.role === 'owner' || user?.role === 'administrator';
      },

      isOwner: () => {
        const user = get().user;
        return user?.role === 'owner';
      },

      hasRole: (role: UserRole) => {
        const user = get().user;
        return user?.role === role;
      },
    }),
    {
      name: "bifrost-docs-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
