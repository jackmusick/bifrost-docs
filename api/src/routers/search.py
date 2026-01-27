"""
Search Router

Provides hybrid search endpoint across all entity types.
Supports semantic search (with OpenAI), text search (without OpenAI),
and hybrid mode (combines both when OpenAI is available).

Also provides AI-powered search using RAG (Retrieval Augmented Generation).
Streaming is handled via WebSocket (client subscribes to search:{request_id} channel).
"""

import asyncio
import logging
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import select

from src.core.auth import CurrentActiveUser
from src.core.database import DbSession, get_db_context
from src.core.pubsub import (
    publish_entity_update,
    publish_search_citations,
    publish_search_delta,
    publish_search_done,
    publish_search_error,
)
from src.models.contracts.chat import ChatRequest, ChatStartResponse
from src.models.contracts.mutations import (
    ApplyMutationRequest,
    ApplyMutationResponse,
    AssetMutation,
    DocumentMutation,
)
from src.models.contracts.search import (
    AISearchRequest,
    AISearchStartResponse,
    SearchResponse,
)
from src.models.enums import UserRole
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.document import Document
from src.repositories.custom_asset import CustomAssetRepository
from src.repositories.document import DocumentRepository
from src.repositories.organization import OrganizationRepository
from src.services.ai_chat import get_ai_chat_service, get_conversational_chat_service
from src.services.embeddings import get_embeddings_service
from src.services.llm.factory import get_completions_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    current_user: CurrentActiveUser,
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    org_id: UUID | None = Query(None, description="Filter to specific organization"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    mode: Literal["auto", "text", "semantic", "hybrid"] = Query(
        "auto",
        description="Search mode: 'auto' (default, picks best available), "
        "'text' (ILIKE only), 'semantic' (embeddings only, requires OpenAI), "
        "'hybrid' (combines both when available)",
    ),
    show_disabled: bool = Query(False, description="Include disabled items in search results"),
) -> SearchResponse:
    """
    Search across all entities.

    Searches passwords, configurations, locations, documents, and custom assets.
    Results are ordered by relevance.

    Search modes:
    - auto: Uses hybrid if OpenAI is configured, otherwise text search
    - text: Uses PostgreSQL ILIKE matching only (no AI required)
    - semantic: Uses OpenAI embeddings for similarity search (requires OpenAI)
    - hybrid: Combines semantic and text search, dedupes and ranks results

    Args:
        q: Search query text
        org_id: Optional organization ID filter. If not provided, searches all
                organizations the user belongs to.
        limit: Maximum number of results (default 20, max 100)
        mode: Search mode to use
        show_disabled: Include disabled items in search results (default: False)

    Returns:
        SearchResponse with query and ranked results

    Raises:
        HTTPException 400: If semantic mode requested but OpenAI not configured
        HTTPException 403: If user doesn't have access to specified org
    """
    embeddings_service = get_embeddings_service(db)

    # Validate mode requirements
    if mode == "semantic" and not await embeddings_service.check_openai_available():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Semantic search requires OpenAI API key to be configured",
        )

    # Get organizations to search
    org_repo = OrganizationRepository(db)

    if org_id:
        # In the new model, all users can see all organizations
        # Just verify the organization exists
        org = await org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        org_ids = [org_id]
    else:
        # Get all organizations (all users can see all orgs in new model)
        # For global search, always filter out disabled organizations
        orgs = await org_repo.get_all()
        org_ids = [org.id for org in orgs if org.is_enabled]

    if not org_ids:
        return SearchResponse(query=q, results=[])

    # Determine effective search mode
    effective_mode = mode
    if mode == "auto":
        # Auto mode: use hybrid if OpenAI available, otherwise text
        openai_available = await embeddings_service.check_openai_available()
        effective_mode = "hybrid" if openai_available else "text"

    try:
        match effective_mode:
            case "text":
                results = await embeddings_service.text_search(db, q, org_ids, limit=limit, show_disabled=show_disabled)
            case "semantic":
                results = await embeddings_service.search(db, q, org_ids, limit=limit, show_disabled=show_disabled)
            case "hybrid":
                results = await embeddings_service.hybrid_search(db, q, org_ids, limit=limit, show_disabled=show_disabled)
            case _:
                # Should not happen due to Literal type, but handle gracefully
                results = await embeddings_service.hybrid_search(db, q, org_ids, limit=limit, show_disabled=show_disabled)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed due to an internal error",
        ) from e

    logger.info(
        f"Search completed: mode={effective_mode}, query='{q}', results={len(results)}",
        extra={"user_id": str(current_user.user_id), "org_ids": [str(o) for o in org_ids]},
    )

    return SearchResponse(query=q, results=results)


