---
title: Control Field Visibility
description: Master JavaScript expressions for conditional field visibility in forms
---

Visibility rules allow you to show and hide form fields based on other field values, launch workflow data, or query parameters. This creates dynamic, progressive forms that only show relevant fields.

## How Visibility Works

Each field has an optional **Visibility Expression** - a JavaScript expression that must return `true` for the field to appear.

When the expression evaluates to:
- **true**: Field is visible and sent to workflow
- **false** (or falsy): Field is hidden and not sent to workflow

Expressions are re-evaluated whenever any form field changes.

## Accessing Context

Visibility expressions have access to three context objects:

### context.field - Current Form Field Values

Values users have entered or selected:

```javascript
// Text field value
context.field.email

// Dropdown selection
context.field.department

// Checkbox state
context.field.is_admin

// File upload array
context.field.attachments
```

All fields are included, even if not visible. Hidden fields have their last value or null.

### context.workflow - Launch Workflow Results

Results from the launch workflow (if configured):

```javascript
// From a launch workflow that returns user info
context.workflow.user_id
context.workflow.is_admin
context.workflow.organization_id
context.workflow.organization_name
```

Launch workflow runs once when form loads. Results available for entire session.

### context.query - URL Query Parameters

Values from URL query string (only for enabled fields):

```javascript
// From: /execute/form-id?customer_id=123&mode=advanced
context.query.customer_id   // "123"
context.query.mode          // "advanced"
```

Only fields with **Allow as Query Parameter** enabled appear here.

## Writing Expressions

### Simple Comparisons

Check if field equals a value:

```javascript
// Show if user selected full-time
context.field.employee_type === 'full-time'

// Show if age is 18 or older
context.field.age >= 18

// Show if priority is high
context.field.priority === 'high'
```

### Checking Empty Values

Field might be null, empty string, or undefined:

```javascript
// Show if field has a value
context.field.email !== null && context.field.email !== ""

// Show if field is empty
context.field.optional_field === null || context.field.optional_field === ""

// Check existence (safer)
if (context.field.email) { ... }
```

### Multiple Conditions

Combine conditions with AND (&&) and OR (||):

```javascript
// Both must be true (AND)
context.field.country === 'USA' && context.field.state !== null

// Either can be true (OR)
context.field.role === 'admin' || context.field.role === 'manager'

// Complex logic
(context.field.employee_type === 'full-time' && context.field.department === 'IT') 
|| context.field.is_executive === true
```

### Using Workflow Context

Show fields based on launch workflow data:

```javascript
// Only for admin users (from launch workflow)
context.workflow.is_admin === true

// Show if organization is set
context.workflow.organization_id !== null

// Show based on user role
context.workflow.user_role === 'manager'
```

### Using Query Parameters

Show fields based on URL parameters:

```javascript
// /execute/form?mode=advanced
context.query.mode === 'advanced'

// Show if customer_id provided
context.query.customer_id !== null && context.query.customer_id !== ""
```

### Checking Array Contents

For file uploads or multi-select:

```javascript
// Show if files uploaded
context.field.attachments && context.field.attachments.length > 0

// Check for specific file type
context.field.documents?.some(doc => doc.filename.endsWith('.pdf'))
```

### String Operations

```javascript
// Check if email contains specific domain
context.field.email.includes('@company.com')

// Check if name starts with certain letter
context.field.first_name.startsWith('J')

// Case insensitive comparison
context.field.department.toLowerCase() === 'engineering'
```

### Ternary Operators

```javascript
// Show field based on complex condition
context.field.ticket_type === 'bug' 
  ? context.field.severity !== 'low'
  : context.field.priority === 'high'
```

## Common Patterns

### Conditional Field Groups

Create sections that appear together:

```javascript
// All equipment fields appear when employee_type is full-time
context.field.employee_type === 'full-time'
```

Then apply same visibility to:
- equipment_type field
- equipment_specs field
- special_requests field

### Progressive Disclosure

Reveal advanced options when needed:

```javascript
// Show advanced options only if user selected it
context.field.show_advanced_options === true
```

```javascript
// Show advanced timing only if workflow type requires it
context.field.workflow_type === 'recurring' || context.field.workflow_type === 'scheduled'
```

### Cascading Visibility

Show fields in sequence:

