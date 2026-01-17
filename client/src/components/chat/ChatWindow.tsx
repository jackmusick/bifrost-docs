import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { MessageSquare, Loader2, AlertCircle, Send, FileText, Boxes } from "lucide-react";
import { FloatingWindow } from "@/components/ui/floating-window";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MarkdownRenderer } from "@/components/ui/markdown-renderer";
import { MutationPreview } from "./MutationPreview";
import { useChat, type ChatMessage, type ChatCitation } from "@/hooks/useChat";
import { useOrganizationStore } from "@/stores/organization.store";
import { getEntityIcon, getEntityRoute } from "@/lib/entity-icons";
import { cn } from "@/lib/utils";

interface ChatWindowProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialMessage?: string;
  currentEntityId?: string;
  currentEntityType?: "document" | "custom_asset";
}

type ChatScope = "org" | "global";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming: boolean;
  onCitationClick: (citation: ChatCitation) => void;
  conversationId: string | null;
  requestId: string | null;
}

function MessageBubble({
  message,
  isStreaming,
  onCitationClick,
  conversationId,
  requestId,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const showCursor = isStreaming && !isUser && !message.content;

  // Handle mutation pending state
  if (message.type === "mutation_pending") {
    return (
      <div className="flex flex-col gap-1 max-w-[85%] self-start items-start">
        <div className="rounded-lg px-4 py-3 bg-muted border border-border/50">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">
              Preparing action...
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Handle mutation error state
  if (message.type === "mutation_error") {
    return (
      <div className="flex flex-col gap-1 max-w-[85%] self-start items-start">
        <div className="rounded-lg px-4 py-3 bg-destructive/10 border border-destructive/20">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-destructive" />
            <span className="text-sm text-destructive">
              {message.errorMessage || "Unable to preview this action"}
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Handle mutation preview message
  if (message.type === "mutation_preview" && message.previewData) {
    return (
      <div className="flex flex-col gap-1 max-w-[85%] self-start items-start">
        <MutationPreview
          data={message.previewData as {
            entity_type: "document" | "custom_asset";
            entity_id: string;
            organization_id: string;
            mutation: {
              content?: string;
              field_updates?: Record<string, string>;
              summary: string;
            };
          }}
          conversationId={conversationId || ""}
          requestId={requestId || ""}
          onApply={(success, link) => {
            if (success && link) {
              console.log("Applied mutation:", link);
            }
          }}
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-1 max-w-[85%]",
        isUser ? "self-end items-end" : "self-start items-start"
      )}
    >
      <div
        className={cn(
          "rounded-lg px-3 py-2 text-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.content ? (
          isStreaming ? (
            // Show plain text while streaming to avoid partial markdown parsing issues
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <MarkdownRenderer
              content={message.content}
              className="prose-sm prose-p:my-1 prose-headings:mt-2 prose-headings:mb-1"
            />
          )
        ) : showCursor ? (
          <span className="inline-block w-2 h-4 bg-foreground/60 animate-pulse" />
        ) : null}
      </div>

      {/* Citations */}
      {!isUser && message.citations && message.citations.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {message.citations.map((citation, idx) => {
            const Icon = getEntityIcon(citation.entity_type);
            return (
              <Button
                key={`${citation.entity_id}-${idx}`}
                variant="outline"
                size="sm"
                className="h-6 px-2 text-xs gap-1"
                onClick={() => onCitationClick(citation)}
              >
                <Icon className="h-3 w-3" />
                <span className="max-w-[120px] truncate">{citation.name}</span>
              </Button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function ChatWindow({
  open,
  onOpenChange,
  initialMessage,
  currentEntityId,
  currentEntityType,
}: ChatWindowProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentOrg } = useOrganizationStore();

  // Check if we're on global view
  const isGlobalView = location.pathname.startsWith("/global");

  const [scope, setScope] = useState<ChatScope>(isGlobalView ? "global" : "org");
  const [input, setInput] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialMessageSentRef = useRef(false);
  const prevEntityIdRef = useRef<string | undefined>(currentEntityId);

  // Initialize chat with org context based on scope
  const orgId = scope === "org" ? currentOrg?.id : undefined;
  const {
    messages,
    isLoading,
    isStreaming,
    error,
    sendMessage,
    reset,
    conversationId,
    requestId,
  } = useChat({ orgId, currentEntityId, currentEntityType });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus textarea when opening
  useEffect(() => {
    if (open) {
      // Small delay to allow the window to render
      const timer = setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [open]);

  // Send initial message if provided
  useEffect(() => {
    if (open && initialMessage && !initialMessageSentRef.current) {
      initialMessageSentRef.current = true;
      sendMessage(initialMessage);
    }
  }, [open, initialMessage, sendMessage]);

  // Sync scope when view changes (e.g., user navigates from org to global)
  useEffect(() => {
    setScope(isGlobalView ? "global" : "org");
  }, [isGlobalView]);

  // Track entity changes but don't auto-reset
  // The backend handles context freshness - conversation can continue across navigation
  useEffect(() => {
    prevEntityIdRef.current = currentEntityId;
  }, [currentEntityId]);

  // Reset on close
  const handleOpenChange = useCallback(
    (newOpen: boolean) => {
      if (!newOpen) {
        // Delay reset to avoid visual flash
        setTimeout(() => {
          reset();
          setInput("");
          initialMessageSentRef.current = false;
        }, 200);
      }
      onOpenChange(newOpen);
    },
    [onOpenChange, reset]
  );

  // Handle send
  const handleSend = useCallback(() => {
    if (!input.trim() || isLoading || isStreaming) return;
    sendMessage(input.trim());
    setInput("");
  }, [input, isLoading, isStreaming, sendMessage]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // Handle citation click - navigate to entity and close chat
  const handleCitationClick = useCallback(
    (citation: ChatCitation) => {
      const route = getEntityRoute(citation.entity_type);
      navigate(
        `/org/${citation.organization_id}/${route}/${citation.entity_id}`
      );
      handleOpenChange(false);
    },
    [navigate, handleOpenChange]
  );

  // Scope selector for header
  const scopeSelector = (
    <Select
      value={scope}
      onValueChange={(value) => setScope(value as ChatScope)}
    >
      <SelectTrigger className="h-7 w-auto min-w-[140px] text-xs">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="org">
          {currentOrg?.name || "Current Organization"}
        </SelectItem>
        <SelectItem value="global">All Organizations</SelectItem>
      </SelectContent>
    </Select>
  );

  return (
    <FloatingWindow
      open={open}
      onOpenChange={handleOpenChange}
      title={
        <span className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Chat
        </span>
      }
      headerExtra={scopeSelector}
      defaultSize={{ width: 420, height: 550 }}
      minSize={{ width: 320, height: 400 }}
    >
      <div className="flex flex-col h-full">
        {/* Context indicator */}
        {currentEntityId && currentEntityType && (
          <div className="px-3 py-2 bg-primary/5 border-b border-border/50">
            <div className="flex items-center gap-2 text-xs">
              {currentEntityType === "document" ? (
                <FileText className="h-3 w-3 text-primary" />
              ) : (
                <Boxes className="h-3 w-3 text-primary" />
              )}
              <span className="text-muted-foreground">
                {currentEntityType === "document"
                  ? "Viewing current document"
                  : "Viewing current asset"}
              </span>
            </div>
          </div>
        )}

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <MessageSquare className="h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">Start a conversation</p>
              <p className="text-xs mt-1">
                Ask questions about your documentation
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                isStreaming={isStreaming}
                onCitationClick={handleCitationClick}
                conversationId={conversationId}
                requestId={requestId}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Error display */}
        {error && (
          <div className="mx-3 mb-2 p-2 bg-destructive/10 text-destructive text-sm rounded-md flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="truncate">{error}</span>
          </div>
        )}

        {/* Input area */}
        <div className="p-3 border-t bg-background">
          <div className="flex gap-2">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question..."
              className="min-h-[40px] max-h-[120px] resize-none text-sm"
              disabled={isLoading || isStreaming}
              rows={1}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isLoading || isStreaming}
              size="icon"
              className="shrink-0"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              <span className="sr-only">Send message</span>
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Press Enter to send, Shift+Enter for newline
          </p>
        </div>
      </div>
    </FloatingWindow>
  );
}
