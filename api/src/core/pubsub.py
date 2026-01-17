"""
WebSocket Connection Manager with Redis Pub/Sub

Manages WebSocket connections and enables multi-instance scaling via Redis pub/sub.
Falls back to local-only broadcasting when Redis is unavailable.
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from src.core.cache import get_redis

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""

    DELTA = "delta"  # Streaming content chunk
    PROGRESS = "progress"  # Progress update
    COMPLETED = "completed"  # Operation completed
    FAILED = "failed"  # Operation failed
    ERROR = "error"  # Error message
    PING = "ping"  # Keepalive ping
    PONG = "pong"  # Keepalive pong
    MUTATION_PENDING = "mutation_pending"  # Mutation tool call started
    MUTATION_PREVIEW = "mutation_preview"  # Mutation preview ready
    MUTATION_ERROR = "mutation_error"  # Mutation parsing failed


@dataclass
class WebSocketMessage:
    """
    WebSocket message structure.

    Attributes:
        type: Message type (delta, progress, completed, failed, error)
        channel: Channel the message is for (e.g., reindex:123, search:456)
        data: Message payload
        timestamp: When the message was created
    """

    type: MessageType
    channel: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(
            {
                "type": self.type.value,
                "channel": self.channel,
                "data": self.data,
                "timestamp": self.timestamp.isoformat(),
            }
        )

    @classmethod
    def from_json(cls, json_str: str) -> "WebSocketMessage":
        """Deserialize message from JSON string."""
        data = json.loads(json_str)
        return cls(
            type=MessageType(data["type"]),
            channel=data["channel"],
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class ConnectionInfo:
    """
    Information about a WebSocket connection.

    Attributes:
        websocket: The WebSocket connection
        user_id: Authenticated user ID
        channels: Set of subscribed channels
        connected_at: When the connection was established
    """

    websocket: WebSocket
    user_id: UUID
    channels: set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.

    Supports Redis pub/sub for multi-instance scaling with fallback
    to local-only broadcasting when Redis is unavailable.
    """

    # Redis pub/sub channel prefix
    PUBSUB_CHANNEL_PREFIX = "ws:pubsub:"

    def __init__(self) -> None:
        # Map of connection ID to ConnectionInfo
        self._connections: dict[str, ConnectionInfo] = {}
        # Map of channel to set of connection IDs
        self._channel_subscribers: dict[str, set[str]] = defaultdict(set)
        # Redis pub/sub task
        self._pubsub_task: asyncio.Task[None] | None = None
        # Whether Redis pub/sub is active
        self._redis_enabled = False
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def start_pubsub(self) -> None:
        """
        Start Redis pub/sub listener for multi-instance broadcasting.

        Falls back to local-only if Redis is unavailable.
        """
        if self._pubsub_task is not None:
            return

        try:
            redis = await get_redis()
            # Test connection - ping returns bool with decode_responses=True
            result = await redis.ping()  # type: ignore[misc]
            if not result:
                raise ConnectionError("Redis ping failed")
            self._redis_enabled = True
            self._pubsub_task = asyncio.create_task(self._listen_pubsub())
            logger.info("WebSocket Redis pub/sub started")
        except Exception as e:
            logger.warning(f"Redis pub/sub not available, using local-only mode: {e}")
            self._redis_enabled = False

    async def stop_pubsub(self) -> None:
        """Stop Redis pub/sub listener."""
        if self._pubsub_task is not None:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
            self._pubsub_task = None
            logger.info("WebSocket Redis pub/sub stopped")

    async def _listen_pubsub(self) -> None:
        """Listen for messages from Redis pub/sub and broadcast locally."""
        try:
            redis = await get_redis()
            pubsub = redis.pubsub()
            # Subscribe to wildcard channel pattern
            await pubsub.psubscribe(f"{self.PUBSUB_CHANNEL_PREFIX}*")

            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        # Extract channel name from pattern match
                        full_channel = message["channel"]
                        if isinstance(full_channel, bytes):
                            full_channel = full_channel.decode()
                        channel = full_channel[len(self.PUBSUB_CHANNEL_PREFIX) :]

                        # Parse and broadcast message
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode()
                        ws_message = WebSocketMessage.from_json(data)
                        await self._broadcast_local(channel, ws_message)
                    except Exception as e:
                        logger.error(f"Error processing pub/sub message: {e}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Redis pub/sub listener error: {e}")
            self._redis_enabled = False

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: UUID,
        channels: list[str],
    ) -> None:
        """
        Accept a new WebSocket connection and subscribe to channels.

        Args:
            websocket: The WebSocket connection
            connection_id: Unique connection identifier
            user_id: Authenticated user ID
            channels: List of channels to subscribe to
        """
        await websocket.accept()

        async with self._lock:
            # Store connection
            info = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                channels=set(channels),
            )
            self._connections[connection_id] = info

            # Subscribe to channels
            for channel in channels:
                self._channel_subscribers[channel].add(connection_id)

        logger.info(
            f"WebSocket connected: {connection_id} (user: {user_id}, channels: {channels})"
        )

    async def disconnect(self, connection_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            connection_id: Connection identifier to remove
        """
        async with self._lock:
            if connection_id not in self._connections:
                return

            info = self._connections[connection_id]

            # Unsubscribe from all channels
            for channel in info.channels:
                self._channel_subscribers[channel].discard(connection_id)
                # Clean up empty channel sets
                if not self._channel_subscribers[channel]:
                    del self._channel_subscribers[channel]

            # Remove connection
            del self._connections[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe(self, connection_id: str, channel: str) -> None:
        """
        Subscribe a connection to a channel.

        Args:
            connection_id: Connection identifier
            channel: Channel to subscribe to
        """
        async with self._lock:
            if connection_id not in self._connections:
                return

            self._connections[connection_id].channels.add(channel)
            self._channel_subscribers[channel].add(connection_id)

        logger.debug(f"Connection {connection_id} subscribed to {channel}")

    async def unsubscribe(self, connection_id: str, channel: str) -> None:
        """
        Unsubscribe a connection from a channel.

        Args:
            connection_id: Connection identifier
            channel: Channel to unsubscribe from
        """
        async with self._lock:
            if connection_id not in self._connections:
                return

            self._connections[connection_id].channels.discard(channel)
            self._channel_subscribers[channel].discard(connection_id)

            if not self._channel_subscribers[channel]:
                del self._channel_subscribers[channel]

        logger.debug(f"Connection {connection_id} unsubscribed from {channel}")

    async def broadcast(self, channel: str, message: WebSocketMessage) -> None:
        """
        Broadcast a message to all subscribers of a channel.

        If Redis is enabled, publishes to Redis for multi-instance broadcast.
        Otherwise, broadcasts locally only.

        Args:
            channel: Channel to broadcast to
            message: Message to send
        """
        if self._redis_enabled:
            try:
                redis = await get_redis()
                await redis.publish(
                    f"{self.PUBSUB_CHANNEL_PREFIX}{channel}",
                    message.to_json(),
                )
                return
            except Exception as e:
                logger.warning(f"Redis publish failed, falling back to local: {e}")

        # Local broadcast (fallback or primary if Redis not available)
        await self._broadcast_local(channel, message)

    async def _broadcast_local(self, channel: str, message: WebSocketMessage) -> None:
        """
        Broadcast a message to local subscribers only.

        Args:
            channel: Channel to broadcast to
            message: Message to send
        """
        async with self._lock:
            connection_ids = self._channel_subscribers.get(channel, set()).copy()

        if not connection_ids:
            return

        json_message = message.to_json()

        for connection_id in connection_ids:
            try:
                info = self._connections.get(connection_id)
                if info:
                    await info.websocket.send_text(json_message)
            except WebSocketDisconnect:
                # Connection closed, will be cleaned up elsewhere
                pass
            except Exception as e:
                logger.warning(f"Failed to send to {connection_id}: {e}")

    async def send_to_user(self, user_id: UUID, message: WebSocketMessage) -> None:
        """
        Send a message to all connections for a specific user.

        Args:
            user_id: User ID to send to
            message: Message to send
        """
        json_message = message.to_json()

        async with self._lock:
            connections = [
                info
                for info in self._connections.values()
                if info.user_id == user_id
            ]

        for info in connections:
            try:
                await info.websocket.send_text(json_message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

    def get_channel_subscriber_count(self, channel: str) -> int:
        """Get the number of subscribers for a channel."""
        return len(self._channel_subscribers.get(channel, set()))


# Singleton instance
_connection_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """
    Get the singleton ConnectionManager instance.

    Returns:
        ConnectionManager instance
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


# =============================================================================
# Helper Functions for Publishing Messages
# =============================================================================


async def _publish_to_redis(channel: str, message: WebSocketMessage) -> None:
    """
    Publish a message directly to Redis pub/sub.

    This bypasses the ConnectionManager and publishes directly to Redis,
    which is necessary for worker processes that don't have WebSocket
    connections but need to send updates to connected clients.

    The API's ConnectionManager listens to Redis pub/sub and forwards
    messages to local WebSocket connections.
    """
    try:
        redis = await get_redis()
        await redis.publish(
            f"{ConnectionManager.PUBSUB_CHANNEL_PREFIX}{channel}",
            message.to_json(),
        )
        logger.debug(f"Published to Redis channel: {channel}")
    except Exception as e:
        logger.error(f"Failed to publish to Redis channel {channel}: {e}")


async def publish_reindex_progress(
    job_id: str,
    phase: str,
    current: int,
    total: int,
    entity_type: str | None = None,
) -> None:
    """
    Publish reindex progress update.

    Args:
        job_id: Reindex job identifier
        phase: Current phase (e.g., "indexing", "embedding")
        current: Current item number
        total: Total items to process
        entity_type: Type of entity being processed
    """
    channel = f"reindex:{job_id}"
    message = WebSocketMessage(
        type=MessageType.PROGRESS,
        channel=channel,
        data={
            "phase": phase,
            "current": current,
            "total": total,
            "entity_type": entity_type,
            "percent": round((current / total * 100) if total > 0 else 0, 1),
        },
    )
    await _publish_to_redis(channel, message)


async def publish_reindex_completed(
    job_id: str,
    counts: dict[str, int],
    duration_seconds: float,
) -> None:
    """
    Publish reindex completion notification.

    Args:
        job_id: Reindex job identifier
        counts: Dictionary of entity type to count indexed
        duration_seconds: Total duration of the reindex
    """
    channel = f"reindex:{job_id}"
    message = WebSocketMessage(
        type=MessageType.COMPLETED,
        channel=channel,
        data={
            "status": "completed",
            "counts": counts,
            "duration_seconds": duration_seconds,
            "total_indexed": sum(counts.values()),
        },
    )
    await _publish_to_redis(channel, message)


async def publish_reindex_failed(job_id: str, error: str) -> None:
    """
    Publish reindex failure notification.

    Args:
        job_id: Reindex job identifier
        error: Error message
    """
    channel = f"reindex:{job_id}"
    message = WebSocketMessage(
        type=MessageType.FAILED,
        channel=channel,
        data={"status": "failed", "error": error},
    )
    await _publish_to_redis(channel, message)


async def publish_reindex_cancelling(job_id: str) -> None:
    """
    Publish reindex cancellation requested notification.

    Args:
        job_id: Reindex job identifier
    """
    channel = f"reindex:{job_id}"
    message = WebSocketMessage(
        type=MessageType.PROGRESS,
        channel=channel,
        data={"status": "cancelling", "message": "Cancellation requested, waiting for worker..."},
    )
    await _publish_to_redis(channel, message)


async def publish_reindex_cancelled(
    job_id: str,
    processed: int,
    total: int,
    force: bool = False,
) -> None:
    """
    Publish reindex cancelled notification.

    Args:
        job_id: Reindex job identifier
        processed: Number of entities processed before cancellation
        total: Total entities that were to be processed
        force: Whether this was a force cancel
    """
    channel = f"reindex:{job_id}"
    message = WebSocketMessage(
        type=MessageType.COMPLETED,
        channel=channel,
        data={
            "status": "cancelled",
            "processed": processed,
            "total": total,
            "force": force,
            "message": "Force cancelled by administrator" if force else "Cancelled by user",
        },
    )
    await _publish_to_redis(channel, message)


async def publish_search_citations(
    request_id: str,
    citations: list[dict[str, Any]],
) -> None:
    """
    Publish AI search citations.

    Args:
        request_id: Search request identifier
        citations: List of citation dictionaries
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.DELTA,
        channel=f"search:{request_id}",
        data={
            "type": "citations",
            "data": citations,
        },
    )
    await manager.broadcast(f"search:{request_id}", message)


async def publish_search_delta(
    request_id: str,
    content: str,
) -> None:
    """
    Publish AI search content delta (streaming chunk).

    Args:
        request_id: Search request identifier
        content: Text content chunk
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.DELTA,
        channel=f"search:{request_id}",
        data={
            "type": "delta",
            "content": content,
        },
    )
    await manager.broadcast(f"search:{request_id}", message)


