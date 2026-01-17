"""Pydantic contracts (API request/response schemas)."""

from src.models.contracts.access_tracking import (
    FrequentItem,
    RecentItem,
)
from src.models.contracts.api_key import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyPublic,
)
from src.models.contracts.attachment import (
    AttachmentCreate,
    AttachmentDownloadResponse,
    AttachmentList,
    AttachmentPublic,
    AttachmentUploadResponse,
    DocumentImageCreate,
    DocumentImageUploadResponse,
)
from src.models.contracts.auth import (
    LoginRequest,
    LogoutResponse,
    MFAEnrollVerifyResponse,
    MFARequiredResponse,
    MFASetupResponse,
    MFAVerifyRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.models.contracts.chat import (
    ChatMessage,
    ChatRequest,
    ChatStartResponse,
)
from src.models.contracts.common import (
    ErrorResponse,
    HealthResponse,
)
from src.models.contracts.configuration import (
    ConfigurationCreate,
    ConfigurationPublic,
    ConfigurationStatusCreate,
    ConfigurationStatusPublic,
    ConfigurationTypeCreate,
    ConfigurationTypePublic,
    ConfigurationUpdate,
)
from src.models.contracts.custom_asset import (
    CustomAssetCreate,
    CustomAssetPublic,
    CustomAssetReveal,
    CustomAssetTypeCreate,
    CustomAssetTypePublic,
    CustomAssetTypeReorder,
    CustomAssetTypeUpdate,
    CustomAssetUpdate,
    FieldDefinition,
)
from src.models.contracts.document import (
    DocumentCreate,
    DocumentPublic,
    DocumentUpdate,
    FolderList,
)
from src.models.contracts.location import (
    LocationCreate,
    LocationPublic,
    LocationUpdate,
)
from src.models.contracts.organization import (
    OrganizationCreate,
    OrganizationPublic,
    OrganizationUpdate,
)
from src.models.contracts.passkeys import (
    PasskeyAuthOptionsRequest,
    PasskeyAuthOptionsResponse,
    PasskeyAuthVerifyRequest,
    PasskeyDeleteResponse,
    PasskeyListResponse,
    PasskeyPublic,
    PasskeyRegistrationOptionsRequest,
    PasskeyRegistrationOptionsResponse,
    PasskeyRegistrationVerifyRequest,
    PasskeyRegistrationVerifyResponse,
)
from src.models.contracts.password import (
    PasswordCreate,
    PasswordPublic,
    PasswordReveal,
    PasswordUpdate,
)
from src.models.contracts.relationship import (
    RelatedEntity,
    RelatedItemsResponse,
    RelationshipCreate,
    RelationshipPublic,
)
from src.models.contracts.search import (
    SearchResponse,
    SearchResult,
)
from src.models.contracts.user_preferences import (
    ColumnPreferences,
    PreferencesData,
    UserPreferencesCreate,
    UserPreferencesPublic,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)

__all__ = [
    # Access Tracking
    "FrequentItem",
    "RecentItem",
    # API Key
    "ApiKeyCreate",
    "ApiKeyCreated",
    "ApiKeyPublic",
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "MFARequiredResponse",
    "MFASetupResponse",
    "MFAVerifyRequest",
    "MFAEnrollVerifyResponse",
    "UserResponse",
    "LogoutResponse",
    # Passkeys
    "PasskeyRegistrationOptionsRequest",
    "PasskeyRegistrationOptionsResponse",
    "PasskeyRegistrationVerifyRequest",
    "PasskeyRegistrationVerifyResponse",
    "PasskeyAuthOptionsRequest",
    "PasskeyAuthOptionsResponse",
    "PasskeyAuthVerifyRequest",
    "PasskeyPublic",
    "PasskeyListResponse",
    "PasskeyDeleteResponse",
    # Organization
    "OrganizationCreate",
    "OrganizationUpdate",
    "OrganizationPublic",
    # Location
    "LocationCreate",
    "LocationUpdate",
    "LocationPublic",
    # Document
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentPublic",
    "FolderList",
    # Password
    "PasswordCreate",
    "PasswordUpdate",
    "PasswordPublic",
    "PasswordReveal",
    # Configuration
    "ConfigurationTypeCreate",
    "ConfigurationTypePublic",
    "ConfigurationStatusCreate",
    "ConfigurationStatusPublic",
    "ConfigurationCreate",
    "ConfigurationUpdate",
    "ConfigurationPublic",
    # Custom Asset
    "FieldDefinition",
    "CustomAssetTypeCreate",
    "CustomAssetTypeUpdate",
    "CustomAssetTypePublic",
    "CustomAssetTypeReorder",
    "CustomAssetCreate",
    "CustomAssetUpdate",
    "CustomAssetPublic",
    "CustomAssetReveal",
    # Attachment
    "AttachmentCreate",
    "AttachmentPublic",
    "AttachmentUploadResponse",
    "AttachmentDownloadResponse",
    "AttachmentList",
    "DocumentImageCreate",
    "DocumentImageUploadResponse",
    # Common
    "ErrorResponse",
    "HealthResponse",
    # Relationship
    "RelationshipCreate",
    "RelationshipPublic",
    "RelatedEntity",
    "RelatedItemsResponse",
    # Search
    "SearchResult",
    "SearchResponse",
    # Chat
    "ChatMessage",
    "ChatRequest",
    "ChatStartResponse",
    # User Preferences
    "ColumnPreferences",
    "PreferencesData",
    "UserPreferencesCreate",
    "UserPreferencesUpdate",
    "UserPreferencesPublic",
    "UserPreferencesResponse",
]
