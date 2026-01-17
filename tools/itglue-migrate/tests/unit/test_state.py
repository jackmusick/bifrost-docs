"""Unit tests for migration state persistence module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from itglue_migrate.id_map import IdMapper
from itglue_migrate.progress import Phase
from itglue_migrate.state import (
    STATE_VERSION,
    FailedEntity,
    MigrationState,
    MigrationStateError,
    PhaseStats,
    StateValidationError,
    StateVersionError,
)


class TestFailedEntity:
    """Tests for FailedEntity dataclass."""

    def test_init_with_defaults(self) -> None:
        """FailedEntity should initialize with timestamp default."""
        entity = FailedEntity(itglue_id="123", error="Test error")

        assert entity.itglue_id == "123"
        assert entity.error == "Test error"
        assert entity.timestamp  # Should have a timestamp

    def test_init_with_timestamp(self) -> None:
        """FailedEntity should accept custom timestamp."""
        entity = FailedEntity(
            itglue_id="123",
            error="Test error",
            timestamp="2024-01-15T10:30:00",
        )

        assert entity.timestamp == "2024-01-15T10:30:00"

    def test_to_dict(self) -> None:
        """to_dict should return all fields."""
        entity = FailedEntity(
            itglue_id="123",
            error="Test error",
            timestamp="2024-01-15T10:30:00",
        )

        result = entity.to_dict()

        assert result["itglue_id"] == "123"
        assert result["error"] == "Test error"
        assert result["timestamp"] == "2024-01-15T10:30:00"

    def test_from_dict(self) -> None:
        """from_dict should create entity from dictionary."""
        data = {
            "itglue_id": "123",
            "error": "Test error",
            "timestamp": "2024-01-15T10:30:00",
        }

        entity = FailedEntity.from_dict(data)

        assert entity.itglue_id == "123"
        assert entity.error == "Test error"
        assert entity.timestamp == "2024-01-15T10:30:00"

    def test_from_dict_missing_timestamp(self) -> None:
        """from_dict should handle missing timestamp."""
        data = {"itglue_id": "123", "error": "Test error"}

        entity = FailedEntity.from_dict(data)

        assert entity.itglue_id == "123"
        assert entity.timestamp  # Should have default timestamp


class TestPhaseStats:
    """Tests for PhaseStats dataclass."""

    def test_init(self) -> None:
        """PhaseStats should initialize with counts."""
        stats = PhaseStats(completed_count=10, failed_count=2)

        assert stats.completed_count == 10
        assert stats.failed_count == 2

    def test_total_processed(self) -> None:
        """total_processed should sum completed and failed."""
        stats = PhaseStats(completed_count=10, failed_count=2)

        assert stats.total_processed == 12


class TestMigrationStateInit:
    """Tests for MigrationState initialization."""

    def test_init_defaults(self) -> None:
        """MigrationState should initialize with defaults."""
        state = MigrationState()

        assert state.export_path is None
        assert state.api_url is None
        assert state.current_phase is None
        assert isinstance(state.id_mapper, IdMapper)
        assert state.warnings == []

    def test_init_with_params(self) -> None:
        """MigrationState should accept initialization params."""
        mapper = IdMapper()
        state = MigrationState(
            export_path="/path/to/export",
            api_url="https://api.example.com",
            id_mapper=mapper,
        )

        assert state.export_path == "/path/to/export"
        assert state.api_url == "https://api.example.com"
        assert state.id_mapper is mapper

    def test_init_timestamps(self) -> None:
        """MigrationState should set timestamps on init."""
        state = MigrationState()

        assert isinstance(state.start_time, datetime)
        assert isinstance(state.last_update_time, datetime)

    def test_init_empty_completed_for_all_phases(self) -> None:
        """MigrationState should have empty completed for all phases."""
        state = MigrationState()

        for phase in Phase:
            assert state.get_completed_ids(phase) == set()

    def test_init_empty_failed_for_all_phases(self) -> None:
        """MigrationState should have empty failed for all phases."""
        state = MigrationState()

        for phase in Phase:
            assert state.get_failed_ids(phase) == []

    def test_init_empty_attachments_completed(self) -> None:
        """MigrationState should have empty attachments_completed on init."""
        state = MigrationState()

        assert state.get_attachments_completed_count() == 0

    def test_init_empty_attachments_failed(self) -> None:
        """MigrationState should have empty attachments_failed on init."""
        state = MigrationState()

        assert state.get_attachments_failed_count() == 0


class TestMigrationStateMarkCompleted:
    """Tests for mark_completed method."""

    def test_mark_completed_adds_id(self) -> None:
        """mark_completed should add ID to completed set."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "123")

        assert state.is_completed(Phase.ORGANIZATIONS, "123")

    def test_mark_completed_multiple_ids(self) -> None:
        """mark_completed should handle multiple IDs."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")
        state.mark_completed(Phase.ORGANIZATIONS, "2")
        state.mark_completed(Phase.ORGANIZATIONS, "3")

        assert state.is_completed(Phase.ORGANIZATIONS, "1")
        assert state.is_completed(Phase.ORGANIZATIONS, "2")
        assert state.is_completed(Phase.ORGANIZATIONS, "3")

    def test_mark_completed_different_phases(self) -> None:
        """mark_completed should track per phase."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")
        state.mark_completed(Phase.CONFIGURATIONS, "1")

        assert state.is_completed(Phase.ORGANIZATIONS, "1")
        assert state.is_completed(Phase.CONFIGURATIONS, "1")
        assert not state.is_completed(Phase.DOCUMENTS, "1")

    def test_mark_completed_converts_int_to_string(self) -> None:
        """mark_completed should convert integer IDs to strings."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, 123)  # type: ignore[arg-type]

        assert state.is_completed(Phase.ORGANIZATIONS, "123")
        assert state.is_completed(Phase.ORGANIZATIONS, 123)  # type: ignore[arg-type]

    def test_mark_completed_removes_from_failed(self) -> None:
        """mark_completed should remove ID from failed (retry success)."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "123", "Initial error")
        assert state.is_failed(Phase.ORGANIZATIONS, "123")

        state.mark_completed(Phase.ORGANIZATIONS, "123")

        assert state.is_completed(Phase.ORGANIZATIONS, "123")
        assert not state.is_failed(Phase.ORGANIZATIONS, "123")

    def test_mark_completed_updates_timestamp(self) -> None:
        """mark_completed should update last_update_time."""
        state = MigrationState()
        initial_time = state.last_update_time

        state.mark_completed(Phase.ORGANIZATIONS, "123")

        assert state.last_update_time >= initial_time

    def test_mark_completed_empty_id_raises(self) -> None:
        """mark_completed with empty ID should raise ValueError."""
        state = MigrationState()

        with pytest.raises(ValueError, match="itglue_id cannot be empty"):
            state.mark_completed(Phase.ORGANIZATIONS, "")

    def test_mark_completed_invalid_phase_raises(self) -> None:
        """mark_completed with invalid phase should raise TypeError."""
        state = MigrationState()

        with pytest.raises(TypeError, match="Expected Phase enum"):
            state.mark_completed("organizations", "123")  # type: ignore[arg-type]

    @pytest.mark.parametrize("phase", list(Phase))
    def test_mark_completed_all_phases(self, phase: Phase) -> None:
        """mark_completed should work for all phases."""
        state = MigrationState()
        state.mark_completed(phase, "123")

        assert state.is_completed(phase, "123")


