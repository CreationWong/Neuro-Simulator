# neuro_simulator/api/system.py
"""API endpoints for system, config, and utility functions."""

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..core.config import AppSettings, config_manager
from ..utils.process import process_manager


router = APIRouter(tags=["System & Utilities"])


# --- Utility function to filter config for frontend ---
def filter_config_for_frontend(settings):
    """Filters the full settings object to remove sensitive fields before sending to the frontend."""
    # Create a dictionary representation of the settings
    config_dict = settings.model_dump()
    
    # Remove sensitive fields
    config_dict.pop('api_keys', None)
    
    return config_dict


# --- Auth Dependency ---

async def get_api_token(request: Request):
    """FastAPI dependency to check for the API token in headers."""
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
    from ..utils.process import process_manager
    return {
        "status": "healthy",
        "backend_running": True,
        "process_manager_running": process_manager.is_running,
        "timestamp": time.time()
    }

@router.get("/")
async def root():
    """Returns basic information about the API."""
    return {
        "message": "Neuro-Sama Simulator Backend",
        "version": "2.0",
        "api_docs": "/docs",
    }