# =============================================================================
# AI Search Endpoint (RAG) - WebSocket Streaming
# =============================================================================


async def _perform_ai_search(
    request_id: str,
    query: str,
    org_ids: list[UUID],
) -> None:
    """
    Background task to perform AI search and stream results via WebSocket.

    Publishes messages to search:{request_id} channel:
    - {"type": "citations", "data": [...]}
    - {"type": "delta", "content": "..."}
    - {"type": "done"}
    - {"type": "error", "message": "..."}
    """
    # Small delay to allow client to establish WebSocket subscription
    # The client receives request_id and then connects to WebSocket
    await asyncio.sleep(0.5)

    try:
        async with get_db_context() as db:
            # Perform semantic search to get context
            embeddings_service = get_embeddings_service(db)

            try:
                search_results = await embeddings_service.search(
                    db, query, org_ids, limit=30
                )
            except Exception as e:
                logger.error(f"Search for AI context failed: {e}", exc_info=True)
                await publish_search_error(request_id, "Failed to retrieve search context")
                return

            # Build and publish citations
            citations = [
                {
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "organization_id": r.organization_id,
                    "name": r.name,
                }
                for r in search_results[:10]
            ]
            await publish_search_citations(request_id, citations)

            # Stream the AI response
            ai_chat_service = get_ai_chat_service(db)

            try:
                async for chunk in ai_chat_service.stream_response(query, search_results):
                    await publish_search_delta(request_id, chunk)
                    # Small delay to prevent overwhelming WebSocket
                    await asyncio.sleep(0.01)

                await publish_search_done(request_id)

            except ValueError as e:
                logger.warning(f"AI search failed: {e}")
                await publish_search_error(request_id, str(e))
            except Exception as e:
                logger.error(f"AI search stream error: {e}", exc_info=True)
                error_msg = str(e) if str(e) else "An error occurred while generating the response"
                await publish_search_error(request_id, error_msg)

    except Exception as e:
        logger.error(f"AI search background task failed: {e}", exc_info=True)
        await publish_search_error(request_id, "AI search failed unexpectedly")


