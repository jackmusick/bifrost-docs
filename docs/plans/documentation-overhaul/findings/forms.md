# Forms - Codebase Review Findings

## Source of Truth

This document captures the current state of Forms in the Bifrost platform based on codebase analysis conducted on 2026-01-20.

---

## 1. Overview

Forms are virtual entities stored exclusively in the PostgreSQL database (not on S3/filesystem). They provide a user-friendly interface for executing workflows by:

- Collecting user input with validation
- Displaying dynamic dropdown options via data providers
- Supporting conditional field visibility via JavaScript expressions
- Supporting launch/startup workflows that pre-populate form context
- Handling file uploads with presigned S3 URLs
- Executing linked workflows on submission

### Key Architecture Points

- **Database-only storage**: Forms are stored in the `forms` and `form_fields` tables. No filesystem representation.
- **Virtualized for git sync**: Serialized to JSON on-the-fly during git sync operations.
- **Soft delete**: Forms are deactivated (`is_active=false`) rather than hard deleted.
- **Role-based or authenticated access**: Two access control levels.

---

## 2. Form Field Types

The codebase defines **12 field types** in `api/src/models/enums.py`:

| Type | Description | Special Properties |
|------|-------------|-------------------|
| `text` | Single-line text input | standard |
| `email` | Email with validation | standard |
| `number` | Integer or decimal | `validation.min`, `validation.max` |
| `select` | Single choice dropdown | `options` or `data_provider_id` |
| `checkbox` | Boolean true/false | standard |
| `textarea` | Multi-line text | standard |
| `radio` | Radio button group | `options` |
| `date` | Date picker | standard |
| `datetime` | Date and time picker | standard |
| `markdown` | Rendered markdown content | `content` (display only, no input) |
| `html` | JSX template or static HTML | `content` (display only, no input) |
| `file` | File upload | `allowed_types`, `multiple`, `max_size_mb` |

**Note**: `markdown` and `html` types are display-only components that don't collect user input. They require `content` field instead of `label`.

---

## 3. Data Provider Integration

### Input Modes for Data Providers

Data providers can receive inputs from three sources, configured via `data_provider_inputs`:

| Mode | Description | Required Field |
|------|-------------|---------------|
| `static` | Hard-coded value | `value` |
| `fieldRef` | Value from another form field | `field_name` |
| `expression` | JavaScript expression | `expression` |

**Example configuration**:
```json
{
  "department": {
    "mode": "fieldRef",
    "field_name": "department_select"
  },
  "region": {
    "mode": "static",
    "value": "west_coast"
  }
}
```

### Cascading Behavior

When a field's value changes:
1. Dependent data provider fields detect the change
2. Clear existing options
3. Re-fetch with new input values
4. Update dropdown options

---

## 4. Visibility Expressions

Fields support conditional visibility via `visibility_expression`:

- JavaScript expression evaluated in browser
- Access to `context.field.*`, `context.workflow.*`, `context.query.*`
- Field appears when expression evaluates to truthy value

**Examples**:
```javascript
// Show if checkbox is checked
context.field.is_manager === true

// Show for specific role from launch workflow
context.workflow.is_admin === true

// Combine multiple conditions
context.field.department === "engineering" && context.workflow.can_approve === true
```

---

## 5. Launch/Startup Workflows

Forms support a `launch_workflow_id` that executes when the form loads:

### Purpose
- Pre-populate form context before display
- Check user permissions
- Load dynamic defaults
- Fetch organization-specific data

### Flow
1. User navigates to form
2. Form calls `POST /api/forms/{form_id}/startup`
3. Launch workflow executes
4. Results stored in `context.workflow`
5. Form renders with data available for visibility/HTML templates
6. On submit, `startup_data` passed to main workflow via `context.startup`

### API Endpoint
```
POST /api/forms/{form_id}/startup
Body: { ... input parameters ... }
Response: { result: { ... workflow output ... } }
```

---

## 6. File Upload Handling

### Endpoint
```
POST /api/forms/{form_id}/upload
```

### Flow
1. Client requests presigned URL with file metadata
2. Server validates file type/size against field constraints
3. Server returns presigned S3 URL
4. Client uploads directly to S3
5. S3 path stored as field value

### File Storage Path
```
uploads/{form_id}/{uuid}/{sanitized_filename}
```

### Field Properties
- `allowed_types`: Array of MIME types or extensions (e.g., `["application/pdf", "image/*", ".docx"]`)
- `multiple`: Boolean for multiple file uploads
- `max_size_mb`: Maximum file size in MB

### Returned to Workflow (single file)
```json
{
  "name": "document.pdf",
  "content_type": "application/pdf",
  "size": 1024000,
  "path": "uploads/form-id/uuid/document.pdf"
}
```

---

## 7. Access Control

### Access Levels

| Level | Description |
|-------|-------------|
| `authenticated` | Any logged-in user with org access |
| `role_based` | User must have assigned role via `form_roles` table |

