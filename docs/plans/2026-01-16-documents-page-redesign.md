# Documents Page Redesign

## Overview

Redesign the documents page to provide a more integrated, documentation-focused experience inspired by Notion and Starlight. The goal is to move away from a file-manager aesthetic toward a curated knowledge base feel.

## Key Changes

### 1. Sidebar Navigation Model

Replace the current folder tree with a section-based hierarchy:

| Level | Display | Behavior |
|-------|---------|----------|
| L1 | **Section** (bold) | Collapsible, top-level paths |
| L2 | Subsection (indented once) | Collapsible, second-level paths |
| L3+ | Flattened with `·` separator | Group label, documents listed underneath |

**Example:**
```
Archive                                    ← L1 Section (bold, collapsible)
  Tech                                     ← L2 Subsection (indented, collapsible)
    Overview doc                           ← Document directly under Tech
    Microsoft · Office 365 · Teams         ← L3+ flattened as group label
      Setting up Teams channels            ← Document
      Teams guest access policy            ← Document
    Microsoft · Office 365 · Word          ← Another flattened group
      Document templates guide             ← Document
  HR                                       ← L2 Subsection
    Onboarding                             ← L3+ (single level, just shows name)
      New hire checklist                   ← Document
```

**Key decisions:**
- No "Root" label - top-level documents go into explicit sections
- Sections emerge from document paths (no empty sections)
- Visual depth caps at 2 levels; deeper paths flatten into `·`-separated labels
- Documents appear directly under their section/subsection/flattened group

### 2. Sidebar Visual Style

**Current:** FolderTree wrapped in a Card with 256px fixed width

**New:**
- Flush sidebar (no card wrapper)
- Filter input at top of sidebar for quick filtering
- Thin vertical divider (`border-r`) separating sidebar from content
- Collapsible via button near org switcher

### 3. Document Detail Page Layout

**Current:** Single content area with cards for related items/attachments

**New:** Two-column layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Nav Sidebar]   │  [Document Content]    │  [Right Rail]   │
│                  │                        │                 │
│  (collapsible)   │  Title                 │  On this page   │
│                  │  ─────────────────     │    Overview     │
│                  │  Content paragraph...  │    Setup        │
│                  │                        │    Config       │
│                  │  ## Setup              │  ────────────── │
│                  │  More content...       │  Related        │
│                  │                        │    Doc A        │
│                  │                        │    Doc B        │
│                  │                        │  ────────────── │
│                  │                        │  Attachments    │
│                  │                        │    file.pdf     │
└─────────────────────────────────────────────────────────────┘
```

**Content column:**
- Centered with readable max-width (e.g., 720px)
- No border/shadow container
- Title at top, content below

**Right rail:**
- "On this page" table of contents (parsed from HTML headings)
- Related items
- Attachments
- Separated by subtle horizontal dividers (`border-b`), no cards
- Thin vertical divider (`border-l`) from content

**Table of contents:**
- Parse `<h1>`, `<h2>`, `<h3>` from document HTML content
- Add `id` attributes to headings at render time
- Clicking a ToC item smooth-scrolls to that heading

### 4. Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| Desktop | Three columns: nav sidebar, content, right rail |
| Tablet | Nav sidebar collapses (hamburger/icon), content + right rail visible |
| Mobile | Both sidebars become dropdowns at top (Starlight pattern), full-width content |

**Mobile dropdown pattern:**
- "On this page" dropdown shows ToC
- Navigation dropdown shows section tree
- Content takes full width below

### 5. Document/Section Management

#### Creating Documents

- `+` button appears on hover next to section headers
- Opens "New Document" modal with section pre-selected
- Global `+` in header for creating docs without pre-selected section

#### Section Selection UX

Cascading combobox/breadcrumb picker instead of typing paths:

```
Section:    [Archive      ▾] / [Tech        ▾] / [+ New subsection...]
```

- Each level is a dropdown showing existing options
- Last option is always "+ New..." for creating new subsections
- Can stop at any level (document goes in that section)
- Visual shows full path as you build it

#### Moving Documents

- Drag and drop in sidebar
- Restricted to dragging documents (not sections, for now)
- Drop on section/subsection updates document path

#### Renaming Sections

- Right-click or `...` menu on section → "Rename"
- Confirmation: "Rename 'Tech' to 'Engineering'? This will update 23 documents."
- If target section exists: "This section already exists. Would you like to merge?"
- Validates uniqueness constraints (org_id + path + name) before merge

#### Deleting Sections

- Warning: "This will delete X documents" or require moving documents first

### 6. Edit Mode

- Same two-column layout
- Content area becomes editable via TipTap (inline editing)
- Right rail stays visible (ToC can update live as headings are added)
- TipTap toolbar appears at top of content area
- No separate "edit page" - toggle between view and edit states

## Data Model Considerations

### Path-Based Sections

Sections continue to be derived from document paths. No new `Section` entity required.

**Changes needed:**
- Add `order` field to documents (or derive from position) for manual ordering within sections
- Potentially add section metadata (icon, description) as a separate lightweight store if needed later

### Batch Path Updates

Renaming/merging sections requires:
1. Find all documents with paths starting with old prefix
2. Update paths to new prefix
3. Validate no uniqueness conflicts
4. Execute in single transaction

## Components to Create/Modify

### New Components

| Component | Purpose |
|-----------|---------|
| `DocumentSidebar` | New section-based navigation tree |
| `SectionItem` | Collapsible section with documents |
| `FlattenedGroupLabel` | Renders `·`-separated deep paths |
| `DocumentRightRail` | ToC + Related + Attachments |
| `TableOfContents` | Parses HTML headings, renders linked list |
| `SectionPicker` | Cascading combobox for section selection |
| `MobileDocNav` | Dropdown navigation for mobile |

### Modified Components

| Component | Changes |
|-----------|---------|
| `DocumentsPage` | Remove Card wrapper, integrate new sidebar |
| `DocumentDetailPage` | Two-column layout, remove card wrappers |
| `Sidebar` | Add collapse button |
| `TiptapEditor` | Add `id` attributes to headings |

## Migration

Existing documents with deep folder structures will automatically display with the flattened `·` pattern. No data migration required.

## Out of Scope (For Now)

- Section reordering (manual ordering of L1/L2 sections)
- Empty sections (sections without documents)
- Section icons/descriptions
- Full-text search (keeping filter-only for sidebar)

## Open Questions

None - design validated through brainstorming session.
