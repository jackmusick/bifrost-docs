---
title: Form Field Types Reference
description: Complete reference of all form field types, their configurations, and data formats
---

Bifrost forms support a variety of field types for different data collection needs.

## Text Input

Single-line text entry for names, titles, and short answers.

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Label | Text | Required | Display text for field |
| Field Name | Text | Required | Internal identifier, unique within form |
| Required | Checkbox | false | Whether field must be filled |
| Placeholder | Text | - | Helper text in empty field |
| Help Text | Text | - | Guidance below field |
| Default Value | Text | - | Pre-populated value |
| Visibility Expression | Expression | - | Show/hide condition |
| Allow as Query Parameter | Checkbox | false | Accept value from URL |

### Data Format

Returns as string to workflow.

### Example

```
Field Name: first_name
Label: First Name
Placeholder: John
Help Text: Enter your first name
Required: true
Default Value: (empty)
```

### Validation

- No built-in validation beyond required check
- Server-side validation can be added in workflow

## Email

Email address input with format validation.

### Configuration

Same as Text Input, with automatic email validation.

### Data Format

Returns as string to workflow (validated email format).

### Example

```
Field Name: email_address
Label: Email Address
Placeholder: user@example.com
Help Text: We'll send a confirmation to this email
Required: true
```

### Validation

- Client-side: Email format validation (must contain @)
- Server-side: Further validation in workflow

## Number

Numeric input with up/down spinner controls.

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Label | Text | Required | Display text |
| Field Name | Text | Required | Internal identifier |
| Required | Checkbox | false | Must be filled |
| Placeholder | Text | - | Helper text |
| Help Text | Text | - | Guidance |
| Default Value | Number | - | Pre-populated number |
| Visibility Expression | Expression | - | Show/hide condition |
| Allow as Query Parameter | Checkbox | false | Accept from URL |
| Validation Pattern | Text | - | Min/max values (JSON) |

### Data Format

Returns as number to workflow.

### Validation Configuration

Set min/max in validation:

```json
{
  "min": 0,
  "max": 100
}
```

### Example

```
Field Name: employee_count
Label: Number of Employees
Help Text: Enter a number between 1 and 10000
Default Value: 1
Validation: {"min": 1, "max": 10000}
```

## Dropdown (Select)

Single selection from a list of options.

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Label | Text | Required | Display text |
| Field Name | Text | Required | Internal identifier |
| Required | Checkbox | false | Must select option |
| Placeholder | Text | "Select..." | Default text |
| Help Text | Text | - | Guidance |
| Default Value | Text | - | Pre-selected option value |
| Data Provider | Dropdown | - | Source for options |
| Options (Static) | List | - | Manual label/value pairs |
| Visibility Expression | Expression | - | Show/hide condition |
| Data Provider Inputs | Config | - | Provider parameters |

### Data Format

Returns selected value as string to workflow.

### Options Format

Static options are label/value pairs:

```
[
  {"label": "Engineering", "value": "eng"},
  {"label": "Sales", "value": "sales"},
  {"label": "Marketing", "value": "marketing"}
]
```

### Dynamic Options

Use Data Provider to load options:

1. Select Data Provider from dropdown
2. Choose provider name
3. Configure provider inputs if needed
4. Options load when form opens

### Example: Static

```
Field Name: department
Label: Department
Required: true
Options:
  - Engineering (eng)
  - Sales (sales)
  - Marketing (marketing)
```

### Example: Dynamic

```
Field Name: manager
Label: Manager
Data Provider: get_managers
Provider Inputs:
  - department_id (Field Reference → department)
Help Text: Manager list updates when department selected
```

## Checkbox

Single yes/no toggle.

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Label | Text | Required | Display text |
| Field Name | Text | Required | Internal identifier |
| Required | Checkbox | false | Must be checked |
| Help Text | Text | - | Guidance |
| Default Value | Boolean | false | Checked (true) or unchecked (false) |
| Visibility Expression | Expression | - | Show/hide condition |

### Data Format

Returns boolean (true or false) to workflow.

### Example

```
Field Name: agree_to_terms
Label: I agree to the terms and conditions
Default Value: false (unchecked)
Required: true
```

## Text Area

Multi-line text entry for longer content.

### Configuration

Same as Text Input, but renders with multiple rows.

### Data Format

Returns as string (may contain newlines) to workflow.

### Example

```
Field Name: description
Label: Project Description
Placeholder: Describe your project in detail...
Help Text: Maximum 500 characters recommended
Required: true
```

## Radio Buttons

Single selection with all options visible at once.

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Label | Text | Required | Display text |
| Field Name | Text | Required | Internal identifier |
| Required | Checkbox | false | Must select option |
| Help Text | Text | - | Guidance |
| Default Value | Text | - | Pre-selected option value |
| Options | List | Required | Label/value pairs |
| Visibility Expression | Expression | - | Show/hide condition |

### Data Format

Returns selected value as string to workflow.

### Options Format

Label/value pairs (static only):

```
[
  {"label": "Full-time", "value": "full-time"},
  {"label": "Part-time", "value": "part-time"},
  {"label": "Contractor", "value": "contractor"}
]
```

### Use Cases

- 2-5 options that benefit from being all visible
- Clear choices (yes/no, priority levels)
- Better UX than dropdown when options are few

### Example

```
Field Name: employment_type
Label: Employment Type
Options:
  - Full-time (full-time)
  - Part-time (part-time)
  - Contractor (contractor)
Required: true
```

