# Search & Chat Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split search into two interfaces: a quick-lookup search modal with rich document preview, and a separate floating chat window for AI-powered conversational exploration.

**Architecture:** The search modal (CMD+K) shows results with a live preview pane. A separate floating chat window handles AI conversations with session-only persistence. Shift+Enter bridges search to chat by pre-filling and auto-sending the query.

**Tech Stack:** React, TypeScript, TanStack Query, WebSocket streaming, FastAPI, shadcn/ui components

---

## Task 1: Create FloatingWindow UI Component

Create a reusable floating window component with drag and resize capabilities.

**Files:**
- Create: `client/src/components/ui/floating-window.tsx`

**Step 1: Create the floating window component**

```tsx
import { useState, useRef, useCallback, useEffect } from "react";
import { X, GripVertical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FloatingWindowProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: React.ReactNode;
  children: React.ReactNode;
  defaultPosition?: { x: number; y: number };
  defaultSize?: { width: number; height: number };
  minSize?: { width: number; height: number };
  className?: string;
  headerExtra?: React.ReactNode;
}

interface Position {
  x: number;
  y: number;
}

interface Size {
  width: number;
  height: number;
}

export function FloatingWindow({
  open,
  onOpenChange,
  title,
  children,
  defaultPosition = { x: window.innerWidth - 450, y: window.innerHeight - 650 },
  defaultSize = { width: 420, height: 550 },
  minSize = { width: 320, height: 400 },
  className,
  headerExtra,
}: FloatingWindowProps) {
  const [position, setPosition] = useState<Position>(defaultPosition);
  const [size, setSize] = useState<Size>(defaultSize);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const windowRef = useRef<HTMLDivElement>(null);
  const dragOffset = useRef<Position>({ x: 0, y: 0 });

  // Constrain position to viewport
  const constrainPosition = useCallback(
    (pos: Position, currentSize: Size): Position => {
      const maxX = window.innerWidth - currentSize.width;
      const maxY = window.innerHeight - currentSize.height;
      return {
        x: Math.max(0, Math.min(pos.x, maxX)),
        y: Math.max(0, Math.min(pos.y, maxY)),
      };
    },
    []
  );

  // Handle drag start
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest("button")) return;
    setIsDragging(true);
    dragOffset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
  }, [position]);

  // Handle drag
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newPos = {
        x: e.clientX - dragOffset.current.x,
        y: e.clientY - dragOffset.current.y,
      };
      setPosition(constrainPosition(newPos, size));
    };

    const handleMouseUp = () => setIsDragging(false);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, size, constrainPosition]);

  // Handle resize
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = Math.max(minSize.width, e.clientX - position.x);
      const newHeight = Math.max(minSize.height, e.clientY - position.y);
      setSize({ width: newWidth, height: newHeight });
    };

    const handleMouseUp = () => setIsResizing(false);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing, position, minSize]);

  // Handle escape key
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div
      ref={windowRef}
      className={cn(
        "fixed z-50 flex flex-col bg-card border rounded-lg shadow-2xl",
        isDragging && "cursor-grabbing select-none",
        className
      )}
      style={{
        left: position.x,
        top: position.y,
        width: size.width,
        height: size.height,
      }}
    >
      {/* Header - draggable */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b bg-muted/50 rounded-t-lg cursor-grab shrink-0"
        onMouseDown={handleDragStart}
      >
        <div className="flex items-center gap-2">
          <GripVertical className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium text-sm">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          {headerExtra}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onOpenChange(false)}
            className="h-7 w-7"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">{children}</div>

      {/* Resize handle */}
      <div
        className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize"
        onMouseDown={handleResizeStart}
      >
        <svg
          className="w-4 h-4 text-muted-foreground/50"
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path d="M14 14H12V12H14V14ZM14 10H12V8H14V10ZM10 14H8V12H10V14Z" />
        </svg>
      </div>
    </div>
  );
}
```

**Step 2: Run type check**

Run: `cd /Users/jack/GitHub/gocovi-docs/client && npm run tsc`
Expected: PASS with no errors related to floating-window.tsx

**Step 3: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add client/src/components/ui/floating-window.tsx
git commit -m "feat: add FloatingWindow UI component

