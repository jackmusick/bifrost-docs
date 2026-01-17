"""
Security Utilities

Password hashing and JWT token handling using industry-standard libraries.
Based on FastAPI's official security tutorial patterns.

Uses pwdlib (modern replacement for unmaintained passlib) for password hashing.
"""

import base64
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from src.config import get_settings

# Password hashing using pwdlib with bcrypt
# This is the modern replacement for passlib, recommended by FastAPI
# We explicitly use BcryptHasher to avoid requiring argon2 dependency
password_hash = PasswordHash((BcryptHasher(),))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The password to verify
        hashed_password: The hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return password_hash.hash(password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(
            UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update(
        {
            "exp": expire,
            "type": "access",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        }
    )

    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm)

    return encoded_jwt


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> tuple[str, str]:
    """
    Create a JWT refresh token with JTI for revocation support.

    Refresh tokens have longer expiration and are used to obtain new access tokens.
    Each token has a unique JTI (JWT ID) that must be stored in Redis for validation.

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Tuple of (encoded JWT token string, JTI for Redis storage)
    """
    settings = get_settings()

    jti = str(uuid4())
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(
            UTC) + timedelta(days=settings.refresh_token_expire_days)

    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
            "jti": jti,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        }
    )

    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm)

    return encoded_jwt, jti


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode
        expected_type: If provided, validates that token type matches (e.g., "access", "refresh")

    Returns:
        Decoded token payload or None if invalid/expired/wrong type
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )

        # Validate token type if specified
        if expected_type is not None and payload.get("type") != expected_type:
            return None

        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_mfa_token(user_id: str, purpose: str = "mfa_verify") -> str:
    """
    Create a short-lived token for MFA verification step.

    This token is returned after password verification and must be
    provided along with the MFA code to complete login.

    Args:
        user_id: User ID
        purpose: Token purpose (mfa_verify, mfa_setup)

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    # Use different expiry times based on purpose
    # Setup needs more time for users to install/configure authenticator apps
    if purpose == "mfa_setup":
        expire_minutes = settings.mfa_setup_token_expire_minutes
    else:
        expire_minutes = settings.mfa_verify_token_expire_minutes

    expire = datetime.now(UTC) + timedelta(minutes=expire_minutes)

    to_encode = {
        "sub": user_id,
        "type": purpose,
        "exp": expire,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_mfa_token(token: str, expected_purpose: str = "mfa_verify") -> dict[str, Any] | None:
    """
    Decode and validate an MFA token.

    Args:
        token: JWT token string to decode
        expected_purpose: Expected token purpose

    Returns:
        Decoded token payload or None if invalid/expired/wrong type
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
        if payload.get("type") != expected_purpose:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# =============================================================================
# Secret Encryption (for storing secrets in database)
# =============================================================================


def _get_fernet_key() -> bytes:
    """
    Derive a Fernet-compatible key from the application secret using HKDF.

    HKDF (HMAC-based Key Derivation Function) is more appropriate than PBKDF2
    when deriving keys from a high-entropy master key (as opposed to passwords).
    It's faster and provides better key separation with the info parameter.

    Returns:
        32-byte key suitable for Fernet encryption
    """
    settings = get_settings()

    # Use HKDF to derive a key from the secret
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=settings.fernet_salt.encode(),
        info=b"bifrost-docs-secrets-encryption",
    )

    key = base64.urlsafe_b64encode(kdf.derive(settings.secret_key.encode()))
    return key


def encrypt_secret(plaintext: str) -> str:
    """
    Encrypt a secret value for storage in the database.

    Args:
        plaintext: The secret value to encrypt

    Returns:
        Base64-encoded encrypted value
    """
    key = _get_fernet_key()
    f = Fernet(key)
    encrypted = f.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_secret(encrypted: str) -> str:
    """
    Decrypt a secret value from the database.

    Args:
        encrypted: Base64-encoded encrypted value

    Returns:
        Decrypted plaintext value
    """
    key = _get_fernet_key()
    f = Fernet(key)
    encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode())
    decrypted = f.decrypt(encrypted_bytes)
    return decrypted.decode()


# =============================================================================
# CSRF Protection
# =============================================================================


def generate_csrf_token() -> str:
    """
    Generate a cryptographically secure CSRF token.

    Returns:
        URL-safe base64 encoded random string (43 characters)
    """
    return secrets.token_urlsafe(32)


def validate_csrf_token(cookie_token: str, header_token: str) -> bool:
    """
    Validate CSRF token using constant-time comparison.

    Args:
        cookie_token: CSRF token from cookie
        header_token: CSRF token from X-CSRF-Token header

    Returns:
        True if tokens match, False otherwise
    """
    if not cookie_token or not header_token:
        return False
    return secrets.compare_digest(cookie_token, header_token)


# =============================================================================
# API Key Hashing
# =============================================================================


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.

    Uses SHA-256 since API keys are already high-entropy random strings
    and don't need bcrypt's intentional slowness.

    Args:
        api_key: The raw API key

    Returns:
        SHA-256 hash of the API key
    """
    import hashlib

    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """
    Generate a new API key.

    Returns:
        A URL-safe random string prefixed with 'bifrost_docs'
    """
    return f"bifrost_docs{secrets.token_urlsafe(32)}"
