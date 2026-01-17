"""Field type inference for custom asset type schema generation.

This module analyzes CSV column data to infer the appropriate BifrostDocs
field types for custom asset type schemas.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict

# Supported field types in BifrostDocs API
FieldType = Literal[
    "text",
    "textbox",
    "number",
    "date",
    "checkbox",
    "select",
    "header",
    "password",
    "totp",
]

# Pattern to detect HTML tags in field values
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


class _FieldDefinitionRequired(TypedDict):
    """Required fields for FieldDefinition."""

    key: str
    name: str
    type: FieldType
    required: bool
    show_in_list: bool


class FieldDefinition(_FieldDefinitionRequired, total=False):
    """Definition of a custom asset type field.

    Required fields:
        key: Unique identifier within the type (snake_case)
        name: Display name (original column name)
        type: Field type from FieldType
        required: Whether field is required
        show_in_list: Whether to show in list view

    Optional fields:
        options: List of options for select type
        hint: Hint text for the field
        default_value: Default value for the field
    """

    options: list[str]
    hint: str
    default_value: str


# Patterns for column name detection (case-insensitive)
PASSWORD_PATTERNS = re.compile(r"password|secret|key|credential|token", re.IGNORECASE)
TOTP_PATTERNS = re.compile(r"otp|totp|mfa|2fa|two.?factor", re.IGNORECASE)

# Date patterns for value detection
DATE_PATTERNS = [
    # ISO format: YYYY-MM-DD
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    # US format: MM/DD/YYYY
    re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"),
    # EU format: DD/MM/YYYY
    re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"),
    # ISO datetime: YYYY-MM-DDTHH:MM:SS
    re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"),
    # US datetime: MM/DD/YYYY HH:MM
    re.compile(r"^\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}"),
    # Format: YYYY/MM/DD
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),
    # Format: DD-MM-YYYY
    re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$"),
]

# Boolean value patterns (case-insensitive matching done separately)
BOOLEAN_TRUE_VALUES = frozenset({"true", "yes", "1", "on", "enabled"})
BOOLEAN_FALSE_VALUES = frozenset({"false", "no", "0", "off", "disabled"})
BOOLEAN_VALUES = BOOLEAN_TRUE_VALUES | BOOLEAN_FALSE_VALUES

# Thresholds for inference
TEXTBOX_LENGTH_THRESHOLD = 200  # Characters
SELECT_MAX_UNIQUE_VALUES = 10  # Maximum unique values for select
SELECT_MIN_FREQUENCY_RATIO = 0.5  # At least 50% of values use one of the options


def column_name_to_key(column_name: str) -> str:
    """Convert a column header to a snake_case key.

    Args:
        column_name: Original column header name.

    Returns:
        Snake case key suitable for field definition.

    Examples:
        >>> column_name_to_key("Common Name")
        'common_name'
        >>> column_name_to_key("SSL/TLS Version")
        'ssl_tls_version'
        >>> column_name_to_key("User's Email Address")
        'users_email_address'
        >>> column_name_to_key("  Multiple   Spaces  ")
        'multiple_spaces'
    """
    # Strip leading/trailing whitespace
    result = column_name.strip()

    # Replace common separators with underscores (preserve underscores)
    result = re.sub(r"[/\\-]", "_", result)

    # Remove special characters except spaces, underscores, and alphanumeric
    result = re.sub(r"[^a-zA-Z0-9\s_]", "", result)

    # Replace all whitespace (spaces, tabs, etc.) with underscores
    result = re.sub(r"\s+", "_", result)

    # Collapse multiple underscores to single underscore
    result = re.sub(r"_+", "_", result)

    # Convert to lowercase
    result = result.lower()

    # Strip leading/trailing underscores
    result = result.strip("_")

    # Handle empty result
    if not result:
        return "field"

    return result


def _is_numeric(value: str) -> bool:
    """Check if a value is numeric (integer or float).

    Args:
        value: String value to check.

    Returns:
        True if the value can be parsed as a number.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False


def _is_date(value: str) -> bool:
    """Check if a value matches any date pattern.

    Args:
        value: String value to check.

    Returns:
        True if the value matches a date pattern.
    """
    return any(pattern.match(value) for pattern in DATE_PATTERNS)


def _is_boolean(value: str) -> bool:
    """Check if a value is a boolean representation.

    Args:
        value: String value to check.

    Returns:
        True if the value represents a boolean.
    """
    return value.lower() in BOOLEAN_VALUES


def _has_newlines_or_long(value: str) -> bool:
    """Check if a value has newlines, HTML tags, or exceeds length threshold.

    Args:
        value: String value to check.

    Returns:
        True if the value contains newlines, HTML tags, or is very long.
    """
    return "\n" in value or len(value) > TEXTBOX_LENGTH_THRESHOLD or bool(
        HTML_TAG_PATTERN.search(value)
    )


def detect_field_type(samples: list[str]) -> str:
    """Detect field type from sample values.

    Checks for multi-line text indicators including newlines and HTML tags.

    Args:
        samples: List of sample values for a field.

    Returns:
        "textbox" if newlines or HTML detected, "text" otherwise.
    """
    for sample in samples:
        if not sample:
            continue
        # Check for newlines
        if "\n" in sample or "\r" in sample:
            return "textbox"
        # Check for HTML tags using regex
        if HTML_TAG_PATTERN.search(sample):
            return "textbox"
    return "text"  # Default to single-line text


