---
title: Create and Configure Forms
description: Complete guide to creating forms, configuring fields, and managing form settings in Bifrost
---

This guide covers the form builder interface, field configuration, and all form settings.

## Creating a New Form

Navigate to **Forms** in the sidebar and click the **+** button.

### Form Info Dialog

Fill in the initial form details:

| Setting | Required | Description |
|---------|----------|-------------|
| Name | Yes | Display name for the form (max 200 characters) |
| Description | No | Optional description shown to users |
| Linked Workflow | Yes | The workflow to execute when form is submitted |
| Scope | Yes | Global (all orgs) or Organization-specific |

## Form Builder Interface

The form builder has three main areas:

### Left Panel: Field Palette

**Workflow Inputs Section**
- Shows all parameters from your linked workflow
- Drag parameters directly onto canvas to auto-create fields
- Pre-populated with parameter settings (type, required, help text, data provider)

**All Field Types Section**
- Standard form components available for any form
- Drag to canvas or click to open configuration dialog

Available field types:
- Text Input
- Email
- Number
- Dropdown (Select)
- Checkbox
- Text Area
- Radio Buttons
- Date & Time
- Markdown
- HTML Content
- File Upload

### Center Canvas

Drag-and-drop area to arrange form fields. Features:

- **Reorder fields**: Click and drag fields to reorder
- **Edit fields**: Click on any field to open configuration
- **Delete fields**: Click the X button on field
- **Real-time preview**: See form layout as you build

### Right Panel: Form Settings

#### Basic Settings
- **Form Name**: Change the form title
- **Description**: Edit form description
- **Linked Workflow**: Change which workflow executes
- **Scope**: Toggle between Global and Organization-specific
- **Active/Inactive**: Enable or disable the form
  - Disabled forms show "Inactive" message to users
  - Form can still be edited in builder

#### Launch Workflow Settings

Optional workflow to run when form loads:

1. **Launch Workflow**: Select workflow to run on form open
2. **Default Launch Parameters**: Provide default values for launch workflow parameters
3. **Allowed Query Parameters**: List of form fields allowed to receive values from URL

The launch workflow results populate `context.workflow.*` for use in visibility expressions and HTML templates.

#### Query Parameter Configuration

Enable fields to receive values from URL:

```
/execute/form-id?email=user@example.com&department=IT
```

For each field you want to allow via URL:
1. Open field configuration
2. Enable **Allow as Query Parameter**
3. Field will be added to `allowedQueryParams` automatically

Query values are available in visibility expressions and default values as:
```javascript
context.query.field_name
```

## Field Configuration

Click any field to open the configuration dialog.

### Basic Settings

| Setting | Type | Description |
|---------|------|-------------|
| Field Name | Text (read-only for workflow inputs) | Internal identifier, must be unique |
| Label | Text | Display text shown to users |
| Field Type | Dropdown | Text, Email, Number, Dropdown, etc. |
| Required | Checkbox | Whether field must be filled |
| Placeholder | Text | Helper text in empty input |
| Help Text | Text | Additional guidance below field |
| Default Value | Field-specific | Value when form loads |

### Advanced Settings

#### Visibility Expression

JavaScript expression to show/hide field. Access:
- `context.field.*` - Current form field values
- `context.workflow.*` - Launch workflow results
- `context.query.*` - URL query parameters

Examples:
```javascript
// Simple comparison
context.field.country === 'USA'

// Check if value exists
context.field.email !== null && context.field.email !== ''

// Multiple conditions
context.field.employee_type === 'full-time' && context.field.department === 'IT'

// Using workflow context
context.workflow.is_admin === true
```

Expression must return a boolean. If not visible, field is not sent to workflow.

#### Allow as Query Parameter

Enable this field to receive values from URL query parameters. When enabled:
- Field appears in URL: `/execute/form-id?field_name=value`
- Value available in: `context.query.field_name`
- Used for pre-filling forms from email links

### Field-Specific Options

#### Text Input, Email, Number, Text Area

Standard text input fields. Email and Number have automatic format validation.

#### Dropdown / Select

Single selection from options list.

**Options Source**:
1. **Static Options**
   - Manually define label/value pairs
   - Click **Add Option** to add more
   - Good for fixed lists (countries, departments)

2. **Data Provider**
   - Dynamically load options from a data source
   - Select from available data providers list
   - Options load when form opens

**Data Provider Inputs** (for parameterized providers):

If your data provider requires parameters, configure how to provide them:

1. Click **Data Provider Inputs**
2. For each required parameter, set the mode:

| Mode | Use | Configuration |
|------|-----|---------------|
| Static | Hard-coded value | Enter the value |
| Field Reference | Value from another form field | Select field name |
| Expression | JavaScript expression | Enter expression |