async def publish_search_done(request_id: str) -> None:
    """
    Publish AI search completion.

    Args:
        request_id: Search request identifier
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.COMPLETED,
        channel=f"search:{request_id}",
        data={"type": "done"},
    )
    await manager.broadcast(f"search:{request_id}", message)


async def publish_search_error(
    request_id: str,
    error_message: str,
) -> None:
    """
    Publish AI search error.

    Args:
        request_id: Search request identifier
        error_message: Error description
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.ERROR,
        channel=f"search:{request_id}",
        data={
            "type": "error",
            "message": error_message,
        },
    )
    await manager.broadcast(f"search:{request_id}", message)


async def publish_mutation_pending(
    request_id: str,
    tool_call_id: str,
) -> None:
    """
    Publish mutation pending state.

    Args:
        request_id: Search request identifier
        tool_call_id: Tool call identifier for tracking
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.MUTATION_PENDING,
        channel=f"search:{request_id}",
        data={
            "tool_call_id": tool_call_id,
        },
    )
    await manager.broadcast(f"search:{request_id}", message)


async def publish_mutation_preview(
    request_id: str,
    preview_data: dict[str, Any],
) -> None:
    """
    Publish mutation preview.

    Args:
        request_id: Search request identifier
        preview_data: Mutation preview data including entity_type, entity_id, etc.
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.MUTATION_PREVIEW,
        channel=f"search:{request_id}",
        data=preview_data,
    )
    await manager.broadcast(f"search:{request_id}", message)


