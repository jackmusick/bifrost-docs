# OAuth and Authentication System - Findings

This document provides a comprehensive technical review of the OAuth and Authentication system in the Bifrost platform.

## Source of Truth

### Overview

The Bifrost platform has **two distinct authentication systems** that serve different purposes:

1. **User Authentication (SSO)** - Authenticates platform users (administrators, developers) via OAuth/SSO providers
2. **Integration OAuth Connections** - Authenticates integrations to access third-party APIs (Microsoft Graph, etc.)

These systems share some infrastructure but have separate code paths, data models, and purposes.

---

## 1. User Authentication (SSO)

### Purpose
Authenticates users who access the Bifrost platform itself. Supports multiple authentication methods.

### Supported Authentication Methods

| Method | Description | Status |
|--------|-------------|--------|
| Email/Password | Traditional login with MFA requirement | Active |
| Microsoft Entra ID | OAuth 2.0 + OIDC with PKCE | Active |
| Google OAuth | OAuth 2.0 + OIDC with PKCE | Active |
| Generic OIDC | Any OIDC-compliant provider (Okta, Auth0, Keycloak) | Active |
| Passkeys/WebAuthn | Passwordless authentication via biometrics | Active |
| Device Authorization | RFC 8628 flow for CLI tools | Active |

### Key Files - Backend

| File | Purpose |
|------|---------|
| `/Users/jack/GitHub/bifrost/api/src/routers/auth.py` | Main authentication router - login, logout, token refresh, MFA, device auth, passkeys |
| `/Users/jack/GitHub/bifrost/api/src/routers/oauth_sso.py` | OAuth SSO router - provider list, OAuth flow init, callback handling, account linking |
| `/Users/jack/GitHub/bifrost/api/src/routers/oauth_config.py` | OAuth SSO configuration router - admin endpoints to configure providers |
| `/Users/jack/GitHub/bifrost/api/src/services/oauth_sso.py` | Core OAuth SSO service - PKCE generation, token exchange, user info retrieval |
| `/Users/jack/GitHub/bifrost/api/src/services/oauth_config_service.py` | OAuth provider configuration CRUD in database |
| `/Users/jack/GitHub/bifrost/api/src/models/orm/users.py` | User ORM model with authentication fields |
| `/Users/jack/GitHub/bifrost/api/src/models/orm/mfa.py` | MFA methods, recovery codes, trusted devices, OAuth accounts, passkeys |

### Key Files - Frontend

| File | Purpose |
|------|---------|
| `/Users/jack/GitHub/bifrost/client/src/contexts/AuthContext.tsx` | Authentication state management, JWT handling, login methods |
| `/Users/jack/GitHub/bifrost/client/src/pages/Login.tsx` | Login page with all authentication options |
| `/Users/jack/GitHub/bifrost/client/src/pages/AuthCallback.tsx` | OAuth SSO callback handler |
| `/Users/jack/GitHub/bifrost/client/src/pages/settings/OAuth.tsx` | Admin UI for configuring OAuth SSO providers |

### Authentication Flow Architecture

#### Email/Password with MFA
```
1. POST /auth/login (email/password)
2. If MFA not enrolled -> return mfa_setup_required + mfa_token
3. If MFA enrolled:
   a. Check trusted device -> skip MFA, return tokens
   b. Otherwise -> return mfa_required + mfa_token + available_methods
4. POST /auth/mfa/login (mfa_token + code) -> JWT tokens
```

#### OAuth SSO Flow
```
1. GET /auth/oauth/init/{provider}?redirect_uri=...
   - Generates PKCE code_verifier and state
   - Stores code_verifier in Redis (keyed by state) - NEVER sent to client
   - Returns authorization_url + state
2. User redirects to provider, authenticates
3. Provider redirects to /auth/callback with code + state
4. POST /auth/oauth/callback (provider, code, state)
   - Retrieves code_verifier from Redis using state (single-use)
   - Exchanges code for tokens using PKCE
   - Gets user info from provider
   - Provisions user if new (ensure_user_provisioned)
   - Links OAuth account to user
   - Returns JWT access + refresh tokens
```

