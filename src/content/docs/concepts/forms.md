---
title: Forms
description: Conceptual overview of how forms work in Bifrost and their role in workflow execution
---

Forms are the user-facing interface for collecting data and executing workflows. They bridge the gap between end-users and workflow automation by providing an intuitive, guided experience for data collection.

## Core Concept

A form is a configuration that defines:
- **Input fields** - What data to collect
- **Field behavior** - How fields interact and show/hide
- **Data source** - Which workflow executes
- **Context** - Pre-populated data available in the form

When a user fills out a form and submits it, the collected data is sent to a workflow, which processes it and returns results.

## Why Forms Matter

Workflows can be complex with many parameters and validation rules. Forms make workflows accessible to non-technical users by:

### 1. Guided Data Collection

Instead of requiring manual API calls with correct parameter names and types, forms provide:
- Clear labels explaining what data is needed
- Input validation preventing invalid data
- Help text guiding users through complex scenarios
- Sensible defaults reducing user effort

### 2. Progressive Disclosure

Not all workflows need all parameters visible at once. Forms can:
- Show only relevant fields based on previous selections
- Simplify complex workflows into digestible steps
- Reveal advanced options only when needed
- Create wizard-like experiences

### 3. Dynamic Data

Forms can populate options and values from live data sources:
- Department dropdowns load current departments
- Manager lists update based on selected department
- Pre-fill user information from directory
- Show permissions based on user role

### 4. Accessibility

Forms make workflows accessible to users without technical knowledge:
- No need to understand workflow parameter structures
- Visual feedback on required fields and errors
- Help text and instructions
- Clear form layout and organization

## Form Lifecycle

### 1. Form Load

User navigates to form URL (`/execute/form-id`):

1. Browser requests form definition
2. If startup workflow configured:
   - Form executes startup workflow
   - Results stored in `context.workflow`
   - Shows loading state to user
3. Form UI renders with fields
4. Data providers load initial options
5. Visibility expressions evaluate
6. Form displays to user

### 2. User Interaction

User fills out the form:

1. User types/selects in fields
2. `context.field` updates in real-time
3. Visibility expressions re-evaluate
4. Fields show/hide based on conditions
5. Data providers update based on field changes
6. HTML content updates with new values
7. Form validates each field as user types

### 3. Form Submission

User clicks submit:

1. Form validates all required fields
2. Client-side validation runs
3. If valid, sends data to server
4. Server validates data structure
5. Workflow executes with form data
6. Workflow returns result
7. User redirected to execution history

### 4. Workflow Execution

Workflow processes the data:

1. Receives form data as parameters
2. Can access user/organization context
3. Performs business logic
4. Returns result
5. Result stored in execution history

## Key Components

### Fields

Fields are the basic building blocks of forms. Each field:
- Collects a specific piece of data
- Has a type (text, number, dropdown, etc.)
- Can be required or optional
- May have validation rules
- Can be conditionally visible

### Data Providers

Data providers are functions that return dynamic options for dropdowns and radio buttons. They allow forms to:
- Load options from databases or APIs
- Filter options based on form inputs
- Update options in real-time
- Provide fresh data on each form load

### Startup Workflows

Optional workflows that run when form loads to populate context. They allow:
- Pre-filling user information
- Checking user permissions
- Loading organization data
- Providing conditional visibility rules

### Context

Runtime data available throughout form:
- `context.field` - User input
- `context.workflow` - Launch workflow results
- `context.query` - URL parameters

Context is available in:
- Visibility expressions
- Default values
- HTML content
- Data provider inputs

## Form Lifecycle Data Flow

