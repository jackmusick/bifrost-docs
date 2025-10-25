---
title: HTML Content Fields
description: Display dynamic HTML and JSX templates in forms with context access
---

HTML Content fields allow you to display rich, formatted content in forms with full access to form context and workflow data. These fields return **actual React components**, not just static HTML strings, giving you powerful dynamic rendering capabilities.

## Overview

HTML Content fields are:
- **Display-only** - They don't collect user input
- **Fully dynamic** - Access to all context data (workflow, fields, query params)
- **JSX-powered** - Use React JSX syntax with full Tailwind CSS support
- **Safe** - Content is automatically sanitized to prevent XSS attacks

## Adding HTML Content Fields

1. Open form builder
2. Drag **HTML Content** field from field palette
3. Configure in dialog:
   - **Label**: Display name (optional, can be empty for inline content)
   - **Content**: JSX template with context access
   - **Visibility Expression**: Show/hide based on conditions

HTML Content fields are non-interactive display-only fields - they don't collect input.

## JSX Templates

HTML Content uses JSX syntax for templates, enabling:
- Dynamic value interpolation
- Conditional rendering
- React-style className attributes
- HTML and text content

### Basic Interpolation

Insert values from context:

```jsx
<p>Welcome, {context.workflow.user_email}!</p>

<div className="p-4">
  <h3>{context.workflow.organization_name}</h3>
  <p>User ID: {context.workflow.user_id}</p>
</div>
```

### Conditional Rendering

Show content based on conditions:

```jsx
{context.workflow.is_admin ? (
  <div className="bg-blue-50 p-4 rounded">
    <p>You have administrator access.</p>
  </div>
) : (
  <div className="bg-gray-50 p-4 rounded">
    <p>You have standard user access.</p>
  </div>
)}
```

### Loops (Arrays)

Display arrays from workflow context:

```jsx
<div className="space-y-2">
  <p>Your organizations:</p>
  <ul className="list-disc ml-4">
    {context.workflow.organizations?.map((org) => (
      <li key={org.id}>{org.name}</li>
    ))}
  </ul>
</div>
```

### Combining with Form Fields

Reference current form field values:

```jsx
<div className="p-4 bg-green-50 rounded">
  <p>Email: {context.field.email}</p>
  <p>Department: {context.field.department}</p>
</div>
```

## Styling with className

Use Tailwind CSS class names (React style, not HTML style):

```jsx
<!-- Good: React className syntax -->
<div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
  <h3 className="font-bold text-lg mb-2">Title</h3>
  <p className="text-gray-700">Content</p>
</div>

<!-- Not: HTML class attribute won't work -->
<div class="p-4 bg-blue-50">...</div>
```

## Common Patterns

### Welcome Message

```jsx
<div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
  <h2 className="font-bold text-lg mb-2">Welcome!</h2>
  <p className="text-gray-700">
    Hello {context.workflow.user_name}, you're creating an account for {context.workflow.organization_name}.
  </p>
</div>
```

### Status Display

```jsx
<div className={`p-4 rounded-lg ${
  context.workflow.account_status === 'active' 
    ? 'bg-green-50 border border-green-200' 
    : 'bg-yellow-50 border border-yellow-200'
}`}>
  <p>Account Status: <strong>{context.workflow.account_status}</strong></p>
</div>
```

### Instructions Based on Selection

```jsx
{context.field.request_type === 'urgent' && (
  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
    <p className="text-red-900">
      Urgent requests require approval from your manager before submission.
    </p>
  </div>
)}
```

### List of Permissions

```jsx
{context.workflow.user_permissions && context.workflow.user_permissions.length > 0 ? (
  <div className="p-4 bg-blue-50 rounded-lg">
    <p className="font-semibold mb-2">Your Permissions:</p>
    <ul className="list-disc ml-5 space-y-1">
      {context.workflow.user_permissions.map((perm) => (
        <li key={perm}>{perm}</li>
      ))}
    </ul>
  </div>
) : (
  <div className="p-4 bg-gray-50 rounded-lg">
    <p>No permissions assigned yet.</p>
  </div>
)}
```

