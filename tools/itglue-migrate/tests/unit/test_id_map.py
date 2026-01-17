"""Unit tests for ID mapping storage module."""

import json
import tempfile
from pathlib import Path

import pytest

from itglue_migrate.id_map import (
    VALID_ENTITY_TYPES,
    IdMapper,
    IdMapperError,
    InvalidEntityTypeError,
)


class TestIdMapperInit:
    """Tests for IdMapper initialization."""

    def test_init_creates_empty_mappings(self) -> None:
        """IdMapper should initialize with empty mappings for all entity types."""
        mapper = IdMapper()

        for entity_type in VALID_ENTITY_TYPES:
            assert mapper.get_all(entity_type) == {}

    def test_init_stats_all_zero(self) -> None:
        """Stats should show zero for all entity types on init."""
        mapper = IdMapper()
        stats = mapper.stats()

        for entity_type in VALID_ENTITY_TYPES:
            assert stats[entity_type] == 0

    def test_total_count_zero_on_init(self) -> None:
        """Total count should be zero on init."""
        mapper = IdMapper()
        assert mapper.total_count() == 0


class TestIdMapperAdd:
    """Tests for adding mappings."""

    def test_add_creates_mapping(self) -> None:
        """Adding a mapping should store it correctly."""
        mapper = IdMapper()
        mapper.add("organization", "123", "uuid-abc")

        assert mapper.get("organization", "123") == "uuid-abc"

    def test_add_multiple_types(self) -> None:
        """Adding mappings for different types should store them separately."""
        mapper = IdMapper()
        mapper.add("organization", "1", "org-uuid")
        mapper.add("configuration", "1", "config-uuid")
        mapper.add("document", "1", "doc-uuid")

        assert mapper.get("organization", "1") == "org-uuid"
        assert mapper.get("configuration", "1") == "config-uuid"
        assert mapper.get("document", "1") == "doc-uuid"

    def test_add_overwrites_existing(self) -> None:
        """Adding a mapping for an existing ID should overwrite it."""
        mapper = IdMapper()
        mapper.add("organization", "123", "old-uuid")
        mapper.add("organization", "123", "new-uuid")

        assert mapper.get("organization", "123") == "new-uuid"

    def test_add_converts_int_to_string(self) -> None:
        """Adding with integer ID should convert to string."""
        mapper = IdMapper()
        mapper.add("organization", 123, "uuid-abc")  # type: ignore[arg-type]

        assert mapper.get("organization", "123") == "uuid-abc"
        assert mapper.get("organization", 123) == "uuid-abc"  # type: ignore[arg-type]

    def test_add_invalid_entity_type_raises(self) -> None:
        """Adding with invalid entity type should raise InvalidEntityTypeError."""
        mapper = IdMapper()

        with pytest.raises(InvalidEntityTypeError) as exc_info:
            mapper.add("invalid_type", "123", "uuid")

        assert exc_info.value.entity_type == "invalid_type"
        assert "invalid_type" in str(exc_info.value)

    def test_add_empty_itglue_id_raises(self) -> None:
        """Adding with empty itglue_id should raise ValueError."""
        mapper = IdMapper()

        with pytest.raises(ValueError, match="itglue_id cannot be empty"):
            mapper.add("organization", "", "uuid")

    def test_add_empty_uuid_raises(self) -> None:
        """Adding with empty uuid should raise ValueError."""
        mapper = IdMapper()

        with pytest.raises(ValueError, match="uuid cannot be empty"):
            mapper.add("organization", "123", "")

    @pytest.mark.parametrize("entity_type", list(VALID_ENTITY_TYPES))
    def test_add_all_valid_entity_types(self, entity_type: str) -> None:
        """All valid entity types should be accepted."""
        mapper = IdMapper()
        mapper.add(entity_type, "123", "uuid-abc")

        assert mapper.get(entity_type, "123") == "uuid-abc"


class TestIdMapperGet:
    """Tests for getting mappings."""

    def test_get_existing_returns_uuid(self) -> None:
        """Getting an existing mapping should return the UUID."""
        mapper = IdMapper()
        mapper.add("organization", "123", "uuid-abc")

        assert mapper.get("organization", "123") == "uuid-abc"

    def test_get_nonexistent_returns_none(self) -> None:
        """Getting a non-existent mapping should return None."""
        mapper = IdMapper()

        assert mapper.get("organization", "123") is None

    def test_get_wrong_type_returns_none(self) -> None:
        """Getting from wrong entity type should return None."""
        mapper = IdMapper()
        mapper.add("organization", "123", "uuid-abc")

        assert mapper.get("configuration", "123") is None

    def test_get_invalid_entity_type_raises(self) -> None:
        """Getting with invalid entity type should raise InvalidEntityTypeError."""
        mapper = IdMapper()

        with pytest.raises(InvalidEntityTypeError):
            mapper.get("invalid_type", "123")


