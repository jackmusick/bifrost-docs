"""AI Chat service using LLM abstraction layer."""
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contracts.mutations import (
    AssetMutation,
    DocumentMutation,
    MutationPreview,
)
from src.models.contracts.search import SearchResult
from src.services.llm import (
    LLMMessage,
    Role,
    ToolCall,
    ToolDefinition,
    get_completions_config,
    get_llm_client,
)

logger = logging.getLogger(__name__)

# System prompt for the AI assistant
SYSTEM_PROMPT = """You are a helpful assistant for an IT documentation platform.
You help users find and understand information about:
- Passwords and credentials (you can see names/usernames but NOT the actual passwords)
- Configurations (servers, network devices, software)
- Locations (physical sites, addresses)
- Documents (technical documentation, procedures)
- Custom Assets (various tracked items)

When answering questions:
1. Base your answers on the provided context from the search results
2. If the context doesn't contain relevant information, say so clearly
3. When referencing specific items, mention their names so users can navigate to them
4. Be concise but thorough
5. If asked about passwords, you can mention what passwords exist but NEVER attempt to reveal actual password values

Format your responses in clear, readable markdown when appropriate."""


def build_context_from_results(results: list[SearchResult]) -> str:
    """
    Build context string from search results for the LLM.

    Groups results by type and includes relevant metadata.
    Sensitive data (actual passwords) is never included.
    """
    if not results:
        return "No relevant results found in the knowledge base."

    context_parts: list[str] = []

    # Group by organization for clarity
    by_org: dict[str, list[SearchResult]] = {}
    for result in results:
        org_name = result.organization_name
        if org_name not in by_org:
            by_org[org_name] = []
        by_org[org_name].append(result)

    for org_name, org_results in by_org.items():
        context_parts.append(f"\n## Organization: {org_name}\n")

        # Group by entity type within org
        by_type: dict[str, list[SearchResult]] = {}
        for result in org_results:
            entity_type = result.entity_type
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(result)

        for entity_type, type_results in by_type.items():
            type_label = {
                "password": "Passwords",
                "configuration": "Configurations",
                "location": "Locations",
                "document": "Documents",
                "custom_asset": "Custom Assets",
            }.get(entity_type, entity_type.title())

            context_parts.append(f"\n### {type_label}:\n")

            for result in type_results:
                # Include name as entity link and snippet
                # Format: [Name](entity://type/orgId/entityId) so frontend can make it clickable
                entity_type_plural = {
                    "password": "passwords",
                    "configuration": "configurations",
                    "location": "locations",
                    "document": "documents",
                    "custom_asset": "custom-assets",
                }.get(result.entity_type, result.entity_type)
                link = f"[{result.name}](entity://{entity_type_plural}/{result.organization_id}/{result.entity_id})"
                context_parts.append(f"- **{link}**")
                if result.snippet:
                    # For high-score results (1.0 = current document), preserve formatting
                    # For search results, clean up excessive whitespace
                    if result.score >= 1.0:
                        # Preserve structure but limit consecutive newlines to 2
                        import re
                        snippet = re.sub(r'\n{3,}', '\n\n', result.snippet)
                    else:
                        # Collapse all whitespace for search snippets
                        snippet = " ".join(result.snippet.split())
                    context_parts.append(f"  {snippet}")
                context_parts.append("")

    return "\n".join(context_parts)