Reusable draggable/resizable floating window for chat interface."
```

---

## Task 2: Create Chat Hook for Conversation State

Create a hook to manage chat conversation state and streaming.

**Files:**
- Create: `client/src/hooks/useChat.ts`

**Step 1: Create the chat hook**

```tsx
import { useState, useCallback, useRef, useEffect } from "react";
import api from "@/lib/api-client";
import { webSocketService, type SearchChunk } from "@/services/websocket";
import type { EntityType } from "@/lib/entity-icons";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  citations?: ChatCitation[];
}

export interface ChatCitation {
  entity_type: EntityType;
  entity_id: string;
  organization_id: string;
  name: string;
}

interface ChatStartResponse {
  request_id: string;
  conversation_id: string;
}

interface UseChatOptions {
  orgId?: string;
}

export function useChat(options: UseChatOptions = {}) {
  const { orgId } = options;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const conversationIdRef = useRef<string | null>(null);
  const requestIdRef = useRef<string | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const pendingContentRef = useRef<string>("");
  const pendingCitationsRef = useRef<ChatCitation[]>([]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, []);

  const handleChunk = useCallback((chunk: SearchChunk) => {
    switch (chunk.type) {
      case "citations":
        if (chunk.data) {
          pendingCitationsRef.current = chunk.data as ChatCitation[];
        }
        break;

      case "delta":
        pendingContentRef.current += chunk.content || "";
        // Update the last message with new content
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage?.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...lastMessage, content: pendingContentRef.current },
            ];
          }
          return prev;
        });
        break;

      case "done":
        // Finalize the message with citations
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage?.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              {
                ...lastMessage,
                content: pendingContentRef.current,
                citations: pendingCitationsRef.current,
              },
            ];
          }
          return prev;
        });
        setIsStreaming(false);
        pendingContentRef.current = "";
        pendingCitationsRef.current = [];
        break;

      case "error":
        setError(chunk.message || "An error occurred");
        setIsStreaming(false);
        break;
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      // Cleanup previous subscription
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }

      // Add user message
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim(),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Add placeholder assistant message
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      setIsLoading(true);
      setError(null);
      pendingContentRef.current = "";
      pendingCitationsRef.current = [];

      try {
        // Get conversation history for context (excluding the placeholder)
        const history = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        // Start the chat request
        const response = await api.post<ChatStartResponse>("/api/chat", {
          message: content.trim(),
          conversation_id: conversationIdRef.current,
          history,
          ...(orgId ? { org_id: orgId } : {}),
        });

        const { request_id, conversation_id } = response.data;
        requestIdRef.current = request_id;
        conversationIdRef.current = conversation_id;

        // Connect to WebSocket and subscribe
        await webSocketService.connectToSearch(request_id);
        unsubscribeRef.current = webSocketService.onSearchChunk(
          request_id,
          handleChunk
        );

        setIsLoading(false);
        setIsStreaming(true);
      } catch (err) {
        setIsLoading(false);
        setIsStreaming(false);
        setError((err as Error).message || "Failed to send message");
        // Remove the placeholder assistant message on error
        setMessages((prev) => prev.slice(0, -1));
      }
    },
    [messages, orgId, handleChunk]
  );

  const reset = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
    if (requestIdRef.current) {
      webSocketService.unsubscribe(`search:${requestIdRef.current}`);
    }
    setMessages([]);
    setIsLoading(false);
    setIsStreaming(false);
    setError(null);
    conversationIdRef.current = null;
    requestIdRef.current = null;
    pendingContentRef.current = "";
    pendingCitationsRef.current = [];
  }, []);

  return {
    messages,
    isLoading,
    isStreaming,
    error,
    sendMessage,
    reset,
  };
}
```

**Step 2: Run type check**

Run: `cd /Users/jack/GitHub/gocovi-docs/client && npm run tsc`
Expected: PASS with no errors related to useChat.ts

**Step 3: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add client/src/hooks/useChat.ts
git commit -m "feat: add useChat hook for conversation state

Manages chat messages, streaming responses, and conversation history."
```

---

## Task 3: Create Chat Window Component

