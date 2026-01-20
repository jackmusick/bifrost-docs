# Documentation Overhaul Plan

## Executive Summary

This documentation overhaul effort systematically reviewed the Bifrost platform codebase against existing documentation to identify gaps, outdated content, and areas needing new documentation.

### Overall Documentation Health

**Status: Significant Updates Required**

| Metric | Count |
|--------|-------|
| Topics Reviewed | 11 of 11 |
| Critical Issues (Immediate Fix) | 5 |
| Major Gaps (High Priority) | 22 |
| Minor Gaps (Lower Priority) | 28 |
| Inaccuracies Found | 7 |

### Areas with Good Coverage
- OAuth SSO configuration (Microsoft, Google, OIDC)
- Passkeys/WebAuthn setup
- Basic form creation tutorials
- Integration OAuth basics
- Secrets management and encryption

### Areas with Major Gaps
- **App Builder/Code Engine** - Documentation describes legacy JSON architecture; actual system uses TSX/JSX Code Engine (complete rewrite needed)
- **AI Coding / MCP Tools** - 40+ tools in codebase, ~25 documented; Code Engine SDK hooks completely missing
- **Admin Features** - Cross-org log aggregation, stuck execution cleanup, debug logs undocumented
- **Agent Access Levels** - Documentation incorrectly lists "Public" access level which doesn't exist
- **MFA/Device Auth** - Implemented but not documented

---

## Critical Issues (Fix Immediately)

These issues could cause security problems, major confusion, or significantly impact users:

### 1. Agent Access Levels Are Incorrect (Security)
**File:** `/src/content/docs/how-to-guides/ai/agents-and-chat.mdx`

**Issue:** Documentation shows three access levels: "Public, Authenticated, Role-based" but codebase only has `AUTHENTICATED` and `ROLE_BASED`. The "Public" level does not exist.

**Impact:** Users may believe they can create publicly accessible agents, which could lead to security misconfigurations.

**Fix:** Remove "Public" from documentation, clarify the two valid access levels, document cascade scoping pattern.

---

### 2. App Builder Architecture Completely Wrong
**Files:** All files in `/src/content/docs/sdk-reference/app-builder/`

**Issue:** Existing documentation describes a JSON-based declarative app system with drag-and-drop editor:
- Docs show: `{ "type": "heading", "props": { "text": "..." } }`
- Reality is: `<Heading level={1}>Welcome</Heading>` in TSX files

The platform now uses a **Code Engine** with:
- Browser-based Babel compilation
- File-based routing (Next.js-like)
- React components with `import { ... } from "bifrost"`
- shadcn/ui components globally available

**Impact:** Users following current docs will not understand how the system actually works.

**Fix:** Complete rewrite of app-builder documentation section.

---

### 3. Code Engine SDK Hooks Missing
**Gap:** No documentation exists for critical app development APIs:
- `useWorkflow<T>(workflowId)` - Streaming workflow execution
- `runWorkflow(id, params)` - Imperative workflow calls
- `useParams()`, `useSearchParams()` - Route parameters
- `useUser()` - Current user with `hasRole()` method
- `navigate()`, `useNavigate()` - Path-transforming navigation
- `useAppState(key, initial)` - Cross-page state

**Impact:** AI agents and developers cannot build TSX apps without this documentation.

**Fix:** Create new `/sdk-reference/app-builder/code-engine.mdx` and `/sdk-reference/app-builder/sdk-hooks.mdx`.

---

### 4. MCP Tools List Incomplete
**File:** `/src/content/docs/how-to-guides/local-dev/ai-coding.md`

**Issue:** Documentation lists ~25 MCP tools; codebase has 40+ tools including:
- Agent tools (list, get, create, update, delete agents)
- Table tools (list, get, create, update tables)
- Organization tools
- Execution viewing tools
- **Code file tools** (`list_app_files`, `get_app_file`, `create_app_file`, `update_app_file`, `delete_app_file`)

**Impact:** AI coding agents don't know all available capabilities.

**Fix:** Update MCP tool reference with complete list, add restricted vs default-enabled distinction.

---

