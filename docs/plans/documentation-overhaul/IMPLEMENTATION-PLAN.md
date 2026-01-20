# Documentation Implementation Plan

## Overview

This plan organizes 130-160 hours of documentation work into a structured, phased implementation with clear dependencies and parallel execution groups.

| Metric | Value |
|--------|-------|
| **Total Estimated Effort** | 130-160 hours |
| **New Pages** | ~25 |
| **Major Updates** | ~15 |
| **Minor Fixes** | ~12 |
| **Recommended Timeline** | 5-7 weeks (1 FTE) |

---

## Documentation Principles

### Diataxis Categories

All documentation follows the Diataxis framework:

| Type | Purpose | Directory | Content Style |
|------|---------|-----------|---------------|
| **Tutorial** | Learning-oriented hands-on walkthroughs | `getting-started/` | Step-by-step, beginner-friendly |
| **How-To Guide** | Task-oriented steps for specific goals | `how-to-guides/` | Practical, goal-focused |
| **Reference** | Information-oriented API/SDK docs | `sdk-reference/` | Accurate, complete, searchable |
| **Explanation** | Understanding-oriented conceptual context | `core-concepts/` | Conceptual, background, "why" |

### What NOT to Include

User-facing documentation should NOT include:
- Internal file paths (e.g., `api/src/repositories/org_scoped.py`)
- Internal function names unless part of the public SDK
- Implementation details users do not need
- Backend architecture details (except in dedicated platform developer docs)

User-facing documentation SHOULD include:
- SDK module APIs (`from bifrost import context, config, files`)
- Public hooks (`useWorkflow`, `runWorkflow`, `useParams`)
- Decorator usage (`@workflow`, `@tool`, `@data_provider`)
- MCP tool names and parameters (for AI coding)
- UI walkthrough with screenshots

---

## Phase 1: Foundation and Critical Fixes

**Priority:** P0 - Must complete first
**Effort:** 40-50 hours
**Timeline:** 1-2 weeks

These issues block users, create security confusion, or describe completely incorrect architecture.

### Phase 1 Dependencies

```
Security Fixes (can run in parallel)
    |
Architecture Rewrites (depend on understanding security model)
    |
Code Engine SDK Reference (depends on architecture docs existing)
```

### Task Group 1A: Security and Accuracy Fixes

**Can run in parallel.** These are independent, isolated fixes.

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Fix Agent Access Levels | Reference Update | `how-to-guides/ai/agents-and-chat.mdx` | Remove "Public" access level (does not exist). Document only `AUTHENTICATED` and `ROLE_BASED`. Add cascade scoping explanation. | 2 hours |
| Document Platform Admin Bypass | Reference Update | `core-concepts/permissions.md` | Add section explaining platform admin bypass behavior for role checks. Document `is_superuser` flag. | 1 hour |
| Fix @mention Syntax | Reference Update | `how-to-guides/ai/agents-and-chat.mdx` | Update examples from `@agent-name` to `@[Agent Name]` (with brackets). | 30 min |
| Remove Multi-select Field Type | Reference Update | `core-concepts/forms.mdx` | Remove "Multi-select" from field types (does not exist in codebase). | 30 min |
| Fix Broken Doc Links | Reference Update | Multiple files | Fix data provider guide link in forms.mdx, context object reference link in context-field-references.mdx. | 1 hour |
| Fix Typo in Scopes | Reference Update | `core-concepts/scopes.mdx` | Fix "oranization" typo. | 5 min |

**Dependencies:** None
**Total Effort:** 5 hours

### Task Group 1B: MFA Documentation (New)

**Dependencies:** None

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Create MFA Configuration Guide | How-To Guide | `how-to-guides/authentication/mfa.mdx` (NEW) | TOTP enrollment flow, recovery codes, trusted devices (30-day bypass), MFA enforcement behavior. Include screenshots. | 4 hours |

### Task Group 1C: Code Engine Architecture Rewrite

**Dependencies:** Understanding of current Code Engine implementation

