/**
 * WebSocket Service for real-time updates
 *
 * Uses native WebSocket connection to FastAPI backend.
 *
 * Provides connection management and event subscriptions for:
 * - AI Search streaming
 * - Reindex progress updates
 * - User notifications
 */

import type { EntityType } from "@/lib/entity-icons";

// =============================================================================
// Types for useWebSocket hook compatibility
// =============================================================================

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";

export interface WebSocketMessage<T = unknown> {
  type: string;
  channel: string;
  data: T;
  timestamp: string;
}

export type MessageHandler<T = unknown> = (message: WebSocketMessage<T>) => void;
export type StatusChangeHandler = (status: ConnectionStatus) => void;

// =============================================================================
// AI Search streaming types
// =============================================================================

export interface AISearchCitation {
  entity_type: EntityType;
  entity_id: string;
  organization_id: string;
  name: string;
}

export interface SearchChunk {
  type: "citations" | "delta" | "done" | "error" | "mutation_preview" | "mutation_pending" | "mutation_error";
  data?: AISearchCitation[] | {
    tool_call_id?: string;
    entity_type: string;
    entity_id: string;
    organization_id: string;
    mutation: {
      content?: string;
      field_updates?: Record<string, string>;
      summary: string;
    };
  } | {
    tool_call_id?: string;
    message?: string;
  };
  content?: string;
  message?: string;
}

// =============================================================================
// Reindex streaming types
// =============================================================================

export interface ReindexProgress {
  type: "progress";
  phase: string;
  current: number;
  total: number;
  entity_type?: string;
  percent?: number;
}

export interface ReindexCompleted {
  type: "completed";
  counts: Record<string, number>;
  duration_seconds?: number;
  total_indexed?: number;
}

export interface ReindexFailed {
  type: "failed";
  error: string;
}

export interface ReindexCancelling {
  type: "cancelling";
}

export interface ReindexCancelled {
  type: "cancelled";
  processed: number;
  total: number;
  force: boolean;
}

export type ReindexMessage = ReindexProgress | ReindexCompleted | ReindexFailed | ReindexCancelling | ReindexCancelled;

// =============================================================================
// Internal types
// =============================================================================

type SearchChunkCallback = (chunk: SearchChunk) => void;
type ReindexCallback = (message: ReindexMessage) => void;

// =============================================================================
// WebSocket Service Class
// =============================================================================

export class WebSocketService {
  private static instance: WebSocketService | null = null;

  private ws: WebSocket | null = null;
  private connectionPromise: Promise<void> | null = null;
  private isConnecting = false;
  private retryCount = 0;
  private maxRetries = 3;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private currentStatus: ConnectionStatus = "disconnected";
  private connectionStartTime: number = 0;
  private isRefreshingToken = false;

  // Status change listeners
  private statusListeners = new Set<StatusChangeHandler>();

  // Channel message handlers (for useWebSocket hook compatibility)
  private channelHandlers = new Map<string, Set<MessageHandler<unknown>>>();

  // Subscribers for different event types (for backwards compatibility)
  private searchCallbacks = new Map<string, SearchChunkCallback>();
  private reindexCallbacks = new Map<string, Set<ReindexCallback>>();

  // Track subscribed channels
  private subscribedChannels = new Set<string>();
  private pendingSubscriptions = new Set<string>();

