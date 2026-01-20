# Agents - Documentation Review Findings

## Source of Truth

See main findings document: `/Users/jack/GitHub/bifrost-integrations-docs/docs/plans/documentation-overhaul/agents.md`

---

## Documentation State

_Completed by Docs Review Agent on 2026-01-20_

### Existing Docs

| File | Purpose | Last Updated |
|------|---------|--------------|
| `/src/content/docs/how-to-guides/ai/agents-and-chat.mdx` | Main agents and chat documentation | Current |
| `/src/content/docs/how-to-guides/ai/knowledge-bases.mdx` | Knowledge base / RAG documentation | Current |
| `/src/content/docs/how-to-guides/ai/llm-configuration.mdx` | LLM provider configuration | Current |
| `/src/content/docs/how-to-guides/ai/using-ai-in-workflows.mdx` | AI completions in workflows | Current |
| `/src/content/docs/sdk-reference/sdk/ai-module.mdx` | AI module SDK reference | Current |
| `/src/content/docs/sdk-reference/sdk/knowledge-module.mdx` | Knowledge module SDK reference | Current |

**Note:** There is NO dedicated "Agents" page in core-concepts. Agent information is only in how-to-guides.

---

### Gaps Identified

#### 1. Agent Architecture (CRITICAL GAP)

**Codebase Reality:**
- Agents are **virtual database entities only** - no file storage
- Git sync serializes agents on-the-fly from database to `agents/{id}.agent.json`
- Uses `VirtualFileProvider` and `AgentIndexer` for serialization/deserialization
- Portable workflow refs (UUID to path::function_name) for cross-environment sync

**Current Docs:** Silent on architecture. Users may incorrectly assume agents have file-based storage or not understand how Git sync works with agents.

**Impact:** High - MSPs need to understand this for multi-environment deployment.

---

#### 2. Agent Access Control (SIGNIFICANT GAP)

**Codebase Reality:**
- Two access levels: `AUTHENTICATED` and `ROLE_BASED`
- Role-based access uses `AgentRole` junction table
- Cascade pattern: org users see their org's agents + global agents (org_id=NULL)
- Platform admins bypass role restrictions

**Current Docs:** Has a basic table showing "Public, Authenticated, Role-based" levels but:
- Mentions "Public" access level which is NOT in the current model (code shows `ROLE_BASED` and `AUTHENTICATED` only)
- Does not explain the cascade scoping pattern (org + global)
- Does not explain platform admin bypass
- Does not document role assignment

**Impact:** Medium-High - Incorrect access level documentation could cause security misconfigurations.

---

#### 3. System Tools vs Workflow Tools (MODERATE GAP)

**Codebase Reality:**
- **Workflow tools**: Assigned via `AgentTool` junction table, workflows with `type='tool'`
- **System tools**: Stored in `system_tools` array on agent, auto-discovered via `@system_tool` decorator
- System tools available: 18+ tools including file ops, workflow execution, form management, knowledge search
- Coding Agent gets ALL system tools by default

**Current Docs:** Lists system tools in the "Coding Agent" section but:
- Does not explain the difference between system tools and workflow tools clearly
- Does not document how to configure system tools for custom agents
- Missing: `system_tools` configuration field

**Impact:** Medium - Users may not understand how to configure agent capabilities.

---

#### 4. Coding Mode / Claude Agent SDK (MODERATE GAP)

**Codebase Reality:**
- `is_coding_mode` flag enables Claude Agent SDK
- Permission modes: `PLAN` (read-only) and `EXECUTE` (full access)
- MCP integration with Bifrost-specific tools
- Session management via Redis with 24hr TTL
- `AskUserQuestion` for interactive prompts during execution
- `TodoWrite` for task tracking

**Current Docs:** Documents the Coding Agent and lists system tools but:
- Missing: Permission modes (PLAN vs EXECUTE)
- Missing: Session management behavior
- Missing: MCP integration details
- Missing: Interactive prompt (`AskUserQuestion`) functionality
- Missing: Task tracking (`TodoWrite`) functionality

**Impact:** Medium - Power users cannot fully leverage coding mode capabilities.

---

#### 5. Agent Delegation (MINOR GAP)

**Codebase Reality:**
- Parent-child delegation via `AgentDelegation` junction table
- Delegation generates `delegate_to_{agent_name}` tools automatically
- Self-delegation prevented by validation
- Delegation endpoints for CRUD operations

**Current Docs:** Mentions delegation exists with "Delegation is useful for specialized agents" tip, but:
- Missing: How delegation tools are generated (automatic naming convention)
- Missing: API endpoints for managing delegations
- Missing: Self-delegation prevention

**Impact:** Low - Basic concept is documented, details are missing.

---

#### 6. Chat System (MINOR GAP)

