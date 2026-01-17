# Phases 16-22 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete Bifrost Docs V2 with user roles, advanced data tables, global view, soft delete, Tiptap editor, and data export.

**Architecture:** Role-based access control replaces `is_superuser`/`user_type`. Server-side pagination for all list endpoints. Shared page components for org/global views. Tiptap replaces custom markdown editor. Export generates ZIP files uploaded to S3 with WebSocket progress.

**Tech Stack:** FastAPI, SQLAlchemy (async), PostgreSQL, React, TanStack Table, Tiptap, Zustand, WebSockets

---

## Execution Tracks

This plan is organized into **parallel execution tracks**:

| Track                  | Phases                 | Dependencies    | Est. Tasks |
| ---------------------- | ---------------------- | --------------- | ---------- |
| **A: Roles**           | 16                     | None (do first) | 15         |
| **B: Tables Backend**  | 17.2, 17.3, 17.4, 18.3 | After Track A   | 20         |
| **C: Tables Frontend** | 17.1, 18.1, 18.2       | After Track B   | 12         |
| **D: Soft Delete**     | 19                     | After Track A   | 10         |
| **E: Tiptap**          | 20                     | After Track A   | 8          |
| **F: Export**          | 21                     | After Track A   | 15         |
| **G: Cleanup**         | 22                     | After all       | 5          |

**Recommended order:** A → (B, D, E, F in parallel) → C → G

---

## Track A: User Roles (Phase 16)

### Task A1: Create UserRole Enum

**Files:**

-   Modify: `api/src/models/contracts/enums.py`

**Step 1: Add UserRole enum**

```python
# Add to api/src/models/contracts/enums.py

class UserRole(str, Enum):
    OWNER = "owner"
    ADMINISTRATOR = "administrator"
    CONTRIBUTOR = "contributor"
    READER = "reader"

    @classmethod
    def can_edit_data(cls, role: "UserRole") -> bool:
        return role in (cls.OWNER, cls.ADMINISTRATOR, cls.CONTRIBUTOR)

    @classmethod
    def can_access_settings(cls, role: "UserRole") -> bool:
        return role in (cls.OWNER, cls.ADMINISTRATOR)

    @classmethod
    def can_manage_owners(cls, role: "UserRole") -> bool:
        return role == cls.OWNER
```

**Step 2: Run type check**

```bash
cd api && pyright src/models/contracts/enums.py
```

**Step 3: Commit**

```bash
git add api/src/models/contracts/enums.py
git commit -m "feat(auth): add UserRole enum with permission helpers"
```

---

### Task A2: Update User ORM Model

**Files:**

-   Modify: `api/src/models/orm/user.py`

**Step 1: Update User model**

Replace `is_superuser` and `user_type` with `role`:

```python
# In api/src/models/orm/user.py

from src.models.contracts.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    hashed_password: Mapped[str | None] = mapped_column(String(255))

    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    mfa_enabled: Mapped[bool] = mapped_column(default=False)

    # Replace is_superuser and user_type with role
    role: Mapped[UserRole] = mapped_column(
        SQLAlchemyEnum(UserRole, name="user_role", create_type=False),
        default=UserRole.CONTRIBUTOR
    )

    webauthn_user_id: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    last_login: Mapped[datetime | None] = mapped_column()

    # ... relationships remain the same
```

**Step 2: Run type check**

```bash
cd api && pyright src/models/orm/user.py
```

---

### Task A3: Write Role Migration

**Files:**

-   Create: `api/alembic/versions/20260113_000000_add_user_role.py`

**Step 1: Create migration file**

```python
"""Add user role enum and migrate from is_superuser/user_type

Revision ID: 20260113_000000
Revises: [previous_revision]
Create Date: 2026-01-13
"""
from alembic import op
import sqlalchemy as sa

revision = "20260113_000000"
down_revision = None  # Update with actual previous revision
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create the enum type
    op.execute("CREATE TYPE user_role AS ENUM ('owner', 'administrator', 'contributor', 'reader')")

    # Add role column with default
    op.add_column(
        "users",
        sa.Column("role", sa.Enum("owner", "administrator", "contributor", "reader", name="user_role"),
                  nullable=False, server_default="contributor")
    )

    # Migrate existing data: is_superuser=True -> owner, else contributor
    op.execute("""
        UPDATE users
        SET role = CASE
            WHEN is_superuser = true THEN 'owner'::user_role
            ELSE 'contributor'::user_role
        END
    """)

    # Drop old columns
    op.drop_column("users", "is_superuser")
    op.drop_column("users", "user_type")

    # Drop old enum if exists
    op.execute("DROP TYPE IF EXISTS usertype")

def downgrade() -> None:
    # Re-create old columns
    op.add_column("users", sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("user_type", sa.String(20), nullable=False, server_default="ORG"))

    # Migrate back
    op.execute("""
        UPDATE users
        SET is_superuser = (role = 'owner'),
            user_type = 'PLATFORM'
        WHERE role = 'owner'
    """)

    # Drop role column and enum
    op.drop_column("users", "role")
    op.execute("DROP TYPE user_role")
```

**Step 2: Run migration**

```bash
cd api && alembic upgrade head
```

**Step 3: Commit**

```bash
git add api/alembic/versions/20260113_000000_add_user_role.py api/src/models/orm/user.py
git commit -m "feat(auth): migrate user model from is_superuser to role enum"
```

---

### Task A4: Update Auth Contracts

**Files:**

-   Modify: `api/src/models/contracts/auth.py`

**Step 1: Update UserResponse contract**

```python
# In api/src/models/contracts/auth.py

from src.models.contracts.enums import UserRole

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    role: UserRole  # Changed from is_superuser
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

**Step 2: Run type check**

```bash
cd api && pyright src/models/contracts/auth.py
```

**Step 3: Commit**

```bash
git add api/src/models/contracts/auth.py
git commit -m "feat(auth): update UserResponse contract with role field"
```

---

### Task A5: Update Core Auth Module

**Files:**

-   Modify: `api/src/core/auth.py`

**Step 1: Update UserPrincipal and JWT handling**

```python
# In api/src/core/auth.py

from src.models.contracts.enums import UserRole

@dataclass
class UserPrincipal:
    user_id: uuid.UUID
    email: str
    role: UserRole  # Changed from is_superuser
    # ... other fields

def create_access_token(user: User, ...) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,  # Changed
        # ...
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

async def get_user_from_token(token: str, db: AsyncSession) -> UserPrincipal:
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    return UserPrincipal(
        user_id=uuid.UUID(payload["sub"]),
        email=payload["email"],
        role=UserRole(payload["role"]),  # Changed
        # ...
    )
```

**Step 2: Add role-checking dependency**

```python
# Add to api/src/core/auth.py

def require_role(min_role: UserRole):
    """Dependency that checks if user has minimum required role."""
    role_hierarchy = [UserRole.READER, UserRole.CONTRIBUTOR, UserRole.ADMINISTRATOR, UserRole.OWNER]

    async def check_role(user: CurrentActiveUser) -> User:
        user_level = role_hierarchy.index(user.role)
        required_level = role_hierarchy.index(min_role)
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Requires {min_role.value} role or higher"
            )
        return user

    return check_role

# Type aliases for common role requirements
RequireContributor = Annotated[User, Depends(require_role(UserRole.CONTRIBUTOR))]
RequireAdmin = Annotated[User, Depends(require_role(UserRole.ADMINISTRATOR))]
RequireOwner = Annotated[User, Depends(require_role(UserRole.OWNER))]
```

**Step 3: Run type check and tests**

```bash
cd api && pyright src/core/auth.py && pytest tests/unit/test_security.py -v
```

**Step 4: Commit**

```bash
git add api/src/core/auth.py
git commit -m "feat(auth): add role-based authorization with require_role dependency"
```

---

### Task A6: Update Auth Router

**Files:**

-   Modify: `api/src/routers/auth.py`

**Step 1: Update setup endpoint to assign owner role**

```python
# In api/src/routers/auth.py - setup endpoint

