"""Entity importers for IT Glue to BifrostDocs migration.

This module contains the logic to import entities from parsed CSV data
into BifrostDocs via the API.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from itglue_migrate.api_client import APIError, BifrostDocsClient
from itglue_migrate.csv_parser import slugify_to_display_name
from itglue_migrate.progress import Phase, ProgressReporter, SimpleProgressReporter
from itglue_migrate.state import MigrationState

logger = logging.getLogger(__name__)

# Pattern to match IT Glue document folders: DOC-{org_id}-{doc_id} {name}
DOC_FOLDER_PATTERN = re.compile(r"^DOC-\d+-(\d+)\s")


def map_archived_to_is_enabled(archived_value: str | None) -> bool:
    """Convert IT Glue archived Yes/No to is_enabled boolean.

    Args:
        archived_value: "Yes" or "No" from IT Glue export

    Returns:
        False if archived=Yes, True if archived=No or missing
    """
    if not archived_value:
        return True  # Default to enabled if missing
    return str(archived_value).lower() != "yes"


def map_org_status_to_is_enabled(status: str | None) -> bool:
    """Convert IT Glue organization_status to is_enabled boolean.

    Args:
        status: "Active" or other status from IT Glue export

    Returns:
        True if Active, False otherwise
    """
    if not status:
        return True  # Default to enabled if missing
    return str(status).lower() == "active"


def format_location_notes_html(row: dict[str, Any]) -> str:
    """Format location address fields as HTML with proper line breaks.

    Args:
        row: Dict containing location fields from CSV

    Returns:
        HTML string with address fields on separate lines
    """
    parts = []

    if row.get("address_1"):
        parts.append(f'<strong>Address 1:</strong> {row["address_1"]}')
    if row.get("address_2"):
        parts.append(f'<strong>Address 2:</strong> {row["address_2"]}')
    if row.get("city"):
        parts.append(f'<strong>City:</strong> {row["city"]}')
    if row.get("region"):
        parts.append(f'<strong>Region:</strong> {row["region"]}')
    if row.get("country"):
        parts.append(f'<strong>Country:</strong> {row["country"]}')
    if row.get("postal_code"):
        parts.append(f'<strong>Postal Code:</strong> {row["postal_code"]}')

    # Join with <br> tags for line breaks
    return "<br>".join(parts)


def _build_document_folder_map(
    documents_path: Path,
) -> dict[str, tuple[str, Path | None]]:
    """
    Scan export documents folder and map document IDs to (folder_path, html_file).

    The IT Glue export structure is:
    - documents/{folder}/DOC-{org}-{doc_id} {name}/{name}.html - nested in folder
    - documents/DOC-{org}-{doc_id} {name}/{name}.html - root level

    Args:
        documents_path: Path to the documents/ folder in the export.

    Returns:
        Dict mapping doc_id to (folder_path, html_file_path).
        folder_path is "/" for root-level documents, otherwise "/FolderName".
        html_file_path is the path to the HTML file, or None if not found.
    """
    result: dict[str, tuple[str, Path | None]] = {}

    if not documents_path.exists():
        logger.warning(f"Documents path does not exist: {documents_path}")
        return result

    # Walk the documents directory
    for item in documents_path.rglob("*"):
        if not item.is_dir():
            continue

        # Check if this is a DOC-* folder
        match = DOC_FOLDER_PATTERN.match(item.name)
        if not match:
            continue

        doc_id = match.group(1)

        # Determine the folder path based on parent
        # If parent is documents_path, it's root level ("/")
        # Otherwise, extract folder name from path between documents_path and item
        rel_path = item.relative_to(documents_path)
        parts = rel_path.parts

        if len(parts) == 1:
            # Root level: documents/DOC-xxx-123 Name/
            folder_path = "/"
        else:
            # Nested: documents/FolderName/DOC-xxx-123 Name/
            # The folder path is everything except the last DOC-* part
            folder_parts = parts[:-1]
            folder_path = "/" + "/".join(folder_parts)

        # Find HTML file inside the DOC-* folder
        html_files = list(item.glob("*.html"))
        html_file = html_files[0] if html_files else None

        result[doc_id] = (folder_path, html_file)
        logger.debug(f"Mapped document {doc_id} -> {folder_path}, {html_file}")

    logger.info(f"Built document folder map with {len(result)} entries")
    return result


class EntityImporter:
    """Imports entities from IT Glue export data into BifrostDocs.

    Handles all entity types: organizations, locations, configuration types,
    configurations, custom asset types, custom assets, documents, and passwords.

    The importer uses the MigrationState for tracking progress and enabling
    resume capability, and the ProgressReporter for displaying progress to users.

    Example:
        >>> async with BifrostDocsClient(base_url, api_key) as client:
        ...     state = MigrationState(export_path="/path/to/export")
        ...     reporter = ProgressReporter()
        ...     importer = EntityImporter(client, state, reporter)
        ...     await importer.import_organizations(orgs, org_mapping)
    """

    def __init__(
        self,
        client: BifrostDocsClient,
        state: MigrationState,
        reporter: ProgressReporter | SimpleProgressReporter,
    ) -> None:
        """Initialize the entity importer.

        Args:
            client: BifrostDocs API client instance.
            state: Migration state for tracking progress.
            reporter: Progress reporter for displaying progress.
        """
        self.client = client
        self.state = state
        self.reporter = reporter

        # Cache for configuration type name -> UUID mapping
        self._config_type_cache: dict[str, str] = {}

        # Cache for configuration status name -> UUID mapping
        self._config_status_cache: dict[str, str] = {}

        # Cache for custom asset type name -> UUID mapping
        self._custom_asset_type_cache: dict[str, str] = {}

    def _get_org_uuid(self, itglue_org_id: str) -> str | None:
        """Get the BifrostDocs UUID for an IT Glue organization ID.

        Args:
            itglue_org_id: The IT Glue organization ID.

        Returns:
            The BifrostDocs UUID if found, None otherwise.
        """
        return self.state.id_mapper.get("organization", itglue_org_id)

    async def import_organizations(
        self,
        orgs: list[dict[str, Any]],
        org_mapping: dict[str, Any],
    ) -> int:
        """Import organizations from IT Glue export.

        For matched organizations (status="matched"), adds them to the ID map
        without creating new organizations. For organizations to create
        (status="create"), calls the API to create them.

        Args:
            orgs: List of organization dictionaries from CSV parser.
            org_mapping: Organization mapping from plan.json with structure:
                {
                    "mappings": [
                        {
                            "itglue_id": "123",
                            "itglue_name": "Acme Inc",
                            "status": "matched" | "create",
                            "bifrost_id": "uuid-abc",  # if matched
                            "bifrost_name": "Acme Inc"  # if matched
                        }
                    ]
                }

        Returns:
            Count of newly created organizations.
        """
        self.reporter.start_phase(Phase.ORGANIZATIONS, len(orgs))
        self.state.current_phase = Phase.ORGANIZATIONS

        created_count = 0
        seen_names: set[str] = set()

        # Build lookup from org_mapping
        mapping_lookup: dict[str, dict[str, Any]] = {}
        for mapping in org_mapping.get("mappings", []):
            itglue_id = str(mapping.get("itglue_id", ""))
            if itglue_id:
                mapping_lookup[itglue_id] = mapping

        for org in orgs:
            itglue_id = str(org.get("id", ""))
            org_name = org.get("name", "")

            if not itglue_id:
                self.reporter.warning("Organization missing ID, skipping")
                self.reporter.update_progress(skipped=1)
                continue

            # Check if already completed
            if self.state.is_completed(Phase.ORGANIZATIONS, itglue_id):
                self.reporter.update_progress(skipped=1)
                continue

            self.reporter.set_current_item(f"Organization: {org_name}")

            try:
                mapping = mapping_lookup.get(itglue_id, {})
                status = mapping.get("status", "create")

                if status == "matched":
                    # Just add to ID map without creating
                    bifrost_id = mapping.get("bifrost_id")
                    if bifrost_id:
                        # Add both by IT Glue ID and by name (CSVs reference orgs by name)
                        self.state.id_mapper.add("organization", itglue_id, bifrost_id)
                        self.state.id_mapper.add("organization", org_name, bifrost_id)
                        self.state.mark_completed(Phase.ORGANIZATIONS, itglue_id)
                        self.reporter.update_progress(succeeded=1)
                        logger.debug(
                            f"Matched organization '{org_name}' to existing BifrostDocs org {bifrost_id}"
                        )
                    else:
                        self.reporter.warning(
                            f"Matched organization '{org_name}' has no bifrost_id"
                        )
                        self.reporter.update_progress(failed=1)
                        self.state.mark_failed(
                            Phase.ORGANIZATIONS,
                            itglue_id,
                            "Matched organization missing bifrost_id",
                        )
                else:
                    # Create new organization
                    # Check for duplicate names
                    if org_name.lower() in seen_names:
                        self.reporter.warning(
                            f"Duplicate organization name '{org_name}', skipping"
                        )
                        self.reporter.update_progress(skipped=1)
                        self.state.add_warning(
                            f"Skipped duplicate organization: {org_name}"
                        )
                        continue

                    seen_names.add(org_name.lower())

                    # Map organization_status to is_enabled
                    org_status = org.get("organization_status")
                    is_enabled = map_org_status_to_is_enabled(org_status)

                    # Create organization via API
                    metadata = {"itglue_id": itglue_id}
                    if org.get("description"):
                        metadata["description"] = org["description"]
                    if org.get("quick_notes"):
                        metadata["quick_notes"] = org["quick_notes"]

                    result = await self.client.create_organization(
                        name=org_name,
                        is_enabled=is_enabled,
                        metadata=metadata,
                    )

                    bifrost_id = result.get("id")
                    if bifrost_id:
                        # Add both by IT Glue ID and by name (CSVs reference orgs by name)
                        self.state.id_mapper.add("organization", itglue_id, bifrost_id)
                        self.state.id_mapper.add("organization", org_name, bifrost_id)
                        self.state.mark_completed(Phase.ORGANIZATIONS, itglue_id)
                        self.reporter.update_progress(succeeded=1)
                        created_count += 1
                        logger.info(f"Created organization '{org_name}' -> {bifrost_id}")
                    else:
                        raise APIError(
                            500, f"API response missing 'id' for organization '{org_name}'"
                        )

            except APIError as e:
                error_msg = f"Failed to import organization '{org_name}': {e.message}"
                self.reporter.error(error_msg)
                self.reporter.update_progress(failed=1)
                self.state.mark_failed(Phase.ORGANIZATIONS, itglue_id, error_msg)
                logger.error(error_msg)

        self.reporter.complete_phase()
        return created_count

    async def import_locations(self, locations: list[dict[str, Any]]) -> int:
        """Import locations from IT Glue export.

        Requires organizations to be imported first for org UUID lookup.

        Args:
            locations: List of location dictionaries from CSV parser.

        Returns:
            Count of created locations.
        """
        self.reporter.start_phase(Phase.LOCATIONS, len(locations))
        self.state.current_phase = Phase.LOCATIONS

        created_count = 0

        for location in locations:
            itglue_id = str(location.get("id", ""))
            location_name = location.get("name", "Unknown Location")
            org_id = str(location.get("organization_id", ""))

            if not itglue_id:
                self.reporter.warning(f"Location '{location_name}' missing ID, skipping")
                self.reporter.update_progress(skipped=1)
                continue

            # Check if already completed
            if self.state.is_completed(Phase.LOCATIONS, itglue_id):
                self.reporter.update_progress(skipped=1)
                continue

            self.reporter.set_current_item(f"Location: {location_name}")

            try:
                # Get organization UUID
                org_uuid = self._get_org_uuid(org_id)
                if not org_uuid:
                    self.reporter.warning(
                        f"Location '{location_name}' has unknown org ID {org_id}, skipping"
                    )
                    self.reporter.update_progress(skipped=1)
                    self.state.add_warning(
                        f"Skipped location '{location_name}': unknown organization"
                    )
                    continue

                # Build notes from address fields using HTML formatting
                html_notes = format_location_notes_html(location)

                # Add phone if present
                if location.get("phone"):
                    if html_notes:
                        html_notes += "<br><strong>Phone:</strong> " + location["phone"]
                    else:
                        html_notes = f'<strong>Phone:</strong> {location["phone"]}'

                # Wrap in paragraph tags for tiptap compatibility
                notes = f"<p>{html_notes}</p>" if html_notes else None

                # Create location via API
                metadata = {"itglue_id": itglue_id}

                result = await self.client.create_location(
                    org_id=org_uuid,
                    name=location_name,
                    notes=notes,
                    metadata=metadata,
                )

                bifrost_id = result.get("id")
                if bifrost_id:
                    self.state.id_mapper.add("location", itglue_id, bifrost_id)
                    self.state.mark_completed(Phase.LOCATIONS, itglue_id)
                    self.reporter.update_progress(succeeded=1)
                    created_count += 1
                    logger.debug(f"Created location '{location_name}' -> {bifrost_id}")
                else:
                    raise APIError(
                        500, f"API response missing 'id' for location '{location_name}'"
                    )

            except APIError as e:
                error_msg = f"Failed to import location '{location_name}': {e.message}"
                self.reporter.error(error_msg)
                self.reporter.update_progress(failed=1)
                self.state.mark_failed(Phase.LOCATIONS, itglue_id, error_msg)
                logger.error(error_msg)

        self.reporter.complete_phase()
        return created_count

    async def import_configuration_types(
        self, configs: list[dict[str, Any]]
    ) -> int:
        """Import configuration types from IT Glue configurations.

        Extracts unique configuration_type values from configurations,
        fetches existing types from API, and creates missing types.

        Args:
            configs: List of configuration dictionaries from CSV parser.

        Returns:
            Count of created configuration types.
        """
        # Extract unique configuration types
        type_names: set[str] = set()
        for config in configs:
            config_type = config.get("configuration_type")
            if config_type:
                type_names.add(config_type)

        self.reporter.start_phase(Phase.CONFIGURATION_TYPES, len(type_names))
        self.state.current_phase = Phase.CONFIGURATION_TYPES

        created_count = 0

        # Fetch existing configuration types
        try:
            existing_types = await self.client.list_configuration_types(
                include_inactive=True
            )
            existing_type_names = {t["name"].lower(): t["id"] for t in existing_types}
        except APIError as e:
            self.reporter.error(f"Failed to fetch existing configuration types: {e.message}")
            self.reporter.complete_phase()
            return 0

        for type_name in sorted(type_names):
            # Use type name as ID for state tracking
            type_id = f"type:{type_name}"

            # Check if already completed in this run
            if self.state.is_completed(Phase.CONFIGURATION_TYPES, type_id):
                self.reporter.update_progress(skipped=1)
                continue

            self.reporter.set_current_item(f"Config Type: {type_name}")

            try:
                # Check if type already exists
                existing_id = existing_type_names.get(type_name.lower())
                if existing_id:
                    self._config_type_cache[type_name.lower()] = existing_id
                    self.state.id_mapper.add("configuration_type", type_id, existing_id)
                    self.state.mark_completed(Phase.CONFIGURATION_TYPES, type_id)
                    self.reporter.update_progress(skipped=1)
                    logger.debug(
                        f"Configuration type '{type_name}' already exists: {existing_id}"
                    )
                    continue

                # Create new configuration type
                result = await self.client.create_configuration_type(name=type_name)
                bifrost_id = result.get("id")

                if bifrost_id:
                    self._config_type_cache[type_name.lower()] = bifrost_id
                    self.state.id_mapper.add("configuration_type", type_id, bifrost_id)
                    self.state.mark_completed(Phase.CONFIGURATION_TYPES, type_id)
                    self.reporter.update_progress(succeeded=1)
                    created_count += 1
                    logger.info(f"Created configuration type '{type_name}' -> {bifrost_id}")
                else:
                    raise APIError(
                        500,
                        f"API response missing 'id' for configuration type '{type_name}'",
                    )

            except APIError as e:
                error_msg = f"Failed to create configuration type '{type_name}': {e.message}"
                self.reporter.error(error_msg)
                self.reporter.update_progress(failed=1)
                self.state.mark_failed(Phase.CONFIGURATION_TYPES, type_id, error_msg)
                logger.error(error_msg)

        self.reporter.complete_phase()
        return created_count

    async def import_configurations(self, configs: list[dict[str, Any]]) -> int:
        """Import configurations from IT Glue export.

        Requires organizations and configuration types to be imported first.

        Args:
            configs: List of configuration dictionaries from CSV parser.

        Returns:
            Count of created configurations.
        """
        self.reporter.start_phase(Phase.CONFIGURATIONS, len(configs))
        self.state.current_phase = Phase.CONFIGURATIONS

        created_count = 0

        # Ensure config type cache is populated
        if not self._config_type_cache:
            try:
                existing_types = await self.client.list_configuration_types(
                    include_inactive=True
                )
                self._config_type_cache = {
                    t["name"].lower(): t["id"] for t in existing_types
                }
            except APIError as e:
                self.reporter.error(
                    f"Failed to fetch configuration types: {e.message}"
                )

        # Ensure config status cache is populated
        if not self._config_status_cache:
            try:
                existing_statuses = await self.client.list_configuration_statuses(
                    include_inactive=True
                )
                self._config_status_cache = {
                    s["name"].lower(): s["id"] for s in existing_statuses
                }
            except APIError as e:
                self.reporter.error(
                    f"Failed to fetch configuration statuses: {e.message}"
                )

        for config in configs:
            itglue_id = str(config.get("id", ""))
            config_name = config.get("name", "Unknown Configuration")
            org_id = str(config.get("organization_id", ""))

            if not itglue_id:
                self.reporter.warning(
                    f"Configuration '{config_name}' missing ID, skipping"
                )
                self.reporter.update_progress(skipped=1)
                continue

            # Check if already completed
            if self.state.is_completed(Phase.CONFIGURATIONS, itglue_id):
                self.reporter.update_progress(skipped=1)
                continue

            self.reporter.set_current_item(f"Configuration: {config_name}")

            try:
                # Get organization UUID
                org_uuid = self._get_org_uuid(org_id)
                if not org_uuid:
                    self.reporter.warning(
                        f"Configuration '{config_name}' has unknown org ID {org_id}, skipping"
                    )
                    self.reporter.update_progress(skipped=1)
                    self.state.add_warning(
                        f"Skipped configuration '{config_name}': unknown organization"
                    )
                    continue

                # Get configuration type UUID
                config_type_name = config.get("configuration_type", "")
                config_type_id = None
                if config_type_name:
                    config_type_id = self._config_type_cache.get(config_type_name.lower())

                # Get configuration status UUID
                config_status_name = config.get("configuration_status", "")
                config_status_id = None
                if config_status_name:
                    config_status_id = self._config_status_cache.get(
                        config_status_name.lower()
                    )

                # Parse configuration_interfaces if it's a string
                interfaces = config.get("configuration_interfaces")
                if isinstance(interfaces, str):
                    try:
                        interfaces = json.loads(interfaces)
                    except json.JSONDecodeError:
                        interfaces = None

                # Map archived AND status to is_enabled
                # Rule: is_enabled = False if archived == 'Yes' OR status != 'Active'
                archived = config.get("archived")
                is_enabled = map_archived_to_is_enabled(archived)
                if config_status_name and config_status_name.lower() != "active":
                    is_enabled = False

                # Debug: Log is_enabled value
                if not is_enabled:
                    logger.info(f"CONFIG DISABLED: '{config_name}' archived={archived!r} status={config_status_name!r} -> is_enabled={is_enabled}")

                # Create configuration via API
                metadata = {"itglue_id": itglue_id}

                result = await self.client.create_configuration(
                    org_id=org_uuid,
                    name=config_name,
                    configuration_type_id=config_type_id,
                    configuration_status_id=config_status_id,
                    serial_number=config.get("serial"),
                    manufacturer=config.get("manufacturer"),
                    model=config.get("model"),
                    ip_address=config.get("ip"),
                    mac_address=config.get("mac"),
                    notes=config.get("notes"),
                    metadata=metadata,
                    interfaces=interfaces,
                    is_enabled=is_enabled,
                )

                bifrost_id = result.get("id")
                if bifrost_id:
                    self.state.id_mapper.add("configuration", itglue_id, bifrost_id)
                    self.state.mark_completed(Phase.CONFIGURATIONS, itglue_id)
                    disabled_count = 1 if not is_enabled else 0
                    self.reporter.update_progress(succeeded=1, disabled=disabled_count)
                    created_count += 1
                    logger.debug(f"Created configuration '{config_name}' -> {bifrost_id}")
                else:
                    raise APIError(
                        500,
                        f"API response missing 'id' for configuration '{config_name}'",
                    )

            except APIError as e:
                error_msg = f"Failed to import configuration '{config_name}': {e.message}"
                self.reporter.error(error_msg)
                self.reporter.update_progress(failed=1)
                self.state.mark_failed(Phase.CONFIGURATIONS, itglue_id, error_msg)
                logger.error(error_msg)

        self.reporter.complete_phase()
        return created_count

    async def import_custom_asset_types(
        self, schemas: dict[str, dict[str, Any]]
    ) -> int:
        """Import custom asset types from plan.json schemas.

        Args:
            schemas: Dictionary mapping type slug to schema info:
                {
                    "ssl-certificates": {
                        "display_name": "SSL Certificates",
                        "fields": [
                            {"name": "Domain", "field_type": "text", "required": true},
                            ...
                        ]
                    }
                }

        Returns:
            Count of created custom asset types.
        """
        self.reporter.start_phase(Phase.CUSTOM_ASSET_TYPES, len(schemas))
        self.state.current_phase = Phase.CUSTOM_ASSET_TYPES

        created_count = 0

        # Fetch existing custom asset types
        try:
            existing_types = await self.client.list_custom_asset_types(
                include_inactive=True
            )
            existing_type_names = {t["name"].lower(): t["id"] for t in existing_types}
        except APIError as e:
            self.reporter.error(
                f"Failed to fetch existing custom asset types: {e.message}"
            )
            self.reporter.complete_phase()
            return 0

        for type_slug, schema in schemas.items():
            type_id = f"type:{type_slug}"
            display_name = schema.get("display_name") or slugify_to_display_name(type_slug)

            # Check if already completed
            if self.state.is_completed(Phase.CUSTOM_ASSET_TYPES, type_id):
                self.reporter.update_progress(skipped=1)
                continue

            self.reporter.set_current_item(f"Custom Asset Type: {display_name}")

            try:
                # Check if type already exists
                existing_id = existing_type_names.get(display_name.lower())
                if existing_id:
                    self._custom_asset_type_cache[type_slug] = existing_id
                    self.state.id_mapper.add("custom_asset_type", type_id, existing_id)
                    self.state.mark_completed(Phase.CUSTOM_ASSET_TYPES, type_id)
                    self.reporter.update_progress(skipped=1)
                    logger.debug(
                        f"Custom asset type '{display_name}' already exists: {existing_id}"
                    )
                    continue

                # Build field definitions for API
                api_fields = []
                field_defs = schema.get("fields", [])
                display_field_key = None
                first_text_field_key = None

                for idx, field_def in enumerate(field_defs):
                    field_name = field_def.get("name", f"field_{idx}")
                    field_type = field_def.get("field_type", "text")

                    # Map IT Glue field types to BifrostDocs field types
                    type_mapping = {
                        "text": "text",
                        "textbox": "textbox",
                        "number": "number",
                        "date": "date",
                        "checkbox": "checkbox",
                        "select": "select",
                    }
                    api_field_type = type_mapping.get(field_type, "text")

                    # Generate a key from the field name
                    field_key = (
                        field_name.lower()
                        .replace(" ", "_")
                        .replace("-", "_")
                        .replace(".", "_")
                    )

                    api_field = {
                        "key": field_key,
                        "name": field_name,
                        "type": api_field_type,
                        "required": field_def.get("required", False),
                        "show_in_list": idx < 3,  # Show first 3 fields in list view
                    }

                    api_fields.append(api_field)

                    # Track display_field_key: priority is name > title > first text field
                    if api_field_type in ("text", "textbox"):
                        if first_text_field_key is None:
                            first_text_field_key = field_key
                        if field_key == "name" and display_field_key is None:
                            display_field_key = field_key
                        elif field_key == "title" and display_field_key != "name":
                            display_field_key = field_key

                # If no name/title field found, use first text field
                if display_field_key is None:
                    display_field_key = first_text_field_key

                # Create custom asset type
                result = await self.client.create_custom_asset_type(
                    name=display_name,
                    fields=api_fields,
                    display_field_key=display_field_key,
                )

                bifrost_id = result.get("id")
                if bifrost_id:
                    self._custom_asset_type_cache[type_slug] = bifrost_id
                    self.state.id_mapper.add("custom_asset_type", type_id, bifrost_id)
                    self.state.mark_completed(Phase.CUSTOM_ASSET_TYPES, type_id)
                    self.reporter.update_progress(succeeded=1)
                    created_count += 1
                    logger.info(
                        f"Created custom asset type '{display_name}' -> {bifrost_id}"
                    )
                else:
                    raise APIError(
                        500,
                        f"API response missing 'id' for custom asset type '{display_name}'",
                    )

            except APIError as e:
                error_msg = (
                    f"Failed to create custom asset type '{display_name}': {e.message}"
                )
                self.reporter.error(error_msg)
                self.reporter.update_progress(failed=1)
                self.state.mark_failed(Phase.CUSTOM_ASSET_TYPES, type_id, error_msg)
                logger.error(error_msg)

        self.reporter.complete_phase()
        return created_count

    async def import_custom_assets(
        self, assets_by_type: dict[str, list[dict[str, Any]]]
    ) -> int:
        """Import custom assets from IT Glue export.

        Requires organizations and custom asset types to be imported first.

        Args:
            assets_by_type: Dictionary mapping type slug to list of assets:
                {
                    "ssl-certificates": [
                        {
                            "id": "123",
                            "organization_id": "456",
                            "fields": {"Domain": "example.com", ...}
                        },
                        ...
                    ]
                }

        Returns:
            Count of created custom assets.
        """
        # Count total assets
        total_assets = sum(len(assets) for assets in assets_by_type.values())

        self.reporter.start_phase(Phase.CUSTOM_ASSETS, total_assets)
        self.state.current_phase = Phase.CUSTOM_ASSETS

        created_count = 0

        # Ensure custom asset type cache is populated
        if not self._custom_asset_type_cache:
            try:
                existing_types = await self.client.list_custom_asset_types(
                    include_inactive=True
                )
                # Map by both name and try to match slugs
                for t in existing_types:
                    self._custom_asset_type_cache[t["name"].lower()] = t["id"]
            except APIError as e:
                self.reporter.error(
                    f"Failed to fetch custom asset types: {e.message}"
                )

        for type_slug, assets in assets_by_type.items():
            # Get type UUID from cache or lookup by display name
            type_uuid = self._custom_asset_type_cache.get(type_slug)
            if not type_uuid:
                # Try display name
                display_name = slugify_to_display_name(type_slug)
                type_uuid = self._custom_asset_type_cache.get(display_name.lower())

            if not type_uuid:
                self.reporter.warning(
                    f"Custom asset type '{type_slug}' not found, skipping {len(assets)} assets"
                )
                for _asset in assets:
                    self.reporter.update_progress(skipped=1)
                continue

            for asset in assets:
                itglue_id = str(asset.get("id", ""))
                org_id = str(asset.get("organization_id", ""))

                # Generate display name from fields for logging/progress
                fields = asset.get("fields", {})
                display_name = None
                for name_field in ["name", "Name", "title", "Title", "domain", "Domain"]:
                    if fields.get(name_field):
                        display_name = fields[name_field]
                        break
                if not display_name:
                    # Use first non-empty field value
                    for value in fields.values():
                        if value:
                            display_name = str(value)[:50]
                            break
                if not display_name:
                    display_name = f"Asset {itglue_id}"

                if not itglue_id:
                    self.reporter.warning("Custom asset missing ID, skipping")
                    self.reporter.update_progress(skipped=1)
                    continue

                # Check if already completed
                if self.state.is_completed(Phase.CUSTOM_ASSETS, itglue_id):
                    self.reporter.update_progress(skipped=1)
                    continue

                self.reporter.set_current_item(f"Asset: {display_name}")

                try:
                    # Get organization UUID
                    org_uuid = self._get_org_uuid(org_id)
                    if not org_uuid:
                        self.reporter.warning(
                            f"Custom asset '{display_name}' has unknown org ID {org_id}, skipping"
                        )
                        self.reporter.update_progress(skipped=1)
                        self.state.add_warning(
                            f"Skipped custom asset '{display_name}': unknown organization"
                        )
                        continue

                    # Convert field names to keys for API
                    # All values go into the values dict (no separate name field)
                    values = {}
                    for field_name, field_value in fields.items():
                        if field_value is not None:
                            field_key = (
                                field_name.lower()
                                .replace(" ", "_")
                                .replace("-", "_")
                                .replace(".", "_")
                            )
                            values[field_key] = field_value

                    # Map archived to is_enabled
                    archived = asset.get("archived")
                    is_enabled = map_archived_to_is_enabled(archived)

                    # Create custom asset via API (no name field, all in values)
                    metadata = {"itglue_id": itglue_id}

                    result = await self.client.create_custom_asset(
                        org_id=org_uuid,
                        type_id=type_uuid,
                        values=values,
                        metadata=metadata,
                        is_enabled=is_enabled,
                    )

                    bifrost_id = result.get("id")
                    if bifrost_id:
                        self.state.id_mapper.add("custom_asset", itglue_id, bifrost_id)
                        self.state.mark_completed(Phase.CUSTOM_ASSETS, itglue_id)
                        disabled_count = 1 if not is_enabled else 0
                        self.reporter.update_progress(succeeded=1, disabled=disabled_count)
                        created_count += 1
                        logger.debug(
                            f"Created custom asset '{display_name}' -> {bifrost_id}"
                        )
                    else:
                        raise APIError(
                            500,
                            f"API response missing 'id' for custom asset '{display_name}'",
                        )

                except APIError as e:
                    error_msg = (
                        f"Failed to import custom asset '{display_name}': {e.message}"
                    )
                    self.reporter.error(error_msg)
                    self.reporter.update_progress(failed=1)
                    self.state.mark_failed(Phase.CUSTOM_ASSETS, itglue_id, error_msg)
                    logger.error(error_msg)

        self.reporter.complete_phase()
        return created_count

    async def import_documents(
        self, docs: list[dict[str, Any]], export_path: Path
    ) -> int:
        """Import documents from IT Glue export.

        Requires organizations to be imported first. Loads HTML content from
        the documents/ folder in the export directory.

        Args:
            docs: List of document dictionaries from CSV parser.
            export_path: Path to the IT Glue export directory.

        Returns:
            Count of created documents.
        """
        self.reporter.start_phase(Phase.DOCUMENTS, len(docs))
        self.state.current_phase = Phase.DOCUMENTS

        created_count = 0
        documents_path = export_path / "documents"

        # Build folder map to find HTML files and determine folder paths
        folder_map = _build_document_folder_map(documents_path)

        for doc in docs:
            itglue_id = str(doc.get("id", ""))
            doc_name = doc.get("name", "Untitled Document")
            org_id = str(doc.get("organization_id", ""))

            if not itglue_id:
                self.reporter.warning(f"Document '{doc_name}' missing ID, skipping")
                self.reporter.update_progress(skipped=1)
                continue

            # Check if already completed
            if self.state.is_completed(Phase.DOCUMENTS, itglue_id):
                self.reporter.update_progress(skipped=1)
                continue

            self.reporter.set_current_item(f"Document: {doc_name}")

            try:
                # Get organization UUID
                org_uuid = self._get_org_uuid(org_id)
                if not org_uuid:
                    self.reporter.warning(
                        f"Document '{doc_name}' has unknown org ID {org_id}, skipping"
                    )
                    self.reporter.update_progress(skipped=1)
                    self.state.add_warning(
                        f"Skipped document '{doc_name}': unknown organization"
                    )
                    continue

                # Get folder path and HTML file from folder map
                content = ""
                path = "/"

                if itglue_id in folder_map:
                    path, html_file = folder_map[itglue_id]
                    if html_file and html_file.exists():
                        try:
                            content = html_file.read_text(encoding="utf-8")
                        except UnicodeDecodeError:
                            try:
                                content = html_file.read_text(encoding="latin-1")
                            except Exception as e:
                                logger.warning(
                                    f"Failed to read document file {html_file}: {e}"
                                )
                else:
                    logger.debug(
                        f"Document {itglue_id} not found in folder map, using root path"
                    )

                # Map archived to is_enabled
                archived = doc.get("archived")
                is_enabled = map_archived_to_is_enabled(archived)

                # Create document via API
                metadata = {"itglue_id": itglue_id}

                result = await self.client.create_document(
                    org_id=org_uuid,
                    path=path,
                    name=doc_name,
                    content=content,
                    metadata=metadata,
                    is_enabled=is_enabled,
                )

                bifrost_id = result.get("id")
                if bifrost_id:
                    self.state.id_mapper.add("document", itglue_id, bifrost_id)
                    self.state.mark_completed(Phase.DOCUMENTS, itglue_id)
                    disabled_count = 1 if not is_enabled else 0
                    self.reporter.update_progress(succeeded=1, disabled=disabled_count)
                    created_count += 1
                    logger.debug(f"Created document '{doc_name}' -> {bifrost_id}")
                else:
                    raise APIError(
                        500, f"API response missing 'id' for document '{doc_name}'"
                    )

            except APIError as e:
                error_msg = f"Failed to import document '{doc_name}': {e.message}"
                self.reporter.error(error_msg)
                self.reporter.update_progress(failed=1)
                self.state.mark_failed(Phase.DOCUMENTS, itglue_id, error_msg)
                logger.error(error_msg)

        self.reporter.complete_phase()
        return created_count

    async def import_passwords(self, passwords: list[dict[str, Any]]) -> int:
        """Import passwords from IT Glue export.

        Requires organizations to be imported first.

        Args:
            passwords: List of password dictionaries from CSV parser.

        Returns:
            Count of created passwords.
        """
        self.reporter.start_phase(Phase.PASSWORDS, len(passwords))
        self.state.current_phase = Phase.PASSWORDS

        created_count = 0

        for pwd in passwords:
            itglue_id = str(pwd.get("id", ""))
            pwd_name = pwd.get("name", "Untitled Password")
            org_id = str(pwd.get("organization_id", ""))
            password_value = pwd.get("password", "")

            if not itglue_id:
                self.reporter.warning(f"Password '{pwd_name}' missing ID, skipping")
                self.reporter.update_progress(skipped=1)
                continue

            # Check if already completed
            if self.state.is_completed(Phase.PASSWORDS, itglue_id):
                self.reporter.update_progress(skipped=1)
                continue

            self.reporter.set_current_item(f"Password: {pwd_name}")

            # Skip passwords with empty password field
            if not password_value:
                self.reporter.warning(
                    f"Password '{pwd_name}' has empty password value, skipping"
                )
                self.reporter.update_progress(skipped=1)
                self.state.add_warning(
                    f"Skipped password '{pwd_name}': empty password value"
                )
                continue

            try:
                # Get organization UUID
                org_uuid = self._get_org_uuid(org_id)
                if not org_uuid:
                    self.reporter.warning(
                        f"Password '{pwd_name}' has unknown org ID {org_id}, skipping"
                    )
                    self.reporter.update_progress(skipped=1)
                    self.state.add_warning(
                        f"Skipped password '{pwd_name}': unknown organization"
                    )
                    continue

                # Map otp_secret to totp_secret
                totp_secret = pwd.get("otp_secret")

                # Map archived to is_enabled
                archived = pwd.get("archived")
                is_enabled = map_archived_to_is_enabled(archived)

                # Create password via API
                metadata = {"itglue_id": itglue_id}
                if pwd.get("resource_type"):
                    metadata["resource_type"] = pwd["resource_type"]
                if pwd.get("resource_id"):
                    metadata["resource_id"] = pwd["resource_id"]

                result = await self.client.create_password(
                    org_id=org_uuid,
                    name=pwd_name,
                    password=password_value,
                    username=pwd.get("username"),
                    totp_secret=totp_secret,
                    url=pwd.get("url"),
                    notes=pwd.get("notes"),
                    metadata=metadata,
                    is_enabled=is_enabled,
                )

                bifrost_id = result.get("id")
                if bifrost_id:
                    self.state.id_mapper.add("password", itglue_id, bifrost_id)
                    self.state.mark_completed(Phase.PASSWORDS, itglue_id)
                    disabled_count = 1 if not is_enabled else 0
                    self.reporter.update_progress(succeeded=1, disabled=disabled_count)
                    created_count += 1
                    logger.debug(f"Created password '{pwd_name}' -> {bifrost_id}")
                else:
                    raise APIError(
                        500, f"API response missing 'id' for password '{pwd_name}'"
                    )

            except APIError as e:
                error_msg = f"Failed to import password '{pwd_name}': {e.message}"
                self.reporter.error(error_msg)
                self.reporter.update_progress(failed=1)
                self.state.mark_failed(Phase.PASSWORDS, itglue_id, error_msg)
                logger.error(error_msg)

        self.reporter.complete_phase()
        return created_count
