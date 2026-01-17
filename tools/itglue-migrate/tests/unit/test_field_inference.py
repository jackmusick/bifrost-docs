"""Unit tests for field inference module."""

from itglue_migrate.field_inference import (
    BOOLEAN_VALUES,
    FieldInferrer,
    column_name_to_key,
)


class TestColumnNameToKey:
    """Tests for column_name_to_key function."""

    def test_basic_conversion(self) -> None:
        """Basic column names convert to snake_case."""
        assert column_name_to_key("Common Name") == "common_name"
        assert column_name_to_key("Status") == "status"
        assert column_name_to_key("IP Address") == "ip_address"

    def test_special_characters_removed(self) -> None:
        """Special characters are removed or converted."""
        assert column_name_to_key("SSL/TLS Version") == "ssl_tls_version"
        assert column_name_to_key("User's Email Address") == "users_email_address"
        assert column_name_to_key("Price ($)") == "price"
        assert column_name_to_key("Date & Time") == "date_time"

    def test_whitespace_handling(self) -> None:
        """Whitespace is properly normalized."""
        assert column_name_to_key("  Multiple   Spaces  ") == "multiple_spaces"
        assert column_name_to_key("\tTabbed\tName\t") == "tabbed_name"
        assert column_name_to_key("  Leading Space") == "leading_space"
        assert column_name_to_key("Trailing Space  ") == "trailing_space"

    def test_hyphen_handling(self) -> None:
        """Hyphens are converted to underscores."""
        assert column_name_to_key("First-Name") == "first_name"
        assert column_name_to_key("created-at") == "created_at"
        assert column_name_to_key("end-to-end") == "end_to_end"

    def test_backslash_handling(self) -> None:
        """Backslashes are converted properly."""
        assert column_name_to_key("Domain\\User") == "domain_user"

    def test_numeric_names(self) -> None:
        """Names with numbers are handled correctly."""
        assert column_name_to_key("Field 1") == "field_1"
        assert column_name_to_key("IPv4 Address") == "ipv4_address"
        assert column_name_to_key("2FA Code") == "2fa_code"

    def test_already_snake_case(self) -> None:
        """Already snake_case names are preserved."""
        assert column_name_to_key("already_snake_case") == "already_snake_case"
        assert column_name_to_key("snake_case_name") == "snake_case_name"

    def test_uppercase_conversion(self) -> None:
        """Uppercase is converted to lowercase."""
        assert column_name_to_key("ALL CAPS") == "all_caps"
        assert column_name_to_key("MixedCase") == "mixedcase"
        assert column_name_to_key("UPPER_CASE") == "upper_case"

    def test_empty_string(self) -> None:
        """Empty string returns 'field'."""
        assert column_name_to_key("") == "field"
        assert column_name_to_key("   ") == "field"

    def test_special_only_characters(self) -> None:
        """String with only special characters returns 'field'."""
        assert column_name_to_key("!@#$%") == "field"
        assert column_name_to_key("---") == "field"

    def test_consecutive_underscores_collapsed(self) -> None:
        """Multiple underscores are collapsed."""
        assert column_name_to_key("Name__Value") == "name_value"
        assert column_name_to_key("a / / b") == "a_b"


class TestFieldInferrerPasswordType:
    """Tests for password field type inference."""

    def test_password_column_name(self) -> None:
        """Columns with 'password' in name infer as password."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Password", ["abc123", "def456"])
        assert field["type"] == "password"

        field = inferrer.infer_type("Admin Password", ["secret1", "secret2"])
        assert field["type"] == "password"

        field = inferrer.infer_type("password_hash", ["hash1", "hash2"])
        assert field["type"] == "password"

    def test_secret_column_name(self) -> None:
        """Columns with 'secret' in name infer as password."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("API Secret", ["abc123", "def456"])
        assert field["type"] == "password"

        field = inferrer.infer_type("client_secret", ["secret1"])
        assert field["type"] == "password"

    def test_key_column_name(self) -> None:
        """Columns with 'key' in name infer as password."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("API Key", ["key123", "key456"])
        assert field["type"] == "password"

        field = inferrer.infer_type("access_key", ["key1"])
        assert field["type"] == "password"

    def test_credential_column_name(self) -> None:
        """Columns with 'credential' in name infer as password."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Credentials", ["cred1", "cred2"])
        assert field["type"] == "password"

    def test_token_column_name(self) -> None:
        """Columns with 'token' in name infer as password."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Auth Token", ["token123"])
        assert field["type"] == "password"

        field = inferrer.infer_type("bearer_token", ["abc"])
        assert field["type"] == "password"

    def test_case_insensitive_password_detection(self) -> None:
        """Password pattern matching is case insensitive."""
        inferrer = FieldInferrer()

        assert inferrer.infer_type("PASSWORD", ["x"])["type"] == "password"
        assert inferrer.infer_type("Secret", ["x"])["type"] == "password"
        assert inferrer.infer_type("API_KEY", ["x"])["type"] == "password"


class TestFieldInferrerTOTPType:
    """Tests for TOTP field type inference."""

    def test_totp_column_name(self) -> None:
        """Columns with 'totp' in name infer as totp."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("TOTP Secret", ["ABC123"])
        assert field["type"] == "totp"

        field = inferrer.infer_type("totp_seed", ["seed"])
        assert field["type"] == "totp"

    def test_otp_column_name(self) -> None:
        """Columns with 'otp' in name infer as totp."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("OTP Code", ["123456"])
        assert field["type"] == "totp"

    def test_mfa_column_name(self) -> None:
        """Columns with 'mfa' in name infer as totp."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("MFA Secret", ["secret"])
        assert field["type"] == "totp"

    def test_2fa_column_name(self) -> None:
        """Columns with '2fa' in name infer as totp."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("2FA Code", ["code"])
        assert field["type"] == "totp"

    def test_two_factor_column_name(self) -> None:
        """Columns with 'two factor' in name infer as totp."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Two Factor Secret", ["secret"])
        assert field["type"] == "totp"

        field = inferrer.infer_type("Two-Factor Auth", ["auth"])
        assert field["type"] == "totp"


