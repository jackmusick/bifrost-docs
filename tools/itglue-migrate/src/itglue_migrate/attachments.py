"""Attachment scanner for IT Glue export files.

This module scans IT Glue export directories to discover and catalog
attachments and document images, providing statistics and file listings.

Export structure expected:
    export/
    ├── documents/
    │   └── DOC-{org_id}-{doc_id} Document Name/
    │       └── {org_id}/docs/{doc_id}/images/{image_id}  (embedded images)
    ├── attachments/
    │   ├── configurations/{config_id}/file.pdf
    │   ├── documents/{doc_id}/file.docx
    │   ├── passwords/{password_id}/file.txt
    │   ├── site-summary/{asset_id}/file.pdf
    │   └── ...other custom asset types.../
    └── floor_plans_photos/
        └── {id}/file.jpg
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class AttachmentScannerError(Exception):
    """Base exception for attachment scanner errors."""

    pass


class ExportNotFoundError(AttachmentScannerError):
    """Raised when the export directory is not found."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Export directory not found: {path}")


class DocumentNotFoundError(AttachmentScannerError):
    """Raised when a document folder is not found."""

    def __init__(self, doc_id: str, export_path: Path) -> None:
        self.doc_id = doc_id
        self.export_path = export_path
        super().__init__(f"Document folder not found for ID {doc_id} in {export_path}")


# Size formatting constants
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


def format_size(size_bytes: int) -> str:
    """Format a size in bytes as a human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string (e.g., "5.4 GB", "128 KB").

    Examples:
        >>> format_size(0)
        '0 B'
        >>> format_size(1024)
        '1.0 KB'
        >>> format_size(5800000000)
        '5.4 GB'
    """
    if size_bytes == 0:
        return "0 B"

    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(SIZE_UNITS) - 1:
        size /= 1024
        unit_index += 1

    # Use integer format for bytes, one decimal for larger units
    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {SIZE_UNITS[unit_index]}"


@dataclass
class EntityAttachmentStats:
    """Statistics for attachments of a specific entity type.

    Attributes:
        count: Number of attachment files.
        size_bytes: Total size of attachments in bytes.
    """

    count: int = 0
    size_bytes: int = 0

    @property
    def formatted_size(self) -> str:
        """Get human-readable size."""
        return format_size(self.size_bytes)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "count": self.count,
            "size_bytes": self.size_bytes,
            "formatted_size": self.formatted_size,
        }


@dataclass
class AttachmentStats:
    """Statistics for all attachments in an IT Glue export.

    Attributes:
        total_files: Total number of attachment files.
        total_size_bytes: Total size of all attachments in bytes.
        by_entity_type: Statistics broken down by entity type.
    """

    total_files: int = 0
    total_size_bytes: int = 0
    by_entity_type: dict[str, EntityAttachmentStats] = field(default_factory=dict)

    @property
    def formatted_size(self) -> str:
        """Get human-readable total size."""
        return format_size(self.total_size_bytes)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_files": self.total_files,
            "total_size_bytes": self.total_size_bytes,
            "formatted_size": self.formatted_size,
            "by_entity_type": {
                entity_type: stats.to_dict()
                for entity_type, stats in self.by_entity_type.items()
            },
        }


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


# Regex patterns for parsing document folder names and image paths
# DOC-{org_id}-{doc_id} Document Name
DOC_FOLDER_PATTERN = re.compile(r"^DOC-(\d+)-(\d+)\s")

# Image src patterns in HTML
IMG_SRC_PATTERN = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


