"""
OAuth SSO Router

Provides endpoints for OAuth/SSO authentication:
- Get available providers
- Initialize OAuth flow
- Handle OAuth callback
- Link/unlink OAuth accounts
"""

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Response, status

from src.config import get_settings
from src.core.auth import CurrentActiveUser, UserPrincipal
from src.core.cache import get_redis
from src.core.database import DbSession
from src.core.security import (
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
)
from src.models.contracts.oauth_config import (
    LinkedAccountResponse,
    LinkedAccountsResponse,
    OAuthCallbackRequest,
    OAuthInitResponse,
    OAuthProviderInfo,
    OAuthProvidersResponse,
    OAuthTokenResponse,
)
from src.models.enums import AuditAction
from src.repositories.user import UserRepository
from src.services.audit_service import get_audit_service
from src.services.oauth_config_service import OAuthConfigService
from src.services.oauth_sso import OAuthError, OAuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oauth", tags=["OAuth SSO"])


# Redis key prefixes and TTLs
OAUTH_STATE_PREFIX = "oauth_state:"
OAUTH_STATE_TTL = 600  # 10 minutes


def _oauth_state_key(state: str) -> str:
    """Generate Redis key for OAuth state."""
    return f"{OAUTH_STATE_PREFIX}{state}"


# =============================================================================
# Cookie Helpers
# =============================================================================


