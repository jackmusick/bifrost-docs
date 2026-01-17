"""
Unit tests for security utilities.

Tests JWT encoding/decoding, password hashing, and encryption.
"""

from datetime import timedelta


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_password_hash_and_verify(self):
        """Test that password hashing and verification works."""
        from src.core.security import get_password_hash, verify_password

        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        # Hash should be different from password
        assert hashed != password

        # Should verify correctly
        assert verify_password(password, hashed) is True

        # Wrong password should not verify
        assert verify_password("WrongPassword", hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes."""
        from src.core.security import get_password_hash

        hash1 = get_password_hash("Password1")
        hash2 = get_password_hash("Password2")

        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self):
        """Test that the same password produces different hashes (due to salt)."""
        from src.core.security import get_password_hash

        password = "SamePassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Bcrypt includes random salt, so hashes should differ
        assert hash1 != hash2


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_and_decode_access_token(self):
        """Test access token creation and decoding."""
        from src.core.security import create_access_token, decode_token

        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(data)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Should decode successfully
        payload = decode_token(token, expected_type="access")
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        """Test refresh token creation and decoding."""
        from src.core.security import create_refresh_token, decode_token

        data = {"sub": "user-123"}
        token, jti = create_refresh_token(data)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # JTI should be a UUID string
        assert isinstance(jti, str)
        assert len(jti) == 36  # UUID format

        # Should decode successfully
        payload = decode_token(token, expected_type="refresh")
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"
        assert payload["jti"] == jti

    def test_token_type_validation(self):
        """Test that token type validation works."""
        from src.core.security import create_access_token, decode_token

        token = create_access_token({"sub": "user-123"})

        # Should fail with wrong expected type
        payload = decode_token(token, expected_type="refresh")
        assert payload is None

        # Should succeed with correct type
        payload = decode_token(token, expected_type="access")
        assert payload is not None

    def test_expired_token_returns_none(self):
        """Test that expired tokens return None."""
        from src.core.security import create_access_token, decode_token

        # Create token that expires immediately
        token = create_access_token(
            {"sub": "user-123"}, expires_delta=timedelta(seconds=-1))

        # Should return None for expired token
        payload = decode_token(token)
        assert payload is None

    def test_invalid_token_returns_none(self):
        """Test that invalid tokens return None."""
        from src.core.security import decode_token

        # Garbage token
        payload = decode_token("not-a-valid-token")
        assert payload is None

        # Empty token
        payload = decode_token("")
        assert payload is None


class TestMFATokens:
    """Tests for MFA token functions."""

    def test_create_and_decode_mfa_verify_token(self):
        """Test MFA verify token creation and decoding."""
        from src.core.security import create_mfa_token, decode_mfa_token

        user_id = "user-123"
        token = create_mfa_token(user_id, purpose="mfa_verify")

        # Should decode successfully
        payload = decode_mfa_token(token, expected_purpose="mfa_verify")
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "mfa_verify"

    def test_create_and_decode_mfa_setup_token(self):
        """Test MFA setup token creation and decoding."""
        from src.core.security import create_mfa_token, decode_mfa_token

        user_id = "user-123"
        token = create_mfa_token(user_id, purpose="mfa_setup")

        # Should decode successfully
        payload = decode_mfa_token(token, expected_purpose="mfa_setup")
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "mfa_setup"

    def test_mfa_token_purpose_validation(self):
        """Test that MFA token purpose validation works."""
        from src.core.security import create_mfa_token, decode_mfa_token

        token = create_mfa_token("user-123", purpose="mfa_verify")

        # Should fail with wrong purpose
        payload = decode_mfa_token(token, expected_purpose="mfa_setup")
        assert payload is None

        # Should succeed with correct purpose
        payload = decode_mfa_token(token, expected_purpose="mfa_verify")
        assert payload is not None


class TestSecretEncryption:
    """Tests for secret encryption/decryption."""

    def test_encrypt_and_decrypt_secret(self):
        """Test that secrets can be encrypted and decrypted."""
        from src.core.security import decrypt_secret, encrypt_secret

        plaintext = "my-super-secret-api-key"
        encrypted = encrypt_secret(plaintext)

        # Encrypted should be different from plaintext
        assert encrypted != plaintext

        # Should decrypt back to original
        decrypted = decrypt_secret(encrypted)
        assert decrypted == plaintext

    def test_different_plaintexts_produce_different_ciphertexts(self):
        """Test that different secrets produce different encrypted values."""
        from src.core.security import encrypt_secret

        enc1 = encrypt_secret("secret1")
        enc2 = encrypt_secret("secret2")

        assert enc1 != enc2


class TestCSRFTokens:
    """Tests for CSRF token functions."""

    def test_generate_csrf_token(self):
        """Test CSRF token generation."""
        from src.core.security import generate_csrf_token

        token = generate_csrf_token()

        # Should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Should be URL-safe
        assert "/" not in token
        assert "+" not in token

    def test_validate_csrf_token(self):
        """Test CSRF token validation."""
        from src.core.security import generate_csrf_token, validate_csrf_token

        token = generate_csrf_token()

        # Should validate matching tokens
        assert validate_csrf_token(token, token) is True

        # Should reject different tokens
        assert validate_csrf_token(token, "different-token") is False

        # Should reject empty tokens
        assert validate_csrf_token("", token) is False
        assert validate_csrf_token(token, "") is False


class TestAPIKeyFunctions:
    """Tests for API key functions."""

    def test_generate_api_key(self):
        """Test API key generation."""
        from src.core.security import generate_api_key

        key = generate_api_key()

        # Should start with bifrost_docs
        assert key.startswith("bifrost_docs")

        # Should be a reasonable length
        assert len(key) > 40

    def test_hash_api_key(self):
        """Test API key hashing."""
        from src.core.security import generate_api_key, hash_api_key

        key = generate_api_key()
        hashed = hash_api_key(key)

        # Hash should be 64 chars (SHA-256 hex)
        assert len(hashed) == 64

        # Same key should produce same hash
        assert hash_api_key(key) == hashed

        # Different key should produce different hash
        key2 = generate_api_key()
        assert hash_api_key(key2) != hashed
