# Attachment Uploads Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add entity attachment uploads to migration pipeline and attachment validation to preview mode.

**Architecture:** Inline attachment uploads after each entity creation (configs, docs, passwords, locations, custom assets). Separate attachment state tracking for granular retry. Preview validates attachments against entities being migrated and warns about orphans.

**Tech Stack:** Python 3.11+, pytest, asyncio, Pydantic dataclasses

---

## Task 1: Add FailedAttachment Dataclass

**Files:**
- Modify: `src/itglue_migrate/state.py:46-70` (near FailedEntity)
- Test: `tests/unit/test_state.py`

**Step 1: Write the failing test**

Add to `tests/unit/test_state.py` after the `TestFailedEntity` class:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate
uv run pytest tests/unit/test_state.py::TestFailedAttachment -v
```

Expected: FAIL with `ImportError: cannot import name 'FailedAttachment'`

**Step 3: Write minimal implementation**

Add to `src/itglue_migrate/state.py` after the `FailedEntity` class (around line 70):

```python
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
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_state.py::TestFailedAttachment -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/itglue_migrate/state.py tests/unit/test_state.py
git commit -m "feat(state): add FailedAttachment dataclass for tracking failed uploads"
```

---

## Task 2: Add Attachment Tracking Fields to MigrationState

**Files:**
- Modify: `src/itglue_migrate/state.py:105-140` (MigrationState.__init__)
- Test: `tests/unit/test_state.py`

**Step 1: Write the failing tests**

Add to `tests/unit/test_state.py` in the `TestMigrationStateInit` class:

```python
    def test_init_empty_attachments_completed(self) -> None:
        """MigrationState should have empty attachments_completed on init."""
        state = MigrationState()

        assert state.get_attachments_completed_count() == 0

    def test_init_empty_attachments_failed(self) -> None:
        """MigrationState should have empty attachments_failed on init."""
        state = MigrationState()

        assert state.get_attachments_failed_count() == 0
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_state.py::TestMigrationStateInit::test_init_empty_attachments_completed -v
```

Expected: FAIL with `AttributeError: 'MigrationState' object has no attribute 'get_attachments_completed_count'`

**Step 3: Write minimal implementation**

In `src/itglue_migrate/state.py`, update `MigrationState.__init__` (around line 105):

Add after line 139 (`self._warnings: list[str] = []`):

```python
        # Track completed attachments: "entity_type:itglue_id" → set of filenames
        self._attachments_completed: dict[str, set[str]] = {}

        # Track failed attachments: "entity_type:itglue_id" → {filename: FailedAttachment}
        self._attachments_failed: dict[str, dict[str, FailedAttachment]] = {}
```

Add these methods to the class (after the `get_total_failed` method, around line 600):

```python
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
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_state.py::TestMigrationStateInit::test_init_empty_attachments_completed tests/unit/test_state.py::TestMigrationStateInit::test_init_empty_attachments_failed -v
```

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/itglue_migrate/state.py tests/unit/test_state.py
git commit -m "feat(state): add attachment tracking fields to MigrationState"
```

---

## Task 3: Add mark_attachment_completed Method

**Files:**
- Modify: `src/itglue_migrate/state.py`
- Test: `tests/unit/test_state.py`

**Step 1: Write the failing tests**

Add new test class to `tests/unit/test_state.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_state.py::TestMigrationStateMarkAttachmentCompleted -v
```

Expected: FAIL with `AttributeError: 'MigrationState' object has no attribute 'mark_attachment_completed'`

**Step 3: Write minimal implementation**

Add to `src/itglue_migrate/state.py` in the `MigrationState` class:

