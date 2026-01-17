"""
WebSocket Router

Provides WebSocket endpoint for real-time communication.
Supports channel-based subscriptions with authentication.
"""

import asyncio
import logging
import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from src.core.auth import UserPrincipal
from src.core.database import get_db_context
from src.core.pubsub import (
    ConnectionManager,
    MessageType,
    WebSocketMessage,
    get_connection_manager,
)
from src.core.security import decode_token, hash_api_key
from src.models.enums import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


async def authenticate_websocket(websocket: WebSocket) -> UserPrincipal | None:
    """
    Authenticate a WebSocket connection.

    Checks for authentication token in:
    1. access_token cookie (browser clients)
    2. token query parameter (fallback)

    Args:
        websocket: The WebSocket connection

    Returns:
        UserPrincipal if authenticated, None otherwise
    """
    from sqlalchemy import select

    from src.models.orm.api_key import APIKey
    from src.models.orm.user import User

    token = None

    # Try cookie first (browser clients)
    if "access_token" in websocket.cookies:
        token = websocket.cookies["access_token"]
    # Fallback to query parameter
    elif "token" in websocket.query_params:
        token = websocket.query_params["token"]

    if not token:
        return None

    # Check if it's an API key (starts with bifrost_docs)
    if token.startswith("bifrost_docs"):
        async with get_db_context() as db:
            key_hash = hash_api_key(token)
            stmt = select(APIKey).where(APIKey.key_hash == key_hash)
            result = await db.execute(stmt)
            api_key = result.scalar_one_or_none()

            if not api_key or api_key.is_expired:
                return None

            user_stmt = select(User).where(User.id == api_key.user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if not user or not user.is_active:
                return None

            return UserPrincipal(
                user_id=user.id,
                email=user.email,
                name=user.name or "",
                role=user.role,
                is_active=user.is_active,
                is_verified=True,
                api_key_id=api_key.id,
            )

    # Otherwise treat as JWT
    payload = decode_token(token, expected_type="access")
    if payload is None:
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return None

    # Tokens MUST have email claim
    if "email" not in payload:
        logger.warning(
            f"WebSocket token for user {user_id} missing required email claim.")
        return None

    # Get role from token (default to CONTRIBUTOR for backwards compatibility)
    role_str = payload.get("role", "contributor")
    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.CONTRIBUTOR

    # JWT tokens no longer include org_id - all users can see all organizations
    return UserPrincipal(
        user_id=user_id,
        email=payload.get("email", ""),
        name=payload.get("name", ""),
        role=role,
        is_active=True,
        is_verified=True,
    )

# Ping interval in seconds
PING_INTERVAL = 15

# Channel validation patterns
CHANNEL_PATTERNS = {
    "reindex": re.compile(r"^reindex:[a-f0-9-]{36}$"),
    "search": re.compile(r"^search:[a-f0-9-]{36}$"),
    "user": re.compile(r"^user:[a-f0-9-]{36}$"),
    "export": re.compile(r"^export:[a-f0-9-]{36}$"),
    "entity_update": re.compile(r"^entity_update:(document|custom_asset):[a-f0-9-]{36}$"),
}


def validate_channel(channel: str) -> bool:
    """
    Validate that a channel name matches an allowed pattern.

    Args:
        channel: Channel name to validate

    Returns:
        True if valid, False otherwise
    """
    for pattern in CHANNEL_PATTERNS.values():
        if pattern.match(channel):
            return True
    return False


def can_subscribe_to_channel(user_id: UUID, channel: str) -> bool:
    """
    Check if a user can subscribe to a specific channel.

    Channel access rules:
    - reindex:{job_id}: Any authenticated user (they can only see their org's jobs anyway)
    - search:{request_id}: Any authenticated user (their own request)
    - user:{user_id}: Only the user themselves
    - export:{export_id}: Any authenticated user (they can only see their own exports)
    - entity_update:{entity_type}:{entity_id}: Any authenticated user (for real-time updates)

    Args:
        user_id: User's ID
        channel: Channel to subscribe to

    Returns:
        True if user can subscribe, False otherwise
    """
    if not validate_channel(channel):
        return False

    # User channels require exact match
    if channel.startswith("user:"):
        channel_user_id = channel.split(":")[1]
        return str(user_id) == channel_user_id

    # Reindex, search, export, and entity_update channels are allowed for any authenticated user
    # (They'll only receive messages for their own organization's jobs/entities anyway)
    return True


async def ping_loop(
    websocket: WebSocket,
    connection_id: str,
    manager: ConnectionManager,
) -> None:
    """
    Send periodic ping messages to keep the connection alive.

    Args:
        websocket: WebSocket connection
        connection_id: Connection identifier
        manager: Connection manager
    """
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL)

            if websocket.client_state != WebSocketState.CONNECTED:
                break

            try:
                ping_message = WebSocketMessage(
                    type=MessageType.PING,
                    channel="system",
                    data={},
                )
                await websocket.send_text(ping_message.to_json())
            except Exception as e:
                logger.debug(f"Ping failed for {connection_id}: {e}")
                break
    except asyncio.CancelledError:
        pass


