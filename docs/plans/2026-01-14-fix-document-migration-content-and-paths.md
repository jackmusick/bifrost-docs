# Fix Document Migration Content and Paths Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix ITGlue document migration to (1) upload actual HTML content with images instead of empty content, and (2) use correct folder paths by stripping the DOC prefix and extracting real folder names from the filesystem.

**Architecture:** The current `_migrate_documents()` function in `cli.py` only uses the CSV `content` field (which is empty) and the `locator` field (which has incorrect paths). The fix is to:
1. Use the existing `_build_document_folder_map()` helper to get correct paths from the filesystem
2. Use the existing `DocumentProcessor.process_document()` to read HTML files, upload images, and transform the content

**Tech Stack:** Python 3.11+, asyncio, httpx, pytest, existing ITGlue migration codebase

---

## Context

### Current Problems

1. **Missing Content**: Documents are created with empty `content` field because `cli.py:_migrate_documents()` uses `doc.get("content", "")` from the CSV, which doesn't contain the actual HTML.

2. **Incorrect Paths**: Folder paths contain the DOC prefix (e.g., "DOC-1774800-8077468") and miss the actual folder name (e.g., "Proofpoint go live template"). The code uses the CSV `locator` field instead of scanning the filesystem.

### Existing Correct Code

The `importers.py` file already has:
- `_build_document_folder_map()` (lines 26-85) - correctly extracts paths from DOC folder names
- `DocumentProcessor.process_document()` (document_processor.py:163-230) - reads HTML, uploads images, transforms content

But `cli.py:_migrate_documents()` doesn't use either of these!

### File Structure

```
tools/itglue-migrate/
├── src/itglue_migrate/
│   ├── cli.py                  # HAS BUG: _migrate_documents() function
│   ├── importers.py            # HAS CORRECT CODE: _build_document_folder_map()
│   └── document_processor.py   # HAS CORRECT CODE: DocumentProcessor.process_document()
└── tests/unit/
    └── test_document_processor.py  # Existing tests
```

---

## Task 1: Add Helper Function to Build Document Folder Map in cli.py

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/cli.py`
- Reference: `tools/itglue-migrate/src/itglue_migrate/importers.py:26-85`

**Why:** The `_build_document_folder_map()` function exists in `importers.py` but `cli.py` can't easily use it. We need a version in `cli.py` that the migration function can call.

**Step 1: Add the `_build_document_folder_map()` helper function to cli.py**

Add this function before the `_migrate_documents()` function (around line 1305):

```python
def _build_document_folder_map(
    documents_path: Path,
) -> dict[str, tuple[str, Path | None]]:
    """
    Scan export documents folder and map document IDs to (folder_path, html_file).

    The IT Glue export structure is:
    - documents/{folder}/DOC-{org}-{doc_id} {name}/{name}.html - nested in folder
    - documents/DOC-{org}-{doc_id} {name}/{name}.html - root level

    Args:
        documents_path: Path to the documents/ folder in the export.

    Returns:
        Dict mapping doc_id to (folder_path, html_file_path).
        folder_path is "/" for root-level documents, otherwise "/FolderName".
        html_file_path is the path to the HTML file, or None if not found.
    """
    import re
    from itglue_migrate.attachments import DOC_FOLDER_PATTERN

    result: dict[str, tuple[str, Path | None]] = {}

    if not documents_path.exists():
        logger.warning(f"Documents path does not exist: {documents_path}")
        return result

    # Walk the documents directory
    for item in documents_path.rglob("*"):
        if not item.is_dir():
            continue

        # Check if this is a DOC-* folder
        match = DOC_FOLDER_PATTERN.match(item.name)
        if not match:
            continue

        doc_id = match.group(1)

        # Determine the folder path based on parent
        # If parent is documents_path, it's root level ("/")
        # Otherwise, extract folder name from path between documents_path and item
        rel_path = item.relative_to(documents_path)
        parts = rel_path.parts

        if len(parts) == 1:
            # Root level: documents/DOC-xxx-123 Name/
            folder_path = "/"
        else:
            # Nested: documents/FolderName/DOC-xxx-123 Name/
            # The folder path is everything except the last DOC-* part
            folder_parts = parts[:-1]
            folder_path = "/" + "/".join(folder_parts)

        # Find HTML file inside the DOC-* folder
        html_files = list(item.glob("*.html"))
        html_file = html_files[0] if html_files else None

        result[doc_id] = (folder_path, html_file)
        logger.debug(f"Mapped document {doc_id} -> {folder_path}, {html_file}")

    logger.info(f"Built document folder map with {len(result)} entries")
    return result
