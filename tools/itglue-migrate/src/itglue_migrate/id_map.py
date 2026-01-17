"""ID mapping storage for IT Glue to BifrostDocs migration.

This module provides persistent storage for mapping IT Glue IDs to new UUIDs,
supporting migration resume and relationship tracking across entity types.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

# Supported entity types for migration
EntityType = Literal[
    "organization",
    "configuration",
    "document",
    "password",
    "location",
    "custom_asset",
    "custom_asset_type",
    "configuration_type",
]

VALID_ENTITY_TYPES: frozenset[str] = frozenset(
    [
        "organization",
        "configuration",
        "document",
        "password",
        "location",
        "custom_asset",
        "custom_asset_type",
        "configuration_type",
    ]
)


class IdMapperError(Exception):
    """Base exception for IdMapper errors."""

    pass


class InvalidEntityTypeError(IdMapperError):
    """Raised when an invalid entity type is provided."""

    def __init__(self, entity_type: str) -> None:
        self.entity_type = entity_type
        super().__init__(
            f"Invalid entity type: '{entity_type}'. "
            f"Valid types: {sorted(VALID_ENTITY_TYPES)}"
        )


class IdMapper:
    """Maps IT Glue IDs to new UUIDs for migration tracking.

    Provides in-memory storage with JSON persistence for resuming
    interrupted migrations. Supports multiple entity types with
    separate namespaces.

    Example:
        >>> mapper = IdMapper()
        >>> mapper.add("organization", "itglue_123", "uuid-abc-123")
        >>> mapper.get("organization", "itglue_123")
        'uuid-abc-123'
        >>> mapper.save("id_map.json")
        >>>
        >>> # Later, resume migration
        >>> mapper2 = IdMapper()
        >>> mapper2.load("id_map.json")
        >>> mapper2.get("organization", "itglue_123")
        'uuid-abc-123'
    """

    def __init__(self) -> None:
        """Initialize an empty ID mapper."""
        self._mappings: dict[str, dict[str, str]] = {
            entity_type: {} for entity_type in VALID_ENTITY_TYPES
        }

    def _validate_entity_type(self, entity_type: str) -> None:
        """Validate that entity_type is a supported type.

        Args:
            entity_type: The entity type to validate.

        Raises:
            InvalidEntityTypeError: If entity_type is not valid.
        """
        if entity_type not in VALID_ENTITY_TYPES:
            raise InvalidEntityTypeError(entity_type)

    def add(self, entity_type: str, itglue_id: str, uuid: str) -> None:
        """Add a mapping from IT Glue ID to UUID.

        Args:
            entity_type: The type of entity being mapped.
            itglue_id: The original IT Glue ID.
            uuid: The new UUID in the target system.

        Raises:
            InvalidEntityTypeError: If entity_type is not valid.
            ValueError: If itglue_id or uuid is empty.
        """
        self._validate_entity_type(entity_type)

        if not itglue_id:
            raise ValueError("itglue_id cannot be empty")
        if not uuid:
            raise ValueError("uuid cannot be empty")

        # Convert to string to handle integer IDs from IT Glue
        itglue_id_str = str(itglue_id)
        self._mappings[entity_type][itglue_id_str] = uuid

    def get(self, entity_type: str, itglue_id: str) -> str | None:
        """Get the UUID for an IT Glue ID.

        Args:
            entity_type: The type of entity to look up.
            itglue_id: The IT Glue ID to look up.

        Returns:
            The UUID if found, None otherwise.

        Raises:
            InvalidEntityTypeError: If entity_type is not valid.
        """
        self._validate_entity_type(entity_type)
        itglue_id_str = str(itglue_id)
        return self._mappings[entity_type].get(itglue_id_str)

    def has(self, entity_type: str, itglue_id: str) -> bool:
        """Check if a mapping exists for an IT Glue ID.

        Args:
            entity_type: The type of entity to check.
            itglue_id: The IT Glue ID to check.

        Returns:
            True if the mapping exists, False otherwise.

        Raises:
            InvalidEntityTypeError: If entity_type is not valid.
        """
        self._validate_entity_type(entity_type)
        itglue_id_str = str(itglue_id)
        return itglue_id_str in self._mappings[entity_type]

    def get_all(self, entity_type: str) -> dict[str, str]:
        """Get all mappings for an entity type.

        Args:
            entity_type: The type of entity to get mappings for.

        Returns:
            A copy of the mappings dictionary for the entity type.

        Raises:
            InvalidEntityTypeError: If entity_type is not valid.
        """
        self._validate_entity_type(entity_type)
        return self._mappings[entity_type].copy()

    def save(self, path: str | Path) -> None:
        """Save all mappings to a JSON file.

        Args:
            path: The file path to save to.

        Raises:
            OSError: If the file cannot be written.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "mappings": self._mappings,
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def load(self, path: str | Path) -> None:
        """Load mappings from a JSON file.

        This merges loaded mappings with any existing mappings,
        with loaded mappings taking precedence on conflicts.

        Args:
            path: The file path to load from.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is invalid.
            OSError: If the file cannot be read.
        """
        path = Path(path)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid ID map file format: expected dict, got {type(data).__name__}")

        version = data.get("version")
        if version != 1:
            raise ValueError(f"Unsupported ID map version: {version}")

        mappings = data.get("mappings")
        if not isinstance(mappings, dict):
            raise ValueError("Invalid ID map file format: missing or invalid 'mappings' field")

        # Merge loaded mappings into existing mappings
        for entity_type, type_mappings in mappings.items():
            if entity_type not in VALID_ENTITY_TYPES:
                # Skip unknown entity types for forward compatibility
                continue
            if not isinstance(type_mappings, dict):
                raise ValueError(
                    f"Invalid mappings for entity type '{entity_type}': "
                    f"expected dict, got {type(type_mappings).__name__}"
                )
            self._mappings[entity_type].update(type_mappings)

    def clear(self) -> None:
        """Clear all mappings."""
        for entity_type in self._mappings:
            self._mappings[entity_type].clear()

    def stats(self) -> dict[str, int]:
        """Get the count of mappings per entity type.

        Returns:
            A dictionary mapping entity type to count of mappings.
        """
        return {
            entity_type: len(mappings)
            for entity_type, mappings in self._mappings.items()
        }

    def total_count(self) -> int:
        """Get the total count of all mappings.

        Returns:
            The total number of mappings across all entity types.
        """
        return sum(len(mappings) for mappings in self._mappings.values())

    def __repr__(self) -> str:
        """Return a string representation of the mapper."""
        total = self.total_count()
        return f"IdMapper(total_mappings={total})"