Create the main chat window using FloatingWindow and useChat.

**Files:**
- Create: `client/src/components/chat/ChatWindow.tsx`

**Step 1: Create the chat window component**

```tsx
import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquare, Loader2, AlertCircle, Send } from "lucide-react";
import { FloatingWindow } from "@/components/ui/floating-window";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MarkdownRenderer } from "@/components/ui/markdown-renderer";
import { useChat, type ChatMessage, type ChatCitation } from "@/hooks/useChat";
import { useOrganizationStore } from "@/stores/organization.store";
import { getEntityIcon, getEntityRoute } from "@/lib/entity-icons";
import { cn } from "@/lib/utils";

interface ChatWindowProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialMessage?: string;
}

export function ChatWindow({ open, onOpenChange, initialMessage }: ChatWindowProps) {
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [scope, setScope] = useState<"org" | "global">("org");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialMessageSentRef = useRef(false);

  const currentOrg = useOrganizationStore((state) => state.currentOrg);
  const effectiveOrgId = currentOrg && scope === "org" ? currentOrg.id : undefined;

  const { messages, isLoading, isStreaming, error, sendMessage, reset } = useChat({
    orgId: effectiveOrgId,
  });

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Reset when closing
  useEffect(() => {
    if (!open) {
      const timer = setTimeout(() => {
        reset();
        setInput("");
        setScope("org");
        initialMessageSentRef.current = false;
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [open, reset]);

  // Send initial message if provided
  useEffect(() => {
    if (open && initialMessage && !initialMessageSentRef.current) {
      initialMessageSentRef.current = true;
      sendMessage(initialMessage);
    }
  }, [open, initialMessage, sendMessage]);

  // Focus textarea when opening
  useEffect(() => {
    if (open && !initialMessage) {
      textareaRef.current?.focus();
    }
  }, [open, initialMessage]);

  const handleSubmit = useCallback(() => {
    if (!input.trim() || isLoading || isStreaming) return;
    sendMessage(input);
    setInput("");
  }, [input, isLoading, isStreaming, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleCitationClick = useCallback(
    (citation: ChatCitation) => {
      const route = getEntityRoute(citation.entity_type);
      navigate(`/org/${citation.organization_id}/${route}/${citation.entity_id}`);
      onOpenChange(false);
    },
    [navigate, onOpenChange]
  );

  const headerExtra = currentOrg ? (
    <Select value={scope} onValueChange={(v) => setScope(v as "org" | "global")}>
      <SelectTrigger className="h-7 w-[140px] text-xs">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="org">{currentOrg.name}</SelectItem>
        <SelectItem value="global">All Organizations</SelectItem>
      </SelectContent>
    </Select>
  ) : null;

  return (
    <FloatingWindow
      open={open}
      onOpenChange={onOpenChange}
      title={
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-primary" />
          <span>Chat</span>
        </div>
      }
      headerExtra={headerExtra}
    >
      <div className="flex flex-col h-full">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
          {messages.length === 0 && !isLoading && (
            <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
              <MessageSquare className="h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">Ask me anything about your documentation.</p>
              <p className="text-xs mt-1">I can help find and synthesize information.</p>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              isStreaming={isStreaming && message === messages[messages.length - 1]}
              onCitationClick={handleCitationClick}
            />
          ))}

          {error && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="shrink-0 border-t px-3 py-2">
          <div className="flex items-end gap-2">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              rows={1}
              className="flex-1 min-h-[36px] max-h-[120px] resize-none text-sm"
              disabled={isLoading || isStreaming}
            />
            <Button
              onClick={handleSubmit}
              disabled={!input.trim() || isLoading || isStreaming}
              size="icon"
              className="h-9 w-9 shrink-0"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </FloatingWindow>
  );
}

// Message bubble component
interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming: boolean;
  onCitationClick: (citation: ChatCitation) => void;
}

function MessageBubble({ message, isStreaming, onCitationClick }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex flex-col gap-1", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "rounded-lg px-3 py-2 max-w-[85%]",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        )}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownRenderer content={message.content} />
            {isStreaming && (
              <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-0.5" />
            )}
          </div>
        )}
      </div>

      {/* Citations */}
      {message.citations && message.citations.length > 0 && !isStreaming && (
        <div className="flex flex-wrap gap-1 max-w-[85%]">
          {message.citations.map((citation, idx) => {
            const Icon = getEntityIcon(citation.entity_type);
            return (
              <button
                key={`${citation.entity_id}-${idx}`}
                onClick={() => onCitationClick(citation)}
                className="inline-flex items-center gap-1 rounded-md border bg-muted/50 px-2 py-1 text-xs hover:bg-muted transition-colors"
              >
                <Icon className="h-3 w-3 text-muted-foreground" />
                <span className="truncate max-w-[150px]">{citation.name}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Run type check**

Run: `cd /Users/jack/GitHub/gocovi-docs/client && npm run tsc`
Expected: PASS with no errors related to ChatWindow.tsx

**Step 3: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add client/src/components/chat/ChatWindow.tsx
git commit -m "feat: add ChatWindow component

Floating chat window with streaming AI responses and inline citations."
```

