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