class AttachmentScanner:
    """Scanner for attachments and document images in IT Glue exports.

    This class provides methods to scan an IT Glue export directory and
    discover all attachments and embedded document images, calculating
    statistics and providing file listings.

    Example:
        >>> scanner = AttachmentScanner()
        >>> stats = scanner.scan_export(Path("/path/to/export"))
        >>> print(f"Total files: {stats.total_files}")
        >>> print(f"Total size: {stats.formatted_size}")
        >>>
        >>> # Get attachments for a specific configuration
        >>> files = scanner.get_entity_attachments(
        ...     Path("/path/to/export"),
        ...     "configurations",
        ...     "12345"
        ... )
    """

    def __init__(self) -> None:
        """Initialize the attachment scanner."""
        pass

    def _validate_export_path(self, export_path: Path) -> None:
        """Validate that the export path exists and is a directory.

        Args:
            export_path: Path to the IT Glue export directory.

        Raises:
            ExportNotFoundError: If the path does not exist or is not a directory.
        """
        if not export_path.exists():
            raise ExportNotFoundError(export_path)
        if not export_path.is_dir():
            raise ExportNotFoundError(export_path)

    def _get_file_size(self, file_path: Path) -> int:
        """Get the size of a file in bytes.

        Args:
            file_path: Path to the file.

        Returns:
            File size in bytes, or 0 if file cannot be read.
        """
        try:
            return file_path.stat().st_size
        except OSError:
            return 0

    def _scan_directory_files(self, directory: Path) -> list[Path]:
        """Recursively scan a directory for all files.

        Args:
            directory: Directory to scan.

        Returns:
            List of file paths found in the directory.
        """
        if not directory.exists() or not directory.is_dir():
            return []

        files: list[Path] = []
        for item in directory.rglob("*"):
            if item.is_file():
                files.append(item)
        return files

    def _find_document_folder(self, export_path: Path, doc_id: str) -> Path | None:
        """Find the document folder for a given document ID.

        Document folders are named like: DOC-{org_id}-{doc_id} Document Name
        They may be nested in subdirectories (e.g., _Archive/, _Archives/).

        Args:
            export_path: Path to the IT Glue export directory.
            doc_id: The document ID to find.

        Returns:
            Path to the document folder, or None if not found.
        """
        documents_dir = export_path / "documents"
        if not documents_dir.exists():
            return None

        # Use rglob to recursively search for DOC-* folders in any subdirectory
        for folder in documents_dir.rglob("DOC-*"):
            if not folder.is_dir():
                continue

            match = DOC_FOLDER_PATTERN.match(folder.name)
            if match and match.group(2) == str(doc_id):
                return folder

        return None

    def _parse_html_for_images(self, html_path: Path) -> list[str]:
        """Parse an HTML file and extract image source paths.

        Args:
            html_path: Path to the HTML file.

        Returns:
            List of image source paths found in the HTML.
        """
        try:
            content = html_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Try with latin-1 encoding as fallback
            try:
                content = html_path.read_text(encoding="latin-1")
            except OSError:
                return []

        return IMG_SRC_PATTERN.findall(content)

    def _resolve_image_path(
        self, img_src: str, html_path: Path, doc_folder: Path
    ) -> Path | None:
        """Resolve an image source path to an actual file path.

        Args:
            img_src: The image source from HTML (may be relative or absolute).
            html_path: Path to the HTML file containing the image reference.
            doc_folder: Path to the document folder.

        Returns:
            Resolved file path, or None if the file doesn't exist.
        """
        # Try relative to HTML file first
        relative_to_html = html_path.parent / img_src
        if relative_to_html.exists():
            return relative_to_html.resolve()

        # Try relative to document folder
        relative_to_doc = doc_folder / img_src
        if relative_to_doc.exists():
            return relative_to_doc.resolve()

        # Try as absolute path within document folder (strip leading slash)
        if img_src.startswith("/"):
            clean_path = img_src.lstrip("/")
            absolute_in_doc = doc_folder / clean_path
            if absolute_in_doc.exists():
                return absolute_in_doc.resolve()

        return None

    def scan_export(self, export_path: Path) -> AttachmentStats:
        """Scan an IT Glue export directory for all attachments.

        Scans the following locations:
        - attachments/ - Entity attachments organized by type
        - floor_plans_photos/ - Floor plan and photo files
        - documents/*/images/ - Embedded document images

        Args:
            export_path: Path to the IT Glue export directory.

        Returns:
            AttachmentStats with counts and sizes.

        Raises:
            ExportNotFoundError: If the export path does not exist.
        """
        self._validate_export_path(export_path)

        stats = AttachmentStats()

        # Scan attachments directory
        attachments_dir = export_path / "attachments"
        if attachments_dir.exists() and attachments_dir.is_dir():
            self._scan_attachments_directory(attachments_dir, stats)

        # Scan floor_plans_photos directories
        # IT Glue exports floor plans as {asset_type}-floor-plans-photos/ directories
        # e.g., lan-floor-plans-photos/ for LAN custom assets
        self._scan_floor_plans_directories(export_path, stats)

        # Scan document images
        documents_dir = export_path / "documents"
        if documents_dir.exists() and documents_dir.is_dir():
            self._scan_document_images(documents_dir, stats)

        return stats

    def _scan_attachments_directory(
        self, attachments_dir: Path, stats: AttachmentStats
    ) -> None:
        """Scan the attachments directory and update stats.

        Args:
            attachments_dir: Path to the attachments directory.
            stats: AttachmentStats to update.
        """
        for entity_type_dir in attachments_dir.iterdir():
            if not entity_type_dir.is_dir():
                continue

            entity_type = entity_type_dir.name
            files = self._scan_directory_files(entity_type_dir)

            if not files:
                continue

            entity_stats = EntityAttachmentStats()
            for file_path in files:
                entity_stats.count += 1
                entity_stats.size_bytes += self._get_file_size(file_path)

            stats.by_entity_type[entity_type] = entity_stats
            stats.total_files += entity_stats.count
            stats.total_size_bytes += entity_stats.size_bytes

    def _scan_floor_plans_directories(
        self, export_path: Path, stats: AttachmentStats
    ) -> None:
        """Scan for floor plans photo directories and update stats.

        IT Glue exports floor plans as {asset_type}-floor-plans-photos/ directories.
        e.g., lan-floor-plans-photos/ for LAN custom assets.

        Args:
            export_path: Path to the export directory.
            stats: AttachmentStats to update.
        """
        # Look for directories matching *-floor-plans-photos pattern
        for floor_plans_dir in export_path.glob("*-floor-plans-photos"):
            if not floor_plans_dir.is_dir():
                continue

            # Extract the asset type from directory name (e.g., "lan" from "lan-floor-plans-photos")
            asset_type = floor_plans_dir.name.replace("-floor-plans-photos", "")
            entity_type_key = f"{asset_type}_floor_plans_photos"

            files = self._scan_directory_files(floor_plans_dir)
            entity_stats = EntityAttachmentStats()
            for file_path in files:
                entity_stats.count += 1
                entity_stats.size_bytes += self._get_file_size(file_path)

            if entity_stats.count > 0:
                stats.by_entity_type[entity_type_key] = entity_stats
                stats.total_files += entity_stats.count
                stats.total_size_bytes += entity_stats.size_bytes

        # Also check for legacy floor_plans_photos directory (no prefix)
        legacy_floor_plans_dir = export_path / "floor_plans_photos"
        if legacy_floor_plans_dir.exists() and legacy_floor_plans_dir.is_dir():
            files = self._scan_directory_files(legacy_floor_plans_dir)
            entity_stats = EntityAttachmentStats()
            for file_path in files:
                entity_stats.count += 1
                entity_stats.size_bytes += self._get_file_size(file_path)

            if entity_stats.count > 0:
                stats.by_entity_type["floor_plans_photos"] = entity_stats
                stats.total_files += entity_stats.count
                stats.total_size_bytes += entity_stats.size_bytes

    def _scan_document_images(
        self, documents_dir: Path, stats: AttachmentStats
    ) -> None:
        """Scan document folders for embedded images and update stats.

        Args:
            documents_dir: Path to the documents directory.
            stats: AttachmentStats to update.
        """
        entity_stats = EntityAttachmentStats()
        seen_files: set[Path] = set()

        for doc_folder in documents_dir.iterdir():
            if not doc_folder.is_dir():
                continue

            # Find all image files in the document folder
            # Images are typically in: {org_id}/docs/{doc_id}/images/
            for file_path in doc_folder.rglob("*"):
                if not file_path.is_file():
                    continue

                # Check if it's in an images folder or is an image file
                if "images" in file_path.parts or self._is_image_file(file_path):
                    resolved = file_path.resolve()
                    if resolved not in seen_files:
                        seen_files.add(resolved)
                        entity_stats.count += 1
                        entity_stats.size_bytes += self._get_file_size(file_path)

        if entity_stats.count > 0:
            stats.by_entity_type["document_images"] = entity_stats
            stats.total_files += entity_stats.count
            stats.total_size_bytes += entity_stats.size_bytes

    def _is_image_file(self, file_path: Path) -> bool:
        """Check if a file is an image based on extension.

        Args:
            file_path: Path to the file.

        Returns:
            True if the file has an image extension.
        """
        image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".svg",
            ".ico",
            ".tiff",
            ".tif",
        }
        return file_path.suffix.lower() in image_extensions

    def get_document_images(self, export_path: Path, doc_id: str) -> list[Path]:
        """Get all image files for a specific document.

        Finds the document folder and extracts image paths from:
        1. HTML files containing <img> tags
        2. Files in the images/ subdirectory

        Args:
            export_path: Path to the IT Glue export directory.
            doc_id: The document ID.

        Returns:
            List of absolute paths to image files.

        Raises:
            ExportNotFoundError: If the export path does not exist.
            DocumentNotFoundError: If the document folder is not found.
        """
        self._validate_export_path(export_path)

        doc_folder = self._find_document_folder(export_path, doc_id)
        if doc_folder is None:
            raise DocumentNotFoundError(doc_id, export_path)

        images: list[Path] = []
        seen_paths: set[Path] = set()

        # Method 1: Parse HTML files for image references
        for html_file in doc_folder.rglob("*.html"):
            img_srcs = self._parse_html_for_images(html_file)
            for img_src in img_srcs:
                resolved = self._resolve_image_path(img_src, html_file, doc_folder)
                if resolved and resolved not in seen_paths:
                    seen_paths.add(resolved)
                    images.append(resolved)

        # Method 2: Find all files in images/ directories
        for file_path in doc_folder.rglob("*"):
            if not file_path.is_file():
                continue

            # Check if in images folder
            if "images" in file_path.parts:
                resolved = file_path.resolve()
                if resolved not in seen_paths:
                    seen_paths.add(resolved)
                    images.append(resolved)

        return sorted(images)

    def get_entity_attachments(
        self, export_path: Path, entity_type: str, entity_id: str
    ) -> list[Path]:
        """Get all attachment files for a specific entity.

        Args:
            export_path: Path to the IT Glue export directory.
            entity_type: The entity type (e.g., "configurations", "passwords").
            entity_id: The entity ID.

        Returns:
            List of absolute paths to attachment files.

        Raises:
            ExportNotFoundError: If the export path does not exist.
        """
        self._validate_export_path(export_path)

        files: list[Path] = []

        # Check standard attachments directory
        entity_dir = export_path / "attachments" / entity_type / str(entity_id)
        if entity_dir.exists() and entity_dir.is_dir():
            files.extend(self._scan_directory_files(entity_dir))

        # Also check floor plans directory for this entity type
        # IT Glue exports floor plans as {entity_type}-floor-plans-photos/{id}-filename.ext
        floor_plans_dir = export_path / f"{entity_type}-floor-plans-photos"
        if floor_plans_dir.exists() and floor_plans_dir.is_dir():
            entity_id_prefix = f"{entity_id}-"
            for item in floor_plans_dir.iterdir():
                if item.is_file() and item.name.startswith(entity_id_prefix):
                    files.append(item)

        return sorted([f.resolve() for f in files])

    def get_all_attachments(
        self, export_path: Path
    ) -> dict[tuple[str, str], list[Path]]:
        """Get all attachments organized by entity type and ID.

        Args:
            export_path: Path to the IT Glue export directory.

        Returns:
            Dictionary mapping (entity_type, entity_id) tuples to lists of file paths.

        Raises:
            ExportNotFoundError: If the export path does not exist.
        """
        self._validate_export_path(export_path)

        result: dict[tuple[str, str], list[Path]] = {}

        # Scan attachments directory
        attachments_dir = export_path / "attachments"
        if attachments_dir.exists() and attachments_dir.is_dir():
            for entity_type_dir in attachments_dir.iterdir():
                if not entity_type_dir.is_dir():
                    continue

                entity_type = entity_type_dir.name

                for entity_id_dir in entity_type_dir.iterdir():
                    if not entity_id_dir.is_dir():
                        continue

                    entity_id = entity_id_dir.name
                    files = self._scan_directory_files(entity_id_dir)

                    if files:
                        key = (entity_type, entity_id)
                        result[key] = sorted([f.resolve() for f in files])

        # Scan floor_plans_photos directories
        # IT Glue exports floor plans as {asset_type}-floor-plans-photos/ directories
        # Files may be in subdirectories by ID, or directly with ID prefixes in filenames
        self._collect_floor_plans_attachments(export_path, result)

        return result

    def _collect_floor_plans_attachments(
        self,
        export_path: Path,
        result: dict[tuple[str, str], list[Path]],
    ) -> None:
        """Collect floor plan photo attachments from export.

        Handles two formats:
        1. {asset_type}-floor-plans-photos/{id}/files... (subdirectory structure)
        2. {asset_type}-floor-plans-photos/{id}-filename.jpg (prefixed filenames)

        Args:
            export_path: Path to the export directory.
            result: Dictionary to update with (entity_type, entity_id) -> files.
        """
        # Pattern for prefixed filenames: {id}-{filename}.{ext}
        id_prefix_pattern = re.compile(r"^(\d+)-(.+)$")

        # Look for directories matching *-floor-plans-photos pattern
        for floor_plans_dir in export_path.glob("*-floor-plans-photos"):
            if not floor_plans_dir.is_dir():
                continue

            # Extract the asset type from directory name
            asset_type = floor_plans_dir.name.replace("-floor-plans-photos", "")
            entity_type_key = f"{asset_type}_floor_plans_photos"

            for item in floor_plans_dir.iterdir():
                if item.is_dir():
                    # Subdirectory structure: {id}/files...
                    entity_id = item.name
                    files = self._scan_directory_files(item)
                    if files:
                        key = (entity_type_key, entity_id)
                        result[key] = sorted([f.resolve() for f in files])
                elif item.is_file():
                    # Prefixed filename structure: {id}-filename.ext
                    match = id_prefix_pattern.match(item.name)
                    if match:
                        entity_id = match.group(1)
                        key = (entity_type_key, entity_id)
                        if key not in result:
                            result[key] = []
                        result[key].append(item.resolve())

        # Also check for legacy floor_plans_photos directory (no prefix)
        legacy_floor_plans_dir = export_path / "floor_plans_photos"
        if legacy_floor_plans_dir.exists() and legacy_floor_plans_dir.is_dir():
            for item in legacy_floor_plans_dir.iterdir():
                if item.is_dir():
                    entity_id = item.name
                    files = self._scan_directory_files(item)
                    if files:
                        key = ("floor_plans_photos", entity_id)
                        result[key] = sorted([f.resolve() for f in files])
                elif item.is_file():
                    match = id_prefix_pattern.match(item.name)
                    if match:
                        entity_id = match.group(1)
                        key = ("floor_plans_photos", entity_id)
                        if key not in result:
                            result[key] = []
                        result[key].append(item.resolve())

    def get_document_folder_mapping(
        self, export_path: Path
    ) -> dict[str, Path]:
        """Get a mapping of document IDs to their folder paths.

        Recursively searches subdirectories (e.g., _Archive/, _Archives/).

        Args:
            export_path: Path to the IT Glue export directory.

        Returns:
            Dictionary mapping document ID to folder path.

        Raises:
            ExportNotFoundError: If the export path does not exist.
        """
        self._validate_export_path(export_path)

        mapping: dict[str, Path] = {}
        documents_dir = export_path / "documents"

        if not documents_dir.exists():
            return mapping

        # Use rglob to recursively search for DOC-* folders in any subdirectory
        for folder in documents_dir.rglob("DOC-*"):
            if not folder.is_dir():
                continue

            match = DOC_FOLDER_PATTERN.match(folder.name)
            if match:
                doc_id = match.group(2)
                mapping[doc_id] = folder

        return mapping
