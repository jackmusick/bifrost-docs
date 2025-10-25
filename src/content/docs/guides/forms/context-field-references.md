---
title: Access Context and Fields
description: Complete guide to using form context, field references, and dynamic values
---

Form context provides access to form field values, launch workflow results, and query parameters throughout your form. This guide shows how to access and use this data.

## Context Structure

The context object has three main sections:

```javascript
{
  field: {
    // Current form field values as user enters them
    email: "user@example.com",
    department: "engineering",
    first_name: "John"
  },
  
  workflow: {
    // Results from launch workflow (if configured)
    user_id: "user-123",
    is_admin: true,
    organization_name: "Acme Corp"
  },
  
  query: {
    // URL query parameters (only allowed fields)
    customer_id: "cust-456",
    redirect_url: "/dashboard"
  }
}
```

## context.field - Form Field Values

Access values users have entered or selected in the form.

### Accessing Field Values

```javascript
// Text field
context.field.email

// Dropdown selection
context.field.department

// Checkbox (boolean)
context.field.is_admin

// Number
context.field.age

// Date/time
context.field.start_date

// File upload (array)
context.field.attachments
```

All form fields appear in context.field, even if not visible. Hidden fields have their last value or null.

### Using in Visibility Expressions

Show/hide fields based on other field values:

```javascript
// Show if user selected "other"
context.field.contact_method === 'other'

// Show if name is filled
context.field.name !== null && context.field.name !== ""

// Show if age >= 18
context.field.age >= 18
```

### Using as Default Values

Pre-populate one field based on another:

If you select a dropdown value, you can use it to determine another field's default:

```javascript
// This works if context is available in defaults
context.field.department
```

## context.workflow - Launch Workflow Data

Access data from the startup workflow.

### Setup

Startup workflow must be configured in form settings:
1. Select **Launch Workflow**
2. Optionally set **Default Launch Parameters**

### Accessing Workflow Data

```javascript
// String value
context.workflow.user_email

// Boolean
context.workflow.is_admin

// Number
context.workflow.organization_id

// Array/Object
context.workflow.departments
context.workflow.user.name
```

### Using in Visibility Expressions

Show fields based on launch workflow results:

```javascript
// Show admin fields only for admins
context.workflow.is_admin === true

// Show based on tier
context.workflow.customer_tier === 'premium'

// Show if data exists
context.workflow.organization_id !== null
```

### Using as Default Values

Pre-populate with workflow data:

```javascript
// Set email to current user's email
context.workflow.user_email

// Set organization to user's default org
context.workflow.default_organization_id
```

### Using in HTML Content

Display workflow data:

```jsx
<p>Welcome, {context.workflow.user_name}!</p>
<p>Organization: {context.workflow.organization_name}</p>
```

### Using as Data Provider Input

Pass workflow data to data providers:

```
Data Provider Input Mode: Expression
Expression: context.workflow.organization_id
```

This passes organization ID from workflow to data provider.

## context.query - URL Query Parameters

Access values passed via URL query string.

### Setup

Enable fields to accept query parameters:
1. Open field configuration
2. Enable **Allow as Query Parameter**
3. Field name automatically added to allowed params

### Accessing Query Parameters

```javascript
// From: /execute/form?customer_id=123&mode=advanced
context.query.customer_id   // "123"
context.query.mode          // "advanced"
```

Query parameters are strings by default. Convert to other types if needed:

```javascript
// Convert to number
parseInt(context.query.customer_id)

// Check for boolean flag
context.query.detailed === 'true'
```

### Using in Visibility Expressions

Show fields based on query parameters:

```javascript
// Show detailed fields if requested
context.query.detailed === 'true'

// Show specific section if provided
context.query.section === 'advanced'
```

### Using as Default Values

Pre-populate with query parameters:

```javascript
// Set email from URL
context.query.email

// Set customer ID from URL
context.query.customer_id
```

### Example: Pre-filling Forms

Create shareable links that pre-fill forms:

```
URL: /execute/form?email=user@example.com&department=IT

Form setup:
- email field: allow as query param
- department field: allow as query param
- Both fields automatically populated from URL
```

## Field References in Data Providers

Data providers can receive form field values as input.

### Configuring Field References

1. Select dropdown/radio field with data provider
2. Click **Data Provider Inputs**
3. For parameter, select **Field Reference** mode
4. Select the field name to reference

### How It Works

When the referenced field changes:
1. Form detects change
2. Calls data provider with new field value
3. Options list updates

### Example: Cascading Dropdowns

```
Field 1: department (dropdown)
Field 2: manager (dropdown with data provider)

Data Provider Input:
  Parameter: department_id
  Mode: Field Reference
  Field: department

Result: When user selects department, manager list loads for that department
```

## Expressions vs Static Values

### Static Values

Hard-coded values that don't change:

```javascript
// Context: {data: "fixed"}
```

Use for:
- Configuration values
- Fixed lists
- Constants

### Field References

Values from form fields:

```javascript
// Context: {field: {email: "user@example.com"}}
context.field.email
```

