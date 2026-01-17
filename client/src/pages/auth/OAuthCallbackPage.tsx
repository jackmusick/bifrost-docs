/**
 * OAuth Callback Page
 *
 * Handles the OAuth callback after user authenticates with an external provider.
 * Extracts code and state from URL params, exchanges for tokens, and redirects.
 */

import { useEffect, useState } from "react";
import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { authApi } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth.store";
import { Logo } from "@/components/branding/Logo";

type CallbackState = "processing" | "success" | "error";

export function OAuthCallbackPage() {
  const { provider } = useParams<{ provider: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuthStore();

  const [state, setState] = useState<CallbackState>("processing");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get code and state from URL
        const code = searchParams.get("code");
        const returnedState = searchParams.get("state");
        const errorParam = searchParams.get("error");
        const errorDescription = searchParams.get("error_description");

        // Check for OAuth error in URL
        if (errorParam) {
          throw new Error(errorDescription || errorParam);
        }

        if (!code) {
          throw new Error("No authorization code received");
        }

        if (!returnedState) {
          throw new Error("No state parameter received");
        }

        if (!provider) {
          throw new Error("No provider specified");
        }

        // Verify state matches what we stored
        const storedState = sessionStorage.getItem("oauth_state");
        if (storedState && storedState !== returnedState) {
          throw new Error("State mismatch - possible CSRF attack");
        }

        // Exchange code for tokens
        const response = await authApi.oauthCallback({
          code,
          state: returnedState,
          provider,
        });

        const loginData = response.data;

        if (loginData.mfa_required) {
          // MFA flow - for now just show a message
          throw new Error("MFA is required but not yet implemented in the UI");
        }

        if (!loginData.access_token || !loginData.refresh_token) {
          throw new Error("No tokens received from server");
        }

        // Store tokens and get user info
        localStorage.setItem("access_token", loginData.access_token);
        const userResponse = await authApi.me();

        // Complete login
        login(userResponse.data, loginData.access_token, loginData.refresh_token);

        // Clean up session storage
        sessionStorage.removeItem("oauth_state");
        sessionStorage.removeItem("oauth_provider");

        setState("success");
        toast.success("Welcome!");

        // Redirect to dashboard after brief delay
        setTimeout(() => {
          navigate("/", { replace: true });
        }, 1000);
      } catch (err) {
        console.error("OAuth callback error:", err);
        setState("error");
        setError(
          err instanceof Error ? err.message : "Authentication failed"
        );

        // Clean up session storage
        sessionStorage.removeItem("oauth_state");
        sessionStorage.removeItem("oauth_provider");
      }
    };

    handleCallback();
  }, [searchParams, provider, login, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <Logo type="square" className="h-12 w-12" />
          </div>
          <CardTitle className="text-2xl font-bold">
            {state === "processing" && "Signing you in..."}
            {state === "success" && "Welcome!"}
            {state === "error" && "Authentication Failed"}
          </CardTitle>
          <CardDescription>
            {state === "processing" && "Please wait while we complete authentication"}
            {state === "success" && "Redirecting you to the dashboard"}
            {state === "error" && "There was a problem signing you in"}
          </CardDescription>
        </CardHeader>

        <CardContent className="flex flex-col items-center">
          {state === "processing" && (
            <div className="py-8">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
          )}

          {state === "success" && (
            <div className="py-8">
              <CheckCircle2 className="h-12 w-12 text-green-500" />
            </div>
          )}

          {state === "error" && (
            <Alert variant="destructive" className="w-full">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>

        {state === "error" && (
          <CardFooter className="flex flex-col space-y-2">
            <Button asChild className="w-full">
              <Link to="/login">Try Again</Link>
            </Button>
            <p className="text-sm text-muted-foreground text-center">
              If this problem persists, please contact support.
            </p>
          </CardFooter>
        )}
      </Card>
    </div>
  );
}