class TestMigrationStateMarkFailed:
    """Tests for mark_failed method."""

    def test_mark_failed_adds_entity(self) -> None:
        """mark_failed should add entity to failed dict."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "123", "Connection error")

        assert state.is_failed(Phase.ORGANIZATIONS, "123")

    def test_mark_failed_stores_error(self) -> None:
        """mark_failed should store error message."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "123", "Connection error")

        assert state.get_failure_error(Phase.ORGANIZATIONS, "123") == "Connection error"

    def test_mark_failed_multiple_entities(self) -> None:
        """mark_failed should handle multiple failures."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error 1")
        state.mark_failed(Phase.ORGANIZATIONS, "2", "Error 2")

        assert state.is_failed(Phase.ORGANIZATIONS, "1")
        assert state.is_failed(Phase.ORGANIZATIONS, "2")

    def test_mark_failed_overwrites_previous_error(self) -> None:
        """mark_failed should overwrite previous error for same ID."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "123", "First error")
        state.mark_failed(Phase.ORGANIZATIONS, "123", "Second error")

        assert state.get_failure_error(Phase.ORGANIZATIONS, "123") == "Second error"

    def test_mark_failed_converts_int_to_string(self) -> None:
        """mark_failed should convert integer IDs to strings."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, 123, "Error")  # type: ignore[arg-type]

        assert state.is_failed(Phase.ORGANIZATIONS, "123")

    def test_mark_failed_updates_timestamp(self) -> None:
        """mark_failed should update last_update_time."""
        state = MigrationState()
        initial_time = state.last_update_time

        state.mark_failed(Phase.ORGANIZATIONS, "123", "Error")

        assert state.last_update_time >= initial_time

    def test_mark_failed_empty_id_raises(self) -> None:
        """mark_failed with empty ID should raise ValueError."""
        state = MigrationState()

        with pytest.raises(ValueError, match="itglue_id cannot be empty"):
            state.mark_failed(Phase.ORGANIZATIONS, "", "Error")

    def test_mark_failed_empty_error_raises(self) -> None:
        """mark_failed with empty error should raise ValueError."""
        state = MigrationState()

        with pytest.raises(ValueError, match="error cannot be empty"):
            state.mark_failed(Phase.ORGANIZATIONS, "123", "")

    def test_mark_failed_invalid_phase_raises(self) -> None:
        """mark_failed with invalid phase should raise TypeError."""
        state = MigrationState()

        with pytest.raises(TypeError, match="Expected Phase enum"):
            state.mark_failed("organizations", "123", "Error")  # type: ignore[arg-type]


class TestMigrationStateIsCompleted:
    """Tests for is_completed method."""

    def test_is_completed_true_when_completed(self) -> None:
        """is_completed should return True for completed entity."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "123")

        assert state.is_completed(Phase.ORGANIZATIONS, "123") is True

    def test_is_completed_false_when_not_completed(self) -> None:
        """is_completed should return False for non-completed entity."""
        state = MigrationState()

        assert state.is_completed(Phase.ORGANIZATIONS, "123") is False

    def test_is_completed_false_for_wrong_phase(self) -> None:
        """is_completed should return False for wrong phase."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "123")

        assert state.is_completed(Phase.CONFIGURATIONS, "123") is False

    def test_is_completed_invalid_phase_raises(self) -> None:
        """is_completed with invalid phase should raise TypeError."""
        state = MigrationState()

        with pytest.raises(TypeError, match="Expected Phase enum"):
            state.is_completed("organizations", "123")  # type: ignore[arg-type]


class TestMigrationStateIsFailed:
    """Tests for is_failed method."""

    def test_is_failed_true_when_failed(self) -> None:
        """is_failed should return True for failed entity."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "123", "Error")

        assert state.is_failed(Phase.ORGANIZATIONS, "123") is True

    def test_is_failed_false_when_not_failed(self) -> None:
        """is_failed should return False for non-failed entity."""
        state = MigrationState()

        assert state.is_failed(Phase.ORGANIZATIONS, "123") is False

    def test_is_failed_false_for_wrong_phase(self) -> None:
        """is_failed should return False for wrong phase."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "123", "Error")

        assert state.is_failed(Phase.CONFIGURATIONS, "123") is False


class TestMigrationStateGetFailureError:
    """Tests for get_failure_error method."""

    def test_get_failure_error_returns_error(self) -> None:
        """get_failure_error should return error message."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "123", "Connection timeout")

        assert state.get_failure_error(Phase.ORGANIZATIONS, "123") == "Connection timeout"

    def test_get_failure_error_returns_none_when_not_failed(self) -> None:
        """get_failure_error should return None for non-failed entity."""
        state = MigrationState()

        assert state.get_failure_error(Phase.ORGANIZATIONS, "123") is None