async def publish_mutation_error(
    request_id: str,
    error_message: str,
) -> None:
    """
    Publish mutation error.

    Args:
        request_id: Search request identifier
        error_message: Error description
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.MUTATION_ERROR,
        channel=f"search:{request_id}",
        data={
            "message": error_message,
        },
    )
    await manager.broadcast(f"search:{request_id}", message)


# Legacy functions for backwards compatibility
async def publish_search_chunk(
    request_id: str,
    chunk_type: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Publish AI search streaming chunk (legacy).

    Args:
        request_id: Search request identifier
        chunk_type: Type of chunk (e.g., "answer", "source", "thinking")
        content: The content chunk
        metadata: Optional metadata for the chunk
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.DELTA,
        channel=f"search:{request_id}",
        data={
            "chunk_type": chunk_type,
            "content": content,
            "metadata": metadata or {},
        },
    )
    await manager.broadcast(f"search:{request_id}", message)


async def publish_search_completed(
    request_id: str,
    answer: str,
    sources: list[dict[str, Any]],
) -> None:
    """
    Publish AI search completion (legacy).

    Args:
        request_id: Search request identifier
        answer: The complete answer
        sources: List of source documents
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.COMPLETED,
        channel=f"search:{request_id}",
        data={
            "answer": answer,
            "sources": sources,
        },
    )
    await manager.broadcast(f"search:{request_id}", message)


