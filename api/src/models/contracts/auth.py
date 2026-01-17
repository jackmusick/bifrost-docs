"""
Authentication contracts (API request/response schemas).
"""

from pydantic import BaseModel, ConfigDict, EmailStr

from src.models.enums import UserRole


class LoginRequest(BaseModel):
    """Login request model."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """User registration request model."""

    email: EmailStr
    password: str
    name: str | None = None


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str


class MFARequiredResponse(BaseModel):
    """Response when MFA verification is required."""

    mfa_required: bool = True
    mfa_token: str
    available_methods: list[str]
    expires_in: int = 300  # 5 minutes


class MFASetupResponse(BaseModel):
    """MFA setup response with secret."""

    secret: str
    qr_code_uri: str
    provisioning_uri: str
    issuer: str
    account_name: str
    is_existing: bool = False


class MFAVerifyRequest(BaseModel):
    """Request to verify MFA code during login."""

    mfa_token: str
    code: str
    trust_device: bool = False
    device_name: str | None = None


class MFAEnrollVerifyResponse(BaseModel):
    """Response after completing MFA enrollment."""

    success: bool
    recovery_codes: list[str]
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User response model."""

    id: str
    email: str
    name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    mfa_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class LogoutResponse(BaseModel):
    """Logout response model."""

    message: str = "Logged out successfully"


class LoginResponse(BaseModel):
    """Unified login response that can be Token or MFA response."""

    # Token fields (when MFA not required or after MFA verification)
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    # MFA fields (when MFA required)
    mfa_required: bool = False
    mfa_setup_required: bool = False
    mfa_token: str | None = None
    available_methods: list[str] | None = None
    expires_in: int | None = None


# =============================================================================
# Setup Endpoints (First-Time Platform Configuration)
# =============================================================================


class SetupStatusResponse(BaseModel):
    """Response for setup status check."""

    needs_setup: bool


class SetupPasskeyOptionsRequest(BaseModel):
    """Request to start passkey registration during setup."""

    email: EmailStr
    name: str | None = None


class SetupPasskeyOptionsResponse(BaseModel):
    """Response with WebAuthn registration options."""

    registration_token: str
    options: dict  # WebAuthn PublicKeyCredentialCreationOptions
    expires_in: int = 300  # 5 minutes


class SetupPasskeyVerifyRequest(BaseModel):
    """Request to verify passkey registration during setup."""

    registration_token: str
    credential: dict  # WebAuthn credential response
    device_name: str | None = None


class SetupPasskeyVerifyResponse(BaseModel):
    """Response after successful setup with passkey."""

    user_id: str
    email: str
    access_token: str
    refresh_token: str