## Date & Time

Date and time picker with calendar interface.

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Label | Text | Required | Display text |
| Field Name | Text | Required | Internal identifier |
| Required | Checkbox | false | Must be filled |
| Help Text | Text | - | Guidance |
| Default Value | DateTime | - | ISO 8601 format |
| Visibility Expression | Expression | - | Show/hide condition |

### Data Format

Returns as ISO 8601 datetime string to workflow.

Format: `YYYY-MM-DDTHH:MM:SS`

Example: `2024-10-15T14:30:00`

### Example

```
Field Name: start_date
Label: Start Date
Help Text: Select the date you'll begin
Required: true
Default Value: (empty - user selects)
```

## Markdown

Display formatted text (non-input field).

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Label | Text | - | Optional display name |
| Content | Markdown | Required | Formatted text content |
| Visibility Expression | Expression | - | Show/hide condition |

### Data Format

Display-only field. No data sent to workflow.

### Markdown Support

- Headers: `# Heading`, `## Subheading`
- Lists: `- Item`, `1. Numbered`
- Bold: `**text**`
- Italic: `*text*`
- Code: `` `code` ``
- Code blocks: ` ``` `
- Links: `[text](url)`
- Images: `![alt](url)`

### Use Cases

- Section headers
- Instructions
- Help text
- Disclaimers
- Markdown-formatted content

### Example

```
Content:
# Required Information

Please provide the following details:

- Your full name
- Valid email address
- Department assignment

**Note:** All fields are required before submission.
```

## HTML Content

Display rich HTML with context access and React styling.

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Label | Text | - | Optional display name |
| Content | JSX | Required | Template with context |
| Visibility Expression | Expression | - | Show/hide condition |

### Data Format

Display-only field. No data sent to workflow.

### Supported Syntax

- React JSX syntax
- className attributes (not class)
- Context interpolation: `{context.*}`
- Conditional rendering
- Array loops

### Context Access

```jsx
{context.workflow.user_name}
{context.field.email}
{context.query.customer_id}
```

### Styling

React-style Tailwind CSS:

```jsx
<div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
  <p className="text-gray-700">Content</p>
</div>
```

### Use Cases

- Dynamic welcome messages
- Conditional instructions
- Display workflow results
- Rich formatting with user data

### Example

```jsx
<div className="p-4 bg-blue-50 rounded">
  <h2>Welcome, {context.workflow.user_name}!</h2>
  <p>You are creating an account for: {context.workflow.organization_name}</p>
</div>
```

## File Upload

Upload files with type and size restrictions.

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Label | Text | Required | Display text |
| Field Name | Text | Required | Internal identifier |
| Required | Checkbox | false | Must upload file |
| Help Text | Text | - | Guidance |
| Visibility Expression | Expression | - | Show/hide condition |
| Allow as Query Parameter | Checkbox | false | (not applicable) |
| Allowed Types | List | - | MIME type restrictions |
| Multiple Files | Checkbox | false | Allow multi-select |
| Max Size MB | Number | - | File size limit |

### Data Format

Returns array of file objects to workflow (always array, even for single file):

```json
[
  {
    "filename": "document.pdf",
    "content_type": "application/pdf",
    "size_bytes": 1024000,
    "sas_uri": "https://..."
  }
]
```

### File Type Configuration

Specify allowed MIME types:

```
.pdf              → PDF files only
.jpg,.png         → Image files
image/*           → All image types
video/*           → All video types
application/*     → All application types
```

### Example: Single PDF

```
Field Name: contract
Label: Contract Document
Allowed Types: .pdf
Max Size: 5 MB
Multiple: false
Required: true
```

### Example: Multiple Images

```
Field Name: photos
Label: Project Photos
Allowed Types: .jpg,.png,.webp
Max Size: 25 MB
Multiple: true
Required: false
```

## Field Comparison

| Field Type | Input Type | Data Type | Dynamic Options |
|-----------|-----------|-----------|-----------------|
| Text Input | Text | String | No |
| Email | Text | String | No |
| Number | Number | Number | No |
| Dropdown | Select | String | Yes |
| Checkbox | Boolean | Boolean | No |
| Text Area | Text | String | No |
| Radio Buttons | Radio | String | No |
| Date & Time | DateTime | String (ISO 8601) | No |
| Markdown | Display | None | No |
| HTML Content | Display | None | No |
| File Upload | File | Array | No |

## Common Configuration Options

### All Fields

- **Label**: Display text
- **Field Name**: Internal identifier (unique per form)
- **Required**: Whether field must be filled
- **Help Text**: Guidance below field
- **Visibility Expression**: JavaScript condition to show/hide
- **Default Value**: Pre-populated value

### Input Fields Only

- **Placeholder**: Text in empty field

### Selectable Fields

- **Options**: Static label/value pairs
- **Data Provider**: Dynamic option source
- **Data Provider Inputs**: Provider parameters

### File Uploads Only

- **Allowed Types**: MIME type restrictions
- **Multiple Files**: Allow multi-select
- **Max Size**: File size limit in MB

## See Also

- [Creating Forms](/docs/guides/forms/creating-forms) - How to use field types
- [Data Providers](/docs/guides/forms/data-providers) - Populating dropdowns dynamically
- [Visibility Rules](/docs/guides/forms/visibility-rules) - Conditional field display
- [HTML Content](/docs/guides/forms/html-content) - Rich formatting options