class TestFieldInferrerNumberType:
    """Tests for number field type inference."""

    def test_integer_values(self) -> None:
        """All integer values infer as number."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Count", ["1", "2", "3", "100"])
        assert field["type"] == "number"

    def test_float_values(self) -> None:
        """All float values infer as number."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Price", ["1.99", "2.50", "10.00"])
        assert field["type"] == "number"

    def test_mixed_int_float(self) -> None:
        """Mixed integers and floats infer as number."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Value", ["1", "2.5", "3", "4.75"])
        assert field["type"] == "number"

    def test_negative_numbers(self) -> None:
        """Negative numbers are recognized."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Delta", ["-1", "0", "1", "-2.5"])
        assert field["type"] == "number"

    def test_scientific_notation(self) -> None:
        """Scientific notation is recognized as number."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Scientific", ["1e10", "2.5e-3", "1E5"])
        assert field["type"] == "number"

    def test_empty_values_ignored(self) -> None:
        """Empty values are ignored when inferring number."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Count", ["1", None, "2", "", "3"])
        assert field["type"] == "number"

    def test_mixed_text_not_number(self) -> None:
        """Mixed text and numbers do not infer as number."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Mixed", ["1", "two", "3"])
        assert field["type"] != "number"


class TestFieldInferrerDateType:
    """Tests for date field type inference."""

    def test_iso_date_format(self) -> None:
        """ISO date format (YYYY-MM-DD) infers as date."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Created", ["2024-01-15", "2024-02-20"])
        assert field["type"] == "date"

    def test_us_date_format(self) -> None:
        """US date format (MM/DD/YYYY) infers as date."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Date", ["01/15/2024", "12/31/2023"])
        assert field["type"] == "date"

    def test_iso_datetime_format(self) -> None:
        """ISO datetime format infers as date."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Timestamp", ["2024-01-15T10:30:00", "2024-02-20T14:45:30"])
        assert field["type"] == "date"

    def test_slash_date_format(self) -> None:
        """YYYY/MM/DD format infers as date."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Date", ["2024/01/15", "2024/02/20"])
        assert field["type"] == "date"

    def test_hyphen_dmy_format(self) -> None:
        """DD-MM-YYYY format infers as date."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Date", ["15-01-2024", "20-02-2024"])
        assert field["type"] == "date"

    def test_empty_values_ignored(self) -> None:
        """Empty values are ignored when inferring date."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Date", ["2024-01-15", None, "", "2024-02-20"])
        assert field["type"] == "date"

    def test_mixed_formats_not_date(self) -> None:
        """Mixed date and non-date values do not infer as date."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Date", ["2024-01-15", "not a date", "2024-02-20"])
        assert field["type"] != "date"