Use for:
- User input
- Inter-field dependencies
- Dynamic defaults

### Expressions

JavaScript expressions evaluated at load time:

```javascript
// Context: {workflow: {user_id: "123"}}
context.workflow.user_id

// Calculate value
parseInt(context.workflow.user_id) * 2

// Conditional
context.field.country === 'USA' ? 'us' : 'intl'
```

Use for:
- Dynamic computation
- Complex logic
- Context transformation

## Common Access Patterns

### Safe Null Checking

Fields might be null, undefined, or empty:

```javascript
// Check if field has value
if (context.field.email && context.field.email !== "") {
  // Use field
}

// Alternate syntax
if (context.field.email != null) {
  // Use field
}

// With default
const email = context.field.email || "no-email@example.com"
```

### Nested Properties

Access nested workflow data:

```javascript
// Access nested properties
context.workflow.user.email
context.workflow.organization.name

// Safe navigation (optional chaining)
context.workflow.user?.email || "unknown"
```

### Array Operations

Work with arrays from workflow:

```javascript
// Check if has items
if (context.workflow.departments && context.workflow.departments.length > 0) {
  // Has departments
}

// Find specific item
const engineering = context.workflow.departments?.find(d => d.name === 'Engineering')

// Map to array of values
context.workflow.departments?.map(d => d.id)
```

### Type Conversion

Convert types when needed:

```javascript
// String to number
parseInt(context.query.limit, 10)

// String to boolean
context.query.advanced === 'true'

// Format date
new Date(context.workflow.date).toLocaleDateString()
```

## Debugging Context

### View in Form Builder

Click **Info** button (ℹ️) to open context viewer:

Shows:
- `context.field` - Current field values
- `context.workflow` - Launch workflow results
- `context.query` - Query parameters

Helps verify:
- Field names and values
- Workflow data available
- Query parameter names

### Test Visibility Expressions

1. Open context viewer
2. Look at actual field values
3. Write expression to match values
4. Test with edge cases (null, empty)

### Inspect Field Names

Field names are case-sensitive:

```javascript
// Correct (if field name is "first_name")
context.field.first_name

// Wrong (capital letters)
context.field.firstName  // undefined!
```

Use context viewer to confirm exact field names.

## Examples by Use Case

### Pre-filling Customer Form

```
Query URL: /execute/form?customer_id=123

Form setup:
1. customer_id field:
   - Type: text
   - Allow as Query Parameter: enabled
   - Visibility: false (hidden from user)
   - Default: context.query.customer_id

2. Launch Workflow: load_customer
   - Parameter: customer_id (from query)
   - Returns: customer_name, email, address

3. HTML field:
   - Content: "Welcome back, {context.workflow.customer_name}!"

4. Email field:
   - Default: context.workflow.email

Result: Email and customer name pre-populated from context
```

### Role-Based Fields

```
Launch Workflow: get_user_permissions
  Returns: is_manager, is_admin

Field visibility rules:
- Team size field: context.workflow.is_manager === true
- Admin settings: context.workflow.is_admin === true
- Manager notes: context.workflow.is_manager === true

Result: Different fields shown to managers vs regular users
```

### Cascading Selections

```
Field 1: country (dropdown)
Field 2: state (dropdown)

Launch Workflow: get_countries
  Returns: list of countries

Field 1 setup:
- Data Provider: returns all countries

Field 2 setup:
- Data Provider: get_states
- Provider Input: country_id (Field Reference to country field)

Result: When user selects country, state dropdown loads matching states
```

### Conditional Data Providers

```
Field: manager_name (dropdown)

Data Provider: get_managers
- Parameter: department_id

Provider Input:
- Mode: Field Reference
- Field: department

Form Flow:
1. User selects department
2. Manager list updates with departments's managers
3. User selects manager
4. Information available in context.field.manager_name

Visibility Rule:
- Show manager field: context.field.department !== null && context.field.department !== ""
```

## Best Practices

1. **Always check for null/empty**:
   ```javascript
   // Good
   context.field.email !== null && context.field.email !== ""
   
   // Bad - might fail if null
   context.field.email.includes('@')
   ```

2. **Use exact field names**:
   - Field names are case-sensitive
   - Check context viewer for correct names
   - Watch for spaces vs underscores

3. **Test with real data**:
   - Use launch workflow test feature
   - Verify context has expected data
   - Test edge cases (missing fields, nulls)

4. **Keep expressions simple**:
   - Complex expressions are hard to maintain
   - Break into multiple fields if needed
   - Document complex logic in help text

5. **Document dependencies**:
   - Add help text explaining field relationships
   - Note which fields trigger data provider calls
   - Explain visibility rules

## See Also

- [Creating Forms](/docs/guides/forms/creating-forms) - Using context in defaults
- [Visibility Rules](/docs/guides/forms/visibility-rules) - Expression examples
- [HTML Content](/docs/guides/forms/html-content) - Displaying context data
- [Data Providers](/docs/guides/forms/data-providers) - Provider inputs
- [Startup Workflows](/docs/guides/forms/startup-workflows) - Setting up workflow context