```

**Step 2: Verify the code compiles**

Run: `cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate && python -m py_compile src/itglue_migrate/cli.py`

Expected: No output (successful compilation)

**Step 3: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add tools/itglue-migrate/src/itglue_migrate/cli.py
git commit -m "feat: add _build_document_folder_map helper to cli.py"
```

---

## Task 2: Fix _migrate_documents() to Use Correct Folder Paths

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/cli.py:1363-1404`

**Why:** The current code uses the CSV `locator` field which is often empty or contains the full DOC folder name with prefix. We need to use the folder map to get the correct path.

**Step 1: Modify _migrate_documents() to build and use the folder map**

Replace the path/content assignment section (lines 1363-1376) with this:

```python
            else:
                # Build folder map to get correct paths from filesystem
                documents_path = export_path / "documents"
                folder_map = _build_document_folder_map(documents_path)

                # Get folder path and HTML file from folder map
                path = "/"  # Default to root
                html_file = None

                if itglue_id in folder_map:
                    path, html_file = folder_map[itglue_id]
                    logger.debug(f"Document {itglue_id}: found in folder map with path '{path}'")
                else:
                    logger.debug(f"Document {itglue_id}: not found in folder map, using root path")

                # Read HTML content if file exists
                content = ""
                if html_file and html_file.exists():
                    try:
                        content = html_file.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        try:
                            content = html_file.read_text(encoding="latin-1")
                        except Exception as e:
                            logger.warning(f"Failed to read document file {html_file}: {e}")
                            content = ""

                created = await client.create_document(
                    org_id=org_uuid,
                    path=path,
                    name=name,
                    content=content,
                    metadata={"itglue_id": itglue_id},
                )
```

**Step 2: Verify the code compiles**

Run: `cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate && python -m py_compile src/itglue_migrate/cli.py`

Expected: No output (successful compilation)

**Step 3: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add tools/itglue-migrate/src/itglue_migrate/cli.py
git commit -m "fix: use folder map for correct document paths and read HTML content"
```

---

## Task 3: Add Image Processing to _migrate_documents()

**Files:**
- Modify: `tools/itglue-migrate/src/itglue_migrate/cli.py:1305-1404`
- Reference: `tools/itglue-migrate/src/itglue_migrate/document_processor.py:163-230`

**Why:** Reading HTML is not enough - we need to process it with DocumentProcessor to upload images and replace their URLs with the new BifrostDocs URLs.

**Step 1: Modify _migrate_documents() to process document HTML with image uploads**

After reading the HTML content (after the content reading block), add DocumentProcessor call. Replace the content reading section with:

```python
            else:
                # Build folder map to get correct paths from filesystem
                documents_path = export_path / "documents"
                folder_map = _build_document_folder_map(documents_path)

                # Get folder path and HTML file from folder map
                path = "/"  # Default to root
                html_file = None

                if itglue_id in folder_map:
                    path, html_file = folder_map[itglue_id]
                    logger.debug(f"Document {itglue_id}: found in folder map with path '{path}'")
                else:
                    logger.debug(f"Document {itglue_id}: not found in folder map, using root path")

                # Process document HTML: read, upload images, transform content
                content = ""
                content_warnings = []

                if doc_processor and html_file and html_file.exists():
                    try:
                        # Use DocumentProcessor to read HTML, upload images, and transform
                        processed_html, warnings = await doc_processor.process_document(
                            doc=doc,
                            org_uuid=org_uuid,
                        )
                        content = processed_html
                        content_warnings = warnings

                        if content_warnings:
                            for warning in content_warnings:
                                reporter.warning(f"Document '{name}': {warning}")

                    except Exception as e:
                        reporter.warning(f"Failed to process document HTML for '{name}': {e}")
                        # Fallback: read raw HTML
                        try:
                            content = html_file.read_text(encoding="utf-8")
                        except UnicodeDecodeError:
                            try:
                                content = html_file.read_text(encoding="latin-1")
                            except Exception as e2:
                                logger.warning(f"Failed to read document file {html_file}: {e2}")
                                content = ""

                created = await client.create_document(
                    org_id=org_uuid,
                    path=path,
                    name=name,
                    content=content,
                    metadata={"itglue_id": itglue_id},
                )
```

**Wait!** The `DocumentProcessor.process_document()` signature is different - it expects the folder to be found via its internal `_find_document_folder()` method, but we already have the html_file. Let me check the signature again from document_processor.py:

Looking at lines 163-230, the signature is:
```python
async def process_document(
    self, doc: dict, org_uuid: str
) -> tuple[str, list[str]]:
```

It takes the doc dict (with 'id' and 'name') and org_uuid, then internally finds the folder and HTML file. So we should use it directly!

