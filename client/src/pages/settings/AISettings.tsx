import { useState, useRef, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  webSocketService,
  type ReindexMessage,
} from "@/services/websocket";
import {
  Loader2,
  Brain,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Database,
  Bot,
  Check,
  X,
  Eye,
  EyeOff,
  AlertTriangle,
  Zap,
  Search,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Combobox } from "@/components/ui/combobox";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  adminApi,
  aiSettingsApi,
  type EntityType,
  type OpenAIModel,
  type LLMProvider,
} from "@/lib/api-client";
import { formatDateTime } from "@/lib/date-utils";
import {
  useAISettings,
  useUpdateCompletionsConfig,
  useUpdateEmbeddingsConfig,
  useTestAIConnection,
} from "@/hooks/useAISettings";
import { useAuthStore } from "@/stores/auth.store";

const ENTITY_TYPE_LABELS: Record<EntityType, string> = {
  password: "Passwords",
  configuration: "Configurations",
  location: "Locations",
  document: "Documents",
  custom_asset: "Custom Assets",
};

const PROVIDER_OPTIONS: { value: LLMProvider; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "openai_compatible", label: "OpenAI Compatible" },
];

// Schemas for each form
const completionsSchema = z.object({
  provider: z.enum(["openai", "anthropic", "openai_compatible"]),
  api_key: z.string().optional(),
  model: z.string().min(1, "Model is required"),
  endpoint: z.string().optional(),
});

const embeddingsSchema = z.object({
  api_key: z.string().optional(),
  model: z.string().min(1, "Model is required"),
});

type CompletionsFormData = z.infer<typeof completionsSchema>;
type EmbeddingsFormData = z.infer<typeof embeddingsSchema>;