```
┌─────────────────────────────────────┐
│   User navigates to form URL        │
└──────────────────┬──────────────────┘
                   │
                   ▼
      ┌────────────────────────┐
      │  Launch startup wf?    │
      │  (if configured)       │
      └────────────┬───────────┘
                   │
        ┌──────────▼──────────┐
        │ Yes: Execute wf     │
        │ No: Empty context   │
        └──────────┬──────────┘
                   │
                   ▼
      ┌────────────────────────┐
      │   Render form UI       │
      │   - Evaluate visibility │
      │   - Load data providers │
      └────────────┬───────────┘
                   │
                   ▼
      ┌────────────────────────┐
      │  User fills form       │
      │  - Type/select values  │
      │  - Re-evaluate visib.  │
      │  - Update providers    │
      │  - Update content      │
      └────────────┬───────────┘
                   │
                   ▼
      ┌────────────────────────┐
      │  User clicks submit    │
      │  - Validate required   │
      │  - Validate format     │
      └────────────┬───────────┘
                   │
                   ▼
      ┌────────────────────────┐
      │  Send to workflow      │
      │  - Form data as params │
      │  - Server validates    │
      └────────────┬───────────┘
                   │
                   ▼
      ┌────────────────────────┐
      │  Execute workflow      │
      │  - Business logic      │
      │  - Return result       │
      └────────────┬───────────┘
                   │
                   ▼
      ┌────────────────────────┐
      │  Show execution result │
      │  - Redirect to history │
      │  - Display outcome     │
      └────────────────────────┘
```

## Form vs Workflow

### Workflows

- **Purpose**: Automation and business logic
- **Users**: Developers, system integrators
- **Interface**: API, code-based
- **Data**: Passed as parameters
- **Execution**: Manual, scheduled, or triggered

### Forms

- **Purpose**: User data collection
- **Users**: End-users, business users
- **Interface**: Web UI, drag-and-drop builder
- **Data**: Collected via form fields
- **Execution**: On-demand by form submission

**Relationship**: Forms are the UI for workflows. A form is always linked to a workflow that does the actual work.

## Design Principles

### 1. Simplicity

- Keep forms focused - 5-10 fields maximum
- One workflow per form
- Clear field labels and help text
- Logical field ordering

### 2. Guidance

- Provide context about what's needed
- Use help text to explain requirements
- Show examples in placeholders
- Highlight required fields clearly

### 3. Progressive Disclosure

- Show only relevant fields
- Hide advanced options by default
- Reveal based on selections
- Reduce cognitive load

### 4. Feedback

- Real-time validation
- Clear error messages
- Visual field status
- Success confirmation

### 5. Efficiency

- Provide sensible defaults
- Pre-fill known data
- Use query parameters for pre-selection
- Minimize required input

## When to Use Forms

Use forms when you need to:
- Collect data from non-technical users
- Provide a guided user experience
- Show/hide fields based on selections
- Populate options from dynamic sources
- Pre-populate data from context
- Make workflows discoverable and accessible

## When to Use APIs

Use APIs directly when:
- Integrating with other systems
- Automating workflows
- Programmatic access needed
- Custom UI required
- High-frequency execution

Both can coexist - same workflow can be executed via form or API.

## Forms and Permissions

Forms have access control:
- **Global forms**: Available to all organizations (platform admin only)
- **Organization forms**: Only available to specific organization
- **Public forms**: Any authenticated user can execute
- **Restricted forms**: Only users with assigned access

When form executes workflow:
- Form submitter's permissions apply
- Workflow runs with form submitter's identity
- Startup workflow runs with form owner's permissions

## Best Practices

### Design Principles

1. **Start with the workflow**: Understand what parameters are needed
2. **Map to form fields**: Create fields for workflow parameters
3. **Add context**: Set up startup workflow if pre-population needed
4. **Test thoroughly**: Use preview and test modes before publishing
5. **Iterate based on feedback**: Improve form based on user experience

### Field Organization

1. **Required at top**: Put must-have fields first
2. **Related together**: Group logically related fields
3. **Progressive**: Order in the way users think about the task
4. **Hide complexity**: Use visibility to simplify

### Validation Strategy

1. **Client validation**: Quick feedback while typing
2. **Server validation**: Security and business rules
3. **Workflow validation**: Domain-specific logic
4. **Error recovery**: Allow users to fix and resubmit

### Performance

1. **Limit data providers**: Each provider adds latency
2. **Cache when possible**: Provider result caching
3. **Lazy load**: Load data only when needed
4. **Optimize images**: Use appropriate file sizes

## See Also

- [Creating Forms Tutorial](/docs/tutorials/creating-forms) - Step-by-step guide
- [Creating Forms Guide](/docs/guides/forms/creating-forms) - Detailed reference
- [Form Field Types](/docs/reference/forms/field-types) - Available field types
- [Data Providers](/docs/guides/forms/data-providers) - Dynamic options
- [Visibility Rules](/docs/guides/forms/visibility-rules) - Conditional display