This is the most critical documentation gap. The current docs describe a deprecated JSON-based system.

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Rewrite App Builder Core Concepts | Explanation | `core-concepts/app-builder.mdx` | Complete rewrite. Explain Code Engine architecture, TSX/JSX compilation, file-based routing, Bifrost SDK imports. Remove all JSON-based content. | 8 hours |
| Create Code Engine Overview | Explanation | `sdk-reference/app-builder/code-engine.mdx` (NEW) | Browser-based Babel compilation, file structure (`pages/`, `components/`, `modules/`), special files (`_layout.tsx`, `_providers.tsx`), dynamic routes (`[param].tsx`). | 6 hours |
| Create SDK Hooks Reference | Reference | `sdk-reference/app-builder/sdk-hooks.mdx` (NEW) | Complete TypeScript signatures for: `useWorkflow<T>`, `runWorkflow`, `useParams`, `useSearchParams`, `useUser`, `navigate`, `useNavigate`, `useAppState`, `Link`, `NavLink`. | 4 hours |
| Create File Structure Guide | Reference | `sdk-reference/app-builder/file-structure.mdx` (NEW) | Path conventions, directory structure, dynamic route segments, layout files, providers file. Include examples. | 3 hours |

**Dependencies:** Task Group 1A should complete first (for accurate permission references)
**Total Effort:** 21 hours

### Task Group 1D: MCP Tools Update

**Dependencies:** Code Engine docs should exist to reference

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Update MCP Tools Reference | Reference | `how-to-guides/integrations/mcp-server.mdx` | Add all 40+ tools (currently ~25 documented). Add code file tools (`list_app_files`, `get_app_file`, `create_app_file`, `update_app_file`, `delete_app_file`). Document restricted vs default-enabled tools. | 4 hours |
| Update AI Coding System Instructions | How-To Guide | `how-to-guides/local-dev/ai-coding.md` | Expand tool list, add Code Engine app development section, add SDK hooks quick reference. | 3 hours |

**Dependencies:** Code Engine docs
**Total Effort:** 7 hours

### Task Group 1E: Component Reference Rewrite

**Dependencies:** Code Engine overview should exist

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Rewrite Components Reference | Reference | `sdk-reference/app-builder/components.mdx` | Replace JSON component schemas with shadcn/ui React components. Document all available components (Button, Card, Table, Dialog, etc.) and Lucide icons. Show "no import needed" pattern. | 4 hours |

**Dependencies:** Code Engine docs
**Total Effort:** 4 hours

---

## Phase 2: Core Feature Documentation

**Priority:** P1 - High impact features
**Effort:** 55-65 hours
**Timeline:** 2-3 weeks

New features and significant updates to existing documentation.

### Phase 2 Dependencies

```
Phase 1 Complete
    |
    +-- GitHub Sync (independent)
    +-- Entity Management (independent)
    +-- Admin Features (independent)
    +-- Authentication Enhancements (independent)
    +-- Agent System (depends on Code Engine for tool context)
    +-- SDK Files Module (independent)
```

### Task Group 2A: GitHub Sync Documentation (New Section)

**No existing documentation exists.** This is a major feature gap.

| Task | Category | File Path | Scope | Dependencies | Effort |
|------|----------|-----------|-------|--------------|--------|
| Create GitHub Sync Concepts | Explanation | `core-concepts/github-sync.mdx` (NEW) | API-based sync (no local git), preview-then-execute pattern, virtual file system, portable workflow refs. | None | 4 hours |
| Create GitHub Setup Guide | How-To Guide | `how-to-guides/source-control/github-setup.mdx` (NEW) | Connect GitHub account, select/create repo, configure branch, first sync. Screenshots. | Concepts doc | 4 hours |
| Create Syncing Changes Guide | How-To Guide | `how-to-guides/source-control/syncing-changes.mdx` (NEW) | Pull/push workflow, sync preview UI, entity-centric display. | Setup guide | 3 hours |
| Create Conflict Resolution Guide | How-To Guide | `how-to-guides/source-control/conflict-resolution.mdx` (NEW) | What causes conflicts, resolution options, orphan workflows. | Syncing guide | 3 hours |

**Total Effort:** 14 hours

### Task Group 2B: Entity Management Documentation (New Section)

**No existing documentation exists.**

