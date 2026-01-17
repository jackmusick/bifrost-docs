"""
Unit tests for password functionality.

Tests encryption/decryption round-trip for password storage.
"""


class TestPasswordEncryption:
    """Tests for password encryption/decryption."""

    def test_encrypt_and_decrypt_password_roundtrip(self):
        """Test that passwords can be encrypted and decrypted correctly."""
        from src.core.security import decrypt_secret, encrypt_secret

        password = "MySuperSecretPassword123!"
        encrypted = encrypt_secret(password)

        # Encrypted should be different from plaintext
        assert encrypted != password

        # Should decrypt back to original
        decrypted = decrypt_secret(encrypted)
        assert decrypted == password

    def test_encrypt_empty_password(self):
        """Test that empty passwords can be encrypted and decrypted."""
        from src.core.security import decrypt_secret, encrypt_secret

        password = ""
        encrypted = encrypt_secret(password)

        # Should still produce encrypted output
        assert encrypted != password
        assert len(encrypted) > 0

        # Should decrypt back to empty string
        decrypted = decrypt_secret(encrypted)
        assert decrypted == password

    def test_encrypt_special_characters_password(self):
        """Test that passwords with special characters work correctly."""
        from src.core.security import decrypt_secret, encrypt_secret

        password = "P@ss!w0rd#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encrypt_secret(password)

        decrypted = decrypt_secret(encrypted)
        assert decrypted == password

    def test_encrypt_unicode_password(self):
        """Test that passwords with unicode characters work correctly."""
        from src.core.security import decrypt_secret, encrypt_secret

        password = "Passw0rd_"
        encrypted = encrypt_secret(password)

        decrypted = decrypt_secret(encrypted)
        assert decrypted == password

    def test_encrypt_long_password(self):
        """Test that long passwords work correctly."""
        from src.core.security import decrypt_secret, encrypt_secret

        password = "A" * 1000  # 1000 character password
        encrypted = encrypt_secret(password)

        decrypted = decrypt_secret(encrypted)
        assert decrypted == password

    def test_same_password_produces_different_ciphertext(self):
        """Test that encrypting the same password twice produces different ciphertext."""
        from src.core.security import encrypt_secret

        password = "TestPassword123"
        enc1 = encrypt_secret(password)
        enc2 = encrypt_secret(password)

        # Fernet uses random IV, so ciphertexts should differ
        assert enc1 != enc2

    def test_different_passwords_decrypt_to_different_values(self):
        """Test that different encrypted passwords decrypt to different values."""
        from src.core.security import decrypt_secret, encrypt_secret

        password1 = "Password1"
        password2 = "Password2"

        enc1 = encrypt_secret(password1)
        enc2 = encrypt_secret(password2)

        dec1 = decrypt_secret(enc1)
        dec2 = decrypt_secret(enc2)

        assert dec1 != dec2
        assert dec1 == password1
        assert dec2 == password2


class TestPasswordContracts:
    """Tests for password Pydantic contracts."""

    def test_password_create_valid(self):
        """Test PasswordCreate with valid data."""
        from src.models.contracts.password import PasswordCreate

        data = PasswordCreate(
            name="Admin Account",
            username="admin",
            password="secret123",
            url="https://example.com",
            notes="Main admin account",
        )

        assert data.name == "Admin Account"
        assert data.username == "admin"
        assert data.password == "secret123"
        assert data.url == "https://example.com"
        assert data.notes == "Main admin account"

    def test_password_create_minimal(self):
        """Test PasswordCreate with minimal required fields."""
        from src.models.contracts.password import PasswordCreate

        data = PasswordCreate(
            name="Test",
            password="secret",
        )

        assert data.name == "Test"
        assert data.password == "secret"
        assert data.username is None
        assert data.url is None
        assert data.notes is None

    def test_password_update_partial(self):
        """Test PasswordUpdate with partial data."""
        from src.models.contracts.password import PasswordUpdate

        data = PasswordUpdate(name="New Name")

        assert data.name == "New Name"
        assert data.username is None
        assert data.password is None
        assert data.url is None
        assert data.notes is None

    def test_password_update_empty(self):
        """Test PasswordUpdate with no data."""
        from src.models.contracts.password import PasswordUpdate

        data = PasswordUpdate()

        assert data.name is None
        assert data.username is None
        assert data.password is None
        assert data.url is None
        assert data.notes is None

    def test_password_public_excludes_password(self):
        """Test PasswordPublic schema does not include password field."""
        from src.models.contracts.password import PasswordPublic

        # PasswordPublic should not have password field
        fields = PasswordPublic.model_fields
        assert "password" not in fields
        assert "password_encrypted" not in fields
        assert "name" in fields
        assert "username" in fields

    def test_password_reveal_includes_password(self):
        """Test PasswordReveal schema includes password field."""
        from src.models.contracts.password import PasswordReveal

        fields = PasswordReveal.model_fields
        assert "password" in fields
        assert "name" in fields
        assert "username" in fields
