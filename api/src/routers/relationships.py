"""
Relationships Router

Provides endpoints for managing entity relationships.
Relationships are bidirectional - linking entity A to entity B
allows querying from either side.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.core.auth import CurrentActiveUser, RequireContributor
from src.core.database import DbSession
from src.models.contracts.relationship import (
    RelatedEntity,
    RelatedItemsResponse,
    RelationshipCreate,
    RelationshipPublic,
)
from src.repositories.relationship import RelationshipRepository
from src.services.entity_resolver import VALID_ENTITY_TYPES, EntityResolver

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/organizations/{org_id}/relationships", tags=["relationships"]
)


def _validate_entity_type(entity_type: str) -> None:
    """Validate that entity type is valid."""
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type: {entity_type}. Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}",
        )


@router.get("", response_model=list[RelationshipPublic])
async def list_relationships(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    entity_type: str = Query(..., description="Entity type to query relationships for"),
    entity_id: UUID = Query(..., description="Entity ID to query relationships for"),
) -> list[RelationshipPublic]:
    """
    List all relationships for an entity.

    This is a bidirectional query - returns relationships where the entity
    is either the source or target.

    Args:
        org_id: Organization UUID
        entity_type: Entity type (password, configuration, location, document, custom_asset)
        entity_id: Entity UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of relationships involving this entity
    """
    _validate_entity_type(entity_type)

    repo = RelationshipRepository(db)
    relationships = await repo.get_for_entity(org_id, entity_type, entity_id)

    return [
        RelationshipPublic(
            id=str(r.id),
            organization_id=str(r.organization_id),
            source_type=r.source_type,
            source_id=str(r.source_id),
            target_type=r.target_type,
            target_id=str(r.target_id),
            created_at=r.created_at,
        )
        for r in relationships
    ]


@router.post("", response_model=RelationshipPublic, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    org_id: UUID,
    data: RelationshipCreate,
    current_user: RequireContributor,
    db: DbSession,
) -> RelationshipPublic:
    """
    Create a new relationship between two entities.

    The relationship is stored in normalized form to prevent duplicates.
    Creating A->B is equivalent to B->A.

    Args:
        org_id: Organization UUID
        data: Relationship creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created relationship
    """
    _validate_entity_type(data.source_type)
    _validate_entity_type(data.target_type)

    # Validate UUIDs
    try:
        source_id = UUID(data.source_id)
        target_id = UUID(data.target_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {e}",
        ) from e

    # Cannot relate an entity to itself
    if data.source_type == data.target_type and source_id == target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create relationship between an entity and itself",
        )

    # Verify both entities exist
    resolver = EntityResolver(db)
    source_name = await resolver.get_entity_name(org_id, data.source_type, source_id)
    if not source_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source entity not found: {data.source_type}/{data.source_id}",
        )

    target_name = await resolver.get_entity_name(org_id, data.target_type, target_id)
    if not target_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target entity not found: {data.target_type}/{data.target_id}",
        )

    # Check for existing relationship
    repo = RelationshipRepository(db)
    existing = await repo.find_existing(
        org_id, data.source_type, source_id, data.target_type, target_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Relationship already exists",
        )

    # Create the relationship (normalized)
    relationship = await repo.create_relationship(
        organization_id=org_id,
        source_type=data.source_type,
        source_id=source_id,
        target_type=data.target_type,
        target_id=target_id,
    )

    logger.info(
        f"Relationship created: {relationship.source_type}/{relationship.source_id} -> "
        f"{relationship.target_type}/{relationship.target_id}",
        extra={
            "relationship_id": str(relationship.id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )

    return RelationshipPublic(
        id=str(relationship.id),
        organization_id=str(relationship.organization_id),
        source_type=relationship.source_type,
        source_id=str(relationship.source_id),
        target_type=relationship.target_type,
        target_id=str(relationship.target_id),
        created_at=relationship.created_at,
    )


@router.delete("/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relationship(
    org_id: UUID,
    relationship_id: UUID,
    current_user: RequireContributor,
    db: DbSession,
) -> None:
    """
    Delete a relationship.

    Args:
        org_id: Organization UUID
        relationship_id: Relationship UUID
        current_user: Current authenticated user
        db: Database session
    """
    repo = RelationshipRepository(db)
    relationship = await repo.get_by_id_and_org(relationship_id, org_id)

    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found",
        )

    await repo.delete(relationship)

    logger.info(
        f"Relationship deleted: {relationship.source_type}/{relationship.source_id} -> "
        f"{relationship.target_type}/{relationship.target_id}",
        extra={
            "relationship_id": str(relationship.id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )


@router.get("/resolved", response_model=RelatedItemsResponse)
async def get_resolved_relationships(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    entity_type: str = Query(..., description="Entity type to query relationships for"),
    entity_id: UUID = Query(..., description="Entity ID to query relationships for"),
) -> RelatedItemsResponse:
    """
    Get relationships with resolved entity names.

    Returns the related entities with their names resolved for display.

    Args:
        org_id: Organization UUID
        entity_type: Entity type (password, configuration, location, document, custom_asset)
        entity_id: Entity UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of related entities with resolved names
    """
    _validate_entity_type(entity_type)

    repo = RelationshipRepository(db)
    relationships = await repo.get_for_entity(org_id, entity_type, entity_id)

    # Collect the "other" entities (the ones that aren't the queried entity)
    resolver = EntityResolver(db)
    items: list[RelatedEntity] = []

    for rel in relationships:
        # Determine which side is the "other" entity
        if rel.source_type == entity_type and rel.source_id == entity_id:
            other_type = rel.target_type
            other_id = rel.target_id
        else:
            other_type = rel.source_type
            other_id = rel.source_id

        # Resolve the name
        name = await resolver.get_entity_name(org_id, other_type, other_id)
        if name:  # Only include if entity still exists
            items.append(
                RelatedEntity(
                    entity_type=other_type,
                    entity_id=str(other_id),
                    name=name,
                )
            )

    return RelatedItemsResponse(items=items)