def _set_oauth_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    """
    Set HttpOnly authentication cookies for OAuth login.

    Browser clients get XSS protection from HttpOnly cookies.

    Args:
        response: FastAPI response object
        access_token: JWT access token
        refresh_token: JWT refresh token
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

    # CSRF token cookie (JS readable for X-CSRF-Token header)
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # JS needs to read this
        secure=secure,
        samesite="strict",
        max_age=30 * 60,  # Match access token
        path="/",
    )


# Provider display names and icons
PROVIDER_INFO = {
    "microsoft": {"display_name": "Microsoft", "icon": "microsoft"},
    "google": {"display_name": "Google", "icon": "google"},
    "oidc": {"display_name": "SSO", "icon": "key"},
}


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/providers", response_model=OAuthProvidersResponse)
async def get_oauth_providers(db: DbSession) -> OAuthProvidersResponse:
    """
    Get available OAuth providers.

    Returns list of configured OAuth providers that can be used for login.
    This endpoint is public (no authentication required).

    Returns:
        List of available OAuth providers with display info
    """
    oauth_service = OAuthService(db)
    available = await oauth_service.get_available_providers()

    providers = []
    for name in available:
        info = PROVIDER_INFO.get(name, {"display_name": name.title(), "icon": None})

        # For OIDC, try to get the custom display name
        if name == "oidc":
            try:
                config = await oauth_service.get_provider_config("oidc")
                if config.get("display_name"):
                    info["display_name"] = config["display_name"]
            except OAuthError:
                pass

        providers.append(
            OAuthProviderInfo(
                name=name,
                display_name=info.get("display_name") or name.title(),
                icon=info.get("icon"),
            )
        )

    return OAuthProvidersResponse(providers=providers)


@router.get("/init/{provider}", response_model=OAuthInitResponse)
async def init_oauth(
    provider: str,
    db: DbSession,
    redirect_uri: str = Query(..., description="Frontend callback URL"),
) -> OAuthInitResponse:
    """
    Initialize OAuth login flow.

    Generates authorization URL with PKCE challenge for secure OAuth flow.
    The PKCE code_verifier is stored server-side in Redis, bound to the state.
    This endpoint is public (no authentication required).

    Args:
        provider: OAuth provider name (microsoft, google, oidc)
        redirect_uri: Frontend callback URL

    Returns:
        Authorization URL and state for CSRF protection

    Security:
        - State is used for CSRF protection
        - PKCE verifier is stored server-side (never sent to client)
        - State can only be used once and expires after 10 minutes
    """
    oauth_service = OAuthService(db)

    try:
        # Generate PKCE values and state
        code_verifier = OAuthService.generate_code_verifier()
        state = OAuthService.generate_state()

        authorization_url = await oauth_service.get_authorization_url(
            provider=provider,
            redirect_uri=redirect_uri,
            state=state,
            code_verifier=code_verifier,
        )

        # Store state -> {code_verifier, redirect_uri} binding in Redis
        r = await get_redis()
        state_data = json.dumps(
            {
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
                "provider": provider,
            }
        )
        await r.setex(
            _oauth_state_key(state),
            OAUTH_STATE_TTL,
            state_data,
        )

        logger.info(
            f"OAuth flow initiated for provider: {provider}",
            extra={"provider": provider, "state": state[:8] + "..."},
        )

        return OAuthInitResponse(
            authorization_url=authorization_url,
            state=state,
        )

    except OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/callback", response_model=OAuthTokenResponse)
async def oauth_callback(
    callback_data: OAuthCallbackRequest,
    response: Response,
    db: DbSession,
) -> OAuthTokenResponse:
    """
    Complete OAuth login flow.

    Called by frontend after receiving callback from OAuth provider.
    Validates state, retrieves PKCE verifier from Redis, exchanges code for tokens.
    This endpoint is public (no authentication required).

    OAuth users bypass MFA - the OAuth provider is trusted for authentication.

    Sets HttpOnly cookies for browser clients in addition to returning tokens in
    the response body. This provides defense-in-depth: browser clients get XSS
    protection from HttpOnly cookies, while API clients can use the response body.

    Args:
        callback_data: OAuth callback data with code and state
        response: FastAPI response for setting cookies

    Returns:
        JWT access and refresh tokens (also sets cookies)

    Raises:
        HTTPException: If OAuth flow fails or user cannot be provisioned

    Security:
        - State is validated against Redis (CSRF protection)
        - PKCE verifier is retrieved from Redis (never sent by client)
        - State is single-use (deleted after retrieval)
    """
    oauth_service = OAuthService(db)
    user_repo = UserRepository(db)

    # Validate state and retrieve PKCE verifier + redirect_uri from Redis
    r = await get_redis()
    state_key = _oauth_state_key(callback_data.state)
    state_data_raw = await r.get(state_key)

    if not state_data_raw:
        logger.warning(
            "OAuth callback with invalid or expired state",
            extra={
                "state": callback_data.state[:8] + "..."
                if callback_data.state
                else "none"
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    # Delete state immediately (single-use)
    await r.delete(state_key)

    # Parse state data (contains code_verifier and redirect_uri)
    if isinstance(state_data_raw, bytes):
        state_data_raw = state_data_raw.decode("utf-8")

    try:
        state_data = json.loads(state_data_raw)
        code_verifier = state_data["code_verifier"]
        redirect_uri = state_data["redirect_uri"]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Invalid OAuth state data format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state data",
        ) from e

    try:
        # Exchange code for tokens using server-side verifier
        tokens = await oauth_service.exchange_code_for_tokens(
            provider=callback_data.provider,
            code=callback_data.code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

        # Get user info from provider
        user_info = await oauth_service.get_user_info(
            provider=callback_data.provider,
            tokens=tokens,
        )

        if not user_info.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth provider did not return email address",
            )

    except OAuthError as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Check if user already has an OAuth account linked
    existing_user = await oauth_service.find_user_by_oauth(
        provider=user_info.provider,
        provider_user_id=user_info.provider_user_id,
    )

    if existing_user:
        # Existing OAuth user - update last login
        user = existing_user
        user.last_login = datetime.now(UTC)

        # Update OAuth account
        await oauth_service.link_oauth_account(user, user_info, tokens)
        await db.commit()

    else:
        # Check if user exists by email
        user = await user_repo.get_by_email(user_info.email)

        if user:
            # Existing user - link OAuth account
            user.last_login = datetime.now(UTC)
            await oauth_service.link_oauth_account(user, user_info, tokens)
            await db.commit()
        else:
            # New user - validate domain whitelist before creating
            oauth_config_service = OAuthConfigService(db)
            allowed_domain = await oauth_config_service.get_allowed_domain()

            if allowed_domain:
                # Domain whitelist is configured - validate email domain
                email_domain = user_info.email.split("@")[1].lower()
                if email_domain != allowed_domain.lower():
                    logger.warning(
                        f"OAuth auto-provisioning rejected for domain: {email_domain}",
                        extra={
                            "email": user_info.email,
                            "provider": callback_data.provider,
                            "allowed_domain": allowed_domain,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Your email domain is not authorized for auto-provisioning. Please contact your administrator.",
                    )

            # Create account and organization
            user = await user_repo.create_user(
                email=user_info.email,
                name=user_info.name,
                hashed_password=None,  # OAuth users don't have passwords
            )

            # Link OAuth account
            await oauth_service.link_oauth_account(user, user_info, tokens)
            user.last_login = datetime.now(UTC)
            await db.commit()

            logger.info(
                f"Created new user via OAuth: {user.email}",
                extra={
                    "user_id": str(user.id),
                    "provider": callback_data.provider,
                },
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Build JWT claims
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "role": user.role.value,
        "oauth_provider": callback_data.provider,  # Mark as OAuth login
    }

    # Generate tokens
    access_token = create_access_token(data=token_data)
    refresh_token_str, _jti = create_refresh_token(data={"sub": str(user.id)})

    # Audit log - successful OAuth login
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
        actor_label=f"oauth:{callback_data.provider}",
    )

    logger.info(
        f"OAuth login successful: {user.email}",
        extra={
            "user_id": str(user.id),
            "provider": callback_data.provider,
            "oauth_user_id": user_info.provider_user_id,
        },
    )

    # Set HttpOnly cookies for browser clients (XSS protection)
    _set_oauth_auth_cookies(response, access_token, refresh_token_str)

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
    )


# =============================================================================
# Account Linking (for authenticated users)
# =============================================================================


@router.get("/accounts", response_model=LinkedAccountsResponse)
async def get_linked_accounts(
    current_user: CurrentActiveUser,
    db: DbSession,
) -> LinkedAccountsResponse:
    """
    Get OAuth accounts linked to current user.

    Returns:
        List of linked OAuth accounts
    """
    oauth_service = OAuthService(db)
    accounts = await oauth_service.get_user_oauth_accounts(current_user.user_id)

    return LinkedAccountsResponse(
        accounts=[
            LinkedAccountResponse(
                provider=acc.provider_id,
                provider_email=acc.email,
                linked_at=acc.created_at.isoformat(),
                last_used_at=acc.last_login.isoformat() if acc.last_login else None,
            )
            for acc in accounts
        ]
    )


@router.delete("/accounts/{provider}")
async def unlink_oauth_account(
    provider: str,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> dict:
    """
    Unlink an OAuth account from current user.

    User must have password set or another OAuth account to unlink.

    Args:
        provider: OAuth provider to unlink

    Returns:
        Success message

    Raises:
        HTTPException: If account not found or user would be locked out
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    oauth_service = OAuthService(db)

    # Check if user would be locked out
    accounts = await oauth_service.get_user_oauth_accounts(user.id)
    has_password = user.hashed_password is not None
    other_oauth = [a for a in accounts if a.provider_id != provider]

    if not has_password and not other_oauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink: You need a password or another OAuth account to log in",
        )

    # Unlink account
    unlinked = await oauth_service.unlink_oauth_account(user.id, provider)
    if not unlinked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} account linked",
        )

    await db.commit()

    logger.info(
        f"OAuth account unlinked: {provider}",
        extra={"user_id": str(user.id), "provider": provider},
    )

    return {"message": f"{provider.title()} account unlinked"}
