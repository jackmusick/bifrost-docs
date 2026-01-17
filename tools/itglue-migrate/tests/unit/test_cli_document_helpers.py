"""Test CLI document helper functions."""

import tempfile
from pathlib import Path

from itglue_migrate.cli import _build_document_folder_map


def test_build_folder_map_root_level_document():
    """Test folder map correctly maps root-level documents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        documents_path = Path(tmpdir) / "documents"
        documents_path.mkdir()

        # Create a root-level DOC folder
        doc_folder = documents_path / "DOC-12345-67890 My Document"
        doc_folder.mkdir()

        # Create an HTML file inside
        html_file = doc_folder / "index.html"
        html_file.write_text("<html><body>Test</body></html>")

        # Build folder map
        folder_map = _build_document_folder_map(documents_path)

        # Verify
        assert "67890" in folder_map
        path, html = folder_map["67890"]
        assert path == "/"
        assert html is not None
        assert html.name == "index.html"


def test_build_folder_map_nested_document():
    """Test folder map correctly maps nested documents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        documents_path = Path(tmpdir) / "documents"
        documents_path.mkdir()

        # Create a nested DOC folder
        parent_folder = documents_path / "servers"
        parent_folder.mkdir()

        doc_folder = parent_folder / "DOC-12345-67890 Server Config"
        doc_folder.mkdir()

        # Create an HTML file inside
        html_file = doc_folder / "document.html"
        html_file.write_text("<html><body>Test</body></html>")

        # Build folder map
        folder_map = _build_document_folder_map(documents_path)

        # Verify
        assert "67890" in folder_map
        path, html = folder_map["67890"]
        assert path == "/servers"
        assert html is not None
        assert html.name == "document.html"


def test_build_folder_map_deeply_nested_document():
    """Test folder map correctly maps deeply nested documents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        documents_path = Path(tmpdir) / "documents"
        documents_path.mkdir()

        # Create a deeply nested DOC folder
        parent_folder = documents_path / "Infrastructure" / "Network"
        parent_folder.mkdir(parents=True)

        doc_folder = parent_folder / "DOC-12345-67890 Network Diagram"
        doc_folder.mkdir()

        # Create an HTML file inside
        html_file = doc_folder / "index.html"
        html_file.write_text("<html><body>Test</body></html>")

        # Build folder map
        folder_map = _build_document_folder_map(documents_path)

        # Verify
        assert "67890" in folder_map
        path, html = folder_map["67890"]
        assert path == "/Infrastructure/Network"
        assert html is not None


def test_build_folder_map_nonexistent_directory():
    """Test folder map handles nonexistent directory gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        documents_path = Path(tmpdir) / "nonexistent"

        # Build folder map - should not raise
        folder_map = _build_document_folder_map(documents_path)

        # Verify empty map
        assert len(folder_map) == 0


def test_build_folder_map_no_html_file():
    """Test folder map handles folders without HTML files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        documents_path = Path(tmpdir) / "documents"
        documents_path.mkdir()

        # Create a DOC folder without HTML
        doc_folder = documents_path / "DOC-12345-67890 Empty Doc"
        doc_folder.mkdir()

        # Build folder map
        folder_map = _build_document_folder_map(documents_path)

        # Verify path is set but HTML is None
        assert "67890" in folder_map
        path, html = folder_map["67890"]
        assert path == "/"
        assert html is None
