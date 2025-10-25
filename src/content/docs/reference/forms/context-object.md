---
title: Form Context Object
description: Complete reference of the form context object and all available properties
---

The context object provides access to form data throughout the form lifecycle. It's available in visibility expressions, default values, HTML templates, and data provider inputs.

## Context Structure

```javascript
{
  // Current form field values
  field: {
    field_name: value,
    // ... all form fields
  },
  
  // Results from startup/launch workflow
  workflow: {
    result_property: value,
    // ... all workflow return values
  },
  
  // URL query parameters (allowed fields only)
  query: {
    param_name: value,
    // ... allowed query parameters
  }
}
```

## context.field Object

Contains current values of all form fields as users enter them.

### Accessing Field Values

```javascript
// Text field
context.field.first_name

// Email field
context.field.email_address

// Dropdown selection
context.field.department

// Checkbox
context.field.is_admin

// Number
context.field.age

// Date/time
context.field.start_date

// File upload (array of objects)
context.field.attachments
```

### Field Value Types

| Field Type | JavaScript Type | Example |
|-----------|-----------------|---------|
| Text Input | String | `"John"` |
| Email | String | `"user@example.com"` |
| Number | Number | `42` |
| Dropdown | String | `"engineering"` |
| Checkbox | Boolean | `true` |
| Text Area | String | `"Multi-line\ntext"` |
| Radio Buttons | String | `"option-1"` |
| Date & Time | String (ISO 8601) | `"2024-10-15T14:30:00"` |
| File Upload | Array of Objects | `[{filename, content_type, size_bytes, sas_uri}]` |
| Markdown | N/A (display) | N/A |
| HTML Content | N/A (display) | N/A |

### Accessing Empty Fields

Fields might be null, undefined, or empty string:

```javascript
// Check if field has value
if (context.field.email && context.field.email !== "") {
  // Field has value
}

// Check if empty
if (!context.field.optional_field) {
  // Field is empty
}

// Safe navigation (optional chaining)
context.field.nested?.property
```

### Field Names

Field names are case-sensitive and match the field's **Field Name** configuration:

```javascript
// If field name is "first_name"
context.field.first_name   // Correct

// These won't work
context.field.firstName    // undefined
context.field.First_Name   // undefined
```

### Dynamic Updates

`context.field` updates in real-time as users:
- Type in text fields
- Select from dropdowns
- Check/uncheck checkboxes
- Select files
- Enter dates

Visibility expressions re-evaluate whenever any field changes.

## context.workflow Object

Contains results from the startup/launch workflow.

### Prerequisites

Startup workflow must be configured:
1. Select **Launch Workflow** in form settings
2. Form runs workflow on load
3. Results stored in `context.workflow`

### Accessing Workflow Data

```javascript
// Data returned by workflow
context.workflow.user_id
context.workflow.is_admin
context.workflow.organization_name
context.workflow.user_email
context.workflow.departments
```

### Workflow Data Availability

`context.workflow` contains:
- Simple values (strings, numbers, booleans)
- Complex objects and arrays
- Any data returned by workflow

Example workflow:

```python
@workflow(name="get_user_context")
async def get_user_context(context: ExecutionContext):
    user = context
    return {
        "user_id": user.id,
        "user_email": user.email,
        "is_admin": user.is_platform_admin,
        "departments": await fetch_departments(context)
    }
```

Results available:
```javascript
context.workflow.user_id
context.workflow.user_email
context.workflow.is_admin
context.workflow.departments  // Array
```

### Accessing Nested Properties

Workflow can return nested objects:

```javascript
// Simple property
context.workflow.user_id

// Nested object
context.workflow.organization.name
context.workflow.user.email

// Array of objects
context.workflow.departments[0].name
context.workflow.departments.map(d => d.id)
```

### Safe Navigation

Nested properties might not exist:

```javascript
// Could be null or undefined
context.workflow.organization?.name || "Unknown"

// Check existence
if (context.workflow.organization) {
  // Use organization
}

// Default value
const orgName = context.workflow.organization?.name ?? "Not set"
```

### Immutability

`context.workflow` is immutable - it's set once when form loads. Later field changes don't affect it.

This is different from `context.field` which updates in real-time.

## context.query Object

Contains URL query parameters.

### Prerequisites

Query parameters must be enabled per field:
1. Open field configuration
2. Enable **Allow as Query Parameter**
3. Field name automatically added to allowed params
4. Pass values in URL: `/execute/form?field_name=value`

### Accessing Query Parameters

```javascript
// From: /execute/form?customer_id=123&mode=advanced
context.query.customer_id   // "123"
context.query.mode          // "advanced"
```

