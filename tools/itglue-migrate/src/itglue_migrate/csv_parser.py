"""CSV parser for IT Glue export files.

This module parses IT Glue export CSV files including core entities
(organizations, configurations, documents, locations, passwords) and
custom asset types with auto-detected field definitions.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# Known core entity CSV filenames
CORE_ENTITY_FILES = frozenset(
    [
        "organizations.csv",
        "configurations.csv",
        "documents.csv",
        "locations.csv",
        "passwords.csv",
        "contacts.csv",  # Skipped during migration but recognized
    ]
)

# Field type detection patterns
DATE_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$"
)
NUMBER_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?$")
CHECKBOX_VALUES = frozenset(["true", "false", "yes", "no", "1", "0"])

# Field type literal
FieldType = Literal["text", "textbox", "number", "date", "checkbox", "select"]


def slugify_to_display_name(slug: str) -> str:
    """Convert a kebab-case slug to a display name.

    Examples:
        "active-directory" -> "Active Directory"
        "ssl-certificates" -> "SSL Certificates"
        "apps-and-services" -> "Apps and Services"
        "azure-app-registration" -> "Azure App Registration"

    Args:
        slug: Kebab-case string (e.g., "active-directory").

    Returns:
        Title-cased display name (e.g., "Active Directory").
    """
    # Known acronyms that should stay uppercase
    acronyms = {"ssl", "vpn", "wan", "lan", "mdm", "mfa", "otp", "api", "sso", "ad"}
    # Words that should stay lowercase in titles
    lowercase_words = {"and", "or", "the", "a", "an", "of", "for", "to", "in", "on"}

    words = slug.replace("-", " ").split()
    result = []
    for i, word in enumerate(words):
        if word.lower() in acronyms:
            result.append(word.upper())
        elif i > 0 and word.lower() in lowercase_words:
            result.append(word.lower())
        else:
            result.append(word.capitalize())

    return " ".join(result)


class CSVParserError(Exception):
    """Base exception for CSV parsing errors."""

    pass


class FileNotFoundError(CSVParserError):
    """Raised when a CSV file is not found."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"CSV file not found: {path}")


class ParseError(CSVParserError):
    """Raised when CSV parsing fails."""

    def __init__(self, path: Path, message: str, row: int | None = None) -> None:
        self.path = path
        self.row = row
        row_info = f" (row {row})" if row is not None else ""
        super().__init__(f"Failed to parse {path}{row_info}: {message}")


@dataclass
class FieldDefinition:
    """Definition of a custom asset field.

    Attributes:
        name: The field name (from CSV header).
        field_type: Detected field type (text, textbox, number, date, checkbox).
        required: Whether the field appears to be required (has values in all rows).
        sample_values: Sample values for reference (up to 5).
    """

    name: str
    field_type: FieldType
    required: bool = False
    sample_values: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "field_type": self.field_type,
            "required": self.required,
        }


