---
title: Forms Troubleshooting
description: Diagnose and fix form field and submission issues
---

# Forms Troubleshooting

Forms provide the user interface for executing workflows in Bifrost. This guide helps you diagnose and fix form-specific issues.

## Form Not Loading

**Symptom**: Form page shows "Loading..." but never finishes, or shows blank form

### Check 1: Form Exists

```bash
# Check that the form is discoverable
curl http://your-bifrost.com/api/forms

# Response should include:
{
  "forms": [
    {"id": "form-123", "name": "My Form", ...}
  ]
}

# If your form is missing:
# - Check it was saved
# - Verify it's not in draft state
# - Check you have permission to view it
```

### Check 2: Check Browser Console

The form load error is often in browser console:

```
1. Open Developer Tools (F12)
2. Go to Console tab
3. Look for red errors like:
   - "Failed to fetch form: 404"
   - "Unauthorized"
   - "Network error"
```

### Check 3: Form Permissions

```
✅ You are member of the organization that owns the form
✅ You have "View Forms" permission
✅ Form is published (not draft)

❌ You're viewing as different organization
❌ Form is draft/unpublished
❌ You don't have permission
```

### Check 4: Check API Health

```bash
# Verify Bifrost API is running
curl http://your-bifrost.com/api/health

# Should return:
{"status": "healthy"}

# If not:
# See [Azure Functions Troubleshooting](/docs/troubleshooting/azure-functions)
```

## Field Not Displaying

**Symptom**: Form loads but expected field is missing

### Check 1: Field Configuration

In form builder, verify the field:

```
Form Settings → Fields

Required:
✅ Field has name
✅ Field has type (text, email, select, etc.)
✅ Field is not hidden (check visibility rules)

Common issues:
❌ Field is hidden by default visibility rule
❌ Field type is invalid
❌ Field name is empty
```

### Check 2: Visibility Rules

Fields can be hidden based on conditions:

```
Form editor → Field → Visibility

Field may be hidden if:
- Visibility rule: "Hidden unless field X equals Y"
- Previous field value doesn't match condition
- Field requires feature not enabled

Example:
- "License" field only visible if "Assign License" is checked
- If checkbox is unchecked, field is hidden (not removed from form)
```

### Check 3: Data Provider Failure

If field uses a data provider dropdown:

```
Field type: Select
Data Provider: "get_available_licenses"

If dropdown is empty:
1. Provider returned empty list
2. Provider threw error
3. User doesn't have permission for that provider
4. Data provider doesn't exist

See: [Data Provider Issues](#data-provider-issues)
```

## Field Not Saving Value

**Symptom**: You enter a value in a field, submit form, but value doesn't reach workflow

### Check 1: Field Name Matches Workflow Parameter

```python
# Form field name must match workflow parameter name

# Form field: "email"
# ✅ Workflow parameter: email
@workflow(name="test")
@param("email", type="email")
async def test(context, email):
    pass

# ❌ Workflow parameter: recipient_email
@param("recipient_email", type="email")
async def test(context, recipient_email):  # Different name!
    pass
```

### Check 2: Field Type Matches Parameter Type

```python
# Form field type should match workflow parameter type

# ❌ Form field type: "text" but should be "email"
@param("email", type="email")  # Type mismatch

# ✅ Form field type: "email"
@param("email", type="email")

# Mismatched types can cause:
# - Validation rejecting input
# - Value not passed to workflow
# - Type conversion errors
```

### Check 3: Check Form Validation Errors

When you submit, validation errors appear:

```
Form shows: "Email is invalid"
or
"This field is required"

This means:
- Field has validation rule that failed
- Value didn't pass validation
- Can't submit until fixed
```

**Fix validation errors by:**
1. Correcting your input (e.g., valid email format)
2. Checking field requirements (red asterisk = required)
3. Asking form admin to relax validation if too strict

## Data Provider Issues

**Symptom**: Dropdown shows "Loading..." or is empty, or shows error

### Check 1: Data Provider Exists

Data providers power dynamic dropdowns:

```bash
# List available data providers
curl http://your-bifrost.com/api/data-providers

# Should include:
{
  "dataProviders": [
    {"name": "get_available_licenses", ...}
  ]
}

# If expected provider is missing:
# - Check workflow file in /home or /platform
# - Verify @data_provider decorator is applied
# - Check for import errors (see [Workflow Engine Troubleshooting](/docs/troubleshooting/workflow-engine))
```

