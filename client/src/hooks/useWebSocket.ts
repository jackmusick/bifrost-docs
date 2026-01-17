/**
 * useWebSocket Hook
 *
 * React hook for WebSocket connections and channel subscriptions.
 * Handles connection lifecycle and cleanup on unmount.
 */

import { useCallback, useEffect, useState } from "react";

import {
  type ConnectionStatus,
  type MessageHandler,
  type WebSocketMessage,
  WebSocketService,
} from "@/services/websocket";

/**
 * Hook return type
 */
interface UseWebSocketReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Whether the connection is established */
  isConnected: boolean;
  /** Subscribe to a channel */
  subscribe: <T = unknown>(channel: string, handler: MessageHandler<T>) => () => void;
  /** Unsubscribe from a channel */
  unsubscribe: (channel: string) => void;
  /** Connect to the WebSocket server */
  connect: (channels?: string[]) => Promise<void>;
  /** Disconnect from the WebSocket server */
  disconnect: () => void;
}

/**
 * Hook for managing WebSocket connections
 *
 * Usage:
 * ```tsx
 * function ReindexProgress({ jobId }: { jobId: string }) {
 *   const { status, subscribe } = useWebSocket();
 *   const [progress, setProgress] = useState(0);
 *
 *   useEffect(() => {
 *     const unsubscribe = subscribe(`reindex:${jobId}`, (message) => {
 *       if (message.type === "progress") {
 *         setProgress(message.data.percent);
 *       }
 *     });
 *     return unsubscribe;
 *   }, [jobId, subscribe]);
 *
 *   return <ProgressBar value={progress} />;
 * }
 * ```
 */
export function useWebSocket(): UseWebSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");

  // Get the singleton instance
  const ws = WebSocketService.getInstance();

  // Subscribe to status changes
  useEffect(() => {
    return ws.onStatusChange(setStatus);
  }, [ws]);

  // Memoized subscribe function
  const subscribe = useCallback(
    <T = unknown>(channel: string, handler: MessageHandler<T>): (() => void) => {
      return ws.subscribe(channel, handler);
    },
    [ws]
  );

  // Memoized unsubscribe function
  const unsubscribe = useCallback(
    (channel: string): void => {
      ws.unsubscribe(channel);
    },
    [ws]
  );

  // Memoized connect function
  const connect = useCallback(
    async (channels: string[] = []): Promise<void> => {
      return ws.connect(channels);
    },
    [ws]
  );

  // Memoized disconnect function
  const disconnect = useCallback((): void => {
    ws.disconnect();
  }, [ws]);

  return {
    status,
    isConnected: status === "connected",
    subscribe,
    unsubscribe,
    connect,
    disconnect,
  };
}

/**
 * Hook for subscribing to a specific channel
 *
 * Auto-connects if not already connected and subscribes to the channel.
 * Cleans up subscription on unmount.
 *
 * Usage:
 * ```tsx
 * function SearchResults({ requestId }: { requestId: string }) {
 *   const { messages, status } = useWebSocketChannel<SearchDeltaData>(
 *     `search:${requestId}`
 *   );
 *
 *   return (
 *     <div>
 *       {messages.map((msg, i) => (
 *         <p key={i}>{msg.data.content}</p>
 *       ))}
 *     </div>
 *   );
 * }
 * ```
 */
export function useWebSocketChannel<T = unknown>(
  channel: string,
  options?: {
    /** Whether to automatically connect if not connected */
    autoConnect?: boolean;
    /** Callback when a message is received */
    onMessage?: MessageHandler<T>;
    /** Only subscribe when this is true */
    enabled?: boolean;
  }
): {
  status: ConnectionStatus;
  isConnected: boolean;
  messages: WebSocketMessage<T>[];
  latestMessage: WebSocketMessage<T> | null;
  clearMessages: () => void;
} {
  const { autoConnect = true, onMessage, enabled = true } = options ?? {};
  const { status, subscribe, connect } = useWebSocket();
  const [messages, setMessages] = useState<WebSocketMessage<T>[]>([]);

  // Auto-connect if needed
  useEffect(() => {
    if (!enabled) return;

    if (autoConnect && status === "disconnected") {
      connect([channel]).catch(console.error);
    }
  }, [autoConnect, channel, connect, enabled, status]);

  // Subscribe to channel
  useEffect(() => {
    if (!enabled) return;
    if (status !== "connected") return;

    const handler: MessageHandler<T> = (message) => {
      setMessages((prev) => [...prev, message]);
      onMessage?.(message);
    };

    return subscribe(channel, handler);
  }, [channel, enabled, onMessage, status, subscribe]);

  // Clear messages function
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    status,
    isConnected: status === "connected",
    messages,
    latestMessage: messages.length > 0 ? messages[messages.length - 1] : null,
    clearMessages,
  };
}