class TestIdMapperHas:
    """Tests for checking if mapping exists."""

    def test_has_existing_returns_true(self) -> None:
        """Checking for existing mapping should return True."""
        mapper = IdMapper()
        mapper.add("organization", "123", "uuid-abc")

        assert mapper.has("organization", "123") is True

    def test_has_nonexistent_returns_false(self) -> None:
        """Checking for non-existent mapping should return False."""
        mapper = IdMapper()

        assert mapper.has("organization", "123") is False

    def test_has_wrong_type_returns_false(self) -> None:
        """Checking wrong entity type should return False."""
        mapper = IdMapper()
        mapper.add("organization", "123", "uuid-abc")

        assert mapper.has("configuration", "123") is False

    def test_has_invalid_entity_type_raises(self) -> None:
        """Checking with invalid entity type should raise InvalidEntityTypeError."""
        mapper = IdMapper()

        with pytest.raises(InvalidEntityTypeError):
            mapper.has("invalid_type", "123")


class TestIdMapperGetAll:
    """Tests for getting all mappings for a type."""

    def test_get_all_empty_returns_empty_dict(self) -> None:
        """Getting all from empty mapper should return empty dict."""
        mapper = IdMapper()

        assert mapper.get_all("organization") == {}

    def test_get_all_returns_copy(self) -> None:
        """Getting all should return a copy, not the internal dict."""
        mapper = IdMapper()
        mapper.add("organization", "123", "uuid-abc")

        all_mappings = mapper.get_all("organization")
        all_mappings["999"] = "modified"

        assert mapper.get("organization", "999") is None

    def test_get_all_returns_all_mappings(self) -> None:
        """Getting all should return all mappings for the type."""
        mapper = IdMapper()
        mapper.add("organization", "1", "uuid-1")
        mapper.add("organization", "2", "uuid-2")
        mapper.add("organization", "3", "uuid-3")

        all_mappings = mapper.get_all("organization")

        assert all_mappings == {"1": "uuid-1", "2": "uuid-2", "3": "uuid-3"}

    def test_get_all_invalid_entity_type_raises(self) -> None:
        """Getting all with invalid entity type should raise InvalidEntityTypeError."""
        mapper = IdMapper()

        with pytest.raises(InvalidEntityTypeError):
            mapper.get_all("invalid_type")


class TestIdMapperClear:
    """Tests for clearing mappings."""

    def test_clear_removes_all_mappings(self) -> None:
        """Clearing should remove all mappings."""
        mapper = IdMapper()
        mapper.add("organization", "1", "uuid-1")
        mapper.add("configuration", "2", "uuid-2")
        mapper.add("document", "3", "uuid-3")

        mapper.clear()

        assert mapper.total_count() == 0
        assert mapper.get("organization", "1") is None
        assert mapper.get("configuration", "2") is None
        assert mapper.get("document", "3") is None


class TestIdMapperStats:
    """Tests for statistics."""

    def test_stats_counts_per_type(self) -> None:
        """Stats should return counts per entity type."""
        mapper = IdMapper()
        mapper.add("organization", "1", "uuid-1")
        mapper.add("organization", "2", "uuid-2")
        mapper.add("configuration", "3", "uuid-3")

        stats = mapper.stats()

        assert stats["organization"] == 2
        assert stats["configuration"] == 1
        assert stats["document"] == 0

    def test_stats_includes_all_types(self) -> None:
        """Stats should include all valid entity types."""
        mapper = IdMapper()
        stats = mapper.stats()

        for entity_type in VALID_ENTITY_TYPES:
            assert entity_type in stats


class TestIdMapperTotalCount:
    """Tests for total count."""

    def test_total_count_sums_all_types(self) -> None:
        """Total count should sum across all entity types."""
        mapper = IdMapper()
        mapper.add("organization", "1", "uuid-1")
        mapper.add("organization", "2", "uuid-2")
        mapper.add("configuration", "3", "uuid-3")
        mapper.add("document", "4", "uuid-4")

        assert mapper.total_count() == 4


