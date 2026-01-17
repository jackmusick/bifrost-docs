"""Bifrost Docs Models.

ORM models (database tables):
    from src.models import Organization, User
    from src.models.orm import Organization, User

Pydantic contracts (API request/response):
    from src.models import OrganizationCreate, OrganizationPublic
    from src.models.contracts import OrganizationCreate, OrganizationPublic

Enums:
    from src.models import UserType
    from src.models.enums import UserType
"""

# ORM models (database tables)
# Pydantic contracts (API request/response)
from src.models.contracts import (
    ErrorResponse,
    HealthResponse,
    LoginRequest,
    LogoutResponse,
    MFAEnrollVerifyResponse,
    MFARequiredResponse,
    MFASetupResponse,
    MFAVerifyRequest,
    OrganizationCreate,
    OrganizationPublic,
    OrganizationUpdate,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

# Enums
from src.models.enums import (
    MFAMethodStatus,
    MFAMethodType,
    UserType,
)
from src.models.orm import (
    APIKey,
    Base,
    MFARecoveryCode,
    Organization,
    Session,
    User,
    UserMFAMethod,
    UserPasskey,
)

# Combine all exports
__all__ = [
    # Base
    "Base",
    # ORM models
    "Organization",
    "User",
    "Session",
    "UserPasskey",
    "UserMFAMethod",
    "MFARecoveryCode",
    "APIKey",
    # Enums
    "UserType",
    "MFAMethodType",
    "MFAMethodStatus",
    # Contracts (Auth)
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
    # Contracts (Organization)
    "OrganizationCreate",
    "OrganizationUpdate",
    "OrganizationPublic",
    # Contracts (Common)
    "ErrorResponse",
    "HealthResponse",
]