/**
 * Hook for receiving reindex progress updates
 *
 * Usage:
 * ```tsx
 * function ReindexStatus({ jobId }: { jobId: string }) {
 *   const { progress, completed, error } = useReindexProgress(jobId);
 *
 *   if (error) return <Error message={error} />;
 *   if (completed) return <Success counts={completed.counts} />;
 *
 *   return (
 *     <Progress
 *       value={progress?.percent ?? 0}
 *       label={`${progress?.phase}: ${progress?.current}/${progress?.total}`}
 *     />
 *   );
 * }
 * ```
 */
export function useReindexProgress(
  jobId: string | null,
  options?: { enabled?: boolean }
): {
  status: ConnectionStatus;
  progress: {
    phase: string;
    current: number;
    total: number;
    percent: number;
    entityType?: string;
  } | null;
  completed: {
    counts: Record<string, number>;
    totalIndexed: number;
    durationSeconds: number;
  } | null;
  error: string | null;
} {
  const { enabled = true } = options ?? {};
  const channel = jobId ? `reindex:${jobId}` : "";
  const { status, messages } = useWebSocketChannel(channel, {
    enabled: enabled && !!jobId,
  });

  // Find latest progress, completed, or failed message
  let progress = null;
  let completed = null;
  let error = null;

  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.type === "progress" && !progress) {
      const data = msg.data as {
        phase: string;
        current: number;
        total: number;
        percent: number;
        entity_type?: string;
      };
      progress = {
        phase: data.phase,
        current: data.current,
        total: data.total,
        percent: data.percent,
        entityType: data.entity_type,
      };
    }
    if (msg.type === "completed" && !completed) {
      const data = msg.data as {
        counts: Record<string, number>;
        total_indexed: number;
        duration_seconds: number;
      };
      completed = {
        counts: data.counts,
        totalIndexed: data.total_indexed,
        durationSeconds: data.duration_seconds,
      };
    }
    if (msg.type === "failed" && !error) {
      const data = msg.data as { error: string };
      error = data.error;
    }
  }

  return { status, progress, completed, error };
}

/**
 * Hook for receiving AI search streaming results
 *
 * Usage:
 * ```tsx
 * function AISearchResults({ requestId }: { requestId: string }) {
 *   const { chunks, answer, sources, error, isComplete } = useSearchStream(requestId);
 *
 *   return (
 *     <div>
 *       <StreamingText chunks={chunks} />
 *       {isComplete && <Sources items={sources} />}
 *     </div>
 *   );
 * }
 * ```
 */
export function useSearchStream(
  requestId: string | null,
  options?: { enabled?: boolean }
): {
  status: ConnectionStatus;
  chunks: Array<{ chunkType: string; content: string }>;
  answer: string | null;
  sources: Array<{ id: string; type: string; name: string; excerpt: string }>;
  error: string | null;
  isComplete: boolean;
} {
  const { enabled = true } = options ?? {};
  const channel = requestId ? `search:${requestId}` : "";
  const { status, messages } = useWebSocketChannel(channel, {
    enabled: enabled && !!requestId,
  });

  // Process messages
  const chunks: Array<{ chunkType: string; content: string }> = [];
  let answer: string | null = null;
  let sources: Array<{ id: string; type: string; name: string; excerpt: string }> = [];
  let error: string | null = null;
  let isComplete = false;

  for (const msg of messages) {
    if (msg.type === "delta") {
      const data = msg.data as { chunk_type: string; content: string };
      chunks.push({
        chunkType: data.chunk_type,
        content: data.content,
      });
    }
    if (msg.type === "completed") {
      const data = msg.data as {
        answer: string;
        sources: Array<{ id: string; type: string; name: string; excerpt: string }>;
      };
      answer = data.answer;
      sources = data.sources;
      isComplete = true;
    }
    if (msg.type === "failed") {
      const data = msg.data as { error: string };
      error = data.error;
      isComplete = true;
    }
  }

  return { status, chunks, answer, sources, error, isComplete };
}
