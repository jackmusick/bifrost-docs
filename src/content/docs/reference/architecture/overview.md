---
title: Platform Architecture
description: Technical overview of Bifrost platform components, layers, and design decisions
---

# Platform Architecture

Bifrost is a multi-tenant workflow automation platform designed for scalability, security, and developer experience. This document describes the architectural components and design patterns.

## Table of Contents

- [System Overview](#system-overview)
- [Technology Stack](#technology-stack)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Security Architecture](#security-architecture)
- [Scalability Design](#scalability-design)
- [Design Decisions](#design-decisions)

## System Overview

Bifrost consists of three main layers:

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                       │
│              React SPA + Static Web App                 │
│          (Hosted on Azure Static Web Apps)              │
└─────────────────────────────────────────────────────────┘
                          ↑↓
                    HTTPS / REST API
                          ↑↓
┌─────────────────────────────────────────────────────────┐
│                   Backend API Layer                     │
│  Azure Functions v2 + Python 3.11 Runtime               │
│  ├─ HTTP Triggers (REST API)                            │
│  ├─ Queue Triggers (Async Workflows)                    │
│  └─ Timer Triggers (Maintenance Tasks)                  │
└─────────────────────────────────────────────────────────┘
                          ↑↓
        ┌────────────┬────────────┬────────────┐
        ↓            ↓            ↓            ↓
   ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐
   │ Azure   │ │  Azure   │ │  Azure   │ │ Azure  │
   │ Tables  │ │  Blob    │ │  Key     │ │ Files  │
   │         │ │ Storage  │ │ Vault    │ │        │
   │ Org     │ │          │ │          │ │ /work- │
   │ Data    │ │Logs      │ │ Secrets  │ │ space  │
   └─────────┘ └──────────┘ └──────────┘ └────────┘
```

## Technology Stack

### Backend

| Component        | Technology           | Purpose                                   |
| ---------------- | -------------------- | ----------------------------------------- |
| **Runtime**      | Azure Functions v2   | Serverless function execution             |
| **Language**     | Python 3.11          | Workflow code execution                   |
| **Framework**    | Azure Functions SDK  | HTTP/Queue/Timer handlers                 |
| **Data Models**  | Pydantic             | Data validation and serialization         |
| **Storage**      | Azure Tables         | Organization, user, workflow metadata     |
| **File Storage** | Azure Files          | Workflow workspace (`/workspace`, `/tmp`) |
| **Secrets**      | Azure Key Vault      | OAuth tokens, API keys                    |
| **Monitoring**   | Application Insights | Logging and diagnostics                   |

### Frontend

| Component     | Technology           | Purpose                        |
| ------------- | -------------------- | ------------------------------ |
| **Framework** | React 18             | UI component library           |
| **Language**  | TypeScript           | Type-safe frontend code        |
| **Hosting**   | Azure Static Web App | CDN-distributed static content |
| **Styling**   | Tailwind CSS         | Utility-first CSS              |
| **State**     | Zustand              | Client-side state management   |

## Component Architecture

### HTTP Request Flow

```
┌─────────────────────────────────────┐
│  Client (Frontend / API Caller)     │
└─────────────────┬───────────────────┘
                  │ HTTP Request
                  ↓
┌─────────────────────────────────────┐
│  Azure Functions HTTP Trigger       │
│  (functions/http/*.py)              │
│  - Parse request                    │
│  - Validate auth headers            │
│  - Extract organization ID          │
└─────────────────┬───────────────────┘
                  │
                  ↓
┌─────────────────────────────────────┐
│  OpenAPI Decorators                 │
│  - Parameter validation             │
│  - Response schema                  │
│  - Error handling                   │
└─────────────────┬───────────────────┘
                  │
                  ↓
┌─────────────────────────────────────┐
│  Business Logic Handler             │
│  (shared/handlers/*)                │
│  - Core logic                       │
│  - Workflow execution               │
│  - Data processing                  │
└─────────────────┬───────────────────┘
                  │
                  ↓
┌─────────────────────────────────────┐
│  Repository Layer                   │
│  (shared/repositories/*)            │
│  - Data access abstraction          │
│  - Storage operations               │
│  - Query building                   │
└─────────────────┬───────────────────┘
                  │
                  ↓
┌─────────────────────────────────────┐
│  Storage Services                   │
│  - Azure Tables                     │
│  - Azure Files                      │
│  - Azure Key Vault                  │
└─────────────────┬───────────────────┘
                  │
                  ↓ (Return data)
┌─────────────────────────────────────┐
│  Response Handler                   │
│  - Serialize response               │
│  - HTTP status code                 │
│  - Return to client                 │
└─────────────────────────────────────┘
```

### Directory Structure

```
bifrost-api/
├── functions/                     # HTTP/Timer/Queue handlers (thin layer)
│   ├── http/
│   │   ├── discovery.py          # Workflow discovery endpoint
│   │   ├── endpoints.py          # Dynamic workflow execution
│   │   ├── executions.py         # Execution history/status
│   │   ├── organizations.py      # Org CRUD operations
│   │   ├── users.py              # User management
│   │   └── openapi.py            # OpenAPI spec generation
│   ├── timer/
│   │   ├── oauth_refresh.py      # Periodic OAuth token refresh
│   │   └── execution_cleanup.py  # Clean up old executions
│   └── queue/
│       ├── worker.py             # Process async workflow tasks
│       └── poison_queue_handler.py # Handle failed messages
│
├── shared/                        # Business logic (NOT functions/)
│   ├── models.py                 # Pydantic models (source of truth)
│   ├── openapi_decorators.py     # HTTP decorator utilities
│   ├── async_executor.py         # Async workflow execution engine
│   ├── execution_logger.py       # Execution logging
│   ├── handlers/                 # Business logic (separate from HTTP)
│   │   ├── discovery_handlers.py
│   │   ├── endpoints_handlers.py
│   │   ├── executions_handlers.py
│   │   ├── workflows_handlers.py
│   │   └── organizations_handlers.py
│   ├── repositories/             # Data access abstraction
│   │   ├── base_repository.py
│   │   ├── organizations_repository.py
│   │   ├── users_repository.py
│   │   ├── executions_repository.py
│   │   └── workflows_repository.py
│   └── services/                 # External service integration
│       ├── key_vault_service.py
│       └── blob_storage_service.py
│
├── sdk/                           # Bifrost SDK (available in workflows)
│   ├── __init__.py               # Public API
│   ├── _context.py               # Execution context
│   ├── _internal.py              # Internal helpers
│   ├── workflows.py              # Workflow operations
│   ├── executions.py             # Execution management
│   ├── organizations.py          # Organization data
│   ├── secrets.py                # Secrets access
│   ├── oauth.py                  # OAuth operations
│   ├── files.py                  # File operations
│   └── forms.py                  # Form operations
│
├── workspace/                     # User workflows (Azure Files mount)
│   └── examples/                 # Example workflows
│
├── tests/                         # Test suite
│   ├── unit/                     # Unit tests (mocked services)
│   ├── integration/              # Integration tests (real services)
│   └── contract/                 # SDK contract tests
│
├── bifrost.py                     # Azure Functions app entry point
├── requirements.txt               # Python dependencies
├── host.json                      # Functions configuration
└── local.settings.json            # Local development settings
```

## Data Flow

### Workflow Execution Flow

```
1. Client Request
   └─ POST /api/workflows/{name}
   └─ Headers: x-functions-key, X-Organization-Id
   └─ Body: {workflow parameters}

2. Azure Functions HTTP Trigger
   └─ Endpoint receives request
   └─ Validates authentication

3. Handler Layer
   └─ Parse request parameters
   └─ Load workflow from workspace
   └─ Validate input types

4. Workflow Engine
   └─ Create execution context
   └─ Load workflow code
   └─ Import SDK modules
   └─ Execute workflow function

5. Workflow Code
   └─ Access SDK (secrets, oauth, etc.)
   └─ Call external APIs
   └─ Process data
   └─ Return result

6. Response Handler
   └─ Capture output
   └─ Serialize to JSON
   └─ Log execution
   └─ Return HTTP response
```

### Data Storage Layout

**Azure Tables Structure:**

```
Org Table (PartitionKey=organization_id)
├─ RowKey: org-{id}          → Organization metadata
├─ RowKey: user-{user_id}    → User records
├─ RowKey: config-{key}      → Organization settings
└─ RowKey: exec-{exec_id}    → Execution results

KeyVault Secrets:
├─ GraphApiClientSecret      → Microsoft Graph OAuth secret
├─ HaloApiKey                → HaloPSA API key
├─ OrgAbc123-OAuth-Token     → OAuth token (per-org)
└─ WebhookSecret             → Webhook signing key
```

## Security Architecture

### Authentication Layers

```
┌─────────────────────────────────────┐
│  Client Authentication              │
│  • Function Keys (API calls)        │
│  • Azure AD (Frontend)              │
│  • OAuth 2.0 (External APIs)        │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  Middleware Layer                   │
│  • Header validation                │
│  • Organization routing             │
│  • Rate limiting (future)           │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  Authorization (RBAC)               │
│  • Tenant isolation                 │
│  • Role-based access                │
│  • Resource-level permissions       │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  Execution Context                  │
│  • Workflow sandboxing              │
│  • Import restrictions              │
│  • Resource limits                  │
└─────────────────────────────────────┘
```

### Workspace Isolation

Workflows execute in a sandboxed environment with restricted imports:

```python
# ✓ Allowed in workflows
from bifrost import *  # SDK public API
import requests        # External libraries
import json

# ✗ Blocked in workflows
import sys
from azure.storage import ...  # Internal services
import functions       # Framework internals
```

## Scalability Design

### Horizontal Scaling

```
┌──────────────────────────────────┐
│  Azure Front Door (Load Balancer)│
│  • Global distribution            │
│  • DDoS protection               │
└───────────┬──────────────────────┘
            │
    ┌───────┼───────────────┐
    ↓       ↓               ↓
┌────────┐┌────────┐┌─────────────┐
│Instance│ Instance│  Instance N  │
│ 1      │ 2       │              │
│        │        │ Azure         │
│Azure   │ Azure  │ Functions     │
│Func    │ Func   │ (Auto-scale)  │
└────┬───┘└──┬────┘└──────┬───────┘
     │       │           │
     └───────┴───────────┘
             │
     ┌───────┴────────┬──────────┐
     ↓                ↓          ↓
  ┌─────────┐    ┌─────────┐ ┌────────┐
  │ Azure   │    │  Azure  │ │ Azure  │
  │ Tables  │    │ Key     │ │ Files  │
  │(Shared) │    │ Vault   │ │(Shared)│
  └─────────┘    │(Shared) │ └────────┘
                 └────────┘
```

### Auto-Scaling Configuration

Azure Functions automatically scales based on:

- **Queue length** - More messages = more instances
- **CPU usage** - High CPU = scale up
- **Memory pressure** - High memory = scale up
- **Duration** - Long executions = more instances

Configuration in `host.json`:

```json
{
  "functionTimeout": "00:05:00",
  "maxCurrentRequests": 200,
  "healthMonitor": {
    "enabled": true,
    "healthCheckInterval": "00:00:10",
    "healthCheckWindow": "00:01:00",
    "healthCheckThreshold": 6,
    "counterThreshold": 0.8
  }
}
```

## Design Decisions

### Why Azure Functions?

1. **Serverless** - No infrastructure to manage
2. **Python Support** - Native Python 3.11 runtime
3. **Scalability** - Auto-scales based on load
4. **Cost** - Pay per execution and memory
5. **Integration** - Built-in Azure service connectors

### Why Python for Workflows?

1. **Familiar** - Developers know Python
2. **Rich Ecosystem** - Thousands of libraries
3. **Safe Execution** - Can sandbox untrusted code
4. **Performance** - Fast enough for most use cases
5. **Readability** - Clear, maintainable code

### Why Multi-Tenancy?

1. **Cost Efficiency** - Shared infrastructure costs less
2. **Operational Simplicity** - One platform for all customers
3. **Shared Data** - Easy org-to-org collaboration
4. **Scalability** - Grow from 1 to 10,000+ orgs

### Why Azure Tables Over SQL?

1. **Cost** - Tables are cheaper than SQL databases
2. **Scalability** - Automatically handles partitioning
3. **Organization Isolation** - Natural partitioning by org_id
4. **Performance** - Consistent millisecond latency
5. **Availability** - Built-in geo-replication

### Why Azure Files for Workflows?

1. **Mounted Filesystem** - Familiar `/workspace` and `/tmp` paths
2. **Persistence** - Data survives function restarts
3. **Organization Isolation** - Each org has separate directory
4. **Quota Control** - Configurable per-organization limits
5. **Backup** - Built-in Azure backup and recovery

## Key Architectural Principles

1. **Separation of Concerns**

   - Functions are thin HTTP handlers
   - Business logic in `shared/handlers/`
   - Data access in `shared/repositories/`

2. **Type Safety**

   - Pydantic models for all data
   - Type hints on all functions
   - Validation on inputs/outputs

3. **Testability**

   - Mock-friendly repository pattern
   - Unit tests with mocked storage
   - Integration tests with Azurite

4. **Security**

   - Zero trust - validate everything
   - Workspace isolation with import restrictions
   - Secrets in Key Vault, never in code

5. **Scalability**

   - Stateless functions
   - Asynchronous patterns
   - Queue-based background jobs

6. **Observability**
   - Comprehensive logging
   - Structured execution tracking
   - Application Insights integration

---

## Related Documentation

- [Multi-Tenancy Architecture](./multi-tenancy.md) - Organization isolation details
- [Security Model](/reference/architecture/security/) - Authentication and authorization
- [SDK Documentation](/reference/sdk/) - Public API reference
