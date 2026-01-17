import { useState } from "react";
import { Check, X, Eye, EyeOff, Copy, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TOTPDisplay } from "@/components/ui/totp-display";
import { toast } from "sonner";
import type { FieldDefinition } from "@/hooks/useCustomAssets";

interface CustomFieldRendererProps {
  field: FieldDefinition;
  value: unknown;
  revealedValue?: unknown;
  onReveal?: () => void;
  isRevealing?: boolean;
}

export function CustomFieldRenderer({
  field,
  value,
  revealedValue,
  onReveal,
  isRevealing,
}: CustomFieldRendererProps) {
  // Header fields are just section dividers
  if (field.type === "header") {
    return (
      <div className="border-b pb-2 pt-4">
        <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
          {field.name}
        </h4>
      </div>
    );
  }

  const renderValue = () => {
    if (value === undefined || value === null || value === "") {
      return <span className="text-muted-foreground italic">Not set</span>;
    }

    switch (field.type) {
      case "text":
        return <span className="break-words">{String(value)}</span>;

      case "textbox":
        // Render HTML content for multiline text fields
        return (
          <div
            className="prose prose-sm dark:prose-invert max-w-none break-words"
            dangerouslySetInnerHTML={{ __html: String(value) }}
          />
        );

      case "number":
        return (
          <span className="font-mono">
            {typeof value === "number" ? value.toLocaleString() : String(value)}
          </span>
        );

      case "date":
        try {
          const date = new Date(String(value));
          return (
            <span>
              {date.toLocaleDateString(undefined, {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </span>
          );
        } catch {
          return <span>{String(value)}</span>;
        }

      case "checkbox":
        return value === true || value === "true" ? (
          <div className="flex items-center gap-1.5 text-green-600 dark:text-green-500">
            <Check className="h-4 w-4" />
            <span>Yes</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <X className="h-4 w-4" />
            <span>No</span>
          </div>
        );

      case "select":
        return <span>{String(value)}</span>;

      case "password":
        // Password fields - show reveal/copy UI inline
        return (
          <InlinePasswordReveal
            value={revealedValue !== undefined ? String(revealedValue) : undefined}
            onReveal={onReveal}
            isRevealing={isRevealing}
          />
        );

      case "totp":
        // TOTP fields - show live code generator when revealed
        return (
          <InlineTOTPReveal
            value={revealedValue !== undefined ? String(revealedValue) : undefined}
            onReveal={onReveal}
            isRevealing={isRevealing}
          />
        );

      default:
        return <span>{String(value)}</span>;
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <dt className="text-sm font-medium text-muted-foreground flex items-center gap-2">
        {field.name}
        {field.required && (
          <span className="text-xs text-destructive">*</span>
        )}
      </dt>
      <dd className="text-sm">{renderValue()}</dd>
      {field.hint && (
        <p className="text-xs text-muted-foreground">{field.hint}</p>
      )}
    </div>
  );
}

// Inline password reveal component for custom asset fields
interface InlinePasswordRevealProps {
  value?: string;
  onReveal?: () => void;
  isRevealing?: boolean;
}

function InlinePasswordReveal({ value, onReveal, isRevealing }: InlinePasswordRevealProps) {
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleToggleReveal = () => {
    if (!revealed && !value && onReveal) {
      onReveal();
    }
    setRevealed(!revealed);
  };

  const handleCopy = async () => {
    if (!value && onReveal) {
      onReveal();
      return;
    }
    if (value) {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      toast.success("Password copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 font-mono text-sm bg-muted px-3 py-2 rounded-md">
        {isRevealing ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : revealed && value ? (
          value
        ) : (
          <span className="tracking-widest">************</span>
        )}
      </div>
      <Button
        variant="outline"
        size="icon"
        onClick={handleToggleReveal}
        disabled={isRevealing}
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
        disabled={isRevealing}
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

// Inline TOTP reveal component for custom asset fields
interface InlineTOTPRevealProps {
  value?: string;
  onReveal?: () => void;
  isRevealing?: boolean;
}

function InlineTOTPReveal({ value, onReveal, isRevealing }: InlineTOTPRevealProps) {
  const [revealed, setRevealed] = useState(false);

  const handleToggleReveal = () => {
    if (!revealed && !value && onReveal) {
      onReveal();
    }
    setRevealed(!revealed);
  };

  // When not revealed, show masked placeholder with reveal button
  if (!revealed) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 font-mono text-sm bg-muted px-3 py-2 rounded-md">
          {isRevealing ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <span className="tracking-widest">************</span>
          )}
        </div>
        <Button
          variant="outline"
          size="icon"
          onClick={handleToggleReveal}
          disabled={isRevealing}
        >
          <Eye className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  // When revealed and we have the secret, show the TOTP display
  if (value) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <TOTPDisplay secret={value} className="flex-1" />
          <Button
            variant="outline"
            size="icon"
            onClick={handleToggleReveal}
          >
            <EyeOff className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  // Revealed but no value yet (still loading)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 font-mono text-sm bg-muted px-3 py-2 rounded-md">
        <Loader2 className="h-4 w-4 animate-spin" />
      </div>
      <Button
        variant="outline"
        size="icon"
        onClick={handleToggleReveal}
      >
        <EyeOff className="h-4 w-4" />
      </Button>
    </div>
  );
}

interface CustomFieldListProps {
  fields: FieldDefinition[];
  values: Record<string, unknown>;
  revealedValues?: Record<string, unknown>;
  onReveal?: () => void;
  isRevealing?: boolean;
}

export function CustomFieldList({
  fields,
  values,
  revealedValues,
  onReveal,
  isRevealing,
}: CustomFieldListProps) {
  const hasSecretFields = fields.some((f) => f.type === "password" || f.type === "totp");

  return (
    <dl className="grid gap-4">
      {fields.map((field) => (
        <CustomFieldRenderer
          key={field.key}
          field={field}
          value={values[field.key]}
          revealedValue={revealedValues?.[field.key]}
          onReveal={hasSecretFields ? onReveal : undefined}
          isRevealing={isRevealing}
        />
      ))}
    </dl>
  );
}
