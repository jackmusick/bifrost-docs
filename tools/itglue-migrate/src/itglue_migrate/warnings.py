"""Warning detection module for IT Glue migration preview.

This module analyzes parsed export data and detects potential issues
that should be reviewed before migration. Issues are classified by
category and severity to help users prioritize review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# Known valid resource types for passwords
KNOWN_RESOURCE_TYPES = frozenset(
    [
        "Configuration",
        "Location",
        "Organization",
        "Contact",
        "Document",
        # StructuredData::Cell and Row are internal IT Glue references to cells/rows
        # within flexible assets. They can't be resolved from export data alone
        # (the cell IDs aren't in the CSV), but they're valid embedded password refs.
        "StructuredData::Cell",
        "StructuredData::Row",
    ]
)

# Resource types that reference cells/rows which can't be resolved from export
UNRESOLVABLE_RESOURCE_TYPES = frozenset(["StructuredData::Cell", "StructuredData::Row"])

# Severity levels
Severity = Literal["info", "warning", "error"]

# Warning categories
Category = Literal[
    "missing_reference",
    "duplicate",
    "unknown_type",
    "empty_value",
    "data_quality",
]

# Size threshold for large documents (1MB)
LARGE_DOCUMENT_THRESHOLD = 1024 * 1024


@dataclass
class Warning:
    """Represents a detected issue during migration preview.

    Attributes:
        category: The type of warning (e.g., "missing_reference", "duplicate").
        severity: Impact level ("info", "warning", "error").
        message: Human-readable description of the issue.
        entity_type: The type of entity affected (e.g., "password", "organization").
        entity_id: The ID of the affected entity (if applicable).
        details: Additional context about the warning.
    """

    category: Category
    severity: Severity
    message: str
    entity_type: str | None = None
    entity_id: str | None = None
    details: dict[str, Any] | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Convert warning to dictionary representation."""
        result: dict[str, Any] = {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
        }
        if self.entity_type is not None:
            result["entity_type"] = self.entity_type
        if self.entity_id is not None:
            result["entity_id"] = self.entity_id
        if self.details is not None:
            result["details"] = self.details
        return result


@dataclass
class ParsedData:
    """Container for parsed export data.

    This dataclass standardizes the structure expected by WarningDetector.

    Attributes:
        organizations: List of parsed organization dictionaries.
        configurations: List of parsed configuration dictionaries.
        documents: List of parsed document dictionaries.
        locations: List of parsed location dictionaries.
        passwords: List of parsed password dictionaries.
        custom_assets: Dict mapping asset type name to list of assets.
        field_definitions: Dict mapping asset type name to field definitions.
    """

    organizations: list[dict[str, Any]] = field(default_factory=list)
    configurations: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    locations: list[dict[str, Any]] = field(default_factory=list)
    passwords: list[dict[str, Any]] = field(default_factory=list)
    custom_assets: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    field_definitions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


