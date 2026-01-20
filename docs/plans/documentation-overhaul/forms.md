# Forms

## Source of Truth (Codebase Review)

_Completed by Codebase Agent on 2026-01-20_

### Current Features

#### Form Model and Structure

**Database Models** (`/Users/jack/GitHub/bifrost/api/src/models/orm/forms.py`):
- `Form` - Main form entity with fields:
  - `id` (UUID, primary key)
  - `name`, `description` - Basic metadata
  - `workflow_id` - Linked workflow ID (UUID string) to execute on submit
  - `launch_workflow_id` - Optional startup workflow that runs before form display
  - `default_launch_params` - Default parameters for launch workflow (JSONB)
  - `allowed_query_params` - List of URL query params that can populate form context (JSONB)
  - `access_level` - Enum: `authenticated` or `role_based`
  - `organization_id` - NULL for global forms, UUID for org-specific
  - `is_active` - Soft delete flag
  - `module_path`, `last_seen_at` - File sync metadata
  - `workflow_path`, `workflow_function_name` - Cross-environment portability refs

- `FormField` - Individual form fields with:
  - `name`, `label`, `type`, `required`, `position`
  - `placeholder`, `help_text`, `default_value`
  - `options` - Static options for select/radio (JSONB)
  - `data_provider_id` - FK to workflows table (type='data_provider')
  - `data_provider_inputs` - Configuration for data provider parameters (JSONB)
  - `visibility_expression` - JavaScript expression for conditional visibility
  - `validation` - Custom validation rules (JSONB)
  - File field properties: `allowed_types`, `multiple`, `max_size_mb`
  - Display field properties: `content` (for markdown/html)

- `FormRole` - M2M association table for role-based access control

**Pydantic Contract Models** (`/Users/jack/GitHub/bifrost/api/src/models/contracts/forms.py`):
- `FormField` - Field definition with validation
- `FormFieldValidation` - Pattern, min, max, message
- `DataProviderInputConfig` - Configuration for data provider input modes
- `FormSchema` - Container with max 50 fields, unique name validation
- `Form`, `FormCreate`, `FormUpdate`, `FormPublic` - CRUD models
- `FormExecuteRequest`, `FormStartupResponse` - Execution models

**Enums** (`/Users/jack/GitHub/bifrost/api/src/models/enums.py`):
- `FormAccessLevel`: `AUTHENTICATED`, `ROLE_BASED`
- `FormFieldType`: `TEXT`, `EMAIL`, `NUMBER`, `SELECT`, `CHECKBOX`, `TEXTAREA`, `RADIO`, `DATE`, `DATETIME`, `MARKDOWN`, `HTML`, `FILE`
- `DataProviderInputMode` (in base.py): `STATIC`, `FIELD_REF`, `EXPRESSION`

#### Form Virtualization (Database-Only Storage)

Forms are now "virtual entities" - they exist only in the database and are serialized on-the-fly for git sync operations. This is a significant architectural change from file-based storage.

**Key files**:
- `/Users/jack/GitHub/bifrost/api/src/services/file_storage/indexers/form.py` - Form indexer with serialization logic
- `/Users/jack/GitHub/bifrost/api/alembic/versions/20260119_150000_remove_form_agent_workspace_files.py` - Migration removing form/agent entries from workspace_files

**Serialization for Git Sync**:
- `_serialize_form_to_json()` function in form indexer converts Form ORM to JSON bytes
- Uses `FormPublic.model_dump()` with serialization context
- Supports portable workflow refs via workflow_map (UUID to path::function_name transformation)
- Adds `_export` metadata with ref paths when exporting with transforms

**Import/Index Process**:
- `FormIndexer.index_form()` parses `.form.json` files
- Handles portable refs from exports via `build_ref_to_uuid_map()` and `transform_path_refs_to_uuids()`
- Performs upsert on Form table, preserving env-specific fields (organization_id, access_level)
- Deletes and recreates FormField records on schema update

