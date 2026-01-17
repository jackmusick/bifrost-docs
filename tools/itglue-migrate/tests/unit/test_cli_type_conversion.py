"""Unit tests for CLI type conversion functions."""

from __future__ import annotations

from itglue_migrate.cli import _build_field_type_map, _convert_field_value


class TestConvertFieldValue:
    """Test the _convert_field_value function."""

    def test_checkbox_true_values(self) -> None:
        """Test conversion of various checkbox true values."""
        true_values = ["true", "TRUE", "True", "yes", "YES", "Yes", "1", "on", "ON", "enabled", "ENABLED"]
        for value in true_values:
            result = _convert_field_value(value, "checkbox")
            assert result is True, f"Expected True for '{value}'"

    def test_checkbox_false_values(self) -> None:
        """Test conversion of various checkbox false values."""
        false_values = ["false", "FALSE", "False", "no", "NO", "No", "0", "off", "OFF", "disabled", "DISABLED"]
        for value in false_values:
            result = _convert_field_value(value, "checkbox")
            assert result is False, f"Expected False for '{value}'"

    def test_checkbox_unknown_value_defaults_to_false(self) -> None:
        """Test that unrecognized checkbox values default to False."""
        result = _convert_field_value("maybe", "checkbox")
        assert result is False

        result = _convert_field_value("", "checkbox")
        assert result is False

    def test_number_integer_values(self) -> None:
        """Test conversion of integer values."""
        assert _convert_field_value("123", "number") == 123
        assert _convert_field_value("0", "number") == 0
        assert _convert_field_value("-456", "number") == -456

    def test_number_float_values(self) -> None:
        """Test conversion of float values."""
        assert _convert_field_value("123.45", "number") == 123.45
        assert _convert_field_value("0.0", "number") == 0.0
        assert _convert_field_value("-789.12", "number") == -789.12

    def test_number_float_with_integer_value(self) -> None:
        """Test that float values that are whole numbers are converted to int."""
        assert _convert_field_value("6.00", "number") == 6
        assert _convert_field_value("1024.00", "number") == 1024
        assert _convert_field_value("100.0", "number") == 100

    def test_number_invalid_value_returns_string(self) -> None:
        """Test that invalid number values are returned as-is."""
        result = _convert_field_value("not_a_number", "number")
        assert result == "not_a_number"

        result = _convert_field_value("", "number")
        assert result == ""

    def test_text_values_return_as_is(self) -> None:
        """Test that text, textbox, date, select values are returned as-is."""
        text_types = ["text", "textbox", "date", "select"]
        for field_type in text_types:
            result = _convert_field_value("some value", field_type)
            assert result == "some value"

            result = _convert_field_value("", field_type)
            assert result == ""


class TestBuildFieldTypeMap:
    """Test the _build_field_type_map function."""

    def test_build_empty_schema(self) -> None:
        """Test building field type map from empty schema."""
        schema: dict = {}
        result = _build_field_type_map(schema)
        assert result == {}

    def test_build_schema_without_fields(self) -> None:
        """Test building field type map from schema without fields."""
        schema = {"display_name": "Test Type", "count": 5}
        result = _build_field_type_map(schema)
        assert result == {}

    def test_build_schema_with_fields(self) -> None:
        """Test building field type map from schema with fields."""
        schema = {
            "display_name": "Test Type",
            "fields": [
                {"key": "domain", "name": "Domain", "type": "text"},
                {"key": "archived", "name": "Archived", "type": "checkbox"},
                {"key": "quantity", "name": "Quantity", "type": "number"},
                {"key": "expiry", "name": "Expiry Date", "type": "date"},
            ],
        }
        result = _build_field_type_map(schema)

        assert result == {
            "domain": "text",
            "archived": "checkbox",
            "quantity": "number",
            "expiry": "date",
        }

    def test_build_schema_ignores_fields_without_key(self) -> None:
        """Test that fields without a key are ignored."""
        schema = {
            "fields": [
                {"key": "valid_field", "name": "Valid", "type": "text"},
                {"name": "No Key", "type": "checkbox"},  # No key
                {"key": "", "name": "Empty Key", "type": "number"},  # Empty key
            ],
        }
        result = _build_field_type_map(schema)

        assert result == {"valid_field": "text"}
        assert "no_key" not in result

    def test_build_schema_defaults_to_text(self) -> None:
        """Test that fields without type default to 'text'."""
        schema = {
            "fields": [
                {"key": "typed", "name": "Typed", "type": "checkbox"},
                {"key": "untyped", "name": "Untyped"},  # No type
            ],
        }
        result = _build_field_type_map(schema)

        assert result == {
            "typed": "checkbox",
            "untyped": "text",
        }
