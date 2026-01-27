"""
Documents Router

Provides CRUD endpoints for documents within organizations.
All endpoints are scoped to organization for multi-tenancy.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import update

from src.core.auth import CurrentActiveUser, RequireContributor
from src.core.database import DbSession
from src.models.contracts.common import BatchToggleRequest, BatchToggleResponse
from src.models.contracts.document import (
    DocumentCreate,
    DocumentPublic,
    DocumentUpdate,
    FolderCount,
    FolderList,
)
from src.models.enums import AuditAction
from src.models.orm.document import Document
from src.repositories.document import DocumentRepository
from src.services.audit_service import get_audit_service
from src.services.document_mutations import DocumentMutationService
from src.services.llm import get_completions_config, get_llm_client
from src.services.search_indexing import index_entity_for_search, remove_entity_from_search


class DocumentListResponse(BaseModel):
    """Paginated response for document list."""

    items: list[DocumentPublic]
    total: int
    limit: int
    offset: int


class BatchPathUpdateRequest(BaseModel):
    """Request to update paths for section rename."""

    old_path_prefix: str
    new_path_prefix: str
    merge_if_exists: bool = False


class BatchPathUpdateResponse(BaseModel):
    """Response for batch path update."""

    updated_count: int
    conflicts: list[str] = []  # Document names that would conflict


class CleanDocumentResponse(BaseModel):
    """Response for document cleaning operation."""

    cleaned_content: str
    summary: str
    suggested_name: str | None = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations/{org_id}/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    path: str | None = Query(None, description="Filter by folder path"),
    search: str | None = Query(None, description="Search by name, path, or content"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    show_disabled: bool = Query(False, description="Include disabled documents"),
) -> DocumentListResponse:
    """
    List documents in an organization with pagination and search.

    Optionally filter by path to get documents in a specific folder.

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session
        path: Optional folder path filter
        search: Optional search term
        sort_by: Column to sort by
        sort_dir: Sort direction ("asc" or "desc")
        limit: Maximum number of results
        offset: Number of results to skip
        show_disabled: Include disabled documents

    Returns:
        Paginated list of documents
    """
    doc_repo = DocumentRepository(db)
    # Filter by is_enabled: when show_disabled=False, only show enabled (True)
    # When show_disabled=True, show all (None filter)
    is_enabled_filter = None if show_disabled else True
    documents, total = await doc_repo.get_paginated_by_org(
        org_id,
        path=path,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        is_enabled=is_enabled_filter,
    )

    items = [
        DocumentPublic(
            id=str(doc.id),
            organization_id=str(doc.organization_id),
            path=doc.path,
            name=doc.name,
            content=doc.content,
            metadata=doc.metadata_ if isinstance(doc.metadata_, dict) else {},
            is_enabled=doc.is_enabled,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            updated_by_user_id=str(doc.updated_by_user_id) if doc.updated_by_user_id else None,
            updated_by_user_name=(doc.updated_by_user.name or doc.updated_by_user.email) if doc.updated_by_user else None,
        )
        for doc in documents
    ]

    return DocumentListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/folders", response_model=FolderList)
async def list_folders(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> FolderList:
    """
    Get distinct folder paths with document counts for building folder tree.

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of folders with document counts
    """
    doc_repo = DocumentRepository(db)
    paths_with_counts = await doc_repo.get_paths_with_counts(org_id)

    return FolderList(
        folders=[
            FolderCount(path=path, count=count) for path, count in paths_with_counts
        ]
    )


@router.post("", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED)
async def create_document(
    org_id: UUID,
    doc_data: DocumentCreate,
    current_user: RequireContributor,
    db: DbSession,
) -> DocumentPublic:
    """
    Create a new document.

    Args:
        org_id: Organization UUID
        doc_data: Document creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created document
    """
    doc_repo = DocumentRepository(db)

    doc = Document(
        organization_id=org_id,
        path=doc_data.path,
        name=doc_data.name,
        content=doc_data.content,
        metadata_=doc_data.metadata,
        is_enabled=doc_data.is_enabled if doc_data.is_enabled is not None else True,
    )
    doc = await doc_repo.create(doc)

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.CREATE,
        "document",
        doc.id,
        actor=current_user,
        organization_id=org_id,
    )

    logger.info(
        f"Document created: {doc.name}",
        extra={
            "doc_id": str(doc.id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )

    # Index for search (async, non-blocking on failure)
    await index_entity_for_search(db, "document", doc.id, org_id)

    return DocumentPublic(
        id=str(doc.id),
        organization_id=str(doc.organization_id),
        path=doc.path,
        name=doc.name,
        content=doc.content,
        metadata=doc.metadata_ if isinstance(doc.metadata_, dict) else {},
        is_enabled=doc.is_enabled,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        updated_by_user_id=str(doc.updated_by_user_id) if doc.updated_by_user_id else None,
        updated_by_user_name=(doc.updated_by_user.name or doc.updated_by_user.email) if doc.updated_by_user else None,
    )


@router.get("/{doc_id}", response_model=DocumentPublic)
async def get_document(
    org_id: UUID,
    doc_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> DocumentPublic:
    """
    Get document by ID.

    Args:
        org_id: Organization UUID
        doc_id: Document UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Document details

    Raises:
        HTTPException: If document not found
    """
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id_and_org(doc_id, org_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Log view (with 60-second dedupe)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.VIEW,
        "document",
        doc.id,
        actor=current_user,
        organization_id=org_id,
        dedupe_seconds=60,
    )

    return DocumentPublic(
        id=str(doc.id),
        organization_id=str(doc.organization_id),
        path=doc.path,
        name=doc.name,
        content=doc.content,
        metadata=doc.metadata_ if isinstance(doc.metadata_, dict) else {},
        is_enabled=doc.is_enabled,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        updated_by_user_id=str(doc.updated_by_user_id) if doc.updated_by_user_id else None,
        updated_by_user_name=(doc.updated_by_user.name or doc.updated_by_user.email) if doc.updated_by_user else None,
    )


@router.get("/{doc_id}/preview")
async def get_document_preview(
    org_id: UUID,
    doc_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> dict:
    """
    Get document preview for search.

    Returns the document content suitable for rendering in a preview panel.

    Args:
        org_id: Organization UUID
        doc_id: Document UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Preview data with document content

    Raises:
        HTTPException: If document not found
    """
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id_and_org(doc_id, org_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return {
        "id": str(doc.id),
        "name": doc.name,
        "content": doc.content or "",
        "entity_type": "document",
        "organization_id": str(org_id),
    }


@router.post("/{doc_id}/clean", response_model=CleanDocumentResponse)
async def clean_document(
    org_id: UUID,
    doc_id: UUID,
    current_user: RequireContributor,
    db: DbSession,
) -> CleanDocumentResponse:
    """
    Clean and restructure a document using AI.

    Uses the Diataxis framework to clean, restructure, and improve the document.
    Returns the cleaned content without modifying the original document.

    Args:
        org_id: Organization UUID
        doc_id: Document UUID
        current_user: Current authenticated user (requires Contributor role)
        db: Database session

    Returns:
        Cleaned content and summary of changes

    Raises:
        HTTPException: If document not found
    """
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id_and_org(doc_id, org_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Create service and generate cleaned content
    config = await get_completions_config(db)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not configured",
        )
    llm_client = get_llm_client(config)
    mutation_service = DocumentMutationService(llm_client)

    cleaned_content, summary, suggested_name = await mutation_service.generate_cleaned_content(
        original_content=doc.content or "",
        document_name=doc.name,
        user_instruction="clean this up",
    )

    logger.info(
        f"Document cleaned: {doc.name}",
        extra={
            "doc_id": str(doc.id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )

    return CleanDocumentResponse(
        cleaned_content=cleaned_content,
        summary=summary,
        suggested_name=suggested_name,
    )


@router.put("/{doc_id}", response_model=DocumentPublic)
async def update_document(
    org_id: UUID,
    doc_id: UUID,
    doc_data: DocumentUpdate,
    current_user: RequireContributor,
    db: DbSession,
) -> DocumentPublic:
    """
    Update a document.

    Args:
        org_id: Organization UUID
        doc_id: Document UUID
        doc_data: Document update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated document

    Raises:
        HTTPException: If document not found
    """
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id_and_org(doc_id, org_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Update fields if provided
    if doc_data.path is not None:
        doc.path = doc_data.path
    if doc_data.name is not None:
        doc.name = doc_data.name
    if doc_data.content is not None:
        doc.content = doc_data.content
    if doc_data.metadata is not None:
        doc.metadata_ = doc_data.metadata
    if doc_data.is_enabled is not None:
        doc.is_enabled = doc_data.is_enabled

    # Track who updated
    doc.updated_by_user_id = current_user.user_id

    doc = await doc_repo.update(doc)

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.UPDATE,
        "document",
        doc.id,
        actor=current_user,
        organization_id=org_id,
    )

    logger.info(
        f"Document updated: {doc.name}",
        extra={
            "doc_id": str(doc.id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )

    # Update search index (async, non-blocking on failure)
    await index_entity_for_search(db, "document", doc.id, org_id)

    return DocumentPublic(
        id=str(doc.id),
        organization_id=str(doc.organization_id),
        path=doc.path,
        name=doc.name,
        content=doc.content,
        metadata=doc.metadata_ if isinstance(doc.metadata_, dict) else {},
        is_enabled=doc.is_enabled,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        updated_by_user_id=str(doc.updated_by_user_id) if doc.updated_by_user_id else None,
        updated_by_user_name=(doc.updated_by_user.name or doc.updated_by_user.email) if doc.updated_by_user else None,
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    org_id: UUID,
    doc_id: UUID,
    current_user: RequireContributor,
    db: DbSession,
) -> None:
    """
    Delete a document.

    Args:
        org_id: Organization UUID
        doc_id: Document UUID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If document not found
    """
    doc_repo = DocumentRepository(db)

    # Audit log (before delete)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.DELETE,
        "document",
        doc_id,
        actor=current_user,
        organization_id=org_id,
    )

    deleted = await doc_repo.delete_by_id_and_org(doc_id, org_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Remove from search index (async, non-blocking on failure)
    await remove_entity_from_search(db, "document", doc_id)

    logger.info(
        "Document deleted",
        extra={
            "doc_id": str(doc_id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )


@router.patch("/batch", response_model=BatchToggleResponse)
async def batch_toggle_documents(
    org_id: UUID,
    request: BatchToggleRequest,
    current_user: RequireContributor,
    db: DbSession,
) -> BatchToggleResponse:
    """
    Batch toggle documents enabled/disabled status.

    Args:
        org_id: Organization UUID
        request: Batch toggle request with IDs and new is_enabled value
        current_user: Current authenticated user
        db: Database session

    Returns:
        Number of documents updated
    """
    # Convert string IDs to UUIDs
    doc_ids = [UUID(id_str) for id_str in request.ids]

    # Batch update
    result = await db.execute(
        update(Document)
        .where(Document.id.in_(doc_ids))
        .where(Document.organization_id == org_id)
        .values(is_enabled=request.is_enabled)
    )
    await db.commit()

    logger.info(
        f"Batch toggle documents: {result.rowcount} docs set to is_enabled={request.is_enabled}",
        extra={
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
            "updated_count": result.rowcount,
        },
    )

    # Update search index for each affected document
    # The worker will index if enabled, remove from index if disabled
    for doc_id in doc_ids:
        await index_entity_for_search(db, "document", doc_id, org_id)

    return BatchToggleResponse(updated_count=result.rowcount)


@router.patch("/batch/paths", response_model=BatchPathUpdateResponse)
async def batch_update_paths(
    org_id: UUID,
    request: BatchPathUpdateRequest,
    current_user: RequireContributor,
    db: DbSession,
) -> BatchPathUpdateResponse:
    """
    Batch update document paths for section rename/merge.

    When renaming a section/folder, this endpoint updates all documents
    under the old path to use the new path. If merge_if_exists is False
    and there would be conflicts (documents with same name at the new path),
    the operation is rejected and conflicts are returned.

    Args:
        org_id: Organization UUID
        request: Batch path update request with old/new prefixes
        current_user: Current authenticated user (requires Contributor role)
        db: Database session

    Returns:
        Number of documents updated and any conflicts found
    """
    # Validate that prefixes are different
    if request.old_path_prefix == request.new_path_prefix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old and new path prefixes must be different",
        )

    doc_repo = DocumentRepository(db)

    # Check for conflicts if not merging
    if not request.merge_if_exists:
        conflicts = await doc_repo.check_path_conflicts(
            org_id,
            request.old_path_prefix,
            request.new_path_prefix,
        )
        if conflicts:
            return BatchPathUpdateResponse(
                updated_count=0,
                conflicts=conflicts,
            )

    # Perform the batch update
    updated_count = await doc_repo.batch_update_paths(
        org_id,
        request.old_path_prefix,
        request.new_path_prefix,
    )
    await db.commit()

    logger.info(
        f"Batch path update: {updated_count} docs moved from '{request.old_path_prefix}' to '{request.new_path_prefix}'",
        extra={
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
            "old_prefix": request.old_path_prefix,
            "new_prefix": request.new_path_prefix,
            "updated_count": updated_count,
        },
    )

    return BatchPathUpdateResponse(updated_count=updated_count)