class TestFieldInferrerCheckboxType:
    """Tests for checkbox/boolean field type inference."""

    def test_true_false_values(self) -> None:
        """True/false values infer as checkbox."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Enabled", ["true", "false", "true"])
        assert field["type"] == "checkbox"

    def test_yes_no_values(self) -> None:
        """Yes/no values infer as checkbox."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Active", ["yes", "no", "yes"])
        assert field["type"] == "checkbox"

    def test_one_zero_values(self) -> None:
        """1/0 values infer as checkbox."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Flag", ["1", "0", "1", "0"])
        assert field["type"] == "checkbox"

    def test_on_off_values(self) -> None:
        """On/off values infer as checkbox."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Status", ["on", "off", "on"])
        assert field["type"] == "checkbox"

    def test_enabled_disabled_values(self) -> None:
        """Enabled/disabled values infer as checkbox."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("State", ["enabled", "disabled"])
        assert field["type"] == "checkbox"

    def test_mixed_boolean_formats(self) -> None:
        """Mixed boolean formats still infer as checkbox."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Mixed", ["true", "0", "yes", "off"])
        assert field["type"] == "checkbox"

    def test_case_insensitive(self) -> None:
        """Boolean detection is case insensitive."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Case", ["TRUE", "False", "YES", "no"])
        assert field["type"] == "checkbox"

    def test_empty_values_ignored(self) -> None:
        """Empty values are ignored when inferring checkbox."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Flag", ["true", None, "", "false"])
        assert field["type"] == "checkbox"

    def test_all_boolean_values_covered(self) -> None:
        """Verify all expected boolean values are recognized."""
        inferrer = FieldInferrer()

        for value in BOOLEAN_VALUES:
            field = inferrer.infer_type("Test", [value])
            assert field["type"] == "checkbox", f"'{value}' should be recognized as boolean"


class TestFieldInferrerTextboxType:
    """Tests for textbox (multi-line) field type inference."""

    def test_newline_values(self) -> None:
        """Values with newlines infer as textbox."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Notes", ["Line 1\nLine 2", "Another\nNote"])
        assert field["type"] == "textbox"

    def test_long_values(self) -> None:
        """Values over 200 characters infer as textbox."""
        inferrer = FieldInferrer()

        long_text = "x" * 250
        field = inferrer.infer_type("Description", [long_text, "short"])
        assert field["type"] == "textbox"

    def test_most_values_long(self) -> None:
        """More than half long values infers as textbox."""
        inferrer = FieldInferrer()

        long_text = "x" * 250
        field = inferrer.infer_type("Notes", [long_text, long_text, "short"])
        assert field["type"] == "textbox"

    def test_minority_long_not_textbox(self) -> None:
        """Minority long values do not infer as textbox."""
        inferrer = FieldInferrer()

        long_text = "x" * 250
        field = inferrer.infer_type("Notes", ["short", "short", "short", long_text])
        assert field["type"] != "textbox"


class TestFieldInferrerSelectType:
    """Tests for select/dropdown field type inference."""

    def test_few_unique_values(self) -> None:
        """Few unique values with high frequency infer as select."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type(
            "Status", ["Active", "Active", "Inactive", "Active", "Inactive", "Active"]
        )
        assert field["type"] == "select"

    def test_select_options_extracted(self) -> None:
        """Select type includes options list."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type(
            "Status", ["Active", "Active", "Inactive", "Active", "Inactive", "Active"]
        )
        assert field["type"] == "select"
        assert "options" in field
        assert sorted(field["options"]) == ["Active", "Inactive"]

    def test_too_many_unique_values_not_select(self) -> None:
        """More than 10 unique values do not infer as select."""
        inferrer = FieldInferrer()

        values = [f"Value{i}" for i in range(15)]
        field = inferrer.infer_type("Category", values)
        assert field["type"] != "select"

    def test_low_frequency_not_select(self) -> None:
        """All unique values (low frequency) do not infer as select."""
        inferrer = FieldInferrer()

        values = ["A", "B", "C", "D", "E"]  # All unique
        field = inferrer.infer_type("Category", values)
        assert field["type"] != "select"

    def test_select_with_empty_values(self) -> None:
        """Select type handles empty values correctly."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type(
            "Status", ["Active", None, "Active", "", "Inactive", "Active"]
        )
        assert field["type"] == "select"
        assert "options" in field
        assert sorted(field["options"]) == ["Active", "Inactive"]


