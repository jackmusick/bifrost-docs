# Manual Testing Guide: AI Document Mutations

## Prerequisites
- Running development environment (API + Client)
- Test user with Contributor role
- Sample documents with poor formatting (e.g., from IT Glue import)

## Test Cases

### 1. Document Cleanup (Diataxis)
**Objective:** Verify AI applies Diataxis framework when cleaning documents

**Steps:**
1. Navigate to a poorly formatted document (e.g., "Renaming Systems")
2. Open chat interface
3. Send message: "Can you clean up this document?"
4. Verify:
   - AI detects mutation intent
   - Preview shows structured content (with how-to sections)
   - Summary explains changes
   - "Apply Changes" button appears
5. Click "Apply Changes"
6. Verify:
   - Document updates immediately if viewing
   - Success message with link appears
   - Document content is cleaned and structured

**Expected Diataxis Structure:**
- How-to: Prerequisites → Steps → Verification
- Tutorial: Learning Objectives → Guide → Summary
- Reference: Overview → Sections → See Also
- Explanation: Introduction → How It Works → Why It Matters

### 2. Custom Asset Field Update
**Objective:** Verify AI updates custom asset fields

**Steps:**
1. Navigate to a custom asset (e.g., Server)
2. Open chat
3. Send: "Update the IP address to 10.0.0.100"
4. Verify:
   - Preview shows table with field changes
   - Old → New values displayed correctly
5. Apply changes
6. Verify asset fields updated

### 3. Permission Check (Reader Role)
**Objective:** Verify Reader role cannot apply mutations

**Steps:**
1. Login as Reader user
2. Open chat
3. Request document cleanup
4. Verify:
   - Preview may still show
   - "Apply Changes" button is disabled OR
   - Apply returns 403 Forbidden error

### 4. Ambiguous Document Type
**Objective:** Verify AI asks for clarification when type is unclear

**Steps:**
1. Create document with ambiguous content
2. Request cleanup
3. Verify AI asks: "Should this be a tutorial or how-to?"
4. Respond with choice
5. Verify appropriate structure applied

### 5. Real-time Updates
**Objective:** Verify WebSocket updates when viewing entity

**Steps:**
1. Open document in one tab
2. Open chat in another tab (or split view)
3. Apply mutation via chat
4. Verify document view refreshes automatically

## Regression Testing
- [ ] Existing chat functionality still works (Q&A, search)
- [ ] Links in responses still work
- [ ] Citations appear correctly
- [ ] Non-mutation chats don't trigger previews

## Performance
- [ ] Mutation preview appears within 3 seconds
- [ ] Apply completes within 1 second
- [ ] Real-time update appears immediately