@router.post("/ai", response_model=AISearchStartResponse)
async def ai_search(
    request: AISearchRequest,
    current_user: CurrentActiveUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> AISearchStartResponse:
    """
    AI-powered search using Retrieval Augmented Generation (RAG).

    Returns a request_id immediately. Client should subscribe to the
    search:{request_id} WebSocket channel to receive streaming results.

    WebSocket Message Format:
    - {"type": "citations", "data": [...]}  - Citations at start
    - {"type": "delta", "content": "..."}   - Response text chunks
    - {"type": "done"}                       - Stream complete
    - {"type": "error", "message": "..."}   - Error occurred

    Args:
        request: AISearchRequest with query and optional org_id

    Returns:
        AISearchStartResponse with request_id to subscribe to

    Raises:
        HTTPException 400: If OpenAI is not configured
        HTTPException 403: If user doesn't have access to specified org
    """
    # Check if completions LLM is configured
    completions_config = await get_completions_config(db)

    if not completions_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI search is not available - LLM API key not configured",
        )

    # Get organizations to search
    org_repo = OrganizationRepository(db)

    if request.org_id:
        # In the new model, all users can see all organizations
        # Just verify the organization exists
        org = await org_repo.get_by_id(request.org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        org_ids = [request.org_id]
    else:
        # Get all organizations (all users can see all orgs in new model)
        orgs = await org_repo.get_all()
        org_ids = [org.id for org in orgs]

    # Generate unique request ID
    request_id = str(uuid4())

    if not org_ids:
        # Still start background task to send empty response
        background_tasks.add_task(
            _send_empty_ai_response, request_id
        )
    else:
        # Start background task to perform AI search
        background_tasks.add_task(
            _perform_ai_search, request_id, request.query, org_ids
        )

    query_preview = request.query[:50] + "..." if len(request.query) > 50 else request.query
    logger.info(
        f"AI search started: request_id={request_id}, query='{query_preview}'",
        extra={"user_id": str(current_user.user_id)},
    )

    return AISearchStartResponse(request_id=request_id)


async def _send_empty_ai_response(request_id: str) -> None:
    """Send empty response when user has no organizations."""
    # Small delay to allow client to establish WebSocket subscription
    await asyncio.sleep(0.5)
    await publish_search_citations(request_id, [])
    await publish_search_delta(
        request_id,
        "No organizations found. Please join an organization to use AI search.",
    )
    await publish_search_done(request_id)


# =============================================================================
# Chat Endpoint (Conversational RAG) - WebSocket Streaming
# =============================================================================


async def _perform_chat(
    request_id: str,
    message: str,
    org_ids: list[UUID],
    history: list[dict[str, str]],
    current_entity_id: UUID | None = None,
    current_entity_type: str | None = None,
) -> None:
    """
    Background task to perform conversational chat and stream results via WebSocket.

    Publishes messages to search:{request_id} channel:
    - {"type": "citations", "data": [...]}
    - {"type": "delta", "content": "..."}
    - {"type": "done"}
    - {"type": "error", "message": "..."}
    """
    # Small delay to allow client to establish WebSocket subscription
    await asyncio.sleep(0.5)

    try:
        async with get_db_context() as db:
            # Perform hybrid search to get context (combines semantic + text matching)
            # Always search, even when viewing a document - user may ask about related content
            embeddings_service = get_embeddings_service(db)

            try:
                search_results = await embeddings_service.hybrid_search(
                    db, message, org_ids, limit=10
                )
            except Exception as e:
                logger.error(f"Search for chat context failed: {e}", exc_info=True)
                search_results = []

            # Fetch current entity details if provided and add to search results FIRST
            # (so it appears in citations)
            current_entity_context = None
            if current_entity_id and current_entity_type:
                try:
                    if current_entity_type == "document":
                        from sqlalchemy.orm import selectinload

                        # Eager load organization to avoid lazy loading issues
                        stmt = select(Document).where(Document.id == current_entity_id).options(selectinload(Document.organization))
                        result = await db.execute(stmt)
                        entity = result.scalar_one_or_none()

                        if entity:
                            current_entity_context = {
                                "type": "document",
                                "id": str(entity.id),
                                "name": entity.name,
                                "organization_id": str(entity.organization_id),
                            }

                            # Add current document to search results
                            from src.models.contracts.search import SearchResult
                            current_doc_result = SearchResult(
                                entity_type="document",
                                entity_id=str(entity.id),
                                organization_id=str(entity.organization_id),
                                organization_name=entity.organization.name if entity.organization else "Unknown",
                                name=entity.name,
                                snippet=entity.content or "",  # Full document content
                                score=1.0,  # Highest score since it's the current document
                                is_enabled=entity.is_enabled,
                            )

                            # Remove current document from search results if it's already there
                            search_results = [
                                r for r in search_results
                                if not (r.entity_type == "document" and r.entity_id == str(entity.id))
                            ]
                            # Prepend with full content
                            search_results = [current_doc_result] + search_results

                    elif current_entity_type == "custom_asset":
                        from sqlalchemy.orm import selectinload

                        # Eager load organization to avoid lazy loading issues
                        stmt = select(CustomAsset).where(CustomAsset.id == current_entity_id).options(selectinload(CustomAsset.organization))
                        result = await db.execute(stmt)
                        entity = result.scalar_one_or_none()

                        if entity:
                            current_entity_context = {
                                "type": "custom_asset",
                                "id": str(entity.id),
                                "name": entity.name,
                                "organization_id": str(entity.organization_id),
                            }

                            # Add current asset to search results
                            from src.models.contracts.search import SearchResult
                            # Build snippet from custom fields
                            field_texts = [f"{k}: {v}" for k, v in (entity.fields or {}).items()]
                            snippet = "\n".join(field_texts) if field_texts else entity.name

                            current_asset_result = SearchResult(
                                entity_type="custom_asset",
                                entity_id=str(entity.id),
                                organization_id=str(entity.organization_id),
                                organization_name=entity.organization.name if entity.organization else "Unknown",
                                name=entity.name,
                                snippet=snippet,
                                score=1.0,
                                is_enabled=entity.is_enabled,
                            )

                            # Remove current asset from search results if it's already there
                            search_results = [
                                r for r in search_results
                                if not (r.entity_type == "custom_asset" and r.entity_id == str(entity.id))
                            ]
                            # Prepend with full content
                            search_results = [current_asset_result] + search_results

                except Exception as e:
                    logger.warning(f"Failed to fetch current entity context: {e}")

            # Now build and publish citations (with current entity prepended if present)
            citations = [
                {
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "organization_id": r.organization_id,
                    "name": r.name,
                }
                for r in search_results[:10]
            ]
            await publish_search_citations(request_id, citations)

            # Stream the chat response
            chat_service = get_conversational_chat_service(db)

            try:
                async for chunk in chat_service.stream_response(
                    message, search_results, history, current_entity=current_entity_context
                ):
                    # Handle both string content and dict tool calls
                    if isinstance(chunk, str):
                        await publish_search_delta(request_id, chunk)
                    elif isinstance(chunk, dict) and chunk.get("type") == "mutation_pending":
                        # Send pending state for immediate UI feedback
                        from src.core.pubsub import publish_mutation_pending
                        await publish_mutation_pending(
                            request_id,
                            tool_call_id=chunk.get("tool_call_id", "")
                        )
                    elif isinstance(chunk, dict) and chunk.get("type") == "tool_call":
                        # Parse tool call and convert to mutation_preview format
                        from src.core.pubsub import publish_mutation_error, publish_mutation_preview
                        from src.services.ai_chat import parse_mutation_tool_call
                        from src.services.llm.base import ToolCall

                        try:
                            tool_call_data = chunk["tool_call"]
                            tool_call = ToolCall(
                                id=tool_call_data["id"],
                                name=tool_call_data["name"],
                                arguments=tool_call_data["arguments"]
                            )
                            mutation_preview = parse_mutation_tool_call(tool_call)

                            # Build preview data
                            preview_data = {
                                "tool_call_id": tool_call_data["id"],
                                "entity_type": mutation_preview.entity_type,
                                "entity_id": str(mutation_preview.entity_id),
                                "organization_id": str(mutation_preview.organization_id),
                                "mutation": {
                                    "summary": mutation_preview.mutation.summary,
                                }
                            }

                            # Add content or field_updates based on type
                            if isinstance(mutation_preview.mutation, DocumentMutation):
                                preview_data["mutation"]["content"] = mutation_preview.mutation.content
                            elif isinstance(mutation_preview.mutation, AssetMutation):
                                preview_data["mutation"]["field_updates"] = mutation_preview.mutation.field_updates

                            await publish_mutation_preview(request_id, preview_data)
                        except Exception as e:
                            logger.error(f"Failed to parse tool call: {e}", exc_info=True)
                            # Send user-friendly error instead of raw JSON
                            await publish_mutation_error(
                                request_id,
                                "Unable to preview this action"
                            )
                    # Small delay to prevent overwhelming WebSocket
                    await asyncio.sleep(0.01)

                await publish_search_done(request_id)

            except ValueError as e:
                logger.warning(f"Chat failed: {e}")
                await publish_search_error(request_id, str(e))
            except Exception as e:
                logger.error(f"Chat stream error: {e}", exc_info=True)
                error_msg = str(e) if str(e) else "An error occurred while generating the response"
                await publish_search_error(request_id, error_msg)

    except Exception as e:
        logger.error(f"Chat background task failed: {e}", exc_info=True)
        await publish_search_error(request_id, "Chat failed unexpectedly")


@router.post("/chat", response_model=ChatStartResponse)
async def chat(
    request: ChatRequest,
    current_user: CurrentActiveUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ChatStartResponse:
    """
    Conversational chat using Retrieval Augmented Generation (RAG).

    Returns a request_id and conversation_id immediately. Client should subscribe
    to the search:{request_id} WebSocket channel to receive streaming results.

    WebSocket Message Format:
    - {"type": "citations", "data": [...]}  - Citations at start
    - {"type": "delta", "content": "..."}   - Response text chunks
    - {"type": "done"}                       - Stream complete
    - {"type": "error", "message": "..."}   - Error occurred

    Args:
        request: ChatRequest with message, optional conversation_id, history, and org_id

    Returns:
        ChatStartResponse with request_id and conversation_id

    Raises:
        HTTPException 400: If LLM is not configured
        HTTPException 404: If specified org not found
    """
    # Check if completions LLM is configured
    completions_config = await get_completions_config(db)

    if not completions_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat is not available - LLM API key not configured",
        )

    # Get organizations to search
    org_repo = OrganizationRepository(db)

    if request.org_id:
        org = await org_repo.get_by_id(request.org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        org_ids = [request.org_id]
    else:
        orgs = await org_repo.get_all()
        org_ids = [org.id for org in orgs]

    # Generate unique request ID and conversation ID
    request_id = str(uuid4())
    conversation_id = request.conversation_id or str(uuid4())

    # Convert history to dict format for the service
    history = [{"role": msg.role, "content": msg.content} for msg in request.history]

    if not org_ids:
        # Still start background task to send empty response
        background_tasks.add_task(_send_empty_chat_response, request_id)
    else:
        # Start background task to perform chat
        background_tasks.add_task(
            _perform_chat,
            request_id,
            request.message,
            org_ids,
            history,
            request.current_entity_id,
            request.current_entity_type,
        )

    message_preview = request.message[:50] + "..." if len(request.message) > 50 else request.message
    logger.info(
        f"Chat started: request_id={request_id}, conversation_id={conversation_id}, message='{message_preview}'",
        extra={"user_id": str(current_user.user_id)},
    )

    return ChatStartResponse(request_id=request_id, conversation_id=conversation_id)


async def _send_empty_chat_response(request_id: str) -> None:
    """Send empty response when user has no organizations."""
    await asyncio.sleep(0.5)
    await publish_search_citations(request_id, [])
    await publish_search_delta(
        request_id,
        "No organizations found. Please join an organization to use chat.",
    )
    await publish_search_done(request_id)


# =============================================================================
# Mutation Application Endpoint
# =============================================================================


@router.post("/chat/apply", response_model=ApplyMutationResponse)
async def apply_mutation(
    request: ApplyMutationRequest,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> ApplyMutationResponse:
    """
    Apply an AI-generated mutation after user review.

    Requires Contributor role or higher.

    Args:
        request: ApplyMutationRequest with mutation details

    Returns:
        ApplyMutationResponse with success status and entity link

    Raises:
        HTTPException 403: If user doesn't have permission to edit data
        HTTPException 404: If entity not found
        HTTPException 400: If invalid mutation type for entity
    """
    # Check user has permission to edit data
    if not UserRole.can_edit_data(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify entities",
        )

    logger.info(
        f"Apply mutation request: entity_type={request.entity_type}, entity_id={request.entity_id}, org_id={request.organization_id}",
        extra={"user_id": str(current_user.user_id)},
    )

    # Verify organization exists
    org_repo = OrganizationRepository(db)
    org = await org_repo.get_by_id(request.organization_id)
    if not org:
        logger.warning(
            f"Apply mutation failed: Organization not found (org_id={request.organization_id})",
            extra={"user_id": str(current_user.user_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Apply mutation based on entity type
    if request.entity_type == "document":
        if not isinstance(request.mutation, DocumentMutation):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mutation type for document",
            )

        doc_repo = DocumentRepository(db)
        document = await doc_repo.get_by_id(request.entity_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        if document.organization_id != request.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # Update document
        document.content = request.mutation.content
        document.updated_by_user_id = current_user.user_id
        await db.commit()
        await db.refresh(document)

        # Broadcast entity update
        await publish_entity_update(
            entity_type="document",
            entity_id=document.id,
            organization_id=document.organization_id,
            updated_by=current_user.user_id,
        )

        link = f"entity://documents/{request.organization_id}/{request.entity_id}"

    elif request.entity_type == "custom_asset":
        if not isinstance(request.mutation, AssetMutation):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mutation type for custom asset",
            )

        asset_repo = CustomAssetRepository(db)
        asset = await asset_repo.get_by_id(request.entity_id)

        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom asset not found",
            )

        if asset.organization_id != request.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom asset not found",
            )

        # Update fields
        if not asset.values:
            asset.values = {}
        asset.values.update(request.mutation.field_updates)
        asset.updated_by_user_id = current_user.user_id
        await db.commit()
        await db.refresh(asset)

        # Broadcast entity update
        await publish_entity_update(
            entity_type="custom_asset",
            entity_id=asset.id,
            organization_id=asset.organization_id,
            updated_by=current_user.user_id,
        )

        link = f"entity://custom-assets/{request.organization_id}/{request.entity_id}"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity type",
        )

    logger.info(
        f"Mutation applied: entity_type={request.entity_type}, entity_id={request.entity_id}",
        extra={"user_id": str(current_user.user_id), "org_id": str(request.organization_id)},
    )

    return ApplyMutationResponse(
        success=True,
        entity_id=request.entity_id,
        link=link,
        error=None,
    )