@router.post("/setup", response_model=TokenResponse)
async def setup_first_user(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """First user setup - always gets owner role."""
    user_repo = UserRepository(db)

    if await user_repo.has_any_users():
        raise HTTPException(status_code=400, detail="Setup already completed")

    user = await user_repo.create_user(
        email=request.email,
        password=request.password,
        name=request.name,
        role=UserRole.OWNER,  # First user is always owner
    )
    # ... rest of token generation
```

**Step 2: Run integration tests**

```bash
cd api && pytest tests/integration/test_auth.py -v
```

**Step 3: Commit**

```bash
git add api/src/routers/auth.py
git commit -m "feat(auth): setup endpoint assigns owner role to first user"
```

---

### Task A7: Update User Repository

**Files:**

-   Modify: `api/src/repositories/user.py`

**Step 1: Update create_user method**

```python
# In api/src/repositories/user.py

from src.models.contracts.enums import UserRole

class UserRepository(BaseRepository[User]):
    async def create_user(
        self,
        email: str,
        password: str | None = None,
        name: str | None = None,
        role: UserRole = UserRole.CONTRIBUTOR,
    ) -> User:
        hashed_password = hash_password(password) if password else None
        user = User(
            email=email,
            hashed_password=hashed_password,
            name=name,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def count_owners(self) -> int:
        """Count users with owner role."""
        result = await self.db.execute(
            select(func.count(User.id)).where(User.role == UserRole.OWNER)
        )
        return result.scalar() or 0

    async def update_role(self, user_id: uuid.UUID, new_role: UserRole) -> User:
        """Update user role with owner protection."""
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Prevent removing last owner
        if user.role == UserRole.OWNER and new_role != UserRole.OWNER:
            owner_count = await self.count_owners()
            if owner_count <= 1:
                raise ValueError("Cannot remove the last owner")

        user.role = new_role
        await self.db.flush()
        return user
```

**Step 2: Run type check**

```bash
cd api && pyright src/repositories/user.py
```

**Step 3: Commit**

```bash
git add api/src/repositories/user.py
git commit -m "feat(auth): add role management methods to UserRepository"
```

---

### Task A8: Update Admin Router for Role Management

**Files:**

-   Modify: `api/src/routers/admin.py`

**Step 1: Update user management endpoints**

```python
# In api/src/routers/admin.py

from src.models.contracts.enums import UserRole
from src.core.auth import RequireAdmin, RequireOwner

class UpdateUserRoleRequest(BaseModel):
    role: UserRole
    confirm_owner: bool = False  # Required when setting owner role

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    request: UpdateUserRoleRequest,
    current_user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role. Only owners can set/remove owner role."""
    user_repo = UserRepository(db)
    target_user = await user_repo.get_by_id(user_id)

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only owners can modify owner users or set owner role
    if target_user.role == UserRole.OWNER or request.role == UserRole.OWNER:
        if current_user.role != UserRole.OWNER:
            raise HTTPException(status_code=403, detail="Only owners can modify owner roles")
        if request.role == UserRole.OWNER and not request.confirm_owner:
            raise HTTPException(status_code=400, detail="Must confirm to set owner role")

    try:
        updated = await user_repo.update_role(user_id, request.role)
        await db.commit()
        return {"id": updated.id, "role": updated.role}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Step 2: Run integration tests**

```bash
cd api && pytest tests/integration/test_admin.py -v
```

**Step 3: Commit**

```bash
git add api/src/routers/admin.py
git commit -m "feat(admin): add role management endpoint with owner protection"
```

---

### Task A9: Apply Role Checks to Data Routers

**Files:**

-   Modify: `api/src/routers/passwords.py`
-   Modify: `api/src/routers/configurations.py`
-   Modify: `api/src/routers/documents.py`
-   Modify: `api/src/routers/locations.py`
-   Modify: `api/src/routers/custom_assets.py`

**Step 1: Update passwords router as example**

```python
# In api/src/routers/passwords.py

from src.core.auth import CurrentActiveUser, RequireContributor

# GET endpoints - any authenticated user
@router.get("", response_model=list[PasswordPublic])
async def list_passwords(
    org_id: uuid.UUID,
    user: CurrentActiveUser,  # Any role can read
    db: AsyncSession = Depends(get_db),
):
    # ...

# POST/PUT/DELETE - require contributor or higher
@router.post("", response_model=PasswordPublic)
async def create_password(
    org_id: uuid.UUID,
    request: PasswordCreate,
    user: RequireContributor,  # Contributor+ can create
    db: AsyncSession = Depends(get_db),
):
    # ...

@router.delete("/{password_id}")
async def delete_password(
    org_id: uuid.UUID,
    password_id: uuid.UUID,
    user: RequireContributor,  # Contributor+ can delete
    db: AsyncSession = Depends(get_db),
):
    # ...
```

**Step 2: Apply same pattern to other routers**

Repeat for configurations.py, documents.py, locations.py, custom_assets.py:

-   GET endpoints: `CurrentActiveUser`
-   POST/PUT/DELETE: `RequireContributor`

**Step 3: Run all tests**

```bash
cd api && pytest tests/integration/ -v
```

**Step 4: Commit**

```bash
git add api/src/routers/
git commit -m "feat(auth): apply role-based access control to all data routers"
```

---

### Task A10: Apply Role Checks to Settings Routers

**Files:**

-   Modify: `api/src/routers/ai_settings.py`
-   Modify: `api/src/routers/oauth_config.py`
-   Modify: `api/src/routers/configuration_types.py`
-   Modify: `api/src/routers/configuration_statuses.py`
-   Modify: `api/src/routers/custom_asset_types.py`

**Step 1: Update settings routers to require admin**

```python
# Example for ai_settings.py

from src.core.auth import RequireAdmin

@router.get("", response_model=AISettingsPublic)
async def get_ai_settings(
    user: RequireAdmin,  # Only admins can view/modify settings
    db: AsyncSession = Depends(get_db),
):
    # ...

@router.put("")
async def update_ai_settings(
    request: AISettingsUpdate,
    user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
):
    # ...
```

**Step 2: Commit**

```bash
git add api/src/routers/
git commit -m "feat(auth): require admin role for settings endpoints"
```

---

### Task A11: Update Frontend Auth Store

**Files:**

-   Modify: `client/src/stores/auth.store.ts`
-   Modify: `client/src/lib/api-client.ts`

**Step 1: Update User type in api-client.ts**

```typescript
// In client/src/lib/api-client.ts

export type UserRole = "owner" | "administrator" | "contributor" | "reader";

export interface User {
    id: string;
    email: string;
    name: string | null;
    role: UserRole; // Changed from is_superuser
    is_active: boolean;
    is_verified: boolean;
    mfa_enabled: boolean;
    created_at: string;
}
```

**Step 2: Update auth store**

```typescript
// In client/src/stores/auth.store.ts

import type { User, UserRole } from "@/lib/api-client";

interface AuthState {
    user: User | null;
    // ... other fields
}

// Permission helpers
export const usePermissions = () => {
    const user = useAuthStore((state) => state.user);

    const canEdit = user?.role !== "reader";
    const canAccessSettings =
        user?.role === "owner" || user?.role === "administrator";
    const canManageOwners = user?.role === "owner";

    return { canEdit, canAccessSettings, canManageOwners, role: user?.role };
};
```

**Step 3: Commit**

```bash
git add client/src/stores/auth.store.ts client/src/lib/api-client.ts
git commit -m "feat(auth): add role to frontend auth store with permission helpers"
```

---

### Task A12: Create usePermissions Hook

**Files:**

-   Create: `client/src/hooks/usePermissions.ts`

**Step 1: Create hook file**

```typescript
// client/src/hooks/usePermissions.ts

import { useAuthStore } from "@/stores/auth.store";
import type { UserRole } from "@/lib/api-client";

export function usePermissions() {
    const user = useAuthStore((state) => state.user);
    const role = user?.role;

    return {
        role,
        canEdit: role !== "reader",
        canAccessSettings: role === "owner" || role === "administrator",
        canManageOwners: role === "owner",
        isReader: role === "reader",
        isContributor: role === "contributor",
        isAdmin: role === "administrator",
        isOwner: role === "owner",
    };
}
```

**Step 2: Commit**

```bash
git add client/src/hooks/usePermissions.ts
git commit -m "feat(auth): create usePermissions hook for role-based UI"
```

---

### Task A13: Update Layout to Hide Settings for Non-Admins

**Files:**

-   Modify: `client/src/components/layout/Navbar.tsx` (or equivalent header component)

**Step 1: Conditionally show Settings nav item**

```tsx
// In Navbar/Header component

import { usePermissions } from "@/hooks/usePermissions";

export function Navbar() {
    const { canAccessSettings, role } = usePermissions();

    return (
        <nav>
            <NavItem href="/">Dashboard</NavItem>
            <NavItem href="/organizations">Organizations</NavItem>
            <NavItem href="/global">Global</NavItem>
            {canAccessSettings && <NavItem href="/settings">Settings</NavItem>}
            <UserMenu role={role} />
        </nav>
    );
}
```

**Step 2: Commit**

```bash
git add client/src/components/layout/
git commit -m "feat(auth): hide Settings nav for non-admin users"
```

---

### Task A14: Add Role Badge to User Menu

**Files:**

-   Modify: User menu component (find exact location)

**Step 1: Display role badge**

```tsx
// In UserMenu component

import { Badge } from "@/components/ui/badge";
import { usePermissions } from "@/hooks/usePermissions";

const roleColors: Record<UserRole, string> = {
    owner: "bg-purple-500",
    administrator: "bg-blue-500",
    contributor: "bg-green-500",
    reader: "bg-gray-500",
};

export function UserMenu() {
    const { role } = usePermissions();
    const user = useAuthStore((state) => state.user);

    return (
        <DropdownMenu>
            <DropdownMenuTrigger>
                <div className="flex items-center gap-2">
                    <span>{user?.name || user?.email}</span>
                    <Badge className={roleColors[role!]}>{role}</Badge>
                </div>
            </DropdownMenuTrigger>
            {/* ... menu items */}
        </DropdownMenu>
    );
}
```

**Step 2: Commit**

```bash
git add client/src/components/
git commit -m "feat(auth): show role badge in user menu"
```

---

### Task A15: Disable Edit Actions for Readers

**Files:**

-   Modify: Various page components that have edit/delete buttons

**Step 1: Use permission check in components**

```tsx
// Example in PasswordsPage.tsx

import { usePermissions } from "@/hooks/usePermissions";

export function PasswordsPage() {
    const { canEdit } = usePermissions();

    return (
        <div>
            {canEdit && <Button onClick={openCreateModal}>Add Password</Button>}

            <DataTable
                data={passwords}
                columns={[
                    // ...
                    {
                        id: "actions",
                        cell: ({ row }) =>
                            canEdit && (
                                <DropdownMenu>
                                    <DropdownMenuItem
                                        onClick={() => edit(row.original)}
                                    >
                                        Edit
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                        onClick={() => delete row.original}
                                    >
                                        Delete
                                    </DropdownMenuItem>
                                </DropdownMenu>
                            ),
                    },
                ]}
            />
        </div>
    );
}
```

**Step 2: Apply to all entity pages**

Repeat pattern for: ConfigurationsPage, LocationsPage, DocumentsPage, CustomAssetsPage

**Step 3: Run frontend type check**

```bash
cd client && npm run tsc
```

**Step 4: Commit**

```bash
git add client/src/pages/
git commit -m "feat(auth): disable edit/delete actions for reader role"
```

---

## Track B: Tables Backend (Phase 17.2-17.4, 18.3)

### Task B1: Create Paginated Response Contract

**Files:**

-   Create: `api/src/models/contracts/pagination.py`

**Step 1: Create pagination contracts**

```python
# api/src/models/contracts/pagination.py

from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

class PaginationParams(BaseModel):
    limit: int = 100
    offset: int = 0
    search: str | None = None
    sort_by: str | None = None
    sort_dir: str = "asc"  # "asc" or "desc"
```

**Step 2: Commit**

```bash
git add api/src/models/contracts/pagination.py
git commit -m "feat(api): add paginated response contracts"
```

---

### Task B2: Update Base Repository with Pagination

**Files:**

-   Modify: `api/src/repositories/base.py`

**Step 1: Add paginated query method**

```python
# In api/src/repositories/base.py

from sqlalchemy import func, asc, desc

class BaseRepository(Generic[T]):
    # ... existing methods

    async def get_paginated(
        self,
        *,
        filters: list | None = None,
        search_columns: list[str] | None = None,
        search_term: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[T], int]:
        """Get paginated results with optional search and sorting."""
        query = select(self.model)
        count_query = select(func.count(self.model.id))

        # Apply filters
        if filters:
            for f in filters:
                query = query.where(f)
                count_query = count_query.where(f)

        # Apply search
        if search_term and search_columns:
            search_conditions = [
                getattr(self.model, col).ilike(f"%{search_term}%")
                for col in search_columns
                if hasattr(self.model, col)
            ]
            if search_conditions:
                query = query.where(or_(*search_conditions))
                count_query = count_query.where(or_(*search_conditions))

        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            order_func = desc if sort_dir == "desc" else asc
            query = query.order_by(order_func(getattr(self.model, sort_by)))

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total
```

**Step 2: Run tests**

```bash
cd api && pytest tests/unit/ -v
```

**Step 3: Commit**

```bash
git add api/src/repositories/base.py
git commit -m "feat(api): add paginated query method to BaseRepository"
```

---

### Task B3: Update Passwords Router with Pagination

**Files:**

-   Modify: `api/src/routers/passwords.py`
-   Modify: `api/src/repositories/password.py`

**Step 1: Update repository**

```python
# In api/src/repositories/password.py

class PasswordRepository(BaseRepository[Password]):
    SEARCH_COLUMNS = ["name", "username", "url", "notes"]

    async def get_paginated_by_org(
        self,
        org_id: uuid.UUID,
        search: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Password], int]:
        filters = [Password.organization_id == org_id]
        return await self.get_paginated(
            filters=filters,
            search_columns=self.SEARCH_COLUMNS,
            search_term=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
```

**Step 2: Update router**

```python
# In api/src/routers/passwords.py

from src.models.contracts.pagination import PaginatedResponse

class PasswordListResponse(BaseModel):
    items: list[PasswordPublic]
    total: int
    limit: int
    offset: int

@router.get("", response_model=PasswordListResponse)
async def list_passwords(
    org_id: uuid.UUID,
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentActiveUser,
    db: AsyncSession = Depends(get_db),
):
    repo = PasswordRepository(db)
    items, total = await repo.get_paginated_by_org(
        org_id=org_id,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )
    return PasswordListResponse(items=items, total=total, limit=limit, offset=offset)
```

**Step 3: Run tests**

```bash
cd api && pytest tests/integration/test_passwords.py -v
```

**Step 4: Commit**

```bash
git add api/src/routers/passwords.py api/src/repositories/password.py
git commit -m "feat(api): add pagination to passwords endpoint"
```

---

### Task B4: Update Configurations Router with Pagination & Filters

**Files:**

-   Modify: `api/src/routers/configurations.py`
-   Modify: `api/src/repositories/configuration.py`

**Step 1: Update repository with filter support**

```python
# In api/src/repositories/configuration.py

class ConfigurationRepository(BaseRepository[Configuration]):
    SEARCH_COLUMNS = ["name", "serial_number", "asset_tag", "manufacturer", "model", "ip_address", "notes"]

    async def get_paginated_by_org(
        self,
        org_id: uuid.UUID,
        type_id: uuid.UUID | None = None,
        status_id: uuid.UUID | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Configuration], int]:
        filters = [Configuration.organization_id == org_id]

        if type_id:
            filters.append(Configuration.configuration_type_id == type_id)
        if status_id:
            filters.append(Configuration.configuration_status_id == status_id)

        return await self.get_paginated(
            filters=filters,
            search_columns=self.SEARCH_COLUMNS,
            search_term=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
```

**Step 2: Update router**

```python
# In api/src/routers/configurations.py

@router.get("", response_model=ConfigurationListResponse)
async def list_configurations(
    org_id: uuid.UUID,
    type_id: uuid.UUID | None = Query(None),
    status_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentActiveUser,
    db: AsyncSession = Depends(get_db),
):
    repo = ConfigurationRepository(db)
    items, total = await repo.get_paginated_by_org(
        org_id=org_id,
        type_id=type_id,
        status_id=status_id,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )
    return ConfigurationListResponse(items=items, total=total, limit=limit, offset=offset)
```

**Step 3: Commit**

```bash
git add api/src/routers/configurations.py api/src/repositories/configuration.py
git commit -m "feat(api): add pagination and filters to configurations endpoint"
```

---

### Task B5-B7: Repeat for Locations, Documents, Custom Assets

Apply same pagination pattern to:

-   `locations.py` (search: name, notes)
-   `documents.py` (search: name, path, content; filter: path)
-   `custom_assets.py` (search: name + non-password field values)

**Commit each:**

```bash
git commit -m "feat(api): add pagination to locations endpoint"
git commit -m "feat(api): add pagination to documents endpoint"
git commit -m "feat(api): add pagination to custom assets endpoint"
```

---

### Task B8: Create Global Endpoints

**Files:**

-   Create: `api/src/routers/global_data.py`

**Step 1: Create global data router**

```python
# api/src/routers/global_data.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.core.database import get_db
from src.core.auth import CurrentActiveUser
from src.models.orm import Password, Configuration, Location, Document, Organization

router = APIRouter(prefix="/api", tags=["global"])

class GlobalPasswordPublic(PasswordPublic):
    organization_id: uuid.UUID
    organization_name: str

@router.get("/passwords", response_model=GlobalPasswordListResponse)
async def list_all_passwords(
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_dir: str = Query("asc"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentActiveUser,
    db: AsyncSession = Depends(get_db),
):
    """List passwords across all organizations."""
    repo = PasswordRepository(db)
    # No org_id filter = all orgs
    items, total = await repo.get_paginated_global(
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )

    # Join organization names
    org_ids = {p.organization_id for p in items}
    orgs = await db.execute(select(Organization).where(Organization.id.in_(org_ids)))
    org_map = {o.id: o.name for o in orgs.scalars()}

    return GlobalPasswordListResponse(
        items=[
            GlobalPasswordPublic(
                **p.__dict__,
                organization_name=org_map.get(p.organization_id, "Unknown")
            )
            for p in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )

# Repeat for /configurations, /locations, /documents, /custom-assets
```

**Step 2: Register router in main.py**

```python
# In api/src/main.py

from src.routers import global_data

app.include_router(global_data.router)
```

**Step 3: Commit**

```bash
git add api/src/routers/global_data.py api/src/main.py
git commit -m "feat(api): add global data endpoints for cross-org access"
```

---

### Task B9: Create User Preferences Table

**Files:**

-   Create: `api/src/models/orm/user_preferences.py`
-   Create: `api/alembic/versions/20260113_001000_add_user_preferences.py`

**Step 1: Create ORM model**

```python
# api/src/models/orm/user_preferences.py

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.orm.base import Base

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", name="uq_user_preferences_user_entity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    entity_type: Mapped[str] = mapped_column(String(100))  # "passwords", "configurations", etc.
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
```

**Step 2: Create migration**

```python
# api/alembic/versions/20260113_001000_add_user_preferences.py

def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("preferences", sa.dialects.postgresql.JSONB(), default={}),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("user_id", "entity_type", name="uq_user_preferences_user_entity"),
    )

def downgrade() -> None:
    op.drop_table("user_preferences")
```

**Step 3: Run migration and commit**

```bash
cd api && alembic upgrade head
git add api/src/models/orm/user_preferences.py api/alembic/versions/20260113_001000_add_user_preferences.py
git commit -m "feat(api): add user_preferences table for column layouts"
```

---

### Task B10: Create Preferences Router

**Files:**

-   Create: `api/src/routers/preferences.py`
-   Create: `api/src/repositories/user_preferences.py`

**Step 1: Create repository**

```python
# api/src/repositories/user_preferences.py

class UserPreferencesRepository(BaseRepository[UserPreferences]):
    async def get_for_user_entity(
        self, user_id: uuid.UUID, entity_type: str
    ) -> UserPreferences | None:
        result = await self.db.execute(
            select(UserPreferences).where(
                UserPreferences.user_id == user_id,
                UserPreferences.entity_type == entity_type,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, user_id: uuid.UUID, entity_type: str, preferences: dict
    ) -> UserPreferences:
        existing = await self.get_for_user_entity(user_id, entity_type)
        if existing:
            existing.preferences = preferences
            await self.db.flush()
            return existing
        else:
            pref = UserPreferences(
                user_id=user_id,
                entity_type=entity_type,
                preferences=preferences,
            )
            self.db.add(pref)
            await self.db.flush()
            return pref
```

**Step 2: Create router**

```python
# api/src/routers/preferences.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/api/preferences", tags=["preferences"])

class ColumnPreferences(BaseModel):
    visible: list[str]
    order: list[str]
    widths: dict[str, int] = {}

class PreferencesResponse(BaseModel):
    entity_type: str
    columns: ColumnPreferences

class PreferencesUpdate(BaseModel):
    columns: ColumnPreferences

# Default columns per entity type
DEFAULTS = {
    "passwords": ["name", "username", "url", "updated_at"],
    "configurations": ["name", "type", "status", "manufacturer", "model", "updated_at"],
    "locations": ["name", "updated_at"],
    "documents": ["name", "path", "updated_at"],
}

@router.get("/{entity_type}", response_model=PreferencesResponse)
async def get_preferences(
    entity_type: str,
    user: CurrentActiveUser,
    db: AsyncSession = Depends(get_db),
):
    repo = UserPreferencesRepository(db)
    prefs = await repo.get_for_user_entity(user.id, entity_type)

    if prefs and prefs.preferences.get("columns"):
        return PreferencesResponse(
            entity_type=entity_type,
            columns=ColumnPreferences(**prefs.preferences["columns"])
        )

    # Return defaults
    default_cols = DEFAULTS.get(entity_type, ["name", "updated_at"])
    return PreferencesResponse(
        entity_type=entity_type,
        columns=ColumnPreferences(visible=default_cols, order=default_cols)
    )

@router.put("/{entity_type}", response_model=PreferencesResponse)
async def update_preferences(
    entity_type: str,
    request: PreferencesUpdate,
    user: CurrentActiveUser,  # Any role can update own preferences
    db: AsyncSession = Depends(get_db),
):
    repo = UserPreferencesRepository(db)
    prefs = await repo.upsert(
        user_id=user.id,
        entity_type=entity_type,
        preferences={"columns": request.columns.model_dump()}
    )
    await db.commit()
    return PreferencesResponse(entity_type=entity_type, columns=request.columns)
```

**Step 3: Register router and commit**

```bash
git add api/src/routers/preferences.py api/src/repositories/user_preferences.py
git commit -m "feat(api): add user preferences endpoint for column layouts"
```

---

## Track C: Tables Frontend (Phase 17.1, 18.1, 18.2)

### Task C1: Port DataTable from bifrost-api

**Files:**

-   Modify: `client/src/components/ui/data-table.tsx`

**Step 1: Review bifrost-api DataTable**

```bash
cat ../bifrost-api/client/src/components/ui/data-table.tsx
```

**Step 2: Update DataTable with search, pagination**

```tsx
// client/src/components/ui/data-table.tsx

import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    useReactTable,
    SortingState,
    VisibilityState,
} from "@tanstack/react-table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface DataTableProps<TData, TValue> {
    columns: ColumnDef<TData, TValue>[];
    data: TData[];
    total?: number;
    page?: number;
    pageSize?: number;
    onPageChange?: (page: number) => void;
    onPageSizeChange?: (size: number) => void;
    onSearch?: (term: string) => void;
    onSort?: (column: string, direction: "asc" | "desc") => void;
    isLoading?: boolean;
    searchPlaceholder?: string;
}

export function DataTable<TData, TValue>({
    columns,
    data,
    total = 0,
    page = 1,
    pageSize = 100,
    onPageChange,
    onPageSizeChange,
    onSearch,
    onSort,
    isLoading,
    searchPlaceholder = "Search...",
}: DataTableProps<TData, TValue>) {
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(
        {}
    );
    const [searchTerm, setSearchTerm] = useState("");

    const totalPages = Math.ceil(total / pageSize);

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        onSortingChange: setSorting,
        onColumnVisibilityChange: setColumnVisibility,
        state: { sorting, columnVisibility },
        manualSorting: true,
        manualPagination: true,
    });

    // Handle sort changes
    useEffect(() => {
        if (sorting.length > 0 && onSort) {
            onSort(sorting[0].id, sorting[0].desc ? "desc" : "asc");
        }
    }, [sorting, onSort]);

    // Debounced search
    const debouncedSearch = useMemo(
        () => debounce((term: string) => onSearch?.(term), 300),
        [onSearch]
    );

    return (
        <div className="space-y-4">
            {/* Search bar */}
            {onSearch && (
                <div className="flex items-center gap-4">
                    <Input
                        placeholder={searchPlaceholder}
                        value={searchTerm}
                        onChange={(e) => {
                            setSearchTerm(e.target.value);
                            debouncedSearch(e.target.value);
                        }}
                        className="max-w-sm"
                    />
                    <ColumnVisibilityDropdown table={table} />
                </div>
            )}

            {/* Table */}
            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => (
                                    <TableHead key={header.id}>
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(
                                                  header.column.columnDef
                                                      .header,
                                                  header.getContext()
                                              )}
                                    </TableHead>
                                ))}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            <TableSkeleton columns={columns.length} rows={10} />
                        ) : data.length === 0 ? (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length}
                                    className="h-24 text-center"
                                >
                                    No results.
                                </TableCell>
                            </TableRow>
                        ) : (
                            table.getRowModel().rows.map((row) => (
                                <TableRow key={row.id}>
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell key={cell.id}>
                                            {flexRender(
                                                cell.column.columnDef.cell,
                                                cell.getContext()
                                            )}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination */}
            {onPageChange && (
                <div className="flex items-center justify-between">
                    <div className="text-sm text-muted-foreground">
                        Showing {(page - 1) * pageSize + 1} to{" "}
                        {Math.min(page * pageSize, total)} of {total}
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onPageChange(page - 1)}
                            disabled={page <= 1}
                        >
                            Previous
                        </Button>
                        <span className="text-sm">
                            Page {page} of {totalPages}
                        </span>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onPageChange(page + 1)}
                            disabled={page >= totalPages}
                        >
                            Next
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
```

**Step 3: Commit**

```bash
git add client/src/components/ui/data-table.tsx
git commit -m "feat(ui): update DataTable with search, pagination, and column visibility"
```

---

### Task C2: Create useServerTable Hook

**Files:**

-   Create: `client/src/hooks/useServerTable.ts`

**Step 1: Create hook**

```typescript
// client/src/hooks/useServerTable.ts

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";

interface UseServerTableOptions<TData> {
    queryKey: string[];
    fetchFn: (params: TableParams) => Promise<PaginatedResponse<TData>>;
    defaultPageSize?: number;
}

interface TableParams {
    search?: string;
    sortBy?: string;
    sortDir?: "asc" | "desc";
    limit: number;
    offset: number;
    filters?: Record<string, string>;
}

interface PaginatedResponse<T> {
    items: T[];
    total: number;
    limit: number;
    offset: number;
}

export function useServerTable<TData>({
    queryKey,
    fetchFn,
    defaultPageSize = 100,
}: UseServerTableOptions<TData>) {
    const [search, setSearch] = useState("");
    const [sortBy, setSortBy] = useState<string | undefined>();
    const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(defaultPageSize);
    const [filters, setFilters] = useState<Record<string, string>>({});

    const offset = (page - 1) * pageSize;

    const { data, isLoading, error } = useQuery({
        queryKey: [
            ...queryKey,
            { search, sortBy, sortDir, page, pageSize, filters },
        ],
        queryFn: () =>
            fetchFn({
                search: search || undefined,
                sortBy,
                sortDir,
                limit: pageSize,
                offset,
                filters,
            }),
    });

    const onSearch = useCallback((term: string) => {
        setSearch(term);
        setPage(1); // Reset to first page on search
    }, []);

    const onSort = useCallback((column: string, direction: "asc" | "desc") => {
        setSortBy(column);
        setSortDir(direction);
    }, []);

    const onPageChange = useCallback((newPage: number) => {
        setPage(newPage);
    }, []);

    const onFilter = useCallback((key: string, value: string | undefined) => {
        setFilters((prev) => {
            if (value === undefined) {
                const { [key]: _, ...rest } = prev;
                return rest;
            }
            return { ...prev, [key]: value };
        });
        setPage(1);
    }, []);

    return {
        data: data?.items ?? [],
        total: data?.total ?? 0,
        page,
        pageSize,
        isLoading,
        error,
        onSearch,
        onSort,
        onPageChange,
        onPageSizeChange: setPageSize,
        onFilter,
        filters,
    };
}
```

**Step 2: Commit**

```bash
git add client/src/hooks/useServerTable.ts
git commit -m "feat(hooks): create useServerTable hook for server-side pagination"
```

---

### Task C3: Update PasswordsPage with New DataTable

**Files:**

-   Modify: `client/src/pages/passwords/PasswordsPage.tsx`

**Step 1: Update page to use server-side table**

```tsx
// client/src/pages/passwords/PasswordsPage.tsx

import { DataTable } from "@/components/ui/data-table";
import { useServerTable } from "@/hooks/useServerTable";
import { usePermissions } from "@/hooks/usePermissions";
import { apiClient } from "@/lib/api-client";

export function PasswordsPage({ orgId }: { orgId?: string }) {
    const { canEdit } = usePermissions();

    const {
        data,
        total,
        page,
        pageSize,
        isLoading,
        onSearch,
        onSort,
        onPageChange,
    } = useServerTable({
        queryKey: ["passwords", orgId ?? "global"],
        fetchFn: async (params) => {
            const url = orgId
                ? `/api/organizations/${orgId}/passwords`
                : "/api/passwords";
            const response = await apiClient.get(url, { params });
            return response.data;
        },
    });

    const columns = useMemo(() => {
        const cols = [
            { accessorKey: "name", header: "Name" },
            { accessorKey: "username", header: "Username" },
            { accessorKey: "url", header: "URL" },
            { accessorKey: "updated_at", header: "Updated", cell: formatDate },
        ];

        // Add organization column for global view
        if (!orgId) {
            cols.unshift({
                accessorKey: "organization_name",
                header: "Organization",
                cell: ({ row }) => (
                    <Link to={`/org/${row.original.organization_id}/passwords`}>
                        {row.original.organization_name}
                    </Link>
                ),
            });
        }

        // Add actions column if can edit
        if (canEdit) {
            cols.push({
                id: "actions",
                cell: ({ row }) => <PasswordActions password={row.original} />,
            });
        }

        return cols;
    }, [orgId, canEdit]);

    return (
        <div className="space-y-4">
            <div className="flex justify-between">
                <h1 className="text-2xl font-bold">Passwords</h1>
                {canEdit && <Button onClick={openCreate}>Add Password</Button>}
            </div>

            <DataTable
                columns={columns}
                data={data}
                total={total}
                page={page}
                pageSize={pageSize}
                onPageChange={onPageChange}
                onSearch={onSearch}
                onSort={onSort}
                isLoading={isLoading}
                searchPlaceholder="Search passwords..."
            />
        </div>
    );
}
```

**Step 2: Run type check**

```bash
cd client && npm run tsc
```

**Step 3: Commit**

```bash
git add client/src/pages/passwords/PasswordsPage.tsx
git commit -m "feat(ui): update PasswordsPage with server-side pagination"
```

---

### Task C4-C7: Update Other Entity Pages

Apply same pattern to:

-   `ConfigurationsPage.tsx` (add type/status filter dropdowns)
-   `LocationsPage.tsx`
-   `DocumentsPage.tsx`
-   `CustomAssetsPage.tsx`

**Commit each separately.**

---

### Task C8: Add Global Routes

**Files:**

-   Modify: `client/src/App.tsx`

**Step 1: Add global routes**

```tsx
// In client/src/App.tsx routes

<Route path="/global">
    <Route path="passwords" element={<PasswordsPage />} />
    <Route path="configurations" element={<ConfigurationsPage />} />
    <Route path="locations" element={<LocationsPage />} />
    <Route path="documents" element={<DocumentsPage />} />
    <Route path="assets/:typeId" element={<CustomAssetsPage />} />
</Route>
```

**Step 2: Commit**

```bash
git add client/src/App.tsx
git commit -m "feat(routes): add global routes for cross-org data views"
```

---

### Task C9: Update Sidebar for Global View

**Files:**

-   Modify: `client/src/components/layout/Sidebar.tsx` (or equivalent)
-   Modify: `client/src/hooks/useSidebar.ts`

**Step 1: Update sidebar to handle global mode**

```tsx
// In Sidebar component

export function Sidebar({ orgId }: { orgId?: string }) {
    const { data: sidebarData } = useSidebarData(orgId);

    const basePath = orgId ? `/org/${orgId}` : "/global";

    return (
        <nav>
            <NavSection title="Core">
                <NavItem
                    href={`${basePath}/passwords`}
                    count={sidebarData?.passwords}
                >
                    Passwords
                </NavItem>
                <NavItem
                    href={`${basePath}/locations`}
                    count={sidebarData?.locations}
                >
                    Locations
                </NavItem>
                <NavItem
                    href={`${basePath}/documents`}
                    count={sidebarData?.documents}
                >
                    Documents
                </NavItem>
            </NavSection>

            <NavSection title="Configurations">
                {sidebarData?.configurationTypes?.map((type) => (
                    <NavItem
                        key={type.id}
                        href={`${basePath}/configurations?type=${type.id}`}
                        count={type.count}
                    >
                        {type.name}
                    </NavItem>
                ))}
            </NavSection>

            <NavSection title="Assets">
                {sidebarData?.customAssetTypes
                    ?.filter((t) => t.is_active)
                    .map((type) => (
                        <NavItem
                            key={type.id}
                            href={`${basePath}/assets/${type.id}`}
                            count={type.count}
                        >
                            {type.name}
                        </NavItem>
                    ))}
            </NavSection>
        </nav>
    );
}
```

**Step 2: Commit**

```bash
git add client/src/components/layout/
git commit -m "feat(ui): update sidebar for global view with aggregated counts"
```

---

## Track D: Soft Delete (Phase 19)

### Task D1: Add is_active to Custom Asset Types

**Files:**

-   Modify: `api/src/models/orm/custom_asset_type.py`
-   Create: `api/alembic/versions/20260113_002000_add_is_active_to_types.py`

**Step 1: Update model**

```python
# In api/src/models/orm/custom_asset_type.py

class CustomAssetType(Base):
    # ... existing fields
    is_active: Mapped[bool] = mapped_column(default=True)
```

**Step 2: Create migration**

```python
# api/alembic/versions/20260113_002000_add_is_active_to_types.py

def upgrade() -> None:
    op.add_column("custom_asset_types", sa.Column("is_active", sa.Boolean(), server_default="true"))
    op.add_column("configuration_types", sa.Column("is_active", sa.Boolean(), server_default="true"))
    op.add_column("configuration_statuses", sa.Column("is_active", sa.Boolean(), server_default="true"))

def downgrade() -> None:
    op.drop_column("custom_asset_types", "is_active")
    op.drop_column("configuration_types", "is_active")
    op.drop_column("configuration_statuses", "is_active")
```

**Step 3: Run migration and commit**

```bash
cd api && alembic upgrade head
git add api/src/models/orm/ api/alembic/versions/20260113_002000_add_is_active_to_types.py
git commit -m "feat(api): add is_active soft delete to type tables"
```

---

### Task D2: Update Repository for Active Filtering

**Files:**

-   Modify: `api/src/repositories/custom_asset_type.py`

**Step 1: Add active filtering**

```python
# In api/src/repositories/custom_asset_type.py

class CustomAssetTypeRepository(BaseRepository[CustomAssetType]):
    async def get_all_active(self) -> list[CustomAssetType]:
        result = await self.db.execute(
            select(CustomAssetType).where(CustomAssetType.is_active == True)
        )
        return list(result.scalars().all())

    async def get_all_with_inactive(self) -> list[CustomAssetType]:
        result = await self.db.execute(select(CustomAssetType))
        return list(result.scalars().all())

    async def get_asset_count(self, type_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(CustomAsset.id)).where(CustomAsset.custom_asset_type_id == type_id)
        )
        return result.scalar() or 0

    async def deactivate(self, type_id: uuid.UUID) -> CustomAssetType:
        type_obj = await self.get_by_id(type_id)
        type_obj.is_active = False
        await self.db.flush()
        return type_obj

    async def activate(self, type_id: uuid.UUID) -> CustomAssetType:
        type_obj = await self.get_by_id(type_id)
        type_obj.is_active = True
        await self.db.flush()
        return type_obj

    async def can_delete(self, type_id: uuid.UUID) -> bool:
        count = await self.get_asset_count(type_id)
        return count == 0
```

**Step 2: Commit**

```bash
git add api/src/repositories/custom_asset_type.py
git commit -m "feat(api): add soft delete methods to CustomAssetTypeRepository"
```

---

### Task D3: Update Router with Activate/Deactivate Endpoints

**Files:**

-   Modify: `api/src/routers/custom_asset_types.py`

**Step 1: Add endpoints**

```python
# In api/src/routers/custom_asset_types.py

@router.post("/{type_id}/deactivate")
async def deactivate_type(
    type_id: uuid.UUID,
    user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
):
    repo = CustomAssetTypeRepository(db)
    type_obj = await repo.deactivate(type_id)
    await db.commit()
    return {"id": type_obj.id, "is_active": type_obj.is_active}

@router.post("/{type_id}/activate")
async def activate_type(
    type_id: uuid.UUID,
    user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
):
    repo = CustomAssetTypeRepository(db)
    type_obj = await repo.activate(type_id)
    await db.commit()
    return {"id": type_obj.id, "is_active": type_obj.is_active}

@router.delete("/{type_id}")
async def delete_type(
    type_id: uuid.UUID,
    user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
):
    repo = CustomAssetTypeRepository(db)

    if not await repo.can_delete(type_id):
        count = await repo.get_asset_count(type_id)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete - {count} assets exist. Deactivate instead."
        )

    await repo.delete_by_id(type_id)
    await db.commit()
    return {"deleted": True}
```

**Step 2: Commit**

```bash
git add api/src/routers/custom_asset_types.py
git commit -m "feat(api): add activate/deactivate/delete endpoints for custom asset types"
```

---

### Task D4-D5: Repeat for Configuration Types and Statuses

Apply same pattern to:

-   `configuration_types.py`
-   `configuration_statuses.py`

**Commit each separately.**

---

### Task D6: Exclude Inactive from Search

**Files:**

-   Modify: `api/src/services/embeddings.py` (or search service)

**Step 1: Filter out inactive type assets in search**

```python
# In search query building

# When searching custom assets, join to type and filter
query = query.join(CustomAssetType).where(CustomAssetType.is_active == True)
```

**Step 2: Commit**

```bash
git add api/src/services/
git commit -m "feat(search): exclude inactive type assets from search results"
```

---

### Task D7: Update Settings UI for Inactive Types

**Files:**

-   Modify: `client/src/pages/settings/CustomAssetTypesSettings.tsx`

**Step 1: Add toggle and conditional delete**

```tsx
// In CustomAssetTypesSettings.tsx

export function CustomAssetTypesSettings() {
    const { data: types } = useCustomAssetTypes({ includeInactive: true });

    return (
        <div>
            {types?.map((type) => (
                <Card
                    key={type.id}
                    className={!type.is_active ? "opacity-50" : ""}
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <h3>{type.name}</h3>
                            {!type.is_active && (
                                <Badge variant="secondary">
                                    Inactive - {type.asset_count} assets
                                    archived
                                </Badge>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            <Switch
                                checked={type.is_active}
                                onCheckedChange={(checked) =>
                                    checked
                                        ? activateType(type.id)
                                        : deactivateType(type.id)
                                }
                            />
                            <Button
                                variant="destructive"
                                size="sm"
                                disabled={type.asset_count > 0}
                                onClick={() => deleteType(type.id)}
                                title={
                                    type.asset_count > 0
                                        ? `Cannot delete - ${type.asset_count} assets exist`
                                        : "Delete"
                                }
                            >
                                Delete
                            </Button>
                        </div>
                    </div>
                </Card>
            ))}
        </div>
    );
}
```

**Step 2: Commit**

```bash
git add client/src/pages/settings/
git commit -m "feat(ui): add toggle and conditional delete for type settings"
```

---

## Track E: Tiptap Editor (Phase 20)

### Task E1: Install Tiptap Dependencies

**Step 1: Install packages**

```bash
cd client && npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-image @tiptap/extension-link @tiptap/extension-placeholder @tiptap/extension-code-block-lowlight lowlight
```

**Step 2: Commit**

```bash
git add client/package.json client/package-lock.json
git commit -m "chore(deps): install Tiptap editor dependencies"
```

---

### Task E2: Create TiptapEditor Component

**Files:**

-   Create: `client/src/components/documents/TiptapEditor.tsx`

**Step 1: Create component**

```tsx
// client/src/components/documents/TiptapEditor.tsx

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import { useCallback } from "react";
import { apiClient } from "@/lib/api-client";

interface TiptapEditorProps {
    content: string;
    onChange?: (content: string) => void;
    readOnly?: boolean;
    orgId: string;
    placeholder?: string;
}

export function TiptapEditor({
    content,
    onChange,
    readOnly = false,
    orgId,
    placeholder = "Start writing...",
}: TiptapEditorProps) {
    const editor = useEditor({
        extensions: [
            StarterKit,
            Image,
            Link.configure({ openOnClick: false }),
            Placeholder.configure({ placeholder }),
        ],
        content,
        editable: !readOnly,
        onUpdate: ({ editor }) => {
            onChange?.(editor.getHTML());
        },
    });

    // Handle image paste/drop
    const handleImageUpload = useCallback(
        async (file: File) => {
            const formData = new FormData();
            formData.append("file", file);

            try {
                const response = await apiClient.post(
                    `/api/organizations/${orgId}/documents/images`,
                    formData,
                    { headers: { "Content-Type": "multipart/form-data" } }
                );

                editor
                    ?.chain()
                    .focus()
                    .setImage({ src: response.data.url })
                    .run();
            } catch (error) {
                console.error("Image upload failed:", error);
                // Show toast error
            }
        },
        [editor, orgId]
    );

    // Paste handler
    useEffect(() => {
        if (!editor || readOnly) return;

        const handlePaste = (event: ClipboardEvent) => {
            const items = event.clipboardData?.items;
            if (!items) return;

            for (const item of items) {
                if (item.type.startsWith("image/")) {
                    event.preventDefault();
                    const file = item.getAsFile();
                    if (file) handleImageUpload(file);
                    return;
                }
            }
        };

        editor.view.dom.addEventListener("paste", handlePaste);
        return () => editor.view.dom.removeEventListener("paste", handlePaste);
    }, [editor, readOnly, handleImageUpload]);

    if (!editor) return null;

    return (
        <div className="tiptap-editor">
            {!readOnly && (
                <TiptapToolbar
                    editor={editor}
                    onImageUpload={handleImageUpload}
                />
            )}
            <EditorContent editor={editor} className="prose max-w-none" />
        </div>
    );
}
```

**Step 2: Commit**

```bash
git add client/src/components/documents/TiptapEditor.tsx
git commit -m "feat(ui): create TiptapEditor component with image upload"
```

---

### Task E3: Create Tiptap Toolbar

**Files:**

-   Create: `client/src/components/documents/TiptapToolbar.tsx`

**Step 1: Create toolbar**

```tsx
// client/src/components/documents/TiptapToolbar.tsx

import { Editor } from "@tiptap/react";
import { Toggle } from "@/components/ui/toggle";
import { Button } from "@/components/ui/button";
import {
    Bold,
    Italic,
    Strikethrough,
    Code,
    Heading1,
    Heading2,
    Heading3,
    List,
    ListOrdered,
    Quote,
    ImageIcon,
    Link as LinkIcon,
} from "lucide-react";

interface TiptapToolbarProps {
    editor: Editor;
    onImageUpload: (file: File) => void;
}

export function TiptapToolbar({ editor, onImageUpload }: TiptapToolbarProps) {
    const handleImageClick = () => {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = "image/*";
        input.onchange = (e) => {
            const file = (e.target as HTMLInputElement).files?.[0];
            if (file) onImageUpload(file);
        };
        input.click();
    };

    return (
        <div className="flex flex-wrap gap-1 p-2 border-b">
            <Toggle
                pressed={editor.isActive("heading", { level: 1 })}
                onPressedChange={() =>
                    editor.chain().focus().toggleHeading({ level: 1 }).run()
                }
            >
                <Heading1 className="h-4 w-4" />
            </Toggle>
            <Toggle
                pressed={editor.isActive("heading", { level: 2 })}
                onPressedChange={() =>
                    editor.chain().focus().toggleHeading({ level: 2 }).run()
                }
            >
                <Heading2 className="h-4 w-4" />
            </Toggle>
            <Toggle
                pressed={editor.isActive("heading", { level: 3 })}
                onPressedChange={() =>
                    editor.chain().focus().toggleHeading({ level: 3 }).run()
                }
            >
                <Heading3 className="h-4 w-4" />
            </Toggle>

            <div className="w-px h-6 bg-border mx-1" />

            <Toggle
                pressed={editor.isActive("bold")}
                onPressedChange={() =>
                    editor.chain().focus().toggleBold().run()
                }
            >
                <Bold className="h-4 w-4" />
            </Toggle>
            <Toggle
                pressed={editor.isActive("italic")}
                onPressedChange={() =>
                    editor.chain().focus().toggleItalic().run()
                }
            >
                <Italic className="h-4 w-4" />
            </Toggle>
            <Toggle
                pressed={editor.isActive("strike")}
                onPressedChange={() =>
                    editor.chain().focus().toggleStrike().run()
                }
            >
                <Strikethrough className="h-4 w-4" />
            </Toggle>

            <div className="w-px h-6 bg-border mx-1" />

            <Toggle
                pressed={editor.isActive("bulletList")}
                onPressedChange={() =>
                    editor.chain().focus().toggleBulletList().run()
                }
            >
                <List className="h-4 w-4" />
            </Toggle>
            <Toggle
                pressed={editor.isActive("orderedList")}
                onPressedChange={() =>
                    editor.chain().focus().toggleOrderedList().run()
                }
            >
                <ListOrdered className="h-4 w-4" />
            </Toggle>

            <div className="w-px h-6 bg-border mx-1" />

            <Toggle
                pressed={editor.isActive("codeBlock")}
                onPressedChange={() =>
                    editor.chain().focus().toggleCodeBlock().run()
                }
            >
                <Code className="h-4 w-4" />
            </Toggle>
            <Toggle
                pressed={editor.isActive("blockquote")}
                onPressedChange={() =>
                    editor.chain().focus().toggleBlockquote().run()
                }
            >
                <Quote className="h-4 w-4" />
            </Toggle>

            <div className="w-px h-6 bg-border mx-1" />

            <Button variant="ghost" size="sm" onClick={handleImageClick}>
                <ImageIcon className="h-4 w-4" />
            </Button>
        </div>
    );
}
```

**Step 2: Commit**

```bash
git add client/src/components/documents/TiptapToolbar.tsx
git commit -m "feat(ui): create TiptapToolbar with formatting controls"
```

---

### Task E4: Update Document Pages to Use Tiptap

**Files:**

-   Modify: `client/src/pages/documents/DocumentDetailPage.tsx`
-   Delete: `client/src/components/documents/MarkdownEditor.tsx`

**Step 1: Replace MarkdownEditor with TiptapEditor**

```tsx
// In DocumentDetailPage.tsx

import { TiptapEditor } from "@/components/documents/TiptapEditor";
import { usePermissions } from "@/hooks/usePermissions";

export function DocumentDetailPage({ orgId, documentId }: Props) {
    const { canEdit } = usePermissions();
    const { data: document } = useDocument(documentId);
    const [content, setContent] = useState("");

    return (
        <div>
            <TiptapEditor
                content={document?.content || ""}
                onChange={setContent}
                readOnly={!canEdit}
                orgId={orgId}
            />

            {canEdit && (
                <Button onClick={() => saveDocument(content)}>Save</Button>
            )}
        </div>
    );
}
```

**Step 2: Remove old MarkdownEditor**

```bash
rm client/src/components/documents/MarkdownEditor.tsx
```

**Step 3: Commit**

```bash
git add client/src/pages/documents/ client/src/components/documents/
git commit -m "feat(ui): replace MarkdownEditor with TiptapEditor"
```

---

## Track F: Data Export (Phase 21)

### Task F1: Create Export ORM Model

**Files:**

-   Create: `api/src/models/orm/export.py`
-   Create: `api/alembic/versions/20260113_003000_add_exports_table.py`

**Step 1: Create model**

```python
# api/src/models/orm/export.py

from enum import Enum
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.orm.base import Base

class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    organization_ids: Mapped[list | None] = mapped_column(JSONB)  # null = all orgs
    status: Mapped[ExportStatus] = mapped_column(default=ExportStatus.PENDING)
    s3_key: Mapped[str | None] = mapped_column(String(500))
    file_size_bytes: Mapped[int | None] = mapped_column()
    expires_at: Mapped[datetime] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

**Step 2: Create migration and run**

```bash
cd api && alembic revision --autogenerate -m "add exports table"
cd api && alembic upgrade head
git add api/src/models/orm/export.py api/alembic/versions/
git commit -m "feat(api): add exports table for data export tracking"
```

---

### Task F2: Create Export Router

**Files:**

-   Create: `api/src/routers/exports.py`

**Step 1: Create router**

```python
# api/src/routers/exports.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/exports", tags=["exports"])

class CreateExportRequest(BaseModel):
    organization_ids: list[uuid.UUID] | None = None  # null = all
    expires_in_days: int = 7

class ExportResponse(BaseModel):
    id: uuid.UUID
    status: ExportStatus
    organization_ids: list[uuid.UUID] | None
    file_size_bytes: int | None
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

@router.post("", response_model=ExportResponse)
async def create_export(
    request: CreateExportRequest,
    background_tasks: BackgroundTasks,
    user: RequireAdmin,
    db: AsyncSession = Depends(get_db),
):
    repo = ExportRepository(db)

    export = Export(
        user_id=user.id,
        organization_ids=request.organization_ids,
        expires_at=datetime.utcnow() + timedelta(days=request.expires_in_days),
    )
    db.add(export)
    await db.commit()

    # Queue background job
    background_tasks.add_task(process_export, export.id)

    return export

@router.get("", response_model=list[ExportResponse])
async def list_exports(
    user: CurrentActiveUser,
    db: AsyncSession = Depends(get_db),
):
    repo = ExportRepository(db)
    return await repo.get_by_user(user.id)

@router.get("/{export_id}/download")
async def download_export(
    export_id: uuid.UUID,
    user: CurrentActiveUser,
    db: AsyncSession = Depends(get_db),
):
    repo = ExportRepository(db)
    export = await repo.get_by_id(export_id)

    if not export or export.user_id != user.id:
        raise HTTPException(404, "Export not found")
    if export.revoked_at:
        raise HTTPException(400, "Export has been revoked")
    if export.expires_at < datetime.utcnow():
        raise HTTPException(400, "Export has expired")
    if export.status != ExportStatus.COMPLETED:
        raise HTTPException(400, "Export not ready")

    # Generate presigned URL
    url = generate_presigned_url(export.s3_key, expires_in=3600)
    return {"download_url": url}

@router.delete("/{export_id}")
async def revoke_export(
    export_id: uuid.UUID,
    user: CurrentActiveUser,
    db: AsyncSession = Depends(get_db),
):
    repo = ExportRepository(db)
    export = await repo.get_by_id(export_id)

    if not export or export.user_id != user.id:
        raise HTTPException(404, "Export not found")

    export.revoked_at = datetime.utcnow()
    await db.commit()
    return {"revoked": True}
```

**Step 2: Commit**

```bash
git add api/src/routers/exports.py
git commit -m "feat(api): add export CRUD endpoints"
```

---

### Task F3: Create Export Service

**Files:**

-   Create: `api/src/services/export_service.py`

**Step 1: Create service with ZIP generation**

```python
# api/src/services/export_service.py

import csv
import io
import zipfile
import base64
from datetime import datetime

from src.core.pubsub import publish_message
from src.models.orm import Export, ExportStatus
from src.repositories import (
    PasswordRepository, ConfigurationRepository, LocationRepository,
    DocumentRepository, CustomAssetRepository, AttachmentRepository,
)

async def process_export(export_id: uuid.UUID):
    """Background task to generate export ZIP."""
    async with get_db_session() as db:
        repo = ExportRepository(db)
        export = await repo.get_by_id(export_id)

        try:
            export.status = ExportStatus.PROCESSING
            await db.commit()

            # Create in-memory ZIP
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                org_ids = export.organization_ids  # None means all

                # Export passwords
                await publish_progress(export_id, "passwords", 0, 0)
                passwords_csv = await export_passwords(db, org_ids)
                zf.writestr("passwords.csv", passwords_csv)
                await publish_progress(export_id, "passwords", 100, 100)

                # Export configurations
                await publish_progress(export_id, "configurations", 0, 0)
                configs_csv = await export_configurations(db, org_ids)
                zf.writestr("configurations.csv", configs_csv)
                await publish_progress(export_id, "configurations", 100, 100)

                # Export locations
                await publish_progress(export_id, "locations", 0, 0)
                locations_csv = await export_locations(db, org_ids)
                zf.writestr("locations.csv", locations_csv)
                await publish_progress(export_id, "locations", 100, 100)

                # Export documents with embedded images
                await publish_progress(export_id, "documents", 0, 0)
                await export_documents(db, org_ids, zf)
                await publish_progress(export_id, "documents", 100, 100)

                # Export custom assets
                await publish_progress(export_id, "custom_assets", 0, 0)
                await export_custom_assets(db, org_ids, zf)
                await publish_progress(export_id, "custom_assets", 100, 100)

                # Export attachments
                await publish_progress(export_id, "attachments", 0, 0)
                attachments_csv = await export_attachments(db, org_ids, zf)
                zf.writestr("attachments.csv", attachments_csv)
                await publish_progress(export_id, "attachments", 100, 100)

            # Upload to S3
            zip_buffer.seek(0)
            s3_key = f"exports/{export_id}/{datetime.utcnow().strftime('%Y-%m-%d')}-export.zip"
            await upload_to_s3(s3_key, zip_buffer.getvalue())

            export.status = ExportStatus.COMPLETED
            export.s3_key = s3_key
            export.file_size_bytes = len(zip_buffer.getvalue())
            await db.commit()

            await publish_message(f"export:{export_id}", {
                "stage": "complete",
                "file_size_bytes": export.file_size_bytes
            })

        except Exception as e:
            export.status = ExportStatus.FAILED
            export.error_message = str(e)
            await db.commit()

            await publish_message(f"export:{export_id}", {
                "stage": "failed",
                "error": str(e)
            })

async def publish_progress(export_id: uuid.UUID, stage: str, progress: int, total: int):
    await publish_message(f"export:{export_id}", {
        "stage": stage,
        "progress": progress,
        "total": total,
    })

async def export_passwords(db: AsyncSession, org_ids: list | None) -> str:
    """Export passwords to CSV with decrypted values."""
    repo = PasswordRepository(db)
    passwords = await repo.get_all_for_export(org_ids)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["organization_id", "id", "name", "username", "password", "url", "notes"])

    for p in passwords:
        decrypted = decrypt_password(p.password_encrypted)
        writer.writerow([p.organization_id, p.id, p.name, p.username, decrypted, p.url, p.notes])

    return output.getvalue()

# ... similar functions for other entity types
```

**Step 2: Commit**

```bash
git add api/src/services/export_service.py
git commit -m "feat(api): add export service with ZIP generation and progress"
```

---

### Task F4: Create Export Settings UI

**Files:**

-   Create: `client/src/pages/settings/ExportsSettings.tsx`

**Step 1: Create exports page**

```tsx
// client/src/pages/settings/ExportsSettings.tsx

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useWebSocketChannel } from "@/hooks/useWebSocket";
import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export function ExportsSettings() {
    const [creatingExport, setCreatingExport] = useState<string | null>(null);

    const { data: exports, refetch } = useQuery({
        queryKey: ["exports"],
        queryFn: () => apiClient.get("/api/exports").then((r) => r.data),
    });

    const createExport = useMutation({
        mutationFn: (data: CreateExportRequest) =>
            apiClient.post("/api/exports", data).then((r) => r.data),
        onSuccess: (data) => {
            setCreatingExport(data.id);
            refetch();
        },
    });

    // WebSocket progress for active export
    const progress = useWebSocketChannel<ExportProgress>(
        creatingExport ? `export:${creatingExport}` : null
    );

    useEffect(() => {
        if (progress?.stage === "complete" || progress?.stage === "failed") {
            setCreatingExport(null);
            refetch();
        }
    }, [progress, refetch]);

    const statusColors = {
        pending: "bg-yellow-500",
        processing: "bg-blue-500",
        completed: "bg-green-500",
        failed: "bg-red-500",
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between">
                <h1 className="text-2xl font-bold">Exports</h1>
                <Button onClick={() => setShowCreateModal(true)}>
                    New Export
                </Button>
            </div>

            {/* Progress modal */}
            {creatingExport && progress && (
                <Card>
                    <CardHeader>Generating Export...</CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span>Stage: {progress.stage}</span>
                                <span>
                                    {progress.progress} / {progress.total}
                                </span>
                            </div>
                            <Progress
                                value={
                                    (progress.progress / progress.total) * 100
                                }
                            />
                        </div>
                    </CardContent>
                </Card>
            )}

            <DataTable
                data={exports || []}
                columns={[
                    {
                        accessorKey: "created_at",
                        header: "Created",
                        cell: formatDate,
                    },
                    {
                        accessorKey: "status",
                        header: "Status",
                        cell: ({ row }) => (
                            <Badge
                                className={statusColors[row.original.status]}
                            >
                                {row.original.status}
                            </Badge>
                        ),
                    },
                    {
                        accessorKey: "organization_ids",
                        header: "Organizations",
                        cell: ({ row }) =>
                            row.original.organization_ids?.length || "All",
                    },
                    {
                        accessorKey: "file_size_bytes",
                        header: "Size",
                        cell: ({ row }) =>
                            formatBytes(row.original.file_size_bytes),
                    },
                    {
                        accessorKey: "expires_at",
                        header: "Expires",
                        cell: formatDate,
                    },
                    {
                        id: "actions",
                        cell: ({ row }) => (
                            <div className="flex gap-2">
                                {row.original.status === "completed" &&
                                    !row.original.revoked_at && (
                                        <Button
                                            size="sm"
                                            onClick={() =>
                                                downloadExport(row.original.id)
                                            }
                                        >
                                            Download
                                        </Button>
                                    )}
                                {!row.original.revoked_at && (
                                    <Button
                                        size="sm"
                                        variant="destructive"
                                        onClick={() =>
                                            revokeExport(row.original.id)
                                        }
                                    >
                                        Revoke
                                    </Button>
                                )}
                            </div>
                        ),
                    },
                ]}
            />

            {/* Create modal */}
            <CreateExportModal
                open={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                onCreate={(data) => createExport.mutate(data)}
            />
        </div>
    );
}
```

**Step 2: Commit**

```bash
git add client/src/pages/settings/ExportsSettings.tsx
git commit -m "feat(ui): add exports settings page with progress tracking"
```

---

## Track G: Cleanup (Phase 22)

### Task G1: Remove IT Glue References

**Step 1: Search and replace**

```bash
# Find all references
grep -r "IT Glue" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" .

# Update any found references to "Bifrost Docs" or remove
```

**Step 2: Commit**

```bash
git add .
git commit -m "chore: remove IT Glue references from codebase"
```

---

### Task G2: Add Pinned Columns UI to Schema Builder

**Files:**

-   Modify: `client/src/pages/settings/CustomAssetTypeForm.tsx` (or equivalent)

**Step 1: Add pin checkbox to field editor**

```tsx
// In field editor for custom asset types

<FormField
    control={form.control}
    name={`fields.${index}.show_in_list`}
    render={({ field }) => (
        <FormItem className="flex items-center gap-2">
            <FormControl>
                <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                />
            </FormControl>
            <FormLabel>Pin to table</FormLabel>
        </FormItem>
    )}
/>
```

**Step 2: Commit**

```bash
git add client/src/pages/settings/
git commit -m "feat(ui): add pin column toggle to custom asset type schema builder"
```

---

### Task G3: Verify Branding Consistency

**Step 1: Check all branding references**

```bash
grep -r "BifrostDocs" --include="*.ts" --include="*.tsx" --include="*.html" client/
grep -r "bifrost_docs" --include="*.ts" --include="*.tsx" client/
```

**Step 2: Update any remaining to "Bifrost Docs"**

**Step 3: Commit**

```bash
git add .
git commit -m "chore: ensure consistent Bifrost Docs branding"
```

---

### Task G4: Final Type Check and Lint

**Step 1: Run all checks**

```bash
# Backend
cd api && pyright && ruff check && pytest

# Frontend
cd client && npm run tsc && npm run lint && npm test
```

**Step 2: Fix any issues and commit**

```bash
git add .
git commit -m "chore: fix type and lint issues from phases 16-22"
```

---

## Summary

**Total Tasks:** ~85 tasks across 7 tracks

**Parallel Execution:**

1. Start with **Track A** (Roles) - foundation for everything
2. Then run **Tracks B, D, E, F** in parallel (backend heavy)
3. Then **Track C** (frontend tables - depends on B)
4. Finally **Track G** (cleanup)

**Estimated Timeline:**

-   Track A: 15 tasks
-   Track B: 20 tasks (can parallel with D, E, F)
-   Track C: 12 tasks
-   Track D: 10 tasks
-   Track E: 8 tasks
-   Track F: 15 tasks
-   Track G: 5 tasks