class TestMigrationStateGetFailedIds:
    """Tests for get_failed_ids method."""

    def test_get_failed_ids_returns_list(self) -> None:
        """get_failed_ids should return list of failed IDs."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error 1")
        state.mark_failed(Phase.ORGANIZATIONS, "2", "Error 2")

        failed_ids = state.get_failed_ids(Phase.ORGANIZATIONS)

        assert set(failed_ids) == {"1", "2"}

    def test_get_failed_ids_empty_when_no_failures(self) -> None:
        """get_failed_ids should return empty list when no failures."""
        state = MigrationState()

        assert state.get_failed_ids(Phase.ORGANIZATIONS) == []


class TestMigrationStateGetCompletedIds:
    """Tests for get_completed_ids method."""

    def test_get_completed_ids_returns_set(self) -> None:
        """get_completed_ids should return set of completed IDs."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")
        state.mark_completed(Phase.ORGANIZATIONS, "2")

        completed_ids = state.get_completed_ids(Phase.ORGANIZATIONS)

        assert completed_ids == {"1", "2"}

    def test_get_completed_ids_returns_copy(self) -> None:
        """get_completed_ids should return copy, not internal set."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")

        completed_ids = state.get_completed_ids(Phase.ORGANIZATIONS)
        completed_ids.add("999")

        assert not state.is_completed(Phase.ORGANIZATIONS, "999")


class TestMigrationStateGetPhaseStats:
    """Tests for get_phase_stats method."""

    def test_get_phase_stats_returns_stats(self) -> None:
        """get_phase_stats should return PhaseStats."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")
        state.mark_completed(Phase.ORGANIZATIONS, "2")
        state.mark_failed(Phase.ORGANIZATIONS, "3", "Error")

        stats = state.get_phase_stats(Phase.ORGANIZATIONS)

        assert isinstance(stats, PhaseStats)
        assert stats.completed_count == 2
        assert stats.failed_count == 1

    def test_get_phase_stats_empty_phase(self) -> None:
        """get_phase_stats should return zeros for empty phase."""
        state = MigrationState()

        stats = state.get_phase_stats(Phase.ORGANIZATIONS)

        assert stats.completed_count == 0
        assert stats.failed_count == 0

    def test_get_phase_stats_invalid_phase_raises(self) -> None:
        """get_phase_stats with invalid phase should raise TypeError."""
        state = MigrationState()

        with pytest.raises(TypeError, match="Expected Phase enum"):
            state.get_phase_stats("organizations")  # type: ignore[arg-type]


