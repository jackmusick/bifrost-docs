---
title: Configure Startup Workflows
description: Set up launch workflows to pre-populate form context on load
---

Startup workflows (also called launch workflows) run when a form loads to fetch initial context data. This data becomes available throughout the form for visibility rules, default values, and HTML templates.

## What Are Startup Workflows?

A startup workflow is an optional workflow that executes when the form page loads (before showing the form). Results are stored in `context.workflow.*` for the entire form session.

Common uses:
- Get current user information
- Fetch organization details
- Check user permissions
- Load initial data for pre-population
- Determine form visibility
- Provide default values

## Setting Up a Startup Workflow

### Step 1: Configure in Form Settings

1. Open form in builder
2. In right panel, find **Launch Workflow** section
3. Select workflow from dropdown
4. Optionally set **Default Launch Parameters**

### Step 2: Handle Required Parameters

If your startup workflow has required parameters, provide them by:

1. **Default Launch Parameters**: Hard-coded values
2. **Query Parameters**: Allow passing via URL
3. **Form Fields**: Combine approaches

#### Using Default Parameters

For parameters with static values:

```json
{
  "include_permissions": true,
  "environment": "production"
}
```

These values are used when no URL parameter provided.

#### Using Query Parameters

For parameters that vary per request:

1. Create form field with same name as parameter
2. Enable **Allow as Query Parameter** on field
3. Field name automatically added to allowed params
4. Pass value in URL: `/execute/form?user_id=123`

**Example**: get_user_context needs user_id:

```
Form field: user_id (hidden, text input)
Allow as Query Parameter: enabled
URL: /execute/form?user_id=123
```

#### Combining Approaches

Use defaults with query parameter overrides:

```
Default Parameters: {"org_id": "org-default"}
Query Parameters: org_id (can override via URL)
URL: /execute/form?org_id=org-custom
```

## Startup Workflow Examples

### Basic User Context

```python
@workflow(name="get_user_context")
async def get_user_context(context: ExecutionContext):
    """Get current user information."""
    return {
        "user_id": context.user_id,
        "user_email": context.email,
        "user_name": context.name,
        "organization_id": context.org_id,
        "organization_name": context.org_name,
        "is_admin": context.is_platform_admin,
    }
```

Form setup:
- Launch Workflow: `get_user_context`
- No parameters needed
- Use results in visibility: `context.workflow.is_admin === true`

### Parameterized Context

```python
@workflow(name="load_customer_data")
async def load_customer_data(context: ExecutionContext, customer_id: str):
    """Load customer data for survey form."""
    customer = await get_customer(context, customer_id)
    
    return {
        "customer_name": customer.name,
        "purchase_date": customer.last_purchase,
        "customer_tier": customer.tier,
        "email": customer.email,
    }
```

Form setup:
- Launch Workflow: `load_customer_data`
- Parameter: `customer_id`
  - From query param: create form field, enable "Allow as Query Param"
  - URL: `/execute/form?customer_id=12345`
- Use in HTML content: `Welcome back, {context.workflow.customer_name}!`

### With Permissions Check

```python
@workflow(name="get_user_access")
async def get_user_access(context: ExecutionContext):
    """Get user permissions for form."""
    permissions = await fetch_user_permissions(context, context.user_id)

    return {
        "user_id": context.user_id,
        "is_admin": "admin" in permissions,
        "can_approve_budget": "budget_approver" in permissions,
        "can_manage_users": "user_manager" in permissions,
        "departments": await get_accessible_departments(context, context.user_id),
    }
```

Form setup:
- Use for conditional field display
- Field visibility: `context.workflow.can_approve_budget === true`
- Data provider inputs: departments list from context

### Returning Lists

```python
@workflow(name="get_organizations")
async def get_organizations(context: ExecutionContext):
    """Get list of organizations."""
    orgs = await fetch_user_organizations(context)
    
    return {
        "organizations": [
            {
                "id": org.id,
                "name": org.name,
                "role": org.user_role
            }
            for org in orgs
        ],
        "primary_org_id": orgs[0].id if orgs else None,
    }
```

Form setup:
- Display in HTML content: Loop through `context.workflow.organizations`
- Use for pre-population: Set default value to `context.workflow.primary_org_id`

## Using Startup Workflow Results

### In Visibility Expressions

```javascript
// Show field only if user is admin
context.workflow.is_admin === true

// Show field only if user has permission
context.workflow.can_approve_budget === true

// Show based on user tier
context.workflow.customer_tier === 'premium'
```

### In Default Values

Pre-populate fields with startup workflow data:

```javascript
// Set email field to current user email
context.workflow.user_email

// Set organization to user's primary org
context.workflow.primary_org_id

// Set checkbox based on workflow data
context.workflow.has_opted_in
```

### In HTML Content

Display dynamic content:

```jsx
<div className="p-4 bg-blue-50 rounded">
  <p>Welcome, {context.workflow.user_name}!</p>
  <p>Organization: {context.workflow.organization_name}</p>
</div>
```

### As Data Provider Input

Pass workflow data to data providers:

```
Field: manager_dropdown
Data Provider: get_managers
Provider Input:
  - Parameter: organization_id
  - Mode: Expression
  - Expression: context.workflow.organization_id
```

## Testing Startup Workflows

### Test in Form Builder

1. Click **Play** button next to Launch Workflow
2. Enter any required parameters
3. Click **Execute**
4. View results in context preview
5. Use to verify visibility expressions work correctly

### Debug with Context Viewer

1. Click **Info** button in form builder
2. Scroll to `context.workflow` section
3. Verify expected data is present
4. Check property names and values
5. Use for writing expressions

## Error Handling

### Startup Workflow Not Configured

Form loads without startup workflow:
- `context.workflow` is empty object
- Visibility expressions can't access workflow data
- HTML content won't have workflow values

Solution: Configure launch workflow in form settings

### Startup Workflow Has Required Parameters

Form won't load until parameters provided:
1. Add default values in **Default Launch Parameters**
2. Create form fields with same names
3. Enable **Allow as Query Parameter**
4. Pass values via URL

### Startup Workflow Fails

If startup workflow throws error:
- Form shows loading state with error message
- Check workflow logs for error details
- Verify parameters are correct
- Check integrations and data sources

## Best Practices

### Keep Startup Workflows Fast

Minimize startup time since it blocks form rendering:

```python
# Good: Efficient query
@workflow(name="get_user_context")
async def get_user_context(context):
    # Single call, cached
    return {"user_id": context.user_id}

# Avoid: Multiple expensive calls
@workflow(name="get_all_data")
async def get_all_data(context):
    # Multiple API calls, slow
    users = await fetch_users()
    orgs = await fetch_orgs()
    perms = await fetch_permissions()
    # ...
```

### Handle Missing Data Gracefully

```python
@workflow(name="load_optional_data")
async def load_optional_data(context, id: str):
    """Load data with fallbacks."""
    data = await fetch_data(context, id)
    
    return {
        "found": data is not None,
        "value": data.value if data else None,
        "default": "N/A" if not data else data.display_name,
    }
```

### Document Complex Startup Logic

Add comments explaining what's returned:

```python
@workflow(name="get_form_context")
async def get_form_context(context):
    """
    Get context for form initialization.
    
    Returns:
        - user_id: Current user ID
        - is_admin: Whether user has admin role
        - departments: List of departments user can access
        - permissions: Array of permission strings
    """
```

### Combine with Default Parameters

Use sensible defaults for optional parameters:

```
Default Parameters:
{
  "include_archived": false,
  "limit": 50,
  "sort_by": "name"
}
```

Allows overriding via query: `/execute/form?include_archived=true`

## Common Patterns

### Pre-fill Survey Form

```python
@workflow(name="load_customer_for_survey")
async def load_customer_for_survey(context, customer_id: str):
    """Load customer for feedback survey."""
    customer = await get_customer(context, customer_id)
    
    return {
        "customer_name": customer.name,
        "purchase_date": customer.last_purchase.strftime("%Y-%m-%d"),
        "product_name": customer.last_product.name,
        "is_enterprise": customer.tier == "enterprise",
    }
```

Form setup:
- Launch: `load_customer_for_survey`
- Query param: `customer_id`
- URL: `/execute/form?customer_id=123`
- HTML: Welcome message with customer name
- Visibility: Show enterprise feedback field if `context.workflow.is_enterprise`

### Role-Based Field Display

```python
@workflow(name="get_user_roles")
async def get_user_roles(context):
    """Get roles for conditional field display."""
    roles = await fetch_roles(context, context.user_id)

    return {
        "is_manager": "manager" in roles,
        "is_budget_owner": "budget_owner" in roles,
        "is_system_admin": "admin" in roles,
        "team_size": await get_team_size(context, context.user_id) if "manager" in roles else 0,
    }
```

Form visibility rules:
- Team size field: `context.workflow.is_manager === true`
- Budget approval: `context.workflow.is_budget_owner === true`
- System fields: `context.workflow.is_system_admin === true`

### Cascading Selection

```python
@workflow(name="get_initial_selection")
async def get_initial_selection(context, region: str):
    """Get initial data based on region."""
    cities = await fetch_cities_in_region(context, region)
    
    return {
        "region": region,
        "cities": [{"id": c.id, "name": c.name} for c in cities],
        "recommended_city": cities[0].name if cities else None,
    }
```

Form setup:
- Region selection field (dropdown with data provider)
- Launch workflow: `get_initial_selection` with region from query param
- City field gets pre-populated from `context.workflow.recommended_city`

## See Also

- [Creating Forms](/docs/guides/forms/creating-forms) - Form builder interface
- [Visibility Rules](/docs/guides/forms/visibility-rules) - Using context in expressions
- [HTML Content](/docs/guides/forms/html-content) - Displaying workflow data
- [Form Context](/docs/reference/forms/context-object) - Complete context reference
