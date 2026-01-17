"""Tests for asset mutation service."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.asset_mutations import AssetMutationService, extract_field_updates


def test_extract_field_updates_simple():
    """Test extracting field updates from instruction."""
    current_fields = {
        "ip_address": "10.0.0.1",
        "location": "DC1",
        "status": "active"
    }
    instruction = "change IP to 10.0.0.5"

    updates = extract_field_updates(current_fields, instruction)
    assert "ip_address" in updates
    assert updates["ip_address"] == "10.0.0.5"


def test_extract_field_updates_multiple():
    """Test extracting multiple field updates."""
    current_fields = {
        "ip_address": "10.0.0.1",
        "location": "DC1"
    }
    instruction = "update IP to 10.0.0.10 and location to DC2"

    updates = extract_field_updates(current_fields, instruction)
    assert len(updates) >= 2
    assert "ip_address" in updates or "location" in updates


@pytest.mark.asyncio
async def test_generate_field_updates():
    """Test generating field updates via LLM."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = '{"ip_address": "10.0.0.5", "location": "DC2"}'
    mock_client.complete.return_value = mock_response

    service = AssetMutationService(mock_client)

    current_fields = {
        "ip_address": "10.0.0.1",
        "location": "DC1",
        "status": "active"
    }
    instruction = "change IP to 10.0.0.5 and location to DC2"

    updates, summary = await service.generate_field_updates(
        asset_type="Server",
        current_fields=current_fields,
        user_instruction=instruction
    )

    assert isinstance(updates, dict)
    assert len(summary) > 0
    assert mock_client.complete.called


@pytest.mark.asyncio
async def test_generate_field_updates_llm_error():
    """Test handling of LLM API errors."""
    mock_client = AsyncMock()
    mock_client.complete.side_effect = Exception("API Error")

    service = AssetMutationService(mock_client)

    # Should propagate exception
    with pytest.raises(Exception):
        await service.generate_field_updates(
            asset_type="Server",
            current_fields={"ip": "10.0.0.1"},
            user_instruction="change IP to 10.0.0.5"
        )


@pytest.mark.asyncio
async def test_generate_field_updates_invalid_json_uses_fallback():
    """Test that service uses regex fallback when LLM returns invalid JSON."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "This is not JSON at all!"
    mock_client.complete.return_value = mock_response

    service = AssetMutationService(mock_client)

    current_fields = {"ip_address": "10.0.0.1", "location": "DC1"}
    instruction = "change IP to 10.0.0.5"

    updates, summary = await service.generate_field_updates(
        asset_type="Server",
        current_fields=current_fields,
        user_instruction=instruction
    )

    # Should use regex fallback
    assert "ip_address" in updates
    assert updates["ip_address"] == "10.0.0.5"
    assert "field(s)" in summary.lower()


@pytest.mark.asyncio
async def test_generate_field_updates_filters_nonexistent_fields():
    """Test that LLM responses are filtered to existing fields only."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    # LLM returns fields that don't exist
    mock_response.content = '{"ip_address": "10.0.0.5", "fake_field": "value", "another_fake": "test"}'
    mock_client.complete.return_value = mock_response

    service = AssetMutationService(mock_client)

    current_fields = {"ip_address": "10.0.0.1", "location": "DC1"}

    updates, summary = await service.generate_field_updates(
        asset_type="Server",
        current_fields=current_fields,
        user_instruction="update IP and add some fake fields"
    )

    # Should only include ip_address, not fake fields
    assert "ip_address" in updates
    assert "fake_field" not in updates
    assert "another_fake" not in updates
    assert len(updates) == 1


@pytest.mark.asyncio
async def test_generate_field_updates_empty_response():
    """Test handling of empty LLM response."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = None
    mock_client.complete.return_value = mock_response

    service = AssetMutationService(mock_client)

    current_fields = {"ip": "10.0.0.1"}
    instruction = "change IP to 10.0.0.5"

    updates, summary = await service.generate_field_updates(
        asset_type="Server",
        current_fields=current_fields,
        user_instruction=instruction
    )

    # Should use fallback and extract using regex
    # May or may not find the field depending on regex patterns
    assert isinstance(updates, dict)
    assert isinstance(summary, str)
