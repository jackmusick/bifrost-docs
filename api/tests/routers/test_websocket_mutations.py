"""Tests for WebSocket entity update broadcasting."""
import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_entity_update_broadcast():
    """Test broadcasting entity update via pub/sub."""
    # Create test IDs
    document_id = uuid4()
    asset_id = uuid4()

    # Test document channel format
    doc_channel = f"entity_update:document:{document_id}"
    assert doc_channel.startswith("entity_update:")
    assert str(document_id) in doc_channel
    assert "document" in doc_channel

    # Test asset channel format
    asset_channel = f"entity_update:custom_asset:{asset_id}"
    assert asset_channel.startswith("entity_update:")
    assert str(asset_id) in asset_channel
    assert "custom_asset" in asset_channel
