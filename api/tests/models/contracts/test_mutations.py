"""Tests for mutation contracts."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.contracts.mutations import (
    ApplyMutationRequest,
    ApplyMutationResponse,
    DocumentMutation,
    AssetMutation,
    MutationPreview,
)


def test_document_mutation_valid():
    """Test valid document mutation."""
    mutation = DocumentMutation(
        content="# Updated content\n\nNew paragraph.",
        summary="Added introduction paragraph"
    )
    assert mutation.content == "# Updated content\n\nNew paragraph."
    assert mutation.summary == "Added introduction paragraph"


def test_asset_mutation_valid():
    """Test valid asset mutation."""
    mutation = AssetMutation(
        field_updates={"ip_address": "10.0.0.5", "location": "DC2"},
        summary="Updated IP and location"
    )
    assert mutation.field_updates == {"ip_address": "10.0.0.5", "location": "DC2"}
    assert mutation.summary == "Updated IP and location"


def test_mutation_preview_document():
    """Test mutation preview for document."""
    org_id = uuid4()
    entity_id = uuid4()

    preview = MutationPreview(
        entity_type="document",
        entity_id=entity_id,
        organization_id=org_id,
        mutation=DocumentMutation(
            content="# Test\n\nContent",
            summary="Test summary"
        )
    )

    assert preview.entity_type == "document"
    assert preview.entity_id == entity_id
    assert isinstance(preview.mutation, DocumentMutation)


def test_mutation_preview_asset():
    """Test mutation preview for asset."""
    org_id = uuid4()
    entity_id = uuid4()

    preview = MutationPreview(
        entity_type="custom_asset",
        entity_id=entity_id,
        organization_id=org_id,
        mutation=AssetMutation(
            field_updates={"field": "value"},
            summary="Updated field"
        )
    )

    assert preview.entity_type == "custom_asset"
    assert isinstance(preview.mutation, AssetMutation)


def test_apply_mutation_request_document():
    """Test apply mutation request for document."""
    org_id = uuid4()
    entity_id = uuid4()

    request = ApplyMutationRequest(
        conversation_id="conv-123",
        request_id="req-456",
        entity_type="document",
        entity_id=entity_id,
        organization_id=org_id,
        mutation=DocumentMutation(
            content="# New content",
            summary="Summary"
        )
    )

    assert request.entity_type == "document"
    assert isinstance(request.mutation, DocumentMutation)


def test_apply_mutation_response():
    """Test apply mutation response."""
    entity_id = uuid4()
    org_id = uuid4()

    response = ApplyMutationResponse(
        success=True,
        entity_id=entity_id,
        link=f"entity://documents/{org_id}/{entity_id}"
    )

    assert response.success is True
    assert response.entity_id == entity_id
    assert response.link.startswith("entity://")


def test_invalid_entity_type():
    """Test that invalid entity types are rejected."""
    org_id = uuid4()
    entity_id = uuid4()

    with pytest.raises(ValidationError):
        MutationPreview(
            entity_type="invalid_type",
            entity_id=entity_id,
            organization_id=org_id,
            mutation=DocumentMutation(content="test", summary="test")
        )


def test_document_mutation_summary_too_short():
    """Test that empty summary is rejected."""
    with pytest.raises(ValidationError):
        DocumentMutation(content="test", summary="")


def test_document_mutation_summary_too_long():
    """Test that summary over 500 chars is rejected."""
    with pytest.raises(ValidationError):
        DocumentMutation(content="test", summary="x" * 501)


def test_document_mutation_summary_at_boundary():
    """Test that summary at exactly 500 chars is accepted."""
    mutation = DocumentMutation(content="test", summary="x" * 500)
    assert len(mutation.summary) == 500


def test_asset_mutation_summary_too_short():
    """Test that empty summary is rejected."""
    with pytest.raises(ValidationError):
        AssetMutation(field_updates={"key": "value"}, summary="")


def test_asset_mutation_summary_too_long():
    """Test that summary over 500 chars is rejected."""
    with pytest.raises(ValidationError):
        AssetMutation(field_updates={"key": "value"}, summary="x" * 501)


def test_document_mutation_requires_content():
    """Test that content is required."""
    with pytest.raises(ValidationError):
        DocumentMutation(summary="test")


def test_document_mutation_requires_summary():
    """Test that summary is required."""
    with pytest.raises(ValidationError):
        DocumentMutation(content="test")


def test_asset_mutation_requires_field_updates():
    """Test that field_updates is required."""
    with pytest.raises(ValidationError):
        AssetMutation(summary="test")


def test_asset_mutation_requires_summary():
    """Test that summary is required."""
    with pytest.raises(ValidationError):
        AssetMutation(field_updates={"key": "value"})


def test_asset_mutation_empty_field_updates_rejected():
    """Test that empty field_updates is rejected."""
    with pytest.raises(ValidationError):
        AssetMutation(field_updates={}, summary="test")


def test_apply_mutation_response_failure():
    """Test apply mutation response with error."""
    entity_id = uuid4()
    org_id = uuid4()

    response = ApplyMutationResponse(
        success=False,
        entity_id=entity_id,
        link=f"entity://documents/{org_id}/{entity_id}",
        error="Permission denied"
    )

    assert response.success is False
    assert response.error == "Permission denied"
