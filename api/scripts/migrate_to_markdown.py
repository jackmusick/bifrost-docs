#!/usr/bin/env python3
"""
Migration script: Convert all document content from HTML to Markdown.

This script:
1. Queries all documents
2. Converts HTML content to Markdown using markdownify
3. Updates documents in the database

Usage:
    python scripts/migrate_to_markdown.py [--dry-run]
"""

import argparse
import asyncio
import logging

from markdownify import markdownify as md
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session_factory
from src.models.orm.document import Document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def html_to_markdown(html_content: str) -> str:
    """
    Convert HTML content to clean Markdown.

    Args:
        html_content: HTML content to convert

    Returns:
        Markdown content
    """
    # Convert HTML to markdown with clean options
    markdown = md(
        html_content,
        heading_style="atx",  # Use # for headings
        bullets="-",  # Use - for bullets
        code_language="",  # Don't add language to code blocks
        strip=["script", "style"],  # Strip scripts and styles
        escape_asterisks=False,  # Don't escape asterisks
        escape_underscores=False,  # Don't escape underscores
    )

    # Clean up common IT Glue artifacts
    markdown = markdown.replace("&nbsp;", " ")
    markdown = markdown.replace("&amp;", "&")
    markdown = markdown.replace("&lt;", "<")
    markdown = markdown.replace("&gt;", ">")
    markdown = markdown.replace("&quot;", '"')

    # Remove excessive blank lines
    while "\n\n\n" in markdown:
        markdown = markdown.replace("\n\n\n", "\n\n")

    return markdown.strip()


async def migrate_documents(
    session: AsyncSession,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Migrate all documents from HTML to Markdown.

    Args:
        session: Database session
        dry_run: If True, don't commit changes

    Returns:
        Tuple of (total_documents, migrated_documents)
    """
    # Get all documents
    stmt = select(Document).order_by(Document.created_at)
    result = await session.execute(stmt)
    documents = result.scalars().all()

    total = len(documents)
    migrated = 0

    logger.info(f"Found {total} documents to process")

    # Convert each document
    for i, doc in enumerate(documents, 1):
        try:
            logger.info(f"[{i}/{total}] Processing: {doc.name} ({doc.path})")

            # Skip if already looks like markdown (no HTML tags)
            if not ("<" in doc.content and ">" in doc.content):
                logger.info(f"  → Skipping (already markdown-like)")
                continue

            # Convert to markdown
            markdown_content = html_to_markdown(doc.content)

            # Log sample
            if len(doc.content) > 200:
                logger.debug(f"  HTML: {doc.content[:200]}...")
                logger.debug(f"  Markdown: {markdown_content[:200]}...")

            # Update document
            if not dry_run:
                doc.content = markdown_content
                migrated += 1
                logger.info(f"  ✓ Converted ({len(doc.content)} → {len(markdown_content)} chars)")
            else:
                logger.info(f"  [DRY RUN] Would convert ({len(doc.content)} → {len(markdown_content)} chars)")

        except Exception as e:
            logger.error(f"  ✗ Failed to convert {doc.name}: {e}")
            continue

    # Commit changes
    if not dry_run and migrated > 0:
        await session.commit()
        logger.info(f"✓ Committed {migrated} document updates")
    else:
        logger.info(f"[DRY RUN] Would commit {migrated} document updates")

    return total, migrated


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert all document content from HTML to Markdown"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying the database",
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Document HTML → Markdown Migration")
    logger.info("=" * 70)
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    logger.info("=" * 70)

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            total, migrated = await migrate_documents(
                session,
                dry_run=args.dry_run,
            )

            logger.info("=" * 70)
            logger.info(f"Migration complete!")
            logger.info(f"  Total documents: {total}")
            logger.info(f"  Migrated: {migrated}")
            logger.info(f"  Skipped: {total - migrated}")
            logger.info("=" * 70)

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    asyncio.run(main())