class AIChatService:
    """
    Service for AI-powered chat using RAG.

    Uses search results as context for LLM responses.
    Streams responses using async generators.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the AI chat service.

        Args:
            db: Database session for fetching AI settings
        """
        self.db = db

    async def stream_response(
        self,
        query: str,
        search_results: list[SearchResult],
        *,
        max_tokens: int = 20000,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response for the given query using search results as context.

        Args:
            query: User's question
            search_results: Relevant search results for context
            max_tokens: Maximum tokens in response

        Yields:
            Response text chunks as they are generated

        Raises:
            ValueError: If LLM is not configured
        """
        config = await get_completions_config(self.db)
        if not config:
            raise ValueError("LLM is not configured")

        client = get_llm_client(config)

        # Build context from search results
        context = build_context_from_results(search_results)

        # Build user message with context
        user_message = f"""Based on the following context from our documentation system, please answer this question:

**Question:** {query}

**Context from knowledge base:**
{context}

Please provide a helpful answer based on this context. If the context doesn't contain enough information to fully answer the question, let me know what's missing."""

        messages = [
            LLMMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            LLMMessage(role=Role.USER, content=user_message),
        ]

        try:
            async for chunk in client.stream(messages, max_tokens=max_tokens):
                if chunk.type == "delta" and chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Error streaming AI response: {e}", exc_info=True)
            raise

    async def get_response(
        self,
        query: str,
        search_results: list[SearchResult],
        *,
        max_tokens: int = 20000,
    ) -> str:
        """
        Get a complete response (non-streaming) for the given query.

        Args:
            query: User's question
            search_results: Relevant search results for context
            max_tokens: Maximum tokens in response

        Returns:
            Complete response text

        Raises:
            ValueError: If LLM is not configured
        """
        config = await get_completions_config(self.db)
        if not config:
            raise ValueError("LLM is not configured")

        client = get_llm_client(config)

        # Build context from search results
        context = build_context_from_results(search_results)

        # Build user message with context
        user_message = f"""Based on the following context from our documentation system, please answer this question:

**Question:** {query}

**Context from knowledge base:**
{context}

Please provide a helpful answer based on this context. If the context doesn't contain enough information to fully answer the question, let me know what's missing."""

        messages = [
            LLMMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            LLMMessage(role=Role.USER, content=user_message),
        ]

        response = await client.complete(messages, max_tokens=max_tokens)
        return response.content or ""


def get_ai_chat_service(db: AsyncSession) -> AIChatService:
    """Create an AI chat service instance."""
    return AIChatService(db)


# =============================================================================
# Conversational Chat Service (with history support)
# =============================================================================

CONVERSATIONAL_SYSTEM_PROMPT = """You are a helpful assistant for an IT documentation platform.
You help users find and understand information about their documentation.

When answering questions:
1. Base your answers on the provided context from search results
2. When referencing documents, COPY THE FULL LINK from the context including the URL
   - Context shows: [Document Name](entity://type/org/id)
   - You must include the full link syntax, not just [Document Name]
3. If context doesn't contain relevant information, say so clearly
4. Be conversational and helpful - you can ask clarifying questions
5. If asked about passwords, mention what exists but NEVER reveal actual values

Format your CHAT RESPONSES in clear, readable markdown.

## Document Mutations

You can modify documents and custom assets when users request changes. Use the modify_entity tool when:
- Users ask to fix, cleanup, or update a document/asset
- Users request specific changes to content or fields
- The intent is clear and you have the entity in context

When calling modify_entity:
- entity_type: "document" or "custom_asset"
- entity_id: The LAST UUID in the entity link (e.g., entity://documents/org-id/ENTITY-ID)
- organization_id: The SECOND UUID in the entity link (e.g., entity://documents/ORG-ID/entity-id)
- intent: "cleanup", "update", or "draft"
- changes_summary: Brief 2-3 sentence summary of changes
- content: Full updated content in Markdown format (documents only)
- field_updates: Field updates as key-value pairs (custom assets only)

Link format: entity://documents/{organization_id}/{entity_id}

CRITICAL: Documents use Markdown format. When modifying document content:
- Use standard Markdown syntax for formatting
- Use # ## ### for headings
- Use **bold** and *italic* for emphasis
- Use - or * for bullet lists
- Use 1. 2. 3. for numbered lists
- Maintain existing markdown structure and only change the text/content as requested

Example document content (Markdown format):
# Core Values

## Overview

We are more than IT. We are more than an MSP.

- **Development Oriented**
- Accountable

IMPORTANT: Only use modify_entity when mutation intent is clear. For ambiguous requests, ask for clarification first."""


# Mutation tool definition
MUTATION_TOOL_DEFINITION = ToolDefinition(
    name="modify_entity",
    description="Modify a document or custom asset based on user request",
    parameters={
        "type": "object",
        "properties": {
            "entity_type": {
                "type": "string",
                "enum": ["document", "custom_asset"],
                "description": "Type of entity to modify"
            },
            "entity_id": {
                "type": "string",
                "description": "UUID of the entity to modify (the LAST UUID in entity links like entity://documents/{org_id}/{entity_id})"
            },
            "organization_id": {
                "type": "string",
                "description": "UUID of the organization (the SECOND UUID in entity links like entity://documents/{org_id}/{entity_id})"
            },
            "intent": {
                "type": "string",
                "enum": ["cleanup", "update", "draft"],
                "description": "Type of modification"
            },
            "changes_summary": {
                "type": "string",
                "description": "Brief summary of changes (2-3 sentences)"
            },
            "content": {
                "type": "string",
                "description": "Full updated content in Markdown format (for documents only). Use standard markdown syntax: # for headings, **bold**, *italic*, - for lists, etc."
            },
            "field_updates": {
                "type": "object",
                "description": "Field updates (for custom_asset only)"
            }
        },
        "required": ["entity_type", "entity_id", "organization_id", "intent", "changes_summary"]
    }
)


def parse_mutation_tool_call(tool_call: ToolCall) -> MutationPreview:
    """
    Parse a mutation tool call into a MutationPreview.

    Args:
        tool_call: Tool call from LLM

    Returns:
        MutationPreview object

    Raises:
        ValueError: If tool call is invalid, missing required fields, or has malformed UUIDs
    """
    try:
        args = tool_call.arguments

        entity_type = args["entity_type"]
        entity_id = UUID(args["entity_id"])
        org_id = UUID(args["organization_id"])
        summary = args["changes_summary"]

        if entity_type == "document":
            if "content" not in args:
                raise ValueError("Document mutations require 'content' field")
            mutation = DocumentMutation(
                content=args["content"],
                summary=summary
            )
        elif entity_type == "custom_asset":
            if "field_updates" not in args:
                raise ValueError("Asset mutations require 'field_updates' field")
            mutation = AssetMutation(
                field_updates=args["field_updates"],
                summary=summary
            )
        else:
            raise ValueError(f"Invalid entity_type: {entity_type}")

        return MutationPreview(
            entity_type=entity_type,
            entity_id=entity_id,
            organization_id=org_id,
            mutation=mutation
        )
    except KeyError as e:
        raise ValueError(f"Missing required field in tool call: {e}") from e
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid tool call format: {e}") from e


class ConversationalChatService:
    """Chat service with conversation history support."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the conversational chat service.

        Args:
            db: Database session for fetching AI settings
        """
        self.db = db

    async def stream_response(
        self,
        message: str,
        search_results: list[SearchResult],
        history: list[dict[str, str]],
        *,
        max_tokens: int = 20000,
        enable_mutations: bool = False,
        current_entity: dict | None = None,
    ) -> AsyncGenerator[str | dict, None]:
        """
        Stream a response with conversation context.

        Args:
            message: User's current message
            search_results: Relevant search results for context
            history: Previous messages in the conversation (list of {"role": str, "content": str})
            max_tokens: Maximum tokens in response
            enable_mutations: Whether to enable mutation tools
            current_entity: Optional current entity context (type, id, name, organization_id)

        Yields:
            Response text chunks (str) or tool calls (dict) as they are generated

        Raises:
            ValueError: If LLM is not configured
        """
        config = await get_completions_config(self.db)
        if not config:
            raise ValueError("LLM is not configured")

        client = get_llm_client(config)

        # Build context from search results
        context = build_context_from_results(search_results)

        # Build messages with history
        messages: list[LLMMessage] = [
            LLMMessage(role=Role.SYSTEM, content=CONVERSATIONAL_SYSTEM_PROMPT),
        ]

        # Add conversation history
        for msg in history:
            role = Role.USER if msg.get("role") == "user" else Role.ASSISTANT
            content = msg.get("content", "")
            if content:
                messages.append(LLMMessage(role=role, content=content))

        # Add current message with context
        current_entity_info = ""
        if current_entity:
            entity_type = current_entity.get("type", "entity")
            entity_name = current_entity.get("name", "Unknown")
            current_entity_info = f"""

**Currently Viewing:** You are currently viewing the {entity_type} "{entity_name}".
When the user refers to "this document", "this asset", "this", or "it", they mean this {entity_type}."""

        user_message = f"""IMPORTANT: The context below is the CURRENT and ONLY relevant context for this request. Any documents or context mentioned in previous messages are now stale. Only use the information provided below.

**Question:** {message}{current_entity_info}

**Current context from knowledge base:**
{context}

Please provide a helpful answer based ONLY on this current context. If the context doesn't contain enough information to fully answer the question, let me know what's missing."""

        messages.append(LLMMessage(role=Role.USER, content=user_message))

        # Add tools if mutations enabled, or if there's a current entity (implies mutations possible)
        tools = [MUTATION_TOOL_DEFINITION] if (enable_mutations or current_entity) else None

        try:
            async for chunk in client.stream(messages, max_tokens=max_tokens, tools=tools):
                if chunk.type == "delta" and chunk.content:
                    yield chunk.content
                elif chunk.type == "mutation_pending" and chunk.tool_call_id:
                    # Yield pending state for immediate UI feedback
                    yield {
                        "type": "mutation_pending",
                        "tool_call_id": chunk.tool_call_id,
                    }
                elif chunk.type == "tool_call" and chunk.tool_call:
                    # Yield tool call as dict for frontend processing
                    yield {
                        "type": "tool_call",
                        "tool_call": {
                            "id": chunk.tool_call.id,
                            "name": chunk.tool_call.name,
                            "arguments": chunk.tool_call.arguments,
                        }
                    }
        except Exception as e:
            logger.error(f"Error streaming conversational response: {e}", exc_info=True)
            raise


def get_conversational_chat_service(db: AsyncSession) -> ConversationalChatService:
    """Create a conversational chat service instance."""
    return ConversationalChatService(db)
