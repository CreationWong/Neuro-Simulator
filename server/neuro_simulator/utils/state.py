# neuro_simulator/utils/state.py
"""Manages the shared state of the application using a singleton class."""

import asyncio
from collections import deque


class AppState:
    """A singleton class to hold all shared application state."""

    def __init__(self):
        self.live_phase_started_event = asyncio.Event()
        self.neuro_last_speech_lock = asyncio.Lock()
        self.neuro_last_speech: str = (
            "Neuro-Sama has just started the stream and hasn't said anything yet."
        )
        self.superchat_queue = deque()
        self.last_superchat_time: float = 0.0
        # Track stream state to distinguish between true stream start and config updates
        self.is_first_response_for_stream: bool = True  # Only reset when a new stream cycle starts
        self.stream_cycle_id: int = 0  # Incremented each time a new stream cycle starts


# Create a single, globally accessible instance of the AppState.
app_state = AppState()