class TestFieldInferrerTextType:
    """Tests for default text field type inference."""

    def test_empty_values_default_to_text(self) -> None:
        """Empty or None values default to text."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Empty", [None, None, None])
        assert field["type"] == "text"

        field = inferrer.infer_type("Empty", ["", "", ""])
        assert field["type"] == "text"

    def test_all_empty_list(self) -> None:
        """Empty list defaults to text."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Empty", [])
        assert field["type"] == "text"

    def test_mixed_content_defaults_to_text(self) -> None:
        """Mixed non-matching content defaults to text."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Mixed", ["abc", "123", "def"])
        assert field["type"] == "text"


class TestFieldInferrerFieldDefinition:
    """Tests for FieldDefinition output structure."""

    def test_field_has_key(self) -> None:
        """Field definition includes snake_case key."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Column Name", ["value"])
        assert field["key"] == "column_name"

    def test_field_has_name(self) -> None:
        """Field definition includes original name."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Original Name", ["value"])
        assert field["name"] == "Original Name"

    def test_field_has_type(self) -> None:
        """Field definition includes type."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Test", ["value"])
        assert "type" in field
        assert isinstance(field["type"], str)

    def test_field_required_is_false(self) -> None:
        """Field required is always False."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("Test", ["value"])
        assert field["required"] is False

    def test_show_in_list_first_three(self) -> None:
        """First 3 fields have show_in_list=True."""
        inferrer = FieldInferrer()

        field0 = inferrer.infer_type("Field1", ["value"], field_index=0)
        field1 = inferrer.infer_type("Field2", ["value"], field_index=1)
        field2 = inferrer.infer_type("Field3", ["value"], field_index=2)
        field3 = inferrer.infer_type("Field4", ["value"], field_index=3)
        field4 = inferrer.infer_type("Field5", ["value"], field_index=4)

        assert field0["show_in_list"] is True
        assert field1["show_in_list"] is True
        assert field2["show_in_list"] is True
        assert field3["show_in_list"] is False
        assert field4["show_in_list"] is False


class TestFieldInferrerInferSchema:
    """Tests for infer_schema method."""

    def test_infer_schema_basic(self) -> None:
        """Basic schema inference from columns and rows."""
        inferrer = FieldInferrer()

        columns = ["Name", "Status", "Count"]
        rows = [
            {"Name": "Item 1", "Status": "Active", "Count": "5"},
            {"Name": "Item 2", "Status": "Active", "Count": "10"},
            {"Name": "Item 3", "Status": "Inactive", "Count": "3"},
        ]

        fields = inferrer.infer_schema(columns, rows)

        assert len(fields) == 3
        assert fields[0]["key"] == "name"
        assert fields[1]["key"] == "status"
        assert fields[2]["key"] == "count"
        assert fields[2]["type"] == "number"

    def test_infer_schema_skip_columns(self) -> None:
        """Skip columns are excluded from schema."""
        inferrer = FieldInferrer()

        columns = ["ID", "Name", "Value"]
        rows = [
            {"ID": "1", "Name": "Test", "Value": "abc"},
        ]

        fields = inferrer.infer_schema(columns, rows, skip_columns={"ID"})

        assert len(fields) == 2
        keys = [f["key"] for f in fields]
        assert "id" not in keys
        assert "name" in keys
        assert "value" in keys

    def test_infer_schema_show_in_list(self) -> None:
        """First 3 fields have show_in_list=True."""
        inferrer = FieldInferrer()

        columns = ["A", "B", "C", "D", "E"]
        rows = [{"A": "1", "B": "2", "C": "3", "D": "4", "E": "5"}]

        fields = inferrer.infer_schema(columns, rows)

        assert fields[0]["show_in_list"] is True
        assert fields[1]["show_in_list"] is True
        assert fields[2]["show_in_list"] is True
        assert fields[3]["show_in_list"] is False
        assert fields[4]["show_in_list"] is False

    def test_infer_schema_empty_rows(self) -> None:
        """Empty rows produce text fields."""
        inferrer = FieldInferrer()

        columns = ["Name", "Value"]
        rows: list[dict[str, str | None]] = []

        fields = inferrer.infer_schema(columns, rows)

        assert len(fields) == 2
        assert all(f["type"] == "text" for f in fields)

    def test_infer_schema_missing_column_values(self) -> None:
        """Missing column values in rows handled gracefully."""
        inferrer = FieldInferrer()

        columns = ["Name", "Value"]
        rows = [
            {"Name": "Test"},  # Missing "Value"
            {"Name": "Test2", "Value": "123"},
        ]

        fields = inferrer.infer_schema(columns, rows)

        assert len(fields) == 2


class TestFieldInferrerPriorityOrder:
    """Tests for inference priority order."""

    def test_password_overrides_text(self) -> None:
        """Password column name takes priority over value analysis."""
        inferrer = FieldInferrer()

        # Even though values look like text, name indicates password
        field = inferrer.infer_type("Password", ["regular", "text", "values"])
        assert field["type"] == "password"

    def test_totp_overrides_text(self) -> None:
        """TOTP column name takes priority over value analysis."""
        inferrer = FieldInferrer()

        field = inferrer.infer_type("TOTP Secret", ["123456", "654321"])
        assert field["type"] == "totp"

    def test_password_overrides_number(self) -> None:
        """Password column name takes priority over number inference."""
        inferrer = FieldInferrer()

        # Even though values are numbers, name indicates password
        field = inferrer.infer_type("Secret Key", ["123456", "789012"])
        assert field["type"] == "password"
