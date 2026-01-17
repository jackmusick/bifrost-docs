"""Unit tests for the warnings detection module."""

from __future__ import annotations

import pytest

from itglue_migrate.warnings import (
    LARGE_DOCUMENT_THRESHOLD,
    ParsedData,
    Warning,
    WarningDetector,
    summarize,
)


@pytest.fixture
def detector() -> WarningDetector:
    """Create a WarningDetector instance."""
    return WarningDetector()


class TestWarningDataclass:
    """Test Warning dataclass."""

    def test_warning_creation_minimal(self) -> None:
        """Test creating a Warning with minimal fields."""
        warning = Warning(
            category="missing_reference",
            severity="warning",
            message="Test message",
        )

        assert warning.category == "missing_reference"
        assert warning.severity == "warning"
        assert warning.message == "Test message"
        assert warning.entity_type is None
        assert warning.entity_id is None
        assert warning.details is None

    def test_warning_creation_full(self) -> None:
        """Test creating a Warning with all fields."""
        warning = Warning(
            category="duplicate",
            severity="error",
            message="Duplicate found",
            entity_type="organization",
            entity_id="org-1",
            details={"count": 2},
        )

        assert warning.category == "duplicate"
        assert warning.severity == "error"
        assert warning.message == "Duplicate found"
        assert warning.entity_type == "organization"
        assert warning.entity_id == "org-1"
        assert warning.details == {"count": 2}

    def test_warning_to_dict_minimal(self) -> None:
        """Test converting Warning to dict with minimal fields."""
        warning = Warning(
            category="empty_value",
            severity="info",
            message="Empty field",
        )

        result = warning.to_dict()

        assert result == {
            "category": "empty_value",
            "severity": "info",
            "message": "Empty field",
        }
        assert "entity_type" not in result
        assert "entity_id" not in result
        assert "details" not in result

    def test_warning_to_dict_full(self) -> None:
        """Test converting Warning to dict with all fields."""
        warning = Warning(
            category="data_quality",
            severity="warning",
            message="Large document",
            entity_type="document",
            entity_id="doc-1",
            details={"size": 1000000},
        )

        result = warning.to_dict()

        assert result == {
            "category": "data_quality",
            "severity": "warning",
            "message": "Large document",
            "entity_type": "document",
            "entity_id": "doc-1",
            "details": {"size": 1000000},
        }


class TestParsedData:
    """Test ParsedData dataclass."""

    def test_parsed_data_empty(self) -> None:
        """Test creating empty ParsedData."""
        data = ParsedData()

        assert data.organizations == []
        assert data.configurations == []
        assert data.documents == []
        assert data.locations == []
        assert data.passwords == []
        assert data.custom_assets == {}
        assert data.field_definitions == {}

    def test_parsed_data_with_values(self) -> None:
        """Test creating ParsedData with values."""
        data = ParsedData(
            organizations=[{"id": "1", "name": "Acme"}],
            configurations=[{"id": "c1", "name": "Server"}],
            custom_assets={"ssl-certs": [{"id": "ssl-1"}]},
        )

        assert len(data.organizations) == 1
        assert len(data.configurations) == 1
        assert "ssl-certs" in data.custom_assets