#### API Endpoints (`/Users/jack/GitHub/bifrost/api/src/routers/forms.py`)

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/forms` | GET | List forms (cascade scoped + role filtered) | Any user |
| `/api/forms` | POST | Create form | Superuser |
| `/api/forms/{form_id}` | GET | Get specific form | Any user |
| `/api/forms/{form_id}` | PATCH | Update form | Superuser |
| `/api/forms/{form_id}` | DELETE | Soft delete form | Superuser |
| `/api/forms/{form_id}/execute` | POST | Execute form workflow | User with access |
| `/api/forms/{form_id}/startup` | POST | Execute launch workflow | User with access |
| `/api/forms/{form_id}/upload` | POST | Generate presigned upload URL | User with access |

**Access Control**:
- Cascade scoping: org-specific forms + global (NULL org_id) forms
- `authenticated`: Any logged-in user can access
- `role_based`: User must have a role assigned to the form
- Platform admins bypass all access checks

#### Visibility Rules and Conditional Logic

**Client-side evaluation** (`/Users/jack/GitHub/bifrost/client/src/contexts/FormContext.tsx`):
- `evaluateVisibilityExpression()` uses JavaScript `Function` constructor
- Context available: `context.workflow`, `context.query`, `context.field`
- Fail-open: invalid expressions show the field by default
- Security: Only admins write expressions, client-side only with restricted context

**Expression examples**:
```javascript
context.field.is_manager === true
context.field.role === "admin" && context.field.department === "engineering"
context.workflow.user_exists === true
```

#### Data Providers and Cascading Dropdowns

**Input Configuration Modes** (T005, T006):
1. `static` - Fixed value (e.g., `value: "fixed_value"`)
2. `fieldRef` - Reference another field (e.g., `field_name: "department"`)
3. `expression` - JavaScript expression (e.g., `expression: "context.field.x + context.workflow.y"`)

**Client Implementation** (`/Users/jack/GitHub/bifrost/client/src/components/forms/FormRenderer.tsx`):
- `evaluateDataProviderInputs()` evaluates all three modes
- `loadDataProviders()` fetches options with resolved inputs
- Dependent dropdowns: changing a field clears dependent provider data
- Loading state management with `fieldBlurTriggerRef` for user-friendly UX

#### Launch/Startup Workflows

**Purpose**: Pre-populate form context before display

**Flow**:
1. User navigates to form
2. If `launch_workflow_id` configured, `/api/forms/{id}/startup` is called
3. Results stored in `context.workflow`
4. Main workflow receives startup data via `context.startup`

**Use cases**:
- Pre-fetch dynamic options based on user's org
- Load user-specific defaults
- Validate form access based on external systems

#### File Upload

**Endpoint**: `POST /api/forms/{form_id}/upload`
- Generates presigned S3 URL for direct upload
- Path format: `uploads/{form_id}/{uuid}/{sanitized_filename}`
- Server-side validation of file type and size per field configuration
- 10-minute expiration on presigned URLs

**Client Component**: `/Users/jack/GitHub/bifrost/client/src/components/forms/FileUploadField.tsx`

#### SDK Forms Access (`/Users/jack/GitHub/bifrost/api/bifrost/forms.py`)

Read-only SDK for workflows to access form definitions:
- `forms.list()` - List all accessible forms
- `forms.get(form_id)` - Get specific form

### Recent Changes

1. **Form Virtualization** (Jan 2026):
   - Migration `20260119_150000_remove_form_agent_workspace_files.py` removed form entries from workspace_files
   - Forms now serialized on-the-fly for git sync
   - Eliminates S3 file storage dependency for form definitions

2. **Data Provider FK Migration**:
   - Migration `20251222_000000_form_field_data_provider_fk.py`
   - `data_provider_id` now references workflows table (type='data_provider')
   - Previously referenced deprecated data_providers table

3. **Form Fields Table** (Dec 2025):
   - Migration `20251205_023046_add_form_fields_table.py`
   - Moved from JSONB form_schema to relational form_fields table
   - Enables better querying and indexing

4. **Launch Workflow Support**:
   - Migration `20251209_193337_add_launch_workflow_id_to_forms.py`
   - Added startup workflow capability

5. **Portable Workflow References**:
   - Added `workflow_path` and `workflow_function_name` for cross-environment portability
   - Serialization context transforms UUIDs to portable refs during export

### Key Concepts to Document

1. **Form Virtualization Architecture**
   - Why forms are database-only now
   - How git sync serialization works
   - Portable reference transformation

2. **Field Types Reference**
   - All 12 field types with examples
   - When to use each type
   - Field-specific configuration options

3. **Visibility Expressions Guide**
   - Syntax and available context
   - Common patterns and examples
   - Debugging tips

4. **Data Provider Integration**
   - Three input modes (static, fieldRef, expression)
   - Cascading dropdown patterns
   - Performance considerations

5. **Launch Workflows**
   - Use cases and patterns
   - How startup data flows to main workflow
   - Testing in form builder

6. **Access Control**
   - authenticated vs role_based
   - Organization scoping (global vs org-specific)
   - Role assignment workflow

7. **File Upload**
   - S3 presigned URL flow
   - File validation configuration
   - Size and type restrictions

8. **Form Builder UI**
   - Drag-and-drop field ordering
   - Preview mode
   - Context preview panel

### File Reference

**Backend**:
- `/Users/jack/GitHub/bifrost/api/src/models/orm/forms.py` - ORM models
- `/Users/jack/GitHub/bifrost/api/src/models/contracts/forms.py` - Pydantic contracts
- `/Users/jack/GitHub/bifrost/api/src/models/enums.py` - Enums
- `/Users/jack/GitHub/bifrost/api/src/repositories/forms.py` - Repository with scoping
- `/Users/jack/GitHub/bifrost/api/src/routers/forms.py` - API router
- `/Users/jack/GitHub/bifrost/api/src/services/file_storage/indexers/form.py` - Git sync serialization
- `/Users/jack/GitHub/bifrost/api/bifrost/forms.py` - SDK

**Frontend**:
- `/Users/jack/GitHub/bifrost/client/src/pages/FormBuilder.tsx` - Builder UI
- `/Users/jack/GitHub/bifrost/client/src/pages/Forms.tsx` - Forms list
- `/Users/jack/GitHub/bifrost/client/src/pages/RunForm.tsx` - Form execution
- `/Users/jack/GitHub/bifrost/client/src/components/forms/FormRenderer.tsx` - Runtime renderer
- `/Users/jack/GitHub/bifrost/client/src/contexts/FormContext.tsx` - Context/visibility
- `/Users/jack/GitHub/bifrost/client/src/hooks/useForms.ts` - React Query hooks

**Tests**:
- `/Users/jack/GitHub/bifrost/api/tests/unit/models/test_forms_contract.py` - Contract tests
- `/Users/jack/GitHub/bifrost/api/tests/unit/sdk/test_sdk_forms.py` - SDK tests
- `/Users/jack/GitHub/bifrost/api/tests/e2e/api/test_forms.py` - E2E tests
- `/Users/jack/GitHub/bifrost/api/tests/e2e/api/test_form_fields.py` - Field tests

**Existing Documentation**:
- `/Users/jack/GitHub/bifrost/api/shared/docs/core-concepts/forms.txt`
- `/Users/jack/GitHub/bifrost/api/shared/docs/how-to-guides/forms/creating-forms.txt`
- `/Users/jack/GitHub/bifrost/api/shared/docs/troubleshooting/forms.txt`

---

## Documentation State (Docs Review)

_To be completed by Docs Agent_

### Existing Docs
<!-- What docs currently exist, file paths -->

### Gaps Identified
<!-- What's missing, outdated, or inaccurate -->

### Recommended Actions
<!-- Specific actions to take -->
