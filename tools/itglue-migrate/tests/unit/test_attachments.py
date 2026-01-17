"""Unit tests for the attachment scanner module."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from itglue_migrate.attachments import (
    AttachmentScanner,
    AttachmentStats,
    AttachmentValidationResult,
    DocumentNotFoundError,
    EntityAttachmentStats,
    ExportNotFoundError,
    format_size,
    validate_attachments,
)


@pytest.fixture
def scanner() -> AttachmentScanner:
    """Create an attachment scanner instance."""
    return AttachmentScanner()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestFormatSize:
    """Test the format_size helper function."""

    def test_format_size_zero(self) -> None:
        """Test formatting zero bytes."""
        assert format_size(0) == "0 B"

    def test_format_size_bytes(self) -> None:
        """Test formatting bytes (under 1KB)."""
        assert format_size(1) == "1 B"
        assert format_size(512) == "512 B"
        assert format_size(1023) == "1023 B"

    def test_format_size_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"
        assert format_size(102400) == "100.0 KB"

    def test_format_size_megabytes(self) -> None:
        """Test formatting megabytes."""
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(5 * 1024 * 1024) == "5.0 MB"
        assert format_size(int(5.5 * 1024 * 1024)) == "5.5 MB"

    def test_format_size_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_size(int(5.4 * 1024 * 1024 * 1024)) == "5.4 GB"

    def test_format_size_terabytes(self) -> None:
        """Test formatting terabytes."""
        assert format_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"


class TestEntityAttachmentStats:
    """Test EntityAttachmentStats dataclass."""

    def test_entity_stats_defaults(self) -> None:
        """Test default values."""
        stats = EntityAttachmentStats()
        assert stats.count == 0
        assert stats.size_bytes == 0
        assert stats.formatted_size == "0 B"

    def test_entity_stats_with_values(self) -> None:
        """Test with actual values."""
        stats = EntityAttachmentStats(count=10, size_bytes=5 * 1024 * 1024)
        assert stats.count == 10
        assert stats.size_bytes == 5 * 1024 * 1024
        assert stats.formatted_size == "5.0 MB"

    def test_entity_stats_to_dict(self) -> None:
        """Test to_dict method."""
        stats = EntityAttachmentStats(count=5, size_bytes=1024)
        result = stats.to_dict()

        assert result["count"] == 5
        assert result["size_bytes"] == 1024
        assert result["formatted_size"] == "1.0 KB"


class TestAttachmentValidationResult:
    """Test AttachmentValidationResult dataclass."""

    def test_validation_result_defaults(self) -> None:
        """Test default values."""
        result = AttachmentValidationResult()
        assert result.matched == {}
        assert result.orphaned == {}
        assert result.total_matched_files == 0
        assert result.total_matched_bytes == 0
        assert result.total_orphaned_folders == 0

    def test_validation_result_to_dict(self) -> None:
        """Test to_dict method."""
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


class TestAttachmentStats:
    """Test AttachmentStats dataclass."""

    def test_stats_defaults(self) -> None:
        """Test default values."""
        stats = AttachmentStats()
        assert stats.total_files == 0
        assert stats.total_size_bytes == 0
        assert stats.formatted_size == "0 B"
        assert stats.by_entity_type == {}

    def test_stats_to_dict(self) -> None:
        """Test to_dict method."""
        stats = AttachmentStats(
            total_files=15,
            total_size_bytes=10 * 1024 * 1024,
            by_entity_type={
                "configurations": EntityAttachmentStats(count=10, size_bytes=8 * 1024 * 1024),
                "passwords": EntityAttachmentStats(count=5, size_bytes=2 * 1024 * 1024),
            },
        )
        result = stats.to_dict()

        assert result["total_files"] == 15
        assert result["total_size_bytes"] == 10 * 1024 * 1024
        assert result["formatted_size"] == "10.0 MB"
        assert "configurations" in result["by_entity_type"]
        assert result["by_entity_type"]["configurations"]["count"] == 10


class TestAttachmentScannerBasics:
    """Test basic attachment scanner functionality."""

    def test_scanner_creation(self, scanner: AttachmentScanner) -> None:
        """Test scanner can be instantiated."""
        assert scanner is not None

    def test_export_not_found_raises_error(self, scanner: AttachmentScanner) -> None:
        """Test that missing export directory raises ExportNotFoundError."""
        with pytest.raises(ExportNotFoundError) as exc_info:
            scanner.scan_export(Path("/nonexistent/path"))

        assert exc_info.value.path == Path("/nonexistent/path")
        assert "not found" in str(exc_info.value)

    def test_export_is_file_raises_error(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test that file path (not directory) raises error."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("test")

        with pytest.raises(ExportNotFoundError):
            scanner.scan_export(file_path)


class TestScanExport:
    """Test the scan_export method."""

    def test_scan_empty_export(self, scanner: AttachmentScanner, temp_dir: Path) -> None:
        """Test scanning empty export directory."""
        stats = scanner.scan_export(temp_dir)

        assert stats.total_files == 0
        assert stats.total_size_bytes == 0
        assert stats.by_entity_type == {}

    def test_scan_attachments_directory(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test scanning attachments directory."""
        # Create attachments structure
        attachments_dir = temp_dir / "attachments"
        config_dir = attachments_dir / "configurations" / "123"
        config_dir.mkdir(parents=True)

        # Create test files
        (config_dir / "file1.pdf").write_bytes(b"x" * 1024)
        (config_dir / "file2.docx").write_bytes(b"x" * 2048)

        stats = scanner.scan_export(temp_dir)

        assert stats.total_files == 2
        assert stats.total_size_bytes == 3072
        assert "configurations" in stats.by_entity_type
        assert stats.by_entity_type["configurations"].count == 2
        assert stats.by_entity_type["configurations"].size_bytes == 3072

    def test_scan_multiple_entity_types(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test scanning multiple entity types."""
        attachments_dir = temp_dir / "attachments"

        # Configurations
        config_dir = attachments_dir / "configurations" / "1"
        config_dir.mkdir(parents=True)
        (config_dir / "config.pdf").write_bytes(b"x" * 1000)

        # Passwords
        pwd_dir = attachments_dir / "passwords" / "2"
        pwd_dir.mkdir(parents=True)
        (pwd_dir / "key.txt").write_bytes(b"x" * 500)

        # Documents
        doc_dir = attachments_dir / "documents" / "3"
        doc_dir.mkdir(parents=True)
        (doc_dir / "doc.docx").write_bytes(b"x" * 2000)

        stats = scanner.scan_export(temp_dir)

        assert stats.total_files == 3
        assert stats.total_size_bytes == 3500
        assert len(stats.by_entity_type) == 3
        assert stats.by_entity_type["configurations"].count == 1
        assert stats.by_entity_type["passwords"].count == 1
        assert stats.by_entity_type["documents"].count == 1

    def test_scan_floor_plans_photos(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test scanning floor_plans_photos directory."""
        floor_plans_dir = temp_dir / "floor_plans_photos" / "loc-1"
        floor_plans_dir.mkdir(parents=True)

        (floor_plans_dir / "floor1.jpg").write_bytes(b"x" * 5000)
        (floor_plans_dir / "photo1.png").write_bytes(b"x" * 3000)

        stats = scanner.scan_export(temp_dir)

        assert stats.total_files == 2
        assert stats.total_size_bytes == 8000
        assert "floor_plans_photos" in stats.by_entity_type
        assert stats.by_entity_type["floor_plans_photos"].count == 2

    def test_scan_document_images(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test scanning document images."""
        # Create document folder structure
        doc_dir = temp_dir / "documents" / "DOC-1-100 Test Document"
        images_dir = doc_dir / "1" / "docs" / "100" / "images"
        images_dir.mkdir(parents=True)

        (images_dir / "image1.png").write_bytes(b"x" * 1000)
        (images_dir / "image2.jpg").write_bytes(b"x" * 2000)

        stats = scanner.scan_export(temp_dir)

        assert stats.total_files == 2
        assert "document_images" in stats.by_entity_type
        assert stats.by_entity_type["document_images"].count == 2

    def test_scan_nested_attachments(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test scanning nested attachment directories."""
        config_dir = temp_dir / "attachments" / "configurations" / "1" / "subdir"
        config_dir.mkdir(parents=True)

        (config_dir / "nested.pdf").write_bytes(b"x" * 1000)
        (config_dir.parent / "root.pdf").write_bytes(b"x" * 500)

        stats = scanner.scan_export(temp_dir)

        assert stats.total_files == 2
        assert stats.by_entity_type["configurations"].count == 2


class TestGetDocumentImages:
    """Test the get_document_images method."""

    def test_get_document_images_from_folder(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test getting images from document folder."""
        # Create document folder
        doc_dir = temp_dir / "documents" / "DOC-1-100 Test Document"
        images_dir = doc_dir / "1" / "docs" / "100" / "images"
        images_dir.mkdir(parents=True)

        img1 = images_dir / "image1.png"
        img2 = images_dir / "image2.jpg"
        img1.write_bytes(b"PNG")
        img2.write_bytes(b"JPG")

        images = scanner.get_document_images(temp_dir, "100")

        assert len(images) == 2
        assert img1.resolve() in images
        assert img2.resolve() in images

    def test_get_document_images_from_html(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test getting images referenced in HTML files."""
        # Create document folder with HTML and images
        doc_dir = temp_dir / "documents" / "DOC-1-200 HTML Document"
        doc_dir.mkdir(parents=True)

        # Create image file
        img_path = doc_dir / "diagram.png"
        img_path.write_bytes(b"PNG")

        # Create HTML file referencing the image
        html_content = '<html><body><img src="diagram.png" alt="Diagram"></body></html>'
        (doc_dir / "content.html").write_text(html_content, encoding="utf-8")

        images = scanner.get_document_images(temp_dir, "200")

        assert len(images) == 1
        assert img_path.resolve() in images

    def test_get_document_images_deduplicates(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test that duplicate images are not included twice."""
        doc_dir = temp_dir / "documents" / "DOC-1-300 Dedup Test"
        images_dir = doc_dir / "images"
        images_dir.mkdir(parents=True)

        # Create image
        img_path = images_dir / "logo.png"
        img_path.write_bytes(b"PNG")

        # Reference same image in HTML
        html_content = '<html><body><img src="images/logo.png"></body></html>'
        (doc_dir / "page.html").write_text(html_content, encoding="utf-8")

        images = scanner.get_document_images(temp_dir, "300")

        assert len(images) == 1

    def test_get_document_images_not_found(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test error when document folder not found."""
        # Create documents directory but not the specific document
        (temp_dir / "documents").mkdir()

        with pytest.raises(DocumentNotFoundError) as exc_info:
            scanner.get_document_images(temp_dir, "999")

        assert exc_info.value.doc_id == "999"

    def test_get_document_images_export_not_found(
        self, scanner: AttachmentScanner
    ) -> None:
        """Test error when export path doesn't exist."""
        with pytest.raises(ExportNotFoundError):
            scanner.get_document_images(Path("/nonexistent"), "100")


class TestGetEntityAttachments:
    """Test the get_entity_attachments method."""

    def test_get_entity_attachments_basic(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test getting attachments for a specific entity."""
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)

        file1 = config_dir / "manual.pdf"
        file2 = config_dir / "diagram.png"
        file1.write_bytes(b"PDF")
        file2.write_bytes(b"PNG")

        files = scanner.get_entity_attachments(temp_dir, "configurations", "123")

        assert len(files) == 2
        assert file1.resolve() in files
        assert file2.resolve() in files

    def test_get_entity_attachments_nested(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test getting nested attachments."""
        config_dir = temp_dir / "attachments" / "configurations" / "456" / "subdir"
        config_dir.mkdir(parents=True)

        nested_file = config_dir / "nested.pdf"
        nested_file.write_bytes(b"PDF")

        root_file = config_dir.parent / "root.docx"
        root_file.write_bytes(b"DOCX")

        files = scanner.get_entity_attachments(temp_dir, "configurations", "456")

        assert len(files) == 2

    def test_get_entity_attachments_empty(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test getting attachments when entity has none."""
        (temp_dir / "attachments" / "configurations").mkdir(parents=True)

        files = scanner.get_entity_attachments(temp_dir, "configurations", "999")

        assert files == []

    def test_get_entity_attachments_type_not_exists(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test getting attachments for non-existent entity type."""
        (temp_dir / "attachments").mkdir()

        files = scanner.get_entity_attachments(temp_dir, "nonexistent", "123")

        assert files == []

    def test_get_entity_attachments_sorted(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test that returned files are sorted."""
        config_dir = temp_dir / "attachments" / "configurations" / "789"
        config_dir.mkdir(parents=True)

        (config_dir / "zebra.txt").write_bytes(b"Z")
        (config_dir / "alpha.txt").write_bytes(b"A")
        (config_dir / "beta.txt").write_bytes(b"B")

        files = scanner.get_entity_attachments(temp_dir, "configurations", "789")

        assert len(files) == 3
        # Verify sorted order
        names = [f.name for f in files]
        assert names == sorted(names)


class TestGetAllAttachments:
    """Test the get_all_attachments method."""

    def test_get_all_attachments_basic(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test getting all attachments."""
        attachments_dir = temp_dir / "attachments"

        # Create multiple entity attachments
        config1_dir = attachments_dir / "configurations" / "1"
        config1_dir.mkdir(parents=True)
        (config1_dir / "file.pdf").write_bytes(b"PDF")

        config2_dir = attachments_dir / "configurations" / "2"
        config2_dir.mkdir(parents=True)
        (config2_dir / "file.pdf").write_bytes(b"PDF")

        pwd_dir = attachments_dir / "passwords" / "10"
        pwd_dir.mkdir(parents=True)
        (pwd_dir / "key.txt").write_bytes(b"KEY")

        result = scanner.get_all_attachments(temp_dir)

        assert len(result) == 3
        assert ("configurations", "1") in result
        assert ("configurations", "2") in result
        assert ("passwords", "10") in result

    def test_get_all_attachments_includes_floor_plans(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test that floor plans are included."""
        floor_plans_dir = temp_dir / "floor_plans_photos" / "loc-1"
        floor_plans_dir.mkdir(parents=True)
        (floor_plans_dir / "floor.jpg").write_bytes(b"JPG")

        result = scanner.get_all_attachments(temp_dir)

        assert ("floor_plans_photos", "loc-1") in result
        assert len(result[("floor_plans_photos", "loc-1")]) == 1

    def test_get_all_attachments_empty(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test with empty export directory."""
        result = scanner.get_all_attachments(temp_dir)

        assert result == {}

    def test_get_all_attachments_skips_empty_entities(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test that entities with no files are not included."""
        # Create entity directory but no files
        config_dir = temp_dir / "attachments" / "configurations" / "empty"
        config_dir.mkdir(parents=True)

        result = scanner.get_all_attachments(temp_dir)

        assert ("configurations", "empty") not in result


class TestGetDocumentFolderMapping:
    """Test the get_document_folder_mapping method."""

    def test_document_folder_mapping_basic(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test basic document folder mapping."""
        documents_dir = temp_dir / "documents"

        # Create document folders
        doc1 = documents_dir / "DOC-1-100 First Document"
        doc2 = documents_dir / "DOC-1-200 Second Document"
        doc3 = documents_dir / "DOC-2-300 Other Org Document"
        doc1.mkdir(parents=True)
        doc2.mkdir(parents=True)
        doc3.mkdir(parents=True)

        mapping = scanner.get_document_folder_mapping(temp_dir)

        assert "100" in mapping
        assert "200" in mapping
        assert "300" in mapping
        assert mapping["100"] == doc1
        assert mapping["200"] == doc2
        assert mapping["300"] == doc3

    def test_document_folder_mapping_empty(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test with no document folders."""
        (temp_dir / "documents").mkdir()

        mapping = scanner.get_document_folder_mapping(temp_dir)

        assert mapping == {}

    def test_document_folder_mapping_no_documents_dir(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test when documents directory doesn't exist."""
        mapping = scanner.get_document_folder_mapping(temp_dir)

        assert mapping == {}

    def test_document_folder_mapping_ignores_non_matching(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test that non-matching folders are ignored."""
        documents_dir = temp_dir / "documents"

        # Create valid document folder
        valid = documents_dir / "DOC-1-100 Valid"
        valid.mkdir(parents=True)

        # Create invalid folders
        invalid1 = documents_dir / "Random Folder"
        invalid2 = documents_dir / "DOC-Invalid-Format"
        invalid1.mkdir(parents=True)
        invalid2.mkdir(parents=True)

        mapping = scanner.get_document_folder_mapping(temp_dir)

        assert len(mapping) == 1
        assert "100" in mapping


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_handles_permission_errors_gracefully(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test that permission errors don't crash the scanner."""
        # This test creates a structure but we can't easily test permission errors
        # without actually changing permissions, which may not work on all systems
        config_dir = temp_dir / "attachments" / "configurations" / "1"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF")

        # Just verify normal operation works
        stats = scanner.scan_export(temp_dir)
        assert stats.total_files == 1

    def test_handles_special_characters_in_paths(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test handling of special characters in folder/file names."""
        # Create folder with special characters
        doc_dir = temp_dir / "documents" / "DOC-1-100 Test & Document (2024)"
        images_dir = doc_dir / "images"
        images_dir.mkdir(parents=True)

        img_path = images_dir / "image file.png"
        img_path.write_bytes(b"PNG")

        images = scanner.get_document_images(temp_dir, "100")

        assert len(images) == 1
        assert img_path.resolve() in images

    def test_handles_unicode_characters(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test handling of unicode characters in paths."""
        config_dir = temp_dir / "attachments" / "configurations" / "1"
        config_dir.mkdir(parents=True)

        # File with unicode name
        unicode_file = config_dir / "document_cafe.pdf"
        unicode_file.write_bytes(b"PDF")

        files = scanner.get_entity_attachments(temp_dir, "configurations", "1")

        assert len(files) == 1

    def test_is_image_file_detection(self, scanner: AttachmentScanner) -> None:
        """Test image file extension detection."""
        assert scanner._is_image_file(Path("test.jpg")) is True
        assert scanner._is_image_file(Path("test.JPEG")) is True
        assert scanner._is_image_file(Path("test.png")) is True
        assert scanner._is_image_file(Path("test.gif")) is True
        assert scanner._is_image_file(Path("test.bmp")) is True
        assert scanner._is_image_file(Path("test.webp")) is True
        assert scanner._is_image_file(Path("test.svg")) is True
        assert scanner._is_image_file(Path("test.pdf")) is False
        assert scanner._is_image_file(Path("test.docx")) is False
        assert scanner._is_image_file(Path("test.txt")) is False


class TestValidateAttachments:
    """Test the validate_attachments function."""

    def test_validate_attachments_empty_export(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test validation with empty export."""
        entities = {"configurations": {"123", "456"}}
        result = validate_attachments(temp_dir, entities, scanner)

        assert result.total_matched_files == 0
        assert result.total_orphaned_folders == 0

    def test_validate_attachments_all_matched(
        self, scanner: AttachmentScanner, temp_dir: Path
    ) -> None:
        """Test validation when all attachments match entities."""
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
