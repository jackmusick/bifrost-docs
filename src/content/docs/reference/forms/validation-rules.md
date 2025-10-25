---
title: Form Validation Rules
description: Client-side and server-side form validation in Bifrost
---

Bifrost forms provide multiple layers of validation to ensure data quality.

## Validation Layers

### Layer 1: Client-Side Validation

Happens in user's browser before submission:
- **Required field validation**
- **Format validation** (email, number ranges)
- **Type validation** (email, number)
- **Custom pattern matching**

Provides immediate feedback to users.

### Layer 2: Server-Side Validation

Happens on server after form submission:
- **Business logic validation**
- **Database constraint checking**
- **Permission verification**
- **Cross-field validation**

Ensures data integrity regardless of client.

### Layer 3: Workflow Validation

Happens in workflow execution:
- **Domain-specific validation**
- **Integration validation**
- **Custom validation logic**

Best for complex business rules.

## Client-Side Validation

Client validation runs automatically for all field types.

### Required Field Validation

Fields marked as required must be filled:

```
Field Configuration:
- Required: true

Validation: Field cannot be empty
Error: "This field is required"
```

When form is submitted:
1. All required fields checked
2. Submit button disabled if any missing
3. User sees error on first submit

### Format Validation

Different field types have automatic format validation:

#### Email Field

```
Email Format Validation:
- Must contain @
- Example: user@example.com
- Invalid: username, user@, @example.com

Error: "Please enter a valid email address"
```

#### Number Field

```
Number Format Validation:
- Must be numeric
- Supports: integers, decimals
- Invalid: abc, 12x

Error: "Please enter a valid number"
```

#### Date & Time Field

```
Date Format Validation:
- Must be valid date
- Calendar picker ensures format
- Returns: ISO 8601 (YYYY-MM-DDTHH:MM:SS)

Error: Prevents invalid date selection
```

### File Upload Validation

File fields have automatic validation:

#### File Type Validation

```
Configuration:
- Allowed Types: .pdf, .jpg, .png

Validation:
- Checks file extension
- Checks MIME type
- Rejects non-matching files

Error: "File type not allowed. Allowed: PDF, JPG, PNG"
```

#### File Size Validation

```
Configuration:
- Max Size MB: 5

Validation:
- File size in MB <= max
- Real-time check during upload

Error: "File too large. Maximum: 5 MB"
```

#### Multiple Files Validation

```
Configuration:
- Multiple Files: true/false

Validation:
- If false: Only one file allowed
- If true: Multiple files allowed

Error: (if false) "Only one file allowed"
```

### Visual Feedback

Client validation provides:
- **Real-time feedback**: As user types
- **Submit prevention**: Button disabled if invalid
- **Error messages**: Clear, specific messages
- **Field highlighting**: Red border on required empty fields

## Server-Side Validation

Server validates after form submission.

### Built-In Server Validation

The Bifrost API validates:

1. **Required parameters**: All required form fields present
2. **Data structure**: Response format matches schema
3. **Type checking**: Values match expected types
4. **Required field presence**: No null required fields

### Custom Validation in Workflows

Workflows can implement domain-specific validation:

```python
@workflow(name="create_user")
async def create_user(context: ExecutionContext, email: str, age: int):
    """Create user with validation."""
    
    # Check email not already used
    existing = await find_user_by_email(context, email)
    if existing:
        raise ValidationError(
            "Email already in use",
            field="email"
        )
    
    # Check age >= 18
    if age < 18:
        raise ValidationError(
            "Must be 18 or older",
            field="age"
        )
    
    # Create user
    user = await create_user_in_db(context, email, age)
    return {"user_id": user.id}
```

Error is caught and shown to user.

### Database Constraints

Workflows rely on database constraints:

- **Unique constraints**: Email uniqueness
- **Foreign key constraints**: Valid references
- **Check constraints**: Value ranges
- **Not null constraints**: Required columns

Violations result in validation errors.

## Validation Configuration

### Per-Field Validation

In field configuration dialog:

| Setting | Type | Where |
|---------|------|-------|
| Required | Checkbox | Basic Settings |
| Default Value | Field-type specific | Basic Settings |
| Help Text | Text | Basic Settings |
| Visibility Expression | JavaScript | Advanced |
| Pattern | Text (JSON) | Field-specific options |

### Number Field Validation

```json
{
  "min": 0,
  "max": 100
}
```

Configuration in dialog:
1. Open Number field config
2. Scroll to Validation section
3. Enter min/max as JSON

