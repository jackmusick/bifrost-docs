"""
Integration tests for attachments.

Tests attachment CRUD operations using real database.
Note: Full S3 integration tests require MinIO running.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import EntityType
from src.models.orm.attachment import Attachment
from src.models.orm.organization import Organization
from src.repositories.attachment import AttachmentRepository
from src.repositories.organization import OrganizationRepository


@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org_repo = OrganizationRepository(db_session)
    org = Organization(name=f"Test Org {uuid4()}")
    return await org_repo.create(org)


@pytest_asyncio.fixture
async def test_attachment(
    db_session: AsyncSession, test_org: Organization
) -> Attachment:
    """Create a test attachment."""
    repo = AttachmentRepository(db_session)
    attachment = Attachment(
        organization_id=test_org.id,
        entity_type=EntityType.DOCUMENT,
        entity_id=uuid4(),
        filename="test-document.pdf",
        s3_key=f"{test_org.id}/document/{uuid4()}/{uuid4()}/test-document.pdf",
        content_type="application/pdf",
        size_bytes=1024,
    )
    return await repo.create(attachment)


@pytest.mark.integration
class TestAttachmentRepository:
    """Integration tests for AttachmentRepository."""

    @pytest.mark.asyncio
    async def test_create_attachment(
        self, db_session: AsyncSession, test_org: Organization
    ):
        """Test creating an attachment."""
        repo = AttachmentRepository(db_session)
        entity_id = uuid4()

        attachment = Attachment(
            organization_id=test_org.id,
            entity_type=EntityType.PASSWORD,
            entity_id=entity_id,
            filename="credentials.txt",
            s3_key=f"{test_org.id}/password/{entity_id}/{uuid4()}/credentials.txt",
            content_type="text/plain",
            size_bytes=256,
        )

        created = await repo.create(attachment)

        assert created.id is not None
        assert created.organization_id == test_org.id
        assert created.entity_type == EntityType.PASSWORD
        assert created.entity_id == entity_id
        assert created.filename == "credentials.txt"
        assert created.content_type == "text/plain"
        assert created.size_bytes == 256
        assert created.created_at is not None

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, db_session: AsyncSession, test_attachment: Attachment
    ):
        """Test getting attachment by ID."""
        repo = AttachmentRepository(db_session)

        found = await repo.get_by_id(test_attachment.id)

        assert found is not None
        assert found.id == test_attachment.id
        assert found.filename == test_attachment.filename

    @pytest.mark.asyncio
    async def test_get_by_id_and_org(
        self,
        db_session: AsyncSession,
        test_org: Organization,
        test_attachment: Attachment,
    ):
        """Test getting attachment by ID scoped to organization."""
        repo = AttachmentRepository(db_session)

        # Should find with correct org
        found = await repo.get_by_id_and_org(test_attachment.id, test_org.id)
        assert found is not None
        assert found.id == test_attachment.id

        # Should not find with different org
        other_org_id = uuid4()
        not_found = await repo.get_by_id_and_org(test_attachment.id, other_org_id)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_get_by_entity(
        self,
        db_session: AsyncSession,
        test_org: Organization,
    ):
        """Test getting attachments for a specific entity."""
        repo = AttachmentRepository(db_session)
        entity_id = uuid4()

        # Create multiple attachments for the same entity
        for i in range(3):
            attachment = Attachment(
                organization_id=test_org.id,
                entity_type=EntityType.CONFIGURATION,
                entity_id=entity_id,
                filename=f"config-{i}.yaml",
                s3_key=f"{test_org.id}/configuration/{entity_id}/{uuid4()}/config-{i}.yaml",
                content_type="application/yaml",
                size_bytes=512 * (i + 1),
            )
            await repo.create(attachment)

        # Create attachment for different entity
        other_entity_id = uuid4()
        other_attachment = Attachment(
            organization_id=test_org.id,
            entity_type=EntityType.CONFIGURATION,
            entity_id=other_entity_id,
            filename="other.yaml",
            s3_key=f"{test_org.id}/configuration/{other_entity_id}/{uuid4()}/other.yaml",
            content_type="application/yaml",
            size_bytes=256,
        )
        await repo.create(other_attachment)

        # Get attachments for specific entity
        attachments = await repo.get_by_entity(
            organization_id=test_org.id,
            entity_type=EntityType.CONFIGURATION,
            entity_id=entity_id,
        )

        assert len(attachments) == 3
        assert all(a.entity_id == entity_id for a in attachments)

    @pytest.mark.asyncio
    async def test_count_by_entity(
        self,
        db_session: AsyncSession,
        test_org: Organization,
    ):
        """Test counting attachments for an entity."""
        repo = AttachmentRepository(db_session)
        entity_id = uuid4()

        # Create attachments
        for i in range(5):
            attachment = Attachment(
                organization_id=test_org.id,
                entity_type=EntityType.LOCATION,
                entity_id=entity_id,
                filename=f"photo-{i}.jpg",
                s3_key=f"{test_org.id}/location/{entity_id}/{uuid4()}/photo-{i}.jpg",
                content_type="image/jpeg",
                size_bytes=10000 * (i + 1),
            )
            await repo.create(attachment)

        count = await repo.count_by_entity(
            organization_id=test_org.id,
            entity_type=EntityType.LOCATION,
            entity_id=entity_id,
        )

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_all_for_org(
        self,
        db_session: AsyncSession,
        test_org: Organization,
    ):
        """Test getting all attachments for an organization."""
        repo = AttachmentRepository(db_session)

        # Create attachments of different entity types
        entity_types = [EntityType.DOCUMENT, EntityType.PASSWORD, EntityType.LOCATION]
        for entity_type in entity_types:
            entity_id = uuid4()
            attachment = Attachment(
                organization_id=test_org.id,
                entity_type=entity_type,
                entity_id=entity_id,
                filename=f"{entity_type.value}-file.txt",
                s3_key=f"{test_org.id}/{entity_type.value}/{entity_id}/{uuid4()}/file.txt",
                content_type="text/plain",
                size_bytes=100,
            )
            await repo.create(attachment)

        # Get all
        all_attachments = await repo.get_all_for_org(test_org.id)
        assert len(all_attachments) >= 3

        # Filter by entity type
        doc_attachments = await repo.get_all_for_org(
            test_org.id, entity_type=EntityType.DOCUMENT
        )
        assert all(a.entity_type == EntityType.DOCUMENT for a in doc_attachments)

    @pytest.mark.asyncio
    async def test_get_by_s3_key(
        self,
        db_session: AsyncSession,
        test_attachment: Attachment,
    ):
        """Test getting attachment by S3 key."""
        repo = AttachmentRepository(db_session)

        found = await repo.get_by_s3_key(test_attachment.s3_key)

        assert found is not None
        assert found.id == test_attachment.id

        # Non-existent key
        not_found = await repo.get_by_s3_key("nonexistent/key.pdf")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_delete_attachment(
        self,
        db_session: AsyncSession,
        test_attachment: Attachment,
    ):
        """Test deleting an attachment."""
        repo = AttachmentRepository(db_session)

        await repo.delete(test_attachment)

        # Verify deleted
        found = await repo.get_by_id(test_attachment.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_by_entity(
        self,
        db_session: AsyncSession,
        test_org: Organization,
    ):
        """Test deleting all attachments for an entity."""
        repo = AttachmentRepository(db_session)
        entity_id = uuid4()

        # Create attachments
        s3_keys = []
        for i in range(3):
            s3_key = f"{test_org.id}/document/{entity_id}/{uuid4()}/doc-{i}.pdf"
            s3_keys.append(s3_key)
            attachment = Attachment(
                organization_id=test_org.id,
                entity_type=EntityType.DOCUMENT,
                entity_id=entity_id,
                filename=f"doc-{i}.pdf",
                s3_key=s3_key,
                content_type="application/pdf",
                size_bytes=1000,
            )
            await repo.create(attachment)

        # Delete all attachments for entity
        deleted_keys = await repo.delete_by_entity(
            organization_id=test_org.id,
            entity_type=EntityType.DOCUMENT,
            entity_id=entity_id,
        )

        # Verify keys returned
        assert len(deleted_keys) == 3
        for key in s3_keys:
            assert key in deleted_keys

        # Verify deleted from database
        remaining = await repo.get_by_entity(
            organization_id=test_org.id,
            entity_type=EntityType.DOCUMENT,
            entity_id=entity_id,
        )
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_calculate_storage_for_org(
        self,
        db_session: AsyncSession,
        test_org: Organization,
    ):
        """Test calculating total storage used by an organization."""
        repo = AttachmentRepository(db_session)

        # Create attachments with known sizes
        sizes = [1000, 2000, 3000]
        for i, size in enumerate(sizes):
            entity_id = uuid4()
            attachment = Attachment(
                organization_id=test_org.id,
                entity_type=EntityType.DOCUMENT,
                entity_id=entity_id,
                filename=f"file-{i}.txt",
                s3_key=f"{test_org.id}/document/{entity_id}/{uuid4()}/file-{i}.txt",
                content_type="text/plain",
                size_bytes=size,
            )
            await repo.create(attachment)

        total = await repo.calculate_storage_for_org(test_org.id)

        assert total >= sum(sizes)

    @pytest.mark.asyncio
    async def test_pagination(
        self,
        db_session: AsyncSession,
        test_org: Organization,
    ):
        """Test pagination for listing attachments."""
        repo = AttachmentRepository(db_session)
        entity_id = uuid4()

        # Create 10 attachments
        for i in range(10):
            attachment = Attachment(
                organization_id=test_org.id,
                entity_type=EntityType.CUSTOM_ASSET,
                entity_id=entity_id,
                filename=f"asset-{i}.bin",
                s3_key=f"{test_org.id}/custom_asset/{entity_id}/{uuid4()}/asset-{i}.bin",
                content_type="application/octet-stream",
                size_bytes=100,
            )
            await repo.create(attachment)

        # Get first page
        page1 = await repo.get_by_entity(
            organization_id=test_org.id,
            entity_type=EntityType.CUSTOM_ASSET,
            entity_id=entity_id,
            limit=5,
            offset=0,
        )
        assert len(page1) == 5

        # Get second page
        page2 = await repo.get_by_entity(
            organization_id=test_org.id,
            entity_type=EntityType.CUSTOM_ASSET,
            entity_id=entity_id,
            limit=5,
            offset=5,
        )
        assert len(page2) == 5

        # Ensure no duplicates
        page1_ids = {a.id for a in page1}
        page2_ids = {a.id for a in page2}
        assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.integration
class TestAttachmentEntityTypes:
    """Test attachments with different entity types."""

    @pytest.mark.asyncio
    async def test_all_entity_types(
        self,
        db_session: AsyncSession,
        test_org: Organization,
    ):
        """Test creating attachments for all entity types."""
        repo = AttachmentRepository(db_session)

        for entity_type in EntityType:
            entity_id = uuid4()
            attachment = Attachment(
                organization_id=test_org.id,
                entity_type=entity_type,
                entity_id=entity_id,
                filename=f"{entity_type.value}-attachment.txt",
                s3_key=f"{test_org.id}/{entity_type.value}/{entity_id}/{uuid4()}/file.txt",
                content_type="text/plain",
                size_bytes=100,
            )
            created = await repo.create(attachment)

            assert created.entity_type == entity_type

            # Verify can query by entity type
            found = await repo.get_by_entity(
                organization_id=test_org.id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            assert len(found) == 1
            assert found[0].entity_type == entity_type