  /**
   * Get singleton instance
   */
  static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService();
    }
    return WebSocketService.instance;
  }

  /**
   * Update connection status and notify listeners
   */
  private setStatus(status: ConnectionStatus): void {
    this.currentStatus = status;
    this.statusListeners.forEach((listener) => listener(status));
  }

  /**
   * Subscribe to status changes
   */
  onStatusChange(handler: StatusChangeHandler): () => void {
    this.statusListeners.add(handler);
    // Immediately call with current status
    handler(this.currentStatus);
    return () => {
      this.statusListeners.delete(handler);
    };
  }

  /**
   * Subscribe to a channel with a message handler (for useWebSocket hook)
   */
  subscribe<T = unknown>(channel: string, handler: MessageHandler<T>): () => void {
    if (!this.channelHandlers.has(channel)) {
      this.channelHandlers.set(channel, new Set());
    }
    this.channelHandlers.get(channel)!.add(handler as MessageHandler<unknown>);

    // Also subscribe to the WebSocket channel if connected
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.subscribeToChannel(channel);
    }

    // Return unsubscribe function
    return () => {
      this.channelHandlers.get(channel)?.delete(handler as MessageHandler<unknown>);
      if (this.channelHandlers.get(channel)?.size === 0) {
        this.channelHandlers.delete(channel);
        this.unsubscribe(channel);
      }
    };
  }

  /**
   * Send subscribe message to server
   */
  private subscribeToChannel(channel: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.pendingSubscriptions.add(channel);
      return;
    }

    this.ws.send(
      JSON.stringify({
        action: "subscribe",
        channel,
      })
    );
  }

  /**
   * Connect to WebSocket with authentication
   */
  async connect(channels: string[] = []): Promise<void> {
    // If already connected, just subscribe to new channels
    if (this.ws?.readyState === WebSocket.OPEN) {
      for (const channel of channels) {
        if (!this.subscribedChannels.has(channel)) {
          this.subscribeToChannel(channel);
        }
      }
      return;
    }

    // If already connecting, wait for that connection
    if (this.isConnecting && this.connectionPromise) {
      await this.connectionPromise;
      // Subscribe to channels after connection
      for (const channel of channels) {
        if (!this.subscribedChannels.has(channel)) {
          this.subscribeToChannel(channel);
        }
      }
      return;
    }

    this.isConnecting = true;
    this.setStatus("connecting");
    this.pendingSubscriptions = new Set(channels);
    this.connectionPromise = this._connect(channels);

    try {
      await this.connectionPromise;
    } finally {
      this.isConnecting = false;
      this.connectionPromise = null;
    }
  }

  private async _connect(channels: string[]): Promise<void> {
    try {
      // Build WebSocket URL with channels
      // Use window.location.host - Vite proxies /ws in dev, nginx/reverse proxy in prod
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;

      // Add channels as query params
      const params = new URLSearchParams();
      channels.forEach((ch) => params.append("channels", ch));

      const wsUrl = `${protocol}//${host}/ws/connect?${params.toString()}`;

      // Track connection start time to detect auth failures
      this.connectionStartTime = Date.now();

      // Create WebSocket connection
      // Note: Cookies (including access_token) are automatically sent by the browser
      this.ws = new WebSocket(wsUrl);

      // Set up WebSocket handlers
      this.ws.onopen = () => {
        this.retryCount = 0;
        this.setStatus("connected");
        this.startPingInterval();
        // Mark channels as subscribed
        channels.forEach((ch) => this.subscribedChannels.add(ch));
        // Subscribe to any pending handler channels
        this.channelHandlers.forEach((_, channel) => {
          if (!this.subscribedChannels.has(channel)) {
            this.subscribeToChannel(channel);
          }
        });
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          this.handleMessage(message);
        } catch (error) {
          console.error("[WebSocket] Failed to parse message:", error);
        }
      };

      this.ws.onerror = (error) => {
        console.error("[WebSocket] Error:", error);
        this.setStatus("error");
      };

      this.ws.onclose = async (event) => {
        this.ws = null;
        this.stopPingInterval();

        // Check if this looks like an auth failure:
        // - Connection closed quickly (within 2 seconds)
        // - Not a normal closure (code 1000)
        // - Common auth failure codes: 1002 (protocol error), 1006 (abnormal), 1008 (policy violation)
        const connectionDuration = Date.now() - this.connectionStartTime;
        const isQuickClose = connectionDuration < 2000;
        const isAuthLikeCode = [1002, 1006, 1008].includes(event.code);
        const isPotentialAuthFailure = isQuickClose && isAuthLikeCode && !this.isRefreshingToken;

        // If it looks like auth failure and we haven't tried refreshing yet
        if (isPotentialAuthFailure && this.retryCount === 0) {
          console.log("[WebSocket] Potential auth failure detected, attempting token refresh...");
          this.isRefreshingToken = true;

          try {
            // Try to refresh the token
            const { refreshAccessToken } = await import("@/lib/api-client");
            await refreshAccessToken();
            console.log("[WebSocket] Token refreshed successfully, retrying connection...");

            // Retry connection immediately with new token
            this.setStatus("reconnecting");
            this.retryCount++;
            this.isRefreshingToken = false;

            // Small delay to allow cookie to be set
            setTimeout(() => {
              this.connect(Array.from(this.subscribedChannels));
            }, 100);
            return;
          } catch (error) {
            console.error("[WebSocket] Token refresh failed:", error);
            this.isRefreshingToken = false;
            // Fall through to normal reconnect logic
          }
        }

        // Normal reconnect logic for other failures
        if (event.code !== 1000 && this.retryCount < this.maxRetries) {
          this.setStatus("reconnecting");
          this.retryCount++;
          const delay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
          this.reconnectTimeout = setTimeout(() => {
            this.connect(Array.from(this.subscribedChannels));
          }, delay);
        } else {
          this.setStatus("disconnected");
          this.isRefreshingToken = false;
        }
      };

      // Wait for connection to open
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error("WebSocket connection timeout"));
        }, 10000);

        if (this.ws) {
          this.ws.addEventListener(
            "open",
            () => {
              clearTimeout(timeout);
              resolve();
            },
            { once: true }
          );
          this.ws.addEventListener(
            "error",
            (error) => {
              clearTimeout(timeout);
              reject(error);
            },
            { once: true }
          );
        }
      });
    } catch (error) {
      console.error("[WebSocket] Failed to connect:", error);
      this.ws = null;
      this.setStatus("error");
      throw error;
    }
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(message: WebSocketMessage) {
    const { type, channel, data } = message;

    // Handle ping/pong
    if (type === "ping") {
      this.sendPong();
      return;
    }

    // Handle subscription confirmations
    if (data && typeof data === "object" && "subscribed" in data) {
      this.subscribedChannels.add((data as { subscribed: string }).subscribed);
      this.pendingSubscriptions.delete((data as { subscribed: string }).subscribed);
      return;
    }

    if (data && typeof data === "object" && "unsubscribed" in data) {
      this.subscribedChannels.delete((data as { unsubscribed: string }).unsubscribed);
      return;
    }

    // Dispatch to channel handlers (for useWebSocket hook)
    const handlers = this.channelHandlers.get(channel);
    if (handlers) {
      handlers.forEach((handler) => handler(message));
    }

    // Route messages to appropriate handlers based on channel prefix
    if (channel.startsWith("search:")) {
      this.dispatchSearchChunk(channel, type, data as Record<string, unknown>);
    } else if (channel.startsWith("reindex:")) {
      this.dispatchReindexMessage(channel, type, data as Record<string, unknown>);
    }
  }

  private dispatchSearchChunk(
    channel: string,
    type: string,
    data: Record<string, unknown>
  ) {
    const requestId = channel.replace("search:", "");
    const callback = this.searchCallbacks.get(requestId);

    if (!callback) return;

    // Map the message type to SearchChunk format
    const chunk: SearchChunk = { type: type as SearchChunk["type"] };

    switch (type) {
      case "delta":
        // Extract content from the data
        chunk.content = (data.content as string) || "";
        break;
      case "completed":
        // Map completed to done for API compatibility
        chunk.type = "done";
        break;
      case "failed":
        chunk.type = "error";
        chunk.message = (data.error as string) || "Search failed";
        break;
      case "mutation_pending":
        // Pass through pending state
        chunk.type = "mutation_pending";
        chunk.data = {
          tool_call_id: data.tool_call_id as string,
        };
        break;
      case "mutation_preview":
        // Pass through mutation preview data
        chunk.type = "mutation_preview";
        chunk.data = data as {
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
        break;
      case "mutation_error":
        // Pass through error data
        chunk.type = "mutation_error";
        chunk.data = {
          message: data.message as string,
        };
        break;
    }

    // For citations, data contains the citation array directly
    if (data.chunk_type === "citation" && data.metadata) {
      chunk.type = "citations";
      chunk.data = data.metadata as AISearchCitation[];
    }

    callback(chunk);
  }

  private dispatchReindexMessage(
    channel: string,
    type: string,
    data: Record<string, unknown>
  ) {
    const jobId = channel.replace("reindex:", "");
    const callbacks = this.reindexCallbacks.get(jobId);

    if (!callbacks) return;

    let message: ReindexMessage;

    switch (type) {
      case "progress":
        message = {
          type: "progress",
          phase: (data.phase as string) || "",
          current: (data.current as number) || 0,
          total: (data.total as number) || 0,
          entity_type: data.entity_type as string | undefined,
          percent: data.percent as number | undefined,
        };
        break;
      case "completed":
        message = {
          type: "completed",
          counts: (data.counts as Record<string, number>) || {},
          duration_seconds: data.duration_seconds as number | undefined,
          total_indexed: data.total_indexed as number | undefined,
        };
        break;
      case "failed":
        message = {
          type: "failed",
          error: (data.error as string) || "Reindex failed",
        };
        break;
      default:
        return; // Unknown message type
    }

    callbacks.forEach((cb) => cb(message));
  }

  /**
   * Unsubscribe from a channel (removes handlers and sends unsubscribe to server)
   */
  unsubscribe(channel: string): void {
    // Remove handlers
    this.channelHandlers.delete(channel);
    this.subscribedChannels.delete(channel);

    // Send unsubscribe to server if connected
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          action: "unsubscribe",
          channel,
        })
      );
    }
  }

  /**
   * Connect to a search channel for AI search streaming
   */
  async connectToSearch(requestId: string): Promise<void> {
    const channel = `search:${requestId}`;
    if (this.subscribedChannels.has(channel)) {
      return;
    }

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.subscribeToChannel(channel);
      return;
    }

    await this.connect([channel]);
  }

  /**
   * Subscribe to AI search streaming chunks
   */
  onSearchChunk(requestId: string, callback: SearchChunkCallback): () => void {
    this.searchCallbacks.set(requestId, callback);

    // Return unsubscribe function
    return () => {
      this.searchCallbacks.delete(requestId);
    };
  }

  /**
   * Connect to a reindex job channel for progress updates
   */
  async connectToReindex(jobId: string): Promise<void> {
    const channel = `reindex:${jobId}`;
    if (this.subscribedChannels.has(channel)) {
      return;
    }

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.subscribeToChannel(channel);
      return;
    }

    await this.connect([channel]);
  }

  /**
   * Subscribe to reindex progress updates
   */
  onReindexProgress(jobId: string, callback: ReindexCallback): () => void {
    if (!this.reindexCallbacks.has(jobId)) {
      this.reindexCallbacks.set(jobId, new Set());
    }
    this.reindexCallbacks.get(jobId)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.reindexCallbacks.get(jobId)?.delete(callback);
      if (this.reindexCallbacks.get(jobId)?.size === 0) {
        this.reindexCallbacks.delete(jobId);
      }
    };
  }

  /**
   * Send pong response
   */
  private sendPong() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "pong" }));
    }
  }

  /**
   * Start ping interval for keeping connection alive
   */
  private startPingInterval() {
    this.pingInterval = setInterval(() => {
      // The server sends pings, we just need to respond
    }, 15000);
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    this.stopPingInterval();

    if (this.ws) {
      this.subscribedChannels.clear();
      this.ws.close(1000, "Normal closure");
      this.ws = null;
    }

    this.setStatus("disconnected");
  }

  /**
   * Check if currently connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Export singleton instance
export const webSocketService = new WebSocketService();