class TestMigrationStateWarnings:
    """Tests for warning methods."""

    def test_add_warning(self) -> None:
        """add_warning should add warning to list."""
        state = MigrationState()
        state.add_warning("First warning")
        state.add_warning("Second warning")

        assert state.warnings == ["First warning", "Second warning"]

    def test_add_warning_empty_raises(self) -> None:
        """add_warning with empty message should raise ValueError."""
        state = MigrationState()

        with pytest.raises(ValueError, match="message cannot be empty"):
            state.add_warning("")

    def test_warnings_returns_copy(self) -> None:
        """warnings property should return copy."""
        state = MigrationState()
        state.add_warning("Test")

        warnings = state.warnings
        warnings.append("Modified")

        assert state.warnings == ["Test"]

    def test_clear_warnings(self) -> None:
        """clear_warnings should remove all warnings."""
        state = MigrationState()
        state.add_warning("Warning 1")
        state.add_warning("Warning 2")

        state.clear_warnings()

        assert state.warnings == []


class TestMigrationStateClearFailures:
    """Tests for clear_failures method."""

    def test_clear_failures_removes_all_for_phase(self) -> None:
        """clear_failures should remove all failures for phase."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error 1")
        state.mark_failed(Phase.ORGANIZATIONS, "2", "Error 2")

        state.clear_failures(Phase.ORGANIZATIONS)

        assert not state.is_failed(Phase.ORGANIZATIONS, "1")
        assert not state.is_failed(Phase.ORGANIZATIONS, "2")

    def test_clear_failures_returns_count(self) -> None:
        """clear_failures should return number cleared."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error 1")
        state.mark_failed(Phase.ORGANIZATIONS, "2", "Error 2")

        count = state.clear_failures(Phase.ORGANIZATIONS)

        assert count == 2

    def test_clear_failures_does_not_affect_other_phases(self) -> None:
        """clear_failures should not affect other phases."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error")
        state.mark_failed(Phase.CONFIGURATIONS, "2", "Error")

        state.clear_failures(Phase.ORGANIZATIONS)

        assert state.is_failed(Phase.CONFIGURATIONS, "2")

    def test_clear_failures_invalid_phase_raises(self) -> None:
        """clear_failures with invalid phase should raise TypeError."""
        state = MigrationState()

        with pytest.raises(TypeError, match="Expected Phase enum"):
            state.clear_failures("organizations")  # type: ignore[arg-type]


class TestMigrationStateClearAllFailures:
    """Tests for clear_all_failures method."""

    def test_clear_all_failures_removes_all(self) -> None:
        """clear_all_failures should remove all failures."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error")
        state.mark_failed(Phase.CONFIGURATIONS, "2", "Error")
        state.mark_failed(Phase.DOCUMENTS, "3", "Error")

        state.clear_all_failures()

        assert state.get_total_failed() == 0

    def test_clear_all_failures_returns_total_count(self) -> None:
        """clear_all_failures should return total count cleared."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error")
        state.mark_failed(Phase.CONFIGURATIONS, "2", "Error")

        count = state.clear_all_failures()

        assert count == 2


class TestMigrationStateResetPhase:
    """Tests for reset_phase method."""

    def test_reset_phase_clears_completed(self) -> None:
        """reset_phase should clear completed entities."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")

        state.reset_phase(Phase.ORGANIZATIONS)

        assert not state.is_completed(Phase.ORGANIZATIONS, "1")

    def test_reset_phase_clears_failed(self) -> None:
        """reset_phase should clear failed entities."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error")

        state.reset_phase(Phase.ORGANIZATIONS)

        assert not state.is_failed(Phase.ORGANIZATIONS, "1")

    def test_reset_phase_does_not_affect_other_phases(self) -> None:
        """reset_phase should not affect other phases."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")
        state.mark_completed(Phase.CONFIGURATIONS, "2")

        state.reset_phase(Phase.ORGANIZATIONS)

        assert state.is_completed(Phase.CONFIGURATIONS, "2")


class TestMigrationStateCurrentPhase:
    """Tests for current_phase property."""

    def test_current_phase_initially_none(self) -> None:
        """current_phase should be None initially."""
        state = MigrationState()

        assert state.current_phase is None

    def test_current_phase_can_be_set(self) -> None:
        """current_phase should be settable."""
        state = MigrationState()

        state.current_phase = Phase.ORGANIZATIONS

        assert state.current_phase == Phase.ORGANIZATIONS

    def test_current_phase_can_be_cleared(self) -> None:
        """current_phase should be clearable."""
        state = MigrationState()
        state.current_phase = Phase.ORGANIZATIONS

        state.current_phase = None

        assert state.current_phase is None


