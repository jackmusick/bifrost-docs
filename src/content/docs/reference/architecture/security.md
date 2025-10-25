---
title: "Security Model"
description: "Complete overview of Bifrost security architecture and controls"
---

Bifrost implements defense-in-depth security with multiple overlapping layers to protect data, credentials, and integrations.

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Network Layer                            │
│  • HTTPS/TLS encryption for all traffic                     │
│  • Azure Front Door DDoS protection                         │
│  • IP filtering and firewall rules                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Authentication Layer                       │
│  • Azure AD integration                                     │
│  • Multi-Factor Authentication (MFA)                        │
│  • Function key authentication for APIs                     │
│  • Session management and token validation                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 Authorization Layer                         │
│  • Role-Based Access Control (RBAC)                         │
│  • Organization isolation enforcement                       │
│  • Workflow permission checks                               │
│  • API endpoint authorization                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Protection Layer                     │
│  • Encryption at rest (Azure Key Vault)                     │
│  • Secrets never logged                                     │
│  • Organization-scoped data partitioning                    │
│  • Secure token storage                                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Audit & Compliance                        │
│  • Comprehensive audit logging                              │
│  • Access tracking and monitoring                           │
│  • Immutable audit trail                                    │
│  • Compliance reporting                                     │
└─────────────────────────────────────────────────────────────┘
```

## Authentication

### Azure AD Integration

Primary authentication method for users:

- **Single Sign-On (SSO)**: Users log in with Azure AD credentials
- **Multi-Factor Authentication**: Enforced for admin roles
- **Conditional Access**: Risk-based access policies
- **Session Management**: Configurable session timeouts

### Function Key Authentication

For API access:

```bash
# All API requests require function key
curl -H "x-functions-key: your-api-key" \
  https://bifrost.example.com/api/workflows
```

Keys are:
- Managed by Azure Functions
- Regularly rotated
- Scoped to specific functions or all functions
- Can be revoked immediately

### OAuth 2.0 for External Services

For integrations with external APIs:
- Authorization code flow for user-initiated auth
- Client credentials for service accounts
- Token refresh managed automatically
- Tokens stored in Key Vault

## Authorization

### Role-Based Access Control

Five predefined roles with increasing permissions:

| Role | Purpose | Permissions |
|------|---------|-------------|
| **PlatformAdmin** | System administration | Full access across all organizations |
| **OrgAdmin** | Organization management | Full access within organization |
| **WorkflowDeveloper** | Workflow development | Create/modify workflows, use integrations |
| **WorkflowUser** | Workflow execution | Execute approved workflows only |
| **ReadOnlyUser** | Auditing/compliance | View-only access |

See [Permissions](/concepts/permissions) for detailed permission matrix.

### Organization Isolation

Complete isolation between organizations:

1. **Data Level**
   - All queries automatically filtered by organization
   - Cross-org queries impossible without explicit authorization
   - Users can only see their org's data

2. **API Level**
   - Every request requires `X-Organization-Id` header
   - Middleware validates organization membership
   - Unauthorized access attempts logged

3. **Configuration Level**
   - Config, secrets, OAuth connections per organization
   - No shared secrets between orgs
   - Each org has isolated Key Vault namespace

4. **Execution Level**
   - Workflows execute with org context
   - Integrations use org-specific credentials
   - Logs tagged with organization ID

### Workflow Permissions

Workflows can specify required roles:

```python
@workflow(
    name="sensitive_operation",
    required_role="OrgAdmin",  # Only OrgAdmins can execute
)
async def sensitive_operation(ctx):
    pass
```

Permission levels:
- `execute` - Can run the workflow
- `create`/`update`/`delete` - Can modify the workflow
- `read` - Can view the workflow

## Data Protection

### Encryption at Rest

All data stored in Azure is encrypted:

- **Azure Storage**: Encryption with Microsoft-managed keys
- **Azure Key Vault**: FIPS 140-2 Level 2 certified
- **Database**: Transparent Data Encryption (TDE)
- **Backups**: Encrypted with same keys as source

### Encryption in Transit

All data in motion is encrypted:

- **HTTPS/TLS 1.2+**: Required for all connections
- **API Communication**: Encrypted between services
- **OAuth Flows**: Encrypted authorization code exchange
- **Secret Retrieval**: Encrypted Key Vault API calls

### Secret Management

Secrets never appear in logs or responses:

```python
# Bad: Secret in log
ctx.log("info", f"API Key: {api_key}")  # NEVER DO THIS

# Good: Only log metadata
ctx.log("info", "API call successful", {
    "endpoint": "/users",
    "has_api_key": bool(api_key)
})
```

Secrets are:
- Encrypted in Key Vault
- Retrieved only when needed
- Never cached in logs
- Never returned in API responses
- Audited on every access

## Key Vault Integration

Secrets stored in Azure Key Vault with:

### Access Control

- **Managed Identity**: Bifrost authenticates via managed identity (no keys needed)
- **Access Policies**: Explicit permissions for secret operations
- **RBAC**: Role-based access to Key Vault itself

### Operational Security

- **Soft Delete**: 90-day recovery window for accidentally deleted secrets
- **Purge Protection**: Prevents immediate permanent deletion
- **Audit Logging**: All access logged to Azure Monitor
- **Key Rotation**: Secrets can be rotated without downtime

### Naming Convention

```
{organization_id}--{secret_name}
```

Example: `client-acme--api-key`

This ensures:
- Automatic org-level isolation
- Clear ownership of each secret
- No naming conflicts between orgs

## Audit & Compliance

### Comprehensive Logging

All actions logged with:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "user_id": "user-123",
  "user_email": "admin@example.com",
  "organization_id": "org-abc",
  "action": "create_oauth_connection",
  "resource": "microsoft-graph",
  "status": "success",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0..."
}
```

