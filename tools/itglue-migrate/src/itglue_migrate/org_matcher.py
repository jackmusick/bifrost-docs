"""Organization matching for IT Glue to BifrostDocs migration.

This module matches IT Glue organizations to existing organizations in the
target system, supporting migration resume by detecting previously migrated
organizations via their stored IT Glue ID metadata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger(__name__)

# Match result status types
MatchStatus = Literal["matched", "create"]

# How the match was determined
MatchType = Literal["itglue_id", "name"]


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Result of attempting to match an IT Glue org to an existing org.

    Attributes:
        status: Whether a match was found ("matched") or org needs creation ("create").
        uuid: The existing organization UUID if matched, None otherwise.
        match_type: How the match was made ("itglue_id", "name"), or None if no match.
    """

    status: MatchStatus
    uuid: str | None
    match_type: MatchType | None

    @classmethod
    def matched_by_itglue_id(cls, uuid: str) -> MatchResult:
        """Create a result for a match via IT Glue ID metadata."""
        return cls(status="matched", uuid=uuid, match_type="itglue_id")

    @classmethod
    def matched_by_name(cls, uuid: str) -> MatchResult:
        """Create a result for a match via organization name."""
        return cls(status="matched", uuid=uuid, match_type="name")

    @classmethod
    def needs_creation(cls) -> MatchResult:
        """Create a result indicating the org needs to be created."""
        return cls(status="create", uuid=None, match_type=None)


class OrgMatcher:
    """Matches IT Glue organizations to existing organizations in the target system.

    Matching priority:
    1. Match by metadata.itglue_id (exact match from previous migration)
    2. Match by name (case-insensitive exact match)
    3. No match -> mark for creation

    Example:
        >>> existing_orgs = [
        ...     {"id": "uuid-1", "name": "Acme Corp", "metadata": {"itglue_id": "123"}},
        ...     {"id": "uuid-2", "name": "Beta Inc", "metadata": {}},
        ... ]
        >>> matcher = OrgMatcher(existing_orgs)
        >>> result = matcher.match({"id": "123", "attributes": {"name": "Old Name"}})
        >>> result.status
        'matched'
        >>> result.uuid
        'uuid-1'
        >>> result.match_type
        'itglue_id'
    """

    def __init__(self, existing_orgs: list[dict[str, Any]]) -> None:
        """Initialize the matcher with existing organizations.

        Args:
            existing_orgs: List of existing organizations from the target API.
                Each dict should have 'id', 'name', and optionally 'metadata'
                with 'itglue_id' for previously migrated orgs.
        """
        # Build lookup indices
        self._by_itglue_id: dict[str, str] = {}  # itglue_id -> uuid
        self._by_name_lower: dict[str, list[str]] = {}  # lowercase name -> [uuids]

        for org in existing_orgs:
            uuid = org.get("id")
            if not uuid:
                logger.warning("Skipping existing org without id: %s", org)
                continue

            # Index by IT Glue ID if present in metadata
            metadata = org.get("metadata") or {}
            itglue_id = metadata.get("itglue_id")
            if itglue_id:
                itglue_id_str = str(itglue_id)
                if itglue_id_str in self._by_itglue_id:
                    logger.warning(
                        "Duplicate itglue_id '%s' found in existing orgs: %s and %s",
                        itglue_id_str,
                        self._by_itglue_id[itglue_id_str],
                        uuid,
                    )
                self._by_itglue_id[itglue_id_str] = uuid

            # Index by lowercase name
            name = org.get("name")
            if name:
                name_lower = name.lower()
                if name_lower not in self._by_name_lower:
                    self._by_name_lower[name_lower] = []
                self._by_name_lower[name_lower].append(uuid)

        # Track matched results for get_mapping()
        self._matched: dict[str, MatchResult] = {}

        logger.debug(
            "OrgMatcher initialized: %d by itglue_id, %d unique names",
            len(self._by_itglue_id),
            len(self._by_name_lower),
        )

    def match(self, itglue_org: dict[str, Any]) -> MatchResult:
        """Match an IT Glue organization to an existing organization.

        Args:
            itglue_org: IT Glue organization dict with 'id' and 'attributes.name'.

        Returns:
            MatchResult indicating whether a match was found and how.
        """
        itglue_id = itglue_org.get("id")
        attributes = itglue_org.get("attributes") or {}
        name = attributes.get("name")

        # Use IT Glue org name for mapping key (fallback to ID if no name)
        mapping_key = name if name else str(itglue_id) if itglue_id else "<unknown>"

        # Priority 1: Match by IT Glue ID in metadata
        if itglue_id:
            itglue_id_str = str(itglue_id)
            if itglue_id_str in self._by_itglue_id:
                uuid = self._by_itglue_id[itglue_id_str]
                result = MatchResult.matched_by_itglue_id(uuid)
                logger.debug(
                    "Matched org '%s' by itglue_id '%s' -> %s",
                    name,
                    itglue_id_str,
                    uuid,
                )
                self._matched[mapping_key] = result
                return result

        # Priority 2: Match by name (case-insensitive)
        if name:
            name_lower = name.lower()
            if name_lower in self._by_name_lower:
                uuids = self._by_name_lower[name_lower]

                # Warn if multiple orgs have the same name
                if len(uuids) > 1:
                    logger.warning(
                        "Multiple existing orgs match name '%s': %s (using first)",
                        name,
                        uuids,
                    )

                uuid = uuids[0]
                result = MatchResult.matched_by_name(uuid)
                logger.debug("Matched org '%s' by name -> %s", name, uuid)
                self._matched[mapping_key] = result
                return result

        # No match - needs creation
        result = MatchResult.needs_creation()
        if not name:
            logger.warning(
                "IT Glue org id='%s' has no name, will create with empty name",
                itglue_id,
            )
        logger.debug("No match for org '%s' (itglue_id=%s), will create", name, itglue_id)
        self._matched[mapping_key] = result
        return result

    def get_mapping(self) -> dict[str, MatchResult]:
        """Get the mapping of all matched IT Glue orgs.

        Returns:
            Dictionary mapping IT Glue org names to their match results.
            Only includes orgs that have been processed via match().
        """
        return self._matched.copy()

    def get_stats(self) -> dict[str, int]:
        """Get matching statistics.

        Returns:
            Dictionary with counts of matched_by_itglue_id, matched_by_name, and create.
        """
        stats = {
            "matched_by_itglue_id": 0,
            "matched_by_name": 0,
            "create": 0,
        }

        for result in self._matched.values():
            if result.status == "create":
                stats["create"] += 1
            elif result.match_type == "itglue_id":
                stats["matched_by_itglue_id"] += 1
            elif result.match_type == "name":
                stats["matched_by_name"] += 1

        return stats

    def __repr__(self) -> str:
        """Return string representation of the matcher."""
        stats = self.get_stats()
        return (
            f"OrgMatcher(matched={stats['matched_by_itglue_id'] + stats['matched_by_name']}, "
            f"create={stats['create']})"
        )
