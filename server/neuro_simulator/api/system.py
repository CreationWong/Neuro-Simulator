# neuro_simulator/api/system.py
"""API endpoints for system, config, and utility functions."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import time

from ..core.config import config_manager, AppSettings
from ..services.audio import synthesize_audio_segment
from .agent import get_api_token # Re-using the auth dependency

router = APIRouter(tags=["System & Utilities"])

# --- TTS Endpoint ---

class SpeechRequest(BaseModel):
    text: str
    voice_name: str | None = None
    pitch: float | None = None

@router.post("/api/tts/synthesize", dependencies=[Depends(get_api_token)])
async def synthesize_speech_endpoint(request: SpeechRequest):
    """Synthesizes text to speech using the configured TTS service."""
    try:
        audio_base64, _ = await synthesize_audio_segment(
            text=request.text, voice_name=request.voice_name, pitch=request.pitch
        )
        return {"audio_base64": audio_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Config Management Endpoints ---

# This helper can be moved to a more central location if needed
def filter_config_for_frontend(settings: AppSettings):
    """Filters the settings to return only the fields safe for the frontend."""
    # Using .model_dump() with include is a more robust Pydantic approach
    return settings.model_dump(include={
        'stream_metadata': {'stream_title', 'stream_category', 'stream_tags'},
        'agent': {'agent_provider', 'agent_model'},
        'neuro_behavior': {'input_chat_sample_size', 'post_speech_cooldown_sec', 'initial_greeting'},
        'audience_simulation': {'llm_provider', 'gemini_model', 'openai_model', 'llm_temperature', 'chat_generation_interval_sec', 'chats_per_batch', 'max_output_tokens', 'username_blocklist', 'username_pool'},
        'performance': {'neuro_input_queue_max_size', 'audience_chat_buffer_max_size', 'initial_chat_backlog_limit'}
    })

@router.get("/api/configs", dependencies=[Depends(get_api_token)])
async def get_configs():
    """Gets the current, frontend-safe configuration."""
    return filter_config_for_frontend(config_manager.settings)

@router.patch("/api/configs", dependencies=[Depends(get_api_token)])
async def update_configs(new_settings: dict):
    """Updates the configuration with new values from the frontend."""
    try:
        await config_manager.update_settings(new_settings)
        return filter_config_for_frontend(config_manager.settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

@router.post("/api/configs/reload", dependencies=[Depends(get_api_token)])
async def reload_configs():
    """Triggers a reload of the configuration from the config.yaml file."""
    try:
        # Passing an empty dict forces a reload and triggers callbacks
        await config_manager.update_settings({})
        return {"status": "success", "message": "Configuration reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload settings: {str(e)}")

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
