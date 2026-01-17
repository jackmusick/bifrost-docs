"""Unit tests for organization matching module."""

import logging

import pytest

from itglue_migrate.org_matcher import MatchResult, OrgMatcher


class TestMatchResult:
    """Tests for MatchResult dataclass."""

    def test_matched_by_itglue_id_factory(self) -> None:
        """matched_by_itglue_id should create correct result."""
        result = MatchResult.matched_by_itglue_id("uuid-123")

        assert result.status == "matched"
        assert result.uuid == "uuid-123"
        assert result.match_type == "itglue_id"

    def test_matched_by_name_factory(self) -> None:
        """matched_by_name should create correct result."""
        result = MatchResult.matched_by_name("uuid-456")

        assert result.status == "matched"
        assert result.uuid == "uuid-456"
        assert result.match_type == "name"

    def test_needs_creation_factory(self) -> None:
        """needs_creation should create correct result."""
        result = MatchResult.needs_creation()

        assert result.status == "create"
        assert result.uuid is None
        assert result.match_type is None

    def test_match_result_is_frozen(self) -> None:
        """MatchResult should be immutable."""
        result = MatchResult.matched_by_itglue_id("uuid-123")

        with pytest.raises(AttributeError):
            result.status = "create"  # type: ignore[misc]

    def test_match_result_equality(self) -> None:
        """MatchResult instances with same values should be equal."""
        result1 = MatchResult.matched_by_itglue_id("uuid-123")
        result2 = MatchResult.matched_by_itglue_id("uuid-123")

        assert result1 == result2

    def test_match_result_hashable(self) -> None:
        """MatchResult should be hashable (usable in sets/dicts)."""
        result = MatchResult.matched_by_itglue_id("uuid-123")
        result_set = {result}

        assert result in result_set


class TestOrgMatcherInit:
    """Tests for OrgMatcher initialization."""

    def test_init_with_empty_list(self) -> None:
        """OrgMatcher should accept empty org list."""
        matcher = OrgMatcher([])

        assert matcher.get_mapping() == {}

    def test_init_builds_itglue_id_index(self) -> None:
        """OrgMatcher should index orgs by itglue_id metadata."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Org 1", "metadata": {"itglue_id": "123"}},
            {"id": "uuid-2", "name": "Org 2", "metadata": {"itglue_id": "456"}},
        ]
        matcher = OrgMatcher(existing_orgs)

        # Match by itglue_id should work
        result = matcher.match({"id": "123", "attributes": {"name": "Different Name"}})
        assert result.uuid == "uuid-1"
        assert result.match_type == "itglue_id"

    def test_init_builds_name_index(self) -> None:
        """OrgMatcher should index orgs by lowercase name."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Acme Corp", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        # Match by name should work (case-insensitive)
        result = matcher.match({"id": "999", "attributes": {"name": "ACME CORP"}})
        assert result.uuid == "uuid-1"
        assert result.match_type == "name"

    def test_init_skips_org_without_id(self, caplog: pytest.LogCaptureFixture) -> None:
        """OrgMatcher should skip and warn about orgs without id."""
        existing_orgs = [
            {"name": "No ID Org", "metadata": {}},
            {"id": "uuid-1", "name": "Valid Org", "metadata": {}},
        ]

        with caplog.at_level(logging.WARNING):
            matcher = OrgMatcher(existing_orgs)

        # Should still work for valid org
        result = matcher.match({"id": "1", "attributes": {"name": "Valid Org"}})
        assert result.uuid == "uuid-1"

        # Should have logged warning
        assert "Skipping existing org without id" in caplog.text

    def test_init_handles_none_metadata(self) -> None:
        """OrgMatcher should handle orgs with None metadata."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Org 1", "metadata": None},
        ]
        matcher = OrgMatcher(existing_orgs)

        result = matcher.match({"id": "1", "attributes": {"name": "Org 1"}})
        assert result.uuid == "uuid-1"

    def test_init_handles_missing_metadata(self) -> None:
        """OrgMatcher should handle orgs without metadata key."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Org 1"},
        ]
        matcher = OrgMatcher(existing_orgs)

        result = matcher.match({"id": "1", "attributes": {"name": "Org 1"}})
        assert result.uuid == "uuid-1"

    def test_init_warns_duplicate_itglue_id(self, caplog: pytest.LogCaptureFixture) -> None:
        """OrgMatcher should warn about duplicate itglue_id in existing orgs."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Org 1", "metadata": {"itglue_id": "123"}},
            {"id": "uuid-2", "name": "Org 2", "metadata": {"itglue_id": "123"}},
        ]

        with caplog.at_level(logging.WARNING):
            OrgMatcher(existing_orgs)

        assert "Duplicate itglue_id '123'" in caplog.text

    def test_init_converts_itglue_id_to_string(self) -> None:
        """OrgMatcher should convert integer itglue_id to string."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Org 1", "metadata": {"itglue_id": 123}},
        ]
        matcher = OrgMatcher(existing_orgs)

        # Should match with string ID
        result = matcher.match({"id": "123", "attributes": {"name": "Other"}})
        assert result.uuid == "uuid-1"