class TestMigrationStateTotals:
    """Tests for total count methods."""

    def test_get_total_completed(self) -> None:
        """get_total_completed should sum across all phases."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")
        state.mark_completed(Phase.ORGANIZATIONS, "2")
        state.mark_completed(Phase.CONFIGURATIONS, "3")

        assert state.get_total_completed() == 3

    def test_get_total_failed(self) -> None:
        """get_total_failed should sum across all phases."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error")
        state.mark_failed(Phase.CONFIGURATIONS, "2", "Error")

        assert state.get_total_failed() == 2

    def test_get_all_stats(self) -> None:
        """get_all_stats should return stats for all phases."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")
        state.mark_failed(Phase.CONFIGURATIONS, "2", "Error")

        all_stats = state.get_all_stats()

        assert len(all_stats) == len(Phase)
        assert all_stats[Phase.ORGANIZATIONS].completed_count == 1
        assert all_stats[Phase.CONFIGURATIONS].failed_count == 1


class TestMigrationStateIsPhaseStarted:
    """Tests for is_phase_started method."""

    def test_is_phase_started_false_initially(self) -> None:
        """is_phase_started should be False for unstarted phase."""
        state = MigrationState()

        assert state.is_phase_started(Phase.ORGANIZATIONS) is False

    def test_is_phase_started_true_with_completed(self) -> None:
        """is_phase_started should be True when has completed entities."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")

        assert state.is_phase_started(Phase.ORGANIZATIONS) is True

    def test_is_phase_started_true_with_failed(self) -> None:
        """is_phase_started should be True when has failed entities."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error")

        assert state.is_phase_started(Phase.ORGANIZATIONS) is True


class TestMigrationStateSerialization:
    """Tests for to_dict and from_dict methods."""

    def test_to_dict_includes_version(self) -> None:
        """to_dict should include version."""
        state = MigrationState()

        result = state.to_dict()

        assert result["version"] == STATE_VERSION

    def test_to_dict_includes_paths(self) -> None:
        """to_dict should include export_path and api_url."""
        state = MigrationState(
            export_path="/path/to/export",
            api_url="https://api.example.com",
        )

        result = state.to_dict()

        assert result["export_path"] == "/path/to/export"
        assert result["api_url"] == "https://api.example.com"

    def test_to_dict_includes_timestamps(self) -> None:
        """to_dict should include timestamps."""
        state = MigrationState()

        result = state.to_dict()

        assert "start_time" in result
        assert "last_update_time" in result

    def test_to_dict_includes_current_phase(self) -> None:
        """to_dict should include current_phase."""
        state = MigrationState()
        state.current_phase = Phase.ORGANIZATIONS

        result = state.to_dict()

        assert result["current_phase"] == "Organizations"

    def test_to_dict_includes_completed(self) -> None:
        """to_dict should include completed entities."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")
        state.mark_completed(Phase.ORGANIZATIONS, "2")

        result = state.to_dict()

        assert "1" in result["completed"]["Organizations"]
        assert "2" in result["completed"]["Organizations"]

    def test_to_dict_includes_failed(self) -> None:
        """to_dict should include failed entities."""
        state = MigrationState()
        state.mark_failed(Phase.ORGANIZATIONS, "1", "Error 1")

        result = state.to_dict()

        failed = result["failed"]["Organizations"]
        assert len(failed) == 1
        assert failed[0]["itglue_id"] == "1"
        assert failed[0]["error"] == "Error 1"

    def test_to_dict_includes_warnings(self) -> None:
        """to_dict should include warnings."""
        state = MigrationState()
        state.add_warning("Test warning")

        result = state.to_dict()

        assert result["warnings"] == ["Test warning"]

    def test_from_dict_restores_state(self) -> None:
        """from_dict should restore state from dict."""
        original = MigrationState(
            export_path="/path/to/export",
            api_url="https://api.example.com",
        )
        original.mark_completed(Phase.ORGANIZATIONS, "1")
        original.mark_failed(Phase.CONFIGURATIONS, "2", "Error")
        original.add_warning("Test warning")
        original.current_phase = Phase.DOCUMENTS

        data = original.to_dict()
        restored = MigrationState.from_dict(data)

        assert restored.export_path == "/path/to/export"
        assert restored.api_url == "https://api.example.com"
        assert restored.is_completed(Phase.ORGANIZATIONS, "1")
        assert restored.is_failed(Phase.CONFIGURATIONS, "2")
        assert restored.warnings == ["Test warning"]

    def test_from_dict_wrong_version_raises(self) -> None:
        """from_dict with wrong version should raise StateVersionError."""
        data = {"version": 99, "completed": {}, "failed": {}, "warnings": []}

        with pytest.raises(StateVersionError) as exc_info:
            MigrationState.from_dict(data)

        assert exc_info.value.version == 99

    def test_from_dict_invalid_completed_raises(self) -> None:
        """from_dict with invalid completed should raise StateValidationError."""
        data = {"version": STATE_VERSION, "completed": "invalid", "failed": {}, "warnings": []}

        with pytest.raises(StateValidationError, match="Invalid completed data"):
            MigrationState.from_dict(data)

    def test_from_dict_invalid_failed_raises(self) -> None:
        """from_dict with invalid failed should raise StateValidationError."""
        data = {"version": STATE_VERSION, "completed": {}, "failed": "invalid", "warnings": []}

        with pytest.raises(StateValidationError, match="Invalid failed data"):
            MigrationState.from_dict(data)

    def test_from_dict_skips_unknown_phases(self) -> None:
        """from_dict should skip unknown phases for forward compatibility."""
        data = {
            "version": STATE_VERSION,
            "completed": {
                "Organizations": ["1"],
                "FuturePhase": ["2"],  # Unknown phase
            },
            "failed": {},
            "warnings": [],
        }

        state = MigrationState.from_dict(data)

        assert state.is_completed(Phase.ORGANIZATIONS, "1")
        assert state.get_total_completed() == 1

    def test_to_dict_includes_attachments_completed(self) -> None:
        """to_dict should include attachments_completed."""
        state = MigrationState()
        state.mark_attachment_completed("configurations", "123", "file1.pdf")
        state.mark_attachment_completed("configurations", "123", "file2.pdf")

        result = state.to_dict()

        assert "attachments_completed" in result
        assert "configurations:123" in result["attachments_completed"]
        assert set(result["attachments_completed"]["configurations:123"]) == {"file1.pdf", "file2.pdf"}

    def test_to_dict_includes_attachments_failed(self) -> None:
        """to_dict should include attachments_failed."""
        state = MigrationState()
        state.mark_attachment_failed("configurations", "123", "file.pdf", "Upload error")

        result = state.to_dict()

        assert "attachments_failed" in result
        assert "configurations:123" in result["attachments_failed"]
        assert len(result["attachments_failed"]["configurations:123"]) == 1
        assert result["attachments_failed"]["configurations:123"][0]["filename"] == "file.pdf"

    def test_from_dict_restores_attachments(self) -> None:
        """from_dict should restore attachment state."""
        original = MigrationState()
        original.mark_attachment_completed("configurations", "1", "done.pdf")
        original.mark_attachment_failed("documents", "2", "failed.pdf", "Error")

        data = original.to_dict()
        restored = MigrationState.from_dict(data)

        assert restored.is_attachment_completed("configurations", "1", "done.pdf")
        assert restored.is_attachment_failed("documents", "2", "failed.pdf")
        assert restored.get_attachment_failure_error("documents", "2", "failed.pdf") == "Error"