class TestMissingReferences:
    """Test detection of missing references."""

    def test_password_references_existing_configuration(self, detector: WarningDetector) -> None:
        """Test that password referencing existing config produces no warning."""
        data = ParsedData(
            configurations=[{"id": "config-1", "name": "Server"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Server Password",
                    "resource_type": "Configuration",
                    "resource_id": "config-1",
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 0

    def test_password_references_missing_configuration(self, detector: WarningDetector) -> None:
        """Test that password referencing non-existent config produces warning."""
        data = ParsedData(
            configurations=[{"id": "config-1", "name": "Server"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Server Password",
                    "resource_type": "Configuration",
                    "resource_id": "config-999",  # Does not exist
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 1
        assert missing_ref_warnings[0].severity == "warning"
        assert missing_ref_warnings[0].entity_type == "password"
        assert missing_ref_warnings[0].entity_id == "pwd-1"
        assert "config-999" in missing_ref_warnings[0].message

    def test_password_references_existing_location(self, detector: WarningDetector) -> None:
        """Test that password referencing existing location produces no warning."""
        data = ParsedData(
            locations=[{"id": "loc-1", "name": "HQ"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Door Code",
                    "resource_type": "Location",
                    "resource_id": "loc-1",
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 0

    def test_password_references_missing_location(self, detector: WarningDetector) -> None:
        """Test that password referencing non-existent location produces warning."""
        data = ParsedData(
            locations=[{"id": "loc-1", "name": "HQ"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Door Code",
                    "resource_type": "Location",
                    "resource_id": "loc-999",
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 1
        assert "loc-999" in missing_ref_warnings[0].message

    def test_password_references_existing_organization(self, detector: WarningDetector) -> None:
        """Test that password referencing existing org produces no warning."""
        data = ParsedData(
            organizations=[{"id": "org-1", "name": "Acme"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Main Password",
                    "resource_type": "Organization",
                    "resource_id": "org-1",
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 0

    def test_password_references_existing_document(self, detector: WarningDetector) -> None:
        """Test that password referencing existing document produces no warning."""
        data = ParsedData(
            documents=[{"id": "doc-1", "name": "Runbook"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Doc Password",
                    "resource_type": "Document",
                    "resource_id": "doc-1",
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 0

    def test_password_references_existing_custom_asset(self, detector: WarningDetector) -> None:
        """Test that password referencing existing custom asset produces no warning."""
        data = ParsedData(
            custom_assets={"ssl-certificates": [{"id": "ssl-1", "fields": {"name": "Main SSL"}}]},
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "SSL Key",
                    "resource_type": "StructuredData::SSL Certificates",
                    "resource_id": "ssl-1",
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 0

    def test_password_references_missing_custom_asset(self, detector: WarningDetector) -> None:
        """Test that password referencing non-existent custom asset produces warning."""
        data = ParsedData(
            custom_assets={"ssl-certificates": [{"id": "ssl-1", "fields": {"name": "Main SSL"}}]},
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "SSL Key",
                    "resource_type": "StructuredData::SSL Certificates",
                    "resource_id": "ssl-999",
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 1
        assert "ssl-999" in missing_ref_warnings[0].message

    def test_password_without_resource_id_no_warning(self, detector: WarningDetector) -> None:
        """Test that password without resource_id produces no missing reference warning."""
        data = ParsedData(
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Standalone Password",
                    "password": "secret",
                    "resource_type": None,
                    "resource_id": None,
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 0

    def test_password_with_no_type_checks_all_entities(self, detector: WarningDetector) -> None:
        """Test password with resource_id but no type checks all entity types."""
        data = ParsedData(
            configurations=[{"id": "config-1", "name": "Server"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Password",
                    "resource_type": None,
                    "resource_id": "config-1",  # Exists in configurations
                }
            ],
        )

        warnings = detector.detect_all(data)

        missing_ref_warnings = [w for w in warnings if w.category == "missing_reference"]
        assert len(missing_ref_warnings) == 0


class TestUnknownTypes:
    """Test detection of unknown resource types."""

    def test_known_resource_type_no_warning(self, detector: WarningDetector) -> None:
        """Test that known resource types produce no warning."""
        data = ParsedData(
            configurations=[{"id": "config-1", "name": "Server"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Server Password",
                    "resource_type": "Configuration",
                    "resource_id": "config-1",
                }
            ],
        )

        warnings = detector.detect_all(data)

        unknown_type_warnings = [w for w in warnings if w.category == "unknown_type"]
        assert len(unknown_type_warnings) == 0

    def test_unknown_resource_type_warning(self, detector: WarningDetector) -> None:
        """Test that unknown resource types produce warning."""
        data = ParsedData(
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Password",
                    "resource_type": "UnknownType",
                    "resource_id": "some-id",
                }
            ],
        )

        warnings = detector.detect_all(data)

        unknown_type_warnings = [w for w in warnings if w.category == "unknown_type"]
        assert len(unknown_type_warnings) == 1
        assert unknown_type_warnings[0].severity == "info"
        assert "UnknownType" in unknown_type_warnings[0].message

    def test_structured_data_known_custom_type_no_warning(self, detector: WarningDetector) -> None:
        """Test StructuredData reference to known custom type produces no warning."""
        data = ParsedData(
            custom_assets={"ssl-certificates": [{"id": "ssl-1", "fields": {"name": "SSL"}}]},
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "SSL Password",
                    "resource_type": "StructuredData::SSL Certificates",
                    "resource_id": "ssl-1",
                }
            ],
        )

        warnings = detector.detect_all(data)

        unknown_type_warnings = [w for w in warnings if w.category == "unknown_type"]
        assert len(unknown_type_warnings) == 0

    def test_structured_data_unknown_custom_type_warning(self, detector: WarningDetector) -> None:
        """Test StructuredData reference to unknown custom type produces warning."""
        data = ParsedData(
            custom_assets={"ssl-certificates": [{"id": "ssl-1", "fields": {"name": "SSL"}}]},
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Password",
                    "resource_type": "StructuredData::Unknown Asset",
                    "resource_id": "some-id",
                }
            ],
        )

        warnings = detector.detect_all(data)

        unknown_type_warnings = [w for w in warnings if w.category == "unknown_type"]
        assert len(unknown_type_warnings) == 1
        assert "StructuredData::Unknown Asset" in unknown_type_warnings[0].message

    def test_no_resource_type_no_warning(self, detector: WarningDetector) -> None:
        """Test that null resource_type produces no unknown type warning."""
        data = ParsedData(
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Password",
                    "password": "secret",
                    "resource_type": None,
                    "resource_id": None,
                }
            ],
        )

        warnings = detector.detect_all(data)

        unknown_type_warnings = [w for w in warnings if w.category == "unknown_type"]
        assert len(unknown_type_warnings) == 0


class TestDuplicates:
    """Test detection of duplicate entries."""

    def test_unique_organization_names_no_warning(self, detector: WarningDetector) -> None:
        """Test that unique org names produce no warning."""
        data = ParsedData(
            organizations=[
                {"id": "1", "name": "Acme Corp"},
                {"id": "2", "name": "Beta Inc"},
                {"id": "3", "name": "Gamma LLC"},
            ],
        )

        warnings = detector.detect_all(data)

        duplicate_warnings = [w for w in warnings if w.category == "duplicate"]
        assert len(duplicate_warnings) == 0

    def test_duplicate_organization_names_warning(self, detector: WarningDetector) -> None:
        """Test that duplicate org names produce warning."""
        data = ParsedData(
            organizations=[
                {"id": "1", "name": "Acme Corp"},
                {"id": "2", "name": "Acme Corp"},  # Duplicate
                {"id": "3", "name": "Beta Inc"},
            ],
        )

        warnings = detector.detect_all(data)

        duplicate_warnings = [w for w in warnings if w.category == "duplicate"]
        assert len(duplicate_warnings) == 1
        assert duplicate_warnings[0].severity == "warning"
        assert duplicate_warnings[0].entity_type == "organization"
        assert "Acme Corp" in duplicate_warnings[0].message
        assert duplicate_warnings[0].details is not None
        assert duplicate_warnings[0].details["count"] == 2

    def test_duplicate_organization_names_case_insensitive(self, detector: WarningDetector) -> None:
        """Test that duplicate detection is case-insensitive."""
        data = ParsedData(
            organizations=[
                {"id": "1", "name": "Acme Corp"},
                {"id": "2", "name": "ACME CORP"},  # Same name, different case
            ],
        )

        warnings = detector.detect_all(data)

        duplicate_warnings = [w for w in warnings if w.category == "duplicate"]
        assert len(duplicate_warnings) == 1

    def test_unique_custom_assets_no_warning(self, detector: WarningDetector) -> None:
        """Test that unique custom asset names produce no warning."""
        data = ParsedData(
            custom_assets={
                "ssl-certificates": [
                    {"id": "ssl-1", "organization_id": "org-1", "fields": {"name": "Main SSL"}},
                    {"id": "ssl-2", "organization_id": "org-1", "fields": {"name": "API SSL"}},
                ]
            },
        )

        warnings = detector.detect_all(data)

        duplicate_warnings = [w for w in warnings if w.category == "duplicate"]
        assert len(duplicate_warnings) == 0

    def test_duplicate_custom_assets_different_org_no_warning(
        self, detector: WarningDetector
    ) -> None:
        """Test that duplicate custom asset names in different orgs produce no warning."""
        data = ParsedData(
            custom_assets={
                "ssl-certificates": [
                    {"id": "ssl-1", "organization_id": "org-1", "fields": {"name": "Main SSL"}},
                    {"id": "ssl-2", "organization_id": "org-2", "fields": {"name": "Main SSL"}},
                ]
            },
        )

        warnings = detector.detect_all(data)

        duplicate_warnings = [w for w in warnings if w.category == "duplicate"]
        assert len(duplicate_warnings) == 0

    def test_three_duplicates_counted_correctly(self, detector: WarningDetector) -> None:
        """Test that three duplicates are counted correctly."""
        data = ParsedData(
            organizations=[
                {"id": "1", "name": "Acme"},
                {"id": "2", "name": "Acme"},
                {"id": "3", "name": "Acme"},
            ],
        )

        warnings = detector.detect_all(data)

        duplicate_warnings = [w for w in warnings if w.category == "duplicate"]
        assert len(duplicate_warnings) == 1
        assert duplicate_warnings[0].details is not None
        assert duplicate_warnings[0].details["count"] == 3
        assert len(duplicate_warnings[0].details["duplicate_ids"]) == 3


class TestEmptyValues:
    """Test detection of empty/missing required values."""

    def test_password_with_value_no_warning(self, detector: WarningDetector) -> None:
        """Test that password with value produces no warning."""
        data = ParsedData(
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Server Password",
                    "password": "secret123",
                }
            ],
        )

        warnings = detector.detect_all(data)

        empty_value_warnings = [w for w in warnings if w.category == "empty_value"]
        assert len(empty_value_warnings) == 0

    def test_password_empty_field_warning(self, detector: WarningDetector) -> None:
        """Test that empty password field produces warning."""
        data = ParsedData(
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Server Password",
                    "password": "",  # Empty
                }
            ],
        )

        warnings = detector.detect_all(data)

        empty_value_warnings = [w for w in warnings if w.category == "empty_value"]
        assert len(empty_value_warnings) == 1
        assert empty_value_warnings[0].severity == "info"
        assert empty_value_warnings[0].entity_type == "password"
        assert "empty password field" in empty_value_warnings[0].message

    def test_password_none_field_warning(self, detector: WarningDetector) -> None:
        """Test that None password field produces warning."""
        data = ParsedData(
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Server Password",
                    "password": None,
                }
            ],
        )

        warnings = detector.detect_all(data)

        empty_value_warnings = [w for w in warnings if w.category == "empty_value"]
        assert len(empty_value_warnings) == 1

    def test_organization_with_name_no_warning(self, detector: WarningDetector) -> None:
        """Test that organization with name produces no warning."""
        data = ParsedData(
            organizations=[{"id": "1", "name": "Acme Corp"}],
        )

        warnings = detector.detect_all(data)

        empty_value_warnings = [w for w in warnings if w.category == "empty_value"]
        assert len(empty_value_warnings) == 0

    def test_organization_empty_name_error(self, detector: WarningDetector) -> None:
        """Test that organization with empty name produces error."""
        data = ParsedData(
            organizations=[{"id": "1", "name": ""}],
        )

        warnings = detector.detect_all(data)

        empty_value_warnings = [w for w in warnings if w.category == "empty_value"]
        assert len(empty_value_warnings) == 1
        assert empty_value_warnings[0].severity == "error"
        assert empty_value_warnings[0].entity_type == "organization"
        assert "empty name" in empty_value_warnings[0].message

    def test_organization_none_name_error(self, detector: WarningDetector) -> None:
        """Test that organization with None name produces error."""
        data = ParsedData(
            organizations=[{"id": "1", "name": None}],
        )

        warnings = detector.detect_all(data)

        empty_value_warnings = [w for w in warnings if w.category == "empty_value"]
        assert len(empty_value_warnings) == 1
        assert empty_value_warnings[0].severity == "error"

    def test_configuration_with_name_no_warning(self, detector: WarningDetector) -> None:
        """Test that configuration with name produces no warning."""
        data = ParsedData(
            configurations=[{"id": "1", "name": "Server-01"}],
        )

        warnings = detector.detect_all(data)

        empty_value_warnings = [w for w in warnings if w.category == "empty_value"]
        assert len(empty_value_warnings) == 0

    def test_configuration_empty_name_error(self, detector: WarningDetector) -> None:
        """Test that configuration with empty name produces error."""
        data = ParsedData(
            configurations=[{"id": "1", "name": ""}],
        )

        warnings = detector.detect_all(data)

        empty_value_warnings = [w for w in warnings if w.category == "empty_value"]
        assert len(empty_value_warnings) == 1
        assert empty_value_warnings[0].severity == "error"
        assert empty_value_warnings[0].entity_type == "configuration"


class TestDataQuality:
    """Test detection of data quality issues."""

    def test_normal_document_no_warning(self, detector: WarningDetector) -> None:
        """Test that normal-sized document produces no warning."""
        data = ParsedData(
            documents=[
                {
                    "id": "doc-1",
                    "name": "Runbook",
                    "content": "Normal sized content" * 100,
                }
            ],
        )

        warnings = detector.detect_all(data)

        quality_warnings = [w for w in warnings if w.category == "data_quality"]
        assert len(quality_warnings) == 0

    def test_large_document_warning(self, detector: WarningDetector) -> None:
        """Test that large document (>1MB) produces warning."""
        # Create content larger than 1MB
        large_content = "X" * (LARGE_DOCUMENT_THRESHOLD + 1000)
        data = ParsedData(
            documents=[
                {
                    "id": "doc-1",
                    "name": "Large Document",
                    "content": large_content,
                }
            ],
        )

        warnings = detector.detect_all(data)

        quality_warnings = [w for w in warnings if w.category == "data_quality"]
        assert len(quality_warnings) == 1
        assert quality_warnings[0].severity == "warning"
        assert quality_warnings[0].entity_type == "document"
        assert "large content" in quality_warnings[0].message.lower()
        assert quality_warnings[0].details is not None
        assert quality_warnings[0].details["content_size_bytes"] > LARGE_DOCUMENT_THRESHOLD

    def test_document_without_content_no_warning(self, detector: WarningDetector) -> None:
        """Test that document without content produces no warning."""
        data = ParsedData(
            documents=[
                {
                    "id": "doc-1",
                    "name": "Runbook",
                    "content": None,
                }
            ],
        )

        warnings = detector.detect_all(data)

        quality_warnings = [w for w in warnings if w.category == "data_quality"]
        assert len(quality_warnings) == 0

    def test_custom_asset_all_required_fields_filled_no_warning(
        self, detector: WarningDetector
    ) -> None:
        """Test that custom asset with all required fields filled produces no warning."""
        data = ParsedData(
            custom_assets={
                "ssl-certificates": [
                    {
                        "id": "ssl-1",
                        "organization_id": "org-1",
                        "fields": {
                            "name": "Main SSL",
                            "expiry_date": "2024-12-31",
                            "issuer": "DigiCert",
                        },
                    }
                ]
            },
            field_definitions={
                "ssl-certificates": [
                    {"name": "name", "required": True},
                    {"name": "expiry_date", "required": True},
                    {"name": "issuer", "required": True},
                ]
            },
        )

        warnings = detector.detect_all(data)

        quality_warnings = [w for w in warnings if w.category == "data_quality"]
        assert len(quality_warnings) == 0

    def test_custom_asset_many_empty_required_fields_warning(
        self, detector: WarningDetector
    ) -> None:
        """Test that custom asset with many empty required fields produces warning."""
        data = ParsedData(
            custom_assets={
                "ssl-certificates": [
                    {
                        "id": "ssl-1",
                        "organization_id": "org-1",
                        "fields": {
                            "name": "Main SSL",
                            "expiry_date": None,  # Empty required field
                            "issuer": None,  # Empty required field
                            "domain": "",  # Empty required field
                        },
                    }
                ]
            },
            field_definitions={
                "ssl-certificates": [
                    {"name": "name", "required": True},
                    {"name": "expiry_date", "required": True},
                    {"name": "issuer", "required": True},
                    {"name": "domain", "required": True},
                ]
            },
        )

        warnings = detector.detect_all(data)

        quality_warnings = [w for w in warnings if w.category == "data_quality"]
        assert len(quality_warnings) == 1
        assert quality_warnings[0].severity == "info"
        assert quality_warnings[0].details is not None
        assert len(quality_warnings[0].details["empty_required_fields"]) == 3

    def test_custom_asset_one_empty_required_field_no_warning(
        self, detector: WarningDetector
    ) -> None:
        """Test that custom asset with just one empty required field produces no warning."""
        data = ParsedData(
            custom_assets={
                "ssl-certificates": [
                    {
                        "id": "ssl-1",
                        "organization_id": "org-1",
                        "fields": {
                            "name": "Main SSL",
                            "expiry_date": "2024-12-31",
                            "issuer": None,  # One empty field
                        },
                    }
                ]
            },
            field_definitions={
                "ssl-certificates": [
                    {"name": "name", "required": True},
                    {"name": "expiry_date", "required": True},
                    {"name": "issuer", "required": True},
                ]
            },
        )

        warnings = detector.detect_all(data)

        quality_warnings = [w for w in warnings if w.category == "data_quality"]
        # One empty field out of 3 is not "many" (less than half)
        assert len(quality_warnings) == 0


class TestDetectAll:
    """Test the detect_all method combining all checks."""

    def test_detect_all_empty_data(self, detector: WarningDetector) -> None:
        """Test detect_all with empty data produces no warnings."""
        data = ParsedData()

        warnings = detector.detect_all(data)

        assert warnings == []

    def test_detect_all_clean_data(self, detector: WarningDetector) -> None:
        """Test detect_all with clean data produces no warnings."""
        data = ParsedData(
            organizations=[{"id": "org-1", "name": "Acme Corp"}],
            configurations=[{"id": "config-1", "name": "Server-01"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Server Password",
                    "password": "secret123",
                    "resource_type": "Configuration",
                    "resource_id": "config-1",
                }
            ],
        )

        warnings = detector.detect_all(data)

        assert warnings == []

    def test_detect_all_multiple_issues(self, detector: WarningDetector) -> None:
        """Test detect_all finds multiple issues of different types."""
        data = ParsedData(
            organizations=[
                {"id": "org-1", "name": ""},  # Empty name
                {"id": "org-2", "name": "Acme"},
                {"id": "org-3", "name": "Acme"},  # Duplicate
            ],
            configurations=[{"id": "config-1", "name": "Server"}],
            passwords=[
                {
                    "id": "pwd-1",
                    "name": "Password",
                    "password": "",  # Empty password
                    "resource_type": "Configuration",
                    "resource_id": "config-999",  # Missing reference
                },
                {
                    "id": "pwd-2",
                    "name": "Another",
                    "password": "secret",
                    "resource_type": "UnknownType",  # Unknown type
                    "resource_id": "x",
                },
            ],
        )

        warnings = detector.detect_all(data)

        # Verify we got warnings from multiple categories
        categories = {w.category for w in warnings}
        assert "empty_value" in categories
        assert "duplicate" in categories
        assert "missing_reference" in categories
        assert "unknown_type" in categories


class TestSummarize:
    """Test the summarize function."""

    def test_summarize_empty_list(self) -> None:
        """Test summarizing empty warning list."""
        result = summarize([])

        assert result["total"] == 0
        assert result["by_severity"]["info"] == 0
        assert result["by_severity"]["warning"] == 0
        assert result["by_severity"]["error"] == 0
        assert result["by_category"] == {}
        assert result["errors"] == 0
        assert result["has_blockers"] is False

    def test_summarize_single_warning(self) -> None:
        """Test summarizing single warning."""
        warnings = [
            Warning(
                category="missing_reference",
                severity="warning",
                message="Test warning",
            )
        ]

        result = summarize(warnings)

        assert result["total"] == 1
        assert result["by_severity"]["warning"] == 1
        assert result["by_severity"]["error"] == 0
        assert result["by_category"]["missing_reference"] == 1
        assert result["errors"] == 0
        assert result["has_blockers"] is False

    def test_summarize_multiple_warnings(self) -> None:
        """Test summarizing multiple warnings."""
        warnings = [
            Warning(category="missing_reference", severity="warning", message="W1"),
            Warning(category="missing_reference", severity="warning", message="W2"),
            Warning(category="duplicate", severity="warning", message="W3"),
            Warning(category="empty_value", severity="error", message="E1"),
            Warning(category="data_quality", severity="info", message="I1"),
        ]

        result = summarize(warnings)

        assert result["total"] == 5
        assert result["by_severity"]["info"] == 1
        assert result["by_severity"]["warning"] == 3
        assert result["by_severity"]["error"] == 1
        assert result["by_category"]["missing_reference"] == 2
        assert result["by_category"]["duplicate"] == 1
        assert result["by_category"]["empty_value"] == 1
        assert result["by_category"]["data_quality"] == 1
        assert result["errors"] == 1
        assert result["has_blockers"] is True

    def test_summarize_no_errors(self) -> None:
        """Test summarize with no errors."""
        warnings = [
            Warning(category="duplicate", severity="warning", message="W1"),
            Warning(category="data_quality", severity="info", message="I1"),
        ]

        result = summarize(warnings)

        assert result["errors"] == 0
        assert result["has_blockers"] is False

    def test_summarize_multiple_errors(self) -> None:
        """Test summarize with multiple errors."""
        warnings = [
            Warning(category="empty_value", severity="error", message="E1"),
            Warning(category="empty_value", severity="error", message="E2"),
            Warning(category="empty_value", severity="error", message="E3"),
        ]

        result = summarize(warnings)

        assert result["errors"] == 3
        assert result["has_blockers"] is True