### Organization Scoping
- Forms can be global (`organization_id = NULL`) or org-specific
- Org users see: their org's forms + global forms
- Platform admins see all forms

### Form-Role Association
- `form_roles` table links forms to roles
- When form is created/updated, roles are synced to referenced workflows

---

## 8. API Endpoints

| Endpoint | Method | Description | Access |
|----------|--------|-------------|--------|
| `GET /api/forms` | GET | List forms (with org filtering) | User |
| `POST /api/forms` | POST | Create form | Platform admin |
| `GET /api/forms/{form_id}` | GET | Get form by ID | User (with access) |
| `PATCH /api/forms/{form_id}` | PATCH | Update form | Platform admin |
| `DELETE /api/forms/{form_id}` | DELETE | Soft delete form | Platform admin |
| `POST /api/forms/{form_id}/execute` | POST | Execute form workflow | User (with access) |
| `POST /api/forms/{form_id}/startup` | POST | Execute launch workflow | User (with access) |
| `POST /api/forms/{form_id}/upload` | POST | Generate upload URL | User (with access) |

---

## 9. Form Schema Structure

```python
class FormSchema(BaseModel):
    fields: list[FormField]  # Max 50 fields per form

class FormField(BaseModel):
    name: str                           # Parameter name for workflow
    label: str | None                   # Display label (not required for markdown/html)
    type: FormFieldType                 # One of 12 types
    required: bool = False
    validation: dict | None             # pattern, min, max, message
    data_provider_id: UUID | None       # For dynamic options
    data_provider_inputs: dict | None   # Input configuration
    default_value: Any | None
    placeholder: str | None
    help_text: str | None
    visibility_expression: str | None   # JavaScript expression
    options: list[dict] | None          # For radio/select static options
    allowed_types: list[str] | None     # For file fields
    multiple: bool | None               # For file fields
    max_size_mb: int | None             # For file fields
    content: str | None                 # For markdown/html fields
    allow_as_query_param: bool | None   # Enable URL query parameter
```

---

## 10. File Paths Summary

### Backend

| Path | Description |
|------|-------------|
| `/Users/jack/GitHub/bifrost/api/src/models/contracts/forms.py` | Pydantic models |
| `/Users/jack/GitHub/bifrost/api/src/models/orm/forms.py` | SQLAlchemy ORM models |
| `/Users/jack/GitHub/bifrost/api/src/models/enums.py` | FormFieldType, FormAccessLevel enums |
| `/Users/jack/GitHub/bifrost/api/src/routers/forms.py` | API endpoints |
| `/Users/jack/GitHub/bifrost/api/src/repositories/forms.py` | Database repository |
| `/Users/jack/GitHub/bifrost/api/bifrost/forms.py` | SDK forms module |

### Frontend

| Path | Description |
|------|-------------|
| `/Users/jack/GitHub/bifrost/client/src/pages/FormBuilder.tsx` | Form builder page |
| `/Users/jack/GitHub/bifrost/client/src/pages/Forms.tsx` | Forms list page |
| `/Users/jack/GitHub/bifrost/client/src/pages/RunForm.tsx` | Form execution page |
| `/Users/jack/GitHub/bifrost/client/src/components/forms/FormRenderer.tsx` | Form rendering component |
| `/Users/jack/GitHub/bifrost/client/src/contexts/FormContext.tsx` | Form context provider |
| `/Users/jack/GitHub/bifrost/client/src/hooks/useForms.ts` | Forms React hooks |
| `/Users/jack/GitHub/bifrost/client/src/hooks/useFormFileUpload.ts` | File upload hook |

---

## Documentation State

### Existing Documentation Files

| File Path | Topics Covered |
|-----------|---------------|
| `src/content/docs/core-concepts/forms.mdx` | Overview, field types (partial), data providers, visibility rules, security basics |
| `src/content/docs/getting-started/creating-forms.mdx` | Basic form creation tutorial |
| `src/content/docs/troubleshooting/forms.md` | Common issues and solutions |
| `src/content/docs/how-to-guides/forms/creating-forms.mdx` | Form builder guide, unique features overview |
| `src/content/docs/how-to-guides/forms/cascading-dropdowns.mdx` | Cascading dropdown patterns |
| `src/content/docs/how-to-guides/forms/visibility-rules.mdx` | Permission-based visibility |
| `src/content/docs/how-to-guides/forms/html-content.mdx` | HTML/JSX templates |
| `src/content/docs/how-to-guides/forms/startup-workflows.mdx` | Launch workflows |
| `src/content/docs/how-to-guides/forms/context-field-references.mdx` | Context object reference |

### Gaps Identified

#### 1. Field Types - Incomplete Documentation
**Issue**: The core-concepts/forms.mdx lists 9 field types but the codebase has 12.

**Missing Types**:
- `datetime` - Date and time picker
- `markdown` - Display-only markdown content
- `html` - Display-only JSX templates