class CSVParser:
    """Parser for IT Glue export CSV files.

    Handles parsing of both core entity CSVs (organizations, configurations,
    documents, locations, passwords) and custom asset type CSVs with
    automatic field type detection.

    Example:
        >>> parser = CSVParser()
        >>> orgs = parser.parse_organizations(Path("export/organizations.csv"))
        >>> for org in orgs:
        ...     print(org["name"])

        >>> # Parse custom asset with field definitions
        >>> fields, assets = parser.parse_custom_asset_csv(
        ...     Path("export/ssl-certificates.csv"),
        ...     "ssl-certificates"
        ... )
    """

    def __init__(self) -> None:
        """Initialize the CSV parser."""
        pass

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        """Read a CSV file and return rows as dictionaries.

        Handles UTF-8 encoding with BOM and normalizes field names.

        Args:
            path: Path to the CSV file.

        Returns:
            List of dictionaries, one per row.

        Raises:
            FileNotFoundError: If the file does not exist.
            ParseError: If the CSV cannot be parsed.
        """
        if not path.exists():
            raise FileNotFoundError(path)

        try:
            # Try UTF-8 with BOM first (common in Windows exports)
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                return list(reader)
        except UnicodeDecodeError:
            # Fall back to latin-1 for legacy exports
            try:
                with path.open("r", encoding="latin-1", newline="") as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            except csv.Error as e:
                raise ParseError(path, str(e)) from e
        except csv.Error as e:
            raise ParseError(path, str(e)) from e

    def _normalize_value(self, value: str | None) -> str | None:
        """Normalize a CSV value, converting empty strings to None.

        Args:
            value: The raw CSV value.

        Returns:
            The normalized value or None if empty.
        """
        if value is None:
            return None
        value = value.strip()
        return value if value else None

    def _normalize_row(self, row: dict[str, str]) -> dict[str, Any]:
        """Normalize all values in a row.

        Args:
            row: Dictionary of field names to raw values.

        Returns:
            Dictionary with normalized values.
        """
        return {k: self._normalize_value(v) for k, v in row.items()}

    def parse_organizations(self, path: Path) -> list[dict[str, Any]]:
        """Parse organizations.csv.

        Expected columns: id, name, description, quick_notes

        Args:
            path: Path to organizations.csv.

        Returns:
            List of organization dictionaries with fields:
            - id: IT Glue organization ID
            - name: Organization name
            - description: Organization description (optional)
            - quick_notes: Quick notes (optional)

        Raises:
            FileNotFoundError: If the file does not exist.
            ParseError: If the CSV cannot be parsed.
        """
        rows = self._read_csv(path)
        organizations = []

        for row in rows:
            normalized = self._normalize_row(row)
            org = {
                "id": normalized.get("id"),
                "name": normalized.get("name"),
                "description": normalized.get("description"),
                "quick_notes": normalized.get("quick_notes"),
                "organization_status": normalized.get("organization_status"),
            }
            organizations.append(org)

        return organizations

    def parse_configurations(self, path: Path) -> list[dict[str, Any]]:
        """Parse configurations.csv.

        Expected columns: id, name, hostname, ip, mac, serial, manufacturer,
        model, notes, configuration_interfaces (JSON)

        Args:
            path: Path to configurations.csv.

        Returns:
            List of configuration dictionaries with fields:
            - id: IT Glue configuration ID
            - name: Configuration name
            - hostname: Hostname (optional)
            - ip: IP address (optional)
            - mac: MAC address (optional)
            - serial: Serial number (optional)
            - manufacturer: Manufacturer (optional)
            - model: Model (optional)
            - notes: Notes (optional)
            - organization_id: Organization ID (optional)
            - configuration_type: Configuration type name (optional)
            - configuration_interfaces: Parsed JSON list of interfaces (optional)

        Raises:
            FileNotFoundError: If the file does not exist.
            ParseError: If the CSV cannot be parsed.
        """
        rows = self._read_csv(path)
        configurations = []

        for idx, row in enumerate(rows, start=2):  # Row 1 is header
            normalized = self._normalize_row(row)

            # Parse configuration_interfaces JSON if present
            interfaces = None
            interfaces_raw = normalized.get("configuration_interfaces")
            if interfaces_raw:
                try:
                    interfaces = json.loads(interfaces_raw)
                except json.JSONDecodeError as e:
                    raise ParseError(
                        path,
                        f"Invalid JSON in configuration_interfaces: {e}",
                        row=idx,
                    ) from e

            config = {
                "id": normalized.get("id"),
                "name": normalized.get("name"),
                "hostname": normalized.get("hostname"),
                "ip": normalized.get("ip"),
                "mac": normalized.get("mac"),
                "serial": normalized.get("serial"),
                "manufacturer": normalized.get("manufacturer"),
                "model": normalized.get("model"),
                "notes": normalized.get("notes"),
                "organization_id": normalized.get("organization_id") or normalized.get("organization"),
                "configuration_type": normalized.get("configuration_type"),
                "configuration_interfaces": interfaces,
                "archived": normalized.get("archived"),
                "configuration_status": normalized.get("configuration_status"),
            }
            configurations.append(config)

        return configurations

    def parse_documents(self, path: Path) -> list[dict[str, Any]]:
        """Parse documents.csv.

        Expected columns: id, name, locator (path), organization

        Args:
            path: Path to documents.csv.

        Returns:
            List of document dictionaries with fields:
            - id: IT Glue document ID
            - name: Document name
            - locator: Document path/locator (optional)
            - organization_id: Organization ID (optional)
            - content: Document content if exported (optional)

        Raises:
            FileNotFoundError: If the file does not exist.
            ParseError: If the CSV cannot be parsed.
        """
        rows = self._read_csv(path)
        documents = []

        for row in rows:
            normalized = self._normalize_row(row)
            doc = {
                "id": normalized.get("id"),
                "name": normalized.get("name"),
                "locator": normalized.get("locator"),
                "organization_id": normalized.get("organization_id") or normalized.get("organization"),
                "content": normalized.get("content"),
                "archived": normalized.get("archived"),
            }
            documents.append(doc)

        return documents

    def parse_locations(self, path: Path) -> list[dict[str, Any]]:
        """Parse locations.csv.

        Expected columns: id, name, address fields (address_1, address_2,
        city, region, postal_code, country), phone

        Args:
            path: Path to locations.csv.

        Returns:
            List of location dictionaries with fields:
            - id: IT Glue location ID
            - name: Location name
            - address_1: Address line 1 (optional)
            - address_2: Address line 2 (optional)
            - city: City (optional)
            - region: Region/state (optional)
            - postal_code: Postal/ZIP code (optional)
            - country: Country (optional)
            - phone: Phone number (optional)
            - organization_id: Organization ID (optional)

        Raises:
            FileNotFoundError: If the file does not exist.
            ParseError: If the CSV cannot be parsed.
        """
        rows = self._read_csv(path)
        locations = []

        for row in rows:
            normalized = self._normalize_row(row)
            location = {
                "id": normalized.get("id"),
                "name": normalized.get("name"),
                "address_1": normalized.get("address_1") or normalized.get("address1"),
                "address_2": normalized.get("address_2") or normalized.get("address2"),
                "city": normalized.get("city"),
                "region": normalized.get("region") or normalized.get("state"),
                "postal_code": normalized.get("postal_code") or normalized.get("zip"),
                "country": normalized.get("country"),
                "phone": normalized.get("phone"),
                "organization_id": normalized.get("organization_id") or normalized.get("organization"),
            }
            locations.append(location)

        return locations

    def parse_passwords(self, path: Path) -> list[dict[str, Any]]:
        """Parse passwords.csv.

        Expected columns: id, name, username, password, url, notes,
        resource_type, resource_id, otp_secret

        Args:
            path: Path to passwords.csv.

        Returns:
            List of password dictionaries with fields:
            - id: IT Glue password ID
            - name: Password entry name
            - username: Username (optional)
            - password: Password value (optional)
            - url: URL (optional)
            - notes: Notes (optional)
            - resource_type: Linked resource type (optional)
            - resource_id: Linked resource ID (optional)
            - otp_secret: OTP/2FA secret (optional)
            - organization_id: Organization ID (optional)

        Raises:
            FileNotFoundError: If the file does not exist.
            ParseError: If the CSV cannot be parsed.
        """
        rows = self._read_csv(path)
        passwords = []

        for row in rows:
            normalized = self._normalize_row(row)
            pwd = {
                "id": normalized.get("id"),
                "name": normalized.get("name"),
                "username": normalized.get("username"),
                "password": normalized.get("password"),
                "url": normalized.get("url"),
                "notes": normalized.get("notes"),
                "resource_type": normalized.get("resource_type"),
                "resource_id": normalized.get("resource_id"),
                "otp_secret": normalized.get("otp_secret"),
                "organization_id": normalized.get("organization_id") or normalized.get("organization"),
                "archived": normalized.get("archived"),
            }
            passwords.append(pwd)

        return passwords

    def _detect_field_type(self, values: list[str | None]) -> FieldType:
        """Detect the field type from sample values.

        Uses heuristics to determine the most appropriate field type:
        - checkbox: if all values are boolean-like (true/false/yes/no/1/0)
        - number: if all values are numeric
        - date: if all values match date patterns
        - textbox: if any value contains newlines or is > 255 chars
        - text: default for short text values

        Args:
            values: List of sample values from the column.

        Returns:
            The detected field type.
        """
        # Filter to non-empty values
        non_empty = [v for v in values if v]

        if not non_empty:
            return "text"

        # Check for checkbox values
        if all(v.lower() in CHECKBOX_VALUES for v in non_empty):
            return "checkbox"

        # Check for numbers
        if all(NUMBER_PATTERN.match(v) for v in non_empty):
            return "number"

        # Check for dates
        if all(DATE_PATTERN.match(v) for v in non_empty):
            return "date"

        # Check for textbox (multiline or long text)
        if any("\n" in v or len(v) > 255 for v in non_empty):
            return "textbox"

        return "text"

    def _generate_field_definitions(
        self, headers: list[str], rows: list[dict[str, str]]
    ) -> list[FieldDefinition]:
        """Generate field definitions from CSV headers and data.

        Analyzes the data to detect field types and required status.

        Args:
            headers: List of CSV header names.
            rows: List of row dictionaries.

        Returns:
            List of FieldDefinition objects.
        """
        # Skip standard metadata columns
        skip_columns = {"id", "organization", "organization_id", "created_at", "updated_at"}

        definitions = []
        for header in headers:
            # Skip None or empty headers (can occur with malformed CSVs)
            if not header:
                continue

            # Skip metadata columns
            if header.lower() in skip_columns:
                continue

            # Collect values for this column
            values = [self._normalize_value(row.get(header)) for row in rows]
            non_empty_values = [v for v in values if v]

            # Detect field type
            field_type = self._detect_field_type(values)

            # Determine if required (all rows have values)
            required = len(non_empty_values) == len(rows) and len(rows) > 0

            # Collect sample values (up to 5 unique)
            sample_values = list(dict.fromkeys(v for v in non_empty_values[:20] if v))[:5]

            definitions.append(
                FieldDefinition(
                    name=header,
                    field_type=field_type,
                    required=required,
                    sample_values=sample_values,
                )
            )

        return definitions

    def parse_custom_asset_csv(
        self, path: Path, asset_type_name: str
    ) -> tuple[list[FieldDefinition], list[dict[str, Any]]]:
        """Parse a custom asset type CSV file.

        Custom asset CSVs contain an 'id' column, 'organization' column,
        and any number of custom field columns.

        Args:
            path: Path to the custom asset CSV file.
            asset_type_name: Name of the custom asset type.

        Returns:
            Tuple of (field_definitions, assets) where:
            - field_definitions: List of FieldDefinition objects
            - assets: List of asset dictionaries with fields:
              - id: IT Glue asset ID
              - organization_id: Organization ID
              - asset_type: The asset type name
              - fields: Dictionary of field name to value

        Raises:
            FileNotFoundError: If the file does not exist.
            ParseError: If the CSV cannot be parsed.
        """
        rows = self._read_csv(path)

        if not rows:
            return [], []

        # Get headers from first row's keys
        headers = list(rows[0].keys())

        # Generate field definitions
        field_definitions = self._generate_field_definitions(headers, rows)

        # Parse assets
        assets = []
        skip_columns = {"id", "organization", "organization_id", "created_at", "updated_at", "archived"}

        for row in rows:
            normalized = self._normalize_row(row)

            # Extract standard fields
            asset_id = normalized.get("id")
            org_id = normalized.get("organization_id") or normalized.get("organization")

            # Extract custom field values
            fields: dict[str, Any] = {}
            for header in headers:
                if header.lower() not in skip_columns:
                    fields[header] = normalized.get(header)

            asset = {
                "id": asset_id,
                "organization_id": org_id,
                "asset_type": asset_type_name,
                "fields": fields,
                "archived": normalized.get("archived"),
            }
            assets.append(asset)

        return field_definitions, assets

    def discover_custom_asset_types(self, export_path: Path) -> list[str]:
        """Discover custom asset type CSVs in an export directory.

        Scans the export directory for CSV files that are not core entity
        files, treating them as custom asset type exports.

        Args:
            export_path: Path to the IT Glue export directory.

        Returns:
            List of custom asset type names (derived from filenames).

        Raises:
            FileNotFoundError: If the export directory does not exist.
        """
        if not export_path.exists():
            raise FileNotFoundError(export_path)

        if not export_path.is_dir():
            raise ParseError(export_path, "Expected a directory, not a file")

        custom_types = []
        for csv_file in export_path.glob("*.csv"):
            filename = csv_file.name.lower()
            if filename not in CORE_ENTITY_FILES:
                # Derive asset type name from filename
                # e.g., "ssl-certificates.csv" -> "ssl-certificates"
                type_name = csv_file.stem
                custom_types.append(type_name)

        return sorted(custom_types)

    def get_row_count(self, path: Path) -> int:
        """Get the number of data rows in a CSV file.

        Args:
            path: Path to the CSV file.

        Returns:
            Number of data rows (excluding header).

        Raises:
            FileNotFoundError: If the file does not exist.
            ParseError: If the CSV cannot be parsed.
        """
        rows = self._read_csv(path)
        return len(rows)

    def validate_export_structure(self, export_path: Path) -> dict[str, Any]:
        """Validate the structure of an IT Glue export directory.

        Checks for expected core entity files and reports what's present.

        Args:
            export_path: Path to the IT Glue export directory.

        Returns:
            Dictionary with validation results:
            - valid: True if minimum required files are present
            - core_entities: Dict of entity name to presence/count
            - custom_asset_types: List of discovered custom asset types
            - errors: List of error messages

        Raises:
            FileNotFoundError: If the export directory does not exist.
        """
        if not export_path.exists():
            raise FileNotFoundError(export_path)

        if not export_path.is_dir():
            raise ParseError(export_path, "Expected a directory, not a file")

        errors: list[str] = []
        core_entities: dict[str, dict[str, Any]] = {}

        # Check for core entity files
        expected_files = {
            "organizations": "organizations.csv",
            "configurations": "configurations.csv",
            "documents": "documents.csv",
            "locations": "locations.csv",
            "passwords": "passwords.csv",
        }

        for entity_name, filename in expected_files.items():
            file_path = export_path / filename
            if file_path.exists():
                try:
                    row_count = self.get_row_count(file_path)
                    core_entities[entity_name] = {
                        "present": True,
                        "row_count": row_count,
                        "path": str(file_path),
                    }
                except CSVParserError as e:
                    core_entities[entity_name] = {
                        "present": True,
                        "error": str(e),
                    }
                    errors.append(f"Error reading {filename}: {e}")
            else:
                core_entities[entity_name] = {"present": False}

        # Discover custom asset types
        custom_types = self.discover_custom_asset_types(export_path)

        # Validate minimum requirements
        # At minimum, organizations should be present
        valid = core_entities.get("organizations", {}).get("present", False)

        return {
            "valid": valid,
            "core_entities": core_entities,
            "custom_asset_types": custom_types,
            "errors": errors,
        }
