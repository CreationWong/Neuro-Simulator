# neuro_simulator/services/stream.py
import asyncio
import logging
import os
import time

from mutagen.mp4 import MP4, MP4StreamInfoError

from ..core.config import config_manager
from ..utils.state import app_state

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

_WORKING_DIR = os.getcwd()
_WELCOME_VIDEO_PATH_BACKEND = os.path.join(_WORKING_DIR, "assets", "neuro_start.mp4")
_WELCOME_VIDEO_DURATION_SEC_DEFAULT = 10.0

@staticmethod
def _get_video_duration(video_path: str) -> float:
    """Gets the duration of an MP4 video file using mutagen."""
    if not os.path.exists(video_path):
        logger.warning(f"Video file '{video_path}' not found. Using default duration.")
        return _WELCOME_VIDEO_DURATION_SEC_DEFAULT
    try:
        video = MP4(video_path)
        duration = video.info.length
        logger.info(f"Successfully read video duration for '{video_path}': {duration:.2f}s.")
        return duration
    except MP4StreamInfoError:
        logger.warning(f"Could not parse stream info for '{video_path}'. Using default duration.")
        return _WELCOME_VIDEO_DURATION_SEC_DEFAULT
    except Exception as e:
        logger.error(f"Error getting video duration: {e}. Using default duration.")
        return _WELCOME_VIDEO_DURATION_SEC_DEFAULT

class LiveStreamManager:
    class NeuroAvatarStage:
        HIDDEN = "hidden"
        STEP1 = "step1"
        STEP2 = "step2"

    class StreamPhase:
        OFFLINE = "offline"
        INITIALIZING = "initializing"
        AVATAR_INTRO = "avatar_intro"
        LIVE = "live"
    
    event_queue: asyncio.Queue = asyncio.Queue()

    _WORKING_DIR = os.getcwd()
    _WELCOME_VIDEO_PATH_BACKEND = os.path.join(_WORKING_DIR, "assets", "neuro_start.mp4")
    _WELCOME_VIDEO_DURATION_SEC_DEFAULT = 10.0
    _WELCOME_VIDEO_DURATION_SEC = _get_video_duration(_WELCOME_VIDEO_PATH_BACKEND)
    AVATAR_INTRO_TOTAL_DURATION_SEC = 3.0

    def __init__(self):
        self._current_phase: str = self.StreamPhase.OFFLINE
        self._stream_start_global_time: float = 0.0
        self._is_neuro_speaking: bool = False
        logger.info("LiveStreamManager initialized.")

    async def broadcast_stream_metadata(self):
        """Puts the stream metadata into the event queue for broadcasting."""
        metadata_event = {
            "type": "update_stream_metadata",
            **config_manager.settings.stream_metadata.model_dump()
        }
        await self.event_queue.put(metadata_event)

    def reset_stream_state(self):
        """Resets the stream state to offline."""
        self._current_phase = self.StreamPhase.OFFLINE
        self._stream_start_global_time = 0.0
        self._is_neuro_speaking = False
        while not self.event_queue.empty():
            self.event_queue.get_nowait()
        app_state.live_phase_started_event.clear()
        logger.info("Stream state has been reset to OFFLINE.")

    async def start_new_stream_cycle(self):
        """Starts a new stream cycle, from the welcome video onwards."""
        if self._current_phase != self.StreamPhase.OFFLINE:
            return

        logger.info("Starting new stream cycle...")
        self._stream_start_global_time = time.time()
        
        from ..core.agent_factory import create_agent
        try:
            agent = await create_agent()
            await agent.reset_memory()
            logger.info("Agent memory has been reset for the new stream cycle.")
        except Exception as e:
            logger.error(f"Failed to reset agent memory: {e}", exc_info=True)
        
        self._current_phase = self.StreamPhase.INITIALIZING
        await self.event_queue.put({
            "type": "play_welcome_video",
            "progress": 0,
            "elapsed_time_sec": self.get_elapsed_time()
        })
        
        await asyncio.sleep(self._WELCOME_VIDEO_DURATION_SEC)
        
        self._current_phase = self.StreamPhase.AVATAR_INTRO
        await self.event_queue.put({"type": "start_avatar_intro", "elapsed_time_sec": self.get_elapsed_time()})
        
        await asyncio.sleep(self.AVATAR_INTRO_TOTAL_DURATION_SEC)

        self._current_phase = self.StreamPhase.LIVE
        await self.event_queue.put({"type": "enter_live_phase", "elapsed_time_sec": self.get_elapsed_time()})
        
        app_state.live_phase_started_event.set()
        logger.info("Live phase started event has been set.")
    
    def set_neuro_speaking_status(self, speaking: bool):
        """Sets and broadcasts the agent's speaking status."""
        if self._is_neuro_speaking != speaking:
            self._is_neuro_speaking = speaking
            try:
                asyncio.create_task(self.event_queue.put({"type": "neuro_is_speaking", "speaking": speaking}))
            except RuntimeError:
                self.event_queue.put_nowait({"type": "neuro_is_speaking", "speaking": speaking})
    
    def get_elapsed_time(self) -> float:
        """Gets the total elapsed time since the stream started."""
        if self._stream_start_global_time > 0:
            return time.time() - self._stream_start_global_time
        return 0.0

    def get_current_phase(self) -> str:
        """Gets the current stream phase."""
        return self._current_phase

    def get_initial_state_for_client(self) -> dict:
        """Generates the initial state event for a newly connected client."""
        elapsed_time = self.get_elapsed_time()
        base_state = {"elapsed_time_sec": elapsed_time}
        if self._current_phase == self.StreamPhase.INITIALIZING:
            return {"type": "play_welcome_video", "progress": elapsed_time, **base_state}
        elif self._current_phase == self.StreamPhase.AVATAR_INTRO:
            return {"type": "start_avatar_intro", **base_state}
        elif self._current_phase == self.StreamPhase.LIVE:
            return {"type": "enter_live_phase", "is_speaking": self._is_neuro_speaking, **base_state}
        return {"type": "offline", **base_state}

# Global singleton instance
live_stream_manager = LiveStreamManager()