### Audit Trail

- **Immutable**: Cannot be modified after creation
- **Tamper-evident**: Any modifications detected
- **Retention**: Configurable retention (default 7 years)
- **Searchable**: Full text search and filtering

### Compliance Support

Built-in compliance features:

- **SOC 2 Type II**: Audit report available
- **GDPR**: Data export, deletion, and retention
- **HIPAA**: Encryption, access controls, audit trails
- **ISO 27001**: Information security management

### Monitoring

Real-time alerts for:
- Failed authentication attempts
- Unusual data access patterns
- Privilege escalation
- Mass data operations
- Failed OAuth authorizations

## Network Security

### Azure Front Door

DDoS and application protection:

- **DDoS Protection Standard**: Automatic attack mitigation
- **Web Application Firewall**: Rules-based protection
- **SSL/TLS Termination**: Certificate management
- **Rate Limiting**: Prevent abuse

### IP Filtering

Optional IP whitelist:

```
Allowed IPs:
- 192.168.1.0/24
- 10.0.0.0/8
```

### Private Endpoints

Optional: Connect via private network:
- ExpressRoute for hybrid environments
- Azure VPN Gateway for site-to-site
- No internet exposure for data

## Code Security

### Import Restrictions

Workspace code (workflows, data providers) cannot import system internals:

```python
# Allowed: Public APIs and standard libraries
import asyncio
from bifrost import workflow, context

# Blocked: System internals
from shared.keyvault import KeyVaultClient  # ERROR

@workflow(name="my_workflow")
async def my_workflow(ctx):
    pass
```

This prevents:
- Bypassing permission checks
- Accessing other organizations' secrets
- Modifying audit logs
- Disabling security controls

### Runtime Enforcement

Import restrictions enforced at runtime:
- All imports validated before execution
- Violations logged and blocked
- Audit trail of blocked attempts

## Best Practices

### 1. Principle of Least Privilege

Grant minimum required permissions:

```python
# Good: User has only execute permission for specific workflows
user_role = "WorkflowUser"
can_execute = ["data-sync-workflow", "report-generation"]

# Bad: User has admin for everything
user_role = "OrgAdmin"
```

### 2. Defense in Depth

Don't rely on single security layer:
- Use both API key auth AND org validation
- Encrypt both at rest AND in transit
- Implement both code import restrictions AND permission checks

### 3. Audit Regularly

Review logs weekly for:
- Unusual access patterns
- Failed authentication attempts
- Permission changes
- Data export operations

### 4. Rotate Credentials

- OAuth secrets: 6-12 months
- API keys: 3-6 months
- Database passwords: 30-90 days
- SSH keys: On key compromise

### 5. Monitor Integration Health

Check OAuth connections regularly:
- Token refresh success rate
- Failed authorization attempts
- Scope changes
- Connection status

### 6. Secure Configuration

Store sensitive config in Key Vault:

```python
# Bad: API key in plaintext config
config = {"api_key": "sk-secret-value"}

# Good: Reference to Key Vault secret
config = {"api_key": {"secret_ref": "external_api_key"}}
```

### 7. Log Responsibly

Never log sensitive data:

```python
# Bad
ctx.log("info", f"Password: {password}")
ctx.log("info", f"API Key: {api_key}")
ctx.log("debug", f"OAuth response: {oauth_response}")

# Good
ctx.log("info", "Authentication successful", {
    "user_id": user_id,
    "method": "azure_ad"
})
```

## Security Checklist

Before deploying to production:

- [ ] All secrets in Key Vault (not in code or config)
- [ ] OAuth connections authorized and tested
- [ ] Audit logging enabled
- [ ] Rate limiting configured
- [ ] IP filtering enabled (if applicable)
- [ ] API keys rotated
- [ ] Access logs reviewed
- [ ] Compliance policies documented
- [ ] Disaster recovery plan in place
- [ ] Security training completed

## Incident Response

### If Secret is Compromised

1. Immediately rotate the secret
2. Review access logs since compromise detected
3. Audit any operations performed
4. Alert affected organizations
5. Review Key Vault access logs for unauthorized access

### If Account is Compromised

1. Revoke session immediately
2. Force password reset
3. Review user's actions in audit logs
4. Check for data exfiltration
5. Enable MFA if not already enabled

### If Authorization Bypass Suspected

1. Isolate affected organization
2. Review audit logs for unauthorized access
3. Check workflows for malicious code
4. Audit OAuth token usage
5. Notify security team

## References

- [Azure Key Vault Documentation](https://docs.microsoft.com/azure/key-vault/)
- [Azure AD Security](https://docs.microsoft.com/azure/active-directory/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
