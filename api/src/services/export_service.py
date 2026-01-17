"""
Export Service

Handles the background processing of data exports:
- Generates CSV files for each entity type
- Bundles everything into a ZIP file
- Uploads to S3
- Streams progress updates via WebSocket
"""

import csv
import io
import logging
import zipfile
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_context
from src.core.pubsub import MessageType, WebSocketMessage, get_connection_manager
from src.models.orm.configuration import Configuration
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.document import Document
from src.models.orm.export import ExportStatus
from src.models.orm.location import Location
from src.models.orm.organization import Organization
from src.models.orm.password import Password
from src.repositories.export import ExportRepository
from src.services.file_storage import get_file_storage_service

logger = logging.getLogger(__name__)


# =============================================================================
# WebSocket Progress Publishing
# =============================================================================


async def publish_export_progress(
    export_id: UUID,
    stage: str,
    current: int,
    total: int,
    entity_type: str | None = None,
) -> None:
    """
    Publish export progress update via WebSocket.

    Args:
        export_id: Export job identifier
        stage: Current stage (e.g., "passwords", "documents")
        current: Current item number
        total: Total items to process
        entity_type: Type of entity being processed
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.PROGRESS,
        channel=f"export:{export_id}",
        data={
            "stage": stage,
            "current": current,
            "total": total,
            "entity_type": entity_type,
            "percent": round((current / total * 100) if total > 0 else 0, 1),
        },
    )
    await manager.broadcast(f"export:{export_id}", message)


async def publish_export_completed(
    export_id: UUID,
    file_size_bytes: int,
) -> None:
    """
    Publish export completion notification via WebSocket.

    Args:
        export_id: Export job identifier
        file_size_bytes: Size of the generated ZIP file
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.COMPLETED,
        channel=f"export:{export_id}",
        data={
            "stage": "complete",
            "file_size_bytes": file_size_bytes,
        },
    )
    await manager.broadcast(f"export:{export_id}", message)


async def publish_export_failed(
    export_id: UUID,
    error: str,
) -> None:
    """
    Publish export failure notification via WebSocket.

    Args:
        export_id: Export job identifier
        error: Error message
    """
    manager = get_connection_manager()
    message = WebSocketMessage(
        type=MessageType.FAILED,
        channel=f"export:{export_id}",
        data={
            "stage": "failed",
            "error": error,
        },
    )
    await manager.broadcast(f"export:{export_id}", message)


# =============================================================================
# CSV Export Functions
# =============================================================================


async def get_all_organization_ids(
    db: AsyncSession,
) -> list[UUID]:
    """
    Get all organization IDs.

    In the new model, all users can see all organizations.

    Args:
        db: Database session

    Returns:
        List of organization UUIDs
    """
    result = await db.execute(select(Organization.id))
    return [row[0] for row in result.fetchall()]


async def export_passwords_to_csv(
    db: AsyncSession,
    organization_ids: list[UUID],
    export_id: UUID,
) -> str:
    """
    Export passwords to CSV format.

    Note: Passwords are exported encrypted - decryption would require
    additional security considerations.

    Args:
        db: Database session
        organization_ids: List of organization UUIDs to export
        export_id: Export job ID for progress updates

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "organization_id",
        "name",
        "username",
        "url",
        "notes",
        "created_at",
        "updated_at",
    ])

    for i, org_id in enumerate(organization_ids):
        result = await db.execute(
            select(Password)
            .where(Password.organization_id == org_id)
            .order_by(Password.name)
        )
        passwords = result.scalars().all()

        for password in passwords:
            writer.writerow([
                str(password.id),
                str(password.organization_id),
                password.name,
                password.username or "",
                password.url or "",
                password.notes or "",
                password.created_at.isoformat() if password.created_at else "",
                password.updated_at.isoformat() if password.updated_at else "",
            ])

        await publish_export_progress(
            export_id, "passwords", i + 1, len(organization_ids), "password"
        )

    return output.getvalue()


async def export_configurations_to_csv(
    db: AsyncSession,
    organization_ids: list[UUID],
    export_id: UUID,
) -> str:
    """
    Export configurations to CSV format.

    Args:
        db: Database session
        organization_ids: List of organization UUIDs to export
        export_id: Export job ID for progress updates

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "organization_id",
        "name",
        "configuration_type_id",
        "configuration_status_id",
        "serial_number",
        "asset_tag",
        "manufacturer",
        "model",
        "ip_address",
        "notes",
        "created_at",
        "updated_at",
    ])

    for i, org_id in enumerate(organization_ids):
        result = await db.execute(
            select(Configuration)
            .where(Configuration.organization_id == org_id)
            .order_by(Configuration.name)
        )
        configurations = result.scalars().all()

        for config in configurations:
            writer.writerow([
                str(config.id),
                str(config.organization_id),
                config.name,
                str(config.configuration_type_id) if config.configuration_type_id else "",
                str(config.configuration_status_id) if config.configuration_status_id else "",
                config.serial_number or "",
                config.asset_tag or "",
                config.manufacturer or "",
                config.model or "",
                config.ip_address or "",
                config.notes or "",
                config.created_at.isoformat() if config.created_at else "",
                config.updated_at.isoformat() if config.updated_at else "",
            ])

        await publish_export_progress(
            export_id, "configurations", i + 1, len(organization_ids), "configuration"
        )

    return output.getvalue()