### Nested Organization Info

```jsx
<div className="space-y-4">
  {context.workflow.organization && (
    <div className="p-4 bg-blue-50 rounded-lg">
      <p><strong>Organization:</strong> {context.workflow.organization.name}</p>
      <p><strong>Industry:</strong> {context.workflow.organization.industry}</p>
      <p><strong>Founded:</strong> {context.workflow.organization.founded_year}</p>
    </div>
  )}
  
  {context.workflow.billing_info && (
    <div className="p-4 bg-green-50 rounded-lg">
      <p><strong>Plan:</strong> {context.workflow.billing_info.plan_name}</p>
      <p><strong>Next Billing:</strong> {context.workflow.billing_info.next_billing_date}</p>
    </div>
  )}
</div>
```

## Context Access

### Available in context.workflow

From launch workflow results:
```javascript
// Any data returned by launch workflow is available
context.workflow.user_email
context.workflow.organization_id
context.workflow.is_admin
context.workflow.user_permissions
context.workflow.departments
// ... any other data your launch workflow returns
```

### Available in context.field

Current form field values:
```javascript
// Values users have entered
context.field.email
context.field.department
context.field.selected_users
```

### Available in context.query

URL query parameters (if field enabled):
```javascript
// From: /execute/form?customer_id=123
context.query.customer_id
```

## Security

HTML Content is automatically sanitized for security:
- Script tags are removed
- Event handlers are stripped
- Only safe HTML is allowed
- XSS attacks prevented

You can safely display user data without security risks:

```jsx
<!-- Safe: User input is sanitized -->
<p>Welcome, {context.workflow.user_email}</p>
```

## Tips and Tricks

### Formatting Values

```jsx
<!-- Format numbers as currency -->
<p>Total: ${parseFloat(context.workflow.total).toFixed(2)}</p>

<!-- Format dates -->
<p>Date: {new Date(context.workflow.date).toLocaleDateString()}</p>

<!-- Capitalize text -->
<p>Status: {context.workflow.status.toUpperCase()}</p>
```

### Safe Null Checking

```jsx
<!-- Show only if value exists -->
{context.workflow.optional_field && (
  <p>Value: {context.workflow.optional_field}</p>
)}

<!-- Show with fallback -->
<p>Name: {context.workflow.name || 'Not provided'}</p>

<!-- Chain safe checks -->
<p>Email: {context.workflow.user?.email || 'No email'}</p>
```

### Conditional Classes

```jsx
<div className={`p-4 rounded-lg ${
  context.workflow.is_premium 
    ? 'bg-gold-50' 
    : 'bg-gray-50'
}`}>
  {context.workflow.is_premium ? 'Premium User' : 'Standard User'}
</div>
```

### Responsive Design

```jsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  <div className="p-4 bg-blue-50 rounded-lg">
    <p>Field 1</p>
  </div>
  <div className="p-4 bg-green-50 rounded-lg">
    <p>Field 2</p>
  </div>
</div>
```

## Capabilities and Limitations

### What You CAN Do ✅

**1. Full JSX Support**
- JSX expressions with curly braces: `{context.workflow.value}`
- Conditional rendering: `{condition && <div>...</div>}`
- Ternary operators: `{isActive ? <span>Yes</span> : <span>No</span>}`
- Array mapping: `{items.map((item, i) => <div key={i}>{item}</div>)}`

**2. Complete Tailwind CSS Access**
- All Tailwind utility classes work via `className` prop
- Responsive utilities: `md:grid-cols-2`, `lg:text-lg`
- State variants: `hover:bg-blue-600`, `focus:ring-2`
- Custom color schemes from your theme

**3. Context Data Access**
- `context.workflow.*` - Launch workflow results
- `context.field.*` - Current form field values
- `context.query.*` - URL query parameters

**4. JavaScript Operations**
- String methods: `.toUpperCase()`, `.toLowerCase()`, `.substring()`
- Number formatting: `.toFixed(2)`, `parseFloat()`
- Date formatting: `new Date().toLocaleDateString()`
- Array operations: `.map()`, `.filter()`, `.length`