### 5. Multi-Factor Authentication Undocumented
**Gap:** MFA is implemented and required for password login but has zero documentation:
- TOTP enrollment flow
- Recovery codes generation and usage
- Trusted devices (30-day MFA bypass)
- MFA enforcement behavior

**Impact:** Administrators cannot configure MFA, users confused about enrollment.

**Fix:** Create `/how-to-guides/authentication/mfa.mdx`.

---

## Phase 1: Critical Fixes (High Priority)

Complete these first - security and core architecture issues.

### Security-Related Documentation Fixes

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| Fix agent access levels (remove "Public") | agents-and-chat.mdx | 1 hour | P0 |
| Document cascade scoping for agents | agents-and-chat.mdx | 2 hours | P0 |
| Document platform admin bypass behavior | permissions.md | 1 hour | P0 |
| Create MFA configuration guide | NEW: mfa.mdx | 4 hours | P0 |
| Document token lifecycle (30min access, 7day refresh) | sso.mdx | 1 hour | P1 |
| Document server-side PKCE implementation | sso.mdx | 2 hours | P1 |

### Core Architecture Documentation (Complete Rewrite)

| Task | Files | Effort | Priority |
|------|-------|--------|----------|
| Rewrite App Builder core concepts | core-concepts/app-builder.mdx | 8 hours | P0 |
| Create Code Engine architecture doc | NEW: sdk-reference/app-builder/code-engine.mdx | 6 hours | P0 |
| Create SDK hooks reference | NEW: sdk-reference/app-builder/sdk-hooks.mdx | 4 hours | P0 |
| Document file structure conventions | NEW: sdk-reference/app-builder/file-structure.mdx | 3 hours | P0 |
| Rewrite components reference for shadcn/ui | sdk-reference/app-builder/components.mdx | 4 hours | P1 |
| Update MCP tools with code file tools | how-to-guides/integrations/mcp-server.mdx | 4 hours | P1 |

**Estimated Phase 1 Effort: 40-50 hours**

---

## Phase 2: Major Feature Documentation (Medium Priority)

New features and significant updates to existing docs.

### Admin Features (No Documentation Exists)

| Task | Files | Effort |
|------|-------|--------|
| Create admin execution monitoring guide | NEW: how-to-guides/admin/execution-monitoring.mdx | 4 hours |
| Document Logs View (cross-org aggregation) | NEW: how-to-guides/admin/execution-monitoring.mdx | 2 hours |
| Document stuck execution cleanup | NEW: how-to-guides/admin/stuck-execution-cleanup.mdx | 3 hours |
| Document execution debugging (variables, metrics) | NEW: how-to-guides/admin/execution-debugging.mdx | 3 hours |
| Document DEBUG/TRACEBACK log filtering | error-handling.mdx | 1 hour |

### OAuth/Authentication Enhancements

| Task | Files | Effort |
|------|-------|--------|
| Create authentication architecture overview | NEW: core-concepts/authentication-overview.mdx | 4 hours |
| Document Device Authorization Flow (RFC 8628) | NEW or update: local-dev/setup.mdx | 3 hours |
| Document user provisioning (first-user bootstrap) | NEW: how-to-guides/admin/user-provisioning.mdx | 2 hours |
| Expand OAuth troubleshooting (connection statuses) | troubleshooting/oauth.md | 2 hours |
| Document URL templating with `{entity_id}` | creating-integrations.mdx | 2 hours |

### Agent System Improvements

| Task | Files | Effort |
|------|-------|--------|
| Create agents core concept page | NEW: core-concepts/agents.mdx | 4 hours |
| Document agent architecture (virtual entities) | agents-and-chat.mdx | 2 hours |
| Document system tools vs workflow tools | agents-and-chat.mdx | 2 hours |
| Document coding mode (PLAN vs EXECUTE) | agents-and-chat.mdx | 2 hours |
| Document delegation tool generation | agents-and-chat.mdx | 1 hour |

### Forms Improvements

