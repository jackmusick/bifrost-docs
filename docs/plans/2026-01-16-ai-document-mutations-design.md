# AI Document Mutations Design

**Date:** 2026-01-16
**Status:** Approved
**Author:** Claude (Brainstorming Session)

## Overview

Add AI-powered document and custom asset mutation capabilities to the existing chat system. Users can request content cleanup, updates, and drafting through conversational prompts. All mutations require user preview and confirmation before applying.

## Context

The existing chat system is a read-only RAG (Retrieval-Augmented Generation) system that:
- Answers questions using semantic search + LLM
- Supports OpenAI and Anthropic models
- Streams responses via WebSocket
- Maintains org-scoped context
- Uses client-managed conversation history (stateless server)

This design extends the chat to support **write operations** while preserving the existing architecture.

## Use Cases

1. **Format cleanup:** "Can you clean up this document?" → AI fixes formatting, applies structure
2. **Content updates:** "Change the IP address to 10.0.0.5" → AI updates specific fields/content
3. **Document drafting:** "Draft a user onboarding guide" → AI creates new structured document
4. **Conversational editing:** User provides feedback on previewed changes, AI iterates

## Design Principles

1. **Preview-then-commit:** All mutations show preview + summary before applying
2. **Permission-based:** Only Contributor+ roles can apply mutations
3. **Real-time updates:** If user is viewing the entity, see changes immediately
4. **Opinionated structure:** AI applies Diataxis framework to documents automatically
5. **Smart intent detection:** AI infers when to mutate vs answer using function/tool calling

## Architecture

### Mutation Flow

```
Current (Read-Only):
User message → Search/RAG → Stream answer → Done

New (With Mutations):
User message → Intent detection → Branch:
├─ Answer only: Search/RAG → Stream answer → Done
└─ Mutation: Search/RAG → Generate changes → Stream preview + TL;DR →
             Show "Apply Changes" button → User clicks →
             Update entity → Confirm with link
```

### New API Endpoint

**Endpoint:** `POST /api/search/chat/apply`

**Purpose:** Apply AI-generated changes after user reviews preview

**Request:**
```json
{
  "conversation_id": "uuid",
  "request_id": "uuid",
  "entity_type": "document" | "custom_asset",
  "entity_id": "uuid",
  "organization_id": "uuid",
  "changes": {
    "content": "updated markdown content",  // for documents
    "fields": {"field_name": "new_value"}  // for custom_assets
  }
}
```

**Response:**
```json
{
  "success": true,
  "entity_id": "uuid",
  "link": "entity://documents/{org_id}/{doc_id}"
}
```

**Permission Check:**
- User must have Contributor role or higher
- Entity must exist and belong to specified org
- Org must be enabled

### WebSocket Message Type

**Mutation Preview Message:**
```json
{
  "type": "mutation_preview",
  "data": {
    "entity_type": "document" | "custom_asset",
    "entity_id": "uuid",
    "organization_id": "uuid",
    "summary": "TL;DR of changes (2-3 sentences)",
    "preview": "Full content or field diff",
    "action_label": "Apply Changes"
  }
}
```

**Entity Update Notification:**
```json
{
  "type": "entity_update",
  "channel": "entity_update:{entity_type}:{entity_id}",
  "data": {
    "entity_id": "uuid",
    "entity_type": "document" | "custom_asset",
    "updated_by": "user_id"
  }
}
```

## Intent Detection & LLM Prompting

### System Prompt Addition

```
You are a documentation assistant with the ability to modify documents and assets.

When the user asks you to:
- Clean up, fix formatting, improve, or rewrite content
- Update, change, or modify specific information
- Make corrections or adjustments

You should use the `modify_entity` tool to generate the updated content.

For DOCUMENTS:
Always apply the Diataxis framework when modifying:
- Tutorial: Learning-oriented, step-by-step for beginners
- How-to: Task-oriented, solve a specific problem
- Reference: Information-oriented, technical descriptions
- Explanation: Understanding-oriented, clarify concepts

Infer the document type from content, title, and user context. If ambiguous, ask.

For CUSTOM ASSETS:
These are structured data with fields. Update only the specific fields
requested, preserving all other data.
```

### Tool Definition

**Function/Tool Name:** `modify_entity`