### What You CANNOT Do ❌

**1. No ShadCN Component Imports**
- Cannot use `<Button>`, `<Card>`, etc. directly
- Workaround: Style regular HTML elements with Tailwind to mimic components

**2. No External Imports**
- Cannot use `import` statements
- No access to external libraries or utilities
- Only React and context are available in scope

**3. No React Hooks**
- Cannot use `useState`, `useEffect`, `useCallback`, etc.
- Content must be stateless/presentational only

**4. No Interactive State**
- Cannot create forms with inputs (use regular form fields instead)
- Cannot handle click events or user interactions
- Values must come from context only

**5. Must Return Valid JSX**
- Content must be wrapped in a container element (usually `<div>`)
- Invalid JSX shows an error message in the form

### Technical Implementation

HTML templates are:
1. Wrapped in an Immediately Invoked Function Expression (IIFE)
2. Transformed from JSX to JavaScript using Babel's React preset
3. Evaluated with only `React` and `context` in scope
4. Rendered as actual React components in the form

This means Tailwind classes work because the content is scanned during build time and classes are applied to real React elements.

## Advanced Examples

### Data Table from Context Array

Display a nice table of data from workflow context with Tailwind styling:

```jsx
<div className="overflow-hidden rounded-lg border border-gray-200">
  <table className="min-w-full divide-y divide-gray-200">
    <thead className="bg-gray-50">
      <tr>
        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
          Name
        </th>
        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
          Email
        </th>
        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
          Status
        </th>
      </tr>
    </thead>
    <tbody className="bg-white divide-y divide-gray-200">
      {context.workflow.users?.map((user, i) => (
        <tr key={i} className="hover:bg-gray-50">
          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
            {user.name}
          </td>
          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            {user.email}
          </td>
          <td className="px-6 py-4 whitespace-nowrap">
            <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
              user.status === 'active'
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
            }`}>
              {user.status}
            </span>
          </td>
        </tr>
      ))}
    </tbody>
  </table>
</div>
```

### Card Grid from Object Properties

Display nested objects as styled cards:

```jsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {context.workflow.departments?.map((dept, i) => (
    <div key={i} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6 border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{dept.name}</h3>
        <span className="px-3 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
          {dept.employee_count} people
        </span>
      </div>
      <p className="text-sm text-gray-600 mb-3">{dept.description}</p>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Manager:</span>
          <span className="font-medium text-gray-900">{dept.manager}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Budget:</span>
          <span className="font-medium text-gray-900">${dept.budget?.toLocaleString()}</span>
        </div>
      </div>
    </div>
  ))}
</div>
```

### Progress Indicator

Create a visual progress bar based on context values:

```jsx
<div className="space-y-3">
  <div className="flex items-center justify-between">
    <span className="text-sm font-medium text-gray-700">
      Profile Completion
    </span>
    <span className="text-sm font-semibold text-gray-900">
      {context.workflow.profile_completion}%
    </span>
  </div>
  <div className="w-full bg-gray-200 rounded-full h-2.5">
    <div
      className={`h-2.5 rounded-full transition-all ${
        context.workflow.profile_completion >= 75
          ? 'bg-green-500'
          : context.workflow.profile_completion >= 50
          ? 'bg-yellow-500'
          : 'bg-red-500'
      }`}
      style={{width: `${context.workflow.profile_completion}%`}}
    />
  </div>
  {context.workflow.profile_completion < 100 && (
    <p className="text-xs text-gray-500 italic">
      Complete your profile to unlock all features
    </p>
  )}