| Task | Category | File Path | Scope | Dependencies | Effort |
|------|----------|-----------|-------|--------------|--------|
| Create Entity Management Concepts | Explanation | `core-concepts/entity-management.mdx` (NEW) | Four entity types overview, common properties, entity lifecycle. | None | 3 hours |
| Create Entity Management UI Guide | How-To Guide | `how-to-guides/admin/entity-management.mdx` (NEW) | Entity Management page walkthrough, filtering, multi-select, drag-and-drop reassignment. Screenshots. | Concepts doc | 4 hours |
| Create Dependency Graph Guide | How-To Guide | `how-to-guides/admin/dependency-graph.mdx` (NEW) | Visualization explained, relationship types, use cases (impact analysis). | Entity Management guide | 2 hours |

**Total Effort:** 9 hours

### Task Group 2C: Admin Features Documentation (New Section)

**No existing documentation exists.**

| Task | Category | File Path | Scope | Dependencies | Effort |
|------|----------|-----------|-------|--------------|--------|
| Create Execution Monitoring Guide | How-To Guide | `how-to-guides/admin/execution-monitoring.mdx` (NEW) | Logs View (cross-org aggregation), filter parameters, organization filter. | None | 4 hours |
| Create Stuck Execution Cleanup Guide | How-To Guide | `how-to-guides/admin/stuck-execution-cleanup.mdx` (NEW) | What constitutes stuck execution, cleanup dialog, API endpoints. | Monitoring guide | 3 hours |
| Create Execution Debugging Guide | How-To Guide | `how-to-guides/admin/execution-debugging.mdx` (NEW) | Runtime variables (admin-only), resource metrics (memory, CPU), admin vs user view comparison. | None | 3 hours |
| Update Error Handling Doc | Explanation Update | `core-concepts/error-handling.mdx` | Add explicit note about DEBUG/TRACEBACK log filtering for non-admins. | None | 1 hour |

**Total Effort:** 11 hours

### Task Group 2D: Authentication Enhancements

**Builds on existing SSO documentation.**

| Task | Category | File Path | Scope | Dependencies | Effort |
|------|----------|-----------|-------|--------------|--------|
| Create Authentication Architecture Overview | Explanation | `core-concepts/authentication-overview.mdx` (NEW) | Two OAuth systems (User SSO vs Integration OAuth), architecture diagram, security model. | None | 4 hours |
| Document Device Authorization Flow | How-To Guide | `how-to-guides/authentication/device-auth.mdx` (NEW) or update `local-dev/setup.mdx` | RFC 8628 flow, CLI authentication, user code verification. | None | 3 hours |
| Document User Provisioning | How-To Guide | `how-to-guides/admin/user-provisioning.mdx` (NEW) | First-user bootstrap (becomes superuser), OAuth user auto-provisioning, email domain matching. | Auth overview | 2 hours |
| Expand OAuth Troubleshooting | How-To Guide | `troubleshooting/oauth.md` | Add connection status table, refresh scheduler details, cache invalidation. | None | 2 hours |
| Update SSO Guide (PKCE) | How-To Guide | `how-to-guides/authentication/sso.mdx` | Add server-side PKCE explanation, token lifecycle (30min access, 7day refresh). | None | 2 hours |

**Total Effort:** 13 hours

### Task Group 2E: Agent System Improvements

**Updates to existing documentation.**

| Task | Category | File Path | Scope | Dependencies | Effort |
|------|----------|-----------|-------|--------------|--------|
| Create Agents Core Concept | Explanation | `core-concepts/agents.mdx` (NEW) | What agents are, when to use them, agent vs direct AI completion, virtual entity architecture. | None | 4 hours |
| Document System Tools vs Workflow Tools | Reference Update | `how-to-guides/ai/agents-and-chat.mdx` | Clear distinction, `system_tools` array configuration, how to enable specific tools. | None | 2 hours |
| Document Coding Mode Details | Reference Update | `how-to-guides/ai/agents-and-chat.mdx` | Permission modes (PLAN vs EXECUTE), session management, interactive prompts, task tracking. | None | 2 hours |
| Document Delegation Tool Generation | Reference Update | `how-to-guides/ai/agents-and-chat.mdx` | Automatic `delegate_to_{agent_name}` tool generation, delegation management API. | None | 1 hour |

**Total Effort:** 9 hours