#### Device Authorization Flow (RFC 8628)
```
1. POST /auth/device/code
   - Returns device_code, user_code, verification_url
2. CLI displays user_code, user visits /device
3. User enters code, approves access
4. POST /auth/device/authorize (authenticated) - marks device_code as authorized
5. CLI polls POST /auth/device/token
   - Returns tokens when authorized
```

### JWT Token Structure

**Access Token Claims:**
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "name": "User Name",
  "is_superuser": true,
  "org_id": "org-uuid-or-null",
  "roles": ["authenticated", "PlatformAdmin"],
  "oauth_provider": "microsoft"  // if OAuth login
}
```

**Token Lifetimes:**
- Access token: 30 minutes
- Refresh token: 7 days (stored in Redis with JTI for revocation)

### Security Features

| Feature | Implementation |
|---------|----------------|
| PKCE | Code verifier stored server-side in Redis, never sent to client |
| CSRF Protection | State parameter validated against Redis |
| Token Rotation | Refresh tokens are single-use (JTI deleted on use) |
| HttpOnly Cookies | Access/refresh tokens in HttpOnly cookies for browser clients |
| MFA Enforcement | Required for email/password login |
| Trusted Devices | Device fingerprinting for MFA bypass |
| Rate Limiting | 10 requests/minute for login, 5/minute for MFA |

### OAuth SSO Provider Configuration

Stored in `system_configs` table with category `oauth_sso`:

| Provider | Config Keys |
|----------|-------------|
| Microsoft | `microsoft_client_id`, `microsoft_client_secret` (encrypted), `microsoft_tenant_id` |
| Google | `google_client_id`, `google_client_secret` (encrypted) |
| OIDC | `oidc_discovery_url`, `oidc_client_id`, `oidc_client_secret` (encrypted), `oidc_display_name` |

---

## 2. Integration OAuth Connections

### Purpose
Authenticates Bifrost integrations to access external APIs (Microsoft Graph, ConnectWise, HaloPSA, etc.) on behalf of the organization.

### Key Distinction from User Auth
- User auth authenticates **people** to the Bifrost platform
- Integration OAuth authenticates **Bifrost** to third-party services

### Key Files - Backend

| File | Purpose |
|------|---------|
| `/Users/jack/GitHub/bifrost/api/src/routers/oauth_connections.py` | OAuth connection CRUD, authorization flow, token refresh |
| `/Users/jack/GitHub/bifrost/api/src/services/oauth_provider.py` | OAuth provider HTTP client - token exchange, refresh with retry logic |
| `/Users/jack/GitHub/bifrost/api/src/services/oauth_storage.py` | OAuth credential storage operations |
| `/Users/jack/GitHub/bifrost/api/src/models/orm/oauth.py` | OAuthProvider and OAuthToken ORM models |
| `/Users/jack/GitHub/bifrost/api/src/models/contracts/oauth.py` | Pydantic models for OAuth connections API |
| `/Users/jack/GitHub/bifrost/api/src/jobs/schedulers/oauth_token_refresh.py` | Background job for automatic token refresh |

### Key Files - Frontend

| File | Purpose |
|------|---------|
| `/Users/jack/GitHub/bifrost/client/src/hooks/useOAuth.ts` | React Query hooks for OAuth connection management |
| `/Users/jack/GitHub/bifrost/client/src/pages/OAuthCallback.tsx` | Integration OAuth callback handler |
| `/Users/jack/GitHub/bifrost/client/src/components/oauth/OAuthConnectionCard.tsx` | OAuth connection status card component |
| `/Users/jack/GitHub/bifrost/client/src/components/oauth/CreateOAuthConnectionDialog.tsx` | Dialog to create new OAuth connections |

### Database Schema

**oauth_providers table:**
```sql
- id: UUID
- provider_name: String(100)
- display_name: String(255)
- description: Text
- oauth_flow_type: String(50)  -- authorization_code, client_credentials
- client_id: String(255)
- encrypted_client_secret: LargeBinary  -- Fernet encrypted
- authorization_url: String(500)  -- may contain {entity_id} placeholder
- token_url: String(500)  -- may contain {entity_id} placeholder
- token_url_defaults: JSONB  -- e.g., {"entity_id": "common"}
- scopes: JSONB  -- list of scopes
- status: String(50)  -- not_connected, waiting_callback, completed, failed
- status_message: Text
- last_token_refresh: DateTime
- organization_id: UUID (FK -> organizations)
- integration_id: UUID (FK -> integrations)
```

**oauth_tokens table:**
```sql
- id: UUID
- organization_id: UUID
- provider_id: UUID (FK -> oauth_providers)
- user_id: UUID (FK -> users)  -- optional
- encrypted_access_token: LargeBinary
- encrypted_refresh_token: LargeBinary
- expires_at: DateTime
- scopes: JSONB
```

### OAuth Flow Types

| Flow Type | Use Case | User Interaction |
|-----------|----------|------------------|
| `authorization_code` | User-delegated access (Microsoft Graph, etc.) | User approves access in browser |
| `client_credentials` | Application-only access (service-to-service) | None - uses client ID/secret |

### Integration OAuth Flow

```
1. Create OAuth connection via API/UI
   - Linked to an Integration via integration_id
   - Stores client_id, encrypted_client_secret, URLs, scopes
