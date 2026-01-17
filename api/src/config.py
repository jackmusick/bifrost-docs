"""
Application Configuration

Uses pydantic-settings for environment variable loading with validation.
All configuration is centralized here for easy management.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables can be set directly or via .env file.
    All secrets should be provided via environment variables in production.
    """

    model_config = SettingsConfigDict(
        env_prefix="BIFROST_DOCS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Environment
    # ==========================================================================
    environment: Literal["development", "testing", "production"] = Field(
        default="development", description="Runtime environment"
    )

    debug: bool = Field(default=False, description="Enable debug mode")

    # ==========================================================================
    # Database (PostgreSQL)
    # ==========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://bifrost_docs:bifrost_docsdev@localhost:5433/bifrost_docs",
        description="Async PostgreSQL connection URL",
    )

    database_url_sync: str = Field(
        default="postgresql://bifrost_docs:bifrost_docsdev@localhost:5433/bifrost_docs",
        description="Sync PostgreSQL connection URL (for Alembic)",
    )

    database_pool_size: int = Field(
        default=5, description="Database connection pool size")

    database_max_overflow: int = Field(
        default=10, description="Max overflow connections beyond pool size"
    )

    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_url: str = Field(default="redis://localhost:6380/0",
                           description="Redis connection URL")

    # ==========================================================================
    # Security
    # ==========================================================================
    secret_key: str = Field(
        description="Secret key for JWT signing and encryption (BIFROST_DOCS_SECRET_KEY env var required)",
        min_length=32,
    )

    algorithm: str = Field(
        default="HS256", description="JWT signing algorithm")

    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration time in minutes"
    )

    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration time in days"
    )

    jwt_issuer: str = Field(
        default="bifrost-docs-api", description="JWT issuer claim for token validation"
    )

    jwt_audience: str = Field(
        default="bifrost-docs-client", description="JWT audience claim for token validation"
    )

    fernet_salt: str = Field(
        default="bifrost_docssecrets_v1",
        description="Salt for Fernet key derivation (override for different encryption keys)",
    )

    # ==========================================================================
    # CORS
    # ==========================================================================
    cors_origins: str = Field(
        default="http://localhost:3000", description="Comma-separated list of allowed CORS origins"
    )

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # ==========================================================================
    # Default User (for automated deployments and development)
    # ==========================================================================
    default_user_email: str | None = Field(
        default=None, description="Default admin user email (creates user on startup if set)"
    )

    default_user_password: str | None = Field(
        default=None, description="Default admin user password"
    )

    # ==========================================================================
    # MFA Settings
    # ==========================================================================
    mfa_enabled: bool = Field(
        default=True, description="Whether MFA is required for password authentication"
    )

    mfa_totp_issuer: str = Field(
        default="BifrostDocs", description="Issuer name for TOTP QR codes")

    mfa_recovery_code_count: int = Field(
        default=10, description="Number of recovery codes to generate for MFA"
    )

    mfa_trusted_device_days: int = Field(
        default=30, description="Number of days a device stays trusted after MFA verification"
    )

    mfa_setup_token_expire_minutes: int = Field(
        default=15,
        description="MFA setup token expiration time in minutes (longer than verify for setup flow)",
    )

    mfa_verify_token_expire_minutes: int = Field(
        default=5, description="MFA verify token expiration time in minutes (during login)"
    )

    # ==========================================================================
    # WebAuthn/Passkeys
    # ==========================================================================
    webauthn_rp_id: str = Field(
        default="localhost", description="WebAuthn Relying Party ID (must match origin domain)"
    )

    webauthn_rp_name: str = Field(
        default="Bifrost Docs", description="WebAuthn Relying Party display name"
    )

    webauthn_origin: str = Field(
        default="http://localhost:3000",
        description="WebAuthn expected origin URLs (comma-separated for multiple)",
    )

    @property
    def webauthn_origins(self) -> list[str]:
        """Parse webauthn_origin into a list of origins."""
        return [o.strip() for o in self.webauthn_origin.split(",") if o.strip()]

    # ==========================================================================
    # File Storage (Local)
    # ==========================================================================
    temp_location: str = Field(
        default="/tmp/bifrost_docs", description="Path to temporary storage directory"
    )

    # ==========================================================================
    # S3/MinIO Storage
    # ==========================================================================
    s3_endpoint: str = Field(
        default="http://localhost:9000",
        description="S3-compatible endpoint URL (MinIO in development)",
    )

    s3_access_key: str | None = Field(
        default=None, description="S3 access key (required for S3 operations)"
    )

    s3_secret_key: str | None = Field(
        default=None, description="S3 secret key (required for S3 operations)"
    )

    s3_bucket: str = Field(
        default="bifrost-docs", description="S3 bucket name for file storage"
    )

    s3_region: str = Field(
        default="us-east-1", description="S3 region (use us-east-1 for MinIO)"
    )

    s3_presigned_url_expiry: int = Field(
        default=600, description="Presigned URL expiry in seconds (default 10 minutes)"
    )

    s3_download_url_expiry: int = Field(
        default=3600, description="Download URL expiry in seconds (default 1 hour)"
    )

    @computed_field
    @property
    def s3_configured(self) -> bool:
        """Check if S3 storage is properly configured."""
        return self.s3_access_key is not None and self.s3_secret_key is not None

    # ==========================================================================
    # OpenAI (for embeddings)
    # ==========================================================================
    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key for embeddings generation"
    )

    openai_embedding_model: str = Field(
        default="text-embedding-ada-002",
        description="OpenAI embedding model (default: text-embedding-ada-002)",
    )

    # ==========================================================================
    # Server
    # ==========================================================================
    host: str = Field(default="0.0.0.0", description="Server host")

    port: int = Field(default=8000, description="Server port")

    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @computed_field
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "testing"

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def validate_paths(self) -> None:
        """
        Validate that required filesystem paths exist.

        Creates temp directory if it doesn't exist.
        """
        temp = Path(self.temp_location)
        temp.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    Settings are loaded from environment variables via pydantic-settings.
    """
    return Settings()  # type: ignore[call-arg]  # pydantic-settings loads from env


def clear_settings_cache() -> None:
    """Clear the settings cache (useful for testing)."""
    get_settings.cache_clear()
