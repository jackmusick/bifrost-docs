import { useState } from "react";
import { User, KeyRound, Shield, Check, Loader2 } from "lucide-react";
import * as OTPAuth from "otpauth";
import api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "sonner";

interface PasswordRevealResponse {
  password: string;
  totp_secret: string | null;
}

// Minimal interface that works with both Password and GlobalPassword
interface PasswordItem {
  id: string;
  username: string | null;
  has_totp: boolean;
}

interface PasswordListActionsProps {
  password: PasswordItem;
  orgId: string;
}

type CopyState = "idle" | "loading" | "copied";

function generateTOTPCode(secret: string): string | null {
  try {
    const cleanSecret = secret.replace(/\s/g, "").toUpperCase();
    const totp = new OTPAuth.TOTP({
      secret: OTPAuth.Secret.fromBase32(cleanSecret),
      digits: 6,
      period: 30,
    });
    return totp.generate();
  } catch {
    return null;
  }
}

export function PasswordListActions({ password, orgId }: PasswordListActionsProps) {
  const [usernameCopyState, setUsernameCopyState] = useState<CopyState>("idle");
  const [passwordCopyState, setPasswordCopyState] = useState<CopyState>("idle");
  const [totpCopyState, setTotpCopyState] = useState<CopyState>("idle");

  const handleCopyUsername = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!password.username) return;

    try {
      await navigator.clipboard.writeText(password.username);
      setUsernameCopyState("copied");
      toast.success("Username copied");
      setTimeout(() => setUsernameCopyState("idle"), 2000);
    } catch {
      toast.error("Failed to copy username");
    }
  };

  const handleCopyPassword = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setPasswordCopyState("loading");

    try {
      const response = await api.get<PasswordRevealResponse>(
        `/api/organizations/${orgId}/passwords/${password.id}/reveal`
      );
      await navigator.clipboard.writeText(response.data.password);
      setPasswordCopyState("copied");
      toast.success("Password copied");
      setTimeout(() => setPasswordCopyState("idle"), 2000);
    } catch {
      toast.error("Failed to copy password");
      setPasswordCopyState("idle");
    }
  };

  const handleCopyTOTP = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!password.has_totp) return;

    setTotpCopyState("loading");

    try {
      const response = await api.get<PasswordRevealResponse>(
        `/api/organizations/${orgId}/passwords/${password.id}/reveal`
      );

      if (!response.data.totp_secret) {
        toast.error("No TOTP secret available");
        setTotpCopyState("idle");
        return;
      }

      const code = generateTOTPCode(response.data.totp_secret);
      if (!code) {
        toast.error("Failed to generate TOTP code");
        setTotpCopyState("idle");
        return;
      }

      await navigator.clipboard.writeText(code);
      setTotpCopyState("copied");
      toast.success("TOTP code copied");
      setTimeout(() => setTotpCopyState("idle"), 2000);
    } catch {
      toast.error("Failed to copy TOTP code");
      setTotpCopyState("idle");
    }
  };

  const renderCopyIcon = (state: CopyState, defaultIcon: React.ReactNode) => {
    if (state === "loading") {
      return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
    }
    if (state === "copied") {
      return <Check className="h-3.5 w-3.5 text-green-500" />;
    }
    return defaultIcon;
  };

  return (
    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7"
            onClick={handleCopyUsername}
            disabled={!password.username || usernameCopyState !== "idle"}
          >
            {renderCopyIcon(
              usernameCopyState,
              <User className="h-3.5 w-3.5" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>Copy username</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7"
            onClick={handleCopyPassword}
            disabled={passwordCopyState !== "idle"}
          >
            {renderCopyIcon(
              passwordCopyState,
              <KeyRound className="h-3.5 w-3.5" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>Copy password</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7"
            onClick={handleCopyTOTP}
            disabled={!password.has_totp || totpCopyState !== "idle"}
          >
            {renderCopyIcon(
              totpCopyState,
              <Shield className="h-3.5 w-3.5" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          {password.has_totp ? "Copy TOTP code" : "No TOTP configured"}
        </TooltipContent>
      </Tooltip>
    </div>
  );
}