**Codebase Reality:**
- `Conversation` model with nullable `agent_id` for agentless chat
- `Message` model with roles: USER, ASSISTANT, TOOL, SYSTEM
- Message includes `tool_calls`, `tool_call_id`, `execution_id` for full traceability
- WebSocket streaming support
- Token estimation (~4 chars/token) and context pruning at 120K tokens

**Current Docs:** Documents basic chat API and WebSocket streaming but:
- Missing: Message model details (tool_calls, execution_id for log retrieval)
- Missing: Context management (token estimation, pruning, summarization)
- Missing: Agentless chat routing behavior details

**Impact:** Low - Basic functionality documented, advanced features missing.

---

#### 7. Agent Routing (DOCUMENTED BUT OUTDATED)

**Codebase Reality:**
- `@[Agent Name]` mention syntax with regex parsing
- AI-based intent routing for agentless conversations
- `AgentRouter.route_message()` considers description, tools, knowledge sources
- `strip_mention()` removes mention from message before processing

**Current Docs:** Documents @mentions and agentless routing but:
- Uses `@agent-name` syntax in examples (docs show lowercase-dash, code uses `@[Agent Name]` with brackets)
- Missing: How AI routing considers agent capabilities

**Impact:** Low - Syntax inconsistency could confuse users.

---

#### 8. Streaming Response Format (MINOR GAP)

**Codebase Reality:**
- `ChatStreamChunk` unified format for regular + coding mode
- Includes: `ToolCall`, `ToolResult`, `ToolProgress`
- Includes: `TodoItem`, `AskUserQuestion` for coding mode
- Includes: `AgentSwitch`, `ContextWarning` events

**Current Docs:** Shows basic WebSocket streaming but:
- Missing: Full `ChatStreamChunk` schema
- Missing: Tool execution events in stream
- Missing: Agent switch events
- Missing: Context warning events

**Impact:** Low - Developers building custom UIs need this.

---

#### 9. Missing Core Concept Page

**Gap:** No dedicated `/core-concepts/agents.mdx` page exists. All agent documentation is in how-to-guides, but agents deserve a conceptual overview page explaining:
- What agents are and when to use them
- Agent vs direct AI completion trade-offs
- Architecture overview (virtual entities, tool assignment, delegation)

**Impact:** Medium - New users lack conceptual foundation.

---

### Recommended Actions

#### Priority 1 - Critical (Security/Correctness)

1. **Fix Access Level Documentation**
   - Remove "Public" access level from docs (does not exist)
   - Clarify `AUTHENTICATED` vs `ROLE_BASED`
   - Document cascade scoping pattern
   - Add role assignment documentation

2. **Document Agent Architecture**
   - Add section explaining agents are database-only
   - Document Git sync serialization behavior
   - Explain portable workflow refs for multi-environment

#### Priority 2 - High Impact

3. **Clarify Tool Integration**
   - Add clear section distinguishing workflow tools vs system tools
   - Document `system_tools` array configuration
   - Show how to enable specific system tools for custom agents

4. **Expand Coding Mode Documentation**
   - Document permission modes (PLAN vs EXECUTE)
   - Document session management
   - Document interactive prompts and task tracking

5. **Create Core Concept Page**
   - Create `/core-concepts/agents.mdx` with conceptual overview
   - Link from how-to-guide

#### Priority 3 - Completeness

6. **Fix @mention Syntax**
   - Update examples to use `@[Agent Name]` syntax (with brackets)

7. **Document Chat Stream Events**
   - Add section on streaming response format
   - Document tool execution events
   - Document agent switch events

8. **Expand Delegation Documentation**
   - Document automatic tool generation
   - Document delegation management API

---

### Documentation Accuracy Summary

| Topic | Current State | Action Needed |
|-------|---------------|---------------|
| Basic Agent CRUD | Accurate | Minor updates |
| Access Levels | **Incorrect** | Fix immediately |
| Workflow Tools (`is_tool=True`) | Accurate | None |
| System Tools | Partial | Expand |
| Knowledge Sources | Accurate | None |
| Chat API Basics | Accurate | None |
| WebSocket Streaming | Partial | Expand |
| @Mentions | Syntax wrong | Fix examples |
| Agent Delegation | Partial | Expand |
| Coding Agent | Partial | Expand |
| Agent Architecture | **Missing** | Add |
| Context Management | **Missing** | Add |

---

### Files to Update

1. `/src/content/docs/how-to-guides/ai/agents-and-chat.mdx` - Primary updates
2. `/src/content/docs/core-concepts/agents.mdx` - **Create new file**
3. `/src/content/docs/sdk-reference/sdk/ai-module.mdx` - Link to agents

### Estimated Effort

- Priority 1 fixes: 2-3 hours
- Priority 2 additions: 4-6 hours
- Priority 3 completeness: 2-3 hours
- **Total: 8-12 hours**