```python
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
        return key in self._attachments_completed and filename in self._attachments_completed[key]

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
        return key in self._attachments_failed and filename in self._attachments_failed[key]
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_state.py::TestMigrationStateMarkAttachmentCompleted -v
```

Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add src/itglue_migrate/state.py tests/unit/test_state.py
git commit -m "feat(state): add mark_attachment_completed method"
```

---

## Task 4: Add mark_attachment_failed Method

**Files:**
- Modify: `src/itglue_migrate/state.py`
- Test: `tests/unit/test_state.py`

**Step 1: Write the failing tests**

Add new test class to `tests/unit/test_state.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_state.py::TestMigrationStateMarkAttachmentFailed -v
```

Expected: FAIL with `AttributeError: 'MigrationState' object has no attribute 'mark_attachment_failed'`

**Step 3: Write minimal implementation**

Add to `src/itglue_migrate/state.py` in the `MigrationState` class:

```python
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
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_state.py::TestMigrationStateMarkAttachmentFailed -v
```

Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/itglue_migrate/state.py tests/unit/test_state.py
git commit -m "feat(state): add mark_attachment_failed method"
```

---

## Task 5: Add Attachment Serialization to MigrationState

**Files:**
- Modify: `src/itglue_migrate/state.py` (to_dict, from_dict methods)
- Test: `tests/unit/test_state.py`

**Step 1: Write the failing tests**

Add to `tests/unit/test_state.py` in `TestMigrationStateSerialization` class:

```python
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
```

Also update `test_to_dict_includes_version` to check for version 2:

```python
    def test_to_dict_version_is_2(self) -> None:
        """to_dict should include version 2 for attachment support."""
        state = MigrationState()

        result = state.to_dict()

        assert result["version"] == 2
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_state.py::TestMigrationStateSerialization::test_to_dict_includes_attachments_completed -v
```

Expected: FAIL with `KeyError: 'attachments_completed'`

**Step 3: Write minimal implementation**

Update `STATE_VERSION` at top of file:

```python
STATE_VERSION = 2
```

Update `to_dict` method in `MigrationState` to include attachments (add before the return):

```python
            "attachments_completed": {
                key: list(filenames)
                for key, filenames in self._attachments_completed.items()
            },
            "attachments_failed": {
                key: [fa.to_dict() for fa in failed_files.values()]
                for key, failed_files in self._attachments_failed.items()
            },
```

Update `from_dict` method to restore attachments (add before `return state`):

```python
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
```

Update version check in `from_dict` to accept both v1 and v2:

```python
        # Validate version (accept v1 for backward compatibility)
        version = data.get("version")
        if version not in (1, 2):
            raise StateVersionError(version)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_state.py::TestMigrationStateSerialization -v
```

Expected: PASS (all serialization tests)

**Step 5: Commit**

```bash
git add src/itglue_migrate/state.py tests/unit/test_state.py
git commit -m "feat(state): add attachment serialization, bump to version 2"
```

---

## Task 6: Add AttachmentValidationResult Dataclass

**Files:**
- Modify: `src/itglue_migrate/attachments.py`
- Test: `tests/unit/test_attachments.py`

**Step 1: Write the failing tests**

Add to `tests/unit/test_attachments.py`:

```python
class TestAttachmentValidationResult:
    """Test AttachmentValidationResult dataclass."""

    def test_validation_result_defaults(self) -> None:
        """Test default values."""
        from itglue_migrate.attachments import AttachmentValidationResult

        result = AttachmentValidationResult()
        assert result.matched == {}
        assert result.orphaned == {}
        assert result.total_matched_files == 0
        assert result.total_matched_bytes == 0
        assert result.total_orphaned_folders == 0

    def test_validation_result_to_dict(self) -> None:
        """Test to_dict method."""
        from itglue_migrate.attachments import AttachmentValidationResult, EntityAttachmentStats

        result = AttachmentValidationResult(
            matched={"configurations": EntityAttachmentStats(count=10, size_bytes=1024)},
            orphaned={"configurations": ["123", "456"]},
            total_matched_files=10,
            total_matched_bytes=1024,
            total_orphaned_folders=2,
        )
        data = result.to_dict()

        assert data["total_matched_files"] == 10
        assert data["total_matched_bytes"] == 1024
        assert data["total_orphaned_folders"] == 2
        assert "configurations" in data["matched"]
        assert data["orphaned"]["configurations"] == ["123", "456"]
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_attachments.py::TestAttachmentValidationResult -v
```

Expected: FAIL with `ImportError: cannot import name 'AttachmentValidationResult'`

**Step 3: Write minimal implementation**

