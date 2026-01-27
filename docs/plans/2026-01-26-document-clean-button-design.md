# Document Clean Button Design

## Overview

Add a "Clean" button to the document detail page that triggers AI-powered document cleaning directly, without going through the chat interface.

## User Experience

### Button Placement
- New "Clean" button in document header, between Enable/Disable toggle and Edit button
- Uses Sparkles icon to indicate AI-powered action
- Only visible when:
  - User has edit permissions (`canEdit`)
  - Document exists (not creating new document)
  - Not currently in edit mode

### Flow
1. User clicks "Clean" button
2. Button shows loading state ("Cleaning...")
3. Backend returns cleaned content + summary of changes
4. Document enters edit mode with cleaned content pre-populated
5. Toast shows summary: "Document cleaned: Restructured as a How-To guide, improved headings..."
6. User reviews changes in the editor, can tweak if needed
7. User clicks "Save" to persist, or "Cancel" to discard

### Error Handling
- If cleaning fails, show error toast and stay in view mode
- Button disabled during cleaning operation

## Backend Implementation

### New Endpoint

`POST /api/organizations/{org_id}/documents/{document_id}/clean`

**Request:** Empty body

**Response:**
```json
{
  "cleaned_content": "# Getting Started\n\n...",
  "summary": "Restructured as Tutorial, added step-by-step headings, improved clarity",
  "suggested_name": "Getting Started with Authentication"
}
```

### Implementation Details
- Add route in `api/src/routers/documents.py`
- Calls existing `DocumentMutationService.generate_cleaned_content()`
- Requires Contributor+ permission (same as document edit)
- Returns 404 if document not found
- Returns 500 if LLM cleaning fails

### Title Suggestion
The LLM returns structured JSON with both cleaned content and a suggested title:
- `suggested_name` is optional (null if LLM doesn't return valid JSON)
- Frontend uses suggested name when entering edit mode, falling back to current name
- User can accept, modify, or reject the suggestion before saving

### Why New Endpoint vs Chat
- Simpler - no WebSocket, no chat session overhead
- Direct request/response fits the button UX better
- Reuses the same underlying `generate_cleaned_content()` logic

## Frontend Implementation

### File Changes

**`client/src/hooks/useDocuments.ts`**
- Add `useCleanDocument(orgId, documentId)` mutation hook
- Calls the new clean endpoint
- Returns `{ cleaned_content, summary }`

**`client/src/pages/documents/DocumentDetailPage.tsx`**
- Add `isCleaning` state for loading indicator
- Add `handleClean()` handler:
  - Calls clean mutation
  - On success: enters edit mode with cleaned content, shows toast with summary
  - On error: shows error toast
- Add Clean button in header (with Sparkles icon)

### No New Components
Reuses existing:
- Edit mode state management
- Toast notifications (sonner)
- Button component with loading state

## Files to Modify

| File | Changes |
|------|---------|
| `api/src/services/document_mutations.py` | Return JSON with content + suggested title |
| `api/src/routers/documents.py` | Add `/clean` endpoint with `suggested_name` response |
| `client/src/hooks/useDocuments.ts` | Add `useCleanDocument` hook |
| `client/src/pages/documents/DocumentDetailPage.tsx` | Add Clean button and handler, use suggested name |