async def publish_search_failed(request_id: str, error: str) -> None:
    """
    Publish AI search failure (legacy).

    Args:
        request_id: Search request identifier
        error: Error message
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.FAILED,
        channel=f"search:{request_id}",
        data={"error": error},
    )
    await manager.broadcast(f"search:{request_id}", message)


async def publish_user_notification(
    user_id: UUID,
    title: str,
    message: str,
    notification_type: str = "info",
    data: dict[str, Any] | None = None,
) -> None:
    """
    Publish a notification to a specific user.

    Args:
        user_id: User to notify
        title: Notification title
        message: Notification message
        notification_type: Type (info, success, warning, error)
        data: Optional additional data
    """
    manager = get_connection_manager()
    ws_message = WebSocketMessage(
        type=MessageType.DELTA,
        channel=f"user:{user_id}",
        data={
            "title": title,
            "message": message,
            "notification_type": notification_type,
            **(data or {}),
        },
    )
    await manager.send_to_user(user_id, ws_message)


async def publish_entity_update(
    entity_type: str,
    entity_id: UUID,
    organization_id: UUID,
    updated_by: UUID,
) -> None:
    """
    Publish entity update notification.

    Args:
        entity_type: Type of entity (document, custom_asset)
        entity_id: Entity ID
        organization_id: Organization ID
        updated_by: User ID who made the update
    """
    manager = get_connection_manager()
    channel = f"entity_update:{entity_type}:{entity_id}"
    message = WebSocketMessage(
        type=MessageType.DELTA,
        channel=channel,
        data={
            "type": "entity_update",
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "organization_id": str(organization_id),
            "updated_by": str(updated_by),
        },
    )
    await manager.broadcast(channel, message)
