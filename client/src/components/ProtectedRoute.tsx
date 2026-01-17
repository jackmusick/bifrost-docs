import { useState, useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/stores/auth.store";
import { authApi } from "@/lib/api-client";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, needsSetup, setNeedsSetup } = useAuthStore();
  const location = useLocation();
  const [isCheckingSetup, setIsCheckingSetup] = useState(needsSetup === null);

  // Check setup status on mount if not already known
  useEffect(() => {
    async function checkSetup() {
      if (needsSetup !== null) {
        setIsCheckingSetup(false);
        return;
      }

      try {
        const response = await authApi.setupStatus();
        setNeedsSetup(response.data.needs_setup);
      } catch {
        // If endpoint fails, assume setup is not needed
        setNeedsSetup(false);
      } finally {
        setIsCheckingSetup(false);
      }
    }
    checkSetup();
  }, [needsSetup, setNeedsSetup]);

  // Show loading while checking setup status
  if (isCheckingSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Redirect to setup if needed
  if (needsSetup) {
    return <Navigate to="/setup" replace />;
  }

  if (!isAuthenticated) {
    // Redirect to login page, preserving the attempted location
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