### Task Group 2F: SDK Files Module (New)

**No dedicated documentation exists.**

| Task | Category | File Path | Scope | Dependencies | Effort |
|------|----------|-----------|-------|--------------|--------|
| Create Files Module Reference | Reference | `sdk-reference/sdk/files-module.mdx` (NEW) | All file operations (`read`, `write`, `list`, `delete`, `exists`), `FileLocation` enum (workspace, temp, uploads), base64 binary support, mode parameter. | None | 4 hours |
| Fix OAuth References in Examples | Reference Update | `how-to-guides/workflows/writing-workflows.mdx`, `error-handling.mdx` | Replace incorrect `oauth.get()` with `integrations.get()`. Add `await` to async file operations. | None | 1 hour |

**Total Effort:** 5 hours

### Task Group 2G: Permissions and Scope Updates

**Enhances existing documentation.**

| Task | Category | File Path | Scope | Dependencies | Effort |
|------|----------|-----------|-------|--------------|--------|
| Rewrite Scopes Documentation | Explanation | `core-concepts/scopes.mdx` | Cascade scoping explanation with diagram, OrgFilterType values, practical examples. | None | 4 hours |
| Create Scopes Deep Dive | How-To Guide | `how-to-guides/scopes-deep-dive.mdx` (NEW) | Setting up global defaults with org overrides, when to use `scope="global"`, multi-tenant patterns. | Scopes rewrite | 3 hours |
| Document Access Levels | Reference Update | `core-concepts/permissions.md` | Document `authenticated` vs `role_based` access levels, workflow role sync, API reference. | None | 2 hours |

**Total Effort:** 9 hours

### Task Group 2H: Forms Updates

**Fixes and enhancements to existing docs.**

| Task | Category | File Path | Scope | Dependencies | Effort |
|------|----------|-----------|-------|--------------|--------|
| Update Field Types | Reference Update | `core-concepts/forms.mdx` | Add `datetime`, `markdown`, `html`. Remove non-existent `multi-select`. Document display-only fields. | None | 1 hour |
| Document Form Virtualization | Explanation Update | `core-concepts/forms.mdx` | Add architecture section explaining database-only storage, git sync serialization. | None | 2 hours |
| Create File Upload Guide | How-To Guide | `how-to-guides/forms/file-uploads.mdx` (NEW) | Presigned URLs, validation flow, multiple file handling, accessing files in workflows. | None | 3 hours |

**Total Effort:** 6 hours

---

## Phase 3: Polish and Completeness

**Priority:** P2 - Lower priority improvements
**Effort:** 35-45 hours
**Timeline:** 1-2 weeks

Minor updates, edge cases, and nice-to-have improvements.

### Phase 3 Dependencies

```
Phase 2 Complete (all groups)
    |
    +-- All polish tasks can run in parallel
```

### Task Group 3A: AI Coding Enhancements

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Add Tailwind 4 Documentation | Reference | `sdk-reference/app-builder/code-engine.mdx` | Note Tailwind 4 availability, safelisted patterns, typography plugin. | 1 hour |
| Add AI Coding Troubleshooting | How-To Guide | `how-to-guides/local-dev/ai-coding.md` | Common issues (path validation errors, workflow not found, scope issues). | 2 hours |
| Create Component Visual Showcase | Reference | `sdk-reference/app-builder/components.mdx` or new page | Visual examples for Code Engine components. | 4 hours |

**Total Effort:** 7 hours

### Task Group 3B: Agent System Polish

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Document Chat Stream Events | Reference | `how-to-guides/ai/agents-and-chat.mdx` | `ChatStreamChunk` schema, tool execution events, agent switch events. | 2 hours |
| Document Context Management | Explanation | `how-to-guides/ai/agents-and-chat.mdx` | Token estimation (~4 chars/token), context pruning at 120K tokens. | 1 hour |

**Total Effort:** 3 hours

### Task Group 3C: OAuth Polish

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Create Auth API Reference | Reference | `sdk-reference/api/auth.mdx` (NEW) | `/auth/*` and `/api/oauth/*` endpoints. | 4 hours |
| Document Encryption Key Management | Reference | `how-to-guides/integrations/secrets-management.mdx` | Key rotation procedures, ENCRYPTION_KEY vs BIFROST_SECRET_KEY. | 2 hours |
| Document Cache Invalidation | How-To Guide | `troubleshooting/oauth.md` | OAuth cache patterns, invalidation for stale token issues. | 1 hour |

