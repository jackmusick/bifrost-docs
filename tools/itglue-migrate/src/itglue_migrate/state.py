"""Migration state persistence for IT Glue to BifrostDocs migration.

This module provides state tracking and persistence for resuming interrupted
migrations. It tracks completed entities, failures, and warnings per phase,
enabling incremental migration progress.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from itglue_migrate.id_map import IdMapper
from itglue_migrate.progress import Phase

# Current state file format version
STATE_VERSION = 2


class MigrationStateError(Exception):
    """Base exception for migration state errors."""

    pass


class StateVersionError(MigrationStateError):
    """Raised when state file version is incompatible."""

    def __init__(self, version: int | None) -> None:
        self.version = version
        super().__init__(
            f"Unsupported state file version: {version}. "
            f"Expected version {STATE_VERSION}."
        )


class StateValidationError(MigrationStateError):
    """Raised when state file format is invalid."""

    pass


@dataclass
class FailedEntity:
    """Record of a failed entity migration."""

    itglue_id: str
    error: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            "itglue_id": self.itglue_id,
            "error": self.error,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailedEntity:
        """Create from dictionary."""
        return cls(
            itglue_id=str(data["itglue_id"]),
            error=str(data["error"]),
            timestamp=str(data.get("timestamp", datetime.utcnow().isoformat())),
        )


@dataclass
class FailedAttachment:
    """Record of a failed attachment upload."""

    filename: str
    error: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "error": self.error,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailedAttachment:
        """Create from dictionary."""
        return cls(
            filename=str(data["filename"]),
            error=str(data["error"]),
            timestamp=str(data.get("timestamp", datetime.utcnow().isoformat())),
        )


@dataclass
class PhaseStats:
    """Statistics for a migration phase."""

    completed_count: int
    failed_count: int

    @property
    def total_processed(self) -> int:
        """Total entities processed (completed + failed)."""
        return self.completed_count + self.failed_count


class MigrationState:
    """Tracks and persists migration state for resume capability.

    This class manages the state of an ongoing or interrupted migration,
    tracking which entities have been successfully migrated, which have
    failed, and any warnings encountered.

    Example:
        >>> state = MigrationState(export_path="/path/to/export", api_url="https://api.example.com")
        >>> state.mark_completed(Phase.ORGANIZATIONS, "123")
        >>> state.is_completed(Phase.ORGANIZATIONS, "123")
        True
        >>> state.save("migration_state.json")
        >>>
        >>> # Later, resume migration
        >>> state2 = MigrationState.load("migration_state.json")
        >>> state2.is_completed(Phase.ORGANIZATIONS, "123")
        True
    """

    def __init__(
        self,
        export_path: str | None = None,
        api_url: str | None = None,
        id_mapper: IdMapper | None = None,
    ) -> None:
        """Initialize migration state.

        Args:
            export_path: Path to the IT Glue export directory.
            api_url: Target API URL for the migration.
            id_mapper: Optional IdMapper instance for ID mappings.
                      Creates new instance if None.
        """
        self.export_path = export_path
        self.api_url = api_url
        self.id_mapper = id_mapper or IdMapper()

        # Track when migration started and was last updated
        self.start_time: datetime = datetime.utcnow()
        self.last_update_time: datetime = datetime.utcnow()

        # Current phase being processed
        self._current_phase: Phase | None = None

        # Completed entity IDs per phase
        self._completed: dict[Phase, set[str]] = {phase: set() for phase in Phase}

        # Failed entities per phase (with error details)
        self._failed: dict[Phase, dict[str, FailedEntity]] = {
            phase: {} for phase in Phase
        }

        # Warnings collected during migration
        self._warnings: list[str] = []

        # Track completed attachments: "entity_type:itglue_id" -> set of filenames
        self._attachments_completed: dict[str, set[str]] = {}

        # Track failed attachments: "entity_type:itglue_id" -> {filename: FailedAttachment}
        self._attachments_failed: dict[str, dict[str, FailedAttachment]] = {}

    @property
    def current_phase(self) -> Phase | None:
        """Get the current phase being processed."""
        return self._current_phase

    @current_phase.setter
    def current_phase(self, phase: Phase | None) -> None:
        """Set the current phase being processed."""
        self._current_phase = phase
        self._touch()

    @property
    def warnings(self) -> list[str]:
        """Get list of warnings collected during migration."""
        return self._warnings.copy()

    def _touch(self) -> None:
        """Update the last update timestamp."""
        self.last_update_time = datetime.utcnow()

    def _validate_phase(self, phase: Phase) -> None:
        """Validate that phase is a valid Phase enum member.

        Args:
            phase: The phase to validate.

        Raises:
            TypeError: If phase is not a Phase enum member.
        """
        if not isinstance(phase, Phase):
            raise TypeError(
                f"Expected Phase enum, got {type(phase).__name__}: {phase}"
            )

    def mark_completed(self, phase: Phase, itglue_id: str) -> None:
        """Mark an entity as successfully migrated.

        Args:
            phase: The migration phase.
            itglue_id: The IT Glue ID of the migrated entity.

        Raises:
            TypeError: If phase is not a Phase enum.
            ValueError: If itglue_id is empty.
        """
        self._validate_phase(phase)

        if not itglue_id:
            raise ValueError("itglue_id cannot be empty")

        itglue_id_str = str(itglue_id)
        self._completed[phase].add(itglue_id_str)

        # Remove from failed if it was previously failed (retry succeeded)
        if itglue_id_str in self._failed[phase]:
            del self._failed[phase][itglue_id_str]

        self._touch()

    def mark_failed(self, phase: Phase, itglue_id: str, error: str) -> None:
        """Mark an entity as failed to migrate.

        Args:
            phase: The migration phase.
            itglue_id: The IT Glue ID of the failed entity.
            error: Error message describing the failure.

        Raises:
            TypeError: If phase is not a Phase enum.
            ValueError: If itglue_id or error is empty.
        """
        self._validate_phase(phase)

        if not itglue_id:
            raise ValueError("itglue_id cannot be empty")
        if not error:
            raise ValueError("error cannot be empty")

        itglue_id_str = str(itglue_id)
        self._failed[phase][itglue_id_str] = FailedEntity(
            itglue_id=itglue_id_str,
            error=error,
        )
        self._touch()

    def is_completed(self, phase: Phase, itglue_id: str) -> bool:
        """Check if an entity has been successfully migrated.

        Args:
            phase: The migration phase.
            itglue_id: The IT Glue ID to check.

        Returns:
            True if the entity was successfully migrated, False otherwise.

        Raises:
            TypeError: If phase is not a Phase enum.
        """
        self._validate_phase(phase)
        itglue_id_str = str(itglue_id)
        return itglue_id_str in self._completed[phase]

    def is_failed(self, phase: Phase, itglue_id: str) -> bool:
        """Check if an entity previously failed to migrate.

        Args:
            phase: The migration phase.
            itglue_id: The IT Glue ID to check.

        Returns:
            True if the entity previously failed, False otherwise.

        Raises:
            TypeError: If phase is not a Phase enum.
        """
        self._validate_phase(phase)
        itglue_id_str = str(itglue_id)
        return itglue_id_str in self._failed[phase]

    def get_failure_error(self, phase: Phase, itglue_id: str) -> str | None:
        """Get the error message for a failed entity.

        Args:
            phase: The migration phase.
            itglue_id: The IT Glue ID to check.

        Returns:
            The error message if entity failed, None otherwise.

        Raises:
            TypeError: If phase is not a Phase enum.
        """
        self._validate_phase(phase)
        itglue_id_str = str(itglue_id)
        failed = self._failed[phase].get(itglue_id_str)
        return failed.error if failed else None

    def get_failed_ids(self, phase: Phase) -> list[str]:
        """Get all failed entity IDs for a phase.

        Args:
            phase: The migration phase.

        Returns:
            List of IT Glue IDs that failed in this phase.

        Raises:
            TypeError: If phase is not a Phase enum.
        """
        self._validate_phase(phase)
        return list(self._failed[phase].keys())

    def get_completed_ids(self, phase: Phase) -> set[str]:
        """Get all completed entity IDs for a phase.

        Args:
            phase: The migration phase.

        Returns:
            Set of IT Glue IDs that completed in this phase.

        Raises:
            TypeError: If phase is not a Phase enum.
        """
        self._validate_phase(phase)
        return self._completed[phase].copy()

    def get_phase_stats(self, phase: Phase) -> PhaseStats:
        """Get statistics for a migration phase.

        Args:
            phase: The migration phase.

        Returns:
            PhaseStats with completed_count and failed_count.

        Raises:
            TypeError: If phase is not a Phase enum.
        """
        self._validate_phase(phase)
        return PhaseStats(
            completed_count=len(self._completed[phase]),
            failed_count=len(self._failed[phase]),
        )

    def add_warning(self, message: str) -> None:
        """Add a warning message.

        Args:
            message: The warning message.

        Raises:
            ValueError: If message is empty.
        """
        if not message:
            raise ValueError("message cannot be empty")
        self._warnings.append(message)
        self._touch()

    def clear_warnings(self) -> None:
        """Clear all collected warnings."""
        self._warnings.clear()
        self._touch()

    def clear_failures(self, phase: Phase) -> int:
        """Clear failed entities for a phase to allow retry.

        Args:
            phase: The migration phase to clear failures for.

        Returns:
            Number of failures cleared.

        Raises:
            TypeError: If phase is not a Phase enum.
        """
        self._validate_phase(phase)
        count = len(self._failed[phase])
        self._failed[phase].clear()
        self._touch()
        return count

    def clear_all_failures(self) -> int:
        """Clear all failed entities across all phases.

        Returns:
            Total number of failures cleared.
        """
        total = 0
        for phase in Phase:
            total += len(self._failed[phase])
            self._failed[phase].clear()
        self._touch()
        return total

    def reset_phase(self, phase: Phase) -> None:
        """Reset all state for a phase (completed and failed).

        Args:
            phase: The migration phase to reset.

        Raises:
            TypeError: If phase is not a Phase enum.
        """
        self._validate_phase(phase)
        self._completed[phase].clear()
        self._failed[phase].clear()
        self._touch()

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the state.
        """
        return {
            "version": STATE_VERSION,
            "export_path": self.export_path,
            "api_url": self.api_url,
            "start_time": self.start_time.isoformat(),
            "last_update_time": self.last_update_time.isoformat(),
            "current_phase": self._current_phase.value if self._current_phase else None,
            "completed": {
                phase.value: list(ids) for phase, ids in self._completed.items()
            },
            "failed": {
                phase.value: [entity.to_dict() for entity in entities.values()]
                for phase, entities in self._failed.items()
            },
            "warnings": self._warnings,
            "attachments_completed": {
                key: list(filenames)
                for key, filenames in self._attachments_completed.items()
            },
            "attachments_failed": {
                key: [fa.to_dict() for fa in failed_files.values()]
                for key, failed_files in self._attachments_failed.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MigrationState:
        """Create state from dictionary.

        Args:
            data: Dictionary representation of state.

        Returns:
            MigrationState instance.

        Raises:
            StateVersionError: If version is unsupported.
            StateValidationError: If data format is invalid.
        """
        # Validate version (accept v1 for backward compatibility)
        version = data.get("version")
        if version not in (1, 2):
            raise StateVersionError(version)

        # Create state instance
        state = cls(
            export_path=data.get("export_path"),
            api_url=data.get("api_url"),
        )

        # Restore timestamps
        if "start_time" in data:
            try:
                state.start_time = datetime.fromisoformat(data["start_time"])
            except (ValueError, TypeError) as e:
                raise StateValidationError(f"Invalid start_time format: {e}") from e

        if "last_update_time" in data:
            try:
                state.last_update_time = datetime.fromisoformat(data["last_update_time"])
            except (ValueError, TypeError) as e:
                raise StateValidationError(
                    f"Invalid last_update_time format: {e}"
                ) from e

        # Restore current phase
        current_phase_value = data.get("current_phase")
        if current_phase_value is not None:
            try:
                state._current_phase = Phase(current_phase_value)
            except ValueError:
                # Unknown phase, skip for forward compatibility
                pass

        # Restore completed entities
        completed_data = data.get("completed", {})
        if not isinstance(completed_data, dict):
            raise StateValidationError(
                f"Invalid completed data: expected dict, got {type(completed_data).__name__}"
            )

        for phase_value, ids in completed_data.items():
            try:
                phase = Phase(phase_value)
            except ValueError:
                # Unknown phase, skip for forward compatibility
                continue

            if not isinstance(ids, list):
                raise StateValidationError(
                    f"Invalid completed IDs for phase {phase_value}: "
                    f"expected list, got {type(ids).__name__}"
                )

            state._completed[phase] = {str(id_) for id_ in ids}

        # Restore failed entities
        failed_data = data.get("failed", {})
        if not isinstance(failed_data, dict):
            raise StateValidationError(
                f"Invalid failed data: expected dict, got {type(failed_data).__name__}"
            )

        for phase_value, entities in failed_data.items():
            try:
                phase = Phase(phase_value)
            except ValueError:
                # Unknown phase, skip for forward compatibility
                continue

            if not isinstance(entities, list):
                raise StateValidationError(
                    f"Invalid failed entities for phase {phase_value}: "
                    f"expected list, got {type(entities).__name__}"
                )

            for entity_data in entities:
                if not isinstance(entity_data, dict):
                    raise StateValidationError(
                        f"Invalid failed entity in phase {phase_value}: "
                        f"expected dict, got {type(entity_data).__name__}"
                    )

                try:
                    entity = FailedEntity.from_dict(entity_data)
                    state._failed[phase][entity.itglue_id] = entity
                except KeyError as e:
                    raise StateValidationError(
                        f"Missing required field in failed entity: {e}"
                    ) from e

        # Restore warnings
        warnings = data.get("warnings", [])
        if not isinstance(warnings, list):
            raise StateValidationError(
                f"Invalid warnings: expected list, got {type(warnings).__name__}"
            )
        state._warnings = [str(w) for w in warnings]

        # Restore attachments_completed
        attachments_completed = data.get("attachments_completed", {})
        if isinstance(attachments_completed, dict):
            for key, filenames in attachments_completed.items():
                if isinstance(filenames, list):
                    state._attachments_completed[key] = set(filenames)

        # Restore attachments_failed
        attachments_failed = data.get("attachments_failed", {})
        if isinstance(attachments_failed, dict):
            for key, failed_list in attachments_failed.items():
                if isinstance(failed_list, list):
                    state._attachments_failed[key] = {}
                    for fa_data in failed_list:
                        if isinstance(fa_data, dict):
                            fa = FailedAttachment.from_dict(fa_data)
                            state._attachments_failed[key][fa.filename] = fa

        return state

    def save(self, path: str | Path) -> None:
        """Save state to a JSON file.

        Also saves the IdMapper state alongside the state file.

        Args:
            path: The file path to save to.

        Raises:
            OSError: If the file cannot be written.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save main state
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)

        # Save ID mapper alongside state file
        id_map_path = path.with_suffix(".id_map.json")
        self.id_mapper.save(id_map_path)

    @classmethod
    def load(cls, path: str | Path) -> MigrationState:
        """Load state from a JSON file.

        Also loads the IdMapper state if available.

        Args:
            path: The file path to load from.

        Returns:
            MigrationState instance with restored state.

        Raises:
            FileNotFoundError: If the file does not exist.
            StateVersionError: If version is unsupported.
            StateValidationError: If file format is invalid.
            json.JSONDecodeError: If file is not valid JSON.
        """
        path = Path(path)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise StateValidationError(
                f"Invalid state file format: expected dict, got {type(data).__name__}"
            )

        state = cls.from_dict(data)

        # Load ID mapper if available
        id_map_path = path.with_suffix(".id_map.json")
        if id_map_path.exists():
            state.id_mapper.load(id_map_path)

        return state

    def get_total_completed(self) -> int:
        """Get total count of completed entities across all phases.

        Returns:
            Total number of completed entities.
        """
        return sum(len(ids) for ids in self._completed.values())

    def get_total_failed(self) -> int:
        """Get total count of failed entities across all phases.

        Returns:
            Total number of failed entities.
        """
        return sum(len(entities) for entities in self._failed.values())

    def get_attachments_completed_count(self) -> int:
        """Get total count of completed attachment uploads.

        Returns:
            Total number of attachments successfully uploaded.
        """
        return sum(len(files) for files in self._attachments_completed.values())

    def get_attachments_failed_count(self) -> int:
        """Get total count of failed attachment uploads.

        Returns:
            Total number of attachments that failed to upload.
        """
        return sum(len(files) for files in self._attachments_failed.values())

    def _attachment_key(self, entity_type: str, itglue_id: str) -> str:
        """Create a key for attachment tracking.

        Args:
            entity_type: The entity type (e.g., "configurations").
            itglue_id: The IT Glue entity ID.

        Returns:
            Key in format "entity_type:itglue_id".
        """
        return f"{entity_type}:{itglue_id}"

    def mark_attachment_completed(
        self, entity_type: str, itglue_id: str, filename: str
    ) -> None:
        """Mark an attachment as successfully uploaded.

        Args:
            entity_type: The entity type (e.g., "configurations").
            itglue_id: The IT Glue entity ID.
            filename: The attachment filename.

        Raises:
            ValueError: If any argument is empty.
        """
        if not entity_type:
            raise ValueError("entity_type cannot be empty")
        if not itglue_id:
            raise ValueError("itglue_id cannot be empty")
        if not filename:
            raise ValueError("filename cannot be empty")

        key = self._attachment_key(entity_type, str(itglue_id))

        if key not in self._attachments_completed:
            self._attachments_completed[key] = set()
        self._attachments_completed[key].add(filename)

        # Remove from failed if previously failed (retry succeeded)
        if key in self._attachments_failed and filename in self._attachments_failed[key]:
            del self._attachments_failed[key][filename]
            if not self._attachments_failed[key]:
                del self._attachments_failed[key]

        self._touch()

    def is_attachment_completed(
        self, entity_type: str, itglue_id: str, filename: str
    ) -> bool:
        """Check if an attachment has been successfully uploaded.

        Args:
            entity_type: The entity type.
            itglue_id: The IT Glue entity ID.
            filename: The attachment filename.

        Returns:
            True if the attachment was successfully uploaded.
        """
        key = self._attachment_key(entity_type, str(itglue_id))
        return (
            key in self._attachments_completed
            and filename in self._attachments_completed[key]
        )

    def mark_attachment_failed(
        self, entity_type: str, itglue_id: str, filename: str, error: str
    ) -> None:
        """Mark an attachment as failed to upload.

        Args:
            entity_type: The entity type (e.g., "configurations").
            itglue_id: The IT Glue entity ID.
            filename: The attachment filename.
            error: Error message describing the failure.

        Raises:
            ValueError: If any argument is empty.
        """
        if not entity_type:
            raise ValueError("entity_type cannot be empty")
        if not itglue_id:
            raise ValueError("itglue_id cannot be empty")
        if not filename:
            raise ValueError("filename cannot be empty")
        if not error:
            raise ValueError("error cannot be empty")

        key = self._attachment_key(entity_type, str(itglue_id))

        if key not in self._attachments_failed:
            self._attachments_failed[key] = {}
        self._attachments_failed[key][filename] = FailedAttachment(
            filename=filename,
            error=error,
        )

        self._touch()

    def is_attachment_failed(
        self, entity_type: str, itglue_id: str, filename: str
    ) -> bool:
        """Check if an attachment previously failed to upload.

        Args:
            entity_type: The entity type.
            itglue_id: The IT Glue entity ID.
            filename: The attachment filename.

        Returns:
            True if the attachment previously failed.
        """
        key = self._attachment_key(entity_type, str(itglue_id))
        return (
            key in self._attachments_failed
            and filename in self._attachments_failed[key]
        )

    def get_attachment_failure_error(
        self, entity_type: str, itglue_id: str, filename: str
    ) -> str | None:
        """Get the error message for a failed attachment.

        Args:
            entity_type: The entity type.
            itglue_id: The IT Glue entity ID.
            filename: The attachment filename.

        Returns:
            The error message if attachment failed, None otherwise.
        """
        key = self._attachment_key(entity_type, str(itglue_id))
        if key in self._attachments_failed and filename in self._attachments_failed[key]:
            return self._attachments_failed[key][filename].error
        return None

    def get_all_stats(self) -> dict[Phase, PhaseStats]:
        """Get statistics for all phases.

        Returns:
            Dictionary mapping phases to their stats.
        """
        return {phase: self.get_phase_stats(phase) for phase in Phase}

    def is_phase_started(self, phase: Phase) -> bool:
        """Check if a phase has been started (has any completed or failed entities).

        Args:
            phase: The migration phase.

        Returns:
            True if phase has any processed entities, False otherwise.

        Raises:
            TypeError: If phase is not a Phase enum.
        """
        self._validate_phase(phase)
        return bool(self._completed[phase]) or bool(self._failed[phase])

    def __repr__(self) -> str:
        """Return string representation of the state."""
        total_completed = self.get_total_completed()
        total_failed = self.get_total_failed()
        return (
            f"MigrationState("
            f"completed={total_completed}, "
            f"failed={total_failed}, "
            f"warnings={len(self._warnings)}"
            f")"
        )
