"""
MFA Router

Provides endpoints for Multi-Factor Authentication:
- MFA status check
- TOTP setup and verification (stubbed)
- MFA removal (stubbed)

Note: Full MFA functionality to be implemented later.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.auth import CurrentActiveUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


# =============================================================================
# Request/Response Models
# =============================================================================


class MFAStatusResponse(BaseModel):
    """MFA status response."""

    mfa_enabled: bool
    backup_codes_remaining: int


class MFASetupResponse(BaseModel):
    """MFA setup response with secret."""

    secret: str
    qr_code_uri: str
    provisioning_uri: str
    issuer: str
    account_name: str


class MFAVerifyRequest(BaseModel):
    """Request to verify MFA code."""

    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class MFAVerifyResponse(BaseModel):
    """MFA verification response."""

    success: bool
    recovery_codes: list[str] | None = None


class MFARemoveRequest(BaseModel):
    """Request to remove MFA method."""

    password: str | None = None
    mfa_code: str | None = None


# =============================================================================
# MFA Status
# =============================================================================


@router.get("/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    current_user: CurrentActiveUser,
) -> MFAStatusResponse:
    """
    Get MFA status for current user.

    Returns:
        MFA status including enabled state and backup code count
    """
    logger.debug(f"MFA status requested for user: {current_user.email}")

    # Stub response - MFA not yet implemented
    return MFAStatusResponse(
        mfa_enabled=False,
        backup_codes_remaining=0,
    )


# =============================================================================
# MFA Setup and Verification (Stubs)
# =============================================================================


@router.post("/totp/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: CurrentActiveUser,
) -> MFASetupResponse:
    """
    Initialize MFA enrollment for an authenticated user.

    Generates a new TOTP secret and returns the provisioning URI for QR code generation.

    Returns:
        MFA setup data including secret and QR code URI

    Raises:
        HTTPException: MFA not yet implemented (501)
    """
    logger.info(f"MFA setup requested for user: {current_user.email}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MFA not yet implemented",
    )


@router.post("/totp/verify", response_model=MFAVerifyResponse)
async def verify_mfa(
    request: MFAVerifyRequest,
    current_user: CurrentActiveUser,
) -> MFAVerifyResponse:
    """
    Verify MFA code to complete enrollment.

    On success:
    - Activates the MFA method
    - Generates recovery codes (shown only once!)

    Args:
        request: MFA verification request with 6-digit code

    Returns:
        Success status and recovery codes

    Raises:
        HTTPException: MFA not yet implemented (501)
    """
    logger.info(f"MFA verification requested for user: {current_user.email}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MFA not yet implemented",
    )


@router.delete("", status_code=status.HTTP_200_OK)
async def remove_mfa(
    request: MFARemoveRequest,
    current_user: CurrentActiveUser,
) -> dict:
    """
    Remove MFA enrollment.

    Requires either current password or MFA code for verification.

    Args:
        request: Removal request with password or MFA code

    Returns:
        Success message

    Raises:
        HTTPException: MFA not yet implemented (501)
    """
    logger.info(f"MFA removal requested for user: {current_user.email}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MFA not yet implemented",
    )
