import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import type { FieldDefinition } from "@/hooks/useCustomAssets";
import { TiptapEditorAssetField } from "./TiptapEditorAssetField";

interface CustomFieldInputProps {
  field: FieldDefinition;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
  mode?: "create" | "edit";
}

export function CustomFieldInput({
  field,
  value,
  onChange,
  error,
  mode = "create",
}: CustomFieldInputProps) {
  const [showPassword, setShowPassword] = useState(false);

  // Header fields are just section dividers
  if (field.type === "header") {
    return (
      <div className="border-b pb-2 pt-4 col-span-full">
        <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
          {field.name}
        </h4>
      </div>
    );
  }

  const renderInput = () => {
    switch (field.type) {
      case "text":
        return (
          <Input
            type="text"
            value={value !== undefined && value !== null ? String(value) : ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.hint || `Enter ${field.name.toLowerCase()}`}
            className={error ? "border-destructive" : ""}
          />
        );

      case "textbox":
        return (
          <TiptapEditorAssetField
            content={value !== undefined && value !== null ? String(value) : ""}
            onChange={(html) => onChange(html)}
            placeholder={field.hint || `Enter ${field.name.toLowerCase()}`}
            className={error ? "border-destructive" : ""}
          />
        );

      case "number":
        return (
          <Input
            type="number"
            value={value !== undefined && value !== null ? String(value) : ""}
            onChange={(e) => {
              const val = e.target.value;
              onChange(val === "" ? null : Number(val));
            }}
            placeholder={field.hint || `Enter ${field.name.toLowerCase()}`}
            className={error ? "border-destructive" : ""}
          />
        );

      case "date":
        return (
          <Input
            type="date"
            value={value !== undefined && value !== null ? String(value) : ""}
            onChange={(e) => onChange(e.target.value)}
            className={error ? "border-destructive" : ""}
          />
        );

      case "checkbox":
        return (
          <div className="flex items-center gap-2 h-10">
            <Checkbox
              id={field.key}
              checked={value === true || value === "true"}
              onCheckedChange={(checked) => onChange(checked)}
            />
            <Label htmlFor={field.key} className="text-sm cursor-pointer">
              {field.hint || field.name}
            </Label>
          </div>
        );

      case "select":
        return (
          <Select
            value={value !== undefined && value !== null ? String(value) : ""}
            onValueChange={(val) => onChange(val)}
          >
            <SelectTrigger className={error ? "border-destructive" : ""}>
              <SelectValue placeholder={`Select ${field.name.toLowerCase()}`} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case "password":
        return (
          <div className="relative">
            <Input
              type={showPassword ? "text" : "password"}
              value={value !== undefined && value !== null ? String(value) : ""}
              onChange={(e) => onChange(e.target.value)}
              placeholder={
                mode === "edit"
                  ? "Leave blank to keep current"
                  : field.hint || `Enter ${field.name.toLowerCase()}`
              }
              className={`pr-10 ${error ? "border-destructive" : ""}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Eye className="h-4 w-4 text-muted-foreground" />
              )}
            </Button>
          </div>
        );

      case "totp":
        // TOTP field - same masked input as password
        return (
          <div className="relative">
            <Input
              type={showPassword ? "text" : "password"}
              value={value !== undefined && value !== null ? String(value) : ""}
              onChange={(e) => onChange(e.target.value)}
              placeholder={
                mode === "edit"
                  ? "Leave blank to keep current"
                  : field.hint || "Paste your TOTP secret (base32 format)"
              }
              className={`pr-10 ${error ? "border-destructive" : ""}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Eye className="h-4 w-4 text-muted-foreground" />
              )}
            </Button>
          </div>
        );

      default:
        return (
          <Input
            type="text"
            value={value !== undefined && value !== null ? String(value) : ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.hint || `Enter ${field.name.toLowerCase()}`}
            className={error ? "border-destructive" : ""}
          />
        );
    }
  };

  const isSecretField = field.type === "password" || field.type === "totp";
  const showLeaveBlank = isSecretField && mode === "edit";

  return (
    <div className="space-y-2">
      {field.type !== "checkbox" && (
        <Label htmlFor={field.key} className="text-sm font-medium">
          {field.name}
          {field.required && mode === "create" && (
            <span className="text-destructive ml-1">*</span>
          )}
          {showLeaveBlank && (
            <span className="text-muted-foreground font-normal ml-1">
              (leave blank to keep current)
            </span>
          )}
        </Label>
      )}
      {renderInput()}
      {error && <p className="text-xs text-destructive">{error}</p>}
      {field.type !== "checkbox" && field.hint && !error && (
        <p className="text-xs text-muted-foreground">{field.hint}</p>
      )}
    </div>
  );
}