async def export_locations_to_csv(
    db: AsyncSession,
    organization_ids: list[UUID],
    export_id: UUID,
) -> str:
    """
    Export locations to CSV format.

    Args:
        db: Database session
        organization_ids: List of organization UUIDs to export
        export_id: Export job ID for progress updates

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "organization_id",
        "name",
        "address_line_1",
        "address_line_2",
        "city",
        "region",
        "postal_code",
        "country",
        "notes",
        "created_at",
        "updated_at",
    ])

    for i, org_id in enumerate(organization_ids):
        result = await db.execute(
            select(Location)
            .where(Location.organization_id == org_id)
            .order_by(Location.name)
        )
        locations = result.scalars().all()

        for location in locations:
            writer.writerow([
                str(location.id),
                str(location.organization_id),
                location.name,
                getattr(location, "address_line_1", "") or "",
                getattr(location, "address_line_2", "") or "",
                getattr(location, "city", "") or "",
                getattr(location, "region", "") or "",
                getattr(location, "postal_code", "") or "",
                getattr(location, "country", "") or "",
                location.notes or "",
                location.created_at.isoformat() if location.created_at else "",
                location.updated_at.isoformat() if location.updated_at else "",
            ])

        await publish_export_progress(
            export_id, "locations", i + 1, len(organization_ids), "location"
        )

    return output.getvalue()


async def export_documents_to_csv(
    db: AsyncSession,
    organization_ids: list[UUID],
    export_id: UUID,
) -> str:
    """
    Export documents to CSV format.

    Args:
        db: Database session
        organization_ids: List of organization UUIDs to export
        export_id: Export job ID for progress updates

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "organization_id",
        "name",
        "path",
        "content",
        "created_at",
        "updated_at",
    ])

    for i, org_id in enumerate(organization_ids):
        result = await db.execute(
            select(Document)
            .where(Document.organization_id == org_id)
            .order_by(Document.path, Document.name)
        )
        documents = result.scalars().all()

        for doc in documents:
            writer.writerow([
                str(doc.id),
                str(doc.organization_id),
                doc.name,
                doc.path or "",
                doc.content or "",
                doc.created_at.isoformat() if doc.created_at else "",
                doc.updated_at.isoformat() if doc.updated_at else "",
            ])

        await publish_export_progress(
            export_id, "documents", i + 1, len(organization_ids), "document"
        )

    return output.getvalue()


async def export_custom_assets_to_csv(
    db: AsyncSession,
    organization_ids: list[UUID],
    export_id: UUID,
) -> str:
    """
    Export custom assets to CSV format.

    The 'fields' column contains JSON data with custom field values.

    Args:
        db: Database session
        organization_ids: List of organization UUIDs to export
        export_id: Export job ID for progress updates

    Returns:
        CSV content as string
    """
    import json

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "organization_id",
        "custom_asset_type_id",
        "values_json",
        "is_enabled",
        "created_at",
        "updated_at",
    ])

    for i, org_id in enumerate(organization_ids):
        result = await db.execute(
            select(CustomAsset)
            .where(CustomAsset.organization_id == org_id)
            .order_by(CustomAsset.created_at.desc())
        )
        assets = result.scalars().all()

        for asset in assets:
            values_json = json.dumps(asset.values) if asset.values else "{}"
            writer.writerow([
                str(asset.id),
                str(asset.organization_id),
                str(asset.custom_asset_type_id),
                values_json,
                asset.is_enabled,
                asset.created_at.isoformat() if asset.created_at else "",
                asset.updated_at.isoformat() if asset.updated_at else "",
            ])

        await publish_export_progress(
            export_id, "custom_assets", i + 1, len(organization_ids), "custom_asset"
        )

    return output.getvalue()


