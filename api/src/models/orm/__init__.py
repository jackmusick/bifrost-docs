"""SQLAlchemy ORM Models for Bifrost Docs.

Pure database models using SQLAlchemy 2.0 declarative style.
These models define the database schema and relationships.
"""

from src.models.orm.api_key import APIKey
from src.models.orm.attachment import Attachment
from src.models.orm.audit_log import AuditLog
from src.models.orm.base import Base
from src.models.orm.configuration import Configuration
from src.models.orm.configuration_status import ConfigurationStatus
from src.models.orm.configuration_type import ConfigurationType
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.custom_asset_type import CustomAssetType
from src.models.orm.document import Document
from src.models.orm.embedding_index import EmbeddingIndex
from src.models.orm.export import Export, ExportStatus
from src.models.orm.location import Location
from src.models.orm.mfa import MFARecoveryCode, UserMFAMethod
from src.models.orm.organization import Organization
from src.models.orm.passkey import UserPasskey
from src.models.orm.password import Password
from src.models.orm.relationship import Relationship
from src.models.orm.session import Session
from src.models.orm.system_config import SystemConfig
from src.models.orm.user import User
from src.models.orm.user_oauth_account import UserOAuthAccount
from src.models.orm.user_preferences import UserPreferences

__all__ = [
    # Base
    "Base",
    # Organizations
    "Organization",
    # Locations
    "Location",
    # Documents
    "Document",
    # Passwords
    "Password",
    # Configurations
    "ConfigurationType",
    "ConfigurationStatus",
    "Configuration",
    # Users
    "User",
    "UserOAuthAccount",
    "UserPreferences",
    # Sessions
    "Session",
    # Passkeys
    "UserPasskey",
    # MFA
    "UserMFAMethod",
    "MFARecoveryCode",
    # API Keys
    "APIKey",
    # Audit Logs
    "AuditLog",
    # Custom Assets
    "CustomAssetType",
    "CustomAsset",
    # Attachments
    "Attachment",
    # Relationships
    "Relationship",
    # Embedding Index
    "EmbeddingIndex",
    # Exports
    "Export",
    "ExportStatus",
    # System Config
    "SystemConfig",
]