**CORRECTED Step 1: Use DocumentProcessor.process_document() correctly**

```python
            else:
                # Build folder map to get correct paths from filesystem
                documents_path = export_path / "documents"
                folder_map = _build_document_folder_map(documents_path)

                # Get folder path from folder map (for path field only)
                path = "/"  # Default to root

                if itglue_id in folder_map:
                    path, _ = folder_map[itglue_id]
                    logger.debug(f"Document {itglue_id}: found in folder map with path '{path}'")
                else:
                    logger.debug(f"Document {itglue_id}: not found in folder map, using root path")

                # Process document HTML: upload images, transform content
                content = ""
                content_warnings = []

                if doc_processor:
                    try:
                        # Use DocumentProcessor to find HTML, upload images, and transform content
                        processed_html, warnings = await doc_processor.process_document(
                            doc=doc,
                            org_uuid=org_uuid,
                        )
                        content = processed_html
                        content_warnings = warnings

                        if content_warnings:
                            for warning in content_warnings:
                                reporter.warning(f"Document '{name}': {warning}")

                    except Exception as e:
                        reporter.warning(f"Failed to process document HTML for '{name}': {e}")
                        content = ""

                created = await client.create_document(
                    org_id=org_uuid,
                    path=path,
                    name=name,
                    content=content,
                    metadata={"itglue_id": itglue_id},
                )
```

**Step 2: Verify the code compiles**

Run: `cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate && python -m py_compile src/itglue_migrate/cli.py`

Expected: No output (successful compilation)

**Step 3: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add tools/itglue-migrate/src/itglue_migrate/cli.py
git commit -m "feat: process document HTML with DocumentProcessor for image uploads"
```

---

## Task 4: Write Unit Test for _build_document_folder_map()

**Files:**
- Create: `tools/itglue-migrate/tests/unit/test_cli_document_helpers.py`

**Why:** We need to verify the folder map helper correctly extracts paths from various DOC folder structures.

**Step 1: Write failing test for root-level documents**

```python
"""Test CLI document helper functions."""

import tempfile
from pathlib import Path

import pytest

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
```

**Step 2: Run tests to verify they fail initially**

Run: `cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate && python -m pytest tests/unit/test_cli_document_helpers.py -v`

Expected: Tests should PASS (we already implemented the function in Task 1)

If tests pass: Great! Move to next step.

If tests fail: Fix the `_build_document_folder_map()` implementation to make tests pass.

**Step 3: Commit**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add tools/itglue-migrate/tests/unit/test_cli_document_helpers.py
git commit -m "test: add unit tests for _build_document_folder_map helper"
```

---

## Task 5: Run All Tests and Type Checking

**Files:**
- All project files

**Why:** Verify our changes don't break existing functionality and all quality checks pass.

**Step 1: Run all unit tests**

Run: `cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate && python -m pytest tests/unit/ -v`

Expected: All tests PASS

**Step 2: Run type checking**

Run: `cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate && pyright`

Expected: Zero errors or warnings

**Step 3: Run linting**

Run: `cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate && ruff check`

Expected: No issues

**Step 4: If any checks fail, fix issues and re-run**

Repeat steps 1-3 until all checks pass.

**Step 5: Commit if any fixes were needed**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add tools/itglue-migrate/
git commit -m "fix: resolve test and type checking issues"
```

---

## Task 6: Manual Testing with Real Data

**Files:**
- No code changes, testing only

**Why:** Automated tests can't catch all issues with filesystem scanning and HTML processing. Manual testing with real ITGlue export data is essential.

**Step 1: Create a test export structure**

In a temporary directory, create a mock ITGlue export:

```bash
mkdir -p /tmp/test-export/documents/servers
mkdir -p /tmp/test-export/attachments/documents/12345

# Create a document folder with nested path
mkdir -p "/tmp/test-export/documents/servers/DOC-1774800-8077468 Proofpoint go live template"

# Create an HTML file with an image reference
cat > "/tmp/test-export/documents/servers/DOC-1774800-8077468 Proofpoint go live template/document.html" << 'EOF'
<!DOCTYPE html>
<html>
<head><title>Proofpoint Configuration</title></head>
<body>
<h1>Proofpoint Setup</h1>
<p>This is the configuration document.</p>
<img src="1774800/docs/8077468/images/12345" alt="Diagram">
</body>
</html>
EOF

# Create a mock image file (1x1 transparent PNG)
mkdir -p "/tmp/test-export/documents/servers/DOC-1774800-8077468 Proofpoint go live template/1774800/docs/8077468/images"
echo -e "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\x0d\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82" > "/tmp/test-export/documents/servers/DOC-1774800-8077468 Proofpoint go live template/1774800/docs/8077468/images/12345"