# =============================================================================
# Main Export Processing
# =============================================================================


async def process_export(export_id: UUID) -> None:
    """
    Background task to generate export ZIP file.

    This function:
    1. Updates export status to PROCESSING
    2. Generates CSV files for each entity type
    3. Creates a ZIP file containing all CSVs
    4. Uploads ZIP to S3
    5. Updates export status to COMPLETED
    6. Publishes progress via WebSocket throughout

    Args:
        export_id: Export job identifier
    """
    async with get_db_context() as db:
        repo = ExportRepository(db)
        export = await repo.get_by_id(export_id)

        if not export:
            logger.error(f"Export {export_id} not found")
            return

        try:
            # Update status to processing
            await repo.update_status(export, ExportStatus.PROCESSING)
            await db.commit()

            # Determine which organization IDs to export
            if export.organization_ids:
                org_ids = [UUID(org_id) for org_id in export.organization_ids]
            else:
                # Export all organizations (all users can see all orgs in new model)
                org_ids = await get_all_organization_ids(db)

            if not org_ids:
                raise ValueError("No organizations to export")

            logger.info(
                f"Processing export {export_id} for {len(org_ids)} organizations"
            )

            # Create in-memory ZIP file
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                # Export passwords
                await publish_export_progress(export_id, "starting", 0, 5, "passwords")
                passwords_csv = await export_passwords_to_csv(db, org_ids, export_id)
                zf.writestr("passwords.csv", passwords_csv)

                # Export configurations
                await publish_export_progress(export_id, "starting", 1, 5, "configurations")
                configs_csv = await export_configurations_to_csv(db, org_ids, export_id)
                zf.writestr("configurations.csv", configs_csv)

                # Export locations
                await publish_export_progress(export_id, "starting", 2, 5, "locations")
                locations_csv = await export_locations_to_csv(db, org_ids, export_id)
                zf.writestr("locations.csv", locations_csv)

                # Export documents
                await publish_export_progress(export_id, "starting", 3, 5, "documents")
                documents_csv = await export_documents_to_csv(db, org_ids, export_id)
                zf.writestr("documents.csv", documents_csv)

                # Export custom assets
                await publish_export_progress(export_id, "starting", 4, 5, "custom_assets")
                custom_assets_csv = await export_custom_assets_to_csv(db, org_ids, export_id)
                zf.writestr("custom_assets.csv", custom_assets_csv)

                # Add metadata file
                import json

                metadata = {
                    "export_id": str(export_id),
                    "created_at": datetime.now(UTC).isoformat(),
                    "organization_ids": [str(org_id) for org_id in org_ids],
                    "files": [
                        "passwords.csv",
                        "configurations.csv",
                        "locations.csv",
                        "documents.csv",
                        "custom_assets.csv",
                    ],
                }
                zf.writestr("metadata.json", json.dumps(metadata, indent=2))

            # Upload to S3
            await publish_export_progress(export_id, "uploading", 5, 5, None)
            zip_buffer.seek(0)
            zip_content = zip_buffer.getvalue()
            file_size_bytes = len(zip_content)

            s3_key = f"exports/{export_id}/{datetime.now(UTC).strftime('%Y-%m-%d')}-export.zip"
            file_storage = get_file_storage_service()
            success = await file_storage.upload_file(
                s3_key,
                zip_content,
                content_type="application/zip",
            )

            if not success:
                raise RuntimeError("Failed to upload export to S3")

            # Update export status to completed
            await repo.update_status(
                export,
                ExportStatus.COMPLETED,
                s3_key=s3_key,
                file_size_bytes=file_size_bytes,
            )
            await db.commit()

            # Publish completion
            await publish_export_completed(export_id, file_size_bytes)

            logger.info(
                f"Export {export_id} completed successfully: "
                f"{file_size_bytes} bytes, {len(org_ids)} organizations"
            )

        except Exception as e:
            error_message = str(e)
            logger.error(f"Export {export_id} failed: {error_message}", exc_info=True)

            # Update export status to failed
            try:
                await repo.update_status(
                    export,
                    ExportStatus.FAILED,
                    error_message=error_message[:1000],  # Truncate if too long
                )
                await db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update export status: {update_error}")

            # Publish failure
            await publish_export_failed(export_id, error_message)
