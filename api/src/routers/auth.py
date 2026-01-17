"""
Authentication Router

Provides endpoints for user authentication:
- Login (JWT token generation)
- Token refresh with rotation
- Token revocation (logout)
- Current user info
- Registration
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.config import get_settings
from src.core.auth import CurrentActiveUser, UserPrincipal
from src.core.database import DbSession
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    get_password_hash,
    verify_password,
)
from src.models.contracts.auth import (
    LoginResponse,
    LogoutResponse,
    RefreshTokenRequest,
    RegisterRequest,
    SetupPasskeyOptionsRequest,
    SetupPasskeyOptionsResponse,
    SetupPasskeyVerifyRequest,
    SetupPasskeyVerifyResponse,
    SetupStatusResponse,
    TokenResponse,
    UserResponse,
)
from src.models.enums import AuditAction, UserRole
from src.repositories.user import UserRepository
from src.services.audit_service import get_audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# =============================================================================
# Cookie Configuration
# =============================================================================


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Set HttpOnly authentication cookies and CSRF token.

    Cookies are secure, SameSite=Lax, and HttpOnly for XSS protection.
    """
    settings = get_settings()

    # Only use secure cookies in production
    secure = settings.is_production

    # Access token cookie (short-lived)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=30 * 60,  # 30 minutes
        path="/",
    )

    # Refresh token cookie (long-lived)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/",
    )

    # CSRF token cookie (readable by JavaScript)
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=secure,
        samesite="strict",
        max_age=30 * 60,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies on logout."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    response.delete_cookie(key="csrf_token", path="/")


# =============================================================================
# Request/Response Models
# =============================================================================


class RevokeAllResponse(BaseModel):
    """Revoke all sessions response model."""

    message: str
    sessions_revoked: int


class LogoutRequest(BaseModel):
    """Logout request with optional refresh token."""

    refresh_token: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> LoginResponse:
    """
    Login with email and password.

    Args:
        response: FastAPI response object
        form_data: OAuth2 password form with username (email) and password
        db: Database session

    Returns:
        LoginResponse with access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(form_data.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account does not have password authentication enabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.hashed_password):
        # Audit log - failed login (wrong password)
        audit_service = get_audit_service(db)
        await audit_service.log(
            AuditAction.LOGIN_FAILED,
            "user",
            user.id,
            actor_label=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Update last login
    user.last_login = datetime.now(UTC)
    await db.flush()

    # Audit log - successful login
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.LOGIN,
        "user",
        user.id,
        actor=UserPrincipal(
            user_id=user.id,
            email=user.email,
            name=user.name or "",
            role=user.role,
        ),
    )

    # Build JWT claims
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "role": user.role.value,
    }

    # Generate tokens
    access_token = create_access_token(data=token_data)
    refresh_token_str, _jti = create_refresh_token(data={"sub": str(user.id)})

    # Set cookies
    set_auth_cookies(response, access_token, refresh_token_str)

    logger.info(f"User logged in: {user.email}")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: DbSession,
    token_data: RefreshTokenRequest | None = None,
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    The refresh token can be provided in:
    1. Request body (API clients)
    2. HttpOnly cookie (browser clients)

    Args:
        request: FastAPI request object
        response: FastAPI response object
        token_data: Optional refresh token in body
        db: Database session

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    # Get refresh token from body or cookie
    refresh_token_value = None
    if token_data and token_data.refresh_token:
        refresh_token_value = token_data.refresh_token
    else:
        refresh_token_value = request.cookies.get("refresh_token")

    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode with type validation
    payload = decode_token(refresh_token_value, expected_type="refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    from uuid import UUID

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(UUID(user_id))

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Build JWT claims with fresh user info
    new_token_data = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "role": user.role.value,
    }

    # Generate new tokens
    access_token = create_access_token(data=new_token_data)
    new_refresh_token, _jti = create_refresh_token(data={"sub": str(user.id)})

    # Set cookies
    set_auth_cookies(response, access_token, new_refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentActiveUser,
) -> UserResponse:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user (from JWT)

    Returns:
        User information with roles
    """
    return UserResponse(
        id=str(current_user.user_id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        mfa_enabled=False,  # We don't have this in principal, default to False
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> LogoutResponse:
    """
    Logout current user.

    Clears authentication cookies.

    Args:
        response: FastAPI response (to clear cookies)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Logout confirmation
    """
    clear_auth_cookies(response)

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.LOGOUT,
        "user",
        current_user.user_id,
        actor=current_user,
    )

    logger.info(f"User logged out: {current_user.email}")
    return LogoutResponse()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: RegisterRequest,
    db: DbSession,
) -> UserResponse:
    """
    Register a new user.

    Handles three scenarios:
    1. First user in system: Becomes PlatformAdmin
    2. Subsequent users: Regular OrgUser

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user information

    Raises:
        HTTPException: If email already registered
    """
    settings = get_settings()
    user_repo = UserRepository(db)

    # Check if first user (system bootstrap)
    has_users = await user_repo.has_any_users()

    # In production, registration is disabled after first user
    if has_users and not (settings.is_development or settings.is_testing):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registration is disabled. Contact an administrator for access.",
        )

    # Check if email already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    # First user is owner, subsequent users are contributors
    role = UserRole.OWNER if not has_users else UserRole.CONTRIBUTOR

    user = await user_repo.create_user(
        email=user_data.email,
        hashed_password=hashed_password,
        name=user_data.name,
        role=role,
    )

    await db.flush()

    # Audit log - user registration
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.USER_CREATE,
        "user",
        user.id,
        actor_label="self_registration",  # System action for self-registration
    )

    logger.info(
        f"User registered: {user.email}",
        extra={
            "user_id": str(user.id),
            "role": user.role.value,
        },
    )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name or "",
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        mfa_enabled=user.mfa_enabled,
    )