---

## Task 4: Create Chat Backend Endpoint

Add a new chat endpoint that handles conversational context.

**Files:**
- Create: `api/src/models/contracts/chat.py`
- Modify: `api/src/routers/search.py` (add chat endpoint)

**Step 1: Create chat contracts**

```python
# api/src/models/contracts/chat.py
"""Chat request/response contracts."""

from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_id: str | None = Field(None, description="Existing conversation ID")
    history: list[ChatMessage] = Field(
        default_factory=list, description="Previous messages for context"
    )
    org_id: UUID | None = Field(None, description="Filter to specific organization")


class ChatStartResponse(BaseModel):
    """Response when starting a chat."""

    request_id: str = Field(..., description="WebSocket channel ID for streaming")
    conversation_id: str = Field(..., description="Conversation ID for follow-ups")
```

**Step 2: Add chat endpoint to search router**

Add to `api/src/routers/search.py` after the ai_search endpoint:

```python
# Add import at top
from src.models.contracts.chat import ChatRequest, ChatStartResponse

# Add after _send_empty_ai_response function

async def _perform_chat(
    request_id: str,
    message: str,
    history: list[dict],
    org_ids: list[UUID],
) -> None:
    """
    Background task to perform chat and stream results via WebSocket.

    Similar to _perform_ai_search but includes conversation history.
    """
    await asyncio.sleep(0.5)

    try:
        async with get_db_context() as db:
            embeddings_service = get_embeddings_service(db)

            try:
                # Search using the current message for context
                search_results = await embeddings_service.search(
                    db, message, org_ids, limit=30
                )
            except Exception as e:
                logger.error(f"Search for chat context failed: {e}", exc_info=True)
                await publish_search_error(request_id, "Failed to retrieve search context")
                return

            # Build and publish citations
            citations = [
                {
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "organization_id": r.organization_id,
                    "name": r.name,
                }
                for r in search_results[:10]
            ]
            await publish_search_citations(request_id, citations)

            # Stream the chat response with history context
            from src.services.ai_chat import get_conversational_chat_service

            chat_service = get_conversational_chat_service(db)

            try:
                async for chunk in chat_service.stream_response(
                    message, search_results, history
                ):
                    await publish_search_delta(request_id, chunk)
                    await asyncio.sleep(0.01)

                await publish_search_done(request_id)

            except ValueError as e:
                logger.warning(f"Chat failed: {e}")
                await publish_search_error(request_id, str(e))
            except Exception as e:
                logger.error(f"Chat stream error: {e}", exc_info=True)
                error_msg = str(e) if str(e) else "An error occurred"
                await publish_search_error(request_id, error_msg)

    except Exception as e:
        logger.error(f"Chat background task failed: {e}", exc_info=True)
        await publish_search_error(request_id, "Chat failed unexpectedly")


@router.post("/chat", response_model=ChatStartResponse)
async def chat(
    request: ChatRequest,
    current_user: CurrentActiveUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ChatStartResponse:
    """
    Conversational chat with RAG context.

    Similar to ai_search but maintains conversation history for context.
    Returns request_id for WebSocket streaming.
    """
    completions_config = await get_completions_config(db)

    if not completions_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat is not available - LLM API key not configured",
        )

    org_repo = OrganizationRepository(db)

    if request.org_id:
        org = await org_repo.get_by_id(request.org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        org_ids = [request.org_id]
    else:
        orgs = await org_repo.get_all()
        org_ids = [org.id for org in orgs]

    request_id = str(uuid4())
    conversation_id = request.conversation_id or str(uuid4())

    # Convert history to dict format
    history = [{"role": m.role, "content": m.content} for m in request.history]

    if org_ids:
        background_tasks.add_task(
            _perform_chat, request_id, request.message, history, org_ids
        )
    else:
        background_tasks.add_task(_send_empty_ai_response, request_id)

    logger.info(
        f"Chat started: request_id={request_id}, conversation_id={conversation_id}",
        extra={"user_id": str(current_user.user_id)},
    )

    return ChatStartResponse(request_id=request_id, conversation_id=conversation_id)
```