class TestOrgMatcherMatchByItGlueId:
    """Tests for matching by IT Glue ID (priority 1)."""

    def test_match_by_itglue_id_exact(self) -> None:
        """Should match when itglue_id in metadata matches."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Existing Name", "metadata": {"itglue_id": "123"}},
        ]
        matcher = OrgMatcher(existing_orgs)

        result = matcher.match({"id": "123", "attributes": {"name": "IT Glue Name"}})

        assert result.status == "matched"
        assert result.uuid == "uuid-1"
        assert result.match_type == "itglue_id"

    def test_match_by_itglue_id_takes_priority_over_name(self) -> None:
        """itglue_id match should take priority over name match."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Same Name", "metadata": {"itglue_id": "123"}},
            {"id": "uuid-2", "name": "Same Name", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        # Even though name matches uuid-2, itglue_id should win
        result = matcher.match({"id": "123", "attributes": {"name": "Same Name"}})

        assert result.uuid == "uuid-1"
        assert result.match_type == "itglue_id"

    def test_match_by_itglue_id_integer_input(self) -> None:
        """Should handle integer IT Glue ID in input."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Org", "metadata": {"itglue_id": "123"}},
        ]
        matcher = OrgMatcher(existing_orgs)

        result = matcher.match({"id": 123, "attributes": {"name": "Org"}})

        assert result.uuid == "uuid-1"
        assert result.match_type == "itglue_id"


class TestOrgMatcherMatchByName:
    """Tests for matching by name (priority 2)."""

    def test_match_by_name_exact(self) -> None:
        """Should match when name matches exactly."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Acme Corp", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        result = matcher.match({"id": "999", "attributes": {"name": "Acme Corp"}})

        assert result.status == "matched"
        assert result.uuid == "uuid-1"
        assert result.match_type == "name"

    def test_match_by_name_case_insensitive(self) -> None:
        """Should match names case-insensitively."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Acme Corp", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        # All these should match
        assert matcher.match({"id": "1", "attributes": {"name": "acme corp"}}).uuid == "uuid-1"
        assert matcher.match({"id": "2", "attributes": {"name": "ACME CORP"}}).uuid == "uuid-1"
        assert matcher.match({"id": "3", "attributes": {"name": "AcMe CoRp"}}).uuid == "uuid-1"

    def test_match_by_name_warns_on_duplicates(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should warn when multiple existing orgs have the same name."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Duplicate Name", "metadata": {}},
            {"id": "uuid-2", "name": "Duplicate Name", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        with caplog.at_level(logging.WARNING):
            result = matcher.match({"id": "1", "attributes": {"name": "Duplicate Name"}})

        # Should use first match
        assert result.uuid == "uuid-1"
        assert "Multiple existing orgs match name" in caplog.text

    def test_match_by_name_does_not_match_partial(self) -> None:
        """Should not match partial name matches."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Acme Corporation", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        result = matcher.match({"id": "1", "attributes": {"name": "Acme"}})

        assert result.status == "create"


class TestOrgMatcherNoMatch:
    """Tests for no-match scenarios (needs creation)."""

    def test_no_match_returns_create(self) -> None:
        """Should return create status when no match found."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Existing Org", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        result = matcher.match({"id": "999", "attributes": {"name": "New Org"}})

        assert result.status == "create"
        assert result.uuid is None
        assert result.match_type is None

    def test_no_match_empty_existing(self) -> None:
        """Should return create when no existing orgs."""
        matcher = OrgMatcher([])

        result = matcher.match({"id": "1", "attributes": {"name": "Any Org"}})

        assert result.status == "create"


class TestOrgMatcherEdgeCases:
    """Tests for edge cases and error handling."""

    def test_match_handles_none_name(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should handle IT Glue org with None name."""
        matcher = OrgMatcher([])

        with caplog.at_level(logging.WARNING):
            result = matcher.match({"id": "123", "attributes": {"name": None}})

        assert result.status == "create"
        assert "has no name" in caplog.text

    def test_match_handles_missing_name(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should handle IT Glue org without name key."""
        matcher = OrgMatcher([])

        with caplog.at_level(logging.WARNING):
            result = matcher.match({"id": "123", "attributes": {}})

        assert result.status == "create"
        assert "has no name" in caplog.text

    def test_match_handles_empty_name(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should handle IT Glue org with empty string name."""
        matcher = OrgMatcher([])

        with caplog.at_level(logging.WARNING):
            result = matcher.match({"id": "123", "attributes": {"name": ""}})

        assert result.status == "create"
        assert "has no name" in caplog.text

    def test_match_handles_none_attributes(self) -> None:
        """Should handle IT Glue org with None attributes."""
        matcher = OrgMatcher([])

        result = matcher.match({"id": "123", "attributes": None})

        assert result.status == "create"

    def test_match_handles_missing_attributes(self) -> None:
        """Should handle IT Glue org without attributes key."""
        matcher = OrgMatcher([])

        result = matcher.match({"id": "123"})

        assert result.status == "create"

    def test_match_handles_none_id(self) -> None:
        """Should handle IT Glue org with None id."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Test Org", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        # Can still match by name
        result = matcher.match({"id": None, "attributes": {"name": "Test Org"}})

        assert result.status == "matched"
        assert result.match_type == "name"

    def test_match_handles_missing_id(self) -> None:
        """Should handle IT Glue org without id key."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Test Org", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        # Can still match by name
        result = matcher.match({"attributes": {"name": "Test Org"}})

        assert result.status == "matched"
        assert result.match_type == "name"

    def test_match_whitespace_in_name(self) -> None:
        """Should preserve whitespace in name matching."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Acme  Corp", "metadata": {}},  # Double space
        ]
        matcher = OrgMatcher(existing_orgs)

        # Single space should not match double space
        result = matcher.match({"id": "1", "attributes": {"name": "Acme Corp"}})
        assert result.status == "create"

        # Double space should match
        result = matcher.match({"id": "2", "attributes": {"name": "Acme  Corp"}})
        assert result.uuid == "uuid-1"


class TestOrgMatcherGetMapping:
    """Tests for get_mapping method."""

    def test_get_mapping_returns_empty_initially(self) -> None:
        """get_mapping should return empty dict before any matches."""
        matcher = OrgMatcher([])

        assert matcher.get_mapping() == {}

    def test_get_mapping_includes_matched_orgs(self) -> None:
        """get_mapping should include all matched orgs."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Org 1", "metadata": {"itglue_id": "123"}},
            {"id": "uuid-2", "name": "Org 2", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        matcher.match({"id": "123", "attributes": {"name": "IT Glue Org 1"}})
        matcher.match({"id": "456", "attributes": {"name": "Org 2"}})
        matcher.match({"id": "789", "attributes": {"name": "New Org"}})

        mapping = matcher.get_mapping()

        assert len(mapping) == 3
        assert "IT Glue Org 1" in mapping
        assert "Org 2" in mapping
        assert "New Org" in mapping

    def test_get_mapping_returns_copy(self) -> None:
        """get_mapping should return a copy, not internal state."""
        matcher = OrgMatcher([])
        matcher.match({"id": "1", "attributes": {"name": "Org 1"}})

        mapping = matcher.get_mapping()
        mapping["Modified"] = MatchResult.needs_creation()

        # Original should be unchanged
        assert "Modified" not in matcher.get_mapping()

    def test_get_mapping_uses_name_as_key(self) -> None:
        """get_mapping should use org name as key."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Existing", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        matcher.match({"id": "123", "attributes": {"name": "My Org Name"}})

        mapping = matcher.get_mapping()
        assert "My Org Name" in mapping

    def test_get_mapping_uses_id_as_fallback_key(self) -> None:
        """get_mapping should use ID as key when name is missing."""
        matcher = OrgMatcher([])

        matcher.match({"id": "123", "attributes": {}})

        mapping = matcher.get_mapping()
        assert "123" in mapping


class TestOrgMatcherGetStats:
    """Tests for get_stats method."""

    def test_get_stats_initially_zero(self) -> None:
        """get_stats should return zeros before any matches."""
        matcher = OrgMatcher([])

        stats = matcher.get_stats()

        assert stats["matched_by_itglue_id"] == 0
        assert stats["matched_by_name"] == 0
        assert stats["create"] == 0

    def test_get_stats_counts_correctly(self) -> None:
        """get_stats should count each match type correctly."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Org 1", "metadata": {"itglue_id": "123"}},
            {"id": "uuid-2", "name": "Org 2", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        # Match by itglue_id
        matcher.match({"id": "123", "attributes": {"name": "X"}})
        # Match by name
        matcher.match({"id": "456", "attributes": {"name": "Org 2"}})
        # No match
        matcher.match({"id": "789", "attributes": {"name": "New"}})

        stats = matcher.get_stats()

        assert stats["matched_by_itglue_id"] == 1
        assert stats["matched_by_name"] == 1
        assert stats["create"] == 1


class TestOrgMatcherRepr:
    """Tests for string representation."""

    def test_repr_shows_counts(self) -> None:
        """repr should show matched and create counts."""
        existing_orgs = [
            {"id": "uuid-1", "name": "Org 1", "metadata": {}},
        ]
        matcher = OrgMatcher(existing_orgs)

        matcher.match({"id": "1", "attributes": {"name": "Org 1"}})
        matcher.match({"id": "2", "attributes": {"name": "New"}})

        repr_str = repr(matcher)

        assert "matched=1" in repr_str
        assert "create=1" in repr_str

    def test_repr_empty_matcher(self) -> None:
        """repr should work for matcher with no matches."""
        matcher = OrgMatcher([])

        repr_str = repr(matcher)

        assert "matched=0" in repr_str
        assert "create=0" in repr_str


class TestOrgMatcherIntegration:
    """Integration tests for typical usage scenarios."""

    def test_full_migration_scenario(self) -> None:
        """Test a typical migration with mixed match types."""
        # Simulate existing orgs in target system
        existing_orgs = [
            # Previously migrated org (has itglue_id)
            {"id": "uuid-1", "name": "Old Name", "metadata": {"itglue_id": "100"}},
            # Org that exists but wasn't migrated
            {"id": "uuid-2", "name": "Partner Corp", "metadata": {}},
            # Another unmigrated org
            {"id": "uuid-3", "name": "Client Inc", "metadata": {}},
        ]

        matcher = OrgMatcher(existing_orgs)

        # IT Glue orgs to migrate
        itglue_orgs = [
            {"id": "100", "attributes": {"name": "Renamed Org"}},  # Match by itglue_id
            {"id": "200", "attributes": {"name": "Partner Corp"}},  # Match by name
            {"id": "300", "attributes": {"name": "Brand New Org"}},  # No match
            {"id": "400", "attributes": {"name": "Client Inc"}},  # Match by name
        ]

        results = [matcher.match(org) for org in itglue_orgs]

        # Verify results
        assert results[0].match_type == "itglue_id"
        assert results[0].uuid == "uuid-1"

        assert results[1].match_type == "name"
        assert results[1].uuid == "uuid-2"

        assert results[2].status == "create"

        assert results[3].match_type == "name"
        assert results[3].uuid == "uuid-3"

        # Verify stats
        stats = matcher.get_stats()
        assert stats["matched_by_itglue_id"] == 1
        assert stats["matched_by_name"] == 2
        assert stats["create"] == 1

    def test_resume_migration_scenario(self) -> None:
        """Test resuming a migration where some orgs already migrated."""
        # First migration created these orgs
        existing_orgs = [
            {"id": "uuid-1", "name": "Org A", "metadata": {"itglue_id": "1"}},
            {"id": "uuid-2", "name": "Org B", "metadata": {"itglue_id": "2"}},
        ]

        matcher = OrgMatcher(existing_orgs)

        # Resume migration - all should match by itglue_id
        itglue_orgs = [
            {"id": "1", "attributes": {"name": "Org A (renamed)"}},
            {"id": "2", "attributes": {"name": "Org B"}},
            {"id": "3", "attributes": {"name": "Org C"}},  # New
        ]

        results = [matcher.match(org) for org in itglue_orgs]

        # First two should be matched (already migrated)
        assert results[0].status == "matched"
        assert results[1].status == "matched"

        # Third should need creation
        assert results[2].status == "create"