# Create minimal CSV files
cat > /tmp/test-export/documents.csv << 'EOF'
id,name,organization_id,locator,content
8077468,Proofpoint go live template,Test Org,,
EOF

cat > /tmp/test-export/organizations.csv << 'EOF
id,name
1,Test Org
EOF
```

**Step 2: Run preview command to generate plan**

```bash
cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate
uv run itglue-migrate preview \
  --export-path /tmp/test-export \
  --api-url http://localhost:8000 \
  --token test-token \
  --output /tmp/plan.json
```

Expected: Plan generated successfully, shows 1 document

**Step 3: Run migration in dry-run mode**

```bash
cd /Users/jack/GitHub/gocovi-docs/tools/itglue-migrate
uv run itglue-migrate run \
  --plan /tmp/plan.json \
  --org "Test Org" \
  --dry-run \
  --verbose
```

Expected: Shows document would be created with path `/servers`

**Step 4: Clean up test data**

```bash
rm -rf /tmp/test-export /tmp/plan.json
```

**Step 5: Document test results**

Create a note with test results:

```
Manual Test Results:
- Folder path extraction: ✓ Correctly extracted /servers from nested DOC folder
- HTML content reading: ✓ Successfully read HTML from document.html
- Image processing: N/A (requires live API for upload)

Notes:
- The DOC prefix "DOC-1774800-8077468" was correctly stripped
- The actual folder name "Proofpoint go live template" was preserved in the folder map
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `docs/plans/MIGRATION_TOOL.md` (if it exists)
- Or create: `docs/plans/2026-01-14-document-migration-fixes-notes.md`

**Why:** Document the changes for future reference.

**Step 1: Create documentation of the fix**

Create `docs/plans/2026-01-14-document-migration-fixes-notes.md`:

```markdown
# Document Migration Fixes - 2026-01-14

## Problems Fixed

### 1. Empty Document Content
**Issue:** Documents were being created with empty content because the migration tool only used the CSV `content` field, which doesn't contain the actual HTML.

**Root Cause:** `cli.py:_migrate_documents()` was reading `doc.get("content", "")` from the CSV instead of reading the HTML file from the export.

**Fix:** Use `DocumentProcessor.process_document()` to:
- Find the HTML file in the export's `documents/` folder
- Read the HTML content
- Upload embedded images to BifrostDocs
- Replace image src URLs with the new BifrostDocs URLs
- Return the transformed HTML

### 2. Incorrect Folder Paths
**Issue:** Document folder paths contained the DOC prefix (e.g., "DOC-1774800-8077468") and missed the actual folder name.

**Root Cause:** `cli.py:_migrate_documents()` was using the CSV `locator` field instead of scanning the filesystem to extract the correct path.

**Fix:** Added `_build_document_folder_map()` helper function to:
- Scan the `documents/` export folder
- Match DOC folder names using regex: `DOC-{org_id}-{doc_id} {name}`
- Extract the document ID from the folder name
- Determine the folder path based on parent directory
- Return a mapping of `doc_id -> (folder_path, html_file_path)`

## Example

### Before Fix
```
Export structure:
documents/servers/DOC-1774800-8077468 Proofpoint go live template/document.html

Result:
- path: /Imported (from default) or empty locator field
- content: "" (empty string)
```

### After Fix
```
Export structure:
documents/servers/DOC-1774800-8077468 Proofpoint go live template/document.html

Result:
- path: /servers (extracted from filesystem)
- content: "<html>...</html>" (read from file, images uploaded, URLs replaced)
```

## Files Modified

1. `tools/itglue-migrate/src/itglue_migrate/cli.py`
   - Added `_build_document_folder_map()` function
   - Modified `_migrate_documents()` to use folder map and DocumentProcessor

2. `tools/itglue-migrate/tests/unit/test_cli_document_helpers.py`
   - Added unit tests for `_build_document_folder_map()`
```

**Step 2: Commit documentation**

```bash
cd /Users/jack/GitHub/gocovi-docs
git add docs/plans/2026-01-14-document-migration-fixes-notes.md
git commit -m "docs: document document migration fixes"
```

---

## Summary

This plan fixes two critical issues in the ITGlue document migration:

1. **Empty content**: Documents now have their actual HTML content with images uploaded
2. **Incorrect paths**: Folder paths are correctly extracted from the filesystem

The fix leverages existing code (`DocumentProcessor` and folder map pattern) that was already working in `importers.py` but wasn't being used by the CLI's `_migrate_documents()` function.

**Total estimated time:** 1-2 hours

**Risk level:** Low - changes are isolated to document migration only, existing code is being reused
