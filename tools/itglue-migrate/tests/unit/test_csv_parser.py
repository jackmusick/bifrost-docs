"""Unit tests for the CSV parser module."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from itglue_migrate.csv_parser import (
    CORE_ENTITY_FILES,
    CSVParser,
    FieldDefinition,
    FileNotFoundError,
    ParseError,
)


@pytest.fixture
def parser() -> CSVParser:
    """Create a CSV parser instance."""
    return CSVParser()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestCSVParserBasics:
    """Test basic CSV parser functionality."""

    def test_parser_creation(self, parser: CSVParser) -> None:
        """Test parser can be instantiated."""
        assert parser is not None

    def test_file_not_found_raises_error(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse_organizations(temp_dir / "nonexistent.csv")

        assert exc_info.value.path == temp_dir / "nonexistent.csv"
        assert "not found" in str(exc_info.value)


class TestOrganizationsParsing:
    """Test parsing of organizations.csv."""

    def test_parse_organizations_basic(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing basic organizations CSV."""
        csv_content = """id,name,description,quick_notes
1,Acme Corp,A test company,Some quick notes
2,Beta Inc,Another company,
"""
        csv_path = temp_dir / "organizations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        orgs = parser.parse_organizations(csv_path)

        assert len(orgs) == 2
        assert orgs[0]["id"] == "1"
        assert orgs[0]["name"] == "Acme Corp"
        assert orgs[0]["description"] == "A test company"
        assert orgs[0]["quick_notes"] == "Some quick notes"
        assert orgs[1]["id"] == "2"
        assert orgs[1]["name"] == "Beta Inc"
        assert orgs[1]["description"] == "Another company"
        assert orgs[1]["quick_notes"] is None  # Empty string converted to None

    def test_parse_organizations_with_bom(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing organizations CSV with UTF-8 BOM."""
        csv_content = "\ufeffid,name,description,quick_notes\n1,Acme Corp,Test,Notes\n"
        csv_path = temp_dir / "organizations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        orgs = parser.parse_organizations(csv_path)

        assert len(orgs) == 1
        assert orgs[0]["id"] == "1"
        assert orgs[0]["name"] == "Acme Corp"

    def test_parse_organizations_empty_file(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing empty organizations CSV (header only)."""
        csv_content = "id,name,description,quick_notes\n"
        csv_path = temp_dir / "organizations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        orgs = parser.parse_organizations(csv_path)

        assert len(orgs) == 0

    def test_parse_organizations_missing_columns(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing organizations with missing optional columns."""
        csv_content = "id,name\n1,Acme Corp\n"
        csv_path = temp_dir / "organizations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        orgs = parser.parse_organizations(csv_path)

        assert len(orgs) == 1
        assert orgs[0]["id"] == "1"
        assert orgs[0]["name"] == "Acme Corp"
        assert orgs[0]["description"] is None
        assert orgs[0]["quick_notes"] is None


class TestConfigurationsParsing:
    """Test parsing of configurations.csv."""

    def test_parse_configurations_basic(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing basic configurations CSV."""
        csv_content = """id,name,hostname,ip,mac,serial,manufacturer,model,notes,organization_id,configuration_type
1,Server-01,srv01.local,192.168.1.10,00:11:22:33:44:55,ABC123,Dell,PowerEdge R740,Production server,org-1,Server
2,Workstation-01,ws01.local,192.168.1.20,,XYZ789,HP,ProDesk,User workstation,org-1,Workstation
"""
        csv_path = temp_dir / "configurations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        configs = parser.parse_configurations(csv_path)

        assert len(configs) == 2
        assert configs[0]["id"] == "1"
        assert configs[0]["name"] == "Server-01"
        assert configs[0]["hostname"] == "srv01.local"
        assert configs[0]["ip"] == "192.168.1.10"
        assert configs[0]["mac"] == "00:11:22:33:44:55"
        assert configs[0]["serial"] == "ABC123"
        assert configs[0]["manufacturer"] == "Dell"
        assert configs[0]["model"] == "PowerEdge R740"
        assert configs[0]["notes"] == "Production server"
        assert configs[0]["organization_id"] == "org-1"
        assert configs[0]["configuration_type"] == "Server"
        assert configs[1]["mac"] is None  # Empty MAC

    def test_parse_configurations_with_interfaces(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing configurations with JSON interfaces."""
        interfaces = [
            {"name": "eth0", "ip": "192.168.1.10", "primary": True},
            {"name": "eth1", "ip": "192.168.2.10", "primary": False},
        ]
        csv_content = f"""id,name,hostname,configuration_interfaces
1,Server-01,srv01.local,"{json.dumps(interfaces).replace('"', '""')}"
"""
        csv_path = temp_dir / "configurations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        configs = parser.parse_configurations(csv_path)

        assert len(configs) == 1
        assert configs[0]["configuration_interfaces"] == interfaces

    def test_parse_configurations_invalid_json(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing configurations with invalid JSON raises error."""
        csv_content = """id,name,hostname,configuration_interfaces
1,Server-01,srv01.local,"{invalid json}"
"""
        csv_path = temp_dir / "configurations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        with pytest.raises(ParseError) as exc_info:
            parser.parse_configurations(csv_path)

        assert "Invalid JSON" in str(exc_info.value)
        assert exc_info.value.row == 2

    def test_parse_configurations_organization_column_fallback(
        self, parser: CSVParser, temp_dir: Path
    ) -> None:
        """Test parsing configurations with 'organization' column instead of 'organization_id'."""
        csv_content = """id,name,hostname,organization
1,Server-01,srv01.local,org-1
"""
        csv_path = temp_dir / "configurations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        configs = parser.parse_configurations(csv_path)

        assert len(configs) == 1
        assert configs[0]["organization_id"] == "org-1"


class TestDocumentsParsing:
    """Test parsing of documents.csv."""

    def test_parse_documents_basic(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing basic documents CSV."""
        csv_content = """id,name,locator,organization
1,Runbook,/runbooks/main,org-1
2,SOP,/procedures/sop,org-2
"""
        csv_path = temp_dir / "documents.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        docs = parser.parse_documents(csv_path)

        assert len(docs) == 2
        assert docs[0]["id"] == "1"
        assert docs[0]["name"] == "Runbook"
        assert docs[0]["locator"] == "/runbooks/main"
        assert docs[0]["organization_id"] == "org-1"


class TestLocationsParsing:
    """Test parsing of locations.csv."""

    def test_parse_locations_basic(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing basic locations CSV."""
        csv_content = """id,name,address_1,address_2,city,region,postal_code,country,phone,organization
1,HQ,123 Main St,Suite 100,New York,NY,10001,USA,555-1234,org-1
2,Branch,456 Oak Ave,,Los Angeles,CA,90001,USA,,org-1
"""
        csv_path = temp_dir / "locations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        locations = parser.parse_locations(csv_path)

        assert len(locations) == 2
        assert locations[0]["id"] == "1"
        assert locations[0]["name"] == "HQ"
        assert locations[0]["address_1"] == "123 Main St"
        assert locations[0]["address_2"] == "Suite 100"
        assert locations[0]["city"] == "New York"
        assert locations[0]["region"] == "NY"
        assert locations[0]["postal_code"] == "10001"
        assert locations[0]["country"] == "USA"
        assert locations[0]["phone"] == "555-1234"
        assert locations[0]["organization_id"] == "org-1"
        assert locations[1]["address_2"] is None
        assert locations[1]["phone"] is None

    def test_parse_locations_alternate_column_names(
        self, parser: CSVParser, temp_dir: Path
    ) -> None:
        """Test parsing locations with alternate column names."""
        csv_content = """id,name,address1,city,state,zip,organization_id
1,HQ,123 Main St,New York,NY,10001,org-1
"""
        csv_path = temp_dir / "locations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        locations = parser.parse_locations(csv_path)

        assert len(locations) == 1
        assert locations[0]["address_1"] == "123 Main St"
        assert locations[0]["region"] == "NY"
        assert locations[0]["postal_code"] == "10001"


class TestPasswordsParsing:
    """Test parsing of passwords.csv."""

    def test_parse_passwords_basic(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing basic passwords CSV."""
        csv_content = """id,name,username,password,url,notes,resource_type,resource_id,otp_secret,organization
1,Admin Login,admin,secret123,https://example.com,Admin credentials,Configuration,config-1,,org-1
2,API Key,api_user,apikey456,https://api.example.com,API access,,,JBSWY3DPEHPK3PXP,org-1
"""
        csv_path = temp_dir / "passwords.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        passwords = parser.parse_passwords(csv_path)

        assert len(passwords) == 2
        assert passwords[0]["id"] == "1"
        assert passwords[0]["name"] == "Admin Login"
        assert passwords[0]["username"] == "admin"
        assert passwords[0]["password"] == "secret123"
        assert passwords[0]["url"] == "https://example.com"
        assert passwords[0]["notes"] == "Admin credentials"
        assert passwords[0]["resource_type"] == "Configuration"
        assert passwords[0]["resource_id"] == "config-1"
        assert passwords[0]["otp_secret"] is None
        assert passwords[0]["organization_id"] == "org-1"
        assert passwords[1]["otp_secret"] == "JBSWY3DPEHPK3PXP"


class TestCustomAssetParsing:
    """Test parsing of custom asset type CSVs."""

    def test_parse_custom_asset_csv_basic(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing basic custom asset CSV."""
        csv_content = """id,organization,certificate_name,expiry_date,issuer,domain
1,org-1,Main SSL,2024-12-31,DigiCert,example.com
2,org-1,API SSL,2025-06-30,Let's Encrypt,api.example.com
"""
        csv_path = temp_dir / "ssl-certificates.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        fields, assets = parser.parse_custom_asset_csv(csv_path, "ssl-certificates")

        # Check field definitions
        assert len(fields) == 4
        field_names = [f.name for f in fields]
        assert "certificate_name" in field_names
        assert "expiry_date" in field_names
        assert "issuer" in field_names
        assert "domain" in field_names

        # Check id and organization are not in field definitions
        assert "id" not in field_names
        assert "organization" not in field_names

        # Check assets
        assert len(assets) == 2
        assert assets[0]["id"] == "1"
        assert assets[0]["organization_id"] == "org-1"
        assert assets[0]["asset_type"] == "ssl-certificates"
        assert assets[0]["fields"]["certificate_name"] == "Main SSL"
        assert assets[0]["fields"]["expiry_date"] == "2024-12-31"

    def test_parse_custom_asset_csv_empty(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test parsing empty custom asset CSV."""
        csv_content = "id,organization,field1,field2\n"
        csv_path = temp_dir / "empty-asset.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        fields, assets = parser.parse_custom_asset_csv(csv_path, "empty-asset")

        assert len(fields) == 0
        assert len(assets) == 0

    def test_parse_custom_asset_field_type_detection(
        self, parser: CSVParser, temp_dir: Path
    ) -> None:
        """Test field type detection for custom assets."""
        # Long text that exceeds 255 characters (no commas to avoid CSV quoting issues)
        # Must be > 255 chars to trigger textbox detection
        long_text = "A" * 300  # 300 characters
        csv_content = (
            "id,organization,text_field,number_field,date_field,checkbox_field,long_text\n"
            f"1,org-1,short text,123,2024-01-15,true,{long_text}\n"
            "2,org-1,another,456,2024-02-20,false,Short\n"
            "3,org-1,text,789,2024-03-25,yes,Normal\n"
        )
        csv_path = temp_dir / "typed-asset.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        fields, assets = parser.parse_custom_asset_csv(csv_path, "typed-asset")

        # Find fields by name
        field_map = {f.name: f for f in fields}

        assert field_map["text_field"].field_type == "text"
        assert field_map["number_field"].field_type == "number"
        assert field_map["date_field"].field_type == "date"
        assert field_map["checkbox_field"].field_type == "checkbox"
        assert field_map["long_text"].field_type == "textbox"

    def test_parse_custom_asset_required_detection(
        self, parser: CSVParser, temp_dir: Path
    ) -> None:
        """Test required field detection for custom assets."""
        csv_content = """id,organization,always_present,sometimes_present
1,org-1,value1,value1
2,org-1,value2,
3,org-1,value3,value3
"""
        csv_path = temp_dir / "required-asset.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        fields, assets = parser.parse_custom_asset_csv(csv_path, "required-asset")

        field_map = {f.name: f for f in fields}

        assert field_map["always_present"].required is True
        assert field_map["sometimes_present"].required is False


class TestFieldTypeDetection:
    """Test field type detection heuristics."""

    def test_detect_checkbox_values(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test detection of checkbox type from boolean values."""
        csv_content = """id,organization,bool1,bool2,bool3,bool4
1,org-1,true,yes,1,True
2,org-1,false,no,0,False
"""
        csv_path = temp_dir / "bool-asset.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        fields, _ = parser.parse_custom_asset_csv(csv_path, "bool-asset")
        field_map = {f.name: f for f in fields}

        assert field_map["bool1"].field_type == "checkbox"
        assert field_map["bool2"].field_type == "checkbox"
        assert field_map["bool3"].field_type == "checkbox"
        assert field_map["bool4"].field_type == "checkbox"

    def test_detect_date_formats(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test detection of date type from various date formats."""
        csv_content = """id,organization,date1,date2,date3
1,org-1,2024-01-15,2024-01-15T10:30:00,2024-01-15T10:30:00Z
2,org-1,2024-02-20,2024-02-20T14:45:00,2024-02-20T14:45:00+00:00
"""
        csv_path = temp_dir / "date-asset.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        fields, _ = parser.parse_custom_asset_csv(csv_path, "date-asset")
        field_map = {f.name: f for f in fields}

        assert field_map["date1"].field_type == "date"
        assert field_map["date2"].field_type == "date"
        assert field_map["date3"].field_type == "date"

    def test_detect_number_formats(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test detection of number type from numeric values."""
        csv_content = """id,organization,int_field,float_field,negative
1,org-1,123,45.67,-10
2,org-1,456,78.90,-20
"""
        csv_path = temp_dir / "number-asset.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        fields, _ = parser.parse_custom_asset_csv(csv_path, "number-asset")
        field_map = {f.name: f for f in fields}

        assert field_map["int_field"].field_type == "number"
        assert field_map["float_field"].field_type == "number"
        assert field_map["negative"].field_type == "number"

    def test_detect_textbox_multiline(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test detection of textbox type from multiline values."""
        csv_content = '''id,organization,multiline
1,org-1,"Line 1
Line 2
Line 3"
'''
        csv_path = temp_dir / "multiline-asset.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        fields, _ = parser.parse_custom_asset_csv(csv_path, "multiline-asset")
        field_map = {f.name: f for f in fields}

        assert field_map["multiline"].field_type == "textbox"

    def test_detect_empty_column_defaults_to_text(
        self, parser: CSVParser, temp_dir: Path
    ) -> None:
        """Test that empty columns default to text type."""
        csv_content = """id,organization,empty_field
1,org-1,
2,org-1,
"""
        csv_path = temp_dir / "empty-column.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        fields, _ = parser.parse_custom_asset_csv(csv_path, "empty-column")
        field_map = {f.name: f for f in fields}

        assert field_map["empty_field"].field_type == "text"


class TestDiscoverCustomAssetTypes:
    """Test discovery of custom asset types."""

    def test_discover_custom_asset_types(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test discovering custom asset type CSVs."""
        # Create core entity files
        (temp_dir / "organizations.csv").write_text("id,name\n1,Org\n")
        (temp_dir / "configurations.csv").write_text("id,name\n1,Config\n")

        # Create custom asset files
        (temp_dir / "ssl-certificates.csv").write_text("id,organization,cert\n1,org-1,cert1\n")
        (temp_dir / "licensing.csv").write_text("id,organization,license\n1,org-1,lic1\n")
        (temp_dir / "domains.csv").write_text("id,organization,domain\n1,org-1,example.com\n")

        custom_types = parser.discover_custom_asset_types(temp_dir)

        assert "ssl-certificates" in custom_types
        assert "licensing" in custom_types
        assert "domains" in custom_types
        assert "organizations" not in custom_types
        assert "configurations" not in custom_types
        assert len(custom_types) == 3

    def test_discover_custom_asset_types_sorted(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test that discovered types are sorted alphabetically."""
        (temp_dir / "zebra.csv").write_text("id,organization,field\n")
        (temp_dir / "alpha.csv").write_text("id,organization,field\n")
        (temp_dir / "beta.csv").write_text("id,organization,field\n")

        custom_types = parser.discover_custom_asset_types(temp_dir)

        assert custom_types == ["alpha", "beta", "zebra"]

    def test_discover_custom_asset_types_empty_dir(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test discovering in empty directory."""
        custom_types = parser.discover_custom_asset_types(temp_dir)

        assert custom_types == []

    def test_discover_custom_asset_types_missing_dir(self, parser: CSVParser) -> None:
        """Test discovering in non-existent directory raises error."""
        with pytest.raises(FileNotFoundError):
            parser.discover_custom_asset_types(Path("/nonexistent/path"))


class TestValidateExportStructure:
    """Test export structure validation."""

    def test_validate_export_structure_valid(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test validating a valid export structure."""
        # Create all core entity files
        (temp_dir / "organizations.csv").write_text("id,name\n1,Org1\n2,Org2\n")
        (temp_dir / "configurations.csv").write_text("id,name\n1,Config1\n")
        (temp_dir / "documents.csv").write_text("id,name\n1,Doc1\n2,Doc2\n3,Doc3\n")
        (temp_dir / "locations.csv").write_text("id,name\n1,Loc1\n")
        (temp_dir / "passwords.csv").write_text("id,name\n1,Pwd1\n")

        # Create custom asset files
        (temp_dir / "ssl-certificates.csv").write_text("id,organization,cert\n1,org-1,cert1\n")

        result = parser.validate_export_structure(temp_dir)

        assert result["valid"] is True
        assert result["core_entities"]["organizations"]["present"] is True
        assert result["core_entities"]["organizations"]["row_count"] == 2
        assert result["core_entities"]["configurations"]["present"] is True
        assert result["core_entities"]["configurations"]["row_count"] == 1
        assert result["core_entities"]["documents"]["present"] is True
        assert result["core_entities"]["documents"]["row_count"] == 3
        assert "ssl-certificates" in result["custom_asset_types"]
        assert len(result["errors"]) == 0

    def test_validate_export_structure_missing_optional(
        self, parser: CSVParser, temp_dir: Path
    ) -> None:
        """Test validating export with missing optional files."""
        # Only create organizations (minimum required)
        (temp_dir / "organizations.csv").write_text("id,name\n1,Org1\n")

        result = parser.validate_export_structure(temp_dir)

        assert result["valid"] is True
        assert result["core_entities"]["organizations"]["present"] is True
        assert result["core_entities"]["configurations"]["present"] is False
        assert result["core_entities"]["documents"]["present"] is False

    def test_validate_export_structure_missing_organizations(
        self, parser: CSVParser, temp_dir: Path
    ) -> None:
        """Test validating export without organizations (invalid)."""
        # Create everything except organizations
        (temp_dir / "configurations.csv").write_text("id,name\n1,Config1\n")

        result = parser.validate_export_structure(temp_dir)

        assert result["valid"] is False
        assert result["core_entities"]["organizations"]["present"] is False

    def test_validate_export_structure_nonexistent_dir(self, parser: CSVParser) -> None:
        """Test validating non-existent directory raises error."""
        with pytest.raises(FileNotFoundError):
            parser.validate_export_structure(Path("/nonexistent/path"))


class TestFieldDefinition:
    """Test FieldDefinition dataclass."""

    def test_field_definition_creation(self) -> None:
        """Test creating a FieldDefinition."""
        field = FieldDefinition(
            name="test_field",
            field_type="text",
            required=True,
            sample_values=["value1", "value2"],
        )

        assert field.name == "test_field"
        assert field.field_type == "text"
        assert field.required is True
        assert field.sample_values == ["value1", "value2"]

    def test_field_definition_defaults(self) -> None:
        """Test FieldDefinition default values."""
        field = FieldDefinition(name="test_field", field_type="text")

        assert field.required is False
        assert field.sample_values == []

    def test_field_definition_to_dict(self) -> None:
        """Test FieldDefinition to_dict method."""
        field = FieldDefinition(
            name="test_field",
            field_type="number",
            required=True,
            sample_values=["1", "2", "3"],
        )

        result = field.to_dict()

        assert result == {
            "name": "test_field",
            "field_type": "number",
            "required": True,
        }
        # sample_values not included in dict representation
        assert "sample_values" not in result


class TestGetRowCount:
    """Test row count functionality."""

    def test_get_row_count(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test getting row count from CSV."""
        csv_content = "id,name\n1,One\n2,Two\n3,Three\n"
        csv_path = temp_dir / "test.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        count = parser.get_row_count(csv_path)

        assert count == 3

    def test_get_row_count_empty(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test getting row count from empty CSV."""
        csv_content = "id,name\n"
        csv_path = temp_dir / "empty.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        count = parser.get_row_count(csv_path)

        assert count == 0


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_whitespace_handling(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test that whitespace is properly trimmed."""
        csv_content = "id,name,description\n 1 , Acme Corp , Test company \n"
        csv_path = temp_dir / "organizations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        orgs = parser.parse_organizations(csv_path)

        assert orgs[0]["id"] == "1"
        assert orgs[0]["name"] == "Acme Corp"
        assert orgs[0]["description"] == "Test company"

    def test_special_characters_in_values(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test handling of special characters in values."""
        csv_content = 'id,name,description\n1,"Acme, Inc.","A ""quoted"" company"\n'
        csv_path = temp_dir / "organizations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        orgs = parser.parse_organizations(csv_path)

        assert orgs[0]["name"] == "Acme, Inc."
        assert orgs[0]["description"] == 'A "quoted" company'

    def test_unicode_characters(self, parser: CSVParser, temp_dir: Path) -> None:
        """Test handling of unicode characters."""
        csv_content = "id,name,description\n1,Acme GmbH,Gesellschaft mit beschrankter Haftung\n"
        csv_path = temp_dir / "organizations.csv"
        csv_path.write_text(csv_content, encoding="utf-8")

        orgs = parser.parse_organizations(csv_path)

        assert orgs[0]["name"] == "Acme GmbH"

    def test_core_entity_files_constant(self) -> None:
        """Test that CORE_ENTITY_FILES contains expected files."""
        assert "organizations.csv" in CORE_ENTITY_FILES
        assert "configurations.csv" in CORE_ENTITY_FILES
        assert "documents.csv" in CORE_ENTITY_FILES
        assert "locations.csv" in CORE_ENTITY_FILES
        assert "passwords.csv" in CORE_ENTITY_FILES
        assert "contacts.csv" in CORE_ENTITY_FILES