**Total Effort:** 7 hours

### Task Group 3D: Forms Polish

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Document Expression Mode | How-To Guide | `how-to-guides/forms/cascading-dropdowns.mdx` | Expression mode for data provider inputs, syntax reference. | 2 hours |
| Document Launch to Main Workflow Flow | How-To Guide | `how-to-guides/forms/startup-workflows.mdx` | How `startup_data` flows to main workflow via `context.startup`. | 2 hours |
| Add SDK Forms Module Reference | Reference | `sdk-reference/sdk/forms-module.mdx` (NEW) | `forms.list()`, `forms.get()` methods. | 2 hours |
| Document Validation Patterns | Reference | `core-concepts/forms.mdx` | Validation properties (pattern, min, max, message), client vs server validation. | 2 hours |
| Document JSX Detection Logic | Reference | `how-to-guides/forms/html-content.mdx` | When JSX templating triggers (presence of `className=` or `{context.`). | 1 hour |

**Total Effort:** 9 hours

### Task Group 3E: Permissions Polish

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Document Entity-Role Junction Tables | Reference | `core-concepts/permissions.md` | FormRole, AgentRole, AppRole, WorkflowRole tables. | 1 hour |

**Total Effort:** 1 hour

### Task Group 3F: Scope Resolution Polish

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Standardize SDK Scope Parameter Docs | Reference | Multiple SDK reference files | Consistent wording across config, integrations, tables, knowledge modules. | 2 hours |
| Document Tables Three-Level Scoping | Reference | `sdk-reference/sdk/tables-module.mdx` | Organization, Application, Global scope levels explained. | 2 hours |
| Clarify context.scope vs SDK scope | Reference | `sdk-reference/sdk/context-api.mdx` | Execution context read-only vs SDK scope override parameter. | 1 hour |

**Total Effort:** 5 hours

### Task Group 3G: SDK Reference Additions

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Add @tool Decorator Documentation | Reference | `sdk-reference/sdk/decorators.mdx` | Shorthand for `@workflow(is_tool=True)`, equivalence example. | 1 hour |
| Create Workflows Module Reference | Reference | `sdk-reference/sdk/workflows-module.mdx` (NEW) | `workflows.list()`, `workflows.get()` methods. | 2 hours |
| Create Executions Module Reference | Reference | `sdk-reference/sdk/executions-module.mdx` (NEW) | `executions.list()`, `executions.get()` methods. | 2 hours |
| Expand ROI Tracking Documentation | How-To Guide | `sdk-reference/sdk/decorators.mdx` | How `time_saved` and `value` are captured, where ROI data appears in UI. | 1 hour |

**Total Effort:** 6 hours

### Task Group 3H: Virtual Files Reference

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Create Virtual Files Reference | Reference | `reference/virtual-files.mdx` (NEW) | Complete path patterns, entity types, export metadata structure. | 3 hours |
| Document App Directory Structure | Reference | `reference/app-directory-structure.mdx` (NEW) | `app.json` schema, code file organization, dependency tracking. | 2 hours |

**Total Effort:** 5 hours

### Task Group 3I: Troubleshooting Additions

| Task | Category | File Path | Scope | Effort |
|------|----------|-----------|-------|--------|
| Create GitHub Sync Troubleshooting | How-To Guide | `troubleshooting/github-sync.md` (NEW) | Common errors, authentication issues, serialization failures, unresolved references. | 3 hours |

**Total Effort:** 3 hours

---

## Appendix: Full Task List by Diataxis Category

### Tutorials (Getting Started)

*No new tutorials required in this overhaul. Existing tutorials are adequate.*

### How-To Guides

