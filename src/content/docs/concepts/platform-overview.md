---
title: Platform Overview
description: Understand what Bifrost is and why it exists
---

Bifrost is an open-source workflow automation platform designed for MSPs (Managed Service Providers) and Integration Services. It bridges the gap between complex enterprise systems and user-friendly automation.

## The Problem Bifrost Solves

Most organizations struggle with:

- **Manual Processes**: Repetitive tasks waste employee time
- **Disconnected Systems**: Data doesn't flow between applications
- **Complex Integrations**: Building integrations requires deep technical knowledge
- **Scalability**: DIY automation solutions don't scale
- **Multi-Tenancy**: Supporting multiple clients/organizations is complicated

Bifrost solves these problems by providing a platform that:

1. **Democratizes Automation**: Non-developers can use workflows via forms
2. **Bridges Systems**: Easily integrate with Microsoft Graph, HaloPSA, and custom APIs
3. **Scales Automatically**: Built on Azure serverless (Functions, Storage, Key Vault)
4. **Isolates Data**: Complete multi-tenant architecture with organization scoping
5. **Maintains Security**: Enterprise-grade auth, encryption, and audit logging

## Core Concepts

### Workflows

Workflows are the heart of Bifrost. They're Python async functions that:

- Accept parameters
- Access organizational data
- Call external APIs and integrations
- Return results
- Are automatically discovered and registered

```python
@workflow(name="create_user", description="Create a new user")
@param("email", "string", required=True)
async def create_user(context, email: str):
    return {"user_id": "123", "email": email}
```

### Forms

Forms provide a user-friendly interface to workflows. They:

- Have multiple field types (text, select, date, etc.)
- Get options from data providers
- Have visibility rules for conditional fields
- Execute workflows on submission
- Provide real-time validation

### Data Providers

Data providers return dynamic options for form fields:

```python
@data_provider(name="get_departments", description="Get departments")
async def get_departments(context):
    return [
        {"label": "Engineering", "value": "eng"},
        {"label": "Sales", "value": "sales"}
    ]
```

Used in forms:

```json
{
  "name": "department",
  "type": "select",
  "dataProvider": "get_departments"
}
```

### The Discovery System

When Bifrost starts, it:

1. Scans `/workspace/workflows/` and `/workspace/data_providers/`
2. Imports all Python files
3. Executes decorators (@workflow, @data_provider)
4. Registers metadata in the registry
5. Exposes via REST API and to the client

This means:

- **Drop Files, They Work**: No manual registration needed
- **Hot Reload Ready**: Changes picked up automatically (with container restart for decorator changes)
- **Type Safe**: SDK provides type hints via bifrost.pyi

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Client (React SPA)                   │
│  Forms | Workflows | Dashboard | Administration      │
└──────────────────────────────────────────────────────┘
                         │
                         │ REST API
                         ▼
┌──────────────────────────────────────────────────────┐
│            Azure Functions Runtime                    │
│  ┌────────────────────────────────────────────────┐  │
│  │  HTTP Handlers (Discovery, Workflows, Forms)   │  │
│  └────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │  Workflow Registry (Decorators)                │  │
│  └────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │  Execution Context (Organization, User, State) │  │
│  └────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │  Integration Clients (Graph, HaloPSA, OAuth)   │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                         │
                         │ Azure SDK
                         ▼
┌──────────────────────────────────────────────────────┐
│              External Services                        │
│  Microsoft Graph | HaloPSA | Azure Storage | Key Vault
└──────────────────────────────────────────────────────┘
```

## Multi-Tenancy

Bifrost is built for multi-tenant environments:

- **Organization Isolation**: Each organization's data is strictly isolated
- **Org-Scoped Secrets**: Secrets stored as `{org_id}--secret_name`
- **Context Scoping**: Workflows execute with organization context
- **Per-Org Configuration**: Each organization has its own settings

## Security Model

Bifrost implements:

- **Authentication**: Azure AD, function keys
- **Authorization**: Role-based access control (RBAC)
- **Data Isolation**: Organization-level isolation
- **Secret Management**: Azure Key Vault with encryption
- **Audit Logging**: All actions logged with user context
- **OAuth Flow**: Secure OAuth 2.0 connection handling

## Deployment Options

### Local Development

- Docker Compose with Azurite (storage emulator)
- Remote debugging via debugpy
- Hot reload for code changes

### Production

- Azure Container Instances or App Service
- Azure Storage for data persistence
- Azure Key Vault for secrets
- Azure Application Insights for monitoring
- Managed Identity for authentication

## Key Features

### Workflow Development

- Python async functions with decorators
- Parameter validation
- Error handling with custom exceptions
- Logging with context
- State checkpoints for debugging
- Timeout and retry policies

### Form Building

- Multiple field types (text, select, date, file upload, etc.)
- Data provider integration
- Visibility rules with expressions
- Real-time validation
- File upload support
- Rich HTML rendering

### Integrations

- Microsoft Graph API (users, groups, mail)
- HaloPSA (tickets, clients)
- OAuth 2.0 for any service
- Custom REST API integrations
- Automatic token refresh

### Operations

- Workflow execution history
- Real-time execution logs
- Performance metrics
- Error tracking
- Manual re-execution
- Scheduled workflows

## Use Cases

### MSP/IT Service Providers

- User onboarding/offboarding automation
- License management and allocation
- Ticket creation and management
- Service request forms
- Compliance reporting

### Enterprise IT

- User provisioning in multiple systems
- Bulk operations via forms
- Self-service capabilities
- Integration with line-of-business applications
- Workflow orchestration

### Integration Services

- Data synchronization between systems
- Event-driven workflows
- API orchestration
- Custom business logic automation

## Getting Started

1. **Installation**: [Deploy to Azure](/guides/installation)
1. **First Workflow**: [Build your first workflow](/tutorials/first-workflow/)
1. **Forms**: [Create dynamic forms](/tutorials/creating-forms/)

## Open Source

Bifrost is completely open-source:

- **License**: MIT
- **API Repository**: [jackmusick/bifrost-api](https://github.com/jackmusick/bifrost-api)
- **Client Repository**: [jackmusick/bifrost-client](https://github.com/jackmusick/bifrost-client)
- **Contributing**: Issues and pull requests welcome!

## Next Steps

- Understand the [discovery system](/concepts/discovery-system/)
- Learn about [workflow execution](/concepts/workflows/)
- Explore [permissions and security](/concepts/permissions/)
- Check the [architecture reference](/reference/architecture/overview/)
