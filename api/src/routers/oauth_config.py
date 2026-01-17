"""
OAuth SSO Configuration Router.

API endpoints for managing OAuth SSO provider configurations.
Platform admin only - used in the Settings page.
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import CurrentSuperuser
from src.core.database import get_db
from src.models.contracts.oauth_config import (
    GoogleOAuthConfigRequest,
    MicrosoftOAuthConfigRequest,
    OAuthConfigListResponse,
    OAuthConfigTestRequest,
    OAuthConfigTestResponse,
    OAuthProviderConfigResponse,
    OAuthSSOProvider,
    OIDCConfigRequest,
)
from src.services.oauth_config_service import OAuthConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings/oauth", tags=["OAuth SSO Config"])


def _get_callback_url(request: Request) -> str:
    """Get the OAuth callback URL based on the request origin."""
    # Use X-Forwarded headers if behind a proxy, otherwise use request base URL
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))
    return f"{proto}://{host}/auth/oauth/callback"


@router.get(
    "",
    response_model=OAuthConfigListResponse,
    summary="List OAuth provider configurations",
    description="Get configuration status for all OAuth SSO providers (Platform admin only)",
)
async def list_oauth_configs(
    request: Request,
    user: CurrentSuperuser,
    db: AsyncSession = Depends(get_db),
) -> OAuthConfigListResponse:
    """
    List all OAuth provider configurations with their status.

    Returns configuration details for Microsoft, Google, and OIDC providers.
    Client secrets are never exposed - only a flag indicating if they are set.
    """
    service = OAuthConfigService(db)
    providers = await service.get_all_provider_configs()
    callback_url = _get_callback_url(request)

    return OAuthConfigListResponse(
        providers=providers,
        callback_url=callback_url,
    )


@router.get(
    "/{provider}",
    response_model=OAuthProviderConfigResponse,
    summary="Get OAuth provider configuration",
    description="Get configuration for a specific OAuth provider (Platform admin only)",
)
async def get_oauth_config(
    provider: OAuthSSOProvider,
    user: CurrentSuperuser,
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderConfigResponse:
    """Get configuration for a specific OAuth provider."""
    service = OAuthConfigService(db)
    config = await service.get_provider_config(provider)

    if config:
        return OAuthProviderConfigResponse(
            provider=provider,
            configured=config.is_complete,
            client_id=config.client_id,
            client_secret_set=bool(config.client_secret),
            tenant_id=config.tenant_id if provider == "microsoft" else None,
            discovery_url=config.discovery_url if provider == "oidc" else None,
            display_name=config.display_name if provider == "oidc" else None,
        )

    return OAuthProviderConfigResponse(
        provider=provider,
        configured=False,
    )


@router.put(
    "/microsoft",
    response_model=OAuthProviderConfigResponse,
    summary="Configure Microsoft OAuth",
    description="Set up Microsoft Entra ID (Azure AD) OAuth SSO (Platform admin only)",
)
async def set_microsoft_config(
    config: MicrosoftOAuthConfigRequest,
    user: CurrentSuperuser,
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderConfigResponse:
    """
    Configure Microsoft Entra ID (Azure AD) OAuth SSO.

    **Setup Instructions:**
    1. Go to Azure Portal > Microsoft Entra ID > App registrations
    2. Create a new registration or select an existing one
    3. Under "Authentication", add a Web platform redirect URI:
       `{your-domain}/auth/oauth/callback`
    4. Under "Certificates & secrets", create a new client secret
    5. Copy the Application (client) ID and secret value

    **Tenant ID Options:**
    - `common` - Any Microsoft account (personal + work/school) - multi-tenant
    - `organizations` - Work/school accounts only
    - `consumers` - Personal Microsoft accounts only
    - Specific tenant ID/domain - Single organization only

    **Required API Permissions:**
    - Microsoft Graph: User.Read (delegated)
    - Microsoft Graph: email (delegated)
    - Microsoft Graph: openid (delegated)
    - Microsoft Graph: profile (delegated)
    """
    service = OAuthConfigService(db)
    await service.set_microsoft_config(config, updated_by=user.email)
    await db.commit()

    return OAuthProviderConfigResponse(
        provider="microsoft",
        configured=True,
        client_id=config.client_id,
        client_secret_set=True,
        tenant_id=config.tenant_id,
    )


@router.put(
    "/google",
    response_model=OAuthProviderConfigResponse,
    summary="Configure Google OAuth",
    description="Set up Google OAuth SSO (Platform admin only)",
)
async def set_google_config(
    config: GoogleOAuthConfigRequest,
    user: CurrentSuperuser,
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderConfigResponse:
    """
    Configure Google OAuth SSO.

    **Setup Instructions:**
    1. Go to Google Cloud Console > APIs & Services > Credentials
    2. Create an OAuth 2.0 Client ID (Web application type)
    3. Add authorized redirect URI:
       `{your-domain}/auth/oauth/callback`
    4. Copy the Client ID and Client secret

    **OAuth Consent Screen:**
    - Configure the OAuth consent screen if not already done
    - Add scopes: email, profile, openid
    - Set user type (Internal for G Suite, External for any Google account)
    """
    service = OAuthConfigService(db)
    await service.set_google_config(config, updated_by=user.email)
    await db.commit()

    return OAuthProviderConfigResponse(
        provider="google",
        configured=True,
        client_id=config.client_id,
        client_secret_set=True,
    )


@router.put(
    "/oidc",
    response_model=OAuthProviderConfigResponse,
    summary="Configure OIDC provider",
    description="Set up a generic OIDC provider for SSO (Platform admin only)",
)
async def set_oidc_config(
    config: OIDCConfigRequest,
    user: CurrentSuperuser,
    db: AsyncSession = Depends(get_db),
) -> OAuthProviderConfigResponse:
    """
    Configure a generic OIDC provider for SSO.

    **Setup Instructions:**
    1. In your OIDC provider (Okta, Auth0, Keycloak, etc.), create a new application
    2. Set the application type to "Web" or "Regular Web Application"
    3. Add the redirect URI:
       `{your-domain}/auth/oauth/callback`
    4. Copy the discovery URL, client ID, and client secret

    **Discovery URL Examples:**
    - Okta: `https://your-org.okta.com/.well-known/openid-configuration`
    - Auth0: `https://your-tenant.auth0.com/.well-known/openid-configuration`
    - Keycloak: `https://your-server/realms/your-realm/.well-known/openid-configuration`

    **Required Scopes:**
    Most OIDC providers should support: openid, email, profile
    """
    service = OAuthConfigService(db)
    await service.set_oidc_config(config, updated_by=user.email)
    await db.commit()

    return OAuthProviderConfigResponse(
        provider="oidc",
        configured=True,
        client_id=config.client_id,
        client_secret_set=True,
        discovery_url=config.discovery_url,
        display_name=config.display_name,
    )


@router.delete(
    "/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete OAuth provider configuration",
    description="Remove configuration for an OAuth provider (Platform admin only)",
)
async def delete_oauth_config(
    provider: OAuthSSOProvider,
    user: CurrentSuperuser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all configuration for a specific OAuth provider."""
    service = OAuthConfigService(db)
    deleted = await service.delete_provider_config(provider)
    await db.commit()

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth provider {provider} not found or already deleted",
        )

    logger.info(f"OAuth config deleted for {provider} by {user.email}")