| Task | File Path | Phase | Effort |
|------|-----------|-------|--------|
| Create MFA Configuration Guide | `how-to-guides/authentication/mfa.mdx` | 1 | 4h |
| Create GitHub Setup Guide | `how-to-guides/source-control/github-setup.mdx` | 2 | 4h |
| Create Syncing Changes Guide | `how-to-guides/source-control/syncing-changes.mdx` | 2 | 3h |
| Create Conflict Resolution Guide | `how-to-guides/source-control/conflict-resolution.mdx` | 2 | 3h |
| Create Entity Management UI Guide | `how-to-guides/admin/entity-management.mdx` | 2 | 4h |
| Create Dependency Graph Guide | `how-to-guides/admin/dependency-graph.mdx` | 2 | 2h |
| Create Execution Monitoring Guide | `how-to-guides/admin/execution-monitoring.mdx` | 2 | 4h |
| Create Stuck Execution Cleanup Guide | `how-to-guides/admin/stuck-execution-cleanup.mdx` | 2 | 3h |
| Create Execution Debugging Guide | `how-to-guides/admin/execution-debugging.mdx` | 2 | 3h |
| Create Device Authorization Guide | `how-to-guides/authentication/device-auth.mdx` | 2 | 3h |
| Create User Provisioning Guide | `how-to-guides/admin/user-provisioning.mdx` | 2 | 2h |
| Create File Upload Guide | `how-to-guides/forms/file-uploads.mdx` | 2 | 3h |
| Create Scopes Deep Dive | `how-to-guides/scopes-deep-dive.mdx` | 2 | 3h |
| Expand OAuth Troubleshooting | `troubleshooting/oauth.md` | 2 | 2h |
| Update SSO Guide (PKCE) | `how-to-guides/authentication/sso.mdx` | 2 | 2h |
| Update AI Coding Instructions | `how-to-guides/local-dev/ai-coding.md` | 1 | 3h |
| Add AI Coding Troubleshooting | `how-to-guides/local-dev/ai-coding.md` | 3 | 2h |
| Create GitHub Sync Troubleshooting | `troubleshooting/github-sync.md` | 3 | 3h |

### Reference (SDK/API)

| Task | File Path | Phase | Effort |
|------|-----------|-------|--------|
| Create Code Engine Overview | `sdk-reference/app-builder/code-engine.mdx` | 1 | 6h |
| Create SDK Hooks Reference | `sdk-reference/app-builder/sdk-hooks.mdx` | 1 | 4h |
| Create File Structure Guide | `sdk-reference/app-builder/file-structure.mdx` | 1 | 3h |
| Update MCP Tools Reference | `how-to-guides/integrations/mcp-server.mdx` | 1 | 4h |
| Rewrite Components Reference | `sdk-reference/app-builder/components.mdx` | 1 | 4h |
| Create Files Module Reference | `sdk-reference/sdk/files-module.mdx` | 2 | 4h |
| Fix Agent Access Levels | `how-to-guides/ai/agents-and-chat.mdx` | 1 | 2h |
| Fix @mention Syntax | `how-to-guides/ai/agents-and-chat.mdx` | 1 | 30m |
| Create Auth API Reference | `sdk-reference/api/auth.mdx` | 3 | 4h |
| Add SDK Forms Module Reference | `sdk-reference/sdk/forms-module.mdx` | 3 | 2h |
| Create Workflows Module Reference | `sdk-reference/sdk/workflows-module.mdx` | 3 | 2h |
| Create Executions Module Reference | `sdk-reference/sdk/executions-module.mdx` | 3 | 2h |
| Create Virtual Files Reference | `reference/virtual-files.mdx` | 3 | 3h |
| Create App Directory Structure Reference | `reference/app-directory-structure.mdx` | 3 | 2h |

### Explanation (Core Concepts)

| Task | File Path | Phase | Effort |
|------|-----------|-------|--------|
| Rewrite App Builder Core Concepts | `core-concepts/app-builder.mdx` | 1 | 8h |
| Create GitHub Sync Concepts | `core-concepts/github-sync.mdx` | 2 | 4h |
| Create Entity Management Concepts | `core-concepts/entity-management.mdx` | 2 | 3h |
| Create Authentication Architecture | `core-concepts/authentication-overview.mdx` | 2 | 4h |
| Create Agents Core Concept | `core-concepts/agents.mdx` | 2 | 4h |
| Rewrite Scopes Documentation | `core-concepts/scopes.mdx` | 2 | 4h |
| Update Error Handling Doc | `core-concepts/error-handling.mdx` | 2 | 1h |
| Document Platform Admin Bypass | `core-concepts/permissions.md` | 1 | 1h |
| Document Access Levels | `core-concepts/permissions.md` | 2 | 2h |
| Update Field Types | `core-concepts/forms.mdx` | 2 | 1h |
| Document Form Virtualization | `core-concepts/forms.mdx` | 2 | 2h |