### File Upload Validation

```
Allowed Types: .pdf, .jpg
Multiple Files: false
Max Size: 10 MB
```

Configuration:
1. Open File field config
2. Set Allowed Types (comma-separated)
3. Toggle Multiple Files
4. Set Max Size in MB

### Custom Message

Some fields allow custom error messages:

```
Pattern: ^[0-9]{3}-[0-9]{4}$
Message: "Format must be 123-4567"
```

Shows custom message if validation fails.

## Validation in Data Providers

Data providers are validated before use:

### Provider Existence

If form references non-existent provider:
```
Error during form save:
"Unknown data provider 'get_managers'"
```

### Required Parameters

If provider requires parameter not configured:
```
Error during form save:
"Provider 'get_managers' requires parameter 'department_id'"
```

### Parameter Validation

Parameters validated by mode:
- **Static**: Value must be provided
- **Field Reference**: Field must exist
- **Expression**: Expression must be valid JavaScript

## Visibility and Validation

Hidden fields are not validated:

```javascript
// Visibility expression:
context.field.show_advanced === true

// If false:
// - Field is hidden
// - Field value ignored on submit
// - No validation errors for this field
```

However, if required field becomes hidden:
- Form still sends field with last value
- But field not visible to user

Best practice: Make required fields always visible.

## Testing Validation

### In Form Builder

1. **Preview mode**: Click Eye icon
   - See field requirements
   - Check validation visually

2. **Submit test**: Click Play button
   - Try submitting with invalid data
   - See error messages
   - Verify validation works

### Integration Testing

Test validation in workflow code:

```python
def test_create_user_validation():
    # Test email already exists
    with pytest.raises(ValidationError):
        create_user(context, "existing@example.com")
    
    # Test age too young
    with pytest.raises(ValidationError):
        create_user(context, "new@example.com", age=16)
    
    # Test valid input
    result = create_user(context, "new@example.com", age=25)
    assert result.user_id
```

## Error Handling

### Client-Side Errors

User sees inline errors:
```
Email: [user@exam] ✗ "Invalid email format"
```

User must fix before submitting.

### Server-Side Errors

After form submit, user sees error:

```
Error submitting form

Email already in use
Field: email

Please correct and try again.
```

Then form reappears with previous values preserved.

## Common Validation Patterns

### Email Validation

```
Field Type: Email
Client Validation: Automatic email format
Server Validation: 
  - Check email not already registered
  - Check domain allowed (if configured)
  - Verify email format more strictly
```

### Age Validation

```
Field: Age (Number)
Client Validation: Min 0, Max 150
Server Validation:
  - Check minimum age requirement
  - Check maximum age if applicable
```

### Phone Number Validation

```
Field: Phone (Text)
Placeholder: (555) 123-4567
Help Text: Enter 10-digit US phone number
Server Validation:
  - Check format matches pattern
  - Remove formatting characters
  - Validate number exists (optional)
```

### Date Range Validation

```
Field: Start Date (Date)
Field: End Date (Date)
Server Validation:
  - Check end date > start date
  - Check dates not in past
  - Check within allowed range
```

### File Upload Validation

```
Field: Document (File Upload)
Allowed Types: .pdf
Max Size: 5 MB
Server Validation:
  - Verify file not corrupted
  - Check file content matches type
  - Scan for malware (if applicable)
```

## Best Practices

### 1. Clear Error Messages

```python
# Bad
raise ValidationError("Invalid")

# Good
raise ValidationError(
    "Email already in use. Please use a different email or contact support.",
    field="email"
)
```

### 2. Client + Server Validation

Always validate on both sides:
```
Client: Quick feedback, user experience
Server: Security and data integrity
```

### 3. Help Text

Guide users before errors occur:

```
Field: Password
Help Text: "Minimum 8 characters with at least one number"
```

### 4. Sensible Defaults

Minimize validation errors:

```python
@param("country", "string", default_value="US")
async def create_user(context, country):
    # User might not fill this, default provided
```

### 5. Progressive Validation

Validate at multiple points:
- **Real-time**: As user types
- **Field blur**: When user leaves field
- **Submit**: Final check before sending
- **Server**: Final validation on backend

## See Also

- [Creating Forms](/docs/guides/forms/creating-forms) - Field configuration
- [Field Types](/docs/reference/forms/field-types) - Type-specific validation
- [Visibility Rules](/docs/guides/forms/visibility-rules) - Conditional validation
