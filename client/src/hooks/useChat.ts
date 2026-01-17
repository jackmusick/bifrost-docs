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
  type?: "mutation_preview" | "mutation_pending" | "mutation_error";
  toolCallId?: string;  // For tracking pending → complete transitions
  previewData?: {
    entity_type: string;
    entity_id: string;
    organization_id: string;
    mutation: {
      content?: string;
      field_updates?: Record<string, string>;
      summary: string;
    };
  };
  errorMessage?: string;  // For mutation_error type
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
  currentEntityId?: string;
  currentEntityType?: "document" | "custom_asset";
}

export function useChat(options: UseChatOptions = {}) {
  const { orgId, currentEntityId, currentEntityType } = options;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);

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

      case "mutation_pending":
        // Finalize any pending content first
        if (pendingContentRef.current) {
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
          pendingContentRef.current = "";
          pendingCitationsRef.current = [];
        }

        // Add pending mutation message (loading state)
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: "",
            timestamp: new Date(),
            type: "mutation_pending",
            toolCallId: (chunk.data as { tool_call_id?: string })?.tool_call_id,
          },
        ]);
        break;

      case "mutation_preview":
        const previewData = chunk.data as {
          tool_call_id?: string;
          entity_type: string;
          entity_id: string;
          organization_id: string;
          mutation: {
            content?: string;
            field_updates?: Record<string, string>;
            summary: string;
          };
        };

        // Replace pending message if it exists, otherwise add new
        setMessages((prev) => {
          const pendingIndex = prev.findIndex(
            (m) => m.type === "mutation_pending" && m.toolCallId === previewData.tool_call_id
          );

          if (pendingIndex !== -1) {
            // Replace pending with complete preview
            const updated = [...prev];
            updated[pendingIndex] = {
              ...updated[pendingIndex],
              type: "mutation_preview",
              previewData,
            };
            return updated;
          } else {
            // No pending found, add new (backward compatibility)
            return [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "assistant",
                content: "",
                timestamp: new Date(),
                type: "mutation_preview",
                previewData,
              },
            ];
          }
        });
        break;

      case "mutation_error":
        // Replace any pending message with error
        const errorData = chunk.data as { message?: string };
        setMessages((prev) => {
          // Find and replace the most recent pending mutation
          const pendingIndex = [...prev].reverse().findIndex((m) => m.type === "mutation_pending");

          if (pendingIndex !== -1) {
            const actualIndex = prev.length - 1 - pendingIndex;
            const updated = [...prev];
            updated[actualIndex] = {
              ...updated[actualIndex],
              type: "mutation_error",
              errorMessage: errorData.message || "Unable to preview this action",
            };
            return updated;
          } else {
            // No pending found, add error message
            return [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "assistant",
                content: "",
                timestamp: new Date(),
                type: "mutation_error",
                errorMessage: errorData.message || "Unable to preview this action",
              },
            ];
          }
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
        const response = await api.post<ChatStartResponse>("/api/search/chat", {
          message: content.trim(),
          conversation_id: conversationId,
          history,
          ...(orgId ? { org_id: orgId } : {}),
          ...(currentEntityId ? { current_entity_id: currentEntityId } : {}),
          ...(currentEntityType ? { current_entity_type: currentEntityType } : {}),
        });

        const { request_id, conversation_id: conv_id } = response.data;
        setRequestId(request_id);
        setConversationId(conv_id);

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
    [messages, orgId, handleChunk, conversationId, currentEntityId, currentEntityType]
  );

  const reset = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
    if (requestId) {
      webSocketService.unsubscribe(`search:${requestId}`);
    }
    setMessages([]);
    setIsLoading(false);
    setIsStreaming(false);
    setError(null);
    setConversationId(null);
    setRequestId(null);
    pendingContentRef.current = "";
    pendingCitationsRef.current = [];
  }, [requestId]);

  return {
    messages,
    isLoading,
    isStreaming,
    error,
    sendMessage,
    reset,
    conversationId,
    requestId,
  };
}