---

## New Directory Structure

After implementation, the documentation will include these new directories and files:

```
src/content/docs/
├── core-concepts/
│   ├── agents.mdx                     # NEW
│   ├── authentication-overview.mdx     # NEW
│   ├── entity-management.mdx           # NEW
│   ├── github-sync.mdx                 # NEW
│   ├── app-builder.mdx                 # REWRITE
│   ├── scopes.mdx                      # REWRITE
│   ├── permissions.md                  # UPDATE
│   ├── forms.mdx                       # UPDATE
│   └── error-handling.mdx              # UPDATE
├── how-to-guides/
│   ├── admin/                          # NEW DIRECTORY
│   │   ├── entity-management.mdx
│   │   ├── dependency-graph.mdx
│   │   ├── execution-monitoring.mdx
│   │   ├── stuck-execution-cleanup.mdx
│   │   ├── execution-debugging.mdx
│   │   └── user-provisioning.mdx
│   ├── source-control/                 # NEW DIRECTORY
│   │   ├── github-setup.mdx
│   │   ├── syncing-changes.mdx
│   │   └── conflict-resolution.mdx
│   ├── authentication/
│   │   ├── mfa.mdx                     # NEW
│   │   ├── device-auth.mdx             # NEW
│   │   └── sso.mdx                     # UPDATE
│   ├── forms/
│   │   └── file-uploads.mdx            # NEW
│   ├── scopes-deep-dive.mdx            # NEW
│   └── ...
├── sdk-reference/
│   ├── app-builder/
│   │   ├── code-engine.mdx             # NEW
│   │   ├── sdk-hooks.mdx               # NEW
│   │   ├── file-structure.mdx          # NEW
│   │   └── components.mdx              # REWRITE
│   ├── sdk/
│   │   ├── files-module.mdx            # NEW
│   │   ├── forms-module.mdx            # NEW
│   │   ├── workflows-module.mdx        # NEW
│   │   └── executions-module.mdx       # NEW
│   └── api/
│       └── auth.mdx                    # NEW
├── reference/
│   ├── virtual-files.mdx               # NEW
│   └── app-directory-structure.mdx     # NEW
└── troubleshooting/
    ├── github-sync.md                  # NEW
    └── oauth.md                        # UPDATE
```

---

## Implementation Notes

### Parallel Execution Strategy

For maximum efficiency with multiple writers/agents:

**Wave 1 (Week 1-2):**
- Writer A: Security fixes (Task Group 1A) + MFA (1B)
- Writer B: Code Engine rewrite (Task Group 1C)
- Writer C: MCP tools update (Task Group 1D) + Components (1E)

**Wave 2 (Week 2-3):**
- Writer A: GitHub Sync (Task Group 2A)
- Writer B: Entity Management (2B) + Admin Features (2C)
- Writer C: Authentication (2D) + Agent System (2E)
- Writer D: SDK Files Module (2F) + Permissions/Scopes (2G) + Forms (2H)

**Wave 3 (Week 4-5):**
- All writers can work on Phase 3 tasks in parallel

### Quality Checks

Before marking any task complete:
- Verify no internal code paths are referenced
- Ensure all code examples use public SDK/API
- Confirm Diataxis category is correct
- Check for broken links
- Verify screenshots match current UI (where applicable)

### Inaccuracies to Fix Immediately

These specific inaccuracies should be fixed as part of Phase 1:

1. **Agent "Public" access level** - Remove (does not exist)
2. **@mention syntax** - Change from `@agent-name` to `@[Agent Name]`
3. **Multi-select field type** - Remove (does not exist)
4. **Data provider guide link** - Fix broken link in forms.mdx
5. **Context object reference link** - Fix broken link
6. **`list_data_providers` tool name** - Update to correct name
7. **`oauth.get()` in examples** - Change to `integrations.get()`