### Check 2: Data Provider Has Data

Data providers must return data in specific format:

```
Expected response:
{
  "options": [
    {"label": "Option 1", "value": "opt1"},
    {"label": "Option 2", "value": "opt2"}
  ]
}

If dropdown is empty:
- Provider returned empty list (no options available)
- Provider threw an error
- User doesn't have permission to call provider
```

### Check 3: Data Provider Inputs

Some data providers need input parameters:

```
Form field configuration:
- Data Provider: "get_licenses"
- Provider Inputs:
  - "license_type": "static" = "Microsoft365"
  - "filter_available": "static" = true

If dropdown shows error:
- Check required inputs are configured
- Verify input values match parameter types
- Check data provider actually needs those inputs
```

**Check by looking at the data provider code:**

```python
@data_provider(name="get_licenses")
@param("license_type", type="string", required=True)  # This is required!
@param("filter_available", type="bool", default_value=False)
async def get_licenses(context, license_type: str, filter_available: bool = False):
    pass

# Form must provide "license_type" or dropdown will fail
```

### Check 4: Provider Called During Form Load

Data providers are called when form loads:

```
Form load flow:
1. User opens form
2. For each field with data provider:
   - Call provider with configured inputs
   - Display options in dropdown
3. Form shows loading state during this
```

**If this is slow:**
- Provider is making slow API calls
- Reduce cache_ttl_seconds to refresh more often
- Or increase it (data is stale)

### Solution: Check Provider Output

Test the data provider directly:

```bash
# Call data provider API
curl -X POST http://your-bifrost.com/api/data-providers/get_licenses \
  -H "Content-Type: application/json" \
  -d '{
    "license_type": "Microsoft365"
  }'

# Should return:
{
  "provider": "get_licenses",
  "options": [
    {"label": "E3", "value": "SPE_E3"},
    {"label": "E5", "value": "SPE_E5"}
  ]
}
```

## Form Submission Fails

**Symptom**: Click submit but get error instead of executing workflow

### Check 1: Required Fields Filled

All fields marked with red asterisk (*) are required:

```
❌ Form shows: "Email is required"
   Fix: Fill in email field

✅ All required fields have values
```

### Check 2: Values Pass Validation

Fields have validation rules:

```
❌ Form shows: "Email must be valid format"
   Fix: Enter valid email (name@domain.com)

❌ Form shows: "Number must be between 1 and 100"
   Fix: Enter valid number in range

✅ All values match validation rules
```

### Check 3: Check Form Permissions

You need permission to execute the target workflow:

```
✅ You have "Execute Workflows" permission
✅ Organization has access to the workflow

❌ Permission denied
   - Ask admin to grant "Execute Workflows" permission
   - Or check you're executing in correct organization
```

### Check 4: Check Workflow Status

The workflow being executed might have issues:

```bash
# Check if workflow exists and is discoverable
curl http://your-bifrost.com/api/discovery

# Should include workflow being executed
# If missing:
# - Workflow file is missing or broken
# - Check [Workflow Engine Troubleshooting](/docs/troubleshooting/workflow-engine)
```

### Check 5: Server Error During Submission

If form submits but shows "Error executing workflow":

```bash
# Check API logs for error details
1. Azure Portal → Function App → Monitoring → Log Stream
2. Look for error messages during form submission
3. Common errors:
   - OAuth token expired
   - External API unreachable
   - Workflow code threw exception
```

## Form Startup Fails

**Symptom**: "Error loading form configuration" or similar startup error

### Check 1: Form Schema Valid

Form must have valid structure:

```json
✅ Valid form:
{
  "id": "form-123",
  "name": "Create User",
  "formSchema": {
    "fields": [
      {"name": "email", "type": "email", "required": true}
    ]
  }
}

❌ Invalid: Missing required fields
{
  "name": "Create User",
  "formSchema": {}  // Missing fields array
}
```

### Check 2: Workflow Exists

Form must reference an existing workflow:

```
Form configured to execute: "create_user"

If error on form load:
- Workflow "create_user" doesn't exist
- Workflow was deleted
- Wrong workflow name in form config

Check by:
curl http://your-bifrost.com/api/discovery | grep create_user
```

### Check 3: All Data Providers Exist

Each field's data provider must exist:

