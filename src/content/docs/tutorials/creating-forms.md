---
title: Create Dynamic Forms
description: Step-by-step tutorial for creating and executing forms in Bifrost with dynamic fields and data providers
---

Forms in Bifrost provide a user-friendly interface for collecting data and executing workflows. This tutorial walks you through creating your first form, configuring fields, and testing execution.

## What You'll Learn

By the end of this tutorial, you'll know how to:
- Create a new form and link it to a workflow
- Configure form fields with validation and help text
- Use data providers to populate dropdown options dynamically
- Set up a launch workflow for pre-populating context
- Test and execute your form

## Prerequisites

- Access to Bifrost platform with form creation permissions
- At least one workflow already created
- Familiarity with workflow parameters (names, types, required fields)

## Step 1: Create Your First Form

Navigate to the **Forms** section in the sidebar and click the **+** button to create a new form.

You'll see the **Form Info Dialog** asking for:

- **Name**: Display name for your form (e.g., "Create New User", "Report Issue")
- **Description**: Optional description shown to users
- **Scope**: Global (all organizations) or Organization-specific
- **Linked Workflow**: The workflow that will execute when the form is submitted

Example:
- Name: "Create User Account"
- Description: "Provision a new user in your organization"
- Linked Workflow: "create_user"

Click **Create** to proceed to the form builder.

## Step 2: Add Fields from Workflow Parameters

When you open the form builder, the left panel shows two sections:

1. **Workflow Inputs** - Parameters from your linked workflow
2. **All Field Types** - Standard form components

The easiest way to build a form is to drag workflow parameters directly onto the canvas. Each parameter automatically:
- Gets a readable label (converted from parameter name)
- Inherits the parameter type (text, email, number, etc.)
- Shows whether it's required
- Includes any help text from the workflow

**Example**: If your "create_user" workflow has these parameters:
```
- email (required, email type)
- name (required, string)
- department (data_provider: get_departments)
```

Drag each one to your form. They'll pre-populate with the right settings.

## Step 3: Customize Fields

After adding fields, click on each one to customize:

### Basic Settings
- **Label**: Display text (auto-generated but editable)
- **Placeholder**: Helper text in empty input
- **Help Text**: Additional guidance below field
- **Required**: Whether field must be filled
- **Default Value**: Pre-populated value when form loads

### Advanced Settings

**Visibility Expression**: Show/hide field based on other field values

Example: Only show "equipment_request" if user selects "full-time" as employee type:
```javascript
context.field.employee_type === 'full-time'
```

**Allow as Query Parameter**: Enable passing field value via URL

Example: Pre-fill form from link:
```
/execute/form-id?email=user@example.com&department=IT
```

### Field-Specific Options

**Dropdown/Radio Options**:
- **Static**: Manually define options
- **Data Provider**: Load options from a data source dynamically

**File Upload**:
- **Allowed Types**: File type restrictions (`.pdf`, `image/*`)
- **Multiple Files**: Allow selecting multiple files
- **Max Size**: Maximum file size in MB

## Step 4: Use Data Providers

Data providers dynamically populate dropdown and radio options from your system.

### Selecting a Data Provider

1. Add a dropdown or radio field
2. In the field config, select **Data Provider** from the options dropdown
3. Choose from available data providers (e.g., "get_departments", "get_users")

### Configuring Provider Inputs (Optional)

If your data provider requires parameters, configure them:

1. Click **Data Provider Inputs** in the field config
2. For each required parameter, choose a mode:
   - **Static**: Hard-coded value (e.g., "production")
   - **Field Reference**: Value from another form field (e.g., organization_id)
   - **Expression**: JavaScript expression using context (e.g., `context.workflow.user_id`)

**Example**: "get_managers" data provider needs "department_id"
- Mode: **Field Reference**
- Field Name: "department"
- Now managers list will update when user selects a department

## Step 5: Set Up a Launch Workflow

A launch workflow runs when the form loads to pre-populate context data.

### Configure in Form Settings

1. Click the **Form Settings** tab
2. Select **Launch Workflow** from the workflow list
3. Optionally set **Default Launch Parameters**

Example:
- Launch Workflow: "get_user_context"
- Default Parameters: `{"include_permissions": true}`

The launch workflow results are available in visibility expressions and HTML fields as `context.workflow.*`

### Testing the Launch Workflow

Click the **Play** button in the form builder:

1. Enter any required parameters
2. Click **Execute**
3. View results in the context preview
4. Use this data to test visibility expressions with real values

## Step 6: Add Dynamic Content

### HTML Content Fields

Display dynamic information using template expressions:

1. Add an **HTML Content** field
2. Enter template with context access:

```jsx
<div className="p-4 bg-blue-50 rounded">
  <p>Welcome, {context.workflow.user_email}!</p>
  <p>Organization: {context.workflow.organization_name}</p>
</div>
```

### Visibility with Context

Show fields based on launch workflow results:

```javascript
// Only show for admin users
context.workflow.is_admin === true

// Show based on organization
context.workflow.organization_id === 'org-456'
```

## Step 7: Test Your Form

### Preview the Form

Click the **Eye** icon to see how the form appears to users:

1. All fields with visibility enabled will display
2. Load states show while data providers fetch options
3. Submit button only enables when required fields are filled

### Execute for Real

Click the **Play** button to execute your form as an end-user would:

1. Fill out all visible fields
2. Click **Submit**
3. You'll be redirected to execution history showing the result
4. Check the workflow logs to verify data was received correctly

## Step 8: Save Your Form

Click **Save** to publish your form. Options:

- **Global** (Platform Admin only): Available to all organizations
- **Organization-specific**: Only available in your current organization

## Complete Example: Employee Onboarding Form

Here's a complete form workflow:

**Linked Workflow**: `provision_employee`

**Fields**:
1. **employee_type** (radio)
   - Options: full-time, part-time, contractor
   - Required: Yes

2. **email** (email)
   - Required: Yes
   - Help text: "Company email address"

3. **department** (dropdown)
   - Data Provider: get_departments
   - Required: Yes

4. **manager** (dropdown)
   - Data Provider: get_managers
   - Provider Inputs: department_id (field reference to "department" field)
   - Required: Yes

5. **benefits_eligible** (checkbox)
   - Visibility: `context.field.employee_type === 'full-time'`

6. **equipment_request** (textarea)
   - Visibility: `context.field.employee_type !== 'contractor'`
   - Help text: "List required equipment"

7. **start_date** (date/time)
   - Required: Yes

**Launch Workflow**: `get_user_context`
- Pre-populates user info in context

**Result**: A form that shows/hides fields based on employee type and auto-loads manager list for selected department.

## Best Practices

1. **Keep forms focused**: Cover 5-10 fields per form maximum
2. **Use clear labels**: Make it obvious what data is needed
3. **Progressive disclosure**: Show fields only when relevant
4. **Test with real data**: Use the launch workflow feature
5. **Provide help text**: Guide users on format and requirements
6. **Group related fields**: Use visibility to create sections

## Next Steps

- Learn about [visibility rules](/docs/guides/forms/visibility-rules) for complex logic
- Explore [data providers](/docs/guides/forms/data-providers) for dynamic options
- Set up [startup workflows](/docs/guides/forms/startup-workflows) for context
- Read the [field types reference](/docs/reference/forms/field-types) for complete options
