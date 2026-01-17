import { useState } from "react";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { TOTPDisplay } from "@/components/ui/totp-display";

interface TOTPRevealProps {
  orgId: string;
  passwordId: string;
}

interface PasswordRevealResponse {
  password: string;
  totp_secret: string | null;
}

export function TOTPReveal({ orgId, passwordId }: TOTPRevealProps) {
  const [revealed, setRevealed] = useState(false);

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

  return (
    <div className="space-y-2">
      {revealed && data?.totp_secret ? (
        <div className="flex items-center gap-2">
          <div className="flex-1">
            <TOTPDisplay secret={data.totp_secret} />
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={handleToggleReveal}
          >
            <EyeOff className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <div className="flex-1 font-mono text-sm bg-muted px-3 py-2 rounded-md">
            <span className="tracking-widest">******</span>
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={handleToggleReveal}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
