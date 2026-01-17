import { useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, Fingerprint, KeyRound, ExternalLink } from "lucide-react";
import { Logo } from "@/components/branding/Logo";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { authApi, type OAuthProviderInfo } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth.store";
import {
  supportsPasskeys,
  authenticateWithPasskey,
} from "@/lib/passkeys";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

// OAuth provider icon components
function MicrosoftIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 21 21" fill="none">
      <rect x="1" y="1" width="9" height="9" fill="#F25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
      <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

function getProviderIcon(provider: string) {
  switch (provider) {
    case "microsoft":
      return <MicrosoftIcon />;
    case "google":
      return <GoogleIcon />;
    default:
      return <KeyRound className="w-5 h-5" />;
  }
}

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isPasskeyLoading, setIsPasskeyLoading] = useState(false);
  const [isOAuthLoading, setIsOAuthLoading] = useState<string | null>(null);
  const [oauthProviders, setOAuthProviders] = useState<OAuthProviderInfo[]>([]);
  const [passkeysSupported] = useState(() => supportsPasskeys());
  const hasAttemptedAutoPasskey = useRef(false);

  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  // Complete login after successful authentication
  const completeLogin = async (accessToken: string, refreshToken: string) => {
    localStorage.setItem("access_token", accessToken);
    const userResponse = await authApi.me();
    login(userResponse.data, accessToken, refreshToken);
    toast.success("Welcome back!");
    navigate("/");
  };

  // Handle passkey authentication
  const handlePasskeyLogin = async () => {
    setIsPasskeyLoading(true);
    try {
      const result = await authenticateWithPasskey();
      await completeLogin(result.access_token, result.refresh_token);
    } catch (error) {
      // Only show error if it's not a user cancellation
      if (
        error instanceof Error &&
        !error.message.includes("cancelled") &&
        !error.message.includes("aborted")
      ) {
        toast.error(error.message || "Passkey authentication failed");
      }
    } finally {
      setIsPasskeyLoading(false);
    }
  };

  // Load OAuth providers
  useEffect(() => {
    authApi
      .getOAuthProviders()
      .then((response) => {
        setOAuthProviders(response.data.providers);
      })
      .catch(() => {
        // OAuth not configured, that's fine
      });
  }, []);

  // Auto-trigger passkey authentication on mount (conditional UI)
  useEffect(() => {
    if (!passkeysSupported || hasAttemptedAutoPasskey.current) {
      return;
    }

    hasAttemptedAutoPasskey.current = true;

    // Small delay to let the page render first
    const timer = setTimeout(() => {
      handlePasskeyLogin();
    }, 500);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [passkeysSupported]);

  // Handle OAuth login
  const handleOAuthLogin = async (provider: string) => {
    setIsOAuthLoading(provider);
    try {
      // Store provider for callback
      sessionStorage.setItem("oauth_provider", provider);

      // Build callback URL
      const callbackUrl = `${window.location.origin}/auth/callback/${provider}`;

      // Get authorization URL
      const response = await authApi.initOAuth(provider, callbackUrl);
      const { authorization_url, state } = response.data;

      // Store state for verification
      sessionStorage.setItem("oauth_state", state);

      // Redirect to OAuth provider
      window.location.href = authorization_url;
    } catch (error) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(
        axiosError.response?.data?.detail || "OAuth initialization failed"
      );
      setIsOAuthLoading(null);
    }
  };

  async function onSubmit(data: LoginFormData) {
    setIsLoading(true);
    try {
      const response = await authApi.login(data);
      const loginData = response.data;

      if (loginData.mfa_required) {
        // MFA flow - for now just show a message
        toast.error("MFA is required but not yet implemented in the UI");
        return;
      }

      if (loginData.access_token && loginData.refresh_token) {
        await completeLogin(loginData.access_token, loginData.refresh_token);
      }
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(
        axiosError.response?.data?.detail || "Invalid email or password"
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <Logo type="square" className="h-12 w-12" />
          </div>
          <CardTitle className="text-2xl font-bold">Welcome back</CardTitle>
          <CardDescription>
            Enter your credentials to access your account
          </CardDescription>
        </CardHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input
                        type="email"
                        placeholder="name@example.com"
                        autoComplete="email"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="Enter your password"
                        autoComplete="current-password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
            <CardFooter className="flex flex-col space-y-4">
              <Button
                type="submit"
                className="w-full"
                disabled={isLoading || isPasskeyLoading}
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Sign in
              </Button>

              {(passkeysSupported || oauthProviders.length > 0) && (
                <>
                  <div className="relative w-full">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-card px-2 text-muted-foreground">
                        Or continue with
                      </span>
                    </div>
                  </div>

                  <div className="grid gap-2 w-full">
                    {passkeysSupported && (
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full"
                        onClick={handlePasskeyLogin}
                        disabled={isLoading || isPasskeyLoading || isOAuthLoading !== null}
                      >
                        {isPasskeyLoading ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Fingerprint className="mr-2 h-4 w-4" />
                        )}
                        Passkey
                      </Button>
                    )}

                    {oauthProviders.map((provider) => (
                      <Button
                        key={provider.name}
                        type="button"
                        variant="outline"
                        className="w-full"
                        onClick={() => handleOAuthLogin(provider.name)}
                        disabled={isLoading || isPasskeyLoading || isOAuthLoading !== null}
                      >
                        {isOAuthLoading === provider.name ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <span className="mr-2">{getProviderIcon(provider.name)}</span>
                        )}
                        {provider.display_name}
                        <ExternalLink className="ml-auto h-4 w-4 text-muted-foreground" />
                      </Button>
                    ))}
                  </div>
                </>
              )}

              <p className="text-sm text-muted-foreground text-center">
                Don't have an account?{" "}
                <Link
                  to="/register"
                  className="text-primary hover:underline font-medium"
                >
                  Sign up
                </Link>
              </p>
            </CardFooter>
          </form>
        </Form>
      </Card>
    </div>
  );
}