# =============================================================================
# Setup Endpoints (First-Time Platform Configuration)
# =============================================================================


@router.get("/setup/status", response_model=SetupStatusResponse)
async def get_setup_status(
    db: DbSession,
) -> SetupStatusResponse:
    """
    Check if platform setup is needed.

    Returns True if no users exist in the system, indicating
    first-time setup is required.

    Args:
        db: Database session

    Returns:
        SetupStatusResponse with needs_setup flag
    """
    user_repo = UserRepository(db)
    has_users = await user_repo.has_any_users()
    return SetupStatusResponse(needs_setup=not has_users)


@router.post("/setup/passkey/options", response_model=SetupPasskeyOptionsResponse)
async def setup_passkey_options(
    setup_request: SetupPasskeyOptionsRequest,
    db: DbSession,
) -> SetupPasskeyOptionsResponse:
    """
    Start passwordless passkey registration for first-time platform setup.

    This endpoint is ONLY available when no users exist in the system.
    It allows the first user to register with a passkey instead of a password.

    Flow:
    1. Client calls this endpoint with email/name
    2. Server returns WebAuthn options + registration token
    3. Client performs WebAuthn ceremony (Face ID, Touch ID, etc.)
    4. Client calls /auth/setup/passkey/verify with credential

    Args:
        setup_request: Email and optional name for the new account
        db: Database session

    Returns:
        SetupPasskeyOptionsResponse with registration token and WebAuthn options

    Raises:
        HTTPException: If users already exist or email is invalid
    """
    from src.services.passkey_service import PasskeyService

    passkey_service = PasskeyService(db)

    try:
        registration_token, options = await passkey_service.generate_setup_registration_options(
            email=setup_request.email,
            name=setup_request.name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    logger.info(
        f"Passkey setup initiated for first-time registration: {setup_request.email}",
    )

    return SetupPasskeyOptionsResponse(
        registration_token=registration_token,
        options=options,
        expires_in=300,
    )


@router.post("/setup/passkey/verify", response_model=SetupPasskeyVerifyResponse)
async def setup_passkey_verify(
    response: Response,
    verify_request: SetupPasskeyVerifyRequest,
    db: DbSession,
) -> SetupPasskeyVerifyResponse:
    """
    Complete passwordless passkey registration for first-time platform setup.

    This endpoint verifies the WebAuthn credential and creates the user + passkey
    atomically. On success, returns JWT tokens so the user is immediately logged in.

    Args:
        response: FastAPI response object (for setting cookies)
        verify_request: Registration token and WebAuthn credential
        db: Database session

    Returns:
        SetupPasskeyVerifyResponse with user info and JWT tokens

    Raises:
        HTTPException: If token is invalid/expired or verification fails
    """
    import json

    from src.services.passkey_service import PasskeyService

    passkey_service = PasskeyService(db)

    try:
        user, passkey = await passkey_service.verify_setup_registration(
            registration_token=verify_request.registration_token,
            credential_json=json.dumps(verify_request.credential),
            device_name=verify_request.device_name,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    logger.info(
        f"Passkey setup completed for first-time registration: {user.email}",
        extra={"user_id": str(user.id), "passkey_id": str(passkey.id)},
    )

    # Generate tokens for immediate login
    # First user is always OWNER
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "role": user.role.value,
    }

    access_token = create_access_token(data=token_data)
    refresh_token_str, _jti = create_refresh_token(data={"sub": str(user.id)})

    # Set cookies for browser clients
    set_auth_cookies(response, access_token, refresh_token_str)

    return SetupPasskeyVerifyResponse(
        user_id=str(user.id),
        email=user.email,
        access_token=access_token,
        refresh_token=refresh_token_str,
    )