</div>
```

### Alert Banner Based on Context

Display contextual alerts with icons:

```jsx
<div className={`rounded-lg p-4 ${
  context.workflow.alert_type === 'error'
    ? 'bg-red-50 border border-red-200'
    : context.workflow.alert_type === 'warning'
    ? 'bg-yellow-50 border border-yellow-200'
    : context.workflow.alert_type === 'success'
    ? 'bg-green-50 border border-green-200'
    : 'bg-blue-50 border border-blue-200'
}`}>
  <div className="flex items-start">
    <div className="flex-shrink-0">
      <span className={`text-2xl ${
        context.workflow.alert_type === 'error' ? 'text-red-500' :
        context.workflow.alert_type === 'warning' ? 'text-yellow-500' :
        context.workflow.alert_type === 'success' ? 'text-green-500' :
        'text-blue-500'
      }`}>
        {context.workflow.alert_type === 'error' ? '⚠️' :
         context.workflow.alert_type === 'warning' ? '⚡' :
         context.workflow.alert_type === 'success' ? '✓' : 'ℹ️'}
      </span>
    </div>
    <div className="ml-3 flex-1">
      <h3 className={`text-sm font-medium ${
        context.workflow.alert_type === 'error' ? 'text-red-800' :
        context.workflow.alert_type === 'warning' ? 'text-yellow-800' :
        context.workflow.alert_type === 'success' ? 'text-green-800' :
        'text-blue-800'
      }`}>
        {context.workflow.alert_title}
      </h3>
      <p className={`mt-1 text-sm ${
        context.workflow.alert_type === 'error' ? 'text-red-700' :
        context.workflow.alert_type === 'warning' ? 'text-yellow-700' :
        context.workflow.alert_type === 'success' ? 'text-green-700' :
        'text-blue-700'
      }`}>
        {context.workflow.alert_message}
      </p>
    </div>
  </div>
</div>
```

### Timeline from Array

Create a visual timeline of events:

```jsx
<div className="flow-root">
  <ul className="-mb-8">
    {context.workflow.timeline_events?.map((event, idx) => (
      <li key={idx}>
        <div className="relative pb-8">
          {idx !== context.workflow.timeline_events.length - 1 && (
            <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" />
          )}
          <div className="relative flex space-x-3">
            <div>
              <span className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${
                event.type === 'completed' ? 'bg-green-500' :
                event.type === 'in-progress' ? 'bg-blue-500' :
                'bg-gray-400'
              }`}>
                <span className="text-white text-xs font-bold">
                  {idx + 1}
                </span>
              </span>
            </div>
            <div className="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5">
              <div>
                <p className="text-sm font-medium text-gray-900">{event.title}</p>
                <p className="text-sm text-gray-500">{event.description}</p>
              </div>
              <div className="whitespace-nowrap text-right text-sm text-gray-500">
                <time>{event.date}</time>
              </div>
            </div>
          </div>
        </div>
      </li>
    ))}
  </ul>
</div>
```

## Returning HTML from Workflows

In addition to HTML Content fields in forms, workflows can return HTML directly:

```python
@workflow(name="generate_report")
async def generate_report(context: ExecutionContext):
    """Generate and return HTML report."""

    report_html = """
    <div style="padding: 20px; background: #f5f5f5;">
        <h1>Report Title</h1>
        <p>Generated on {date}</p>
    </div>
    """

    return {
        "resultType": "html",
        "result": report_html
    }
```

When execution completes, the result shows as rendered HTML.

## Troubleshooting

**HTML not displaying**
- Check JSX syntax (className not class)
- Verify context properties exist (use Info button to check)
- Check for null/undefined values
- Look for JavaScript errors in browser console

**Values showing as undefined**
- Use context preview to see available properties
- Check spelling of property names (case-sensitive)
- Verify launch workflow is configured and running
- Check if property is nested (use safe navigation: `?.`)

**Styling not applied**
- Use className (React style), not class attribute
- Check Tailwind CSS class names are valid
- Verify no conflicting CSS
- Use browser dev tools to inspect element

**Expression evaluation error**
- Check JSX syntax
- Verify no unmatched braces
- Check for missing commas in objects/arrays
- Look for undefined variables

## See Also

- [Form Context Object](/docs/reference/forms/context-object) - Full context reference
- [Visibility Rules](/docs/guides/forms/visibility-rules) - Conditional rendering patterns
- [Startup Workflows](/docs/guides/forms/startup-workflows) - Setting up context data
