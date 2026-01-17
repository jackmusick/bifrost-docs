"""
Bifrost Docs API - FastAPI Application

Main entry point for the FastAPI application.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, NoResultFound, OperationalError

from src.config import get_settings
from src.core.database import close_db, init_db
from src.models.contracts.common import ErrorResponse
from src.routers import (
    admin_router,
    ai_settings_router,
    api_keys_router,
    attachments_router,
    audit_org_router,
    audit_router,
    auth_router,
    configuration_statuses_router,
    configuration_types_router,
    configurations_router,
    custom_asset_types_router,
    custom_assets_router,
    documents_router,
    exports_router,
    global_view_router,
    health_router,
    locations_router,
    me_router,
    mfa_router,
    oauth_config_router,
    oauth_sso_router,
    organizations_router,
    passkeys_router,
    passwords_router,
    preferences_router,
    relationships_router,
    search_router,
    websocket_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    from src.core.pubsub import get_connection_manager

    # Startup
    logger.info("Starting Bifrost Docs API...")
    settings = get_settings()

    # Initialize database
    logger.info("Initializing database connection...")
    await init_db()
    logger.info("Database connection established")

    # Initialize WebSocket pub/sub
    logger.info("Initializing WebSocket pub/sub...")
    manager = get_connection_manager()
    await manager.start_pubsub()

    # Create default admin user if configured
    if settings.default_user_email and settings.default_user_password:
        await create_default_user()

    logger.info(f"Bifrost Docs API started in {settings.environment} mode")

    yield

    # Shutdown
    logger.info("Shutting down Bifrost Docs API...")
    await manager.stop_pubsub()
    await close_db()
    logger.info("Bifrost Docs API shutdown complete")


async def create_default_user() -> None:
    """
    Create default admin user if it doesn't exist.

    Only runs if BIFROST_DOCS_DEFAULT_USER_EMAIL and BIFROST_DOCS_DEFAULT_USER_PASSWORD
    environment variables are set.
    """
    from src.core.database import get_db_context
    from src.core.security import get_password_hash
    from src.models.orm.organization import Organization
    from src.repositories.organization import OrganizationRepository
    from src.repositories.user import UserRepository

    settings = get_settings()

    if not settings.default_user_email or not settings.default_user_password:
        return

    async with get_db_context() as db:
        user_repo = UserRepository(db)
        org_repo = OrganizationRepository(db)

        # Check if default user exists
        existing = await user_repo.get_by_email(settings.default_user_email)
        if existing:
            logger.info(
                f"Default user already exists: {settings.default_user_email}")
            return

        # Create default admin user with owner role
        from src.models.enums import UserRole

        hashed_password = get_password_hash(settings.default_user_password)
        user = await user_repo.create_user(
            email=settings.default_user_email,
            hashed_password=hashed_password,
            name="Admin",
            role=UserRole.OWNER,
        )

        # Create default organization
        org = Organization(name="Default Organization")
        org = await org_repo.create(org)

        logger.info(
            f"Created default admin user: {user.email} (id: {user.id})")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="Bifrost Docs API",
        description="MSP documentation platform API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ==========================================================================
    # CORS Middleware
    # ==========================================================================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ==========================================================================
    # Global Exception Handlers
    # ==========================================================================

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        """Pydantic model validation errors -> 422."""
        errors = exc.errors()
        field_errors = {".".join(str(loc)
                                 for loc in e["loc"]): e["msg"] for e in errors}
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="validation_error",
                message="Validation failed",
                details={"fields": field_errors},
            ).model_dump(),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        """Database constraint violations -> 409."""
        detail = str(exc.orig) if exc.orig else str(exc)

        if "unique" in detail.lower() or "duplicate" in detail.lower():
            message = "Resource already exists"
        elif "foreign key" in detail.lower():
            message = "Referenced resource not found"
        else:
            message = "Database constraint violation"

        logger.warning(f"IntegrityError: {detail}")
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                error="conflict",
                message=message,
            ).model_dump(),
        )

    @app.exception_handler(NoResultFound)
    async def no_result_handler(request: Request, exc: NoResultFound) -> JSONResponse:
        """Query returned no results -> 404."""
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="not_found",
                message="Resource not found",
            ).model_dump(),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """ValueError from validation -> 422."""
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="validation_error",
                message=str(exc),
            ).model_dump(),
        )

    @app.exception_handler(OperationalError)
    async def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
        """Database connection issues -> 503."""
        logger.error(f"Database operational error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error="service_unavailable",
                message="Service temporarily unavailable",
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unhandled exceptions -> 500."""
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error",
                message="An unexpected error occurred",
            ).model_dump(),
        )

    # ==========================================================================
    # Register Routers
    # ==========================================================================
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(mfa_router)
    app.include_router(passkeys_router)
    app.include_router(api_keys_router)
    app.include_router(oauth_config_router)
    app.include_router(oauth_sso_router)
    app.include_router(admin_router)
    app.include_router(ai_settings_router)
    app.include_router(organizations_router)
    app.include_router(global_view_router)
    app.include_router(locations_router)
    app.include_router(me_router)
    app.include_router(documents_router)
    app.include_router(exports_router)
    app.include_router(passwords_router)
    app.include_router(preferences_router)
    app.include_router(configuration_types_router)
    app.include_router(configuration_statuses_router)
    app.include_router(configurations_router)
    app.include_router(custom_asset_types_router)
    app.include_router(custom_assets_router)
    app.include_router(attachments_router)
    app.include_router(relationships_router)
    app.include_router(search_router)
    app.include_router(audit_router)
    app.include_router(audit_org_router)
    app.include_router(websocket_router)

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "Bifrost Docs API",
            "version": "1.0.0",
            "docs": "/docs",
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )
