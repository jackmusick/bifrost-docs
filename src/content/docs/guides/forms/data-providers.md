---
title: Use Data Providers
description: Guide to creating and using data providers for dynamic form options
---

Data providers dynamically populate form field options from external data sources, enabling forms to show current, accurate information without manual updates.

## What Are Data Providers?

Data providers are Python functions decorated with `@data_provider` that return a list of options for dropdowns and radio buttons.

They allow forms to:
- Load options from databases, APIs, or integrations
- Provide fresh data each time form loads
- Filter options based on form inputs
- Cache results to optimize performance

## Creating Data Providers

Data providers are defined in your workflow files using the `@data_provider` decorator.

### Basic Data Provider

```python
from bifrost import data_provider, ExecutionContext

@data_provider(name="get_departments")
async def get_departments(context: ExecutionContext):
    """Get list of departments."""
    return [
        {"label": "Engineering", "value": "eng"},
        {"label": "Sales", "value": "sales"},
        {"label": "Marketing", "value": "marketing"},
    ]
```

### Provider with Integration

```python
@data_provider(name="get_active_users")
async def get_active_users(context: ExecutionContext):
    """Get active users from Microsoft Graph."""
    graph = context.get_integration("msgraph")
    users_response = await graph.get_users(filter="accountEnabled eq true")
    
    return [
        {
            "label": user.display_name,
            "value": user.id,
            "metadata": {"email": user.mail}
        }
        for user in users_response.value
    ]
```

### Provider with Parameters

Some providers need input parameters (e.g., "get_managers" needs a department):

```python
@data_provider(name="get_managers")
async def get_managers(
    context: ExecutionContext,
    department_id: str  # Parameter from form
):
    """Get managers in a department."""
    # Fetch managers for the department
    managers = await fetch_managers(context, department_id)
    
    return [
        {"label": manager.name, "value": manager.id}
        for manager in managers
    ]
```

Provider parameters can be provided by forms in three ways:
1. **Static**: Hard-coded value in form configuration
2. **Field Reference**: Value from another form field
3. **Expression**: JavaScript expression evaluated in browser

### Provider with Caching

```python
@data_provider(
    name="get_licenses",
    cache_ttl_seconds=300  # Cache for 5 minutes
)
async def get_licenses(context: ExecutionContext):
    """Get available Microsoft 365 licenses (cached)."""
    graph = context.get_integration("msgraph")
    skus = await graph.get_subscribed_skus()
    
    return [
        {
            "label": f"{sku.sku_part_number} ({sku.prepaid_units.enabled} available)",
            "value": sku.sku_id
        }
        for sku in skus.value
    ]
```

Caching prevents excessive API calls while keeping data relatively fresh.

## Using Providers in Forms

### Adding a Data Provider Field

1. Create a **Dropdown** or **Radio** field
2. In field configuration, select **Data Provider** mode
3. Choose the provider from the list
4. Save field

### Handling Provider Parameters

If your provider has required parameters:

1. Click **Data Provider Inputs** in field configuration
2. For each required parameter, choose configuration mode:

#### Static Mode

Hard-coded value (same for all users):

- **Parameter**: `environment`
- **Mode**: Static
- **Value**: `production`

Use for configuration values that don't change per form instance.

#### Field Reference Mode

Value from another form field (changes per user):

- **Parameter**: `department_id`
- **Mode**: Field Reference
- **Field Name**: `department`

The provider is called whenever the referenced field changes, allowing cascading dropdowns (e.g., manager list updates when department changes).

#### Expression Mode

JavaScript expression using form context:

- **Parameter**: `organization_id`
- **Mode**: Expression
- **Expression**: `context.workflow.organization_id`

Evaluate expressions at form load time to pass workflow data to providers.

Example: Pre-filter users by organization from launch workflow:

```javascript
context.workflow.organization_id
```

Or get current year for date filtering:

```javascript
new Date().getFullYear().toString()
```

### Field Dependencies

When a data provider input uses **Field Reference** mode, that field becomes a dependency. If the referenced field changes, the provider is called again.

**Example: Cascading Dropdowns**

```
1. Department dropdown → calls get_departments
2. Manager dropdown → calls get_managers with department_id from field 1
3. When user changes department → manager list updates automatically
```

## Option Structure

Data providers return options with this structure:

### Minimum Required

```python
{
    "label": "Display Text",
    "value": "internal_value"
}
```

### With Metadata

```python
{
    "label": "Engineering",
    "value": "eng",
    "metadata": {
        "budget_code": "PROJ-001",
        "manager": "John Smith",
        "description": "Product Engineering"
    }
}
```

Metadata is available in visibility expressions if you need it:

```javascript
// Access metadata (if available in provider output)
context.field.department_metadata?.budget_code
```

## Provider Lifecycle

### Loading

1. Form loads
2. For each dropdown with data provider:
   - Evaluate data provider inputs
   - Check if all required parameters are available
   - Call provider API
3. Options populate in dropdown
4. Loading state shows while fetching

### Caching

If provider has `cache_ttl_seconds` set:
- Results cached in memory for TTL duration
- Subsequent form loads return cached data
- Reduces API calls and improves performance
- Cache invalidates after TTL expires

### Field Reference Updates

When a field with data provider input (Field Reference mode) changes:
1. Form detects field value changed
2. Evaluates if data provider should be called
3. Calls provider with new field value
4. Updates dropdown options

## Error Handling

### Provider Not Found

If form references non-existent provider:
- Form validation error when creating/updating form
- Shows in form builder: "Unknown data provider 'name'"

### Provider Parameters Missing

If required parameters not provided:
- Options list appears empty
- Form prevents field submission
- No error shown to user (loads silently)

### Provider Execution Error

If provider function raises exception:
- Error logged on server
- Dropdown shows "No options available"
- Form can still be submitted (field not required)

To debug:
1. Check workflow logs
2. Verify provider parameters are correct
3. Check integration configurations
4. Test provider manually in workflow

## Performance Considerations

### Optimize Provider Calls

1. **Use caching**: Set `cache_ttl_seconds` for static data
2. **Limit fields**: Each provider field adds latency
3. **Use parameters**: Filter in provider, not in form
4. **Lazy load**: Load only when field becomes visible

### Data Provider Best Practices

```python
# Good: Efficient provider with caching
@data_provider(name="get_departments", cache_ttl_seconds=3600)
async def get_departments(context: ExecutionContext):
    """Get departments (cached for 1 hour)."""
    # Single API call, cached
    return await fetch_departments(context)

# Avoid: Calling provider multiple times per form
# Each form load calls provider even if just browsing
```

### Form Configuration Best Practices

1. **Avoid cascading** beyond 2-3 levels
2. **Use static options** for small, fixed lists
3. **Cache expensive providers** (Graph API, database queries)
4. **Test with production data** to identify bottlenecks

## Common Patterns

### Status Selection with Filtering

```python
@data_provider(name="get_ticket_statuses")
async def get_ticket_statuses(
    context: ExecutionContext,
    ticket_type: str
):
    """Get available statuses for ticket type."""
    statuses = {
        "bug": ["open", "in_progress", "resolved", "closed"],
        "feature": ["open", "planned", "in_progress", "done"],
        "support": ["open", "waiting_customer", "resolved", "closed"]
    }
    
    return [
        {"label": status.title(), "value": status}
        for status in statuses.get(ticket_type, [])
    ]
```

Form setup:
- **ticket_type** field (dropdown with static options)
- **status** field with provider `get_ticket_statuses`
  - Provider Input: `ticket_type` (Field Reference to ticket_type field)

### User Selection by Organization

```python
@data_provider(name="get_org_users")
async def get_org_users(
    context: ExecutionContext,
    organization_id: str
):
    """Get users in organization."""
    users = await fetch_users_by_org(context, organization_id)
    
    return [
        {"label": user.name, "value": user.id}
        for user in users
    ]
```

Form setup:
- **organization** field (selected via launch workflow context)
- **assigned_user** field with provider `get_org_users`
  - Provider Input: `organization_id` (Expression: `context.workflow.organization_id`)

### Region-Based Selection

```python
@data_provider(name="get_region_cities")
async def get_region_cities(
    context: ExecutionContext,
    region: str
):
    """Get cities in region."""
    cities = REGION_CITIES.get(region, [])
    
    return [
        {"label": city, "value": city.lower().replace(" ", "_")}
        for city in cities
    ]
```

Form setup:
- **region** field (radio with static options)
- **city** field with provider `get_region_cities`
  - Provider Input: `region` (Field Reference to region field)

## Troubleshooting

**Options not loading**
- Check provider exists in registry
- Verify all required parameters provided
- Check server logs for provider errors
- Test provider directly in workflow

**Options load very slowly**
- Add caching to provider
- Optimize database queries
- Consider pagination
- Check network latency

**Options change unexpectedly**
- Check caching isn't stale
- Verify provider logic
- Check if field changes trigger re-load
- Look at provider error logs

**Field Reference not working**
- Verify referenced field exists
- Check field name spelling (case-sensitive)
- Ensure provider parameter name matches
- Verify referenced field is visible

## See Also

- [Creating Forms](/docs/guides/forms/creating-forms) - How to use providers in forms
- [Form Field Types](/docs/reference/forms/field-types) - Dropdown and radio configuration
- [Form Context](/docs/reference/forms/context-object) - Context structure for expressions
