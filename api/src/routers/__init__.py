"""API routers."""

from src.routers.admin import router as admin_router
from src.routers.ai_settings import router as ai_settings_router
from src.routers.api_keys import router as api_keys_router
from src.routers.attachments import router as attachments_router
from src.routers.audit import org_router as audit_org_router
from src.routers.audit import router as audit_router
from src.routers.auth import router as auth_router
from src.routers.configuration_statuses import router as configuration_statuses_router
from src.routers.configuration_types import router as configuration_types_router
from src.routers.configurations import router as configurations_router
from src.routers.custom_asset_types import router as custom_asset_types_router
from src.routers.custom_assets import router as custom_assets_router
from src.routers.documents import router as documents_router
from src.routers.exports import router as exports_router
from src.routers.global_view import router as global_view_router
from src.routers.health import router as health_router
from src.routers.locations import router as locations_router
from src.routers.me import router as me_router
from src.routers.mfa import router as mfa_router
from src.routers.oauth_config import router as oauth_config_router
from src.routers.oauth_sso import router as oauth_sso_router
from src.routers.organizations import router as organizations_router
from src.routers.passkeys import router as passkeys_router
from src.routers.passwords import router as passwords_router
from src.routers.preferences import router as preferences_router
from src.routers.relationships import router as relationships_router
from src.routers.search import router as search_router
from src.routers.websocket import router as websocket_router

__all__ = [
    "health_router",
    "auth_router",
    "admin_router",
    "ai_settings_router",
    "api_keys_router",
    "audit_router",
    "audit_org_router",
    "mfa_router",
    "passkeys_router",
    "oauth_config_router",
    "oauth_sso_router",
    "organizations_router",
    "global_view_router",
    "locations_router",
    "me_router",
    "documents_router",
    "exports_router",
    "passwords_router",
    "preferences_router",
    "configuration_types_router",
    "configuration_statuses_router",
    "configurations_router",
    "custom_asset_types_router",
    "custom_assets_router",
    "attachments_router",
    "relationships_router",
    "search_router",
    "websocket_router",
]