Add to `src/itglue_migrate/attachments.py` after `AttachmentStats` class:

```python
@dataclass
class AttachmentValidationResult:
    """Result of validating attachments against entities to migrate.

    Attributes:
        matched: Attachments that will be uploaded (matched to migrating entities).
        orphaned: Attachment folders with no matching entity in migration.
        total_matched_files: Total files that will be uploaded.
        total_matched_bytes: Total size of files to upload.
        total_orphaned_folders: Count of orphaned attachment folders.
    """

    matched: dict[str, EntityAttachmentStats] = field(default_factory=dict)
    orphaned: dict[str, list[str]] = field(default_factory=dict)
    total_matched_files: int = 0
    total_matched_bytes: int = 0
    total_orphaned_folders: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "matched": {
                entity_type: stats.to_dict()
                for entity_type, stats in self.matched.items()
            },
            "orphaned": self.orphaned,
            "total_matched_files": self.total_matched_files,
            "total_matched_bytes": self.total_matched_bytes,
            "total_orphaned_folders": self.total_orphaned_folders,
            "formatted_matched_size": format_size(self.total_matched_bytes),
        }
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_attachments.py::TestAttachmentValidationResult -v
```

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/itglue_migrate/attachments.py tests/unit/test_attachments.py
git commit -m "feat(attachments): add AttachmentValidationResult dataclass"
```

---

## Task 7: Add validate_attachments Function

**Files:**
- Modify: `src/itglue_migrate/attachments.py`
- Test: `tests/unit/test_attachments.py`

**Step 1: Write the failing tests**

Add to `tests/unit/test_attachments.py`:

```python
class TestValidateAttachments:
    """Test the validate_attachments function."""

    def test_validate_attachments_empty_export(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test validation with empty export."""
        from itglue_migrate.attachments import validate_attachments

        entities = {"configurations": {"123", "456"}}
        result = validate_attachments(temp_dir, entities, scanner)

        assert result.total_matched_files == 0
        assert result.total_orphaned_folders == 0

    def test_validate_attachments_all_matched(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test validation when all attachments match entities."""
        from itglue_migrate.attachments import validate_attachments

        # Create attachments for entities we're migrating
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"x" * 1024)

        entities = {"configurations": {"123"}}
        result = validate_attachments(temp_dir, entities, scanner)

        assert result.total_matched_files == 1
        assert result.total_matched_bytes == 1024
        assert result.total_orphaned_folders == 0
        assert "configurations" in result.matched
        assert result.matched["configurations"].count == 1

    def test_validate_attachments_with_orphans(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test validation detects orphaned attachments."""
        from itglue_migrate.attachments import validate_attachments

        # Create attachments for entity NOT being migrated
        config_dir = temp_dir / "attachments" / "configurations" / "999"
        config_dir.mkdir(parents=True)
        (config_dir / "orphan.pdf").write_bytes(b"x" * 500)

        entities = {"configurations": {"123"}}  # 999 not in list
        result = validate_attachments(temp_dir, entities, scanner)

        assert result.total_orphaned_folders == 1
        assert "configurations" in result.orphaned
        assert "999" in result.orphaned["configurations"]

    def test_validate_attachments_mixed(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test validation with mix of matched and orphaned."""
        from itglue_migrate.attachments import validate_attachments

        attachments_dir = temp_dir / "attachments"

        # Matched attachment
        matched_dir = attachments_dir / "configurations" / "1"
        matched_dir.mkdir(parents=True)
        (matched_dir / "matched.pdf").write_bytes(b"x" * 1000)

        # Orphaned attachment
        orphan_dir = attachments_dir / "configurations" / "999"
        orphan_dir.mkdir(parents=True)
        (orphan_dir / "orphan.pdf").write_bytes(b"x" * 500)

        entities = {"configurations": {"1"}}
        result = validate_attachments(temp_dir, entities, scanner)

        assert result.total_matched_files == 1
        assert result.total_matched_bytes == 1000
        assert result.total_orphaned_folders == 1
        assert "999" in result.orphaned["configurations"]

    def test_validate_attachments_multiple_entity_types(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test validation with multiple entity types."""
        from itglue_migrate.attachments import validate_attachments

        attachments_dir = temp_dir / "attachments"

        # Configurations
        config_dir = attachments_dir / "configurations" / "1"
        config_dir.mkdir(parents=True)
        (config_dir / "config.pdf").write_bytes(b"x" * 1000)

        # Documents
        doc_dir = attachments_dir / "documents" / "2"
        doc_dir.mkdir(parents=True)
        (doc_dir / "doc.pdf").write_bytes(b"x" * 2000)

        # Custom asset type
        asset_dir = attachments_dir / "site-summary" / "3"
        asset_dir.mkdir(parents=True)
        (asset_dir / "summary.pdf").write_bytes(b"x" * 3000)

        entities = {
            "configurations": {"1"},
            "documents": {"2"},
            "site-summary": {"3"},
        }
        result = validate_attachments(temp_dir, entities, scanner)

        assert result.total_matched_files == 3
        assert result.total_matched_bytes == 6000
        assert len(result.matched) == 3
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_attachments.py::TestValidateAttachments -v
```

Expected: FAIL with `ImportError: cannot import name 'validate_attachments'`

**Step 3: Write minimal implementation**

Add to `src/itglue_migrate/attachments.py`:

```python
def validate_attachments(
    export_path: Path,
    entities_to_migrate: dict[str, set[str]],
    scanner: AttachmentScanner | None = None,
) -> AttachmentValidationResult:
    """Validate attachments against entities being migrated.

    Scans the export for attachments and determines which will be uploaded
    (matched to migrating entities) and which are orphaned (no matching entity).

    Args:
        export_path: Path to the IT Glue export directory.
        entities_to_migrate: Dict mapping entity_type to set of itglue_ids.
        scanner: Optional AttachmentScanner instance (creates new if None).

    Returns:
        AttachmentValidationResult with matched and orphaned attachments.
    """
    if scanner is None:
        scanner = AttachmentScanner()

    result = AttachmentValidationResult()

    # Get all attachments from export
    all_attachments = scanner.get_all_attachments(export_path)

    # Process each attachment
    for (entity_type, entity_id), files in all_attachments.items():
        # Check if this entity is being migrated
        migrating_ids = entities_to_migrate.get(entity_type, set())

        if entity_id in migrating_ids:
            # Matched - will be uploaded
            if entity_type not in result.matched:
                result.matched[entity_type] = EntityAttachmentStats()

            for file_path in files:
                result.matched[entity_type].count += 1
                result.matched[entity_type].size_bytes += file_path.stat().st_size
                result.total_matched_files += 1
                result.total_matched_bytes += file_path.stat().st_size
        else:
            # Orphaned - no matching entity
            if entity_type not in result.orphaned:
                result.orphaned[entity_type] = []
            result.orphaned[entity_type].append(entity_id)
            result.total_orphaned_folders += 1

    return result
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_attachments.py::TestValidateAttachments -v
```

Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/itglue_migrate/attachments.py tests/unit/test_attachments.py
git commit -m "feat(attachments): add validate_attachments function"
```

---

## Task 8: Update DocumentProcessor to Use State Tracking

**Files:**
- Modify: `src/itglue_migrate/document_processor.py:472-577`
- Test: `tests/unit/test_document_processor.py`

**Step 1: Write the failing tests**

Add to `tests/unit/test_document_processor.py`:

```python
class TestUploadEntityAttachmentsWithState:
    """Test upload_entity_attachments with state tracking."""

    @pytest.mark.asyncio
    async def test_skips_already_completed_attachments(
        self, mock_client: MagicMock, temp_export: Path
    ) -> None:
        """Should skip attachments already marked as completed."""
        from itglue_migrate.state import MigrationState
        from itglue_migrate.document_processor import DocumentProcessor
        from itglue_migrate.attachments import AttachmentScanner

        # Create attachment
        config_dir = temp_export / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF content")

        # Create state with attachment already completed
        state = MigrationState()
        state.mark_attachment_completed("configurations", "123", "file.pdf")

        processor = DocumentProcessor(
            client=mock_client,
            scanner=AttachmentScanner(),
            export_path=temp_export,
        )

        count = await processor.upload_entity_attachments(
            entity_type="configurations",
            entity_id="123",
            org_uuid="org-uuid",
            our_entity_id="entity-uuid",
            state=state,
        )

        assert count == 0  # Skipped
        mock_client.create_attachment.assert_not_called()

    @pytest.mark.asyncio
    async def test_marks_attachment_completed_on_success(
        self, mock_client: MagicMock, temp_export: Path
    ) -> None:
        """Should mark attachment as completed after successful upload."""
        from itglue_migrate.state import MigrationState
        from itglue_migrate.document_processor import DocumentProcessor
        from itglue_migrate.attachments import AttachmentScanner

        # Create attachment
        config_dir = temp_export / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF content")

        # Mock successful upload
        mock_client.create_attachment.return_value = {"upload_url": "https://upload.url"}
        mock_client.upload_file_to_presigned_url.return_value = None

        state = MigrationState()
        processor = DocumentProcessor(
            client=mock_client,
            scanner=AttachmentScanner(),
            export_path=temp_export,
        )

        await processor.upload_entity_attachments(
            entity_type="configurations",
            entity_id="123",
            org_uuid="org-uuid",
            our_entity_id="entity-uuid",
            state=state,
        )

        assert state.is_attachment_completed("configurations", "123", "file.pdf")

    @pytest.mark.asyncio
    async def test_marks_attachment_failed_on_error(
        self, mock_client: MagicMock, temp_export: Path
    ) -> None:
        """Should mark attachment as failed on upload error."""
        from itglue_migrate.state import MigrationState
        from itglue_migrate.document_processor import DocumentProcessor
        from itglue_migrate.attachments import AttachmentScanner
        from itglue_migrate.client import APIError

        # Create attachment
        config_dir = temp_export / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF content")

        # Mock failed upload
        mock_client.create_attachment.side_effect = APIError("Upload failed")

        state = MigrationState()
        processor = DocumentProcessor(
            client=mock_client,
            scanner=AttachmentScanner(),
            export_path=temp_export,
        )

        await processor.upload_entity_attachments(
            entity_type="configurations",
            entity_id="123",
            org_uuid="org-uuid",
            our_entity_id="entity-uuid",
            state=state,
        )

        assert state.is_attachment_failed("configurations", "123", "file.pdf")
        assert "Upload failed" in state.get_attachment_failure_error("configurations", "123", "file.pdf")
```

Note: You may need to add fixtures for `mock_client` and `temp_export` if they don't exist.

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_document_processor.py::TestUploadEntityAttachmentsWithState -v
```

Expected: FAIL with `TypeError: upload_entity_attachments() got an unexpected keyword argument 'state'`

**Step 3: Write minimal implementation**

Update `upload_entity_attachments` in `src/itglue_migrate/document_processor.py`:

```python
    async def upload_entity_attachments(
        self,
        entity_type: str,
        entity_id: str,
        org_uuid: str,
        our_entity_id: str,
        state: MigrationState | None = None,
    ) -> int:
        """Upload all attachments for an entity to BifrostDocs.

        Finds attachments in the export attachments/{entity_type}/{entity_id}/
        folder and uploads each one via the presigned URL flow.

        Args:
            entity_type: IT Glue entity type (e.g., "configurations", "documents").
            entity_id: IT Glue entity ID.
            org_uuid: Target organization UUID.
            our_entity_id: Our entity UUID to attach files to.
            state: Optional MigrationState for tracking attachment progress.

        Returns:
            Count of successfully uploaded attachments.
        """
        # ... existing entity type mapping code ...

        uploaded_count = 0

        for file_path in attachment_files:
            filename = file_path.name

            # Skip if already completed
            if state and state.is_attachment_completed(entity_type, entity_id, filename):
                logger.debug(f"Skipping already completed attachment: {filename}")
                continue

            try:
                # ... existing upload code ...

                uploaded_count += 1

                # Mark as completed
                if state:
                    state.mark_attachment_completed(entity_type, entity_id, filename)

                logger.debug(
                    f"Uploaded attachment: {filename} -> "
                    f"{target_entity_type}/{our_entity_id}"
                )

            except APIError as e:
                if state:
                    state.mark_attachment_failed(entity_type, entity_id, filename, str(e))
                logger.warning(f"API error uploading attachment {filename}: {e}")
            except OSError as e:
                if state:
                    state.mark_attachment_failed(entity_type, entity_id, filename, str(e))
                logger.warning(f"Failed to read attachment file {file_path}: {e}")
            except Exception as e:
                if state:
                    state.mark_attachment_failed(entity_type, entity_id, filename, str(e))
                logger.warning(f"Unexpected error uploading attachment {filename}: {e}")

        # ... rest of method ...
```

Add import at top of file:

```python
from itglue_migrate.state import MigrationState
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_document_processor.py::TestUploadEntityAttachmentsWithState -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/itglue_migrate/document_processor.py tests/unit/test_document_processor.py
git commit -m "feat(document_processor): add state tracking to upload_entity_attachments"
```

---

## Task 9: Integrate Attachment Uploads into _migrate_configurations

**Files:**
- Modify: `src/itglue_migrate/cli.py:849-934`
- Test: Manual integration test

**Step 1: Update function signature**

Update `_migrate_configurations` to accept `doc_processor` and `export_path`:

```python
async def _migrate_configurations(
    client: BifrostDocsClient,
    parsed_configs: list[dict[str, Any]],
    state: MigrationState,
    reporter: Any,
    dry_run: bool,
    target_org_names: set[str] | None,
    doc_processor: DocumentProcessor | None = None,
    export_path: Path | None = None,
) -> None:
```

**Step 2: Add attachment upload after entity creation**

After `state.mark_completed(Phase.CONFIGURATIONS, itglue_id)` (around line 926), add:

```python
                # Upload attachments for this configuration
                if doc_processor and export_path and not dry_run:
                    try:
                        attachment_count = await doc_processor.upload_entity_attachments(
                            entity_type="configurations",
                            entity_id=itglue_id,
                            org_uuid=org_uuid,
                            our_entity_id=new_uuid,
                            state=state,
                        )
                        if attachment_count > 0:
                            logger.info(f"Uploaded {attachment_count} attachments for config {name}")
                    except Exception as e:
                        logger.warning(f"Failed to upload attachments for config {name}: {e}")
```

**Step 3: Update caller in run() function**

In the `run()` function, update the call to `_migrate_configurations`:

```python
        # Phase 4: Configurations
        await _migrate_configurations(
            client, parsed_configs, state, reporter, dry_run, target_org_names,
            doc_processor=doc_processor,
            export_path=Path(plan_data.get("export_path", "")),
        )
```

**Step 4: Commit**

```bash
git add src/itglue_migrate/cli.py
git commit -m "feat(cli): integrate attachment uploads into _migrate_configurations"
```

---

## Task 10: Integrate Attachment Uploads into Remaining Migration Functions

**Files:**
- Modify: `src/itglue_migrate/cli.py`

Apply the same pattern from Task 9 to these functions:

1. `_migrate_documents` - add attachment upload after document creation
2. `_migrate_passwords` - add attachment upload after password creation
3. `_migrate_locations` - add attachment upload + floor_plans_photos after location creation
4. `_migrate_custom_assets` - add attachment upload using asset type slug

**For _migrate_locations (special case - floor plans):**

```python
                # Upload attachments for this location
                if doc_processor and export_path and not dry_run:
                    # Regular attachments
                    attachment_count = await doc_processor.upload_entity_attachments(
                        entity_type="locations",
                        entity_id=itglue_id,
                        org_uuid=org_uuid,
                        our_entity_id=new_uuid,
                        state=state,
                    )
                    # Floor plans/photos
                    floor_plan_count = await doc_processor.upload_entity_attachments(
                        entity_type="floor_plans_photos",
                        entity_id=itglue_id,
                        org_uuid=org_uuid,
                        our_entity_id=new_uuid,
                        state=state,
                    )
```

**For _migrate_custom_assets:**

Use the asset type slug from the parsed data:

```python
                # Upload attachments using asset type slug
                if doc_processor and export_path and not dry_run:
                    asset_type_slug = asset.get("asset_type_slug", "")
                    if asset_type_slug:
                        attachment_count = await doc_processor.upload_entity_attachments(
                            entity_type=asset_type_slug,
                            entity_id=itglue_id,
                            org_uuid=org_uuid,
                            our_entity_id=new_uuid,
                            state=state,
                        )
```

**Commit:**

```bash
git add src/itglue_migrate/cli.py
git commit -m "feat(cli): integrate attachment uploads into all migration functions"
```

---

## Task 11: Update Preview Output with Attachment Validation

**Files:**
- Modify: `src/itglue_migrate/cli.py` (preview command area)

**Step 1: Add validation call in preview**

In the preview generation code, add:

```python
from itglue_migrate.attachments import validate_attachments, AttachmentScanner

# Build entities_to_migrate dict from parsed data
entities_to_migrate = {
    "configurations": {str(c["id"]) for c in parsed_configs},
    "documents": {str(d["id"]) for d in parsed_docs},
    "passwords": {str(p["id"]) for p in parsed_passwords},
    "locations": {str(l["id"]) for l in parsed_locations},
}

# Add custom asset type slugs
for asset in parsed_custom_assets:
    slug = asset.get("asset_type_slug", "")
    if slug:
        if slug not in entities_to_migrate:
            entities_to_migrate[slug] = set()
        entities_to_migrate[slug].add(str(asset["id"]))

# Validate attachments
scanner = AttachmentScanner()
validation = validate_attachments(export_path, entities_to_migrate, scanner)
```

**Step 2: Update display function**

Add to `_display_dry_run_summary`:

```python
    # Attachment validation
    validation = plan_data.get("attachment_validation")
    if validation:
        console.print()
        console.print("[bold]Attachments to upload:[/bold]")
        for entity_type, stats in validation.get("matched", {}).items():
            count = stats.get("count", 0)
            size = stats.get("formatted_size", "0 B")
            console.print(f"  {entity_type}: {count} files ({size})")

        total_files = validation.get("total_matched_files", 0)
        total_size = validation.get("formatted_matched_size", "0 B")
        console.print(f"  [bold]Total: {total_files} files ({total_size})[/bold]")

        # Orphan warnings
        orphaned = validation.get("orphaned", {})
        if orphaned:
            total_orphans = validation.get("total_orphaned_folders", 0)
            console.print()
            console.print(f"[yellow]⚠️  Orphaned attachments ({total_orphans} folders, no matching entity):[/yellow]")
            for entity_type, ids in orphaned.items():
                ids_preview = ", ".join(ids[:5])
                if len(ids) > 5:
                    ids_preview += f", ... ({len(ids)} total)"
                console.print(f"    {entity_type}: {ids_preview}")
```

**Commit:**

```bash
git add src/itglue_migrate/cli.py
git commit -m "feat(cli): add attachment validation to preview output"
```

---

## Task 12: Run Full Test Suite and Type Check

**Step 1: Run all tests**

```bash
cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate
uv run pytest tests/ -v
```

Expected: All tests PASS

**Step 2: Run type checker**

```bash
uv run pyright
```

Expected: No errors

**Step 3: Run linter**

```bash
uv run ruff check src/ tests/
```

Expected: No errors

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: ensure all tests pass and type checks clean"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | FailedAttachment dataclass | state.py, test_state.py |
| 2 | Attachment tracking fields | state.py, test_state.py |
| 3 | mark_attachment_completed | state.py, test_state.py |
| 4 | mark_attachment_failed | state.py, test_state.py |
| 5 | Attachment serialization | state.py, test_state.py |
| 6 | AttachmentValidationResult | attachments.py, test_attachments.py |
| 7 | validate_attachments function | attachments.py, test_attachments.py |
| 8 | DocumentProcessor state tracking | document_processor.py, test_document_processor.py |
| 9 | _migrate_configurations integration | cli.py |
| 10 | Remaining migration functions | cli.py |
| 11 | Preview output update | cli.py |
| 12 | Full test suite verification | - |
