---
title: "Permissions & Roles"
description: "Understanding user roles, permissions, and access control in Bifrost"
---

Bifrost uses Role-Based Access Control (RBAC) to manage who can do what. Understanding permissions and roles is essential for securing your Bifrost instance.

## Core Concepts

### Roles vs Permissions

- **Role**: A named collection of permissions (e.g., "OrgAdmin")
- **Permission**: The ability to perform a specific action (e.g., "create_workflow")

A user has one role per organization, and that role grants specific permissions.

### Role Hierarchy

Roles form a hierarchy where higher roles include all lower role permissions:

```
PlatformAdmin
  └─ OrgAdmin
      └─ WorkflowDeveloper
          └─ WorkflowUser
              └─ ReadOnlyUser
```

PlatformAdmin includes everything OrgAdmin can do, plus more.

## The Five Roles

### PlatformAdmin

**Scope**: Platform-wide access across all organizations

**Capabilities:**
- Create, manage, and delete organizations
- Manage users across all organizations
- Configure platform-wide settings
- Access all workflows in all organizations
- View audit logs and system metrics
- Manage platform security settings

**Use Cases:**
- Platform maintainers
- System administrators
- Vendor support staff

**Permissions:**
```
Organizations: create, read, update, delete
Users: create, read, update, delete (all orgs)
Workflows: read, execute (all orgs)
Audit: read (all orgs)
Platform: update
```

**When to Assign:**
- Only to trusted admin staff
- Require MFA
- Limit number of admins
- Audit their access regularly

### OrgAdmin

**Scope**: Full control within one organization

**Capabilities:**
- Manage organization settings and configuration
- Create and manage users within organization
- Create, modify, delete workflows
- Configure OAuth connections and integrations
- Manage organization secrets
- View organization audit logs
- Assign roles to other users

**Use Cases:**
- Organization managers
- Workflow administrators
- Integration managers

**Permissions:**
```
Organization: read, update
Users: create, read, update, delete
Workflows: create, read, update, delete, execute
Integrations: create, read, update, delete, configure
Secrets: create, read, update, delete
Audit: read
```

**When to Assign:**
- To organization leadership
- Require MFA for security
- Limit to necessary admins
- Define admin approval workflows

### WorkflowDeveloper

**Scope**: Development and management of workflows

**Capabilities:**
- Create and modify workflows
- Execute workflows for testing
- Use existing integrations
- Access organization configuration
- View execution history
- Cannot modify integrations or users

**Use Cases:**
- Automation engineers
- Business process designers
- Integration specialists

**Permissions:**
```
Workflows: create, read, update, delete, execute
Integrations: read, execute
Organization: read
Audit: read
```

**When to Assign:**
- To technical team members
- Developers building automations
- Users designing workflows

### WorkflowUser

**Scope**: Execution of approved workflows only

**Capabilities:**
- Execute workflows
- View own execution history
- Access workflow forms
- View workflow results
- Cannot modify workflows

**Use Cases:**
- End users running automations
- Business users executing workflows
- Non-technical workflow operators

**Permissions:**
```
Workflows: execute
Executions: read, create
Organization: read
```

**When to Assign:**
- To business users
- Non-technical staff
- Casual workflow users

### ReadOnlyUser

**Scope**: Viewing and auditing only

**Capabilities:**
- View workflow definitions
- View execution history and results
- View organization settings
- View audit logs
- Cannot execute or modify anything

**Use Cases:**
- Auditors
- Compliance officers
- Managers reviewing operations
- Observers monitoring workflows

**Permissions:**
```
Workflows: read
Executions: read
Organization: read
Audit: read
```

**When to Assign:**
- To auditors and compliance staff
- Managers needing visibility
- Third-party observers

## Permission Levels

Permissions are structured in three levels:

### 1. Organization Level

Controls access to the organization itself:

| Permission | Description | Roles |
|-----------|-----------|--------|
| `org:read` | View org settings | All except None |
| `org:update` | Modify org settings | PlatformAdmin, OrgAdmin |
| `org:delete` | Delete organization | PlatformAdmin only |

### 2. Workflow Level

Controls what users can do with workflows:

| Permission | Description | Roles |
|-----------|-----------|--------|
| `workflow:read` | View workflows | All except None |
| `workflow:create` | Create new workflows | PlatformAdmin, OrgAdmin, WorkflowDeveloper |
| `workflow:update` | Modify workflows | PlatformAdmin, OrgAdmin, WorkflowDeveloper |
| `workflow:delete` | Delete workflows | PlatformAdmin, OrgAdmin, WorkflowDeveloper |
| `workflow:execute` | Run workflows | All except ReadOnlyUser |

### 3. Admin Level

Controls administrative operations:

