# neuro_simulator/api/system.py
"""API endpoints for system, config, and utility functions."""

import time

from fastapi import APIRouter, HTTPException, status, Request

from ..core.config import config_manager
from ..utils.process import process_manager


router = APIRouter(tags=["System & Utilities"])


# --- Auth Dependency ---


async def get_api_token(request: Request):
    """FastAPI dependency to check for the API token in headers."""
    assert config_manager.settings is not None
    password = config_manager.settings.server.panel_password
    if not password:
        return True
    header_token = request.headers.get("X-API-Token")
    if header_token and header_token == password:
        return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API token",
        headers={"WWW-Authenticate": "Bearer"},
    )


# --- System Endpoints ---


@router.get("/api/system/health")
async def health_check():
    """Provides a simple health check of the server."""
    return {
        "status": "healthy",
        "backend_running": True,
        "process_manager_running": process_manager.is_running,
        "timestamp": time.time(),
    }
