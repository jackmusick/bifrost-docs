"""
Authentication and Authorization

Provides FastAPI dependencies for authentication and authorization.
Supports JWT bearer token authentication with user context injection.
"""

import logging
from dataclasses import dataclass
from datetime import UTC
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.database import DbSession
from src.core.security import decode_token, hash_api_key
from src.models.enums import UserRole

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class UserPrincipal:
    """
    Authenticated user principal.

    Represents an authenticated user with their identity and permissions.
    All user info is extracted from JWT claims (no database lookup required).
    """

    user_id: UUID
    email: str
    name: str = ""
    role: UserRole = UserRole.CONTRIBUTOR
    is_active: bool = True
    is_verified: bool = False
    # API key authentication
    api_key_id: UUID | None = None

    @property
    def is_platform_admin(self) -> bool:
        """Check if user is a platform admin (owner or administrator)."""
        return self.role in (UserRole.OWNER, UserRole.ADMINISTRATOR)


@dataclass
class ExecutionContext:
    """
    Execution context for request handling.

    Contains the authenticated user, organization scope, and database session.

    Scope rules:
    - Regular users: org_id = user's current organization (always set)
    - Platform users: org_id = None (global access)
    """

    user: UserPrincipal
    org_id: UUID | None  # Execution scope (None only for platform user)
    db: "AsyncSession"

    @property
    def scope(self) -> str:
        """Get the scope string for data access (org_id or 'GLOBAL')."""
        return str(self.org_id) if self.org_id else "GLOBAL"

    @property
    def user_id(self) -> str:
        """Get user ID as string."""
        return str(self.user.user_id)

    @property
    def is_global_scope(self) -> bool:
        """Check if operating in global scope (platform user only)."""
        return self.org_id is None

    @property
    def is_platform_admin(self) -> bool:
        """Check if user is a platform admin (superuser)."""
        return self.user.is_platform_admin