```
Field "license":
  Data Provider: "get_available_licenses"

If this provider doesn't exist:
  Form won't load
  Workflow not discovered
  Check [Workflow Engine Troubleshooting](/docs/troubleshooting/workflow-engine)
```

### Check 4: No Circular Dependencies

Data providers can't depend on themselves:

```
❌ Bad: Circular dependency
Field "license" → Data Provider "get_licenses" → Needs Field "org" → Also has provider...

If this happens:
- Form won't load
- Error: "Circular dependency detected"
- Refactor data provider inputs
```

## Dynamic Form Behavior Issues

### Fields Not Showing/Hiding Based on Conditions

**Symptom**: Conditional field visibility isn't working

#### Check 1: Visibility Rule Syntax

```
Field visibility rule example:
IF field "create_user" = true
THEN show field "license"
ELSE hide field "license"

If not working:
- Check reference field name is correct
- Check condition value is correct
- Check reference field exists on form
```

#### Check 2: Field Dependency Order

Referenced field must come before dependent field:

```
Form field order:
1. "create_user" (checkbox)
2. "license" (select) ← depends on "create_user"

❌ If "license" comes before "create_user":
   - Visibility rule can't find "create_user"
   - Shows validation error

✅ Reorder fields so dependencies come first
```

### Field Values Not Populating from Launch Workflow

**Symptom**: Form doesn't pre-fill values from launch workflow

#### Check 1: Launch Workflow Output Format

Launch workflow must return data in correct format:

```python
# ✅ Correct: Returns dict with field names as keys
@workflow(name="launch_create_user")
async def launch_create_user(context):
    return {
        "email": "user@example.com",
        "name": "John Smith",
        "license": "SPE_E5"
    }

# ❌ Wrong: Wrong format
@workflow(name="launch_create_user")
async def launch_create_user(context):
    return ["user@example.com", "John Smith"]  # List instead of dict
```

#### Check 2: Field Names Match Output Keys

```python
# Launch workflow returns:
{
    "email": "user@example.com"
}

# Form fields must have exact name:
✅ Field name: "email"     (matches)
❌ Field name: "user_email"  (doesn't match)

Field names are case-sensitive!
```

#### Check 3: Check Startup Handler

Form must have a startup handler that receives launch data:

```
Form Settings → Startup Handler

If configured, startup handler receives data from launch workflow
If not configured, launch data is ignored
```

## Advanced Troubleshooting

### Debug Form Data

Check what data was submitted:

```
Workflow Execution History → [Click execution]

Variables section shows:
- All submitted form values
- In the order they were submitted
- With exact values (for debugging)
```

### Check Network Traffic

For form submission issues, check network tab:

```
1. Open Developer Tools (F12)
2. Go to Network tab
3. Fill out and submit form
4. Look for POST request to /api/workflows/...

Check:
✅ Request sent with correct data
✅ Response status is 200 (success)
❌ Response shows error (4xx, 5xx status)
```

### Test Form Without API

For local development, test directly:

```bash
# Test workflow execution directly
curl -X POST http://localhost:7071/api/workflows/my_workflow \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org" \
  -H "x-functions-key: test" \
  -d '{
    "email": "user@example.com",
    "name": "John Smith"
  }'

# If this works but form fails:
# Problem is with form, not workflow
```

## Quick Reference

| Issue | Most Likely Cause | Fix |
|-------|---|---|
| Form won't load | API down or permission denied | Check API health, verify permissions |
| Field not showing | Hidden by visibility rule | Check visibility conditions |
| Dropdown empty | Data provider returned no data | Check provider exists and has data |
| Submit fails | Required field missing or invalid | Fill all required fields, match validation |
| Workflow error after submit | Workflow code threw exception | Check execution logs |
| Values not prefilled | Launch workflow output format wrong | Check launch workflow returns dict with field names |
| Data provider slow | Provider making slow API calls | Check data provider efficiency |

## Getting Help

- **Form Logs**: Check browser console (F12 → Console tab)
- **API Logs**: Azure Portal → Function App → Log Stream
- **Execution Details**: Workflows → Execution History → [Click execution]
- **Provider Test**: Call provider API directly to isolate issue

## Related Topics

- **[Forms Concept](/docs/concepts/forms)** - How forms work
- **[Workflow Engine Troubleshooting](/docs/troubleshooting/workflow-engine)** - Workflow execution issues
- **[Data Provider Issues](/docs/troubleshooting/workflow-engine#data-provider-issues)** - Provider-specific issues
