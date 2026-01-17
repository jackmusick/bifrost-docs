"""
BifrostDocs API Client for IT Glue Migration.

Async HTTP client for interacting with the BifrostDocs API.
Uses httpx for async HTTP requests with bearer token authentication.
"""

import logging
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


def _rewrite_docker_url(url: str) -> str:
    """
    Rewrite Docker-internal hostnames to localhost for local development.

    When the API runs in Docker, it generates presigned URLs with internal
    Docker DNS names (e.g., 'minio:9000'). The migration tool running on
    the host can't resolve these, so we rewrite to localhost.
    """
    # Known Docker-internal hostnames and their localhost mappings
    docker_hosts = {
        "minio": "localhost",
        "minio:9000": "localhost:9000",
        "minio:9001": "localhost:9001",
    }

    parsed = urlparse(url)
    if parsed.netloc in docker_hosts:
        new_netloc = docker_hosts[parsed.netloc]
        return urlunparse(parsed._replace(netloc=new_netloc))
    return url


class APIError(Exception):
    """Exception raised for API errors."""

    def __init__(self, status_code: int, message: str, response_body: Any = None):
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"API Error {status_code}: {message}")


class BifrostDocsClient:
    """
    Async client for the BifrostDocs API.

    Provides methods for all entity types used in IT Glue migration:
    - Organizations
    - Locations
    - Configurations (with types and statuses)
    - Documents
    - Passwords
    - Custom Assets (with types)
    - Relationships
    - Attachments
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
    ):
        """
        Initialize the BifrostDocs API client.

        Args:
            base_url: Base URL of the BifrostDocs API (e.g., "https://api.bifrostdocs.com")
            api_key: API key for authentication
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BifrostDocsClient":
        """Enter async context manager."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API endpoint path
            json: Request body as JSON
            params: Query parameters

        Returns:
            Response data (dict, list, or empty dict for 204)

        Raises:
            APIError: If the request fails
        """
        client = await self._ensure_client()

        try:
            response = await client.request(
                method=method,
                url=path,
                json=json,
                params=params,
            )
        except httpx.TimeoutException as e:
            raise APIError(0, f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise APIError(0, f"Request failed: {e}") from e

        if response.status_code >= 400:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text

            raise APIError(
                status_code=response.status_code,
                message=error_body.get("detail", str(error_body))
                if isinstance(error_body, dict)
                else str(error_body),
                response_body=error_body,
            )

        # Handle 204 No Content
        if response.status_code == 204:
            return {}

        return response.json()

    # =========================================================================
    # Organizations
    # =========================================================================

    async def list_organizations(self) -> list[dict[str, Any]]:
        """
        List all organizations.

        Returns:
            List of organization objects
        """
        result = await self._request("GET", "/api/organizations")
        return result  # type: ignore[return-value]

    async def create_organization(
        self,
        name: str,
        is_enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new organization.

        Args:
            name: Organization name
            is_enabled: Whether the organization is enabled (default: True)
            metadata: Optional metadata dictionary

        Returns:
            Created organization object
        """
        payload: dict[str, Any] = {"name": name, "is_enabled": is_enabled}
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._request("POST", "/api/organizations", json=payload)

    async def get_organization(self, org_id: str | UUID) -> dict[str, Any]:
        """
        Get an organization by ID.

        Args:
            org_id: Organization UUID

        Returns:
            Organization object
        """
        return await self._request("GET", f"/api/organizations/{org_id}")

    # =========================================================================
    # Configuration Types (Global)
    # =========================================================================

    async def list_configuration_types(
        self,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List all configuration types.

        Args:
            include_inactive: Include inactive types

        Returns:
            List of configuration type objects
        """
        result = await self._request(
            "GET",
            "/api/configuration-types",
            params={"include_inactive": include_inactive},
        )
        return result  # type: ignore[return-value]

    async def create_configuration_type(self, name: str) -> dict[str, Any]:
        """
        Create a new configuration type.

        Args:
            name: Configuration type name

        Returns:
            Created configuration type object
        """
        return await self._request(
            "POST",
            "/api/configuration-types",
            json={"name": name},
        )

    async def get_configuration_type(self, type_id: str | UUID) -> dict[str, Any]:
        """
        Get a configuration type by ID.

        Args:
            type_id: Configuration type UUID

        Returns:
            Configuration type object
        """
        return await self._request("GET", f"/api/configuration-types/{type_id}")

    # =========================================================================
    # Configuration Statuses (Global)
    # =========================================================================

    async def list_configuration_statuses(
        self,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List all configuration statuses.

        Args:
            include_inactive: Include inactive statuses

        Returns:
            List of configuration status objects
        """
        result = await self._request(
            "GET",
            "/api/configuration-statuses",
            params={"include_inactive": include_inactive},
        )
        return result  # type: ignore[return-value]

    async def create_configuration_status(self, name: str) -> dict[str, Any]:
        """
        Create a new configuration status.

        Args:
            name: Configuration status name

        Returns:
            Created configuration status object
        """
        return await self._request(
            "POST",
            "/api/configuration-statuses",
            json={"name": name},
        )

    # =========================================================================
    # Custom Asset Types (Global)
    # =========================================================================

    async def list_custom_asset_types(
        self,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List all custom asset types.

        Args:
            include_inactive: Include inactive types

        Returns:
            List of custom asset type objects
        """
        result = await self._request(
            "GET",
            "/api/custom-asset-types",
            params={"include_inactive": include_inactive},
        )
        return result  # type: ignore[return-value]

    async def create_custom_asset_type(
        self,
        name: str,
        fields: list[dict[str, Any]],
        display_field_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new custom asset type.

        Args:
            name: Custom asset type name
            fields: List of field definitions. Each field should have:
                - key: Unique identifier within type
                - name: Display name
                - type: Field type (text, textbox, number, date, checkbox, select, header, password, totp)
                - required: Whether field is required (default: False)
                - show_in_list: Whether to show in list view (default: False)
                - hint: Optional hint text
                - default_value: Optional default value
                - options: Required for select type
            display_field_key: Optional key for the field used to identify assets in lists

        Returns:
            Created custom asset type object
        """
        payload: dict[str, Any] = {"name": name, "fields": fields}
        if display_field_key is not None:
            payload["display_field_key"] = display_field_key
        return await self._request(
            "POST",
            "/api/custom-asset-types",
            json=payload,
        )

    async def get_custom_asset_type(self, type_id: str | UUID) -> dict[str, Any]:
        """
        Get a custom asset type by ID.

        Args:
            type_id: Custom asset type UUID

        Returns:
            Custom asset type object
        """
        return await self._request("GET", f"/api/custom-asset-types/{type_id}")

    # =========================================================================
    # Configurations (Organization-scoped)
    # =========================================================================

    async def list_configurations(
        self,
        org_id: str | UUID,
        configuration_type_id: str | UUID | None = None,
        configuration_status_id: str | UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List configurations for an organization.

        Args:
            org_id: Organization UUID
            configuration_type_id: Filter by configuration type
            configuration_status_id: Filter by configuration status
            limit: Maximum results per page
            offset: Number of results to skip

        Returns:
            Paginated response with items, total, limit, offset
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if configuration_type_id is not None:
            params["configuration_type_id"] = str(configuration_type_id)
        if configuration_status_id is not None:
            params["configuration_status_id"] = str(configuration_status_id)

        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/configurations",
            params=params,
        )

    async def create_configuration(
        self,
        org_id: str | UUID,
        name: str,
        configuration_type_id: str | UUID | None = None,
        configuration_status_id: str | UUID | None = None,
        serial_number: str | None = None,
        asset_tag: str | None = None,
        manufacturer: str | None = None,
        model: str | None = None,
        ip_address: str | None = None,
        mac_address: str | None = None,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
        interfaces: list[dict[str, Any]] | None = None,
        is_enabled: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new configuration.

        Args:
            org_id: Organization UUID
            name: Configuration name
            configuration_type_id: Configuration type UUID
            configuration_status_id: Configuration status UUID
            serial_number: Serial number
            asset_tag: Asset tag
            manufacturer: Manufacturer name
            model: Model name
            ip_address: IP address
            mac_address: MAC address
            notes: Notes (markdown)
            metadata: External system metadata
            interfaces: Network interfaces
            is_enabled: Whether the configuration is enabled (default: True)

        Returns:
            Created configuration object
        """
        payload: dict[str, Any] = {"name": name, "is_enabled": is_enabled}

        # Debug: Log when creating disabled configuration
        if not is_enabled:
            logger.info(f"API CLIENT: Creating config '{name}' with is_enabled={is_enabled}")

        if configuration_type_id is not None:
            payload["configuration_type_id"] = str(configuration_type_id)
        if configuration_status_id is not None:
            payload["configuration_status_id"] = str(configuration_status_id)
        if serial_number is not None:
            payload["serial_number"] = serial_number
        if asset_tag is not None:
            payload["asset_tag"] = asset_tag
        if manufacturer is not None:
            payload["manufacturer"] = manufacturer
        if model is not None:
            payload["model"] = model
        if ip_address is not None:
            payload["ip_address"] = ip_address
        if mac_address is not None:
            payload["mac_address"] = mac_address
        if notes is not None:
            payload["notes"] = notes
        if metadata is not None:
            payload["metadata"] = metadata
        if interfaces is not None:
            payload["interfaces"] = interfaces

        return await self._request(
            "POST",
            f"/api/organizations/{org_id}/configurations",
            json=payload,
        )

    async def get_configuration(
        self,
        org_id: str | UUID,
        config_id: str | UUID,
    ) -> dict[str, Any]:
        """
        Get a configuration by ID.

        Args:
            org_id: Organization UUID
            config_id: Configuration UUID

        Returns:
            Configuration object
        """
        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/configurations/{config_id}",
        )

    # =========================================================================
    # Locations (Organization-scoped)
    # =========================================================================

    async def list_locations(
        self,
        org_id: str | UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List locations for an organization.

        Args:
            org_id: Organization UUID
            limit: Maximum results per page
            offset: Number of results to skip

        Returns:
            Paginated response with items, total, limit, offset
        """
        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/locations",
            params={"limit": limit, "offset": offset},
        )

    async def create_location(
        self,
        org_id: str | UUID,
        name: str,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new location.

        Args:
            org_id: Organization UUID
            name: Location name
            notes: Notes (markdown)
            metadata: External system metadata

        Returns:
            Created location object
        """
        payload: dict[str, Any] = {"name": name}
        if notes is not None:
            payload["notes"] = notes
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._request(
            "POST",
            f"/api/organizations/{org_id}/locations",
            json=payload,
        )

    async def get_location(
        self,
        org_id: str | UUID,
        location_id: str | UUID,
    ) -> dict[str, Any]:
        """
        Get a location by ID.

        Args:
            org_id: Organization UUID
            location_id: Location UUID

        Returns:
            Location object
        """
        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/locations/{location_id}",
        )

    # =========================================================================
    # Documents (Organization-scoped)
    # =========================================================================

    async def list_documents(
        self,
        org_id: str | UUID,
        path: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List documents for an organization.

        Args:
            org_id: Organization UUID
            path: Filter by folder path
            limit: Maximum results per page
            offset: Number of results to skip

        Returns:
            Paginated response with items, total, limit, offset
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if path is not None:
            params["path"] = path

        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/documents",
            params=params,
        )

    async def create_document(
        self,
        org_id: str | UUID,
        path: str,
        name: str,
        content: str = "",
        metadata: dict[str, Any] | None = None,
        is_enabled: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new document.

        Args:
            org_id: Organization UUID
            path: Virtual folder path (e.g., "/Infrastructure/Network")
            name: Document title
            content: Markdown content
            metadata: External system metadata
            is_enabled: Whether the document is enabled (default: True)

        Returns:
            Created document object
        """
        payload: dict[str, Any] = {
            "path": path,
            "name": name,
            "content": content,
            "is_enabled": is_enabled,
        }
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._request(
            "POST",
            f"/api/organizations/{org_id}/documents",
            json=payload,
        )

    async def get_document(
        self,
        org_id: str | UUID,
        doc_id: str | UUID,
    ) -> dict[str, Any]:
        """
        Get a document by ID.

        Args:
            org_id: Organization UUID
            doc_id: Document UUID

        Returns:
            Document object
        """
        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/documents/{doc_id}",
        )

    # =========================================================================
    # Passwords (Organization-scoped)
    # =========================================================================

    async def list_passwords(
        self,
        org_id: str | UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List passwords for an organization.

        Args:
            org_id: Organization UUID
            limit: Maximum results per page
            offset: Number of results to skip

        Returns:
            Paginated response with items, total, limit, offset
        """
        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/passwords",
            params={"limit": limit, "offset": offset},
        )

    async def create_password(
        self,
        org_id: str | UUID,
        name: str,
        password: str,
        username: str | None = None,
        totp_secret: str | None = None,
        url: str | None = None,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
        is_enabled: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new password entry.

        Args:
            org_id: Organization UUID
            name: Password name/title
            password: Password value
            username: Associated username
            totp_secret: TOTP secret for 2FA
            url: Associated URL
            notes: Notes (markdown)
            metadata: External system metadata
            is_enabled: Whether the password is enabled (default: True)

        Returns:
            Created password object (password value not returned)
        """
        payload: dict[str, Any] = {
            "name": name,
            "password": password,
            "is_enabled": is_enabled,
        }
        if username is not None:
            payload["username"] = username
        if totp_secret is not None:
            payload["totp_secret"] = totp_secret
        if url is not None:
            payload["url"] = url
        if notes is not None:
            payload["notes"] = notes
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._request(
            "POST",
            f"/api/organizations/{org_id}/passwords",
            json=payload,
        )

    async def get_password(
        self,
        org_id: str | UUID,
        password_id: str | UUID,
    ) -> dict[str, Any]:
        """
        Get a password by ID (without password value).

        Args:
            org_id: Organization UUID
            password_id: Password UUID

        Returns:
            Password object (without password value)
        """
        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/passwords/{password_id}",
        )

    # =========================================================================
    # Custom Assets (Organization-scoped, Type-scoped)
    # =========================================================================

    async def list_custom_assets(
        self,
        org_id: str | UUID,
        type_id: str | UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List custom assets for a type within an organization.

        Args:
            org_id: Organization UUID
            type_id: Custom asset type UUID
            limit: Maximum results per page
            offset: Number of results to skip

        Returns:
            Paginated response with items, total, limit, offset
        """
        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/custom-asset-types/{type_id}/assets",
            params={"limit": limit, "offset": offset},
        )

    async def create_custom_asset(
        self,
        org_id: str | UUID,
        type_id: str | UUID,
        values: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        is_enabled: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new custom asset.

        Args:
            org_id: Organization UUID
            type_id: Custom asset type UUID
            values: Field values (keys must match type's field definitions)
            metadata: External system metadata
            is_enabled: Whether the custom asset is enabled (default: True)

        Returns:
            Created custom asset object (password fields filtered)
        """
        payload: dict[str, Any] = {
            "values": values,
            "is_enabled": is_enabled,
        }
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._request(
            "POST",
            f"/api/organizations/{org_id}/custom-asset-types/{type_id}/assets",
            json=payload,
        )

    async def get_custom_asset(
        self,
        org_id: str | UUID,
        type_id: str | UUID,
        asset_id: str | UUID,
    ) -> dict[str, Any]:
        """
        Get a custom asset by ID.

        Args:
            org_id: Organization UUID
            type_id: Custom asset type UUID
            asset_id: Custom asset UUID

        Returns:
            Custom asset object (password fields filtered)
        """
        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/custom-asset-types/{type_id}/assets/{asset_id}",
        )

    # =========================================================================
    # Relationships (Organization-scoped)
    # =========================================================================

    async def list_relationships(
        self,
        org_id: str | UUID,
        entity_type: str,
        entity_id: str | UUID,
    ) -> list[dict[str, Any]]:
        """
        List relationships for an entity.

        Args:
            org_id: Organization UUID
            entity_type: Entity type (password, configuration, location, document, custom_asset)
            entity_id: Entity UUID

        Returns:
            List of relationship objects
        """
        result = await self._request(
            "GET",
            f"/api/organizations/{org_id}/relationships",
            params={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
            },
        )
        return result  # type: ignore[return-value]

    async def create_relationship(
        self,
        org_id: str | UUID,
        source_type: str,
        source_id: str | UUID,
        target_type: str,
        target_id: str | UUID,
    ) -> dict[str, Any]:
        """
        Create a relationship between two entities.

        Relationships are bidirectional - creating A->B is equivalent to B->A.

        Args:
            org_id: Organization UUID
            source_type: Source entity type
            source_id: Source entity UUID
            target_type: Target entity type
            target_id: Target entity UUID

        Returns:
            Created relationship object
        """
        return await self._request(
            "POST",
            f"/api/organizations/{org_id}/relationships",
            json={
                "source_type": source_type,
                "source_id": str(source_id),
                "target_type": target_type,
                "target_id": str(target_id),
            },
        )

    async def delete_relationship(
        self,
        org_id: str | UUID,
        relationship_id: str | UUID,
    ) -> None:
        """
        Delete a relationship.

        Args:
            org_id: Organization UUID
            relationship_id: Relationship UUID
        """
        await self._request(
            "DELETE",
            f"/api/organizations/{org_id}/relationships/{relationship_id}",
        )

    # =========================================================================
    # Attachments (Organization-scoped)
    # =========================================================================

    async def list_attachments(
        self,
        org_id: str | UUID,
        entity_type: str | None = None,
        entity_id: str | UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List attachments for an organization.

        Args:
            org_id: Organization UUID
            entity_type: Filter by entity type
            entity_id: Filter by entity ID (requires entity_type)
            limit: Maximum results (1-1000)
            offset: Results to skip

        Returns:
            Response with items list and total count
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if entity_type is not None:
            params["entity_type"] = entity_type
        if entity_id is not None:
            params["entity_id"] = str(entity_id)

        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/attachments",
            params=params,
        )

    async def create_attachment(
        self,
        org_id: str | UUID,
        entity_type: str,
        entity_id: str | UUID,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> dict[str, Any]:
        """
        Create an attachment record and get a presigned upload URL.

        After calling this, use the returned upload_url to PUT the file directly.

        Args:
            org_id: Organization UUID
            entity_type: Entity type this attaches to
            entity_id: Entity UUID this attaches to
            filename: Original filename
            content_type: MIME type
            size_bytes: File size in bytes

        Returns:
            Response with id, filename, upload_url, expires_in
        """
        return await self._request(
            "POST",
            f"/api/organizations/{org_id}/attachments",
            json={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "filename": filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
            },
        )

    async def get_attachment_download_url(
        self,
        org_id: str | UUID,
        attachment_id: str | UUID,
    ) -> dict[str, Any]:
        """
        Get a presigned download URL for an attachment.

        Args:
            org_id: Organization UUID
            attachment_id: Attachment UUID

        Returns:
            Response with download_url, filename, content_type, size_bytes, expires_in
        """
        return await self._request(
            "GET",
            f"/api/organizations/{org_id}/attachments/{attachment_id}/download",
        )

    async def delete_attachment(
        self,
        org_id: str | UUID,
        attachment_id: str | UUID,
    ) -> None:
        """
        Delete an attachment.

        Args:
            org_id: Organization UUID
            attachment_id: Attachment UUID
        """
        await self._request(
            "DELETE",
            f"/api/organizations/{org_id}/attachments/{attachment_id}",
        )

    async def upload_document_image(
        self,
        org_id: str | UUID,
        filename: str,
        content_type: str,
        size_bytes: int,
        document_id: str | UUID | None = None,
    ) -> dict[str, Any]:
        """
        Upload an image for embedding in markdown documents.

        Args:
            org_id: Organization UUID
            filename: Original filename
            content_type: MIME type (must be image/*)
            size_bytes: File size in bytes
            document_id: Optional document ID to associate with

        Returns:
            Response with id, upload_url, image_url, expires_in
        """
        payload: dict[str, Any] = {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
        }
        if document_id is not None:
            payload["document_id"] = str(document_id)

        return await self._request(
            "POST",
            f"/api/organizations/{org_id}/documents/images",
            json=payload,
        )

    async def upload_file_to_presigned_url(
        self,
        upload_url: str,
        file_content: bytes,
        content_type: str,
    ) -> None:
        """
        Upload a file to a presigned S3 URL.

        This uses a separate httpx client without authentication headers.

        Args:
            upload_url: Presigned S3 PUT URL
            file_content: File content as bytes
            content_type: MIME type
        """
        # Rewrite Docker-internal URLs for local development
        upload_url = _rewrite_docker_url(upload_url)

        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.put(
                upload_url,
                content=file_content,
                headers={"Content-Type": content_type},
            )
            if response.status_code >= 400:
                raise APIError(
                    status_code=response.status_code,
                    message=f"Failed to upload file: {response.text}",
                )
