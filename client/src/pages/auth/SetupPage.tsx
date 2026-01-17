/**
 * Setup Wizard Page
 *
 * First-time setup for creating the initial admin user.
 * Only shown when no users exist in the system.
 *
 * Supports two registration methods:
 * 1. Passkey (preferred) - Passwordless via Face ID, Touch ID, etc.
 * 2. Password (fallback) - Traditional password registration
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { Loader2, Mail, Lock, User, Fingerprint, KeyRound } from "lucide-react";
import { Logo } from "@/components/branding/Logo";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { authApi } from "@/lib/api-client";
import { supportsPasskeys, setupWithPasskey } from "@/lib/passkeys";
import { useAuthStore } from "@/stores/auth.store";

type SetupMode = "choose" | "passkey" | "password";

export function SetupPage() {
  const navigate = useNavigate();
  const { login } = useAuthStore();

  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingSetup, setIsCheckingSetup] = useState(true);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<SetupMode>("choose");

  // Check passkey support - computed once on mount
  const [passkeysSupported] = useState(() => supportsPasskeys());

  // Account form (shared between modes)
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");

  // Password-specific fields
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Check if setup is needed
  useEffect(() => {
    async function checkSetup() {
      try {
        const response = await authApi.setupStatus();
        setNeedsSetup(response.data.needs_setup);
        if (!response.data.needs_setup) {
          // Setup not needed, redirect to login
          navigate("/login");
        }
      } catch {
        // If endpoint fails, assume setup is not needed
        navigate("/login");
      } finally {
        setIsCheckingSetup(false);
      }
    }
    checkSetup();
  }, [navigate]);

  const handlePasskeySetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      // Create the user with passkey
      const result = await setupWithPasskey(email, name);

      // Fetch user info and login
      localStorage.setItem("access_token", result.access_token);
      const userResponse = await authApi.me();
      login(userResponse.data, result.access_token, result.refresh_token);

      toast.success("Account created successfully!");
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Passkey setup failed");
      setIsLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setIsLoading(true);

    try {
      // Register the user
      await authApi.register({ email, password, name: name || undefined });

      toast.success("Account created! Please sign in.");
      navigate("/login");
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || "Account creation failed");
      setIsLoading(false);
    }
  };

  const handleModeChange = (newMode: SetupMode) => {
    setError(null);
    setMode(newMode);
  };

  if (isCheckingSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!needsSetup) {
    return null; // Will redirect via useEffect
  }

  // Render method choice screen
  const renderChooseMode = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <div className="relative">
          <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            id="name"
            type="text"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="pl-10"
            autoFocus
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            id="email"
            type="email"
            placeholder="admin@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="pl-10"
            required
          />
        </div>
      </div>

      <div className="pt-2 space-y-3">
        {passkeysSupported && (
          <Button
            type="button"
            className="w-full"
            disabled={!email}
            onClick={() => handleModeChange("passkey")}
          >
            <Fingerprint className="h-4 w-4 mr-2" />
            Continue with Passkey
          </Button>
        )}
        <Button
          type="button"
          variant={passkeysSupported ? "outline" : "default"}
          className="w-full"
          disabled={!email}
          onClick={() => handleModeChange("password")}
        >
          <KeyRound className="h-4 w-4 mr-2" />
          {passkeysSupported ? "Use password instead" : "Continue with Password"}
        </Button>
      </div>

      {passkeysSupported && (
        <p className="text-xs text-center text-muted-foreground pt-2">
          Passkeys use Face ID, Touch ID, or your device PIN for secure,
          passwordless authentication.
        </p>
      )}
    </div>
  );

  // Render passkey setup form
  const renderPasskeyMode = () => (
    <form onSubmit={handlePasskeySetup} className="space-y-4">
      <div className="text-center space-y-2 pb-2">
        <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
          <Fingerprint className="h-6 w-6 text-primary" />
        </div>
        <p className="text-sm text-muted-foreground">
          Create a passkey using Face ID, Touch ID, or your device PIN. No
          password needed!
        </p>
      </div>

      <div className="space-y-2">
        <Label>Name</Label>
        <Input value={name || "Not provided"} disabled className="bg-muted" />
      </div>
      <div className="space-y-2">
        <Label>Email</Label>
        <Input value={email} disabled className="bg-muted" />
      </div>

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
        ) : (
          <Fingerprint className="h-4 w-4 mr-2" />
        )}
        Create Passkey
      </Button>

      <Button
        type="button"
        variant="ghost"
        className="w-full"
        onClick={() => handleModeChange("choose")}
        disabled={isLoading}
      >
        Back
      </Button>
    </form>
  );

  // Render password setup form
  const renderPasswordMode = () => (
    <form onSubmit={handlePasswordSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label>Name</Label>
        <Input value={name || "Not provided"} disabled className="bg-muted" />
      </div>
      <div className="space-y-2">
        <Label>Email</Label>
        <Input value={email} disabled className="bg-muted" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            id="password"
            type="password"
            placeholder="At least 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="pl-10"
            required
            minLength={8}
            autoFocus
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="confirmPassword">Confirm Password</Label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            id="confirmPassword"
            type="password"
            placeholder="Confirm your password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="pl-10"
            required
          />
        </div>
      </div>

      <Button
        type="submit"
        className="w-full"
        disabled={isLoading || !password || !confirmPassword}
      >
        {isLoading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
        Create Account
      </Button>

      <Button
        type="button"
        variant="ghost"
        className="w-full"
        onClick={() => handleModeChange("choose")}
        disabled={isLoading}
      >
        Back
      </Button>
    </form>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-md"
      >
        <Card className="border-primary/10 shadow-xl shadow-primary/5">
          <CardHeader className="text-center space-y-4 pb-2">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.1, duration: 0.3 }}
              className="flex justify-center"
            >
              <Logo type="square" className="h-16 w-16" />
            </motion.div>
            <div className="space-y-1">
              <CardTitle className="text-2xl font-bold tracking-tight">
                Welcome to Bifrost Docs
              </CardTitle>
              <CardDescription className="text-base">
                {mode === "choose" && "Create your admin account to get started"}
                {mode === "passkey" && "Set up passwordless authentication"}
                {mode === "password" && "Create your password"}
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {mode === "choose" && renderChooseMode()}
            {mode === "passkey" && renderPasskeyMode()}
            {mode === "password" && renderPasswordMode()}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

export default SetupPage;
