"""
Embedding Index ORM model.

Stores vector embeddings for semantic search across all entity types.
Uses pgvector for efficient similarity search.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.organization import Organization

# OpenAI text-embedding-ada-002 produces 1536-dimensional vectors
EMBEDDING_DIMENSIONS = 1536


class EmbeddingIndex(Base):
    """Embedding index database table for semantic search."""

    __tablename__ = "embedding_index"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of entity: password, configuration, location, document, custom_asset",
    )
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    content_hash: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="MD5 hash of searchable_text to detect changes",
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=False,
    )
    searchable_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The text that was embedded",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        # Unique constraint on entity_type + entity_id (one embedding per entity)
        UniqueConstraint("entity_type", "entity_id", name="uq_embedding_entity"),
        # Index for filtering by organization
        Index("ix_embedding_index_organization_id", "organization_id"),
        # Index for filtering by entity type
        Index("ix_embedding_index_entity_type", "entity_type"),
        # Note: Vector index for similarity search is created in migration
        # using ivfflat operator class for cosine distance
    )