async def receive_loop(
    websocket: WebSocket,
    connection_id: str,
    manager: ConnectionManager,
    user_id: UUID,
) -> None:
    """
    Handle incoming WebSocket messages.

    Supports:
    - subscribe: Subscribe to a channel
    - unsubscribe: Unsubscribe from a channel
    - pong: Response to ping

    Args:
        websocket: WebSocket connection
        connection_id: Connection identifier
        manager: Connection manager
        user_id: Authenticated user ID
    """
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "subscribe":
                channel = data.get("channel")
                if channel and can_subscribe_to_channel(user_id, channel):
                    await manager.subscribe(connection_id, channel)
                    # Send confirmation
                    confirm = WebSocketMessage(
                        type=MessageType.DELTA,
                        channel="system",
                        data={"subscribed": channel},
                    )
                    await websocket.send_text(confirm.to_json())
                else:
                    error = WebSocketMessage(
                        type=MessageType.ERROR,
                        channel="system",
                        data={"error": f"Cannot subscribe to channel: {channel}"},
                    )
                    await websocket.send_text(error.to_json())

            elif action == "unsubscribe":
                channel = data.get("channel")
                if channel:
                    await manager.unsubscribe(connection_id, channel)
                    confirm = WebSocketMessage(
                        type=MessageType.DELTA,
                        channel="system",
                        data={"unsubscribed": channel},
                    )
                    await websocket.send_text(confirm.to_json())

            elif action == "pong":
                # Client responded to ping, connection is alive
                pass

    except WebSocketDisconnect:
        raise
    except Exception as e:
        logger.error(f"Error in receive loop for {connection_id}: {e}")
        raise


@router.websocket("/connect")
async def websocket_connect(
    websocket: WebSocket,
    channels: list[str] = Query(default=[]),
) -> None:
    """
    WebSocket connection endpoint.

    Authenticates via cookie (access_token) and subscribes to requested channels.

    Query Parameters:
        channels: List of channels to subscribe to on connect

    Channel Types:
        - reindex:{job_id} - Reindex progress updates
        - search:{request_id} - AI search streaming
        - user:{user_id} - User notifications
        - entity_update:{entity_type}:{entity_id} - Entity modification notifications

    Message Format (incoming):
        {
            "action": "subscribe" | "unsubscribe" | "pong",
            "channel": "channel_name"
        }

    Message Format (outgoing):
        {
            "type": "delta" | "progress" | "completed" | "failed" | "error" | "ping" | "pong",
            "channel": "channel_name",
            "data": { ... },
            "timestamp": "ISO8601 timestamp"
        }

    Entity Update Message Data:
        {
            "type": "entity_update",
            "entity_type": "document" | "custom_asset",
            "entity_id": "uuid",
            "organization_id": "uuid",
            "updated_by": "uuid"
        }
    """
    manager = get_connection_manager()
    connection_id = str(uuid4())

    # Authenticate using cookie or query parameter
    user = await authenticate_websocket(websocket)

    if user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Validate requested channels
    valid_channels = []
    for channel in channels:
        if can_subscribe_to_channel(user.user_id, channel):
            valid_channels.append(channel)
        else:
            logger.warning(
                f"User {user.user_id} denied access to channel {channel}"
            )

    # Accept connection and subscribe to channels
    try:
        await manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user.user_id,
            channels=valid_channels,
        )

        # Start ping loop
        ping_task = asyncio.create_task(
            ping_loop(websocket, connection_id, manager)
        )

        try:
            # Handle incoming messages
            await receive_loop(websocket, connection_id, manager, user.user_id)
        finally:
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket {connection_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
    finally:
        await manager.disconnect(connection_id)