```javascript
// Field 1: Show if country is USA
context.field.country === 'USA'

// Field 2: Show if state selected AND country is USA
context.field.state !== null && context.field.country === 'USA'

// Field 3: Show if city selected AND state selected AND country is USA
context.field.city !== null && context.field.state !== null && context.field.country === 'USA'
```

### Admin-Only Fields

```javascript
// Show management fields only for admins
context.workflow.is_admin === true
```

### Based on Selection

```javascript
// Show different fields based on selection
// On "type" field, show approval_budget if type is "budget_request"
context.field.type === 'budget_request'

// Show escalation fields if priority is high
context.field.priority === 'high'
```

### Required Parameters Available

```javascript
// Only show additional fields if required fields filled
context.field.email !== null && context.field.email !== "" && 
context.field.name !== null && context.field.name !== ""
```

## Best Practices

### Always Check for Null/Empty

Fields might be empty, null, or undefined:

```javascript
// Good: Handles all cases
context.field.email !== null && context.field.email !== ""

// Bad: Might fail if field is null
context.field.email.includes('@')
```

### Use Strict Equality

```javascript
// Good: Explicit type comparison
context.field.status === 'active'

// Avoid: Type coercion
context.field.status == 'active'
```

### Keep Expressions Simple

```javascript
// Good: Clear and readable
context.field.country === 'USA' && context.field.state === 'CA'

// Avoid: Hard to understand and maintain
!!(context.field.x && (context.field.y || context.field.z)) || context.field.q
```

### Document Complex Rules

If your visibility rule is complex, add help text to the hidden field explaining when it appears:

```
Help text: "This field appears when country is USA and state is California"
```

### Test with Launch Workflow

Use the **Play** button in form builder to:
1. Execute launch workflow with real data
2. View results in context preview
3. Test visibility expressions against real values
4. Verify edge cases (null, empty, missing values)

## Expression Editor

The visibility expression field has helpful features:

- **Syntax highlighting**: JavaScript syntax colored correctly
- **Error detection**: Red underline for invalid syntax
- **Example below editor**: Shows valid expression format
- **Context preview**: Click Info button to see available context
- **Real-time evaluation**: Test expressions in preview

## Debugging

### Expression Not Working?

1. **Check syntax**: JavaScript expressions are case-sensitive
   - `context.field.name` (correct)
   - `context.field.Name` (wrong field name)

2. **Check field names**: Field names must match exactly
   - Use context preview to see exact names
   - Field names are case-sensitive

3. **Check null values**: Fields might be null instead of empty string
   ```javascript
   // Handle both cases
   context.field.value !== null && context.field.value !== ""
   ```

4. **Use context preview**: Click Info button to see what data is available
   - Look for `context.field.*` properties
   - Verify property names and values

### Field Always Hidden?

- Check if expression returns true
- Verify field names in expression are correct
- Use context preview to check values
- Test with real launch workflow data

### Field Always Showing?

- Check expression isn't reversed
- Look for logic errors (should be && not ||)
- Verify comparison operators correct (=== not ==)

## Examples by Form Type

### Support Ticket Form

```javascript
// Priority field: Show if customer is premium
context.workflow.customer_tier === 'premium'

// Escalation field: Show if priority is critical
context.field.priority === 'critical'

// Emergency contact: Show if escalated
context.field.escalated === true && context.field.priority === 'critical'

// Callback time: Show if callback selected
context.field.contact_method === 'callback'
```

### Employee Onboarding

```javascript
// Manager field: Show if not contractor
context.field.employee_type !== 'contractor'

// Start date: Show if full-time or part-time
context.field.employee_type === 'full-time' || context.field.employee_type === 'part-time'

// Benefits setup: Show if eligible for benefits
context.field.employee_type === 'full-time'

// Client company: Show if contractor
context.field.employee_type === 'contractor'
```

### Survey Form

```javascript
// Satisfaction comment: Show if satisfaction < 3
context.field.satisfaction && context.field.satisfaction <= 2

// Would recommend: Show if satisfaction >= 3
context.field.satisfaction && context.field.satisfaction >= 3

// Follow up contact: Show if would recommend
context.field.would_recommend === true

// Contact method: Show if wants follow up
context.field.wants_followup === true
```

## See Also

- [Form Context Object](/docs/reference/forms/context-object) - Complete context reference
- [Creating Forms](/docs/guides/forms/creating-forms) - How to configure visibility
- [Data Providers](/docs/guides/forms/data-providers) - Using launch workflow context