class TestMigrationStatePersistence:
    """Tests for save/load functionality."""

    def test_save_creates_file(self) -> None:
        """save should create JSON file."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "123")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            state.save(path)

            assert path.exists()

    def test_save_creates_parent_directories(self) -> None:
        """save should create parent directories."""
        state = MigrationState()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "state.json"
            state.save(path)

            assert path.exists()

    def test_save_writes_valid_json(self) -> None:
        """save should write valid JSON."""
        state = MigrationState()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            state.save(path)

            with path.open() as f:
                data = json.load(f)

            assert "version" in data
            assert "completed" in data
            assert "failed" in data

    def test_save_also_saves_id_mapper(self) -> None:
        """save should also save id_mapper state."""
        state = MigrationState()
        state.id_mapper.add("organization", "1", "uuid-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            state.save(path)

            id_map_path = path.with_suffix(".id_map.json")
            assert id_map_path.exists()

    def test_load_restores_state(self) -> None:
        """load should restore saved state."""
        state1 = MigrationState(
            export_path="/export",
            api_url="https://api.example.com",
        )
        state1.mark_completed(Phase.ORGANIZATIONS, "1")
        state1.mark_failed(Phase.CONFIGURATIONS, "2", "Error")
        state1.add_warning("Warning")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            state1.save(path)

            state2 = MigrationState.load(path)

            assert state2.export_path == "/export"
            assert state2.api_url == "https://api.example.com"
            assert state2.is_completed(Phase.ORGANIZATIONS, "1")
            assert state2.is_failed(Phase.CONFIGURATIONS, "2")
            assert state2.warnings == ["Warning"]

    def test_load_restores_id_mapper(self) -> None:
        """load should also restore id_mapper state."""
        state1 = MigrationState()
        state1.id_mapper.add("organization", "1", "uuid-1")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            state1.save(path)

            state2 = MigrationState.load(path)

            assert state2.id_mapper.get("organization", "1") == "uuid-1"

    def test_load_works_without_id_mapper_file(self) -> None:
        """load should work when id_mapper file doesn't exist."""
        state1 = MigrationState()
        state1.mark_completed(Phase.ORGANIZATIONS, "1")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            state1.save(path)

            # Remove id_mapper file
            id_map_path = path.with_suffix(".id_map.json")
            id_map_path.unlink()

            state2 = MigrationState.load(path)

            assert state2.is_completed(Phase.ORGANIZATIONS, "1")
            assert state2.id_mapper.total_count() == 0

    def test_load_nonexistent_file_raises(self) -> None:
        """load with nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            MigrationState.load("/nonexistent/path/state.json")

    def test_load_invalid_json_raises(self) -> None:
        """load with invalid JSON should raise JSONDecodeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            path.write_text("not valid json")

            with pytest.raises(json.JSONDecodeError):
                MigrationState.load(path)

    def test_load_wrong_format_raises(self) -> None:
        """load with wrong format should raise StateValidationError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            path.write_text("[]")  # Array instead of dict

            with pytest.raises(StateValidationError, match="expected dict"):
                MigrationState.load(path)

    def test_load_accepts_string_path(self) -> None:
        """load should accept string path."""
        state1 = MigrationState()
        state1.mark_completed(Phase.ORGANIZATIONS, "1")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/state.json"
            state1.save(path)

            state2 = MigrationState.load(path)

            assert state2.is_completed(Phase.ORGANIZATIONS, "1")

    def test_save_accepts_string_path(self) -> None:
        """save should accept string path."""
        state = MigrationState()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/state.json"
            state.save(path)

            assert Path(path).exists()


class TestMigrationStateRepr:
    """Tests for string representation."""

    def test_repr_shows_counts(self) -> None:
        """repr should show completed, failed, and warning counts."""
        state = MigrationState()
        state.mark_completed(Phase.ORGANIZATIONS, "1")
        state.mark_failed(Phase.CONFIGURATIONS, "2", "Error")
        state.add_warning("Warning")

        result = repr(state)

        assert "completed=1" in result
        assert "failed=1" in result
        assert "warnings=1" in result

    def test_repr_empty_state(self) -> None:
        """repr should work for empty state."""
        state = MigrationState()

        result = repr(state)

        assert "completed=0" in result
        assert "failed=0" in result
        assert "warnings=0" in result


class TestExceptions:
    """Tests for exception classes."""

    def test_state_version_error_is_migration_state_error(self) -> None:
        """StateVersionError should be subclass of MigrationStateError."""
        assert issubclass(StateVersionError, MigrationStateError)

    def test_state_version_error_stores_version(self) -> None:
        """StateVersionError should store the version."""
        error = StateVersionError(99)

        assert error.version == 99

    def test_state_version_error_message(self) -> None:
        """StateVersionError message should include version info."""
        error = StateVersionError(99)

        assert "99" in str(error)
        assert str(STATE_VERSION) in str(error)

    def test_state_validation_error_is_migration_state_error(self) -> None:
        """StateValidationError should be subclass of MigrationStateError."""
        assert issubclass(StateValidationError, MigrationStateError)


class TestFailedAttachment:
    """Tests for FailedAttachment dataclass."""

    def test_init_with_defaults(self) -> None:
        """FailedAttachment should initialize with timestamp default."""
        from itglue_migrate.state import FailedAttachment

        attachment = FailedAttachment(filename="file.pdf", error="Upload failed")

        assert attachment.filename == "file.pdf"
        assert attachment.error == "Upload failed"
        assert attachment.timestamp  # Should have a timestamp

    def test_to_dict(self) -> None:
        """to_dict should return all fields."""
        from itglue_migrate.state import FailedAttachment

        attachment = FailedAttachment(
            filename="file.pdf",
            error="Upload failed",
            timestamp="2024-01-15T10:30:00",
        )

        result = attachment.to_dict()

        assert result["filename"] == "file.pdf"
        assert result["error"] == "Upload failed"
        assert result["timestamp"] == "2024-01-15T10:30:00"

    def test_from_dict(self) -> None:
        """from_dict should create attachment from dictionary."""
        from itglue_migrate.state import FailedAttachment

        data = {
            "filename": "file.pdf",
            "error": "Upload failed",
            "timestamp": "2024-01-15T10:30:00",
        }

        attachment = FailedAttachment.from_dict(data)

        assert attachment.filename == "file.pdf"
        assert attachment.error == "Upload failed"
        assert attachment.timestamp == "2024-01-15T10:30:00"

    def test_init_with_timestamp(self) -> None:
        """FailedAttachment should accept custom timestamp."""
        from itglue_migrate.state import FailedAttachment

        attachment = FailedAttachment(
            filename="file.pdf",
            error="Upload failed",
            timestamp="2024-01-15T10:30:00",
        )

        assert attachment.timestamp == "2024-01-15T10:30:00"

    def test_from_dict_missing_timestamp(self) -> None:
        """from_dict should handle missing timestamp."""
        from itglue_migrate.state import FailedAttachment

        data = {"filename": "file.pdf", "error": "Upload failed"}

        attachment = FailedAttachment.from_dict(data)

        assert attachment.filename == "file.pdf"
        assert attachment.timestamp  # Should have default timestamp


class TestMigrationStateMarkAttachmentCompleted:
    """Tests for mark_attachment_completed method."""

    def test_mark_attachment_completed_adds_filename(self) -> None:
        """mark_attachment_completed should add filename to set."""
        state = MigrationState()
        state.mark_attachment_completed("configurations", "123", "file.pdf")

        assert state.is_attachment_completed("configurations", "123", "file.pdf")

    def test_mark_attachment_completed_multiple_files(self) -> None:
        """mark_attachment_completed should handle multiple files per entity."""
        state = MigrationState()
        state.mark_attachment_completed("configurations", "123", "file1.pdf")
        state.mark_attachment_completed("configurations", "123", "file2.pdf")

        assert state.is_attachment_completed("configurations", "123", "file1.pdf")
        assert state.is_attachment_completed("configurations", "123", "file2.pdf")
        assert state.get_attachments_completed_count() == 2

    def test_mark_attachment_completed_different_entities(self) -> None:
        """mark_attachment_completed should track per entity."""
        state = MigrationState()
        state.mark_attachment_completed("configurations", "1", "file.pdf")
        state.mark_attachment_completed("documents", "2", "doc.pdf")

        assert state.is_attachment_completed("configurations", "1", "file.pdf")
        assert state.is_attachment_completed("documents", "2", "doc.pdf")
        assert not state.is_attachment_completed("configurations", "2", "file.pdf")

    def test_mark_attachment_completed_removes_from_failed(self) -> None:
        """mark_attachment_completed should remove from failed (retry success)."""
        state = MigrationState()
        state.mark_attachment_failed("configurations", "123", "file.pdf", "Initial error")
        assert state.is_attachment_failed("configurations", "123", "file.pdf")

        state.mark_attachment_completed("configurations", "123", "file.pdf")

        assert state.is_attachment_completed("configurations", "123", "file.pdf")
        assert not state.is_attachment_failed("configurations", "123", "file.pdf")

    def test_mark_attachment_completed_empty_entity_type_raises(self) -> None:
        """mark_attachment_completed with empty entity_type should raise ValueError."""
        state = MigrationState()

        with pytest.raises(ValueError, match="entity_type cannot be empty"):
            state.mark_attachment_completed("", "123", "file.pdf")

    def test_mark_attachment_completed_empty_itglue_id_raises(self) -> None:
        """mark_attachment_completed with empty itglue_id should raise ValueError."""
        state = MigrationState()

        with pytest.raises(ValueError, match="itglue_id cannot be empty"):
            state.mark_attachment_completed("configurations", "", "file.pdf")

    def test_mark_attachment_completed_empty_filename_raises(self) -> None:
        """mark_attachment_completed with empty filename should raise ValueError."""
        state = MigrationState()

        with pytest.raises(ValueError, match="filename cannot be empty"):
            state.mark_attachment_completed("configurations", "123", "")


class TestMigrationStateMarkAttachmentFailed:
    """Tests for mark_attachment_failed method."""

    def test_mark_attachment_failed_adds_entry(self) -> None:
        """mark_attachment_failed should add entry to failed dict."""
        state = MigrationState()
        state.mark_attachment_failed("configurations", "123", "file.pdf", "Upload timeout")

        assert state.is_attachment_failed("configurations", "123", "file.pdf")

    def test_mark_attachment_failed_stores_error(self) -> None:
        """mark_attachment_failed should store error message."""
        state = MigrationState()
        state.mark_attachment_failed("configurations", "123", "file.pdf", "Connection error")

        error = state.get_attachment_failure_error("configurations", "123", "file.pdf")
        assert error == "Connection error"

    def test_mark_attachment_failed_multiple_files(self) -> None:
        """mark_attachment_failed should handle multiple files per entity."""
        state = MigrationState()
        state.mark_attachment_failed("configurations", "123", "file1.pdf", "Error 1")
        state.mark_attachment_failed("configurations", "123", "file2.pdf", "Error 2")

        assert state.is_attachment_failed("configurations", "123", "file1.pdf")
        assert state.is_attachment_failed("configurations", "123", "file2.pdf")
        assert state.get_attachments_failed_count() == 2

    def test_mark_attachment_failed_overwrites_previous_error(self) -> None:
        """mark_attachment_failed should overwrite previous error."""
        state = MigrationState()
        state.mark_attachment_failed("configurations", "123", "file.pdf", "First error")
        state.mark_attachment_failed("configurations", "123", "file.pdf", "Second error")

        error = state.get_attachment_failure_error("configurations", "123", "file.pdf")
        assert error == "Second error"

    def test_mark_attachment_failed_empty_error_raises(self) -> None:
        """mark_attachment_failed with empty error should raise ValueError."""
        state = MigrationState()

        with pytest.raises(ValueError, match="error cannot be empty"):
            state.mark_attachment_failed("configurations", "123", "file.pdf", "")