2. POST /api/oauth/connections/{name}/authorize
   - Generates state, builds authorization URL
   - Sets status to "waiting_callback"
   - Returns authorization_url for redirect
3. User authorizes in provider's UI
4. Provider redirects to /oauth/callback/{name}
5. POST /api/oauth/callback/{name} (code, state, redirect_uri)
   - Exchanges code for tokens
   - Encrypts and stores access_token + refresh_token
   - Updates status to "completed"
```

### URL Template Resolution

OAuth URLs can contain placeholders like `{entity_id}` for multi-tenant scenarios:

```python
# Example Microsoft Graph token URL with tenant placeholder
token_url = "https://login.microsoftonline.com/{entity_id}/oauth2/v2.0/token"
defaults = {"entity_id": "common"}

# Resolves to: https://login.microsoftonline.com/common/oauth2/v2.0/token
```

Resolution logic in `/Users/jack/GitHub/bifrost/api/src/services/oauth_provider.py`:
- `resolve_url_template(url, entity_id, defaults)` function
- Falls back to `token_url_defaults` from provider config
- Falls back to `default_entity_id` from linked Integration

### Token Refresh

**Automatic Background Refresh:**
- Scheduler runs every 15 minutes (`oauth_token_refresh.py`)
- Refreshes tokens expiring within 20 minutes (15 min interval + 5 min buffer)
- Updates `encrypted_access_token`, `encrypted_refresh_token`, `expires_at`
- Preserves old refresh token if new one not returned

**Manual Refresh:**
- `POST /api/oauth/connections/{name}/refresh`
- Triggered from UI or API

**Refresh Job Status:**
- Stored in `system_configs` table (category='oauth', key='refresh_job_status')
- Tracks: connections_checked, refreshed_successfully, refresh_failed, errors
- Visible in admin UI via `GET /api/oauth/refresh_job_status`

### Connection Statuses

| Status | Description |
|--------|-------------|
| `not_connected` | Connection created but not authorized |
| `waiting_callback` | Authorization initiated, waiting for callback |
| `testing` | Connection being tested |
| `connected` | Legacy status |
| `completed` | Token acquired successfully |
| `failed` | Token exchange or refresh failed |

### Credential Access (for Workflows)

Workflows access OAuth credentials via:
```python
# GET /api/oauth/credentials/{connection_name}
# Returns decrypted access_token for use in API calls
```

Returned `OAuthCredentials` object provides:
- `access_token` - Current access token
- `token_type` - Usually "Bearer"
- `expires_at` - Token expiration timestamp
- `refresh_token` - For manual refresh if needed
- `is_expired()` - Check if token is expired
- `get_auth_header()` - Returns formatted "Bearer {token}" header

---

## 3. Credential Storage and Encryption

### Encryption Method
- **Algorithm:** Fernet (symmetric encryption)
- **Key:** `ENCRYPTION_KEY` environment variable
- **Functions:** `encrypt_secret()` / `decrypt_secret()` in `/Users/jack/GitHub/bifrost/api/src/core/security.py`

### What's Encrypted

| Data | Storage Location |
|------|-----------------|
| OAuth SSO client secrets | `system_configs.value_json.value` (encrypted string) |
| Integration client secrets | `oauth_providers.encrypted_client_secret` (bytes) |
| Access tokens | `oauth_tokens.encrypted_access_token` (bytes) |
| Refresh tokens | `oauth_tokens.encrypted_refresh_token` (bytes) |
| MFA secrets | `user_mfa_methods.encrypted_secret` (string) |

### Cache Invalidation

OAuth-related cache keys use patterns like:
- `oauth:{org_id}:{provider_name}` - Connection configuration
- `oauth_token:{org_id}:{provider_name}` - Token data

Invalidation functions in `/Users/jack/GitHub/bifrost/api/src/core/cache/__init__.py`:
- `invalidate_oauth(org_id, provider_name)`
- `invalidate_oauth_token(org_id, provider_name)`

---

## 4. Multi-Factor Authentication (MFA)

### MFA Methods

| Method | Status | Storage |
|--------|--------|---------|
| TOTP (Time-based One-Time Password) | Active | `user_mfa_methods` table |
| Recovery Codes | Active | `mfa_recovery_codes` table |
| Passkeys/WebAuthn | Active | `user_passkeys` table |

### MFA Enrollment Flow
```
1. POST /auth/login -> returns mfa_setup_required + mfa_token
2. POST /auth/mfa/setup (mfa_token in header) -> returns secret + QR URI
3. User scans QR code in authenticator app
4. POST /auth/mfa/verify (mfa_token + code) -> validates code, returns recovery codes + JWT tokens
```

### Trusted Devices
- Device fingerprint based on User-Agent
- Can bypass MFA verification for 30 days (configurable)
- Stored in `trusted_devices` table
- Limited by IP address if configured

### Recovery Codes
- Generated during MFA enrollment
- 8 alphanumeric characters each
- Hashed before storage (never stored in plain text)
- Single-use (marked as used after verification)

---

## 5. User Provisioning

### First User Bootstrap
- First user to register/login becomes `is_superuser=True` (PlatformAdmin)
- Subsequent users are matched to organizations by email domain

### OAuth User Provisioning
When a user authenticates via OAuth for the first time:
1. `find_user_by_oauth()` checks if OAuth account is already linked
2. If not found, `ensure_user_provisioned()` creates or finds user by email
3. `link_oauth_account()` associates OAuth provider with user
4. Future logins use the linked OAuth account

### User Model Fields

```python
class User:
    id: UUID
    email: str (unique)
    name: str | None
    hashed_password: str | None  # None for OAuth-only users
    is_active: bool
    is_superuser: bool
    is_verified: bool
    is_registered: bool  # False for pre-created users awaiting registration
    mfa_enabled: bool
    mfa_enforced_at: datetime | None
    organization_id: UUID | None
    last_login: datetime | None
    webauthn_user_id: bytes | None  # For passkey authentication