**Parameters:**
```json
{
  "entity_type": "document | custom_asset",
  "entity_id": "uuid",
  "organization_id": "uuid",
  "intent": "cleanup | update | draft",
  "changes_summary": "Brief description of changes",
  "content": "Full updated markdown content (for documents)",
  "field_updates": {"field_name": "new_value"}  // for custom_assets
}
```

**Execution Flow:**
1. LLM detects mutation intent, calls `modify_entity` function
2. Backend generates full content/changes using second LLM call with Diataxis guidance
3. Stream `mutation_preview` message to client
4. Client renders preview with "Apply Changes" button

### Handling Ambiguity

If document type is unclear, AI responds conversationally:
```
"I can help clean this up! However, I'm not sure if this should be
structured as a tutorial (step-by-step learning) or a how-to guide
(solving a specific problem). Which would you prefer?"
```

Only after clarification does it call `modify_entity`.

## Frontend Preview Rendering

### Document Preview

```
┌─────────────────────────────────────┐
│ 🤖 Assistant                        │
│                                     │
│ **Changes Summary:**                │
│ Restructured as a how-to guide,     │
│ fixed numbered list formatting,     │
│ clarified steps 2-3.                │
│                                     │
│ **Preview:**                        │
│ ┌─────────────────────────────────┐ │
│ │ [Markdown rendered preview]     │ │
│ │ (scrollable if long)            │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Apply Changes] [View Diff]         │
└─────────────────────────────────────┘
```

### Custom Asset Preview

```
┌─────────────────────────────────────┐
│ 🤖 Assistant                        │
│                                     │
│ **Changes Summary:**                │
│ Updated IP address and location.    │
│                                     │
│ **Field Changes:**                  │
│ ┌─────────────────────────────────┐ │
│ │ Field      │ Old → New          │ │
│ │────────────┼────────────────────│ │
│ │ IP Address │ 10.0.0.1 → 10.0.0.5│ │
│ │ Location   │ DC1 → DC2          │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Apply Changes]                     │
└─────────────────────────────────────┘
```

## Apply Changes Flow

1. **Permission Check (Client-side):**
   - User must have Contributor+ role
   - Button disabled if Reader role, tooltip: "You don't have permission to edit this"

2. **User clicks "Apply Changes":**
   - POST to `/api/search/chat/apply` with changes

3. **Backend validates:**
   - User has write permission (Contributor+ role)
   - Entity exists and belongs to org
   - Content/fields are valid

4. **Apply changes:**
   - Update `document.content` or custom asset fields
   - Set `updated_by_user_id` to current user
   - Update `updated_at` timestamp

5. **Broadcast real-time update:**
   - Publish WebSocket: `entity_update:{entity_type}:{entity_id}`
   - Frontend refreshes entity if viewing it

6. **Return success with link:**
   ```json
   {
     "success": true,
     "entity_id": "uuid",
     "link": "entity://documents/{org_id}/{doc_id}"
   }
   ```

7. **Frontend:**
   - Replace "Apply Changes" with ✓ "Applied" + clickable link
   - User navigates to updated entity

## Error Handling

### Permission Validation

```python
# Check user role
if user.role == "Reader":
    raise ForbiddenError("Readers cannot modify entities")

# Check entity exists and belongs to org
if entity_type == "document":
    doc = await document_repo.get_by_id(entity_id)
    if not doc or doc.organization_id != organization_id:
        raise NotFoundError("Document not found")
```

### Edge Cases

1. **Concurrent Edits:**
   - Check `updated_at` timestamp matches expected
   - Reject if changed: "Document modified by someone else. Refresh and try again."

2. **Invalid LLM Output:**
   - Validate content before streaming preview
   - Documents: Valid UTF-8, reasonable length
   - Assets: Field types match schema

3. **Entity Deleted:**
   - Return 404 from `/apply`
   - Frontend: "This document no longer exists"

4. **Organization Disabled:**
   - Check `org.is_enabled` in `/apply`
   - Error: "This organization is no longer active"

5. **API Key Expired:**
   - Handled by existing LLM error handling
   - Stream error message to chat

## Component Implementation

### Backend (Python FastAPI)

**New Files:**
- `/api/src/services/document_mutations.py` - Document modification with Diataxis
- `/api/src/services/asset_mutations.py` - Custom asset field updates
- `/api/src/models/contracts/mutations.py` - Request/response schemas

**Modified Files:**
- `/api/src/services/ai_chat.py` - Add tool definitions, detect mutation intent
- `/api/src/routers/search.py` - Add `POST /api/search/chat/apply`
- `/api/src/routers/websocket.py` - Add `entity_update` message type

