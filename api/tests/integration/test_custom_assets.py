"""
Integration tests for Custom Assets API.

Tests the complete custom asset type and custom asset workflows including
CRUD operations, validation, password encryption.

Note: CustomAssetType is now GLOBAL (not org-scoped), while CustomAsset
instances remain org-scoped.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.custom_asset import CustomAsset
from src.models.orm.custom_asset_type import CustomAssetType
from src.models.orm.organization import Organization
from src.repositories.custom_asset import CustomAssetRepository
from src.repositories.custom_asset_type import CustomAssetTypeRepository
from src.repositories.organization import OrganizationRepository


@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org_repo = OrganizationRepository(db_session)
    org = Organization(name=f"Test Org {uuid4()}")
    return await org_repo.create(org)


@pytest_asyncio.fixture
async def other_org(db_session: AsyncSession) -> Organization:
    """Create another organization for isolation tests."""
    org_repo = OrganizationRepository(db_session)
    org = Organization(name=f"Other Org {uuid4()}")
    return await org_repo.create(org)


@pytest.mark.integration
class TestCustomAssetTypeRepository:
    """Integration tests for CustomAssetTypeRepository (global types)."""

    @pytest_asyncio.fixture
    async def asset_type(self, db_session: AsyncSession) -> CustomAssetType:
        """Create a test custom asset type (global)."""
        repo = CustomAssetTypeRepository(db_session)
        asset_type = CustomAssetType(
            name=f"SSL Certificate {uuid4()}",  # Unique name to avoid conflicts
            fields=[
                {"key": "domain", "name": "Domain", "type": "text", "required": True},
                {"key": "expiry", "name": "Expiry Date", "type": "date"},
                {
                    "key": "provider",
                    "name": "Provider",
                    "type": "select",
                    "options": ["LetsEncrypt", "DigiCert", "Comodo"],
                },
            ],
        )
        return await repo.create(asset_type)

    async def test_create_custom_asset_type(self, db_session: AsyncSession):
        """Test creating a global custom asset type."""
        repo = CustomAssetTypeRepository(db_session)

        asset_type = CustomAssetType(
            name=f"Software License {uuid4()}",
            fields=[
                {"key": "product", "name": "Product Name", "type": "text", "required": True},
                {"key": "license_key", "name": "License Key", "type": "password"},
                {"key": "seats", "name": "Number of Seats", "type": "number"},
            ],
        )
        created = await repo.create(asset_type)

        assert created.id is not None
        assert "Software License" in created.name
        assert len(created.fields) == 3

    async def test_get_by_id(
        self, db_session: AsyncSession, asset_type: CustomAssetType
    ):
        """Test getting asset type by ID."""
        repo = CustomAssetTypeRepository(db_session)

        found = await repo.get_by_id(asset_type.id)

        assert found is not None
        assert found.id == asset_type.id
        assert found.name == asset_type.name

    async def test_get_by_name(
        self, db_session: AsyncSession, asset_type: CustomAssetType
    ):
        """Test getting asset type by name."""
        repo = CustomAssetTypeRepository(db_session)

        found = await repo.get_by_name(asset_type.name)

        assert found is not None
        assert found.id == asset_type.id

    async def test_get_all_ordered(
        self, db_session: AsyncSession, asset_type: CustomAssetType  # noqa: ARG002
    ):
        """Test listing all asset types ordered by name."""
        repo = CustomAssetTypeRepository(db_session)

        # Create another asset type
        another = CustomAssetType(
            name=f"API Key {uuid4()}",
            fields=[{"key": "key", "name": "Key", "type": "password"}],
        )
        await repo.create(another)

        types = await repo.get_all_ordered()

        # Should have at least 2 types
        assert len(types) >= 2
        # Should be ordered by name
        names = [t.name for t in types]
        assert names == sorted(names)

    async def test_unique_name_constraint(self, db_session: AsyncSession):
        """Test that duplicate names are not allowed."""
        repo = CustomAssetTypeRepository(db_session)
        unique_name = f"Unique Type {uuid4()}"

        # Create first type
        first = CustomAssetType(name=unique_name, fields=[])
        await repo.create(first)

        # Attempt to create duplicate should fail
        from sqlalchemy.exc import IntegrityError

        duplicate = CustomAssetType(name=unique_name, fields=[])
        with pytest.raises(IntegrityError):
            await repo.create(duplicate)


@pytest.mark.integration
class TestCustomAssetRepository:
    """Integration tests for CustomAssetRepository (org-scoped assets)."""

    @pytest_asyncio.fixture
    async def asset_type(self, db_session: AsyncSession) -> CustomAssetType:
        """Create a test custom asset type (global)."""
        repo = CustomAssetTypeRepository(db_session)
        asset_type = CustomAssetType(
            name=f"Server Credentials {uuid4()}",
            fields=[
                {"key": "hostname", "name": "Hostname", "type": "text", "required": True},
                {"key": "username", "name": "Username", "type": "text"},
                {"key": "password", "name": "Password", "type": "password"},
                {"key": "port", "name": "Port", "type": "number"},
            ],
        )
        return await repo.create(asset_type)

    @pytest_asyncio.fixture
    async def custom_asset(
        self, db_session: AsyncSession, test_org: Organization, asset_type: CustomAssetType
    ) -> CustomAsset:
        """Create a test custom asset."""
        repo = CustomAssetRepository(db_session)
        asset = CustomAsset(
            organization_id=test_org.id,
            custom_asset_type_id=asset_type.id,
            values={
                "name": "Production Server",
                "hostname": "prod.example.com",
                "username": "admin",
                "password_encrypted": "encrypted-value",
                "port": 22,
            },
        )
        return await repo.create(asset)

    async def test_create_custom_asset(
        self, db_session: AsyncSession, test_org: Organization, asset_type: CustomAssetType
    ):
        """Test creating a custom asset."""
        repo = CustomAssetRepository(db_session)

        asset = CustomAsset(
            organization_id=test_org.id,
            custom_asset_type_id=asset_type.id,
            values={
                "name": "Development Server",
                "hostname": "dev.example.com",
                "username": "developer",
                "port": 2222,
            },
        )
        created = await repo.create(asset)

        assert created.id is not None
        assert created.values.get("name") == "Development Server"
        assert created.values.get("hostname") == "dev.example.com"

    async def test_get_by_id_type_and_org(
        self,
        db_session: AsyncSession,
        test_org: Organization,
        asset_type: CustomAssetType,
        custom_asset: CustomAsset,
    ):
        """Test getting asset by ID, type, and organization."""
        repo = CustomAssetRepository(db_session)

        found = await repo.get_by_id_type_and_org(
            custom_asset.id, asset_type.id, test_org.id
        )

        assert found is not None
        assert found.id == custom_asset.id
        assert found.values.get("name") == custom_asset.values.get("name")

    async def test_get_by_wrong_type_returns_none(
        self,
        db_session: AsyncSession,
        test_org: Organization,
        custom_asset: CustomAsset,
    ):
        """Test that getting asset with wrong type returns None."""
        repo = CustomAssetRepository(db_session)

        found = await repo.get_by_id_type_and_org(
            custom_asset.id, uuid4(), test_org.id  # Wrong type ID
        )

        assert found is None

    async def test_list_by_type_and_organization(
        self,
        db_session: AsyncSession,
        test_org: Organization,
        asset_type: CustomAssetType,
        custom_asset: CustomAsset,  # noqa: ARG002
    ):
        """Test listing assets by type and organization."""
        repo = CustomAssetRepository(db_session)

        # Create another asset
        another = CustomAsset(
            organization_id=test_org.id,
            custom_asset_type_id=asset_type.id,
            values={"name": "Staging Server", "hostname": "staging.example.com"},
        )
        await repo.create(another)

        assets = await repo.list_by_type_and_organization(asset_type.id, test_org.id)

        assert len(assets) >= 2
        names = [a.values.get("name") for a in assets]
        assert "Production Server" in names
        assert "Staging Server" in names

    async def test_search_by_field(
        self,
        db_session: AsyncSession,
        test_org: Organization,
        asset_type: CustomAssetType,
        custom_asset: CustomAsset,
    ):
        """Test searching assets by field value."""
        repo = CustomAssetRepository(db_session)

        # Create assets with different names
        await repo.create(
            CustomAsset(
                organization_id=test_org.id,
                custom_asset_type_id=asset_type.id,
                values={"name": "Database Server", "hostname": "db.example.com"},
            )
        )

        # Search for "Server" in the name field
        results = await repo.search_by_field(
            organization_id=test_org.id,
            search_term="Server",
            field_key="name",
        )

        assert len(results) >= 2
        for asset in results:
            assert "Server" in str(asset.values.get("name", ""))

        # Search for "Database"
        results = await repo.search_by_field(
            organization_id=test_org.id,
            search_term="Database",
            field_key="name",
        )

        assert len(results) >= 1
        assert any(a.values.get("name") == "Database Server" for a in results)

    async def test_organization_isolation(
        self,
        db_session: AsyncSession,
        test_org: Organization,
        other_org: Organization,
        asset_type: CustomAssetType,
        custom_asset: CustomAsset,
    ):
        """Test that assets are isolated by organization."""
        repo = CustomAssetRepository(db_session)

        # Get asset with wrong org
        found = await repo.get_by_id_and_org(custom_asset.id, other_org.id)

        assert found is None

    async def test_cascade_delete_from_type(
        self,
        db_session: AsyncSession,
        test_org: Organization,
        asset_type: CustomAssetType,
        custom_asset: CustomAsset,
    ):
        """Test that assets are deleted when their type is deleted."""
        type_repo = CustomAssetTypeRepository(db_session)
        asset_repo = CustomAssetRepository(db_session)

        # Verify asset exists
        found = await asset_repo.get_by_id_and_org(custom_asset.id, test_org.id)
        assert found is not None

        # Delete the type
        await type_repo.delete(asset_type)

        # Asset should be deleted (cascade)
        found = await asset_repo.get_by_id_and_org(custom_asset.id, test_org.id)
        assert found is None


@pytest.mark.integration
class TestPasswordFieldHandling:
    """Integration tests for password field encryption in custom assets."""

    @pytest_asyncio.fixture
    async def asset_type_with_passwords(
        self, db_session: AsyncSession
    ) -> CustomAssetType:
        """Create an asset type with password fields (global)."""
        repo = CustomAssetTypeRepository(db_session)
        asset_type = CustomAssetType(
            name=f"API Credentials {uuid4()}",
            fields=[
                {"key": "service_name", "name": "Service Name", "type": "text", "required": True},
                {"key": "api_key", "name": "API Key", "type": "password"},
                {"key": "api_secret", "name": "API Secret", "type": "password"},
            ],
        )
        return await repo.create(asset_type)

    async def test_password_encryption_roundtrip(
        self,
        db_session: AsyncSession,
        test_org: Organization,
        asset_type_with_passwords: CustomAssetType,
    ):
        """Test that passwords survive encryption/decryption roundtrip."""
        from src.models.contracts.custom_asset import FieldDefinition
        from src.services.custom_asset_validation import (
            decrypt_password_fields,
            encrypt_password_fields,
        )

        repo = CustomAssetRepository(db_session)
        type_fields = [FieldDefinition(**f) for f in asset_type_with_passwords.fields]

        # Original values
        original_values = {
            "service_name": "Payment Gateway",
            "api_key": "pk_live_abc123",
            "api_secret": "sk_live_xyz789",
        }

        # Encrypt for storage
        encrypted_values = encrypt_password_fields(type_fields, original_values)

        # Create asset with encrypted values
        asset = CustomAsset(
            organization_id=test_org.id,
            custom_asset_type_id=asset_type_with_passwords.id,
            name="Stripe API",
            values=encrypted_values,
        )
        created = await repo.create(asset)

        # Retrieve from database
        retrieved = await repo.get_by_id_and_org(created.id, test_org.id)
        assert retrieved is not None

        # Decrypt the values
        decrypted_values = decrypt_password_fields(type_fields, retrieved.values)

        # Verify roundtrip
        assert decrypted_values["service_name"] == "Payment Gateway"
        assert decrypted_values["api_key"] == "pk_live_abc123"
        assert decrypted_values["api_secret"] == "sk_live_xyz789"

    async def test_encrypted_values_stored_in_database(
        self,
        db_session: AsyncSession,
        test_org: Organization,
        asset_type_with_passwords: CustomAssetType,
    ):
        """Test that encrypted values are actually stored encrypted in database."""
        from src.models.contracts.custom_asset import FieldDefinition
        from src.services.custom_asset_validation import encrypt_password_fields

        repo = CustomAssetRepository(db_session)
        type_fields = [FieldDefinition(**f) for f in asset_type_with_passwords.fields]

        original_secret = "super-secret-value-12345"
        values = {
            "service_name": "Test Service",
            "api_key": original_secret,
        }

        encrypted_values = encrypt_password_fields(type_fields, values)

        asset = CustomAsset(
            organization_id=test_org.id,
            custom_asset_type_id=asset_type_with_passwords.id,
            name="Test Asset",
            values=encrypted_values,
        )
        created = await repo.create(asset)

        # Verify stored values don't contain plaintext
        assert original_secret not in str(created.values)
        assert "api_key_encrypted" in created.values
        assert created.values["api_key_encrypted"] != original_secret
