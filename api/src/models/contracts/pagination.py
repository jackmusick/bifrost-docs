"""
Pagination contracts for API responses.

Provides generic paginated response model and pagination parameters.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response model.

    Provides consistent pagination structure across all list endpoints.
    """

    items: list[T]
    total: int = Field(..., description="Total number of items matching the query")
    limit: int = Field(..., description="Maximum items per page")
    offset: int = Field(..., description="Number of items skipped")

    @property
    def page(self) -> int:
        """Current page number (1-indexed)."""
        return (self.offset // self.limit) + 1 if self.limit > 0 else 1

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        return (self.total + self.limit - 1) // self.limit if self.limit > 0 else 1

    @property
    def has_next(self) -> bool:
        """Whether there are more items after this page."""
        return self.offset + len(self.items) < self.total

    @property
    def has_previous(self) -> bool:
        """Whether there are items before this page."""
        return self.offset > 0


class PaginationParams(BaseModel):
    """
    Common pagination parameters for list endpoints.

    Can be used directly or as a reference for Query parameters.
    """

    limit: int = Field(default=100, ge=1, le=1000, description="Maximum items per page")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    search: str | None = Field(default=None, description="Search term for filtering")
    sort_by: str | None = Field(default=None, description="Column to sort by")
    sort_dir: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort direction: 'asc' or 'desc'",
    )
