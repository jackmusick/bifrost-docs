"""
User Repository

Provides database operations for User model.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.user import User
from src.repositories.base import BaseRepository

if TYPE_CHECKING:
    from src.models.enums import UserRole


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    model = User

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email address.

        Args:
            email: Email address to search for

        Returns:
            User or None if not found
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def has_any_users(self) -> bool:
        """
        Check if any users exist in the system.

        Returns:
            True if at least one user exists, False otherwise
        """
        result = await self.session.execute(select(User.id).limit(1))
        return result.scalar_one_or_none() is not None

    async def create_user(
        self,
        email: str,
        hashed_password: str | None = None,
        name: str | None = None,
        role: "UserRole | None" = None,
    ) -> User:
        """
        Create a new user.

        Args:
            email: User email address
            hashed_password: Hashed password (optional for OAuth users)
            name: User display name
            role: User role (defaults to CONTRIBUTOR if not specified)

        Returns:
            Created User
        """
        from src.models.enums import UserRole

        user = User(
            email=email,
            hashed_password=hashed_password,
            name=name,
            role=role or UserRole.CONTRIBUTOR,
        )
        return await self.create(user)

    async def count_owners(self) -> int:
        """
        Count users with owner role.

        Returns:
            Number of users with OWNER role
        """
        from sqlalchemy import func

        from src.models.enums import UserRole

        result = await self.session.execute(
            select(func.count(User.id)).where(User.role == UserRole.OWNER)
        )
        return result.scalar() or 0

    async def update_role(self, user_id: UUID, new_role: "UserRole") -> User:
        """
        Update user role with owner protection.

        Prevents removing the last owner from the system.

        Args:
            user_id: User UUID
            new_role: New role to assign

        Returns:
            Updated User

        Raises:
            ValueError: If user not found or attempting to remove last owner
        """
        from src.models.enums import UserRole

        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Prevent removing last owner
        if user.role == UserRole.OWNER and new_role != UserRole.OWNER:
            owner_count = await self.count_owners()
            if owner_count <= 1:
                raise ValueError("Cannot remove the last owner")

        user.role = new_role
        await self.session.flush()
        return user