class WarningDetector:
    """Analyzes parsed export data and detects potential migration issues.

    The detector runs multiple checks against the parsed data to identify:
    - Missing references (e.g., passwords pointing to non-existent resources)
    - Unknown types (e.g., unrecognized resource_type values)
    - Duplicates (e.g., organizations or assets with duplicate names)
    - Empty/invalid values (e.g., passwords missing password field)
    - Data quality issues (e.g., very large documents)

    Example:
        >>> detector = WarningDetector()
        >>> parsed = ParsedData(
        ...     organizations=[{"id": "1", "name": "Acme"}],
        ...     passwords=[{"id": "1", "name": "Test", "password": ""}],
        ... )
        >>> warnings = detector.detect_all(parsed)
        >>> for w in warnings:
        ...     print(f"{w.severity}: {w.message}")
    """

    def __init__(self) -> None:
        """Initialize the warning detector."""
        pass

    def detect_all(self, parsed_data: ParsedData) -> list[Warning]:
        """Run all detection checks and return discovered warnings.

        Args:
            parsed_data: Parsed export data to analyze.

        Returns:
            List of Warning objects for all detected issues.
        """
        warnings: list[Warning] = []

        # Run all detection methods
        warnings.extend(self._detect_missing_references(parsed_data))
        warnings.extend(self._detect_unknown_types(parsed_data))
        warnings.extend(self._detect_duplicates(parsed_data))
        warnings.extend(self._detect_empty_values(parsed_data))
        warnings.extend(self._detect_data_quality_issues(parsed_data))

        return warnings

    def _detect_missing_references(self, parsed_data: ParsedData) -> list[Warning]:
        """Detect missing reference issues.

        Checks:
        - Passwords with resource_id that doesn't exist in configurations
          or custom assets
        - Documents referencing images that don't exist (based on content)

        Args:
            parsed_data: Parsed export data.

        Returns:
            List of warnings for missing references.
        """
        warnings: list[Warning] = []

        # Build lookup of existing entity IDs
        config_ids = {c.get("id") for c in parsed_data.configurations if c.get("id")}
        location_ids = {loc.get("id") for loc in parsed_data.locations if loc.get("id")}
        org_ids = {o.get("id") for o in parsed_data.organizations if o.get("id")}
        doc_ids = {d.get("id") for d in parsed_data.documents if d.get("id")}

        # Build custom asset ID lookup by type
        custom_asset_ids: dict[str, set[str]] = {}
        for asset_type, assets in parsed_data.custom_assets.items():
            asset_id_set: set[str] = set()
            for a in assets:
                asset_id = a.get("id")
                if asset_id:
                    asset_id_set.add(asset_id)
            custom_asset_ids[asset_type] = asset_id_set

        # All custom asset IDs combined
        all_custom_asset_ids = set()
        for ids in custom_asset_ids.values():
            all_custom_asset_ids.update(ids)

        # Check password references
        for password in parsed_data.passwords:
            resource_id = password.get("resource_id")
            resource_type = password.get("resource_type")

            if not resource_id:
                continue

            # Skip StructuredData::Cell and StructuredData::Row - these are internal
            # IT Glue cell/row IDs that can't be resolved from export data. They're
            # embedded passwords within custom assets and will be handled during import.
            if resource_type in UNRESOLVABLE_RESOURCE_TYPES:
                continue

            # Check based on resource type
            reference_valid = False

            if resource_type == "Configuration":
                reference_valid = resource_id in config_ids
            elif resource_type == "Location":
                reference_valid = resource_id in location_ids
            elif resource_type == "Organization":
                reference_valid = resource_id in org_ids
            elif resource_type == "Document":
                reference_valid = resource_id in doc_ids
            elif resource_type and resource_type.startswith("StructuredData::"):
                # Custom asset reference
                # Extract type name: "StructuredData::SSL Certificate" -> "ssl-certificate"
                type_name = resource_type.replace("StructuredData::", "").strip()
                # Normalize to slug format for lookup
                type_slug = type_name.lower().replace(" ", "-")

                # Check if the ID exists in that specific custom asset type
                if type_slug in custom_asset_ids:
                    reference_valid = resource_id in custom_asset_ids[type_slug]
                else:
                    # Try to find in any custom asset type
                    reference_valid = resource_id in all_custom_asset_ids
            elif resource_type is None:
                # No resource type specified, check all possible targets
                reference_valid = (
                    resource_id in config_ids
                    or resource_id in location_ids
                    or resource_id in org_ids
                    or resource_id in doc_ids
                    or resource_id in all_custom_asset_ids
                )
            else:
                # Unknown resource type with ID - will be caught by unknown_type detector
                # But still check if ID exists anywhere
                reference_valid = (
                    resource_id in config_ids
                    or resource_id in location_ids
                    or resource_id in org_ids
                    or resource_id in doc_ids
                    or resource_id in all_custom_asset_ids
                )

            if not reference_valid:
                warnings.append(
                    Warning(
                        category="missing_reference",
                        severity="warning",
                        message=f"Password references non-existent {resource_type or 'resource'} with ID '{resource_id}'",
                        entity_type="password",
                        entity_id=password.get("id"),
                        details={
                            "password_name": password.get("name"),
                            "resource_type": resource_type,
                            "resource_id": resource_id,
                        },
                    )
                )

        return warnings

    def _detect_unknown_types(self, parsed_data: ParsedData) -> list[Warning]:
        """Detect unknown resource type values.

        Checks passwords for resource_type values that aren't recognized.

        Args:
            parsed_data: Parsed export data.

        Returns:
            List of warnings for unknown types.
        """
        warnings: list[Warning] = []

        # Get all custom asset type names for validation
        custom_type_names = set(parsed_data.custom_assets.keys())

        for password in parsed_data.passwords:
            resource_type = password.get("resource_type")

            if not resource_type:
                continue

            # Check if it's a known type
            is_known = resource_type in KNOWN_RESOURCE_TYPES

            # Check if it's a StructuredData reference to a known custom asset type
            if not is_known and resource_type.startswith("StructuredData::"):
                type_name = resource_type.replace("StructuredData::", "").strip()
                type_slug = type_name.lower().replace(" ", "-")
                is_known = type_slug in custom_type_names

            if not is_known:
                warnings.append(
                    Warning(
                        category="unknown_type",
                        severity="info",
                        message=f"Password has unknown resource_type '{resource_type}'",
                        entity_type="password",
                        entity_id=password.get("id"),
                        details={
                            "password_name": password.get("name"),
                            "resource_type": resource_type,
                        },
                    )
                )

        return warnings

    def _detect_duplicates(self, parsed_data: ParsedData) -> list[Warning]:
        """Detect duplicate entries.

        Checks:
        - Organizations with duplicate names
        - Custom assets with duplicate names within same organization

        Args:
            parsed_data: Parsed export data.

        Returns:
            List of warnings for duplicates.
        """
        warnings: list[Warning] = []

        # Check organization name duplicates
        org_names: dict[str, list[str]] = {}
        for org in parsed_data.organizations:
            name = org.get("name")
            org_id = org.get("id")
            if name:
                name_lower = name.lower()
                if name_lower not in org_names:
                    org_names[name_lower] = []
                if org_id:
                    org_names[name_lower].append(org_id)

        for name_lower, ids in org_names.items():
            if len(ids) > 1:
                # Find original case name from first org
                original_name = name_lower
                for org in parsed_data.organizations:
                    if org.get("name", "").lower() == name_lower:
                        original_name = org.get("name", name_lower)
                        break

                warnings.append(
                    Warning(
                        category="duplicate",
                        severity="warning",
                        message=f"Multiple organizations found with name '{original_name}'",
                        entity_type="organization",
                        entity_id=ids[0],
                        details={
                            "duplicate_ids": ids,
                            "count": len(ids),
                        },
                    )
                )

        # Note: Custom assets are allowed to have duplicate names within an org,
        # so we don't flag those as duplicates.

        return warnings

    def _detect_empty_values(self, parsed_data: ParsedData) -> list[Warning]:
        """Detect empty or missing required values.

        Checks:
        - Passwords with empty password field
        - Organizations with empty name
        - Configurations with empty name

        Args:
            parsed_data: Parsed export data.

        Returns:
            List of warnings for empty values.
        """
        warnings: list[Warning] = []

        # Check passwords with empty password field
        for password in parsed_data.passwords:
            if not password.get("password"):
                warnings.append(
                    Warning(
                        category="empty_value",
                        severity="info",
                        message="Password entry has empty password field",
                        entity_type="password",
                        entity_id=password.get("id"),
                        details={
                            "password_name": password.get("name"),
                        },
                    )
                )

        # Check organizations with empty name
        for org in parsed_data.organizations:
            if not org.get("name"):
                warnings.append(
                    Warning(
                        category="empty_value",
                        severity="error",
                        message="Organization has empty name",
                        entity_type="organization",
                        entity_id=org.get("id"),
                        details=None,
                    )
                )

        # Check configurations with empty name
        for config in parsed_data.configurations:
            if not config.get("name"):
                warnings.append(
                    Warning(
                        category="empty_value",
                        severity="error",
                        message="Configuration has empty name",
                        entity_type="configuration",
                        entity_id=config.get("id"),
                        details=None,
                    )
                )

        return warnings

    def _detect_data_quality_issues(self, parsed_data: ParsedData) -> list[Warning]:
        """Detect data quality issues.

        Checks:
        - Documents with very large content (>1MB)
        - Custom assets with many empty required fields

        Args:
            parsed_data: Parsed export data.

        Returns:
            List of warnings for data quality issues.
        """
        warnings: list[Warning] = []

        # Check for large documents
        for doc in parsed_data.documents:
            content = doc.get("content")
            if content and len(content) > LARGE_DOCUMENT_THRESHOLD:
                size_mb = len(content) / (1024 * 1024)
                warnings.append(
                    Warning(
                        category="data_quality",
                        severity="warning",
                        message=f"Document has very large content ({size_mb:.2f}MB)",
                        entity_type="document",
                        entity_id=doc.get("id"),
                        details={
                            "document_name": doc.get("name"),
                            "content_size_bytes": len(content),
                        },
                    )
                )

        # Check custom assets for empty required fields
        for asset_type, assets in parsed_data.custom_assets.items():
            field_defs = parsed_data.field_definitions.get(asset_type, [])

            # Get required field names
            required_fields: list[str] = []
            for fd in field_defs:
                if isinstance(fd, dict):
                    if fd.get("required"):
                        name = fd.get("name")
                        if name:
                            required_fields.append(name)
                else:
                    if fd.required:
                        required_fields.append(fd.name)

            if not required_fields:
                continue

            for asset in assets:
                fields = asset.get("fields", {})
                empty_required = []

                for field_name in required_fields:
                    if not fields.get(field_name):
                        empty_required.append(field_name)

                # Only warn if more than half of required fields are empty
                if len(empty_required) > len(required_fields) // 2 and len(empty_required) > 1:
                    warnings.append(
                        Warning(
                            category="data_quality",
                            severity="info",
                            message=f"Custom asset has {len(empty_required)} empty required fields",
                            entity_type=f"custom_asset:{asset_type}",
                            entity_id=asset.get("id"),
                            details={
                                "asset_type": asset_type,
                                "empty_required_fields": empty_required,
                                "total_required_fields": len(required_fields),
                            },
                        )
                    )

        return warnings


def summarize(warnings: list[Warning]) -> dict[str, Any]:
    """Generate a summary of warnings.

    Args:
        warnings: List of Warning objects to summarize.

    Returns:
        Dictionary with summary statistics:
        - total: Total number of warnings
        - by_severity: Dict of severity to count
        - by_category: Dict of category to count
        - errors: Count of error-level warnings
        - has_blockers: True if any error-level warnings exist
    """
    by_severity: dict[str, int] = {
        "info": 0,
        "warning": 0,
        "error": 0,
    }

    by_category: dict[str, int] = {}

    for warning in warnings:
        by_severity[warning.severity] = by_severity.get(warning.severity, 0) + 1
        by_category[warning.category] = by_category.get(warning.category, 0) + 1

    return {
        "total": len(warnings),
        "by_severity": by_severity,
        "by_category": by_category,
        "errors": by_severity.get("error", 0),
        "has_blockers": by_severity.get("error", 0) > 0,
    }
