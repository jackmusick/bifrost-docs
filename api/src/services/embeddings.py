"""
Embeddings Service.

Provides semantic search capabilities using OpenAI embeddings and pgvector.
Also provides text-based search fallback when OpenAI is not configured.
Handles entity indexing, embedding generation, and similarity search.
"""

import hashlib
import logging
from typing import Any, Literal
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contracts.custom_asset import FieldDefinition
from src.models.contracts.search import SearchResult
from src.models.orm.configuration import Configuration
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.custom_asset_type import CustomAssetType
from src.models.orm.document import Document
from src.models.orm.embedding_index import EMBEDDING_DIMENSIONS, EmbeddingIndex
from src.models.orm.location import Location
from src.models.orm.organization import Organization
from src.models.orm.password import Password
from src.services.llm.factory import get_embeddings_config

logger = logging.getLogger(__name__)

EntityType = Literal["password", "configuration", "location", "document", "custom_asset"]


class EmbeddingsService:
    """
    Service for managing embeddings and semantic search.

    Handles:
    - Generating embeddings via OpenAI API
    - Indexing entities for search
    - Performing similarity searches (semantic and text-based)
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the embeddings service.

        Args:
            db: Database session for fetching AI settings
        """
        self.db = db
        self._api_key: str | None = None
        self._model: str | None = None
        self._client: AsyncOpenAI | None = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Fetch AI settings from database if not already done."""
        if self._initialized:
            return

        config = await get_embeddings_config(self.db)
        if config:
            self._api_key = config.api_key
            self._model = config.model
        else:
            self._api_key = None
            self._model = "text-embedding-3-small"

        self._initialized = True

    @property
    def is_openai_available(self) -> bool:
        """Check if OpenAI API is configured and available."""
        return bool(self._api_key)

    async def check_openai_available(self) -> bool:
        """Async check if OpenAI API is configured and available."""
        await self._ensure_initialized()
        return bool(self._api_key)

    async def get_client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client."""
        await self._ensure_initialized()
        if self._client is None:
            if not self._api_key:
                raise ValueError("OpenAI API key is not configured")
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text using OpenAI API.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        client = await self.get_client()
        await self._ensure_initialized()

        response = await client.embeddings.create(
            input=text,
            model=self._model or "text-embedding-3-small",
            dimensions=EMBEDDING_DIMENSIONS,
        )

        return response.data[0].embedding

    def compute_content_hash(self, text: str) -> str:
        """
        Compute MD5 hash of content to detect changes.

        Args:
            text: Text to hash

        Returns:
            32-character hex MD5 hash
        """
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    async def _get_entity_and_org(
        self,
        db: AsyncSession,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> tuple[Any, Organization] | None:
        """
        Fetch entity and its organization.

        Returns:
            Tuple of (entity, organization) or None if not found
        """
        match entity_type:
            case "password":
                result = await db.execute(
                    select(Password, Organization)
                    .join(Organization, Password.organization_id == Organization.id)
                    .where(Password.id == entity_id)
                )
            case "configuration":
                result = await db.execute(
                    select(Configuration, Organization)
                    .join(Organization, Configuration.organization_id == Organization.id)
                    .where(Configuration.id == entity_id)
                )
            case "location":
                result = await db.execute(
                    select(Location, Organization)
                    .join(Organization, Location.organization_id == Organization.id)
                    .where(Location.id == entity_id)
                )
            case "document":
                result = await db.execute(
                    select(Document, Organization)
                    .join(Organization, Document.organization_id == Organization.id)
                    .where(Document.id == entity_id)
                )
            case "custom_asset":
                result = await db.execute(
                    select(CustomAsset, Organization)
                    .join(Organization, CustomAsset.organization_id == Organization.id)
                    .where(CustomAsset.id == entity_id)
                )
            case _:
                raise ValueError(f"Unknown entity type: {entity_type}")

        row = result.one_or_none()
        if row is None:
            return None
        # Row is a tuple-like object, extract the entity and organization
        return (row[0], row[1])

    def extract_searchable_text(
        self,
        entity_type: EntityType,
        entity: Any,
        asset_type_fields: list[FieldDefinition] | None = None,
        display_field_key: str | None = None,
    ) -> str:
        """
        Extract searchable text from an entity.

        Different entity types have different searchable fields.
        Sensitive data (passwords, encrypted fields) is NEVER included.

        Args:
            entity_type: Type of entity
            entity: The entity object
            asset_type_fields: For custom_asset, the field definitions
            display_field_key: For custom_asset, the key of the display name field

        Returns:
            Searchable text string
        """
        parts: list[str] = []

        match entity_type:
            case "password":
                # Name + username + notes (NOT the password value!)
                parts.append(entity.name)
                if entity.username:
                    parts.append(f"Username: {entity.username}")
                if entity.url:
                    parts.append(f"URL: {entity.url}")
                if entity.notes:
                    parts.append(entity.notes)

            case "configuration":
                # name + serial_number + asset_tag + manufacturer + model + ip_address + notes
                parts.append(entity.name)
                if entity.serial_number:
                    parts.append(f"Serial: {entity.serial_number}")
                if entity.asset_tag:
                    parts.append(f"Asset Tag: {entity.asset_tag}")
                if entity.manufacturer:
                    parts.append(f"Manufacturer: {entity.manufacturer}")
                if entity.model:
                    parts.append(f"Model: {entity.model}")
                if entity.ip_address:
                    parts.append(f"IP: {entity.ip_address}")
                if entity.mac_address:
                    parts.append(f"MAC: {entity.mac_address}")
                if entity.notes:
                    parts.append(entity.notes)

            case "location":
                # name + notes
                parts.append(entity.name)
                if entity.notes:
                    parts.append(entity.notes)

            case "document":
                # name + path + content
                parts.append(entity.name)
                if entity.path and entity.path != "/":
                    parts.append(f"Path: {entity.path}")
                if entity.content:
                    parts.append(entity.content)

            case "custom_asset":
                # display name (from values) + non-password field values
                if display_field_key and entity.values:
                    display_name = entity.values.get(display_field_key)
                    if display_name:
                        parts.append(str(display_name))
                if entity.values and asset_type_fields:
                    password_keys = {f.key for f in asset_type_fields if f.type == "password"}
                    for key, value in entity.values.items():
                        # Skip password fields and their encrypted versions
                        if key in password_keys or key.endswith("_encrypted"):
                            continue
                        if value is not None:
                            # Find the field definition for display name
                            field_def = next((f for f in asset_type_fields if f.key == key), None)
                            field_name = field_def.name if field_def else key
                            parts.append(f"{field_name}: {value}")

        return "\n".join(parts)

    async def index_entity(
        self,
        db: AsyncSession,
        entity_type: EntityType,
        entity_id: UUID,
        org_id: UUID,
    ) -> EmbeddingIndex | None:
        """
        Index or re-index an entity for search.

        If the entity's content hasn't changed (same hash), skip re-indexing.

        Args:
            db: Database session
            entity_type: Type of entity
            entity_id: Entity UUID
            org_id: Organization UUID

        Returns:
            Created/updated EmbeddingIndex or None if skipped
        """
        # Fetch entity and organization
        result = await self._get_entity_and_org(db, entity_type, entity_id)
        if not result:
            logger.warning(f"Entity not found for indexing: {entity_type}/{entity_id}")
            return None

        entity, _org = result

        # For custom assets, fetch the type's field definitions
        asset_type_fields: list[FieldDefinition] | None = None
        display_field_key: str | None = None
        if entity_type == "custom_asset":
            type_result = await db.execute(
                select(CustomAssetType).where(CustomAssetType.id == entity.custom_asset_type_id)
            )
            asset_type = type_result.scalar_one_or_none()
            if asset_type:
                asset_type_fields = [FieldDefinition(**f) for f in asset_type.fields]
                display_field_key = asset_type.display_field_key

        # Extract searchable text
        searchable_text = self.extract_searchable_text(
            entity_type, entity, asset_type_fields, display_field_key
        )
        content_hash = self.compute_content_hash(searchable_text)

        # Check if we already have an index for this entity
        existing_result = await db.execute(
            select(EmbeddingIndex).where(
                EmbeddingIndex.entity_type == entity_type,
                EmbeddingIndex.entity_id == entity_id,
            )
        )
        existing = existing_result.scalar_one_or_none()

        # Skip if content hasn't changed
        if existing and existing.content_hash == content_hash:
            logger.debug(f"Skipping index update, content unchanged: {entity_type}/{entity_id}")
            return existing

        # Generate embedding
        try:
            embedding = await self.generate_embedding(searchable_text)
        except Exception as e:
            logger.error(f"Failed to generate embedding for {entity_type}/{entity_id}: {e}")
            raise

        if existing:
            # Update existing index
            existing.embedding = embedding
            existing.searchable_text = searchable_text
            existing.content_hash = content_hash
            await db.flush()
            logger.info(f"Updated embedding index: {entity_type}/{entity_id}")
            return existing
        else:
            # Create new index
            index = EmbeddingIndex(
                organization_id=org_id,
                entity_type=entity_type,
                entity_id=entity_id,
                content_hash=content_hash,
                embedding=embedding,
                searchable_text=searchable_text,
            )
            db.add(index)
            await db.flush()
            await db.refresh(index)
            logger.info(f"Created embedding index: {entity_type}/{entity_id}")
            return index

    async def delete_index(
        self,
        db: AsyncSession,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> bool:
        """
        Remove entity from search index.

        Args:
            db: Database session
            entity_type: Type of entity
            entity_id: Entity UUID

        Returns:
            True if deleted, False if not found
        """
        result = await db.execute(
            delete(EmbeddingIndex).where(
                EmbeddingIndex.entity_type == entity_type,
                EmbeddingIndex.entity_id == entity_id,
            )
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted embedding index: {entity_type}/{entity_id}")
        return deleted

    async def search(
        self,
        db: AsyncSession,
        query: str,
        org_ids: list[UUID],
        limit: int = 20,
        show_disabled: bool = False,
    ) -> list[SearchResult]:
        """
        Perform semantic search across organizations.

        Args:
            db: Database session
            query: Search query text
            org_ids: List of organization IDs to search within
            limit: Maximum number of results
            show_disabled: Include disabled entities in results (default: False)

        Returns:
            List of search results ordered by relevance
        """
        if not org_ids:
            return []

        if not query.strip():
            return []

        # Generate query embedding
        try:
            query_embedding = await self.generate_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise

        # Perform similarity search using cosine distance
        # pgvector's <=> operator computes cosine distance (1 - cosine_similarity)
        # Lower distance = higher similarity
        # We convert to similarity score: 1 - distance
        from sqlalchemy import literal

        # Build the query with cosine distance
        distance_expr = EmbeddingIndex.embedding.cosine_distance(query_embedding)

        # Build base query
        stmt = (
            select(
                EmbeddingIndex,
                Organization.name.label("org_name"),
                (literal(1.0) - distance_expr).label("score"),
            )
            .join(Organization, EmbeddingIndex.organization_id == Organization.id)
            .where(EmbeddingIndex.organization_id.in_(org_ids))
        )

        # Filter out disabled entities if show_disabled is False
        # This requires joining with each entity type table
        if not show_disabled:
            # Build OR conditions for each entity type to filter by is_enabled
            # We use a CASE approach: for each entity_type, join with its table
            # This is complex, so we'll filter after fetching for semantic search
            # For now, fetch all and filter in Python (not ideal but works)
            # TODO: Optimize with proper joins if performance becomes an issue
            pass

        stmt = stmt.order_by(distance_expr).limit(limit)

        result = await db.execute(stmt)
        rows = result.all()

        # Filter out disabled entities if show_disabled is False
        if not show_disabled:
            filtered_rows = []
            for row in rows:
                index: EmbeddingIndex = row[0]
                # Check if the entity is enabled
                is_enabled = await self._check_entity_enabled(db, index.entity_type, index.entity_id)
                if is_enabled:
                    filtered_rows.append(row)
            rows = filtered_rows

        # Convert to SearchResult objects
        results: list[SearchResult] = []
        for row in rows:
            index: EmbeddingIndex = row[0]
            org_name: str = row[1]
            score: float = float(row[2])

            # Get entity name by fetching the entity
            entity_name = await self._get_entity_name(db, index.entity_type, index.entity_id)

            # Get entity enabled status
            is_enabled = await self._check_entity_enabled(db, index.entity_type, index.entity_id)

            # Create snippet from searchable text (first 200 chars)
            snippet = index.searchable_text[:200]
            if len(index.searchable_text) > 200:
                snippet += "..."

            results.append(
                SearchResult(
                    entity_type=index.entity_type,  # type: ignore[arg-type]
                    entity_id=str(index.entity_id),
                    organization_id=str(index.organization_id),
                    organization_name=org_name,
                    name=entity_name or "Unknown",
                    snippet=snippet,
                    score=max(0.0, min(1.0, score)),  # Clamp to 0-1
                    is_enabled=is_enabled,
                )
            )

        return results

    async def text_search(
        self,
        db: AsyncSession,
        query: str,
        org_ids: list[UUID],
        limit: int = 20,
        show_disabled: bool = False,
    ) -> list[SearchResult]:
        """
        Perform text-based search using PostgreSQL ILIKE matching.

        Searches across all entity types using simple text matching.
        Does not require OpenAI API.

        Args:
            db: Database session
            query: Search query text
            org_ids: List of organization IDs to search within
            limit: Maximum number of results
            show_disabled: Include disabled entities in results (default: False)

        Returns:
            List of search results ordered by relevance
        """
        if not org_ids:
            return []

        if not query.strip():
            return []

        # Prepare the search pattern for ILIKE
        search_pattern = f"%{query}%"

        results: list[SearchResult] = []
        seen_entities: set[tuple[str, str]] = set()

        # Search passwords (name, username, url, notes)
        password_conditions = [
            Password.organization_id.in_(org_ids),
            or_(
                Password.name.ilike(search_pattern),
                Password.username.ilike(search_pattern),
                Password.url.ilike(search_pattern),
                Password.notes.ilike(search_pattern),
            ),
        ]
        if not show_disabled:
            password_conditions.append(Password.is_enabled)

        password_stmt = (
            select(Password, Organization.name.label("org_name"))
            .join(Organization, Password.organization_id == Organization.id)
            .where(*password_conditions)
            .limit(limit)
        )
        password_result = await db.execute(password_stmt)
        for row in password_result.all():
            entity = row[0]
            org_name = row[1]
            key = ("password", str(entity.id))
            if key not in seen_entities:
                seen_entities.add(key)
                snippet = self._build_snippet(entity.name, entity.username, entity.url, entity.notes)
                results.append(
                    SearchResult(
                        entity_type="password",
                        entity_id=str(entity.id),
                        organization_id=str(entity.organization_id),
                        organization_name=org_name,
                        name=entity.name,
                        snippet=snippet,
                        score=self._calculate_text_score(query, snippet),
                        is_enabled=entity.is_enabled,
                    )
                )

        # Search documents (name, path, content)
        document_conditions = [
            Document.organization_id.in_(org_ids),
            or_(
                Document.name.ilike(search_pattern),
                Document.path.ilike(search_pattern),
                Document.content.ilike(search_pattern),
            ),
        ]
        if not show_disabled:
            document_conditions.append(Document.is_enabled)

        document_stmt = (
            select(Document, Organization.name.label("org_name"))
            .join(Organization, Document.organization_id == Organization.id)
            .where(*document_conditions)
            .limit(limit)
        )
        document_result = await db.execute(document_stmt)
        for row in document_result.all():
            entity = row[0]
            org_name = row[1]
            key = ("document", str(entity.id))
            if key not in seen_entities:
                seen_entities.add(key)
                snippet = self._build_snippet(entity.name, entity.path, entity.content)
                results.append(
                    SearchResult(
                        entity_type="document",
                        entity_id=str(entity.id),
                        organization_id=str(entity.organization_id),
                        organization_name=org_name,
                        name=entity.name,
                        snippet=snippet,
                        score=self._calculate_text_score(query, snippet),
                        is_enabled=entity.is_enabled,
                    )
                )

        # Search configurations (name, serial_number, asset_tag, manufacturer, model, ip, mac, notes)
        config_conditions = [
            Configuration.organization_id.in_(org_ids),
            or_(
                Configuration.name.ilike(search_pattern),
                Configuration.serial_number.ilike(search_pattern),
                Configuration.asset_tag.ilike(search_pattern),
                Configuration.manufacturer.ilike(search_pattern),
                Configuration.model.ilike(search_pattern),
                Configuration.ip_address.ilike(search_pattern),
                Configuration.mac_address.ilike(search_pattern),
                Configuration.notes.ilike(search_pattern),
            ),
        ]
        if not show_disabled:
            config_conditions.append(Configuration.is_enabled)

        config_stmt = (
            select(Configuration, Organization.name.label("org_name"))
            .join(Organization, Configuration.organization_id == Organization.id)
            .where(*config_conditions)
            .limit(limit)
        )
        config_result = await db.execute(config_stmt)
        for row in config_result.all():
            entity = row[0]
            org_name = row[1]
            key = ("configuration", str(entity.id))
            if key not in seen_entities:
                seen_entities.add(key)
                snippet = self._build_snippet(
                    entity.name,
                    entity.manufacturer,
                    entity.model,
                    entity.serial_number,
                    entity.notes,
                )
                results.append(
                    SearchResult(
                        entity_type="configuration",
                        entity_id=str(entity.id),
                        organization_id=str(entity.organization_id),
                        organization_name=org_name,
                        name=entity.name,
                        snippet=snippet,
                        score=self._calculate_text_score(query, snippet),
                        is_enabled=entity.is_enabled,
                    )
                )

        # Search locations (name, notes)
        location_conditions = [
            Location.organization_id.in_(org_ids),
            or_(
                Location.name.ilike(search_pattern),
                Location.notes.ilike(search_pattern),
            ),
        ]
        if not show_disabled:
            location_conditions.append(Location.is_enabled)

        location_stmt = (
            select(Location, Organization.name.label("org_name"))
            .join(Organization, Location.organization_id == Organization.id)
            .where(*location_conditions)
            .limit(limit)
        )
        location_result = await db.execute(location_stmt)
        for row in location_result.all():
            entity = row[0]
            org_name = row[1]
            key = ("location", str(entity.id))
            if key not in seen_entities:
                seen_entities.add(key)
                snippet = self._build_snippet(entity.name, entity.notes)
                results.append(
                    SearchResult(
                        entity_type="location",
                        entity_id=str(entity.id),
                        organization_id=str(entity.organization_id),
                        organization_name=org_name,
                        name=entity.name,
                        snippet=snippet,
                        score=self._calculate_text_score(query, snippet),
                        is_enabled=entity.is_enabled,
                    )
                )

        # Search custom assets (name + values as text - but not password fields)
        # Note: For custom assets, we use the embedding_index.searchable_text
        # which already excludes password fields
        custom_asset_conditions = [
            EmbeddingIndex.organization_id.in_(org_ids),
            EmbeddingIndex.entity_type == "custom_asset",
            EmbeddingIndex.searchable_text.ilike(search_pattern),
        ]
        # Note: We need to filter by CustomAsset.is_enabled, but EmbeddingIndex
        # doesn't have this field. We'll filter after fetching.
        # For now, include the filter in the query if show_disabled is False
        # by joining with CustomAsset table
        if not show_disabled:
            # Join with CustomAsset to filter by is_enabled
            custom_asset_stmt = (
                select(
                    EmbeddingIndex,
                    Organization.name.label("org_name"),
                )
                .join(Organization, EmbeddingIndex.organization_id == Organization.id)
                .join(CustomAsset, EmbeddingIndex.entity_id == CustomAsset.id)
                .where(*custom_asset_conditions, CustomAsset.is_enabled)
                .limit(limit)
            )
        else:
            custom_asset_stmt = (
                select(
                    EmbeddingIndex,
                    Organization.name.label("org_name"),
                )
                .join(Organization, EmbeddingIndex.organization_id == Organization.id)
                .where(*custom_asset_conditions)
                .limit(limit)
            )
        custom_asset_result = await db.execute(custom_asset_stmt)
        for row in custom_asset_result.all():
            index = row[0]
            org_name = row[1]
            key = ("custom_asset", str(index.entity_id))
            if key not in seen_entities:
                seen_entities.add(key)
                entity_name = await self._get_entity_name(db, "custom_asset", index.entity_id)
                # Get custom asset enabled status
                is_enabled = await self._check_entity_enabled(db, "custom_asset", index.entity_id)
                snippet = index.searchable_text[:200]
                if len(index.searchable_text) > 200:
                    snippet += "..."
                results.append(
                    SearchResult(
                        entity_type="custom_asset",
                        entity_id=str(index.entity_id),
                        organization_id=str(index.organization_id),
                        organization_name=org_name,
                        name=entity_name or "Unknown",
                        snippet=snippet,
                        score=self._calculate_text_score(query, snippet),
                        is_enabled=is_enabled,
                    )
                )

        # Sort by score descending and limit results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def _build_snippet(self, *parts: str | None) -> str:
        """Build a snippet from multiple text parts."""
        non_empty = [p for p in parts if p]
        text = " | ".join(non_empty)
        if len(text) > 200:
            return text[:197] + "..."
        return text

    def _calculate_text_score(self, query: str, text: str) -> float:
        """
        Calculate a relevance score for text search.

        Uses a simple heuristic:
        - Exact match: 0.9
        - Query at start of text: 0.8
        - Contains query: 0.6
        - Base: 0.5

        Args:
            query: Search query
            text: Text being matched

        Returns:
            Score between 0 and 1
        """
        query_lower = query.lower()
        text_lower = text.lower()

        if query_lower == text_lower:
            return 0.9
        if text_lower.startswith(query_lower):
            return 0.8
        if query_lower in text_lower:
            # Score based on how much of the text is the query
            ratio = len(query) / len(text) if text else 0
            return 0.5 + (ratio * 0.2)
        return 0.5

    async def hybrid_search(
        self,
        db: AsyncSession,
        query: str,
        org_ids: list[UUID],
        limit: int = 20,
        show_disabled: bool = False,
    ) -> list[SearchResult]:
        """
        Perform hybrid search combining semantic and text search.

        When OpenAI is available, runs both semantic and text search,
        combines results, deduplicates, and ranks by relevance.
        Semantic results are weighted higher than text matches.

        When OpenAI is not available, falls back to text search only.

        Args:
            db: Database session
            query: Search query text
            org_ids: List of organization IDs to search within
            limit: Maximum number of results
            show_disabled: Include disabled entities in results (default: False)

        Returns:
            List of search results ordered by relevance
        """
        if not org_ids:
            return []

        if not query.strip():
            return []

        # If OpenAI is not available, use text search only
        if not await self.check_openai_available():
            logger.info("OpenAI not configured, using text search only")
            return await self.text_search(db, query, org_ids, limit=limit, show_disabled=show_disabled)

        # Run both searches
        try:
            semantic_results = await self.search(db, query, org_ids, limit=limit, show_disabled=show_disabled)
        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to text search: {e}")
            return await self.text_search(db, query, org_ids, limit=limit, show_disabled=show_disabled)

        text_results = await self.text_search(db, query, org_ids, limit=limit, show_disabled=show_disabled)

        # Combine and deduplicate results
        seen: set[tuple[str, str]] = set()
        combined: list[SearchResult] = []

        # Add semantic results first (higher priority)
        # Boost semantic scores slightly to ensure they rank higher
        for result in semantic_results:
            key = (result.entity_type, result.entity_id)
            if key not in seen:
                seen.add(key)
                # Boost semantic scores by 0.1 (capped at 1.0)
                boosted_score = min(1.0, result.score + 0.1)
                combined.append(
                    SearchResult(
                        entity_type=result.entity_type,
                        entity_id=result.entity_id,
                        organization_id=result.organization_id,
                        organization_name=result.organization_name,
                        name=result.name,
                        snippet=result.snippet,
                        score=boosted_score,
                        is_enabled=result.is_enabled,
                    )
                )

        # Add text results that weren't in semantic results
        for result in text_results:
            key = (result.entity_type, result.entity_id)
            if key not in seen:
                seen.add(key)
                combined.append(result)

        # Sort by score descending
        combined.sort(key=lambda x: x.score, reverse=True)

        return combined[:limit]

    async def _get_entity_name(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
    ) -> str | None:
        """Get the name of an entity by type and ID."""
        match entity_type:
            case "password":
                result = await db.execute(select(Password.name).where(Password.id == entity_id))
            case "configuration":
                result = await db.execute(
                    select(Configuration.name).where(Configuration.id == entity_id)
                )
            case "location":
                result = await db.execute(select(Location.name).where(Location.id == entity_id))
            case "document":
                result = await db.execute(select(Document.name).where(Document.id == entity_id))
            case "custom_asset":
                # Custom assets store name in values JSONB field
                result = await db.execute(
                    select(CustomAsset.values).where(CustomAsset.id == entity_id)
                )
                values = result.scalar_one_or_none()
                if values:
                    # Try common name fields
                    return values.get("name") or values.get("title") or values.get("domain")
                return None
            case _:
                return None

        return result.scalar_one_or_none()

    async def _check_entity_enabled(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
    ) -> bool:
        """Check if an entity is enabled by type and ID."""
        match entity_type:
            case "password":
                result = await db.execute(
                    select(Password.is_enabled).where(Password.id == entity_id)
                )
            case "configuration":
                result = await db.execute(
                    select(Configuration.is_enabled).where(Configuration.id == entity_id)
                )
            case "location":
                result = await db.execute(
                    select(Location.is_enabled).where(Location.id == entity_id)
                )
            case "document":
                result = await db.execute(
                    select(Document.is_enabled).where(Document.id == entity_id)
                )
            case "custom_asset":
                result = await db.execute(
                    select(CustomAsset.is_enabled).where(CustomAsset.id == entity_id)
                )
            case _:
                return True  # Unknown entity type, assume enabled

        is_enabled = result.scalar_one_or_none()
        return is_enabled if is_enabled is not None else True


def get_embeddings_service(db: AsyncSession) -> EmbeddingsService:
    """
    Create an embeddings service instance.

    Args:
        db: Database session for fetching AI settings

    Returns:
        EmbeddingsService instance
    """
    return EmbeddingsService(db)