async def _authenticate_api_key(
    db: "AsyncSession", api_key: str
) -> UserPrincipal | None:
    """
    Authenticate using an API key.

    Args:
        db: Database session
        api_key: The API key from the Authorization header

    Returns:
        UserPrincipal if valid, None otherwise
    """
    from sqlalchemy import select

    from src.models.orm.api_key import APIKey
    from src.models.orm.user import User

    key_hash = hash_api_key(api_key)

    # Query for the API key
    stmt = select(APIKey).where(APIKey.key_hash == key_hash)
    result = await db.execute(stmt)
    api_key_obj = result.scalar_one_or_none()

    if not api_key_obj:
        return None

    # Check if expired
    if api_key_obj.is_expired:
        return None

    # Get the user
    user_stmt = select(User).where(User.id == api_key_obj.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user or not user.is_active:
        return None

    # Update last used timestamp
    from datetime import datetime

    api_key_obj.last_used_at = datetime.now(UTC)
    await db.flush()

    return UserPrincipal(
        user_id=user.id,
        email=user.email,
        name=user.name or "",
        role=user.role,
        is_active=user.is_active,
        is_verified=True,
        api_key_id=api_key_obj.id,
    )


async def get_current_user_optional(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> UserPrincipal | None:
    """
    Get the current user from JWT token or API key (optional).

    Checks for authentication in this order:
    1. Authorization: Bearer header (JWT or API key)
    2. access_token cookie (for browser clients)

    Returns None if no token is provided or token is invalid.
    Does not raise an exception for unauthenticated requests.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials from request
        db: Database session

    Returns:
        UserPrincipal if authenticated, None otherwise
    """
    token = None

    # Try Authorization header first (API clients)
    if credentials:
        token = credentials.credentials
    # Fall back to cookie (browser clients)
    elif "access_token" in request.cookies:
        token = request.cookies["access_token"]

    if not token:
        return None

    # Check if it's an API key (starts with bifrost_docs)
    if token.startswith("bifrost_docs"):
        return await _authenticate_api_key(db, token)

    # Otherwise treat as JWT
    payload = decode_token(token, expected_type="access")

    if payload is None:
        return None

    # Extract user ID from token
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
            f"Token for user {user_id} missing required email claim.")
        return None

    # Get role from token (default to CONTRIBUTOR for backwards compatibility)
    role_str = payload.get("role", "contributor")
    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.CONTRIBUTOR

    return UserPrincipal(
        user_id=user_id,
        email=payload.get("email", ""),
        name=payload.get("name", ""),
        role=role,
        is_active=True,
        is_verified=True,
        api_key_id=None,
    )


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> UserPrincipal:
    """
    Get the current user from JWT token (required).

    Raises HTTPException if not authenticated.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials from request
        db: Database session

    Returns:
        UserPrincipal for authenticated user

    Raises:
        HTTPException: If not authenticated or token is invalid
    """
    user = await get_current_user_optional(request, credentials, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    user: Annotated[UserPrincipal, Depends(get_current_user)],
) -> UserPrincipal:
    """
    Get the current active user.

    Raises HTTPException if user is inactive.

    Args:
        user: Current user from authentication

    Returns:
        UserPrincipal for active user

    Raises:
        HTTPException: If user is inactive
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


async def get_current_admin(
    user: Annotated[UserPrincipal, Depends(get_current_active_user)],
) -> UserPrincipal:
    """
    Get the current admin user (owner or administrator).

    Raises HTTPException if user is not an admin.

    Args:
        user: Current active user

    Returns:
        UserPrincipal for admin user

    Raises:
        HTTPException: If user is not an administrator
    """
    if user.role not in (UserRole.OWNER, UserRole.ADMINISTRATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return user


def require_role(min_role: UserRole):
    """
    Dependency factory that checks if user has minimum required role.

    Role hierarchy (lowest to highest): READER < CONTRIBUTOR < ADMINISTRATOR < OWNER

    Args:
        min_role: Minimum role required to access the endpoint

    Returns:
        Dependency function that validates user role
    """
    role_hierarchy = [
        UserRole.READER,
        UserRole.CONTRIBUTOR,
        UserRole.ADMINISTRATOR,
        UserRole.OWNER,
    ]

    async def check_role(
        user: Annotated[UserPrincipal, Depends(get_current_active_user)],
    ) -> UserPrincipal:
        user_level = role_hierarchy.index(user.role)
        required_level = role_hierarchy.index(min_role)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {min_role.value} role or higher",
            )
        return user

    return check_role


# Legacy alias for backward compatibility
async def get_current_superuser(
    user: Annotated[UserPrincipal, Depends(get_current_active_user)],
) -> UserPrincipal:
    """Legacy alias for get_current_admin. Use get_current_admin instead."""
    return await get_current_admin(user)


# Dependency for requiring platform admin access (legacy)
RequirePlatformAdmin = Depends(get_current_admin)


async def get_execution_context(
    user: Annotated[UserPrincipal, Depends(get_current_active_user)],
    db: DbSession,
) -> ExecutionContext:
    """
    Get execution context for HTTP requests.

    All users operate in global scope - they access resources based on
    their permissions and relationships, not organization scoping.

    Admin-only capabilities are controlled by endpoint-level authorization,
    not by ExecutionContext scope.

    Args:
        user: Current active user
        db: Database session

    Returns:
        ExecutionContext with user and global scope
    """
    return ExecutionContext(
        user=user,
        org_id=None,
        db=db,
    )


# Type aliases for dependency injection
CurrentUser = Annotated[UserPrincipal, Depends(get_current_user)]
CurrentActiveUser = Annotated[UserPrincipal, Depends(get_current_active_user)]
CurrentAdmin = Annotated[UserPrincipal, Depends(get_current_admin)]
Context = Annotated[ExecutionContext, Depends(get_execution_context)]

# Role-based dependencies
RequireReader = Annotated[UserPrincipal,
                          Depends(require_role(UserRole.READER))]
RequireContributor = Annotated[UserPrincipal,
                               Depends(require_role(UserRole.CONTRIBUTOR))]
RequireAdmin = Annotated[UserPrincipal, Depends(
    require_role(UserRole.ADMINISTRATOR))]
RequireOwner = Annotated[UserPrincipal, Depends(require_role(UserRole.OWNER))]

# Keep backward compatibility
CurrentSuperuser = CurrentAdmin
