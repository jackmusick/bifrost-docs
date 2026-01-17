"""Tests for document mutation service."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.document_mutations import (
    DocumentMutationService,
    classify_document_type,
    apply_diataxis_structure,
)


def test_classify_document_type_tutorial():
    """Test classification of tutorial documents."""
    content = "# Getting Started\n\nIn this tutorial, you'll learn step-by-step how to..."
    title = "Getting Started Guide"
    instruction = "clean this up"

    doc_type = classify_document_type(content, title, instruction)
    assert doc_type == "tutorial"


def test_classify_document_type_howto():
    """Test classification of how-to documents."""
    content = "# How to Fix Login Issues\n\n1. Check your password\n2. Verify your email"
    title = "Login Troubleshooting"
    instruction = "fix formatting"

    doc_type = classify_document_type(content, title, instruction)
    assert doc_type == "how-to"


def test_classify_document_type_reference():
    """Test classification of reference documents."""
    content = "# API Reference\n\n## Endpoints\n\n`GET /api/users`"
    title = "API Documentation"
    instruction = "clean up"

    doc_type = classify_document_type(content, title, instruction)
    assert doc_type == "reference"


def test_classify_document_type_explanation():
    """Test classification of explanation documents."""
    content = "# Understanding Authentication\n\nAuthentication is the process..."
    title = "Auth Concepts"
    instruction = "improve this"

    doc_type = classify_document_type(content, title, instruction)
    assert doc_type == "explanation"


def test_apply_diataxis_structure_tutorial():
    """Test applying tutorial structure."""
    content = "Some messy content about learning basics"
    structured = apply_diataxis_structure("tutorial", content)

    # Should have tutorial-appropriate sections
    assert "## Learning Objectives" in structured or "## What You'll Learn" in structured
    assert len(structured) > len(content)


def test_apply_diataxis_structure_howto():
    """Test applying how-to structure."""
    content = "Steps to solve a problem"
    structured = apply_diataxis_structure("how-to", content)

    # Should have problem/solution oriented structure
    assert "## Prerequisites" in structured or "## Steps" in structured


@pytest.mark.asyncio
async def test_generate_cleaned_content():
    """Test generating cleaned document content."""
    # Mock LLM client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "# Clean Document\n\n## Overview\n\nNice clean content."
    mock_client.complete.return_value = mock_response

    service = DocumentMutationService(mock_client)

    original = "Messy document with bad formatting"
    title = "Test Doc"
    instruction = "clean this up"

    content, summary = await service.generate_cleaned_content(
        original_content=original,
        document_name=title,
        user_instruction=instruction
    )

    assert len(content) > 0
    assert len(summary) > 0
    assert mock_client.complete.called


@pytest.mark.asyncio
async def test_generate_cleaned_content_llm_error():
    """Test handling of LLM API errors."""
    mock_client = AsyncMock()
    mock_client.complete.side_effect = Exception("API Error")

    service = DocumentMutationService(mock_client)

    with pytest.raises(Exception):
        await service.generate_cleaned_content(
            original_content="content",
            document_name="Test",
            user_instruction="clean"
        )


@pytest.mark.asyncio
async def test_generate_cleaned_content_empty_response():
    """Test handling of empty LLM response."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = None
    mock_client.complete.return_value = mock_response

    service = DocumentMutationService(mock_client)

    with pytest.raises(ValueError, match="empty response"):
        await service.generate_cleaned_content(
            original_content="content",
            document_name="Test",
            user_instruction="clean"
        )


@pytest.mark.asyncio
async def test_generate_cleaned_content_empty_string_response():
    """Test handling of empty string LLM response."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = ""
    mock_client.complete.return_value = mock_response

    service = DocumentMutationService(mock_client)

    with pytest.raises(ValueError, match="empty response"):
        await service.generate_cleaned_content(
            original_content="content",
            document_name="Test",
            user_instruction="clean"
        )
