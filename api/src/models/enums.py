"""
Enums for Bifrost Docs models.
"""

from enum import Enum


class UserType(str, Enum):
    """User types in the system."""

    PLATFORM = "PLATFORM"  # Platform admin (global access)
    ORG = "ORG"  # Organization user (org-scoped access)


class UserRole(str, Enum):
    """User roles for access control."""

    OWNER = "owner"
    ADMINISTRATOR = "administrator"
    CONTRIBUTOR = "contributor"
    READER = "reader"

    @classmethod
    def can_edit_data(cls, role: "UserRole") -> bool:
        """Check if role can create/edit/delete data."""
        return role in (cls.OWNER, cls.ADMINISTRATOR, cls.CONTRIBUTOR)

    @classmethod
    def can_access_settings(cls, role: "UserRole") -> bool:
        """Check if role can access admin settings."""
        return role in (cls.OWNER, cls.ADMINISTRATOR)

    @classmethod
    def can_manage_owners(cls, role: "UserRole") -> bool:
        """Check if role can add/remove owner role."""
        return role == cls.OWNER


class MFAMethodType(str, Enum):
    """Types of MFA methods."""

    TOTP = "totp"  # Time-based One-Time Password (Google Authenticator, etc.)


class MFAMethodStatus(str, Enum):
    """Status of an MFA method."""

    PENDING = "pending"  # Setup started but not verified
    ACTIVE = "active"  # Verified and active
    DISABLED = "disabled"  # Disabled by user or admin


class EntityType(str, Enum):
    """Entity types that can have attachments."""

    PASSWORD = "password"
    CONFIGURATION = "configuration"
    LOCATION = "location"
    DOCUMENT = "document"
    CUSTOM_ASSET = "custom_asset"
    DOCUMENT_IMAGE = "document_image"  # Embedded images in markdown documents


class AuditAction(str, Enum):
    """Actions tracked in audit logs."""

    # Entity mutations
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    # Status changes
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"

    # Sensitive access
    VIEW = "view"

    # Auth events
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    MFA_SETUP = "mfa_setup"
    MFA_VERIFY = "mfa_verify"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"


class ActorType(str, Enum):
    """Types of actors that can perform audited actions."""

    USER = "user"
    API_KEY = "api_key"
    SYSTEM = "system"
