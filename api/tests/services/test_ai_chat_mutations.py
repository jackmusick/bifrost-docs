"""Tests for AI chat mutation tools."""
import json
from uuid import UUID

import pytest

from src.services.ai_chat import (
    MUTATION_TOOL_DEFINITION,
    parse_mutation_tool_call,
)
from src.services.llm import ToolCall
from src.models.contracts.mutations import (
    MutationPreview,
    DocumentMutation,
    AssetMutation,
)


def test_mutation_tool_definition():
    """Test that mutation tool is properly defined."""
    assert MUTATION_TOOL_DEFINITION.name == "modify_entity"
    assert "document" in str(MUTATION_TOOL_DEFINITION.description)

    # Check required parameters
    params = MUTATION_TOOL_DEFINITION.parameters
    assert params["type"] == "object"

    props = params["properties"]
    assert "entity_type" in props
    assert "entity_id" in props
    assert "organization_id" in props
    assert "intent" in props
    assert "changes_summary" in props

    # Check entity_type enum
    assert set(props["entity_type"]["enum"]) == {"document", "custom_asset"}

    # Check required fields
    required = params["required"]
    assert "entity_type" in required
    assert "entity_id" in required
    assert "organization_id" in required
    assert "intent" in required
    assert "changes_summary" in required


def test_parse_mutation_tool_call_document():
    """Test parsing a document mutation tool call."""
    tool_call = ToolCall(
        id="call_123",
        name="modify_entity",
        arguments={
            "entity_type": "document",
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "organization_id": "660e8400-e29b-41d4-a716-446655440000",
            "intent": "cleanup",
            "changes_summary": "Fixed typos and improved formatting",
            "content": "# Updated Document\n\nNew content here."
        }
    )

    preview = parse_mutation_tool_call(tool_call)

    assert isinstance(preview, MutationPreview)
    assert preview.entity_type == "document"
    assert preview.entity_id == UUID("550e8400-e29b-41d4-a716-446655440000")
    assert preview.organization_id == UUID("660e8400-e29b-41d4-a716-446655440000")

    # Check mutation details
    mutation = preview.mutation
    assert isinstance(mutation, DocumentMutation)
    assert mutation.content == "# Updated Document\n\nNew content here."
    assert mutation.summary == "Fixed typos and improved formatting"


def test_parse_mutation_tool_call_asset():
    """Test parsing an asset mutation tool call."""
    tool_call = ToolCall(
        id="call_456",
        name="modify_entity",
        arguments={
            "entity_type": "custom_asset",
            "entity_id": "770e8400-e29b-41d4-a716-446655440000",
            "organization_id": "660e8400-e29b-41d4-a716-446655440000",
            "intent": "update",
            "changes_summary": "Updated server IP and added notes",
            "field_updates": {
                "ip_address": "192.168.1.100",
                "notes": "Primary web server"
            }
        }
    )

    preview = parse_mutation_tool_call(tool_call)

    assert isinstance(preview, MutationPreview)
    assert preview.entity_type == "custom_asset"
    assert preview.entity_id == UUID("770e8400-e29b-41d4-a716-446655440000")
    assert preview.organization_id == UUID("660e8400-e29b-41d4-a716-446655440000")

    # Check mutation details
    mutation = preview.mutation
    assert isinstance(mutation, AssetMutation)
    assert mutation.field_updates == {
        "ip_address": "192.168.1.100",
        "notes": "Primary web server"
    }
    assert mutation.summary == "Updated server IP and added notes"


def test_parse_mutation_tool_call_invalid_entity_type():
    """Test that invalid entity type raises ValueError."""
    tool_call = ToolCall(
        id="call_789",
        name="modify_entity",
        arguments={
            "entity_type": "invalid_type",
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "organization_id": "660e8400-e29b-41d4-a716-446655440000",
            "intent": "update",
            "changes_summary": "Some changes"
        }
    )

    with pytest.raises(ValueError, match="Invalid entity_type"):
        parse_mutation_tool_call(tool_call)


def test_parse_mutation_tool_call_missing_required_field():
    """Test that missing required fields raise ValueError."""
    tool_call = ToolCall(
        id="call_123",
        name="modify_entity",
        arguments={
            "entity_type": "document",
            # Missing entity_id, organization_id, changes_summary
        }
    )

    with pytest.raises(ValueError, match="Missing required field"):
        parse_mutation_tool_call(tool_call)


def test_parse_mutation_tool_call_invalid_uuid():
    """Test that invalid UUIDs raise ValueError."""
    tool_call = ToolCall(
        id="call_123",
        name="modify_entity",
        arguments={
            "entity_type": "document",
            "entity_id": "not-a-valid-uuid",
            "organization_id": "550e8400-e29b-41d4-a716-446655440000",
            "intent": "cleanup",
            "changes_summary": "Test",
            "content": "test"
        }
    )

    with pytest.raises(ValueError, match="Invalid"):
        parse_mutation_tool_call(tool_call)


def test_parse_mutation_tool_call_document_missing_content():
    """Test that document mutation without content raises ValueError."""
    tool_call = ToolCall(
        id="call_123",
        name="modify_entity",
        arguments={
            "entity_type": "document",
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "organization_id": "660e8400-e29b-41d4-a716-446655440000",
            "intent": "cleanup",
            "changes_summary": "Test"
            # Missing content field
        }
    )

    with pytest.raises(ValueError, match="content"):
        parse_mutation_tool_call(tool_call)


def test_parse_mutation_tool_call_asset_missing_field_updates():
    """Test that asset mutation without field_updates raises ValueError."""
    tool_call = ToolCall(
        id="call_123",
        name="modify_entity",
        arguments={
            "entity_type": "custom_asset",
            "entity_id": "550e8400-e29b-41d4-a716-446655440000",
            "organization_id": "660e8400-e29b-41d4-a716-446655440000",
            "intent": "update",
            "changes_summary": "Test"
            # Missing field_updates
        }
    )

    with pytest.raises(ValueError, match="field_updates"):
        parse_mutation_tool_call(tool_call)
