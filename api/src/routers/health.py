"""
Health Check Router

Provides health check endpoint for monitoring and load balancers.
"""

from fastapi import APIRouter

from src.models.contracts.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with status and version
    """
    return HealthResponse(status="healthy", version="1.0.0")
