"""Unit tests for the document processor module."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from itglue_migrate.api_client import APIError
from itglue_migrate.document_processor import (
    DocumentNotFoundError,
    DocumentProcessor,
    DocumentProcessorError,
    ImageUploadError,
    _guess_attachment_mime_type,
    _guess_image_mime_type,
)
from itglue_migrate.state import MigrationState


def _mock_client(processor: DocumentProcessor) -> Any:
    """Cast processor.client to Any for mock assertions."""
    return processor.client


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_client() -> Any:
    """Create a mock BifrostDocs client."""
    client: Any = MagicMock()
    client.upload_document_image = AsyncMock(
        return_value={
            "id": "img-uuid-123",
            "upload_url": "https://s3.example.com/upload",
            "image_url": "https://cdn.example.com/images/img-uuid-123",
            "expires_in": 3600,
        }
    )
    client.upload_file_to_presigned_url = AsyncMock()
    client.create_attachment = AsyncMock(
        return_value={
            "id": "att-uuid-456",
            "filename": "test.pdf",
            "upload_url": "https://s3.example.com/upload-attachment",
            "expires_in": 3600,
        }
    )
    return client


@pytest.fixture
def processor(mock_client: Any, temp_dir: Path) -> DocumentProcessor:
    """Create a document processor instance."""
    return DocumentProcessor(mock_client, temp_dir)


class TestGuessMimeType:
    """Test MIME type guessing functions."""

    def test_guess_image_mime_type_by_extension(self) -> None:
        """Test guessing image MIME type by file extension."""
        assert _guess_image_mime_type(Path("image.jpg")) == "image/jpeg"
        assert _guess_image_mime_type(Path("image.jpeg")) == "image/jpeg"
        assert _guess_image_mime_type(Path("image.png")) == "image/png"
        assert _guess_image_mime_type(Path("image.gif")) == "image/gif"
        assert _guess_image_mime_type(Path("image.bmp")) == "image/bmp"
        assert _guess_image_mime_type(Path("image.webp")) == "image/webp"
        assert _guess_image_mime_type(Path("image.svg")) == "image/svg+xml"
        assert _guess_image_mime_type(Path("image.ico")) == "image/x-icon"
        assert _guess_image_mime_type(Path("image.tiff")) == "image/tiff"
        assert _guess_image_mime_type(Path("image.tif")) == "image/tiff"

    def test_guess_image_mime_type_by_magic_number_png(self) -> None:
        """Test guessing PNG by magic number."""
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert _guess_image_mime_type(Path("noext"), png_header) == "image/png"

    def test_guess_image_mime_type_by_magic_number_jpeg(self) -> None:
        """Test guessing JPEG by magic number."""
        jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        assert _guess_image_mime_type(Path("noext"), jpeg_header) == "image/jpeg"

    def test_guess_image_mime_type_by_magic_number_gif(self) -> None:
        """Test guessing GIF by magic number."""
        gif87a_header = b"GIF87a" + b"\x00" * 100
        gif89a_header = b"GIF89a" + b"\x00" * 100
        assert _guess_image_mime_type(Path("noext"), gif87a_header) == "image/gif"
        assert _guess_image_mime_type(Path("noext"), gif89a_header) == "image/gif"

    def test_guess_image_mime_type_by_magic_number_webp(self) -> None:
        """Test guessing WebP by magic number."""
        webp_header = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
        assert _guess_image_mime_type(Path("noext"), webp_header) == "image/webp"

    def test_guess_image_mime_type_by_magic_number_bmp(self) -> None:
        """Test guessing BMP by magic number."""
        bmp_header = b"BM" + b"\x00" * 100
        assert _guess_image_mime_type(Path("noext"), bmp_header) == "image/bmp"

    def test_guess_image_mime_type_unknown_defaults_to_png(self) -> None:
        """Test that unknown images default to PNG."""
        assert _guess_image_mime_type(Path("noext")) == "image/png"
        assert _guess_image_mime_type(Path("noext"), b"\x00\x01\x02") == "image/png"

    def test_guess_attachment_mime_type(self) -> None:
        """Test guessing attachment MIME types."""
        assert _guess_attachment_mime_type(Path("doc.pdf")) == "application/pdf"
        assert _guess_attachment_mime_type(Path("doc.txt")) == "text/plain"
        # Unknown defaults to octet-stream
        assert (
            _guess_attachment_mime_type(Path("unknown.unknownextension"))
            == "application/octet-stream"
        )


class TestExceptions:
    """Test exception classes."""

    def test_document_not_found_error(self, temp_dir: Path) -> None:
        """Test DocumentNotFoundError attributes."""
        error = DocumentNotFoundError("123", temp_dir)
        assert error.doc_id == "123"
        assert error.export_path == temp_dir
        assert "123" in str(error)
        assert str(temp_dir) in str(error)

    def test_image_upload_error(self) -> None:
        """Test ImageUploadError attributes."""
        error = ImageUploadError(Path("/test/image.png"), "Network error")
        assert error.image_path == Path("/test/image.png")
        assert error.reason == "Network error"
        assert "image.png" in str(error)
        assert "Network error" in str(error)

    def test_document_processor_error_is_base_exception(self) -> None:
        """Test that DocumentProcessorError is the base exception."""
        assert issubclass(DocumentNotFoundError, DocumentProcessorError)
        assert issubclass(ImageUploadError, DocumentProcessorError)


class TestDocumentProcessorInit:
    """Test DocumentProcessor initialization."""

    def test_init_creates_instance(
        self, mock_client: Any, temp_dir: Path
    ) -> None:
        """Test that processor initializes correctly."""
        processor = DocumentProcessor(mock_client, temp_dir)

        assert processor.client is mock_client
        assert processor.export_path == temp_dir
        assert processor.scanner is not None
        assert processor._image_url_cache == {}

    def test_cache_operations(self, processor: DocumentProcessor) -> None:
        """Test cache property and clear methods."""
        assert processor.cache_size == 0

        # Manually add to cache for testing
        processor._image_url_cache["/test/path"] = "https://example.com/img"
        assert processor.cache_size == 1

        processor.clear_cache()
        assert processor.cache_size == 0


class TestLoadDocumentHtml:
    """Test _load_document_html method."""

    def test_load_html_from_document_folder(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test loading HTML from document folder."""
        doc_dir = temp_dir / "documents" / "DOC-1-100 Test Document"
        doc_dir.mkdir(parents=True)
        (doc_dir / "index.html").write_text("<html><body>Test</body></html>")

        html = processor._load_document_html("100", "Test Document")

        assert html == "<html><body>Test</body></html>"

    def test_load_html_prefers_index_html(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that index.html is preferred over other HTML files."""
        doc_dir = temp_dir / "documents" / "DOC-1-100 Test Document"
        doc_dir.mkdir(parents=True)
        (doc_dir / "other.html").write_text("<html>Other</html>")
        (doc_dir / "index.html").write_text("<html>Index</html>")

        html = processor._load_document_html("100", "Test Document")

        assert html == "<html>Index</html>"

    def test_load_html_falls_back_to_first_html(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test fallback to first HTML file when no index.html."""
        doc_dir = temp_dir / "documents" / "DOC-1-100 Test Document"
        doc_dir.mkdir(parents=True)
        (doc_dir / "content.html").write_text("<html>Content</html>")

        html = processor._load_document_html("100", "Test Document")

        assert html == "<html>Content</html>"

    def test_load_html_returns_none_when_folder_not_found(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test returns None when document folder doesn't exist."""
        (temp_dir / "documents").mkdir()

        html = processor._load_document_html("999", "Missing")

        assert html is None

    def test_load_html_returns_none_when_no_html_files(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test returns None when folder exists but no HTML files."""
        doc_dir = temp_dir / "documents" / "DOC-1-100 Empty"
        doc_dir.mkdir(parents=True)
        (doc_dir / "readme.txt").write_text("No HTML here")

        html = processor._load_document_html("100", "Empty")

        assert html is None

    def test_load_html_handles_latin1_encoding(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test loading HTML with latin-1 encoding fallback."""
        doc_dir = temp_dir / "documents" / "DOC-1-100 Latin"
        doc_dir.mkdir(parents=True)
        # Write bytes that are valid latin-1 but not UTF-8
        (doc_dir / "index.html").write_bytes(b"<html>\xe9</html>")

        html = processor._load_document_html("100", "Latin")

        # Should succeed with latin-1 fallback
        assert html is not None
        assert "<html>" in html


class TestExtractImagePaths:
    """Test _extract_image_paths method."""

    def test_extract_image_paths_single_image(
        self, processor: DocumentProcessor
    ) -> None:
        """Test extracting single image path."""
        html = '<html><body><img src="test.png" alt="Test"></body></html>'

        paths = processor._extract_image_paths(html)

        assert paths == ["test.png"]

    def test_extract_image_paths_multiple_images(
        self, processor: DocumentProcessor
    ) -> None:
        """Test extracting multiple image paths."""
        html = """
        <html>
        <body>
            <img src="img1.png">
            <img src="img2.jpg" alt="Second">
            <img src="path/to/img3.gif">
        </body>
        </html>
        """

        paths = processor._extract_image_paths(html)

        assert len(paths) == 3
        assert "img1.png" in paths
        assert "img2.jpg" in paths
        assert "path/to/img3.gif" in paths

    def test_extract_image_paths_handles_quotes(
        self, processor: DocumentProcessor
    ) -> None:
        """Test extracting paths with different quote styles."""
        html = """<img src="double.png"><img src='single.png'>"""

        paths = processor._extract_image_paths(html)

        assert len(paths) == 2
        assert "double.png" in paths
        assert "single.png" in paths

    def test_extract_image_paths_empty_html(
        self, processor: DocumentProcessor
    ) -> None:
        """Test extracting paths from HTML without images."""
        html = "<html><body>No images here</body></html>"

        paths = processor._extract_image_paths(html)

        assert paths == []

    def test_extract_image_paths_complex_attributes(
        self, processor: DocumentProcessor
    ) -> None:
        """Test extracting paths from img tags with many attributes."""
        html = '<img class="diagram" src="1/docs/2/images/123" width="500" height="300">'

        paths = processor._extract_image_paths(html)

        assert paths == ["1/docs/2/images/123"]


class TestResolveImagePath:
    """Test _resolve_image_path method."""

    def test_resolve_relative_path(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test resolving relative image path."""
        doc_folder = temp_dir / "doc"
        doc_folder.mkdir()
        img_file = doc_folder / "image.png"
        img_file.write_bytes(b"PNG")

        result = processor._resolve_image_path(doc_folder, "image.png")

        assert result == img_file.resolve()

    def test_resolve_nested_path(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test resolving nested image path (IT Glue format)."""
        doc_folder = temp_dir / "doc"
        images_dir = doc_folder / "1" / "docs" / "100" / "images"
        images_dir.mkdir(parents=True)
        img_file = images_dir / "img123"
        img_file.write_bytes(b"PNG")

        result = processor._resolve_image_path(
            doc_folder, "1/docs/100/images/img123"
        )

        assert result == img_file.resolve()

    def test_resolve_path_with_leading_slash(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test resolving path with leading slash."""
        doc_folder = temp_dir / "doc"
        images_dir = doc_folder / "images"
        images_dir.mkdir(parents=True)
        img_file = images_dir / "test.png"
        img_file.write_bytes(b"PNG")

        result = processor._resolve_image_path(doc_folder, "/images/test.png")

        assert result == img_file.resolve()

    def test_resolve_returns_none_for_missing_file(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test returns None when image file doesn't exist."""
        doc_folder = temp_dir / "doc"
        doc_folder.mkdir()

        result = processor._resolve_image_path(doc_folder, "missing.png")

        assert result is None

    def test_resolve_skips_external_urls(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that external URLs return None."""
        doc_folder = temp_dir / "doc"
        doc_folder.mkdir()

        assert processor._resolve_image_path(
            doc_folder, "https://example.com/img.png"
        ) is None
        assert processor._resolve_image_path(
            doc_folder, "http://example.com/img.png"
        ) is None
        assert processor._resolve_image_path(
            doc_folder, "data:image/png;base64,..."
        ) is None


class TestTransformHtml:
    """Test _transform_html method."""

    def test_transform_html_single_replacement(
        self, processor: DocumentProcessor
    ) -> None:
        """Test transforming HTML with single image replacement."""
        html = '<img src="old/path.png">'
        replacements = {"old/path.png": "https://cdn.example.com/new.png"}

        result = processor._transform_html(html, replacements)

        assert 'src="https://cdn.example.com/new.png"' in result
        assert 'src="old/path.png"' not in result

    def test_transform_html_multiple_replacements(
        self, processor: DocumentProcessor
    ) -> None:
        """Test transforming HTML with multiple replacements."""
        html = '<img src="img1.png"><img src="img2.jpg">'
        replacements = {
            "img1.png": "https://cdn.example.com/1.png",
            "img2.jpg": "https://cdn.example.com/2.jpg",
        }

        result = processor._transform_html(html, replacements)

        assert 'src="https://cdn.example.com/1.png"' in result
        assert 'src="https://cdn.example.com/2.jpg"' in result

    def test_transform_html_preserves_other_attributes(
        self, processor: DocumentProcessor
    ) -> None:
        """Test that other img attributes are preserved."""
        html = '<img class="diagram" src="old.png" alt="Test" width="500">'
        replacements = {"old.png": "https://cdn.example.com/new.png"}

        result = processor._transform_html(html, replacements)

        assert 'class="diagram"' in result
        assert 'alt="Test"' in result
        assert 'width="500"' in result
        assert 'src="https://cdn.example.com/new.png"' in result

    def test_transform_html_empty_replacements(
        self, processor: DocumentProcessor
    ) -> None:
        """Test that empty replacements return unchanged HTML."""
        html = '<img src="unchanged.png">'

        result = processor._transform_html(html, {})

        assert result == html

    def test_transform_html_handles_special_characters(
        self, processor: DocumentProcessor
    ) -> None:
        """Test that special regex characters in paths are handled."""
        html = '<img src="path/with.dots/and(parens)/img.png">'
        replacements = {
            "path/with.dots/and(parens)/img.png": "https://cdn.example.com/new.png"
        }

        result = processor._transform_html(html, replacements)

        assert 'src="https://cdn.example.com/new.png"' in result


class TestCleanHtml:
    """Test _clean_html method."""

    def test_removes_br_before_closing_li(
        self, processor: DocumentProcessor
    ) -> None:
        """Test removing <br> tag at end of list item."""
        html = "<ul><li>AutoCAD (Latest version)<br></li></ul>"

        result = processor._clean_html(html)

        assert result == "<ul><li>AutoCAD (Latest version)</li></ul>"

    def test_removes_br_self_closing_before_li(
        self, processor: DocumentProcessor
    ) -> None:
        """Test removing self-closing <br/> tag at end of list item."""
        html = "<ul><li>AutoCAD (Latest version)<br/></li></ul>"

        result = processor._clean_html(html)

        assert result == "<ul><li>AutoCAD (Latest version)</li></ul>"

    def test_removes_br_with_space_before_closing_li(
        self, processor: DocumentProcessor
    ) -> None:
        """Test removing <br > tag with space before closing li."""
        html = "<ul><li>Item<br ></li></ul>"

        result = processor._clean_html(html)

        assert result == "<ul><li>Item</li></ul>"

    def test_removes_br_before_nested_ul(
        self, processor: DocumentProcessor
    ) -> None:
        """Test removing <br> before nested <ul>."""
        html = "<ul><li>Parent<br><ul><li>Child</li></ul></li></ul>"

        result = processor._clean_html(html)

        assert result == "<ul><li>Parent<ul><li>Child</li></ul></li></ul>"

    def test_removes_br_before_nested_ol(
        self, processor: DocumentProcessor
    ) -> None:
        """Test removing <br> before nested <ol>."""
        html = "<ul><li>Parent<br/><ol><li>Child</li></ol></li></ul>"

        result = processor._clean_html(html)

        assert result == "<ul><li>Parent<ol><li>Child</li></ol></li></ul>"

    def test_handles_multiple_list_items(
        self, processor: DocumentProcessor
    ) -> None:
        """Test cleaning multiple list items with <br> tags."""
        html = "<ul><li>Item 1<br></li><li>Item 2<br/></li><li>Item 3<br></li></ul>"

        result = processor._clean_html(html)

        assert result == "<ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>"

    def test_preserves_br_outside_list_items(
        self, processor: DocumentProcessor
    ) -> None:
        """Test that <br> tags outside list items are preserved."""
        html = "<p>Line 1<br>Line 2</p>"

        result = processor._clean_html(html)

        assert result == "<p>Line 1<br>Line 2</p>"

    def test_preserves_br_in_middle_of_list_item(
        self, processor: DocumentProcessor
    ) -> None:
        """Test that <br> tags in the middle of list items are preserved."""
        html = "<ul><li>Line 1<br>Line 2</li></ul>"

        result = processor._clean_html(html)

        # <br> in the middle (not immediately before </li>) should be preserved
        assert result == "<ul><li>Line 1<br>Line 2</li></ul>"

    def test_case_insensitive_br_tags(
        self, processor: DocumentProcessor
    ) -> None:
        """Test that BR tags in different cases are handled."""
        html = "<ul><li>Item 1<BR></li><li>Item 2<Br></li><li>Item 3<bR/></li></ul>"

        result = processor._clean_html(html)

        assert result == "<ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>"

    def test_handles_whitespace_between_br_and_li(
        self, processor: DocumentProcessor
    ) -> None:
        """Test handling whitespace between <br> and </li>."""
        html = "<ul><li>Item<br>  </li></ul>"

        result = processor._clean_html(html)

        assert result == "<ul><li>Item</li></ul>"

    def test_handles_complex_nested_lists(
        self, processor: DocumentProcessor
    ) -> None:
        """Test cleaning complex nested lists from IT Glue export."""
        html = """<ul>
<li>AutoCAD (Latest version)<br></li>
<li>AutoDesk Vault 2024<br></li>
<li>Bluebeam Revu 21<br></li>
<li>Microsoft Office Pro Plus<br>
<ul>
<li>Outlook<br></li>
<li>Word<br></li>
<li>Excel<br></li>
</ul>
</li>
</ul>"""

        result = processor._clean_html(html)

        # All <br> before </li> or <ul> should be removed
        assert "<br></li>" not in result
        assert "<br>\n</li>" not in result
        assert "<br>\n<ul>" not in result


class TestUploadImage:
    """Test _upload_image method."""

    @pytest.mark.asyncio
    async def test_upload_image_success(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test successful image upload."""
        img_path = temp_dir / "test.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)

        result = await processor._upload_image(img_path, "org-uuid-123")

        assert result == "https://cdn.example.com/images/img-uuid-123"
        _mock_client(processor).upload_document_image.assert_called_once()
        _mock_client(processor).upload_file_to_presigned_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_image_uses_cache(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that repeated uploads use cache."""
        img_path = temp_dir / "test.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)

        # First upload
        result1 = await processor._upload_image(img_path, "org-uuid-123")
        # Second upload should use cache
        result2 = await processor._upload_image(img_path, "org-uuid-123")

        assert result1 == result2
        # Should only call API once
        assert _mock_client(processor).upload_document_image.call_count == 1

    @pytest.mark.asyncio
    async def test_upload_image_skips_empty_file(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that empty files are skipped."""
        img_path = temp_dir / "empty.png"
        img_path.write_bytes(b"")

        result = await processor._upload_image(img_path, "org-uuid-123")

        assert result is None
        _mock_client(processor).upload_document_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_image_adds_extension_to_extensionless(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that extension is added to files without one."""
        img_path = temp_dir / "noext"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)

        await processor._upload_image(img_path, "org-uuid-123")

        # Check that filename with extension was passed
        call_kwargs = _mock_client(processor).upload_document_image.call_args[1]
        assert call_kwargs["filename"] == "noext.png"

    @pytest.mark.asyncio
    async def test_upload_image_handles_api_error(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of API errors."""
        from itglue_migrate.api_client import APIError

        processor.client.upload_document_image = AsyncMock(
            side_effect=APIError(500, "Server error")
        )

        img_path = temp_dir / "test.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)

        result = await processor._upload_image(img_path, "org-uuid-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_upload_image_handles_missing_file(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of missing files."""
        img_path = temp_dir / "missing.png"

        result = await processor._upload_image(img_path, "org-uuid-123")

        assert result is None


class TestProcessDocument:
    """Test process_document method."""

    @pytest.mark.asyncio
    async def test_process_document_no_html(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing document when HTML not found."""
        (temp_dir / "documents").mkdir()

        html, warnings = await processor.process_document(
            {"id": "999", "name": "Missing"}, "org-uuid"
        )

        assert html == ""
        assert len(warnings) == 1
        assert "not found" in warnings[0]

    @pytest.mark.asyncio
    async def test_process_document_no_images(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing document with no images."""
        doc_dir = temp_dir / "documents" / "DOC-1-100 Test"
        doc_dir.mkdir(parents=True)
        (doc_dir / "index.html").write_text("<html><body>No images</body></html>")

        html, warnings = await processor.process_document(
            {"id": "100", "name": "Test"}, "org-uuid"
        )

        assert html == "<html><body>No images</body></html>"
        assert len(warnings) == 0

    @pytest.mark.asyncio
    async def test_process_document_with_images(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing document with images."""
        doc_dir = temp_dir / "documents" / "DOC-1-100 Test"
        images_dir = doc_dir / "1" / "docs" / "100" / "images"
        images_dir.mkdir(parents=True)

        # Create image file
        (images_dir / "img123").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)

        # Create HTML referencing the image
        html_content = '<img src="1/docs/100/images/img123">'
        (doc_dir / "index.html").write_text(html_content)

        html, warnings = await processor.process_document(
            {"id": "100", "name": "Test"}, "org-uuid"
        )

        assert "https://cdn.example.com/images/img-uuid-123" in html
        assert len(warnings) == 0

    @pytest.mark.asyncio
    async def test_process_document_missing_image_adds_warning(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that missing images generate warnings."""
        doc_dir = temp_dir / "documents" / "DOC-1-100 Test"
        doc_dir.mkdir(parents=True)

        # HTML references an image that doesn't exist
        (doc_dir / "index.html").write_text('<img src="missing.png">')

        html, warnings = await processor.process_document(
            {"id": "100", "name": "Test"}, "org-uuid"
        )

        assert len(warnings) == 1
        assert "not found" in warnings[0]


class TestUploadEntityAttachments:
    """Test upload_entity_attachments method."""

    @pytest.mark.asyncio
    async def test_upload_entity_attachments_success(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test uploading entity attachments."""
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file1.pdf").write_bytes(b"PDF content")
        (config_dir / "file2.txt").write_bytes(b"Text content")

        count = await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-config-uuid"
        )

        assert count == 2
        assert _mock_client(processor).create_attachment.call_count == 2
        assert _mock_client(processor).upload_file_to_presigned_url.call_count == 2

    @pytest.mark.asyncio
    async def test_upload_entity_attachments_no_attachments(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test when entity has no attachments."""
        (temp_dir / "attachments" / "configurations").mkdir(parents=True)

        count = await processor.upload_entity_attachments(
            "configurations", "999", "org-uuid", "our-config-uuid"
        )

        assert count == 0
        _mock_client(processor).create_attachment.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_entity_attachments_maps_entity_type(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that IT Glue entity types are mapped correctly."""
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF")

        await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-uuid"
        )

        # Should map "configurations" to "configuration"
        call_kwargs = _mock_client(processor).create_attachment.call_args[1]
        assert call_kwargs["entity_type"] == "configuration"

    @pytest.mark.asyncio
    async def test_upload_entity_attachments_skips_empty_files(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that empty files are skipped."""
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "empty.pdf").write_bytes(b"")
        (config_dir / "valid.pdf").write_bytes(b"PDF content")

        count = await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-uuid"
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_upload_entity_attachments_handles_api_error(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of API errors during attachment upload."""
        processor.client.create_attachment = AsyncMock(
            side_effect=APIError(500, "Server error")
        )

        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF content")

        count = await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-uuid"
        )

        assert count == 0


class TestUploadEntityAttachmentsWithState:
    """Test upload_entity_attachments with state tracking."""

    @pytest.mark.asyncio
    async def test_skips_already_completed_attachments(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Should skip attachments already marked as completed."""
        # Create temp export with attachment
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file1.pdf").write_bytes(b"PDF content")
        (config_dir / "file2.pdf").write_bytes(b"PDF content 2")

        # Create state with first attachment already completed
        state = MigrationState()
        state.mark_attachment_completed("configurations", "123", "file1.pdf")

        # Call upload_entity_attachments
        count = await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-config-uuid", state=state
        )

        # Verify only one attachment was uploaded (the second one)
        assert count == 1
        # API should only have been called once for file2.pdf
        assert _mock_client(processor).create_attachment.call_count == 1
        call_kwargs = _mock_client(processor).create_attachment.call_args[1]
        assert call_kwargs["filename"] == "file2.pdf"

    @pytest.mark.asyncio
    async def test_marks_attachment_completed_on_success(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Should mark attachment as completed after successful upload."""
        # Create temp export with attachment
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF content")

        # Create empty state
        state = MigrationState()

        # Call upload_entity_attachments
        count = await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-config-uuid", state=state
        )

        # Verify upload succeeded
        assert count == 1

        # Verify state.is_attachment_completed returns True
        assert state.is_attachment_completed("configurations", "123", "file.pdf")

    @pytest.mark.asyncio
    async def test_marks_attachment_failed_on_api_error(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Should mark attachment as failed on API error."""
        # Create temp export with attachment
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF content")

        # Mock API to raise error
        processor.client.create_attachment = AsyncMock(
            side_effect=APIError(500, "Server error")
        )

        # Create empty state
        state = MigrationState()

        # Call upload_entity_attachments
        count = await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-config-uuid", state=state
        )

        # Verify upload failed
        assert count == 0

        # Verify state.is_attachment_failed returns True
        assert state.is_attachment_failed("configurations", "123", "file.pdf")

        # Verify error message is captured
        error_msg = state.get_attachment_failure_error(
            "configurations", "123", "file.pdf"
        )
        assert error_msg is not None
        assert "Server error" in error_msg

    @pytest.mark.asyncio
    async def test_marks_attachment_failed_on_unexpected_error(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Should mark attachment as failed on unexpected error."""
        # Create temp export with attachment
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF content")

        # Mock API to raise unexpected error
        processor.client.create_attachment = AsyncMock(
            side_effect=RuntimeError("Unexpected failure")
        )

        # Create empty state
        state = MigrationState()

        # Call upload_entity_attachments
        count = await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-config-uuid", state=state
        )

        # Verify upload failed
        assert count == 0

        # Verify state.is_attachment_failed returns True
        assert state.is_attachment_failed("configurations", "123", "file.pdf")

    @pytest.mark.asyncio
    async def test_works_without_state(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Should work normally when state is None."""
        # Create temp export with attachment
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file.pdf").write_bytes(b"PDF content")

        # Call without state parameter
        count = await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-config-uuid"
        )

        # Verify upload succeeded
        assert count == 1
        assert _mock_client(processor).create_attachment.call_count == 1

    @pytest.mark.asyncio
    async def test_skips_all_completed_attachments(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Should return 0 when all attachments are already completed."""
        # Create temp export with attachments
        config_dir = temp_dir / "attachments" / "configurations" / "123"
        config_dir.mkdir(parents=True)
        (config_dir / "file1.pdf").write_bytes(b"PDF content")
        (config_dir / "file2.pdf").write_bytes(b"PDF content 2")

        # Mark both as completed in state
        state = MigrationState()
        state.mark_attachment_completed("configurations", "123", "file1.pdf")
        state.mark_attachment_completed("configurations", "123", "file2.pdf")

        # Call upload_entity_attachments
        count = await processor.upload_entity_attachments(
            "configurations", "123", "org-uuid", "our-config-uuid", state=state
        )

        # Verify no uploads happened
        assert count == 0
        _mock_client(processor).create_attachment.assert_not_called()