@router.post(
    "/{provider}/test",
    response_model=OAuthConfigTestResponse,
    summary="Test OAuth provider configuration",
    description="Test connectivity to an OAuth provider (Platform admin only)",
)
async def test_oauth_config(
    provider: OAuthSSOProvider,
    user: CurrentSuperuser,
    test_data: OAuthConfigTestRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> OAuthConfigTestResponse:
    """
    Test OAuth provider configuration by checking the discovery endpoint.

    Can test with:
    - Saved configuration (if no test_data provided)
    - New credentials (if test_data provided) - useful before saving

    The test validates that the discovery endpoint is reachable and returns
    valid OIDC configuration. It does NOT test the actual OAuth flow.
    """
    service = OAuthConfigService(db)

    test_dict = test_data.model_dump(exclude_none=True) if test_data else None
    result = await service.test_provider_config(provider, test_dict)

    return result


# =============================================================================
# Domain Whitelist Configuration
# =============================================================================


@router.get(
    "/domain-whitelist",
    response_model=dict,
    summary="Get OAuth domain whitelist",
    description="Get the allowed domain for OAuth auto-provisioning (Platform admin only)",
)
async def get_domain_whitelist(
    user: CurrentSuperuser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get the allowed domain for OAuth auto-provisioning.

    Returns None if no domain whitelist is configured (all domains allowed).
    """
    service = OAuthConfigService(db)
    allowed_domain = await service.get_allowed_domain()

    return {"allowed_domain": allowed_domain}


@router.put(
    "/domain-whitelist",
    response_model=dict,
    summary="Set OAuth domain whitelist",
    description="Set the allowed domain for OAuth auto-provisioning (Platform admin only)",
)
async def set_domain_whitelist(
    user: CurrentSuperuser,
    domain: str | None = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Set the allowed domain for OAuth auto-provisioning.

    **Args:**
    - domain: The allowed domain (e.g., "company.com"), or null to allow all domains

    **Behavior:**
    - If set, only users with email addresses from this domain can be auto-provisioned via OAuth
    - Existing users can always log in regardless of domain
    - If null/empty, all domains are allowed (default behavior)
    """
    service = OAuthConfigService(db)
    await service.set_allowed_domain(domain, updated_by=user.email)
    await db.commit()

    logger.info(
        f"OAuth domain whitelist updated by {user.email}: {domain or 'disabled'}",
    )

    return {"allowed_domain": domain}