**Step 3: Add conversational chat service function**

Add to `api/src/services/ai_chat.py`:

```python
# Add to ai_chat.py after AIChatService class

CONVERSATIONAL_SYSTEM_PROMPT = """You are a helpful assistant for an IT documentation platform.
You help users find and understand information about their documentation.

When answering questions:
1. Base your answers on the provided context from search results
2. Reference specific documents by name so users can navigate to them
3. Use inline links when referencing documents: [Document Name]
4. If context doesn't contain relevant information, say so clearly
5. Be conversational and helpful - you can ask clarifying questions
6. If asked about passwords, mention what exists but NEVER reveal actual values

Format your responses in clear, readable markdown."""


class ConversationalChatService:
    """Chat service with conversation history support."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def stream_response(
        self,
        message: str,
        search_results: list[SearchResult],
        history: list[dict],
        *,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream a response with conversation context."""
        config = await get_completions_config(self.db)
        if not config:
            raise ValueError("LLM is not configured")

        client = get_llm_client(config)
        context = build_context_from_results(search_results)

        # Build messages with history
        messages = [LLMMessage(role=Role.SYSTEM, content=CONVERSATIONAL_SYSTEM_PROMPT)]

        # Add conversation history
        for msg in history[-10:]:  # Last 10 messages for context
            role = Role.USER if msg["role"] == "user" else Role.ASSISTANT
            messages.append(LLMMessage(role=role, content=msg["content"]))

        # Add current message with context
        user_message = f"""Based on the following context, please answer my question.

**Context from knowledge base:**
{context}

**My question:** {message}"""

        messages.append(LLMMessage(role=Role.USER, content=user_message))

        try:
            async for chunk in client.stream(messages, max_tokens=max_tokens):
                if chunk.type == "delta" and chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Error streaming chat response: {e}", exc_info=True)
            raise


def get_conversational_chat_service(db: AsyncSession) -> ConversationalChatService:
    """Create a conversational chat service instance."""
    return ConversationalChatService(db)
```

**Step 4: Run type check**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pyright`
Expected: PASS with no errors

**Step 5: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add api/src/models/contracts/chat.py api/src/routers/search.py api/src/services/ai_chat.py
git commit -m "feat: add chat endpoint with conversation history

New /api/chat endpoint that maintains conversation context for follow-up questions."
```

---

## Task 5: Add Rich Preview to Search Modal

Modify the search modal to show a rich document preview pane.

**Files:**
- Create: `client/src/hooks/useEntityPreview.ts`
- Modify: `client/src/components/search/CommandPalette.tsx`

**Step 1: Create entity preview hook**

