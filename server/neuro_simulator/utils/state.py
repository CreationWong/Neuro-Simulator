# neuro_simulator/utils/state.py
"""Manages the shared state of the application using a singleton class."""

import asyncio

class AppState:
    """A singleton class to hold all shared application state."""
    def __init__(self):
        self.live_phase_started_event = asyncio.Event()
        self.neuro_last_speech_lock = asyncio.Lock()
        self.neuro_last_speech: str = "Neuro-Sama has just started the stream and hasn't said anything yet."

# Create a single, globally accessible instance of the AppState.
app_state = AppState()