### Query Parameter Format

All query parameters are strings:

```javascript
// String
context.query.customer_id   // "123" (string, not number)

// Convert to number
parseInt(context.query.customer_id)

// Convert to boolean
context.query.advanced === 'true'

// Check existence
if (context.query.customer_id) {
  // Parameter provided
}
```

### Allowed Parameters

Only fields with **Allow as Query Parameter** enabled appear in `context.query`.

To allow a parameter:
1. Add form field
2. Open field config
3. Enable **Allow as Query Parameter**
4. Field appears in `context.query`

Example:
- Form fields: email, department, name
- Allow as Query Parameter: enabled for email only
- URL: `/execute/form?email=user@example.com`
- Result: `context.query.email` exists, others don't

### Multiple Query Parameters

```
URL: /execute/form?customer_id=123&redirect=/dashboard&detailed=true

context.query.customer_id   // "123"
context.query.redirect      // "/dashboard"
context.query.detailed      // "true"
```

### Special Cases

#### Empty Parameter

```
URL: /execute/form?refresh

context.query.refresh       // "" (empty string)
```

Check for presence:
```javascript
'refresh' in context.query  // true
```

#### Multiple Values

```
URL: /execute/form?tags=js&tags=react

context.query.tags         // "react" (last value wins)
```

For multiple values, pass as comma-separated:
```
URL: /execute/form?tags=js,react,node

context.query.tags         // "js,react,node"
context.query.tags.split(',')  // ["js", "react", "node"]
```

## Context Object Availability

### Where Context Is Available

| Location | context.field | context.workflow | context.query |
|----------|---------------|-----------------|---------------|
| Visibility Expression | ✓ | ✓ | ✓ |
| Default Value | ✓ | ✓ | ✓ |
| HTML Content | ✓ | ✓ | ✓ |
| Data Provider Input (Expression mode) | ✓ | ✓ | ✓ |

### Where Context Is Not Available

- Field label
- Field placeholder
- Help text
- Data provider input (static mode)
- Field options (static)

## Common Context Patterns

### Pre-filling from Query Parameters

```javascript
// Field default value:
context.query.email

// User visits: /execute/form?email=user@example.com
// Email field pre-populated with that value
```

### Pre-filling from Workflow

```javascript
// Field default value:
context.workflow.user_email

// Launch workflow provides user info
// Email field pre-populated with current user's email
```

### Conditional Visibility

```javascript
// Visibility expression:
context.workflow.is_admin === true

// Field shows only for admin users
```

### Cascading Dropdowns

```javascript
// Second field's data provider input (Expression mode):
context.field.first_field_value

// When first field changes, second field updates
```

### Dynamic Content

```jsx
// HTML field content:
<p>Welcome, {context.workflow.user_name}!</p>
<p>Department: {context.field.department}</p>
```

## Debugging Context

### View Context in Form Builder

1. Click **Info** button (ℹ️) in form builder
2. Opens **Context Viewer** panel
3. Shows all current context values:
   - `context.field.*` - Current field values
   - `context.workflow.*` - Workflow results
   - `context.query.*` - Query parameters

### Test Visibility Expressions

1. Open context viewer
2. Check actual field/workflow values
3. Write expression matching those values
4. Verify syntax is correct

### Inspect Field Values

Context viewer shows:
- Exact field names (case-sensitive)
- Current values
- Data types
- Nested properties

Use to verify:
- Field names are spelled correctly
- Values are what you expect
- Data types are correct

### Common Debugging Steps

1. **Check field name**: 
   - Use context viewer to see exact name
   - Field names are case-sensitive

2. **Check for null/undefined**:
   - Workflow data might not exist
   - Fields might be empty
   - Use safe navigation: `?.`

3. **Check data types**:
   - Query parameters are always strings
   - Numbers need conversion: `parseInt()`
   - Booleans need comparison: `=== 'true'`

4. **Test with real data**:
   - Click Play button to run launch workflow
   - Use actual values in testing
   - Check edge cases

## TypeScript Types (Reference)

For developers using TypeScript:

```typescript
interface FormContext {
  field: Record<string, any>;
  workflow: Record<string, any>;
  query: Record<string, string>;
}
```

Field values are `any` because they depend on field types configured in the form.

## See Also

- [Visibility Rules](/docs/guides/forms/visibility-rules) - Using context in expressions
- [HTML Content](/docs/guides/forms/html-content) - Displaying context data
- [Data Providers](/docs/guides/forms/data-providers) - Provider inputs using context
- [Startup Workflows](/docs/guides/forms/startup-workflows) - Providing workflow data
- [Context & Field References](/docs/guides/forms/context-field-references) - Usage guide