| Permission | Description | Roles |
|-----------|-----------|--------|
| `admin:users` | Manage users | PlatformAdmin, OrgAdmin |
| `admin:integrations` | Manage integrations | PlatformAdmin, OrgAdmin |
| `admin:secrets` | Manage secrets | PlatformAdmin, OrgAdmin |
| `admin:audit` | View audit logs | PlatformAdmin, OrgAdmin, WorkflowDeveloper |

## Enforcing Permissions

### At Workflow Definition

Require specific role to execute:

```python
@workflow(
    name="sensitive_operation",
    description="Admin-only operation",
    required_role="OrgAdmin"  # Only OrgAdmins can execute
)
async def sensitive_operation(ctx):
    pass
```

### In API Calls

The API validates permissions:

```bash
# User with WorkflowUser role tries to create workflow
curl -X POST \
  -H "Authorization: Bearer token" \
  https://bifrost.example.com/api/workflows
# Response: 403 Forbidden - insufficient permissions
```

### Middleware Checks

Every request is validated:

1. Extract user's organization and role
2. Check if role allows the action
3. Verify organization membership
4. Allow or deny request
5. Audit the decision

## Multi-Organization Users

Users can have different roles in different organizations:

```
User: alice@example.com

Organization: ACME Corp
  Role: OrgAdmin
  Permissions: Full control

Organization: TechCorp
  Role: WorkflowDeveloper
  Permissions: Create/modify workflows only

Organization: FintechCo
  Role: WorkflowUser
  Permissions: Execute workflows only
```

Each role is independent per organization.

## Default Permission Assignments

### New User

Default role assignment:

1. **First user in organization**: OrgAdmin
2. **Subsequent users**: WorkflowUser (least privilege)
3. **Invited users**: Role specified by inviter

### Best Practices

Always assign minimal required role:

```python
# Good: Start with WorkflowUser
user_role = "WorkflowUser"

# If they need to create workflows, upgrade to:
user_role = "WorkflowDeveloper"

# If they need to manage integrations, upgrade to:
user_role = "OrgAdmin"

# Bad: Assigning OrgAdmin to everyone
user_role = "OrgAdmin"  # Over-privileged
```

## Permission Changes

### Revoking Permissions

When removing a user or changing roles:

1. Access is revoked immediately
2. Existing sessions terminated
3. In-progress workflows complete with current privileges
4. Action logged in audit trail

### Audit Trail

All permission changes logged:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "action": "role_change",
  "user_id": "user-123",
  "organization_id": "org-abc",
  "old_role": "WorkflowUser",
  "new_role": "WorkflowDeveloper",
  "changed_by": "admin@example.com",
  "reason": "Promotion to developer"
}
```

## Separation of Duties

Best practice: Don't give users conflicting roles:

```python
# Bad: Same person is both developer and approver
user_permissions = ["workflow:update", "workflow:approve"]

# Good: Different people for each role
developer_permissions = ["workflow:create", "workflow:update"]
approver_permissions = ["workflow:approve"]
```

## Special Cases

### Service Accounts

For automated processes:

```
User: bifrost-service
Organization: ACME Corp
Role: WorkflowDeveloper

Purpose: Automated workflow scheduling
Permissions: Execute workflows, read logs
No: Create/modify workflows, manage users
```

### Temporary Access

For consultants or contractors:

```
User: consultant@external.com
Organization: TechCorp
Role: WorkflowDeveloper
Expires: 2024-12-31

After expiration: Access automatically revoked
```

### Read-Only Auditors

For compliance and security:

```
User: auditor@compliance.com
Organization: All (custom permission)
Role: ReadOnlyUser

Permissions: View all workflows, see all audit logs
No: Execute anything, modify anything
```

## Troubleshooting Permissions

### "Insufficient Permissions" Error

Check:
1. User's role in this organization
2. Workflow requirements (if defined)
3. Your membership in the organization
4. Workflow status (not archived/deleted)

### Lost Access After Role Change

This is expected and correct:
- Old permissions revoked immediately
- Need to re-login to get new permissions
- Sessions from old role terminated
- In-progress workflows use new permissions

### Can't See Other Organization

You're not a member:
- Only see organizations you're assigned to
- Ask OrgAdmin to add you
- PlatformAdmins can add themselves

## Recommendations

### For Individuals

- **Developers**: WorkflowDeveloper role
- **Operators**: WorkflowUser role
- **Managers**: ReadOnlyUser role
- **Admins**: OrgAdmin role (one or two people)

### For Teams

- **Admin Team**: 2-3 OrgAdmins maximum
- **Dev Team**: Mostly WorkflowDeveloper
- **Ops Team**: Mostly WorkflowUser
- **Audit Team**: ReadOnlyUser only

### Security

- Review role assignments quarterly
- Audit admin access monthly
- Remove unused accounts immediately
- Require MFA for admin roles
- Document reasons for high permissions

## Reference

See [Permissions and Roles](/public/docs/permissions-and-roles.md) for the detailed specifications from the platform documentation.