class FieldInferrer:
    """Infer field types from CSV column data.

    Analyzes values across all rows in a column to determine the best
    BifrostDocs field type for custom asset type schemas.

    Example:
        >>> inferrer = FieldInferrer()
        >>> field = inferrer.infer_type(
        ...     "Status",
        ...     ["Active", "Active", "Inactive", "Active", None, "Inactive"]
        ... )
        >>> field["type"]
        'select'
        >>> field["options"]
        ['Active', 'Inactive']
    """

    def infer_type(
        self,
        column_name: str,
        values: Sequence[str | None],
        *,
        field_index: int = 0,
    ) -> FieldDefinition:
        """Infer the field type from column name and values.

        Args:
            column_name: Original column header name.
            values: List of values from all rows for this column.
            field_index: Position index for show_in_list calculation.

        Returns:
            FieldDefinition with inferred type and settings.
        """
        key = column_name_to_key(column_name)
        field_type = self._infer_field_type(column_name, values)

        field: FieldDefinition = {
            "key": key,
            "name": column_name,
            "type": field_type,
            "required": False,
            "show_in_list": field_index < 3,  # First 3 non-id fields
        }

        # Add options for select type
        if field_type == "select":
            options = self._extract_select_options(values)
            if options:
                field["options"] = options

        return field

    def _infer_field_type(
        self,
        column_name: str,
        values: Sequence[str | None],
    ) -> FieldType:
        """Determine the field type based on column name and values.

        Args:
            column_name: Original column header name.
            values: List of values from all rows.

        Returns:
            Inferred field type.
        """
        # Check column name patterns first (highest priority)
        # TOTP must be checked before password (because TOTP columns often contain "secret")
        if TOTP_PATTERNS.search(column_name):
            return "totp"

        if PASSWORD_PATTERNS.search(column_name):
            return "password"

        # Filter to non-empty values for content analysis
        non_empty_values = [v for v in values if v is not None and v.strip()]

        # No values to analyze - default to text
        if not non_empty_values:
            return "text"

        # Check if all values are boolean (before number check, since "1"/"0" are both)
        if all(_is_boolean(v) for v in non_empty_values):
            return "checkbox"

        # Check if all values are numeric
        if all(_is_numeric(v) for v in non_empty_values):
            return "number"

        # Check if all values are dates
        if all(_is_date(v) for v in non_empty_values):
            return "date"

        # Check if most values are long or have newlines (textbox)
        # Use >= for "most" to include exactly half
        long_values = sum(1 for v in non_empty_values if _has_newlines_or_long(v))
        if long_values >= len(non_empty_values) / 2 and long_values > 0:
            return "textbox"

        # Check if suitable for select (few unique values, high frequency)
        if self._is_suitable_for_select(non_empty_values):
            return "select"

        # Default to text
        return "text"

    def _is_suitable_for_select(self, values: list[str]) -> bool:
        """Check if values are suitable for a select/dropdown field.

        Criteria:
        - Less than SELECT_MAX_UNIQUE_VALUES unique values
        - At least SELECT_MIN_FREQUENCY_RATIO of rows use one of the top values

        Args:
            values: List of non-empty values.

        Returns:
            True if values are suitable for select type.
        """
        if not values:
            return False

        unique_values = set(values)

        # Too many unique values
        if len(unique_values) > SELECT_MAX_UNIQUE_VALUES:
            return False

        # Check frequency - at least 50% should use one of the options
        value_counts = Counter(values)
        total = len(values)

        # Calculate what percentage of values are repeated
        repeated_count = sum(count for count in value_counts.values() if count > 1)

        # If most values are unique (not repeated), not suitable for select
        if repeated_count / total < SELECT_MIN_FREQUENCY_RATIO:
            return False

        return True

    def _extract_select_options(self, values: Sequence[str | None]) -> list[str]:
        """Extract unique options for a select field.

        Args:
            values: List of all values (may include None/empty).

        Returns:
            Sorted list of unique non-empty options.
        """
        options: set[str] = set()

        for value in values:
            if value is not None and value.strip():
                options.add(value.strip())

        return sorted(options)

    def infer_schema(
        self,
        columns: Sequence[str],
        rows: Sequence[Mapping[str, str | None]],
        *,
        skip_columns: set[str] | None = None,
    ) -> list[FieldDefinition]:
        """Infer field definitions for all columns in a dataset.

        Args:
            columns: List of column names.
            rows: List of row dictionaries.
            skip_columns: Column names to skip (e.g., ID columns).

        Returns:
            List of FieldDefinition dicts for all non-skipped columns.
        """
        skip_columns = skip_columns or set()

        # Filter columns
        filtered_columns = [c for c in columns if c not in skip_columns]

        # Collect values per column
        column_values: dict[str, list[str | None]] = {col: [] for col in filtered_columns}

        for row in rows:
            for col in filtered_columns:
                column_values[col].append(row.get(col))

        # Infer types for each column
        fields: list[FieldDefinition] = []
        field_index = 0

        for col in filtered_columns:
            field = self.infer_type(
                col,
                column_values[col],
                field_index=field_index,
            )
            fields.append(field)
            field_index += 1

        return fields
