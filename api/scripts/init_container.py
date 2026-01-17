#!/usr/bin/env python3
"""
Init container script for Bifrost Docs.

Runs database migrations before API starts.

Usage:
    python -m scripts.init_container

Exit codes:
    0 - Success
    1 - Migration failure
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [init] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("init_container")


def run_migrations() -> bool:
    """
    Run alembic migrations.

    Returns:
        True if migrations succeeded, False otherwise
    """
    logger.info("Running database migrations...")

    # Get the api/ directory (parent of scripts/)
    api_dir = Path(__file__).parent.parent

    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=api_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=300,  # 5 minute timeout
        )

        # Log migration output
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    logger.info(f"alembic: {line}")

        logger.info("Database migrations completed successfully")
        return True

    except subprocess.TimeoutExpired:
        logger.error("Migration timed out after 5 minutes")
        return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed with exit code {e.returncode}")
        if e.stderr:
            for line in e.stderr.strip().split("\n"):
                logger.error(f"alembic: {line}")
        if e.stdout:
            for line in e.stdout.strip().split("\n"):
                logger.info(f"alembic: {line}")
        return False

    except FileNotFoundError:
        logger.error("alembic command not found - ensure it's installed")
        return False


def main() -> int:
    """
    Main entry point for init container.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 60)
    logger.info("Bifrost Docs Init Container Starting")
    logger.info("=" * 60)

    logger.info("")
    logger.info("Running Database Migrations")
    logger.info("-" * 40)

    if not run_migrations():
        logger.error("FAILED: Database migrations failed - aborting startup")
        return 1

    logger.info("")
    logger.info("=" * 60)
    logger.info("Init Container Completed Successfully")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