| Task | Files | Effort |
|------|-------|--------|
| Update field types (add datetime, markdown, html; remove multi-select) | core-concepts/forms.mdx | 1 hour |
| Document form virtualization architecture | core-concepts/forms.mdx | 2 hours |
| Create comprehensive file upload guide | NEW: how-to-guides/forms/file-uploads.mdx | 3 hours |
| Fix broken documentation links | Multiple files | 1 hour |

### Permissions & Roles

| Task | Files | Effort |
|------|-------|--------|
| Document access levels (authenticated vs role_based) | permissions.md | 2 hours |
| Document workflow role sync | permissions.md | 2 hours |
| Add role management API reference | permissions.md | 2 hours |

### Scope Resolution

| Task | Files | Effort |
|------|-------|--------|
| Rewrite scopes.mdx with cascade scoping explanation | core-concepts/scopes.mdx | 4 hours |
| Document OrgFilterType values | core-concepts/scopes.mdx | 1 hour |
| Add practical scope examples | NEW: how-to-guides/scopes-deep-dive.mdx | 3 hours |
| Fix typo ("oranization" -> "organization") | core-concepts/scopes.mdx | 5 min |

**Estimated Phase 2 Effort: 55-65 hours**

---

## Phase 3: Polish and Completeness (Lower Priority)

Minor updates and nice-to-have improvements.

### AI Coding Enhancements

| Task | Files | Effort |
|------|-------|--------|
| Add Tailwind 4 documentation | code-engine.mdx | 1 hour |
| Create component visual showcase | NEW: visual reference | 4 hours |
| Add troubleshooting for common AI coding issues | ai-coding.md | 2 hours |

### Agent System Polish

| Task | Files | Effort |
|------|-------|--------|
| Fix @mention syntax (should be `@[Agent Name]`) | agents-and-chat.mdx | 30 min |
| Document chat stream events (ChatStreamChunk) | agents-and-chat.mdx | 2 hours |
| Document context management (token estimation) | agents-and-chat.mdx | 1 hour |

### OAuth Polish

| Task | Files | Effort |
|------|-------|--------|
| Create API reference for auth endpoints | NEW: api-reference/auth.mdx | 4 hours |
| Document encryption key management/rotation | secrets-management.mdx | 2 hours |
| Document cache invalidation patterns | troubleshooting/oauth.md | 1 hour |

### Forms Polish

| Task | Files | Effort |
|------|-------|--------|
| Document expression mode for data providers | cascading-dropdowns.mdx | 2 hours |
| Document launch workflow -> main workflow data flow | startup-workflows.mdx | 2 hours |
| Add SDK forms module reference | NEW: sdk-reference/sdk/forms-module.mdx | 2 hours |
| Document validation patterns | core-concepts/forms.mdx | 2 hours |
| Document JSX vs static HTML detection | html-content.mdx | 1 hour |

### Permissions Polish

| Task | Files | Effort |
|------|-------|--------|
| Add OrgScopedRepository technical reference | NEW: developer guide | 3 hours |
| Document entity-role junction tables | permissions.md | 1 hour |

### Scope Resolution Polish

| Task | Files | Effort |
|------|-------|--------|
| Standardize SDK scope parameter docs across modules | Multiple SDK refs | 2 hours |
| Document tables three-level scoping | tables-module.mdx | 2 hours |
| Clarify context.scope vs SDK scope parameter | context-api.mdx | 1 hour |

**Estimated Phase 3 Effort: 35-45 hours**

---

## Inaccuracies Found

| Issue | Location | Fix |
|-------|----------|-----|
| Agent "Public" access level doesn't exist | agents-and-chat.mdx | Remove from docs |
| @mention syntax wrong (`@agent-name` vs `@[Agent Name]`) | agents-and-chat.mdx | Update examples |
| Multi-select field type doesn't exist | core-concepts/forms.mdx | Remove from docs |
| Data provider guide link broken | core-concepts/forms.mdx | Fix link |
| Context object reference link broken | context-field-references.mdx | Fix link |
| `list_data_providers` tool name wrong | ai-coding.md | Update to correct name |
| App Builder MCP tools don't match codebase | ai-coding.md | Update tool list |

---

## Topic Status