```

---

## 6. API Endpoints Reference

### User Authentication (`/auth/*`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/login` | POST | Email/password login |
| `/auth/mfa/setup` | POST | Initialize MFA enrollment |
| `/auth/mfa/verify` | POST | Complete MFA enrollment |
| `/auth/mfa/login` | POST | MFA verification during login |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/logout` | POST | Logout and revoke refresh token |
| `/auth/revoke-all` | POST | Revoke all user sessions |
| `/auth/me` | GET | Get current user info |
| `/auth/status` | GET | Get auth system status (for login page) |
| `/auth/device/code` | POST | Request device authorization code |
| `/auth/device/token` | POST | Poll for device authorization tokens |
| `/auth/device/authorize` | POST | Authorize a device code |
| `/auth/setup/passkey/options` | POST | Start passkey registration |
| `/auth/setup/passkey/verify` | POST | Complete passkey registration |

### OAuth SSO (`/auth/oauth/*`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/oauth/providers` | GET | List available OAuth providers |
| `/auth/oauth/init/{provider}` | GET | Initialize OAuth flow |
| `/auth/oauth/callback` | POST | Complete OAuth flow |
| `/auth/oauth/accounts` | GET | List linked OAuth accounts |
| `/auth/oauth/accounts/{provider}` | DELETE | Unlink OAuth account |

### OAuth SSO Configuration (`/api/settings/oauth/*`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/settings/oauth` | GET | List all provider configurations |
| `/api/settings/oauth/{provider}` | GET | Get provider configuration |
| `/api/settings/oauth/microsoft` | PUT | Configure Microsoft OAuth |
| `/api/settings/oauth/google` | PUT | Configure Google OAuth |
| `/api/settings/oauth/oidc` | PUT | Configure OIDC provider |
| `/api/settings/oauth/{provider}` | DELETE | Delete provider configuration |
| `/api/settings/oauth/{provider}/test` | POST | Test provider configuration |

### Integration OAuth (`/api/oauth/*`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/oauth/connections` | GET | List OAuth connections |
| `/api/oauth/connections` | POST | Create OAuth connection |
| `/api/oauth/connections/{name}` | GET | Get connection details |
| `/api/oauth/connections/{name}` | PUT | Update connection |
| `/api/oauth/connections/{name}` | DELETE | Delete connection |
| `/api/oauth/connections/{name}/authorize` | POST | Start OAuth authorization |
| `/api/oauth/connections/{name}/cancel` | POST | Cancel pending authorization |
| `/api/oauth/connections/{name}/refresh` | POST | Manually refresh token |
| `/api/oauth/callback/{name}` | POST | Handle OAuth callback |
| `/api/oauth/credentials/{name}` | GET | Get credentials for workflow use |
| `/api/oauth/refresh_job_status` | GET | Get background refresh job status |
| `/api/oauth/refresh_all` | POST | Trigger manual refresh of all tokens |

---

## 7. Key Concepts for Documentation

### Concepts to Document

1. **Two OAuth Systems** - Clear distinction between user SSO and integration OAuth
2. **PKCE Flow** - Server-side code verifier storage pattern
3. **Token Lifecycle** - Access vs refresh, rotation, revocation
4. **MFA Enforcement** - Required for password login, trusted devices
5. **URL Templating** - `{entity_id}` placeholders for multi-tenant providers
6. **Automatic Token Refresh** - Background scheduler behavior
7. **Encryption Model** - What's encrypted, how keys are managed
8. **User Provisioning** - First user bootstrap, domain-based org matching

### Recent Changes

Based on code structure and patterns observed:

1. **Server-side PKCE** - Code verifier stored in Redis, never sent to client
2. **OAuth Callback Refactoring** - Integration OAuth callbacks separated from SSO callbacks
3. **URL Template Resolution** - Support for `{entity_id}` placeholders with defaults
4. **Integration Linking** - OAuth providers linked to integrations via `integration_id`
5. **Passkey Support** - WebAuthn passwordless authentication added
6. **Device Authorization Flow** - RFC 8628 for CLI authentication

---

## 8. Architecture Diagram

```
                                    BIFROST AUTHENTICATION ARCHITECTURE

    +-----------------+          +------------------+          +-------------------+
    |   Login Page    |          |   OAuth Provider |          |   External API    |
    |   (React)       |          |   (Microsoft,    |          |   (Graph, PSA,    |
    |                 |          |    Google, OIDC) |          |    etc.)          |
    +-----------------+          +------------------+          +-------------------+
            |                            ^                              ^
            v                            |                              |
    +-----------------+          +------------------+          +-------------------+
    |  AuthContext    |--------->|  OAuth SSO       |          |  OAuth Connection |
    |  (Frontend)     |   init   |  Flow            |          |  Token            |
    +-----------------+  callback+------------------+          +-------------------+
            |                            |                              ^
            v                            v                              |
    +-----------------+          +------------------+          +-------------------+
    |  /auth/*        |          | /auth/oauth/*    |          |  /api/oauth/*     |
    |  Router         |          | Router           |          |  Router           |
    +-----------------+          +------------------+          +-------------------+
            |                            |                              |
            v                            v                              v
    +-----------------+          +------------------+          +-------------------+
    |  User           |          | UserOAuthAccount |          |  OAuthProvider    |
    |  (users table)  |<-------->| (SSO links)      |          |  OAuthToken       |
    +-----------------+          +------------------+          +-------------------+
            |                                                           |
            v                                                           v
    +-----------------+                                         +-------------------+
    |  JWT Tokens     |                                         |  Encrypted        |
    |  (Redis JTI)    |                                         |  Credentials      |
    +-----------------+                                         +-------------------+
```

---

## 9. Testing Approach

### Unit Tests
- `/Users/jack/GitHub/bifrost/api/tests/unit/services/test_oauth_provider.py` - OAuth provider client
- `/Users/jack/GitHub/bifrost/api/tests/unit/services/test_oauth_url_templating.py` - URL template resolution
- `/Users/jack/GitHub/bifrost/api/tests/unit/models/test_oauth_credentials_contract.py` - Credential models
- `/Users/jack/GitHub/bifrost/api/tests/unit/models/test_oauth_api_contract.py` - API contracts

### E2E Tests
- `/Users/jack/GitHub/bifrost/api/tests/e2e/api/test_oauth.py` - OAuth connection flows
- `/Users/jack/GitHub/bifrost/api/tests/e2e/test_device_auth.py` - Device authorization flow
- `/Users/jack/GitHub/bifrost/client/e2e/oauth.admin.spec.ts` - Playwright E2E for OAuth admin UI

---

## 10. Documentation State

### Existing Documentation Files

| File | Purpose | Status |
|------|---------|--------|
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/how-to-guides/authentication/passkeys.mdx` | WebAuthn/Passkeys setup guide | Good - Complete |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/how-to-guides/authentication/sso.mdx` | SSO configuration (Microsoft, Google, OIDC) | Good - Complete |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/troubleshooting/oauth.md` | OAuth troubleshooting for integrations | Minimal - Needs expansion |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/how-to-guides/integrations/secrets-management.mdx` | Secrets encryption and storage | Good - Covers Fernet encryption |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/getting-started/integrations.mdx` | OAuth Integration tutorial (Microsoft Graph) | Good - Practical walkthrough |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/how-to-guides/integrations/microsoft-graph.mdx` | Microsoft Graph API patterns | Good - Workflow examples |
| `/Users/jack/GitHub/bifrost-integrations-docs/src/content/docs/how-to-guides/integrations/creating-integrations.mdx` | General integration creation | Adequate - Basic coverage |

### Gaps Identified

#### Critical Gaps (Major missing documentation)

1. **No clear distinction between User SSO and Integration OAuth**
   - Documentation treats them as overlapping concepts
   - Missing conceptual explanation of why two systems exist
   - Users may confuse SSO (for platform login) with Integration OAuth (for API access)
   - **Recommendation**: Create a new "OAuth Architecture" concept page explaining both systems

2. **Server-side PKCE implementation not documented**
   - The SSO guide doesn't mention PKCE at all
   - Critical security feature: code verifier stored server-side in Redis, never sent to client
   - Documentation claims standard OAuth but doesn't explain security enhancements
   - **Recommendation**: Add security section to SSO guide explaining PKCE implementation

3. **Device Authorization Flow (RFC 8628) not documented**
   - CLI/device authentication flow exists in codebase but is not mentioned in docs
   - Only brief mention in `local-dev/setup.mdx` without explanation
   - **Recommendation**: Create new page or section for CLI/device authentication

4. **MFA enforcement and flow not documented**
   - No documentation about MFA being required for password login
   - Missing: TOTP setup flow, recovery codes, trusted devices
   - **Recommendation**: Create MFA configuration guide for administrators and users

5. **Token lifecycle not fully documented**
   - Access token (30 min) and refresh token (7 days) lifetimes not mentioned
   - Single-use refresh token rotation not documented
   - JWT claims structure not documented
   - **Recommendation**: Add "Token Management" section to security docs

#### Moderate Gaps (Missing details in existing docs)

6. **URL templating with `{entity_id}` partially documented**
   - Mentioned in `getting-started/integrations.mdx` as a hint
   - Missing: explanation of resolution order (explicit > defaults > integration defaults)
   - Missing: multi-tenant pattern explanation
   - **Recommendation**: Expand URL templating section in creating-integrations guide

7. **Automatic token refresh behavior incomplete**
   - Docs mention "automatic refresh" but not the scheduler (15-minute interval)
   - Missing: 20-minute refresh window (15 min interval + 5 min buffer)
   - Missing: refresh job status monitoring (`/api/oauth/refresh_job_status`)
   - **Recommendation**: Add "Token Refresh Internals" section to troubleshooting guide

8. **OAuth connection statuses not documented**
   - Valid statuses: `not_connected`, `waiting_callback`, `testing`, `connected`, `completed`, `failed`
   - UI may show these but no documentation explains them
   - **Recommendation**: Add status table to OAuth troubleshooting guide

9. **User provisioning and first-user bootstrap not documented**
   - First user becomes superuser
   - OAuth users auto-provisioned on first login
   - Email domain matching to organizations
   - **Recommendation**: Create "User Management" or "User Provisioning" guide

10. **OAuth callback URL patterns inconsistent in docs**
    - SSO callbacks: `/auth/callback/{provider}` (mentioned in sso.mdx)
    - Integration callbacks: `/oauth/callback/{name}` (mentioned in integrations.mdx)
    - Docs don't clearly distinguish these callback patterns
    - **Recommendation**: Clarify callback URL patterns in both guides

#### Minor Gaps (Polish and completeness)

11. **API endpoints not documented**
    - No reference docs for `/auth/*` endpoints
    - No reference docs for `/api/oauth/*` endpoints
    - **Recommendation**: Add API reference section (low priority - most users use UI)

12. **Encryption key management briefly mentioned**
    - `BIFROST_SECRET_KEY` mentioned in secrets-management.mdx
    - Codebase uses `ENCRYPTION_KEY` in some places
    - Missing: key rotation procedures
    - **Recommendation**: Add key management section to deployment/security docs

13. **Cache invalidation not documented**
    - OAuth cache patterns and invalidation not mentioned
    - Relevant for troubleshooting stale token issues
    - **Recommendation**: Add cache section to troubleshooting guide

### Recommended Actions

#### High Priority (Create new content)

1. **Create `core-concepts/authentication-overview.mdx`**
   - Explain two OAuth systems (User SSO vs Integration OAuth)
   - Include the architecture diagram from findings
   - Link to specific how-to guides for each

2. **Create `how-to-guides/authentication/mfa.mdx`**
   - TOTP enrollment flow
   - Recovery codes
   - Trusted devices configuration
   - Admin management of user MFA

3. **Expand `troubleshooting/oauth.md`**
   - Add connection status table
   - Add refresh scheduler details
   - Add cache invalidation info
   - Improve error handling examples

#### Medium Priority (Enhance existing content)

4. **Update `how-to-guides/authentication/sso.mdx`**
   - Add PKCE security section explaining server-side storage
   - Add token lifecycle information (30 min access, 7 day refresh)
   - Add JWT claims structure for advanced users

5. **Update `how-to-guides/integrations/creating-integrations.mdx`**
   - Expand URL templating with `{entity_id}` examples
   - Add resolution order explanation
   - Add multi-tenant patterns section

6. **Create `how-to-guides/authentication/device-auth.mdx`** or add to `local-dev/setup.mdx`
   - Document RFC 8628 device authorization flow
   - CLI authentication workflow
   - User code verification process

#### Low Priority (Reference and polish)

7. **Create API reference for authentication endpoints**
   - `/auth/*` endpoints
   - `/api/oauth/*` endpoints
   - Could be auto-generated from OpenAPI spec

8. **Update secrets-management.mdx**
   - Clarify `ENCRYPTION_KEY` vs `BIFROST_SECRET_KEY`
   - Add key rotation procedures
   - Add external secret manager integration notes

### Documentation vs Codebase Consistency

| Feature | Codebase | Documentation | Match? |
|---------|----------|---------------|--------|
| Microsoft SSO | Implemented | Documented | Yes |
| Google SSO | Implemented | Documented | Yes |
| Generic OIDC | Implemented | Documented | Yes |
| Passkeys/WebAuthn | Implemented | Documented | Yes |
| Server-side PKCE | Implemented | Not mentioned | No |
| Device Auth Flow | Implemented | Not mentioned | No |
| MFA (TOTP) | Implemented | Not documented | No |
| Recovery Codes | Implemented | Not documented | No |
| Trusted Devices | Implemented | Not documented | No |
| Integration OAuth | Implemented | Documented | Yes |
| URL Templating | Implemented | Partially documented | Partial |
| Token Refresh Scheduler | Implemented | Mentioned without details | Partial |
| JWT Claims Structure | Implemented | Not documented | No |
| Encryption (Fernet) | Implemented | Documented | Yes |
| First-user Bootstrap | Implemented | Not documented | No |
