"""
Integration tests for pagination functionality.

Tests the pagination, search, and sorting features across list endpoints.
Uses the passwords endpoint as the test subject.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.auth import UserPrincipal, get_current_active_user
from src.main import app
from src.models.enums import UserRole
from src.models.orm.password import Password


@pytest.fixture
def test_org_id():
    """Generate a test organization ID."""
    return uuid4()


@pytest.fixture
def test_user(test_org_id):
    """Create a test user principal."""
    return UserPrincipal(
        user_id=uuid4(),
        email="test@example.com",
        name="Test User",
        role=UserRole.CONTRIBUTOR,
        is_active=True,
        is_verified=True,
    )


def create_mock_password(
    org_id,
    name: str,
    username: str | None = None,
    url: str | None = None,
    notes: str | None = None) -> MagicMock:
    """Create a mock password object."""
    mock = MagicMock(spec=Password)
    mock.id = uuid4()
    mock.organization_id = org_id
    mock.name = name
    mock.username = username
    mock.url = url
    mock.notes = notes
    mock.created_at = datetime.now()
    mock.updated_at = datetime.now()
    return mock


@pytest.mark.integration
class TestPaginationBasic:
    """Tests for basic pagination functionality."""

    async def test_pagination_first_page(self, test_user, test_org_id):
        """Test getting the first page of results with limit=2."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        # Create 5 mock passwords
        all_passwords = [
            create_mock_password(test_org_id, f"Password {i}") for i in range(1, 6)
        ]

        mock_password_repo = AsyncMock()
        # Return first 2 passwords, total of 5
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=(all_passwords[:2], 5)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"limit": 2, "offset": 0})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["total"] == 5
            assert data["limit"] == 2
            assert data["offset"] == 0

            # Verify repository was called with correct params
            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search=None,
                sort_by=None,
                sort_dir="asc",
                limit=2,
                offset=0)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_pagination_second_page(self, test_user, test_org_id):
        """Test getting the second page of results with limit=2, offset=2."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        # Create 5 mock passwords
        all_passwords = [
            create_mock_password(test_org_id, f"Password {i}") for i in range(1, 6)
        ]

        mock_password_repo = AsyncMock()
        # Return passwords 3-4, total of 5
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=(all_passwords[2:4], 5)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"limit": 2, "offset": 2})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["total"] == 5
            assert data["limit"] == 2
            assert data["offset"] == 2

            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search=None,
                sort_by=None,
                sort_dir="asc",
                limit=2,
                offset=2)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_pagination_last_page_partial(self, test_user, test_org_id):
        """Test getting the last page with fewer items than limit."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        # Create 5 mock passwords
        all_passwords = [
            create_mock_password(test_org_id, f"Password {i}") for i in range(1, 6)
        ]

        mock_password_repo = AsyncMock()
        # Return last password (only 1), total of 5
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=([all_passwords[4]], 5)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"limit": 2, "offset": 4})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["total"] == 5
            assert data["limit"] == 2
            assert data["offset"] == 4

            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search=None,
                sort_by=None,
                sort_dir="asc",
                limit=2,
                offset=4)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_pagination_default_values(self, test_user, test_org_id):
        """Test that default pagination values are applied."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(return_value=([], 0))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    # No pagination params - should use defaults
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords"
                    )

            assert response.status_code == 200
            data = response.json()
            # Default limit is 100, offset is 0
            assert data["limit"] == 100
            assert data["offset"] == 0

            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search=None,
                sort_by=None,
                sort_dir="asc",
                limit=100,
                offset=0)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestPaginationSearch:
    """Tests for search filtering with pagination."""

    async def test_search_filters_results(self, test_user, test_org_id):
        """Test that search parameter filters results."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        # Create passwords with different names
        admin_password = create_mock_password(test_org_id, "Admin Account")

        mock_password_repo = AsyncMock()
        # Search for "admin" should return only matching password
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=([admin_password], 1)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"search": "admin"})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["total"] == 1
            assert data["items"][0]["name"] == "Admin Account"

            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search="admin",
                sort_by=None,
                sort_dir="asc",
                limit=100,
                offset=0)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_search_returns_empty_when_no_match(self, test_user, test_org_id):
        """Test that search returns empty results when no match."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        mock_password_repo = AsyncMock()
        # Search for non-existent term returns empty
        mock_password_repo.get_paginated_by_org = AsyncMock(return_value=([], 0))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"search": "nonexistent"})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 0
            assert data["total"] == 0
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_search_with_pagination(self, test_user, test_org_id):
        """Test that search works correctly with pagination."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        # Create multiple matching passwords
        matching_passwords = [
            create_mock_password(test_org_id, f"Admin {i}") for i in range(1, 6)
        ]

        mock_password_repo = AsyncMock()
        # Return first 2 matching passwords, total of 5 matches
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=(matching_passwords[:2], 5)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"search": "Admin", "limit": 2, "offset": 0})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            # Total reflects filtered count, not total passwords
            assert data["total"] == 5
            assert data["limit"] == 2
            assert data["offset"] == 0

            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search="Admin",
                sort_by=None,
                sort_dir="asc",
                limit=2,
                offset=0)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestPaginationSorting:
    """Tests for sorting functionality with pagination."""

    async def test_sort_ascending(self, test_user, test_org_id):
        """Test sorting results in ascending order."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        # Create passwords in alphabetical order
        passwords = [
            create_mock_password(test_org_id, "Alpha"),
            create_mock_password(test_org_id, "Beta"),
            create_mock_password(test_org_id, "Gamma"),
        ]

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=(passwords, 3)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"sort_by": "name", "sort_dir": "asc"})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 3
            # Verify sorting was requested
            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search=None,
                sort_by="name",
                sort_dir="asc",
                limit=100,
                offset=0)
            # Verify order in response
            assert data["items"][0]["name"] == "Alpha"
            assert data["items"][1]["name"] == "Beta"
            assert data["items"][2]["name"] == "Gamma"
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_sort_descending(self, test_user, test_org_id):
        """Test sorting results in descending order."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        # Create passwords in reverse alphabetical order
        passwords = [
            create_mock_password(test_org_id, "Gamma"),
            create_mock_password(test_org_id, "Beta"),
            create_mock_password(test_org_id, "Alpha"),
        ]

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=(passwords, 3)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"sort_by": "name", "sort_dir": "desc"})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 3
            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search=None,
                sort_by="name",
                sort_dir="desc",
                limit=100,
                offset=0)
            # Verify reverse order in response
            assert data["items"][0]["name"] == "Gamma"
            assert data["items"][1]["name"] == "Beta"
            assert data["items"][2]["name"] == "Alpha"
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_sort_with_pagination(self, test_user, test_org_id):
        """Test sorting combined with pagination."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        # Return second page of sorted results
        passwords = [
            create_mock_password(test_org_id, "Delta"),
            create_mock_password(test_org_id, "Epsilon"),
        ]

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=(passwords, 5)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={
                            "sort_by": "name",
                            "sort_dir": "asc",
                            "limit": 2,
                            "offset": 2,
                        })

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["total"] == 5
            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search=None,
                sort_by="name",
                sort_dir="asc",
                limit=2,
                offset=2)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestPaginationEdgeCases:
    """Tests for edge cases in pagination."""

    async def test_offset_beyond_total_returns_empty(self, test_user, test_org_id):
        """Test that offset beyond total returns empty items but correct total."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        mock_password_repo = AsyncMock()
        # Offset is beyond total, return empty list but correct total
        mock_password_repo.get_paginated_by_org = AsyncMock(return_value=([], 5))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"limit": 10, "offset": 100})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 0
            assert data["total"] == 5  # Total still reflects actual count
            assert data["offset"] == 100
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_very_large_offset(self, test_user, test_org_id):
        """Test handling of very large offset values."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(return_value=([], 5))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"limit": 10, "offset": 999999})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 0
            assert data["offset"] == 999999
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_limit_zero_returns_validation_error(self, test_user, test_org_id):
        """Test that limit=0 returns a validation error."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.get(
                    f"/api/organizations/{test_org_id}/passwords",
                    params={"limit": 0})

            # Should return 422 validation error because limit must be >= 1
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_limit_exceeds_max_returns_validation_error(
        self, test_user, test_org_id
    ):
        """Test that limit exceeding max (1000) returns validation error."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.get(
                    f"/api/organizations/{test_org_id}/passwords",
                    params={"limit": 1001})

            # Should return 422 validation error because limit max is 1000
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_negative_offset_returns_validation_error(
        self, test_user, test_org_id
    ):
        """Test that negative offset returns validation error."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.get(
                    f"/api/organizations/{test_org_id}/passwords",
                    params={"offset": -1})

            # Should return 422 validation error because offset must be >= 0
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_invalid_sort_direction_returns_validation_error(
        self, test_user, test_org_id
    ):
        """Test that invalid sort direction returns validation error."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.get(
                    f"/api/organizations/{test_org_id}/passwords",
                    params={"sort_dir": "invalid"})

            # Should return 422 validation error for invalid sort_dir
            assert response.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_empty_search_treated_as_no_search(self, test_user, test_org_id):
        """Test that empty search string is handled correctly."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        passwords = [create_mock_password(test_org_id, "Test Password")]

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=(passwords, 1)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"search": ""})

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            # Empty search is passed as empty string
            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search="",
                sort_by=None,
                sort_dir="asc",
                limit=100,
                offset=0)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestPaginationCombined:
    """Tests for combined pagination, search, and sorting."""

    async def test_search_sort_and_paginate(self, test_user, test_org_id):
        """Test combining search, sort, and pagination together."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        # Filtered and sorted results
        passwords = [
            create_mock_password(test_org_id, "Admin Beta"),
            create_mock_password(test_org_id, "Admin Alpha"),
        ]

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=(passwords, 10)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={
                            "search": "Admin",
                            "sort_by": "name",
                            "sort_dir": "desc",
                            "limit": 2,
                            "offset": 4,
                        })

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["total"] == 10
            assert data["limit"] == 2
            assert data["offset"] == 4

            mock_password_repo.get_paginated_by_org.assert_called_once_with(
                test_org_id,
                search="Admin",
                sort_by="name",
                sort_dir="desc",
                limit=2,
                offset=4)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_max_limit_value(self, test_user, test_org_id):
        """Test that max limit (1000) is accepted."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(return_value=([], 0))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"limit": 1000})

            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 1000
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_min_limit_value(self, test_user, test_org_id):
        """Test that min limit (1) is accepted."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        passwords = [create_mock_password(test_org_id, "Single Result")]

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(
            return_value=(passwords, 5)
        )

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords",
                        params={"limit": 1})

            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 1
            assert len(data["items"]) == 1
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