| Topic | Codebase Review | Docs Review | Status |
|-------|-----------------|-------------|--------|
| [App Builder](./findings/app-builder.md) | ✅ Complete | ✅ Complete | **Critical - Complete Rewrite** |
| [Entity Management](./findings/entity-management.md) | ✅ Complete | ✅ Complete | **High Priority - No Docs Exist** |
| [GitHub Sync](./findings/github-sync.md) | ✅ Complete | ✅ Complete | **High Priority - No Docs Exist** |
| [SDK Workflows](./findings/sdk-workflows.md) | ✅ Complete | ✅ Complete | **Medium Priority - Files Module Missing** |
| [Permissions & Roles](./findings/permissions-roles.md) | ✅ Complete | ✅ Complete | **High Priority - Major Gaps** |
| [Scope Resolution](./findings/scope-resolution.md) | ✅ Complete | ✅ Complete | **Medium Priority - Rewrite Recommended** |
| [Forms](./findings/forms.md) | ✅ Complete | ✅ Complete | **Medium Priority - Updates Needed** |
| [Agents](./findings/agents.md) | ✅ Complete | ✅ Complete | **High Priority - Access Level Wrong** |
| [OAuth & Authentication](./findings/oauth-authentication.md) | ✅ Complete | ✅ Complete | **High Priority - MFA Missing** |
| [Admin Features](./findings/admin-features.md) | ✅ Complete | ✅ Complete | **High Priority - No Docs Exist** |
| [AI Coding & MCP](./findings/ai-coding-mcp.md) | ✅ Complete | ✅ Complete | **Critical - Code Engine Missing** |

---

## Total Effort Estimate

| Phase | Effort | Timeline (1 FTE) |
|-------|--------|------------------|
| Phase 1: Critical Fixes | 40-50 hours | 1-2 weeks |
| Phase 2: Major Features | 55-65 hours | 2-3 weeks |
| Phase 3: Polish | 35-45 hours | 1-2 weeks |
| **Total** | **130-160 hours** | **4-7 weeks** |

---

## Instructions for Agents

### Codebase Agent
1. Search the `/Users/jack/GitHub/bifrost` repository for relevant code
2. Focus on recent commits and current implementation
3. Document key features, how they work, and important concepts
4. Note any patterns or conventions that should be documented

### Docs Agent
1. Search `/Users/jack/GitHub/bifrost-integrations-docs` for existing documentation
2. Identify what exists, what's missing, and what's outdated
3. Note specific gaps and recommend actions
4. Reference specific file paths for existing docs

### Writing Agent
1. Synthesize findings from both agents
2. Create or update documentation in the docs repository
3. Follow existing documentation conventions and style

---

## Topic Descriptions

### App Builder
Code Engine, JSX-based apps, file routing, platform hooks, component model changes. Covers how developers build and deploy custom applications on the Bifrost platform.

### Entity Management
New Entity Management page, mass reassignment, dependency graphs. Covers managing entities across organizations and handling bulk operations.

### GitHub Sync
App indexing, entity-centric sync, source control panel changes. Covers how Bifrost syncs with GitHub repositories and manages version control.

### SDK Workflows
Workflow execution, SDK modules, file operations, decorators. Covers the Python SDK for building automation workflows.

### Permissions & Roles
Role-based access, repository pattern authorization, org hierarchy. Covers the permission system and how access control works.

### Scope Resolution
How scopes work, cascade scoping, organization hierarchy. Covers the scoping system that determines data visibility and access.

### Forms
Form virtualization, S3 removal, serialization changes. Covers the form system and recent architectural changes.

### Agents
Agent virtualization, S3 removal, agent execution. Covers the agent system and how agents run automations.

### OAuth & Authentication
OAuth flow, Entra ID, connection management. Covers authentication mechanisms and third-party integrations.

### Admin Features
Execution logs, admin endpoints, monitoring. Covers administrative tools and observability features.

### AI Coding & MCP
MCP tools for AI agents, system prompt, TSX structure, Bifrost SDK hooks (runWorkflow, useWorkflow, useParams, etc.), available ShadCN components, Tailwind 4. Covers how AI assistants can build Bifrost applications.
