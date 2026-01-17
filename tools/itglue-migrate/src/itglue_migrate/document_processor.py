"""Document processor for IT Glue migration.

This module handles document HTML transformation and image uploads,
converting IT Glue document HTML to use stable BifrostDocs image URLs.

Export structure expected:
    documents/
    └── DOC-{org_id}-{doc_id} Document Name/
        ├── index.html (or similar)
        └── {org_id}/docs/{doc_id}/images/
            └── {image_id} (no extension, binary files)

Image src format in HTML: <img src="{org_id}/docs/{doc_id}/images/{image_id}">
"""

from __future__ import annotations

import logging
import mimetypes
import re
from pathlib import Path
from typing import TYPE_CHECKING

from itglue_migrate.api_client import APIError, BifrostDocsClient
from itglue_migrate.attachments import DOC_FOLDER_PATTERN, AttachmentScanner
from itglue_migrate.state import MigrationState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Regex pattern for extracting image src attributes from HTML
IMG_SRC_PATTERN = re.compile(
    r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE
)

# Common image MIME types by extension or content
IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


def _guess_image_mime_type(file_path: Path, file_content: bytes | None = None) -> str:
    """Guess the MIME type of an image file.

    Args:
        file_path: Path to the image file.
        file_content: Optional file content for magic number detection.

    Returns:
        MIME type string (defaults to image/png if unknown).
    """
    # Try by extension first
    suffix = file_path.suffix.lower()
    if suffix in IMAGE_MIME_TYPES:
        return IMAGE_MIME_TYPES[suffix]

    # Try mimetypes module
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type and mime_type.startswith("image/"):
        return mime_type

    # Try magic number detection if content is available
    if file_content and len(file_content) >= 8:
        # PNG magic number
        if file_content[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        # JPEG magic number
        if file_content[:2] == b"\xff\xd8":
            return "image/jpeg"
        # GIF magic number
        if file_content[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        # WebP magic number
        if file_content[:4] == b"RIFF" and file_content[8:12] == b"WEBP":
            return "image/webp"
        # BMP magic number
        if file_content[:2] == b"BM":
            return "image/bmp"

    # Default to PNG for unknown images (common in IT Glue exports)
    return "image/png"


def _guess_attachment_mime_type(file_path: Path) -> str:
    """Guess the MIME type of an attachment file.

    Args:
        file_path: Path to the attachment file.

    Returns:
        MIME type string (defaults to application/octet-stream if unknown).
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


class DocumentProcessorError(Exception):
    """Base exception for document processor errors."""

    pass


class DocumentNotFoundError(DocumentProcessorError):
    """Raised when a document folder or HTML file is not found."""

    def __init__(self, doc_id: str, export_path: Path) -> None:
        self.doc_id = doc_id
        self.export_path = export_path
        super().__init__(
            f"Document HTML not found for ID {doc_id} in {export_path}"
        )


class ImageUploadError(DocumentProcessorError):
    """Raised when an image upload fails."""

    def __init__(self, image_path: Path, reason: str) -> None:
        self.image_path = image_path
        self.reason = reason
        super().__init__(f"Failed to upload image {image_path}: {reason}")


class DocumentProcessor:
    """Processor for IT Glue document HTML transformation and image uploads.

    This class handles:
    1. Loading document HTML from IT Glue export
    2. Extracting and uploading embedded images
    3. Transforming HTML to use new stable image URLs

    Example:
        >>> async with BifrostDocsClient(base_url, api_key) as client:
        ...     processor = DocumentProcessor(client, Path("/path/to/export"))
        ...     html, warnings = await processor.process_document(
        ...         {"id": "12345", "name": "Network Diagram"},
        ...         org_uuid="uuid-abc-123"
        ...     )
    """

    def __init__(self, client: BifrostDocsClient, export_path: Path) -> None:
        """Initialize the document processor.

        Args:
            client: BifrostDocs API client for uploading images.
            export_path: Path to the IT Glue export directory.
        """
        self.client = client
        self.export_path = export_path
        self.scanner = AttachmentScanner()
        self._image_url_cache: dict[str, str] = {}  # local path -> uploaded URL

    async def process_document(
        self, doc: dict, org_uuid: str
    ) -> tuple[str, list[str]]:
        """Process a document's HTML, uploading images and transforming content.

        Args:
            doc: Document dictionary with at least 'id' key.
                 Optional 'name' key helps locate the folder.
            org_uuid: Target organization UUID for image uploads.

        Returns:
            Tuple of (transformed_html, list_of_warnings).
            If document HTML is not found, returns ("", [warning_message]).

        Raises:
            DocumentProcessorError: If a critical error occurs during processing.
        """
        doc_id = str(doc.get("id", ""))
        doc_name = doc.get("name", "")
        warnings: list[str] = []

        # Step 1: Load HTML content from export
        html = self._load_document_html(doc_id, doc_name)
        if html is None:
            warnings.append(
                f"Document HTML not found for ID {doc_id} "
                f"(name: {doc_name or 'unknown'})"
            )
            return "", warnings

        # Clean HTML for tiptap compatibility (remove <br> inside list items)
        html = self._clean_html(html)

        # Step 2: Extract image paths from HTML
        image_srcs = self._extract_image_paths(html)
        if not image_srcs:
            logger.debug(f"No images found in document {doc_id}")
            return html, warnings

        # Step 3: Find document folder for resolving image paths
        doc_folder = self._find_document_folder(doc_id)
        if doc_folder is None:
            warnings.append(
                f"Document folder not found for ID {doc_id}, "
                "cannot resolve image paths"
            )
            return html, warnings

        # Step 4: Upload each image and build replacement map
        replacements: dict[str, str] = {}
        for src in image_srcs:
            image_path = self._resolve_image_path(doc_folder, src)
            if image_path is None:
                warnings.append(f"Image not found: {src}")
                continue

            new_url = await self._upload_image(image_path, org_uuid)
            if new_url is None:
                warnings.append(f"Failed to upload image: {src}")
                continue

            replacements[src] = new_url

        # Step 5: Transform HTML with new URLs
        if replacements:
            html = self._transform_html(html, replacements)
            logger.info(
                f"Document {doc_id}: replaced {len(replacements)} image URLs"
            )

        return html, warnings

    def _load_document_html(self, doc_id: str, doc_name: str) -> str | None:
        """Load HTML content from the export documents folder.

        Document folders are named like: DOC-{org_id}-{doc_id} Document Name/
        Inside, look for .html files (typically index.html or similar).

        Args:
            doc_id: The document ID to find.
            doc_name: The document name (helps with logging).

        Returns:
            HTML content as string, or None if not found.
        """
        doc_folder = self._find_document_folder(doc_id)
        if doc_folder is None:
            logger.debug(f"Document folder not found for ID {doc_id}")
            return None

        # Find HTML files in the document folder
        html_files = list(doc_folder.glob("*.html"))
        if not html_files:
            # Also check for .htm files
            html_files = list(doc_folder.glob("*.htm"))

        if not html_files:
            logger.debug(f"No HTML files found in {doc_folder}")
            return None

        # Prefer index.html if it exists, otherwise take the first one
        html_file = None
        for f in html_files:
            if f.name.lower() in ("index.html", "index.htm"):
                html_file = f
                break
        if html_file is None:
            html_file = html_files[0]

        # Read the HTML content
        try:
            return html_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            try:
                return html_file.read_text(encoding="latin-1")
            except OSError as e:
                logger.warning(f"Failed to read HTML file {html_file}: {e}")
                return None
        except OSError as e:
            logger.warning(f"Failed to read HTML file {html_file}: {e}")
            return None

    def _find_document_folder(self, doc_id: str) -> Path | None:
        """Find the document folder for a given document ID.

        Document folders may be nested in subdirectories (e.g., _Archive/, _Archives/).

        Args:
            doc_id: The document ID to find.

        Returns:
            Path to the document folder, or None if not found.
        """
        documents_dir = self.export_path / "documents"
        if not documents_dir.exists():
            return None

        doc_id_str = str(doc_id)

        # Use rglob to recursively search for DOC-* folders in any subdirectory
        for folder in documents_dir.rglob("DOC-*"):
            if not folder.is_dir():
                continue

            match = DOC_FOLDER_PATTERN.match(folder.name)
            if match and match.group(2) == doc_id_str:
                return folder

        return None

    def _extract_image_paths(self, html: str) -> list[str]:
        """Extract all image src values from HTML.

        Args:
            html: HTML content to parse.

        Returns:
            List of image src attribute values.
        """
        return IMG_SRC_PATTERN.findall(html)

    def _resolve_image_path(self, doc_folder: Path, src: str) -> Path | None:
        """Resolve an image src to an actual file path.

        IT Glue uses nested path format: {org_id}/docs/{doc_id}/images/{image_id}
        The image files often have no extension.

        Args:
            doc_folder: Path to the document folder.
            src: Image src attribute value from HTML.

        Returns:
            Resolved file path, or None if not found.
        """
        # Skip external URLs
        if src.startswith(("http://", "https://", "data:")):
            return None

        # Try relative to document folder first (most common)
        relative_path = doc_folder / src
        if relative_path.exists() and relative_path.is_file():
            return relative_path.resolve()

        # Try stripping leading slash
        if src.startswith("/"):
            clean_src = src.lstrip("/")
            clean_path = doc_folder / clean_src
            if clean_path.exists() and clean_path.is_file():
                return clean_path.resolve()

        # Try URL-decoded path
        try:
            from urllib.parse import unquote

            decoded_src = unquote(src)
            if decoded_src != src:
                decoded_path = doc_folder / decoded_src
                if decoded_path.exists() and decoded_path.is_file():
                    return decoded_path.resolve()
        except Exception:
            pass

        return None

    async def _upload_image(self, image_path: Path, org_uuid: str) -> str | None:
        """Upload an image and return its stable URL.

        Uses caching to avoid re-uploading the same image multiple times.

        Args:
            image_path: Local path to the image file.
            org_uuid: Target organization UUID.

        Returns:
            Stable image URL, or None on failure.
        """
        cache_key = str(image_path.resolve())

        # Check cache first
        if cache_key in self._image_url_cache:
            logger.debug(f"Using cached URL for {image_path.name}")
            return self._image_url_cache[cache_key]

        try:
            # Read file content
            file_content = image_path.read_bytes()
            file_size = len(file_content)

            if file_size == 0:
                logger.warning(f"Skipping empty image file: {image_path}")
                return None

            # Determine MIME type
            content_type = _guess_image_mime_type(image_path, file_content)

            # Generate filename with proper extension if needed
            filename = image_path.name
            if not image_path.suffix:
                # Add extension based on detected MIME type
                ext = {
                    "image/png": ".png",
                    "image/jpeg": ".jpg",
                    "image/gif": ".gif",
                    "image/webp": ".webp",
                    "image/bmp": ".bmp",
                    "image/svg+xml": ".svg",
                }.get(content_type, ".png")
                filename = f"{filename}{ext}"

            # Request upload URL from API
            upload_response = await self.client.upload_document_image(
                org_id=org_uuid,
                filename=filename,
                content_type=content_type,
                size_bytes=file_size,
            )

            upload_url = upload_response.get("upload_url")
            image_url = upload_response.get("image_url")

            if not upload_url or not image_url:
                logger.error(
                    f"Invalid upload response for {filename}: {upload_response}"
                )
                return None

            # Upload the file to presigned URL
            await self.client.upload_file_to_presigned_url(
                upload_url=upload_url,
                file_content=file_content,
                content_type=content_type,
            )

            # Cache and return the stable URL
            self._image_url_cache[cache_key] = image_url
            logger.debug(f"Uploaded image {filename} -> {image_url}")

            return image_url

        except APIError as e:
            logger.warning(f"API error uploading image {image_path}: {e}")
            return None
        except OSError as e:
            logger.warning(f"Failed to read image file {image_path}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error uploading image {image_path}: {e}")
            return None

    def _transform_html(self, html: str, replacements: dict[str, str]) -> str:
        """Replace image src values in HTML with new URLs.

        Args:
            html: Original HTML content.
            replacements: Dictionary mapping old src values to new URLs.

        Returns:
            Transformed HTML with updated image URLs.
        """
        if not replacements:
            return html

        # Escape special regex characters in the old values and do replacements
        result = html
        for old_src, new_url in replacements.items():
            # Use a function to replace within img tags only
            # This handles both single and double quotes
            pattern = re.compile(
                r'(<img\s+[^>]*src=["\'])' + re.escape(old_src) + r'(["\'][^>]*>)',
                re.IGNORECASE,
            )
            result = pattern.sub(r"\1" + new_url + r"\2", result)

        return result

    def _clean_html(self, html: str) -> str:
        """Clean HTML content for tiptap compatibility.

        Removes <br> tags inside <li> elements that cause list items
        to break across lines in the tiptap editor.

        Args:
            html: Original HTML content.

        Returns:
            Cleaned HTML with <br> tags removed from inside list items.
        """
        # Remove <br> and <br/> tags that appear at the end of <li> content
        # Pattern: <br> or <br/> followed by </li>
        html = re.sub(r"<br\s*/?>\s*(?=</li>)", "", html, flags=re.IGNORECASE)
        # Pattern: <br> or <br/> followed by nested <ul> or <ol>
        html = re.sub(r"<br\s*/?>\s*(?=<[uo]l>)", "", html, flags=re.IGNORECASE)
        return html

    async def upload_entity_attachments(
        self,
        entity_type: str,
        entity_id: str,
        org_uuid: str,
        our_entity_id: str,
        state: MigrationState | None = None,
        known_custom_asset_types: set[str] | None = None,
    ) -> int:
        """Upload all attachments for an entity to BifrostDocs.

        Finds attachments in the export attachments/{entity_type}/{entity_id}/
        folder and uploads each one via the presigned URL flow.

        Args:
            entity_type: IT Glue entity type (e.g., "configurations", "documents").
            entity_id: IT Glue entity ID.
            org_uuid: Target organization UUID.
            our_entity_id: Our entity UUID to attach files to.
            state: Optional migration state for tracking progress.

        Returns:
            Count of successfully uploaded attachments.
        """
        # Map IT Glue entity types to BifrostDocs entity types
        # Use three-tier mapping: standard types -> known custom assets -> unknown
        entity_type_mapping = {
            "configurations": "configuration",
            "documents": "document",
            "passwords": "password",
            "locations": "location",
        }

        # Tier 1: Check standard types
        if entity_type in entity_type_mapping:
            target_entity_type = entity_type_mapping[entity_type]
        # Tier 2: Check known custom asset types
        elif known_custom_asset_types and entity_type in known_custom_asset_types:
            target_entity_type = "custom_asset"
        # Tier 3: Unknown type - warn and map to custom_asset
        else:
            logger.warning(
                f"Unknown entity type '{entity_type}' - treating as custom_asset. "
                f"If this is incorrect, add it to the standard mapping or custom asset types."
            )
            target_entity_type = "custom_asset"

        # Get attachment files from export
        attachment_files = self.scanner.get_entity_attachments(
            self.export_path, entity_type, entity_id
        )

        if not attachment_files:
            logger.debug(
                f"No attachments found for {entity_type}/{entity_id}"
            )
            return 0

        uploaded_count = 0

        for file_path in attachment_files:
            filename = file_path.name

            # Skip if already completed
            if state and state.is_attachment_completed(entity_type, entity_id, filename):
                logger.debug(f"Skipping already completed attachment: {filename}")
                continue

            try:
                # Read file content
                file_content = file_path.read_bytes()
                file_size = len(file_content)

                if file_size == 0:
                    logger.warning(f"Skipping empty attachment: {file_path}")
                    continue

                # Determine MIME type
                content_type = _guess_attachment_mime_type(file_path)

                # Create attachment record and get presigned upload URL
                attachment_response = await self.client.create_attachment(
                    org_id=org_uuid,
                    entity_type=target_entity_type,
                    entity_id=our_entity_id,
                    filename=filename,
                    content_type=content_type,
                    size_bytes=file_size,
                )

                upload_url = attachment_response.get("upload_url")
                if not upload_url:
                    logger.error(
                        f"No upload URL in attachment response for {filename}"
                    )
                    continue

                # Upload the file
                await self.client.upload_file_to_presigned_url(
                    upload_url=upload_url,
                    file_content=file_content,
                    content_type=content_type,
                )

                uploaded_count += 1

                # Mark as completed in state
                if state:
                    state.mark_attachment_completed(entity_type, entity_id, filename)

                logger.debug(
                    f"Uploaded attachment: {filename} -> "
                    f"{target_entity_type}/{our_entity_id}"
                )

            except APIError as e:
                if state:
                    state.mark_attachment_failed(entity_type, entity_id, filename, str(e))
                logger.warning(
                    f"API error uploading attachment {filename}: {e}"
                )
            except OSError as e:
                if state:
                    state.mark_attachment_failed(entity_type, entity_id, filename, str(e))
                logger.warning(
                    f"Failed to read attachment file {file_path}: {e}"
                )
            except Exception as e:
                if state:
                    state.mark_attachment_failed(entity_type, entity_id, filename, str(e))
                logger.warning(
                    f"Unexpected error uploading attachment {filename}: {e}"
                )

        if uploaded_count > 0:
            logger.info(
                f"Uploaded {uploaded_count}/{len(attachment_files)} attachments "
                f"for {entity_type}/{entity_id}"
            )

        return uploaded_count

    def clear_cache(self) -> None:
        """Clear the image URL cache.

        Call this when starting a new organization to avoid
        cross-organization caching issues.
        """
        self._image_url_cache.clear()
        logger.debug("Cleared image URL cache")

    @property
    def cache_size(self) -> int:
        """Get the number of cached image URLs."""
        return len(self._image_url_cache)
