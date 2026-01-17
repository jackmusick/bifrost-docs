"""Unit tests for IT Glue importer utility functions."""

from itglue_migrate.importers import (
    format_location_notes_html,
    map_archived_to_is_enabled,
    map_org_status_to_is_enabled,
)


class TestMapArchivedToIsEnabled:
    """Tests for map_archived_to_is_enabled function."""

    def test_yes_returns_false(self) -> None:
        """Test that 'Yes' returns False."""
        assert map_archived_to_is_enabled("Yes") is False

    def test_yes_case_insensitive(self) -> None:
        """Test that 'yes' (lowercase) returns False."""
        assert map_archived_to_is_enabled("yes") is False
        assert map_archived_to_is_enabled("YES") is False
        assert map_archived_to_is_enabled("YeS") is False

    def test_no_returns_true(self) -> None:
        """Test that 'No' returns True."""
        assert map_archived_to_is_enabled("No") is True

    def test_no_case_insensitive(self) -> None:
        """Test that 'no' (lowercase) returns True."""
        assert map_archived_to_is_enabled("no") is True
        assert map_archived_to_is_enabled("NO") is True

    def test_none_returns_true(self) -> None:
        """Test that None returns True (default to enabled)."""
        assert map_archived_to_is_enabled(None) is True

    def test_empty_string_returns_true(self) -> None:
        """Test that empty string returns True (default to enabled)."""
        assert map_archived_to_is_enabled("") is True

    def test_whitespace_returns_true(self) -> None:
        """Test that whitespace string returns True (default to enabled)."""
        assert map_archived_to_is_enabled("   ") is True

    def test_other_values_return_true(self) -> None:
        """Test that other values return True."""
        assert map_archived_to_is_enabled("Maybe") is True
        assert map_archived_to_is_enabled("Unknown") is True
        assert map_archived_to_is_enabled("Archive") is True


class TestMapOrgStatusToIsEnabled:
    """Tests for map_org_status_to_is_enabled function."""

    def test_active_returns_true(self) -> None:
        """Test that 'Active' returns True."""
        assert map_org_status_to_is_enabled("Active") is True

    def test_active_case_insensitive(self) -> None:
        """Test that 'active' (lowercase) returns True."""
        assert map_org_status_to_is_enabled("active") is True
        assert map_org_status_to_is_enabled("ACTIVE") is True
        assert map_org_status_to_is_enabled("AcTiVe") is True

    def test_inactive_returns_false(self) -> None:
        """Test that 'Inactive' returns False."""
        assert map_org_status_to_is_enabled("Inactive") is False

    def test_none_returns_true(self) -> None:
        """Test that None returns True (default to enabled)."""
        assert map_org_status_to_is_enabled(None) is True

    def test_empty_string_returns_true(self) -> None:
        """Test that empty string returns True (default to enabled)."""
        assert map_org_status_to_is_enabled("") is True

    def test_other_statuses_return_false(self) -> None:
        """Test that other statuses return False."""
        assert map_org_status_to_is_enabled("Suspended") is False
        assert map_org_status_to_is_enabled("Pending") is False
        assert map_org_status_to_is_enabled("Closed") is False
        assert map_org_status_to_is_enabled("On Hold") is False


class TestFormatLocationNotesHtml:
    """Tests for format_location_notes_html function."""

    def test_full_address(self) -> None:
        """Test formatting a complete address."""
        row = {
            "address_1": "123 Main St",
            "address_2": "Suite 100",
            "city": "Springfield",
            "region": "IL",
            "country": "USA",
            "postal_code": "62701",
        }
        result = format_location_notes_html(row)
        expected = (
            "<strong>Address 1:</strong> 123 Main St<br>"
            "<strong>Address 2:</strong> Suite 100<br>"
            "<strong>City:</strong> Springfield<br>"
            "<strong>Region:</strong> IL<br>"
            "<strong>Country:</strong> USA<br>"
            "<strong>Postal Code:</strong> 62701"
        )
        assert result == expected

    def test_partial_address(self) -> None:
        """Test formatting a partial address with some fields missing."""
        row = {
            "address_1": "456 Oak Ave",
            "city": "Shelbyville",
            "region": "IL",
        }
        result = format_location_notes_html(row)
        expected = (
            "<strong>Address 1:</strong> 456 Oak Ave<br>"
            "<strong>City:</strong> Shelbyville<br>"
            "<strong>Region:</strong> IL"
        )
        assert result == expected

    def test_only_address_1(self) -> None:
        """Test formatting with only address_1 field."""
        row = {"address_1": "789 Pine Rd"}
        result = format_location_notes_html(row)
        expected = "<strong>Address 1:</strong> 789 Pine Rd"
        assert result == expected

    def test_empty_row(self) -> None:
        """Test formatting with no address fields."""
        row = {}
        result = format_location_notes_html(row)
        assert result == ""

    def test_none_values(self) -> None:
        """Test formatting with None values."""
        row = {
            "address_1": None,
            "city": None,
            "region": "IL",
        }
        result = format_location_notes_html(row)
        expected = "<strong>Region:</strong> IL"
        assert result == expected

    def test_empty_string_values(self) -> None:
        """Test formatting with empty string values."""
        row = {
            "address_1": "",
            "city": "Capital City",
            "region": "",
        }
        result = format_location_notes_html(row)
        expected = "<strong>City:</strong> Capital City"
        assert result == expected

    def test_special_characters(self) -> None:
        """Test formatting with special characters in values."""
        row = {
            "address_1": "123 Main St (Building A)",
            "city": "O'Connor's Village",
            "region": "IL",
        }
        result = format_location_notes_html(row)
        expected = (
            "<strong>Address 1:</strong> 123 Main St (Building A)<br>"
            "<strong>City:</strong> O'Connor's Village<br>"
            "<strong>Region:</strong> IL"
        )
        assert result == expected

    def test_unicode_characters(self) -> None:
        """Test formatting with Unicode characters."""
        row = {
            "address_1": "Straße 123",
            "city": "München",
            "region": "Bayern",
            "country": "Deutschland",
        }
        result = format_location_notes_html(row)
        expected = (
            "<strong>Address 1:</strong> Straße 123<br>"
            "<strong>City:</strong> München<br>"
            "<strong>Region:</strong> Bayern<br>"
            "<strong>Country:</strong> Deutschland"
        )
        assert result == expected