Example: "get_managers" provider needs "department_id"
- Parameter name: "department_id"
- Mode: Field Reference
- Field Name: "department"
- Manager list updates when user selects department

#### Checkbox

Boolean yes/no toggle.

- **Default Value**: true (checked) or false (unchecked)
- Returns as boolean to workflow

#### Radio Buttons

Single selection with all options visible at once.

- **Options**: Static label/value pairs only
- Use when 2-5 options that benefit from being visible
- Good for clear alternatives (yes/no, priority levels)

#### Date & Time

Date and time picker with calendar interface.

- **Default Value**: ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- Returns as ISO 8601 string to workflow

#### Markdown

Display formatted text (non-input field).

- **Content**: Full Markdown syntax supported
- Use for instructions, section headers, explanations
- Supports headings, lists, bold, italic, code blocks, links

#### HTML Content

Display rich HTML with context access and React-style styling.

**Content Field**: Enter JSX template with context variables

```jsx
<div className="p-4 bg-blue-50 rounded">
  <h3>Welcome, {context.workflow.user_email}!</h3>
  <p>Organization: {context.workflow.organization_name}</p>
</div>
```

**Features**:
- Full context access with `{context.*}`
- React-style className for styling
- Conditional rendering with ternary operators
- HTML is sanitized for security

#### File Upload

Upload files with restrictions.

**Settings**:
- **Allowed Types**: MIME type restrictions
  - Single type: `.pdf`
  - Multiple: `.pdf,.jpg,.png`
  - Wildcard: `image/*`, `video/*`
  
- **Multiple Files**: Allow selecting multiple files at once
  - Returns array of file objects
  
- **Max Size**: Maximum file size in MB
  - Enforced on upload
  - User sees validation error if exceeded

**Data Structure**:
File uploads return an array of objects:

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

The `sas_uri` is a secure URL for accessing the uploaded file.

## Context Viewer

Click the **Info** (ℹ️) button in the form builder to preview context:

Shows:
- `context.workflow.*` - Results from launch workflow
- `context.query.*` - URL query parameters
- `context.field.*` - Current form field values

Helps when writing visibility expressions to see what data is available.

## Enabling/Disabling Forms

In the form list, toggle the **Active** status:

- **Active** (Green): Users can execute
- **Inactive** (Gray): Shows "Inactive" message
  - Form builder can still edit
  - Cannot be executed by users

## Testing Forms

### Preview Mode

Click the **Eye** icon to preview form:
- See layout and field visibility
- Visibility expressions evaluated in real-time
- Click on fields to test defaults

### Execute Test

Click the **Play** button to test form execution:
- Fill out form as user would
- Submit to execute linked workflow
- See results in execution history
- Check workflow logs

### Test Launch Workflow

Click **Play** button in form settings:
- Enter parameters for launch workflow
- Executes immediately
- View results in context preview
- Use to test visibility expressions with real data

## Form Actions

In the form list:

| Action | Effect |
|--------|--------|
| Edit (✏️) | Open form builder |
| Launch (▶️) | Execute form as user |
| Delete (🗑️) | Soft delete (sets inactive) |
| Toggle Active | Enable/disable for users |

## Best Practices

### Field Organization

1. **Top to bottom flow**: Order fields in the order users will fill them
2. **Required first**: Put must-have fields near top
3. **Group related**: Use visibility to create logical sections
4. **Clear progression**: Match user's mental model of the task

### Field Configuration

1. **Clear labels**: Make it obvious what data is needed
2. **Helpful text**: Guide on format, examples, requirements
3. **Smart defaults**: Pre-populate when you know the value
4. **Validation**: Use field type validation (email, number ranges)

### Visibility Rules

1. **Keep simple**: Complex expressions are hard to maintain
2. **Test edge cases**: What if field is null? Empty?
3. **Avoid excessive hiding**: Don't show/hide fields too aggressively
4. **Document complex rules**: Add help text explaining why field shows

### Performance

1. **Limit data providers**: Each call adds latency
2. **Use static options when possible**: Faster and more reliable
3. **Cache provider results**: Fewer API calls during form use
4. **Minimize HTML templates**: Keep templates simple and focused

## Troubleshooting

**Form won't save**
- Check all required fields are filled
- Verify linked workflow exists
- Check visibility expressions have correct syntax

**Fields not appearing**
- Check visibility expression returns true
- Verify field is enabled (not hidden by expression)
- Look in context preview to see available data

**Data provider not loading**
- Check provider exists and is available
- Verify required parameters are provided
- Check network tab for API errors

**Launch workflow not executing**
- Verify workflow is selected
- Check for required parameters
- Verify launch workflow in registry