export function AISettings() {
  const authStore = useAuthStore();
  const isAdmin = authStore.isAdmin();
  const { data: settings } = useAISettings();

  if (!isAdmin) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertTriangle className="h-12 w-12 text-amber-500 mb-4" />
          <p className="text-lg font-medium mb-1">Admin Access Required</p>
          <p className="text-sm text-muted-foreground">
            Only administrators can manage AI settings.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Show reindex sections only if embeddings are configured
  const embeddingsConfigured = settings?.embeddings?.api_key_set;

  return (
    <div className="space-y-6">
      <CompletionsConfigSection />
      <EmbeddingsConfigSection />
      <IndexingConfigSection />
      {embeddingsConfigured ? (
        <>
          <Separator className="my-8" />
          <IndexStatsSection />
          <ReindexSection />
        </>
      ) : (
        <Card>
          <CardContent className="py-8">
            <div className="flex items-center gap-3 text-muted-foreground">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              <p className="text-sm">
                Configure embeddings above to enable semantic search and reindexing.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// =============================================================================
// Completions Configuration Section
// =============================================================================
function CompletionsConfigSection() {
  const queryClient = useQueryClient();
  const [showApiKey, setShowApiKey] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    models?: OpenAIModel[];
  } | null>(null);

  const { data: settings, isLoading, error } = useAISettings();
  const updateMutation = useUpdateCompletionsConfig();
  const testMutation = useTestAIConnection();

  const form = useForm<CompletionsFormData>({
    resolver: zodResolver(completionsSchema),
    defaultValues: {
      provider: "openai",
      api_key: "",
      model: "gpt-4o-mini",
      endpoint: "",
    },
  });

  const selectedProvider = form.watch("provider");
  const isConfigured = settings?.completions?.api_key_set;

  // Update form when settings load
  useEffect(() => {
    if (settings?.completions) {
      form.setValue("provider", settings.completions.provider);
      form.setValue("model", settings.completions.model);
      if (settings.completions.endpoint) {
        form.setValue("endpoint", settings.completions.endpoint);
      }
    }
  }, [settings, form]);

  async function onTestConnection() {
    const apiKey = form.getValues("api_key");
    const provider = form.getValues("provider");
    const endpoint = form.getValues("endpoint");

    if (!apiKey) {
      toast.error("Please enter an API key first");
      return;
    }

    if (provider === "openai_compatible" && !endpoint) {
      toast.error("Please enter an endpoint URL for OpenAI Compatible");
      return;
    }

    setTestResult(null);
    try {
      const result = await testMutation.mutateAsync({
        provider,
        api_key: apiKey,
        endpoint: provider === "openai_compatible" ? endpoint : undefined,
      });
      setTestResult({
        success: result.success,
        message: result.message,
        models: result.completions_models,
      });

      if (result.success) {
        toast.success("Connection successful!", { description: result.message });
        if (result.completions_models?.length) {
          form.setValue("model", result.completions_models[0].id);
        }
      } else {
        toast.error("Connection failed", { description: result.error || result.message });
      }
    } catch {
      toast.error("Failed to test connection");
    }
  }

  async function onSubmit(data: CompletionsFormData) {
    try {
      await updateMutation.mutateAsync({
        provider: data.provider,
        api_key: data.api_key || undefined,
        model: data.model,
        endpoint: data.provider === "openai_compatible" ? data.endpoint : undefined,
      });

      form.setValue("api_key", "");
      setTestResult(null);
      toast.success("Completions configuration saved");
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
    } catch {
      toast.error("Failed to save configuration");
    }
  }

  async function onClearConfig() {
    try {
      await updateMutation.mutateAsync({ api_key: "" });
      setTestResult(null);
      toast.success("Completions configuration removed");
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
    } catch {
      toast.error("Failed to remove configuration");
    }
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
          <p className="text-lg font-medium mb-1">Failed to load settings</p>
          <p className="text-sm text-muted-foreground">Please try again later</p>
        </CardContent>
      </Card>
    );
  }

  const hasTestedSuccessfully = testResult?.success === true;
  const canSave = hasTestedSuccessfully && form.formState.isValid;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="h-5 w-5" />
          Chat Completions
        </CardTitle>
        <CardDescription>
          Configure the AI provider for chat and document understanding.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <>
            {/* Status Banner */}
            {isConfigured && (
              <div className="rounded-lg border bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium text-green-800 dark:text-green-200">
                      Configured
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onClearConfig}
                    disabled={updateMutation.isPending}
                  >
                    {updateMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Remove"
                    )}
                  </Button>
                </div>
                <div className="mt-2 space-y-1">
                  <p className="text-sm text-green-700 dark:text-green-300">
                    <span className="font-medium">Provider:</span>{" "}
                    {PROVIDER_OPTIONS.find(p => p.value === settings?.completions?.provider)?.label}
                  </p>
                  <p className="text-sm text-green-700 dark:text-green-300">
                    <span className="font-medium">Model:</span> {settings?.completions?.model}
                  </p>
                </div>
              </div>
            )}

            {/* Configuration Form */}
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                {/* Provider Selection */}
                <FormField
                  control={form.control}
                  name="provider"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Provider</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select a provider" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {PROVIDER_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Endpoint (only for OpenAI Compatible) */}
                {selectedProvider === "openai_compatible" && (
                  <FormField
                    control={form.control}
                    name="endpoint"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Endpoint URL</FormLabel>
                        <FormControl>
                          <Input placeholder="https://your-server.com/v1" {...field} />
                        </FormControl>
                        <FormDescription>
                          Base URL for your OpenAI-compatible API.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}

                {/* API Key */}
                <FormField
                  control={form.control}
                  name="api_key"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        API Key
                        {isConfigured && (
                          <span className="text-muted-foreground font-normal ml-2">
                            (leave blank to keep existing)
                          </span>
                        )}
                      </FormLabel>
                      <FormControl>
                        <div className="flex gap-2">
                          <div className="relative flex-1">
                            <Input
                              type={showApiKey ? "text" : "password"}
                              placeholder={selectedProvider === "anthropic" ? "sk-ant-..." : "sk-..."}
                              {...field}
                            />
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="absolute right-0 top-0 h-full px-3"
                              onClick={() => setShowApiKey(!showApiKey)}
                            >
                              {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </Button>
                          </div>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={onTestConnection}
                            disabled={testMutation.isPending || !field.value}
                          >
                            {testMutation.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : hasTestedSuccessfully ? (
                              <>
                                <Check className="h-4 w-4 mr-2 text-green-600" />
                                Verified
                              </>
                            ) : testResult?.success === false ? (
                              <>
                                <X className="h-4 w-4 mr-2 text-destructive" />
                                Failed
                              </>
                            ) : (
                              <>
                                <Zap className="h-4 w-4 mr-2" />
                                Test
                              </>
                            )}
                          </Button>
                        </div>
                      </FormControl>
                      <FormDescription>
                        {selectedProvider === "openai" && (
                          <>Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">platform.openai.com</a></>
                        )}
                        {selectedProvider === "anthropic" && (
                          <>Get your API key from <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">console.anthropic.com</a></>
                        )}
                        {selectedProvider === "openai_compatible" && "API key for your OpenAI-compatible endpoint."}
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Test Result */}
                {testResult && !testResult.success && (
                  <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
                    <div className="flex items-center gap-2 text-sm text-destructive">
                      <X className="h-4 w-4" />
                      <span>{testResult.message}</span>
                    </div>
                  </div>
                )}

                {/* Model Selection (after successful test) */}
                {hasTestedSuccessfully && (
                  <>
                    <div className="rounded-lg border border-green-500/50 bg-green-50 dark:bg-green-950/20 p-3">
                      <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-300">
                        <Check className="h-4 w-4" />
                        <span>{testResult?.message}</span>
                      </div>
                    </div>

                    <FormField
                      control={form.control}
                      name="model"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Model</FormLabel>
                          <FormControl>
                            <Combobox
                              options={
                                testResult?.models?.map((model) => ({
                                  value: model.id,
                                  label: model.name,
                                  description: model.description,
                                })) ?? []
                              }
                              value={field.value}
                              onValueChange={field.onChange}
                              placeholder="Select a model"
                              searchPlaceholder="Search models..."
                              emptyText="No model found."
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <div className="flex justify-end">
                      <Button type="submit" disabled={!canSave || updateMutation.isPending}>
                        {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save
                      </Button>
                    </div>
                  </>
                )}

                {/* Hint */}
                {!hasTestedSuccessfully && form.getValues("api_key") && (
                  <p className="text-sm text-muted-foreground text-center">
                    Test your API key to see available models
                  </p>
                )}
              </form>
            </Form>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Embeddings Configuration Section
// =============================================================================
function EmbeddingsConfigSection() {
  const queryClient = useQueryClient();
  const [showApiKey, setShowApiKey] = useState(false);
  const [useExistingKey, setUseExistingKey] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    models?: OpenAIModel[];
  } | null>(null);

  const { data: settings, isLoading } = useAISettings();
  const updateMutation = useUpdateEmbeddingsConfig();

  const form = useForm<EmbeddingsFormData>({
    resolver: zodResolver(embeddingsSchema),
    defaultValues: {
      api_key: "",
      model: "text-embedding-3-small",
    },
  });

  const isConfigured = settings?.embeddings?.api_key_set;

  // Check if completions has OpenAI configured (for key reuse)
  const completionsHasOpenAI = settings?.completions?.provider === "openai" && settings?.completions?.api_key_set;

  // Update form when settings load
  useEffect(() => {
    if (settings?.embeddings) {
      form.setValue("model", settings.embeddings.model);
    }
  }, [settings, form]);

  async function onTestConnection() {
    const apiKey = form.getValues("api_key");

    if (!apiKey && !useExistingKey) {
      toast.error("Please enter an API key first");
      return;
    }

    setTestResult(null);
    try {
      // If using existing key, we need to test with the stored key
      // We'll use a special endpoint or the stored key logic
      const testKey = useExistingKey ? "__USE_STORED__" : apiKey;

      if (useExistingKey) {
        // Test with the embeddings provider - fetch models directly
        const result = await aiSettingsApi.testConnection({
          provider: "openai",
          api_key: testKey!,
        }).then(r => r.data);

        setTestResult({
          success: result.success,
          message: result.success
            ? `Using existing OpenAI key. Found ${result.embedding_models?.length || 0} embedding models.`
            : result.message,
          models: result.embedding_models,
        });

        if (result.success) {
          toast.success("Connection verified!");
          if (result.embedding_models?.length) {
            form.setValue("model", result.embedding_models[0].id);
          }
        } else {
          toast.error("Connection failed", { description: result.error || result.message });
        }
      } else {
        const result = await aiSettingsApi.testConnection({
          provider: "openai",
          api_key: apiKey!,
        }).then(r => r.data);

        setTestResult({
          success: result.success,
          message: result.message,
          models: result.embedding_models,
        });

        if (result.success) {
          toast.success("Connection successful!", { description: result.message });
          if (result.embedding_models?.length) {
            form.setValue("model", result.embedding_models[0].id);
          }
        } else {
          toast.error("Connection failed", { description: result.error || result.message });
        }
      }
    } catch {
      toast.error("Failed to test connection");
    }
  }

  async function onSubmit(data: EmbeddingsFormData) {
    try {
      await updateMutation.mutateAsync({
        api_key: useExistingKey ? undefined : (data.api_key || undefined),
        model: data.model,
      });

      form.setValue("api_key", "");
      setTestResult(null);
      setUseExistingKey(false);
      toast.success("Embeddings configuration saved");
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
    } catch {
      toast.error("Failed to save configuration");
    }
  }

  async function onClearConfig() {
    try {
      await updateMutation.mutateAsync({ api_key: "" });
      setTestResult(null);
      toast.success("Embeddings configuration removed");
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
    } catch {
      toast.error("Failed to remove configuration");
    }
  }

  const hasTestedSuccessfully = testResult?.success === true;
  const canSave = hasTestedSuccessfully && form.formState.isValid;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          Embeddings
        </CardTitle>
        <CardDescription>
          Configure OpenAI for semantic search and document indexing.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <>
            {/* Status Banner */}
            {isConfigured ? (
              <div className="rounded-lg border bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium text-green-800 dark:text-green-200">
                      Configured
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onClearConfig}
                    disabled={updateMutation.isPending}
                  >
                    {updateMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Remove"
                    )}
                  </Button>
                </div>
                <div className="mt-2">
                  <p className="text-sm text-green-700 dark:text-green-300">
                    <span className="font-medium">Model:</span> {settings?.embeddings?.model}
                  </p>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900 p-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <span className="text-sm font-medium text-amber-800 dark:text-amber-200">
                    Not Configured
                  </span>
                </div>
                <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                  Embeddings are required for semantic search and reindexing to work.
                </p>
              </div>
            )}

            {/* Option to use existing OpenAI key */}
            {completionsHasOpenAI && !isConfigured && (
              <div className="rounded-lg border bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                      Use existing OpenAI key?
                    </p>
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                      Your completions config uses OpenAI. You can reuse that API key.
                    </p>
                  </div>
                  <Button
                    variant={useExistingKey ? "default" : "outline"}
                    size="sm"
                    onClick={() => {
                      setUseExistingKey(!useExistingKey);
                      if (!useExistingKey) {
                        form.setValue("api_key", "");
                      }
                    }}
                  >
                    {useExistingKey ? "Using existing key" : "Use existing key"}
                  </Button>
                </div>
              </div>
            )}

            {/* Configuration Form */}
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                {/* API Key (hidden if using existing) */}
                {!useExistingKey && (
                  <FormField
                    control={form.control}
                    name="api_key"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          OpenAI API Key
                          {isConfigured && (
                            <span className="text-muted-foreground font-normal ml-2">
                              (leave blank to keep existing)
                            </span>
                          )}
                        </FormLabel>
                        <FormControl>
                          <div className="flex gap-2">
                            <div className="relative flex-1">
                              <Input
                                type={showApiKey ? "text" : "password"}
                                placeholder="sk-..."
                                {...field}
                              />
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="absolute right-0 top-0 h-full px-3"
                                onClick={() => setShowApiKey(!showApiKey)}
                              >
                                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                              </Button>
                            </div>
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={onTestConnection}
                              disabled={!field.value}
                            >
                              {hasTestedSuccessfully ? (
                                <>
                                  <Check className="h-4 w-4 mr-2 text-green-600" />
                                  Verified
                                </>
                              ) : testResult?.success === false ? (
                                <>
                                  <X className="h-4 w-4 mr-2 text-destructive" />
                                  Failed
                                </>
                              ) : (
                                <>
                                  <Zap className="h-4 w-4 mr-2" />
                                  Test
                                </>
                              )}
                            </Button>
                          </div>
                        </FormControl>
                        <FormDescription>
                          Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">platform.openai.com</a>
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}

                {/* Test button when using existing key */}
                {useExistingKey && !hasTestedSuccessfully && (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={onTestConnection}
                    className="w-full"
                  >
                    <Zap className="h-4 w-4 mr-2" />
                    Verify existing key works for embeddings
                  </Button>
                )}

                {/* Test Result */}
                {testResult && !testResult.success && (
                  <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
                    <div className="flex items-center gap-2 text-sm text-destructive">
                      <X className="h-4 w-4" />
                      <span>{testResult.message}</span>
                    </div>
                  </div>
                )}

                {/* Model Selection (after successful test) */}
                {hasTestedSuccessfully && (
                  <>
                    <div className="rounded-lg border border-green-500/50 bg-green-50 dark:bg-green-950/20 p-3">
                      <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-300">
                        <Check className="h-4 w-4" />
                        <span>{testResult?.message}</span>
                      </div>
                    </div>

                    <FormField
                      control={form.control}
                      name="model"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Embeddings Model</FormLabel>
                          <FormControl>
                            <Combobox
                              options={
                                testResult?.models?.map((model) => ({
                                  value: model.id,
                                  label: model.name,
                                  description: model.description,
                                })) ?? []
                              }
                              value={field.value}
                              onValueChange={field.onChange}
                              placeholder="Select an embeddings model"
                              searchPlaceholder="Search models..."
                              emptyText="No model found."
                            />
                          </FormControl>
                          <FormDescription>
                            Used for semantic search and document indexing.
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <div className="flex justify-end">
                      <Button type="submit" disabled={!canSave || updateMutation.isPending}>
                        {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save
                      </Button>
                    </div>
                  </>
                )}

                {/* Hint */}
                {!hasTestedSuccessfully && !useExistingKey && form.getValues("api_key") && (
                  <p className="text-sm text-muted-foreground text-center">
                    Test your API key to see available models
                  </p>
                )}
              </form>
            </Form>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Indexing Configuration Section
// =============================================================================
function IndexingConfigSection() {
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useAISettings();

  const updateMutation = useMutation({
    mutationFn: (data: { enabled: boolean }) =>
      aiSettingsApi.updateIndexingConfig(data),
    onSuccess: () => {
      toast.success("Indexing configuration updated");
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
    },
    onError: () => {
      toast.error("Failed to update indexing configuration");
    },
  });

  const isEnabled = settings?.indexing?.enabled ?? false;

  function handleToggle(checked: boolean) {
    updateMutation.mutate({ enabled: checked });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Search Indexing
        </CardTitle>
        <CardDescription>
          Control whether entities are automatically indexed for semantic search when created or updated.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <>
            {/* Status Banner */}
            {isEnabled && (
              <div className="rounded-lg border bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900 p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium text-green-800 dark:text-green-200">
                    Automatic indexing is enabled
                  </span>
                </div>
                <p className="mt-1 text-sm text-green-700 dark:text-green-300">
                  Entities will be automatically indexed for semantic search when created or updated.
                </p>
              </div>
            )}

            {/* Toggle Control */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-0.5">
                <div className="font-medium">Enable automatic indexing</div>
                <div className="text-sm text-muted-foreground">
                  Index entities for semantic search when they are created or updated
                </div>
              </div>
              <Switch
                checked={isEnabled}
                onCheckedChange={handleToggle}
                disabled={updateMutation.isPending}
              />
            </div>

            {updateMutation.isPending && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Updating configuration...</span>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Index Stats Section
// =============================================================================
function IndexStatsSection() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["index-stats"],
    queryFn: () => adminApi.getIndexStats().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const totalEntities = stats?.total_entities ?? 0;
  const totalIndexed = stats?.total_indexed ?? 0;
  const totalUnindexed = stats?.total_unindexed ?? 0;
  const indexPercent = totalEntities > 0 ? Math.round((totalIndexed / totalEntities) * 100) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Search Index Statistics
        </CardTitle>
        <CardDescription>
          Overview of indexed entities for semantic search
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-4">
          <div className="p-4 bg-muted rounded-lg text-center">
            <p className="text-3xl font-bold">{totalEntities}</p>
            <p className="text-sm text-muted-foreground">Total Entities</p>
          </div>
          <div className="p-4 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900 rounded-lg text-center">
            <p className="text-3xl font-bold text-green-700 dark:text-green-300">{totalIndexed}</p>
            <p className="text-sm text-green-600 dark:text-green-400">Indexed</p>
          </div>
          <div className="p-4 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-lg text-center">
            <p className="text-3xl font-bold text-amber-700 dark:text-amber-300">{totalUnindexed}</p>
            <p className="text-sm text-amber-600 dark:text-amber-400">Unindexed</p>
          </div>
        </div>

        {/* Progress Bar */}
        {totalEntities > 0 && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Index Coverage</span>
              <span className="font-medium">{indexPercent}%</span>
            </div>
            <Progress value={indexPercent} />
          </div>
        )}

        {/* Last Indexed */}
        {stats?.last_indexed_at && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Last indexed {formatDateTime(stats.last_indexed_at)}</span>
          </div>
        )}

        {totalEntities === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No entities found.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Reindex Section with WebSocket Progress
// =============================================================================
interface ReindexState {
  isRunning: boolean;
  phase: string;
  current: number;
  total: number;
  errors: number;
  entityType: string | null;
  startedAt: string | null;
  completedAt: string | null;
  errorMessage: string | null;
  counts: Record<string, number> | null;
  durationSeconds: number | null;
}

function ReindexSection() {
  const queryClient = useQueryClient();
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const [wsState, setWsState] = useState<Partial<ReindexState> | null>(null);

  const { data: stats } = useQuery({
    queryKey: ["index-stats"],
    queryFn: () => adminApi.getIndexStats().then((r) => r.data),
  });

  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ["reindex-status"],
    queryFn: () => adminApi.getReindexStatus().then((r) => r.data),
    refetchInterval: false,
  });

  const reindexState: ReindexState = {
    isRunning: wsState?.isRunning ?? status?.is_running ?? false,
    phase: wsState?.phase ?? "",
    current: wsState?.current ?? status?.processed ?? 0,
    total: wsState?.total ?? status?.total ?? 0,
    errors: wsState?.errors ?? status?.errors ?? 0,
    entityType: wsState?.entityType ?? status?.current_entity_type ?? null,
    startedAt: wsState?.startedAt ?? status?.started_at ?? null,
    completedAt: wsState?.completedAt ?? status?.completed_at ?? null,
    errorMessage: wsState?.errorMessage ?? status?.error_message ?? null,
    counts: wsState?.counts ?? null,
    durationSeconds: wsState?.durationSeconds ?? null,
  };

  const handleReindexMessage = useCallback(
    (message: ReindexMessage) => {
      switch (message.type) {
        case "progress":
          setWsState((prev) => ({
            ...prev,
            isRunning: true,
            phase: message.phase,
            current: message.current,
            total: message.total,
            entityType: message.entity_type ?? prev?.entityType,
          }));
          break;

        case "completed":
          setWsState((prev) => ({
            ...prev,
            isRunning: false,
            completedAt: new Date().toISOString(),
            counts: message.counts,
            durationSeconds: message.duration_seconds ?? null,
            errorMessage: null,
          }));
          queryClient.invalidateQueries({ queryKey: ["index-stats"] });
          toast.success("Reindex completed successfully");
          if (unsubscribeRef.current) {
            unsubscribeRef.current();
            unsubscribeRef.current = null;
          }
          setCurrentJobId(null);
          break;

        case "failed":
          setWsState((prev) => ({
            ...prev,
            isRunning: false,
            completedAt: new Date().toISOString(),
            errorMessage: message.error,
          }));
          toast.error("Reindex failed", { description: message.error });
          if (unsubscribeRef.current) {
            unsubscribeRef.current();
            unsubscribeRef.current = null;
          }
          setCurrentJobId(null);
          break;

        case "cancelling":
          setWsState((prev) => ({
            ...prev,
            phase: "Cancelling...",
          }));
          break;

        case "cancelled":
          setWsState((prev) => ({
            ...prev,
            isRunning: false,
            completedAt: new Date().toISOString(),
            errorMessage: message.force ? "Force cancelled by user" : "Cancelled by user",
          }));
          toast.info("Reindex cancelled");
          if (unsubscribeRef.current) {
            unsubscribeRef.current();
            unsubscribeRef.current = null;
          }
          setCurrentJobId(null);
          break;
      }
    },
    [queryClient]
  );

  useEffect(() => {
    if (currentJobId) {
      webSocketService.connectToReindex(currentJobId).catch((error) => {
        console.error("[AISettings] WebSocket connection failed:", error);
        toast.error("Failed to connect for live progress updates. The reindex is still running in the background.");
      });

      unsubscribeRef.current = webSocketService.onReindexProgress(
        currentJobId,
        handleReindexMessage
      );
    }

    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
    };
  }, [currentJobId, handleReindexMessage]);

  const startReindexMutation = useMutation({
    mutationFn: (params?: { entity_type?: EntityType; organization_id?: string }) =>
      adminApi.startReindex(params).then((r) => r.data),
    onSuccess: (data) => {
      toast.success(data.message);
      setWsState({
        isRunning: true,
        phase: "Starting...",
        current: 0,
        total: 0,
        errors: 0,
        entityType: null,
        startedAt: new Date().toISOString(),
        completedAt: null,
        errorMessage: null,
        counts: null,
        durationSeconds: null,
      });
      setCurrentJobId(data.job_id);
      refetchStatus();
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || "Failed to start reindex");
    },
  });

  const cancelReindexMutation = useMutation({
    mutationFn: (force: boolean) => adminApi.cancelReindex(force).then((r) => r.data),
    onSuccess: (data) => {
      toast.success(data.message);
      if (data.status === "cancelled") {
        // Force cancel completed immediately
        setWsState((prev) => ({
          ...prev,
          isRunning: false,
          completedAt: new Date().toISOString(),
          errorMessage: "Cancelled by user",
        }));
        setCurrentJobId(null);
      }
      // For graceful cancel (status === "cancelling"), wait for WebSocket message
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      toast.error(axiosError.response?.data?.detail || "Failed to cancel reindex");
    },
  });

  function handleStartReindex() {
    startReindexMutation.mutate(undefined);
  }

  const progressPercent = reindexState.total > 0
    ? Math.round((reindexState.current / reindexState.total) * 100)
    : 0;

  const unindexedCount = stats?.total_unindexed ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5" />
          Reindex Search Data
        </CardTitle>
        <CardDescription>
          Index unindexed entities for semantic search. Already indexed entities will be skipped.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Reindex Button */}
        <div className="flex items-center gap-4">
          <Button
            onClick={handleStartReindex}
            disabled={reindexState.isRunning || startReindexMutation.isPending || unindexedCount === 0}
            className="w-full md:w-auto"
          >
            {(reindexState.isRunning || startReindexMutation.isPending) ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            {reindexState.isRunning ? "Reindexing..." : `Index ${unindexedCount} Unindexed Entities`}
          </Button>
          {unindexedCount === 0 && !reindexState.isRunning && (
            <span className="text-sm text-muted-foreground flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              All entities indexed
            </span>
          )}
        </div>

        <Separator />

        {/* Job Status */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium">Reindex Status</h4>

          {reindexState.isRunning ? (
            <div className="space-y-4 p-4 bg-muted rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="font-medium">
                    {reindexState.phase || "Reindexing in progress..."}
                  </span>
                </div>
                {reindexState.entityType && (
                  <Badge variant="outline">
                    {ENTITY_TYPE_LABELS[reindexState.entityType as EntityType] ??
                      reindexState.entityType}
                  </Badge>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Progress</span>
                  <span>
                    {reindexState.current} / {reindexState.total} ({progressPercent}%)
                  </span>
                </div>
                <Progress value={progressPercent} />
              </div>

              {reindexState.errors > 0 && (
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <XCircle className="h-4 w-4" />
                  <span>{reindexState.errors} errors encountered</span>
                </div>
              )}

              {reindexState.startedAt && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>Started {formatDateTime(reindexState.startedAt)}</span>
                </div>
              )}

              {/* Cancel Buttons */}
              <div className="flex gap-2 pt-2 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => cancelReindexMutation.mutate(false)}
                  disabled={cancelReindexMutation.isPending}
                >
                  {cancelReindexMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <XCircle className="mr-2 h-4 w-4" />
                  )}
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => cancelReindexMutation.mutate(true)}
                  disabled={cancelReindexMutation.isPending}
                >
                  Force Cancel
                </Button>
              </div>
            </div>
          ) : reindexState.completedAt ? (
            <div className="p-4 bg-muted rounded-lg space-y-3">
              <div className="flex items-center gap-2">
                {reindexState.errorMessage ? (
                  <>
                    <XCircle className="h-5 w-5 text-destructive" />
                    <span className="font-medium text-destructive">
                      Last reindex failed
                    </span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                    <span className="font-medium text-green-600">
                      Last reindex completed successfully
                    </span>
                  </>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Processed:</span>{" "}
                  <span className="font-medium">{reindexState.current}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Errors:</span>{" "}
                  <span className="font-medium">{reindexState.errors}</span>
                </div>
                {reindexState.startedAt && (
                  <div>
                    <span className="text-muted-foreground">Started:</span>{" "}
                    <span className="font-medium">
                      {formatDateTime(reindexState.startedAt)}
                    </span>
                  </div>
                )}
                {reindexState.completedAt && (
                  <div>
                    <span className="text-muted-foreground">Completed:</span>{" "}
                    <span className="font-medium">
                      {formatDateTime(reindexState.completedAt)}
                    </span>
                  </div>
                )}
                {reindexState.durationSeconds !== null && (
                  <div>
                    <span className="text-muted-foreground">Duration:</span>{" "}
                    <span className="font-medium">
                      {reindexState.durationSeconds.toFixed(1)}s
                    </span>
                  </div>
                )}
              </div>

              {reindexState.errorMessage && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded text-sm text-destructive">
                  {reindexState.errorMessage}
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 bg-muted rounded-lg text-center text-muted-foreground">
              <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No reindex job has been run yet.</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