```tsx
// client/src/hooks/useEntityPreview.ts
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import type { EntityType } from "@/lib/entity-icons";

interface EntityPreviewData {
  id: string;
  name: string;
  content: string;
  entity_type: EntityType;
  organization_id: string;
  organization_name: string;
}

export function useEntityPreview(
  entityType: EntityType | null,
  entityId: string | null,
  organizationId: string | null
) {
  return useQuery({
    queryKey: ["entity-preview", entityType, entityId],
    queryFn: async () => {
      if (!entityType || !entityId || !organizationId) return null;

      // Map entity type to API endpoint
      const endpointMap: Record<EntityType, string> = {
        password: "passwords",
        configuration: "configurations",
        location: "locations",
        document: "documents",
        custom_asset: "custom-assets",
      };

      const endpoint = endpointMap[entityType];
      if (!endpoint) return null;

      const response = await api.get<EntityPreviewData>(
        `/api/org/${organizationId}/${endpoint}/${entityId}/preview`
      );
      return response.data;
    },
    enabled: !!entityType && !!entityId && !!organizationId,
    staleTime: 60000, // Cache for 1 minute
  });
}
```

**Step 2: Create SearchPreview component**

Create `client/src/components/search/SearchPreview.tsx`:

```tsx
import { Loader2 } from "lucide-react";
import { MarkdownRenderer } from "@/components/ui/markdown-renderer";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { useEntityPreview } from "@/hooks/useEntityPreview";
import { getEntityIcon, getEntityLabel, type EntityType } from "@/lib/entity-icons";
import { cn } from "@/lib/utils";

interface SearchPreviewProps {
  entityType: EntityType | null;
  entityId: string | null;
  organizationId: string | null;
  highlightQuery?: string;
  className?: string;
}

export function SearchPreview({
  entityType,
  entityId,
  organizationId,
  highlightQuery,
  className,
}: SearchPreviewProps) {
  const { data, isLoading, error } = useEntityPreview(
    entityType,
    entityId,
    organizationId
  );

  if (!entityType || !entityId) {
    return (
      <div className={cn("flex items-center justify-center text-muted-foreground text-sm", className)}>
        Select a result to preview
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={cn("flex items-center justify-center", className)}>
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={cn("flex items-center justify-center text-muted-foreground text-sm", className)}>
        Preview not available
      </div>
    );
  }

  const Icon = getEntityIcon(entityType);
  const typeLabel = getEntityLabel(entityType);

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Preview header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b shrink-0">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <span className="font-medium text-sm truncate flex-1">{data.name}</span>
        <Badge variant="outline" className="shrink-0">
          {typeLabel}
        </Badge>
      </div>

      {/* Preview content */}
      <ScrollArea className="flex-1">
        <div className="p-3">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownRenderer
              content={data.content}
              highlightText={highlightQuery}
            />
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
```

**Step 3: Update CommandPalette to include preview pane**

Modify `client/src/components/search/CommandPalette.tsx`:

Replace the main content area (inside `CommandDialog`) with:

```tsx
// Add import at top
import { SearchPreview } from "./SearchPreview";

// Add state for selected result (after existing state)
const [selectedResult, setSelectedResult] = useState<{
  entityType: EntityType | null;
  entityId: string | null;
  organizationId: string | null;
} | null>(null);

// Update the main content area (replace the flex div with h-[440px])
<div className="flex flex-col h-[500px] overflow-hidden">
  {/* Results list - 40% height */}
  <div className="h-[40%] border-b overflow-hidden">
    <CommandList className="h-full max-h-full">
      {showHint && (
        <div className="py-6 text-center text-sm text-muted-foreground">
          Type at least 2 characters to search
        </div>
      )}

      {showLoading && (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Searching...</span>
        </div>
      )}

      {showEmpty && (
        <CommandEmpty>No results found for "{debouncedQuery}"</CommandEmpty>
      )}

      {showResults && (
        <SearchResults
          groupedResults={groupedResults}
          onSelect={handleClose}
          onHover={(result) =>
            setSelectedResult({
              entityType: result.entity_type,
              entityId: result.entity_id,
              organizationId: result.organization_id,
            })
          }
          highlightQuery={debouncedQuery}
        />
      )}
    </CommandList>
  </div>

  {/* Preview pane - 60% height */}
  <div className="h-[60%] overflow-hidden bg-muted/30">
    <SearchPreview
      entityType={selectedResult?.entityType ?? null}
      entityId={selectedResult?.entityId ?? null}
      organizationId={selectedResult?.organizationId ?? null}
      highlightQuery={debouncedQuery}
      className="h-full"
    />
  </div>
</div>
```

**Step 4: Update SearchResults to support hover**

