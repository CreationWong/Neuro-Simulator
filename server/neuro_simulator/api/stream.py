# neuro_simulator/api/stream.py
"""API endpoints for controlling the live stream lifecycle."""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends

from ..core.agent_factory import create_agent
from ..utils.process import process_manager
from .agent import get_api_token # Re-using the auth dependency from agent API

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))
router = APIRouter(prefix="/api/stream", tags=["Stream Control"])

@router.post("/start", dependencies=[Depends(get_api_token)])
async def start_stream():
    """Starts the live stream processes."""
    try:
        agent = await create_agent()
        await agent.reset_memory()
    except Exception as e:
        logger.error(f"Could not reset agent memory on stream start: {e}", exc_info=True)

    if not process_manager.is_running:
        process_manager.start_live_processes()
        return {"status": "success", "message": "Stream started"}
    else:
        return {"status": "info", "message": "Stream is already running"}

@router.post("/stop", dependencies=[Depends(get_api_token)])
async def stop_stream():
    """Stops the live stream processes."""
    if process_manager.is_running:
        await process_manager.stop_live_processes()
        return {"status": "success", "message": "Stream stopped"}
    else:
        return {"status": "info", "message": "Stream is not running"}

@router.post("/restart", dependencies=[Depends(get_api_token)])
async def restart_stream():
    """Restarts the live stream processes."""
    await process_manager.stop_live_processes()
    await asyncio.sleep(1) # Give time for tasks to cancel
    process_manager.start_live_processes()
    return {"status": "success", "message": "Stream restarted"}

@router.get("/status", dependencies=[Depends(get_api_token)])
async def get_stream_status():
    """Gets the current status of the stream."""
    return {
        "is_running": process_manager.is_running,
        "backend_status": "running" if process_manager.is_running else "stopped"
    }