class TestIdMapperPersistence:
    """Tests for save/load functionality."""

    def test_save_creates_file(self) -> None:
        """Saving should create a JSON file."""
        mapper = IdMapper()
        mapper.add("organization", "123", "uuid-abc")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            mapper.save(path)

            assert path.exists()

    def test_save_creates_parent_directories(self) -> None:
        """Saving should create parent directories if needed."""
        mapper = IdMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "id_map.json"
            mapper.save(path)

            assert path.exists()

    def test_save_writes_valid_json(self) -> None:
        """Saved file should contain valid JSON."""
        mapper = IdMapper()
        mapper.add("organization", "123", "uuid-abc")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            mapper.save(path)

            with path.open() as f:
                data = json.load(f)

            assert "version" in data
            assert "mappings" in data

    def test_save_includes_version(self) -> None:
        """Saved file should include version number."""
        mapper = IdMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            mapper.save(path)

            with path.open() as f:
                data = json.load(f)

            assert data["version"] == 1

    def test_load_restores_mappings(self) -> None:
        """Loading should restore saved mappings."""
        mapper1 = IdMapper()
        mapper1.add("organization", "123", "uuid-abc")
        mapper1.add("configuration", "456", "uuid-def")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            mapper1.save(path)

            mapper2 = IdMapper()
            mapper2.load(path)

            assert mapper2.get("organization", "123") == "uuid-abc"
            assert mapper2.get("configuration", "456") == "uuid-def"

    def test_load_merges_with_existing(self) -> None:
        """Loading should merge with existing mappings."""
        mapper1 = IdMapper()
        mapper1.add("organization", "1", "uuid-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            mapper1.save(path)

            mapper2 = IdMapper()
            mapper2.add("organization", "2", "uuid-2")
            mapper2.load(path)

            assert mapper2.get("organization", "1") == "uuid-1"
            assert mapper2.get("organization", "2") == "uuid-2"

    def test_load_overwrites_conflicts(self) -> None:
        """Loaded mappings should overwrite existing on conflict."""
        mapper1 = IdMapper()
        mapper1.add("organization", "1", "loaded-uuid")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            mapper1.save(path)

            mapper2 = IdMapper()
            mapper2.add("organization", "1", "existing-uuid")
            mapper2.load(path)

            assert mapper2.get("organization", "1") == "loaded-uuid"

    def test_load_nonexistent_file_raises(self) -> None:
        """Loading non-existent file should raise FileNotFoundError."""
        mapper = IdMapper()

        with pytest.raises(FileNotFoundError):
            mapper.load("/nonexistent/path/id_map.json")

    def test_load_invalid_json_raises(self) -> None:
        """Loading invalid JSON should raise error."""
        mapper = IdMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            path.write_text("not valid json")

            with pytest.raises(json.JSONDecodeError):
                mapper.load(path)

    def test_load_wrong_format_raises(self) -> None:
        """Loading file with wrong format should raise ValueError."""
        mapper = IdMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            path.write_text("[]")  # Array instead of dict

            with pytest.raises(ValueError, match="expected dict"):
                mapper.load(path)

    def test_load_wrong_version_raises(self) -> None:
        """Loading file with unsupported version should raise ValueError."""
        mapper = IdMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            path.write_text('{"version": 99, "mappings": {}}')

            with pytest.raises(ValueError, match="Unsupported ID map version"):
                mapper.load(path)

    def test_load_missing_mappings_raises(self) -> None:
        """Loading file without mappings field should raise ValueError."""
        mapper = IdMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            path.write_text('{"version": 1}')

            with pytest.raises(ValueError, match="missing or invalid 'mappings' field"):
                mapper.load(path)

    def test_load_skips_unknown_entity_types(self) -> None:
        """Loading should skip unknown entity types for forward compatibility."""
        mapper = IdMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "id_map.json"
            data = {
                "version": 1,
                "mappings": {
                    "organization": {"1": "uuid-1"},
                    "future_type": {"2": "uuid-2"},  # Unknown type
                },
            }
            path.write_text(json.dumps(data))

            mapper.load(path)

            assert mapper.get("organization", "1") == "uuid-1"
            # Unknown type is silently ignored
            assert mapper.total_count() == 1

    def test_load_accepts_string_path(self) -> None:
        """Loading should accept string path."""
        mapper1 = IdMapper()
        mapper1.add("organization", "123", "uuid-abc")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/id_map.json"
            mapper1.save(path)

            mapper2 = IdMapper()
            mapper2.load(path)  # String path

            assert mapper2.get("organization", "123") == "uuid-abc"


class TestIdMapperRepr:
    """Tests for string representation."""

    def test_repr_shows_total(self) -> None:
        """Repr should show total mapping count."""
        mapper = IdMapper()
        mapper.add("organization", "1", "uuid-1")
        mapper.add("configuration", "2", "uuid-2")

        assert "total_mappings=2" in repr(mapper)

    def test_repr_empty_mapper(self) -> None:
        """Repr should work for empty mapper."""
        mapper = IdMapper()

        assert "total_mappings=0" in repr(mapper)


class TestExceptions:
    """Tests for exception classes."""

    def test_invalid_entity_type_error_is_id_mapper_error(self) -> None:
        """InvalidEntityTypeError should be subclass of IdMapperError."""
        assert issubclass(InvalidEntityTypeError, IdMapperError)

    def test_invalid_entity_type_error_stores_type(self) -> None:
        """InvalidEntityTypeError should store the invalid type."""
        error = InvalidEntityTypeError("bad_type")

        assert error.entity_type == "bad_type"

    def test_invalid_entity_type_error_message_includes_valid_types(self) -> None:
        """Error message should list valid types."""
        error = InvalidEntityTypeError("bad_type")

        assert "organization" in str(error)
        assert "configuration" in str(error)
