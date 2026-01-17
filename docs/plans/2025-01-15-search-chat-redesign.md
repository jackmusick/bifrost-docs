# Search & Chat Redesign

## Overview

Split the current search experience into two distinct interfaces:

| Interface | Trigger | Purpose |
|-----------|---------|---------|
| Search Modal | CMD+K | Quick lookup - find docs fast |
| Chat Window | Chat icon, or Shift+Enter from search | Deep exploration - synthesize info, ask follow-ups |

**The bridge:** Shift+Enter in search closes the modal, opens chat, pre-fills the query, and auto-sends it.

**Scope behavior (both interfaces):** Contextual with toggle. If on an org page, defaults to that org. Can broaden to global.

---

## Search Modal

### Layout

```
┌────────────────────────────────────────────┐
│ 🔍 [Search input]            [Scope toggle]│
├────────────────────────────────────────────┤
│ Results list (~40% height, scrolls)        │
│ ┌────────────────────────────────────────┐ │
│ │ 📄 Acme Onboarding Guide        [Doc]  │ │ ← selected
│ │ 🔑 Acme Admin Credentials      [Pass]  │ │
│ │ 📄 Generic Onboarding Checklist [Doc]  │ │
│ └────────────────────────────────────────┘ │
├────────────────────────────────────────────┤
│ Preview pane (~60% height, scrolls)        │
│ ┌────────────────────────────────────────┐ │
│ │ # Acme Onboarding Guide                │ │
│ │                                        │ │
│ │ This document covers the standard      │ │
│ │ onboarding process for new users...    │ │
│ │                                        │ │
│ │ ## Step 1: Create AD Account           │ │
│ │ [highlighted match here]               │ │
│ └────────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

### Behavior

- Results update on debounce (300ms) as you type
- Preview updates instantly on hover or arrow key navigation
- Enter navigates to the selected result
- Shift+Enter hands off to chat
- Preview renders full document with rich formatting (markdown)
- Search match highlighted and scrolled-to in preview

### Changes from Current

- **Removed:** AI panel on the right (chat handles this now)
- **Added:** Rich preview pane showing full document content
- **Fixed:** Preview uses proper markdown rendering (not raw HTML)

---

## Chat Interface

### Appearance

Floating window - draggable and resizable. Can position anywhere on screen.

### Layout

```
┌─────────────────────────────────────────┐
│ 💬 Chat          [Scope: Acme ▾]    [✕] │  ← header with scope toggle
├─────────────────────────────────────────┤
│                                         │
│  You: Do we have documentation on       │
│  onboarding users?                      │
│                                         │
│  AI: Yes, you have several onboarding   │
│  documents. For Acme Corp specifically, │
│  see the [Acme Onboarding Guide] which  │
│  covers AD account creation and M365    │
│  provisioning.                          │
│                                         │
│  For general procedures, check the      │
│  [Standard User Onboarding Checklist].  │
│                                         │
│  Are you looking for a specific client? │
│                                         │
│  You: Yeah, what about Contoso?         │
│                                         │
│  AI: For Contoso, their process is...   │
│                                         │
├─────────────────────────────────────────┤
│ [Type a message...]            [Send ➤] │
└─────────────────────────────────────────┘
```

### Behavior

- **Session-only persistence:** Closing the window clears the conversation. No database storage.
- **Backend context:** Backend maintains conversation history for follow-ups during the session.
- **Inline links:** Document references render as clickable links (e.g., `[Acme Onboarding Guide]`) that navigate to that entity.
- **Streaming:** Response streams in real-time (same as current AI).
- **Conversational:** AI can ask clarifying questions, user can refine and dig deeper.

### Entry Points

1. **Chat icon in header** - Always available, opens empty chat
2. **Shift+Enter from search** - Closes search, opens chat, pre-fills query, auto-sends

---

## Implementation Notes

### Link Format for AI

Backend should provide entity references in a consistent format:
- Format: `[Title](entity://type/uuid)` (e.g., `[Acme Onboarding](entity://documents/abc-123)`)
- Frontend parses these and routes to the correct detail page
- Prevents broken URL fragments or raw URLs in responses

### Preview Rendering

Use the same markdown renderer as document detail pages for consistency.

### Chat Window Defaults

- Default size: ~400x500px
- Remember last size/position for the session
- Min size constraints to keep it usable

### Keyboard Shortcut Hints

- Search input placeholder or footer: "Shift+Enter to ask AI"
- Chat window: Standard send (Enter or click)

---

## Issues Addressed

| Original Issue | Solution |
|----------------|----------|
| AI sidebar too small for generated docs | Chat is now a separate floating window |
| Shift+Enter doesn't resend results | Shift+Enter opens chat with query |
| No sources shown | Inline links in chat responses |
| Broken URL fragments in AI responses | Consistent entity link format |
| Preview doesn't handle HTML properly | Rich markdown preview pane |