Modify `client/src/components/search/SearchResults.tsx` to add onHover prop:

```tsx
// Add to props interface
onHover?: (result: SearchResult) => void;

// Update CommandItem to call onHover
<CommandItem
  key={result.entity_id}
  value={`${result.organization_name}-${result.entity_type}-${result.name}`}
  onSelect={() => {
    navigate(`/org/${result.organization_id}/${route}/${result.entity_id}`);
    onSelect?.();
  }}
  onMouseEnter={() => onHover?.(result)}
  onFocus={() => onHover?.(result)}
  className="flex items-center gap-2 py-2"
>
```

**Step 5: Remove AI panel code from CommandPalette**

Remove the entire right column AI panel section and the AIPanel component since chat is now separate.

**Step 6: Run type check**

Run: `cd /Users/jack/GitHub/gocovi-docs/client && npm run tsc`
Expected: PASS

**Step 7: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add client/src/hooks/useEntityPreview.ts client/src/components/search/SearchPreview.tsx client/src/components/search/CommandPalette.tsx client/src/components/search/SearchResults.tsx
git commit -m "feat: add rich preview pane to search modal

Shows full document content when hovering/selecting results. Removes AI panel."
```

---

## Task 6: Add Preview API Endpoints

Add preview endpoints for each entity type.

**Files:**
- Modify: `api/src/routers/passwords.py`
- Modify: `api/src/routers/configurations.py`
- Modify: `api/src/routers/locations.py`
- Modify: `api/src/routers/documents.py`

**Step 1: Add preview endpoint to passwords router**

Add to `api/src/routers/passwords.py`:

```python
@router.get("/{password_id}/preview")
async def get_password_preview(
    org_id: UUID,
    password_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> dict:
    """Get password preview for search (no actual password value)."""
    repo = PasswordRepository(db)
    password = await repo.get_by_id(password_id, org_id)

    if not password:
        raise HTTPException(status_code=404, detail="Password not found")

    # Build preview content without actual password
    content_parts = [f"# {password.name}"]
    if password.username:
        content_parts.append(f"\n**Username:** {password.username}")
    if password.url:
        content_parts.append(f"\n**URL:** {password.url}")
    if password.notes:
        content_parts.append(f"\n## Notes\n{password.notes}")

    return {
        "id": str(password.id),
        "name": password.name,
        "content": "\n".join(content_parts),
        "entity_type": "password",
        "organization_id": str(org_id),
    }
```

**Step 2: Add preview endpoint to documents router**

Add to `api/src/routers/documents.py`:

```python
@router.get("/{document_id}/preview")
async def get_document_preview(
    org_id: UUID,
    document_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> dict:
    """Get document preview for search."""
    repo = DocumentRepository(db)
    document = await repo.get_by_id(document_id, org_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": str(document.id),
        "name": document.name,
        "content": document.content or "",
        "entity_type": "document",
        "organization_id": str(org_id),
    }
```

**Step 3: Add preview endpoints to configurations and locations routers**

Similar pattern for configurations and locations.

**Step 4: Run type check**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pyright`
Expected: PASS

**Step 5: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add api/src/routers/passwords.py api/src/routers/documents.py api/src/routers/configurations.py api/src/routers/locations.py
git commit -m "feat: add preview endpoints for search

New /preview endpoints return formatted content for each entity type."
```

---

## Task 7: Add Chat Button to Header and Wire Up Integration

Add chat button to header and connect Shift+Enter bridge.

**Files:**
- Modify: `client/src/components/layout/Header.tsx`
- Modify: `client/src/components/layout/AppLayout.tsx`

**Step 1: Add chat state to AppLayout**

```tsx
// In AppLayout.tsx, add state and handler
const [chatOpen, setChatOpen] = useState(false);
const [chatInitialMessage, setChatInitialMessage] = useState<string | undefined>();

const handleOpenChatWithMessage = useCallback((message: string) => {
  setChatInitialMessage(message);
  setChatOpen(true);
}, []);

// Add ChatWindow to render
<ChatWindow
  open={chatOpen}
  onOpenChange={(open) => {
    setChatOpen(open);
    if (!open) setChatInitialMessage(undefined);
  }}
  initialMessage={chatInitialMessage}
/>
```

**Step 2: Add chat button to Header**

```tsx
// Add to Header.tsx
import { MessageSquare } from "lucide-react";

// Add chat button next to search button
<Button
  variant="ghost"
  size="icon"
  onClick={() => onChatClick?.()}
  className="h-9 w-9"
>
  <MessageSquare className="h-5 w-5" />
</Button>
```

**Step 3: Update CommandPalette Shift+Enter to bridge to chat**

```tsx
// Modify the Shift+Enter handler in CommandPalette
const handleAskAI = useCallback(() => {
  if (query.length >= 2) {
    // Close search and open chat with query
    handleClose();
    onOpenChat?.(query);
  }
}, [query, handleClose, onOpenChat]);
```

**Step 4: Run type check and lint**

Run: `cd /Users/jack/GitHub/gocovi-docs/client && npm run tsc && npm run lint`
Expected: PASS

**Step 5: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add client/src/components/layout/Header.tsx client/src/components/layout/AppLayout.tsx client/src/components/search/CommandPalette.tsx
git commit -m "feat: integrate chat window with header and search

Add chat icon to header. Shift+Enter in search opens chat with query."
```

---

## Task 8: Update MarkdownRenderer to Handle Entity Links

Update the markdown renderer to convert entity links to clickable navigation.

**Files:**
- Modify: `client/src/components/ui/markdown-renderer.tsx`

**Step 1: Add entity link handling**

```tsx
// Add custom link component that handles entity:// URLs
const components = {
  a: ({ href, children, ...props }) => {
    if (href?.startsWith("entity://")) {
      // Parse entity://type/id format
      const [, type, id] = href.replace("entity://", "").split("/");
      const route = getEntityRoute(type as EntityType);

      return (
        <button
          onClick={() => navigate(`/org/${orgId}/${route}/${id}`)}
          className="text-primary hover:underline"
          {...props}
        >
          {children}
        </button>
      );
    }

    return (
      <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
        {children}
      </a>
    );
  },
};
```

**Step 2: Run type check**

Run: `cd /Users/jack/GitHub/gocovi-docs/client && npm run tsc`
Expected: PASS

**Step 3: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add client/src/components/ui/markdown-renderer.tsx
git commit -m "feat: handle entity links in markdown renderer

Converts entity://type/id links to internal navigation."
```

---

## Task 9: Manual Testing Checklist

**Search Modal:**
- [ ] CMD+K opens search modal
- [ ] Typing shows results in top 40%
- [ ] Hovering/arrowing updates preview in bottom 60%
- [ ] Preview shows full document content with match highlighted
- [ ] Enter navigates to selected result
- [ ] Shift+Enter closes search and opens chat with query
- [ ] Escape closes modal

**Chat Window:**
- [ ] Chat icon in header opens empty chat
- [ ] Shift+Enter from search opens chat with pre-filled query
- [ ] Messages stream in real-time
- [ ] Citations appear as clickable buttons below AI messages
- [ ] Clicking citation navigates to entity
- [ ] Scope toggle switches between org and global
- [ ] Window is draggable
- [ ] Window is resizable
- [ ] Escape closes chat
- [ ] Closing chat clears conversation

**Step 1: Run the full test suite**

Run: `cd /Users/jack/GitHub/gocovi-docs && npm test`
Expected: All tests pass

**Step 2: Final commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add -A
git commit -m "chore: search and chat redesign complete

- Search modal with rich preview pane
- Floating chat window for AI conversations
- Shift+Enter bridges search to chat"
```

---

## Summary

This plan implements:

1. **FloatingWindow** - Reusable draggable/resizable window component
2. **useChat hook** - Manages conversation state and streaming
3. **ChatWindow** - Full chat interface in floating window
4. **Chat API** - Backend endpoint with conversation history
5. **Search preview** - Rich document preview in search modal
6. **Preview endpoints** - API endpoints for each entity type
7. **Integration** - Chat button in header, Shift+Enter bridge

The search modal becomes a quick-lookup tool with instant preview, while the chat window handles deeper AI-powered exploration with conversation history.
