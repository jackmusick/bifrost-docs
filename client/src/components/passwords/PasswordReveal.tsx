import { useState } from "react";
import { Eye, EyeOff, Copy, Check, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface PasswordRevealProps {
  orgId: string;
  passwordId: string;
}

interface PasswordRevealResponse {
  password: string;
}

export function PasswordReveal({ orgId, passwordId }: PasswordRevealProps) {
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);

  const { data, isLoading, refetch, isFetched } = useQuery({
    queryKey: ["passwords", orgId, passwordId, "reveal"],
    queryFn: async () => {
      const response = await api.get<PasswordRevealResponse>(
        `/api/organizations/${orgId}/passwords/${passwordId}/reveal`
      );
      return response.data;
    },
    enabled: false,
  });

  const handleToggleReveal = async () => {
    if (!revealed && !isFetched) {
      await refetch();
    }
    setRevealed(!revealed);
  };

  const handleCopy = async () => {
    if (!data?.password) {
      // Fetch if not already fetched
      const result = await refetch();
      if (result.data?.password) {
        await navigator.clipboard.writeText(result.data.password);
        setCopied(true);
        toast.success("Password copied to clipboard");
        setTimeout(() => setCopied(false), 2000);
      }
      return;
    }

    await navigator.clipboard.writeText(data.password);
    setCopied(true);
    toast.success("Password copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 font-mono text-sm bg-muted px-3 py-2 rounded-md">
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : revealed && data?.password ? (
          data.password
        ) : (
          <span className="tracking-widest">************</span>
        )}
      </div>
      <Button
        variant="outline"
        size="icon"
        onClick={handleToggleReveal}
        disabled={isLoading}
      >
        {revealed ? (
          <EyeOff className="h-4 w-4" />
        ) : (
          <Eye className="h-4 w-4" />
        )}
      </Button>
      <Button
        variant="outline"
        size="icon"
        onClick={handleCopy}
        disabled={isLoading}
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
