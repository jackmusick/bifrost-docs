import { useState, useEffect, useMemo } from "react";
import * as OTPAuth from "otpauth";
import { Copy, Check, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface TOTPDisplayProps {
  secret: string;
  className?: string;
}

// Generate code outside of component to avoid effect dependencies
function generateTOTPCode(secret: string): { code: string | null; error: string | null } {
  try {
    // Clean the secret - remove spaces and make uppercase
    const cleanSecret = secret.replace(/\s/g, "").toUpperCase();

    const totp = new OTPAuth.TOTP({
      secret: OTPAuth.Secret.fromBase32(cleanSecret),
      digits: 6,
      period: 30,
    });

    return { code: totp.generate(), error: null };
  } catch {
    return { code: null, error: "Invalid TOTP secret" };
  }
}

export function TOTPDisplay({ secret, className }: TOTPDisplayProps) {
  const [secondsRemaining, setSecondsRemaining] = useState(() => {
    const now = Math.floor(Date.now() / 1000);
    return 30 - (now % 30);
  });
  const [copied, setCopied] = useState(false);
  const [counter, setCounter] = useState(0); // Used to trigger code regeneration

  // Generate code using useMemo - regenerates when secret or counter changes
  const { code, error } = useMemo(() => {
    // counter is used to force regeneration on period expiry
    void counter;
    return generateTOTPCode(secret);
  }, [secret, counter]);

  useEffect(() => {
    // Update every second
    const interval = setInterval(() => {
      const currentTime = Math.floor(Date.now() / 1000);
      const newRemaining = 30 - (currentTime % 30);
      setSecondsRemaining(newRemaining);

      // Increment counter when period expires to regenerate code
      if (newRemaining === 30) {
        setCounter((c) => c + 1);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleCopy = async () => {
    if (!code) return;

    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast.success("Code copied");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy code");
    }
  };

  // Calculate stroke-dasharray and stroke-dashoffset for circular progress
  const radius = 12;
  const circumference = 2 * Math.PI * radius;
  const progress = secondsRemaining / 30;
  const strokeDashoffset = circumference * (1 - progress);

  if (error) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 text-destructive text-sm",
          className
        )}
      >
        <AlertCircle className="h-4 w-4" />
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* Circular countdown */}
      <div className="relative h-8 w-8 flex items-center justify-center">
        <svg
          className="h-8 w-8 -rotate-90"
          viewBox="0 0 32 32"
        >
          {/* Background circle */}
          <circle
            cx="16"
            cy="16"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-muted"
          />
          {/* Progress circle */}
          <circle
            cx="16"
            cy="16"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={cn(
              "transition-all duration-1000 ease-linear",
              secondsRemaining <= 5 ? "text-destructive" : "text-primary"
            )}
          />
        </svg>
        <span className="absolute text-[10px] font-medium tabular-nums">
          {secondsRemaining}
        </span>
      </div>

      {/* Code display */}
      <div
        className={cn(
          "font-mono text-2xl tracking-widest select-all transition-opacity duration-300",
          secondsRemaining <= 5 && "opacity-50"
        )}
      >
        {code ? (
          <>
            <span>{code.slice(0, 3)}</span>
            <span className="mx-1 text-muted-foreground/50">-</span>
            <span>{code.slice(3)}</span>
          </>
        ) : (
          <span className="text-muted-foreground">------</span>
        )}
      </div>

      {/* Copy button */}
      <Button
        variant="outline"
        size="icon"
        onClick={handleCopy}
        disabled={!code}
        className="h-8 w-8"
      >
        {copied ? (
          <Check className="h-4 w-4 text-green-500" />
        ) : (
          <Copy className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
}