**Note**: `Multi-select` is mentioned in docs but doesn't exist in the codebase. The `select` type doesn't appear to support multiple selections.

**Recommended Action**: Update core-concepts/forms.mdx to list all 12 field types accurately with their specific properties.

#### 2. Form Virtualization Architecture
**Issue**: No documentation explains that forms are database-only entities, not stored on filesystem.

**Impact**: Developers may be confused about where forms are stored and how git sync works.

**Recommended Action**: Add architecture section explaining:
- Forms stored only in PostgreSQL (`forms` and `form_fields` tables)
- No S3/filesystem storage
- Serialized to JSON on-the-fly for git sync
- Implications for backup and migration

#### 3. Data Provider Input Modes - Incomplete
**Issue**: The `expression` mode for data provider inputs is mentioned in cascading-dropdowns.mdx but lacks detailed documentation.

**Missing Details**:
- Full syntax reference for expressions
- Available context variables
- Example expressions with complex logic
- Error handling for invalid expressions

**Recommended Action**: Add dedicated section on data provider expression mode with examples.

#### 4. File Upload - Incomplete Documentation
**Issue**: File upload is mentioned in how-to-guides/forms/creating-forms.mdx but lacks detailed coverage.

**Missing Details**:
- How presigned URLs work
- File size and type validation flow
- Multiple file upload handling
- How to access uploaded files in workflows (SDK pattern)
- File storage path structure
- Upload error handling

**Recommended Action**: Create dedicated file upload guide or expand existing documentation.

#### 5. Access Control - Needs Expansion
**Issue**: Security section in core-concepts/forms.mdx is brief and lacks implementation details.

**Missing Details**:
- How form-role assignments work
- API for assigning roles to forms
- How access is evaluated at runtime
- Integration with workflow role sync

**Recommended Action**: Expand access control documentation with implementation patterns.

#### 6. HTML Content Field - JSX Support Underdocumented
**Issue**: html-content.mdx documents JSX templates but doesn't fully explain the JSX vs static HTML distinction.

**Missing Details**:
- When JSX templating is triggered (presence of `className=` or `{context.`)
- DOMPurify sanitization for static HTML
- Performance implications
- Complete list of available context properties

**Recommended Action**: Add technical reference for HTML field rendering behavior.

#### 7. Launch Workflow Results - Flow Documentation
**Issue**: startup-workflows.mdx explains launch workflows but doesn't document how results flow to main workflow execution.

**Missing Details**:
- `startup_data` is passed to main workflow in execute request
- Main workflow accesses via `context.startup`
- Complete data flow diagram

**Recommended Action**: Add end-to-end flow documentation showing launch workflow -> form render -> main workflow execution.

#### 8. Form Validation - Incomplete
**Issue**: Validation patterns mentioned in docs but not comprehensively covered.

**Missing Details**:
- Available validation properties (`pattern`, `min`, `max`, `message`)
- Client-side vs server-side validation
- Zod schema generation in frontend
- Custom validation patterns

**Recommended Action**: Add validation reference documentation.

#### 9. Query Parameters - URL Pre-filling
**Issue**: Query parameter functionality is documented but `allowed_query_params` form-level setting not explained.

**Missing Details**:
- Form-level `allowed_query_params` setting vs field-level `allow_as_query_param`
- How params are passed to launch workflow
- Security implications

**Recommended Action**: Clarify the two-level query parameter system.

#### 10. SDK Forms Module
**Issue**: No documentation for the Python SDK `bifrost.forms` module.

**Missing Details**:
- `forms.list()` method
- `forms.get(form_id)` method
- When to use SDK vs API directly

**Recommended Action**: Add SDK reference documentation for forms module.

### Inaccuracies Found

1. **Multi-select field type**: Docs mention "Multi-select: Multiple choice" but this type doesn't exist in the codebase. The `FormFieldType` enum only has `select` without multi-select support.

2. **Data provider guide link**: core-concepts/forms.mdx links to `/how-to-guides/forms/data-providers` which doesn't exist. Should link to `/how-to-guides/forms/cascading-dropdowns`.

3. **Context Object Reference link**: context-field-references.mdx links to `/sdk-reference/forms/context-object` which doesn't exist.

### Recommended Actions Summary

| Priority | Action | Effort |
|----------|--------|--------|
| High | Update field types to show all 12 types accurately, remove non-existent multi-select | Low |
| High | Document form virtualization (database-only architecture) | Medium |
| High | Create comprehensive file upload guide | Medium |
| Medium | Expand access control documentation | Medium |
| Medium | Document expression mode for data providers | Low |
| Medium | Add launch workflow to main workflow data flow | Medium |
| Medium | Fix broken documentation links | Low |
| Low | Add SDK forms module reference | Low |
| Low | Add validation reference | Medium |
| Low | Document JSX vs static HTML detection logic | Low |