### Frontend (TypeScript/React)

**New Files:**
- `/client/src/components/chat/MutationPreview.tsx` - Preview + Apply button
- `/client/src/components/chat/DocumentPreview.tsx` - Markdown preview
- `/client/src/components/chat/AssetFieldDiff.tsx` - Table view for assets
- `/client/src/hooks/useMutationApply.ts` - Apply logic, permission checks

**Modified Files:**
- `/client/src/hooks/useChat.ts` - Handle `mutation_preview` message
- `/client/src/components/chat/ChatWindow.tsx` - Render mutation previews

## Service Layer Design

### Document Mutations Service

```python
class DocumentMutationService:
    def __init__(self, llm_client, document_repo):
        self.llm = llm_client
        self.repo = document_repo

    async def generate_cleaned_content(
        self,
        original_content: str,
        document_name: str,
        user_instruction: str
    ) -> tuple[str, str]:
        """
        Apply Diataxis framework + user instructions

        Returns:
            (new_content, summary_of_changes)
        """
        # 1. Infer document type from content/name/instruction
        # 2. Structure according to Diataxis
        # 3. Apply user's requested changes
        # 4. Return (new_content, summary)
```

### Asset Mutations Service

```python
class AssetMutationService:
    async def generate_field_updates(
        self,
        asset_type: str,
        current_fields: dict,
        user_instruction: str
    ) -> tuple[dict, str]:
        """
        Generate field updates based on instruction

        Returns:
            (field_updates, summary_of_changes)
            Only changed fields are included
        """
```

## Testing Strategy

### Backend Unit Tests

```
/api/tests/services/test_document_mutations.py
- Diataxis classification accuracy
- Content transformation preserves info
- Summary generation

/api/tests/services/test_asset_mutations.py
- Field update extraction
- Field validation

/api/tests/routers/test_search_mutations.py
- /chat/apply with permissions
- Reader role rejection
- Contributor role success
- Concurrent edit detection
```

### Integration Tests

```
/api/tests/integration/test_mutation_flow.py
- Full flow: chat → preview → apply
- WebSocket streaming
- Real-time entity updates
```

### Frontend Tests

```
/client/src/components/chat/__tests__/MutationPreview.test.tsx
- Document preview rendering
- Asset field diff rendering
- Apply button calls correct endpoint
- Permission-based button state
```

## Observability

### Logging

```python
logger.info("Mutation detected", extra={
    "user_id": user.id,
    "entity_type": entity_type,
    "entity_id": entity_id,
    "intent": intent,
    "org_id": org_id
})

logger.info("Mutation applied", extra={
    "user_id": user.id,
    "entity_id": entity_id,
    "changes_summary": summary
})

logger.info("Mutation tokens used", extra={
    "user_id": user.id,
    "org_id": org_id,
    "tokens": {
        "prompt": 1500,
        "completion": 800,
        "total": 2300
    },
    "model": "gpt-4o-mini"
})
```

### Metrics to Track

- **Mutation requests** per user/org
- **Apply rate:** Previews shown vs applied (measures suggestion quality)
- **Token usage** per user (cost tracking, rate limiting)
- **Error rates** by type:
  - Permission denied
  - Validation failed
  - Entity not found
  - LLM errors

## Initial Scope (MVP)

**Included:**
- Document cleanup (formatting + Diataxis restructuring)
- Document updates (content modifications)
- Custom asset field updates
- Preview + apply workflow
- Permission checks (Contributor+ only)
- Real-time entity updates

**Excluded (Future):**
- Batch operations (multiple docs at once)
- Version history / rollback
- Collaborative editing (multiple users on same preview)
- Feature flags / gradual rollout (ship to all users)

## Success Criteria

1. Users can clean up imported IT Glue documents via chat
2. Apply rate > 60% (users accept majority of AI suggestions)
3. Zero permission bypass bugs
4. < 5% error rate on mutations
5. Real-time updates work when viewing entity

## Diataxis Framework Reference

**Tutorial:** Learning-oriented, step-by-step lesson for beginners
**How-to Guide:** Task-oriented, practical steps to solve specific problem
**Reference:** Information-oriented, technical descriptions
**Explanation:** Understanding-oriented, clarification of concepts

AI infers type from content, title, and user prompt. Asks if ambiguous.
