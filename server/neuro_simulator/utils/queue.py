# neuro_simulator/utils/queue.py
"""Manages the chat queues for audience and agent input."""

import logging
from collections import deque

from ..core.config import config_manager
from ..utils.state import app_state

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

# Deques for chat messages
audience_chat_buffer: deque[dict] = deque()
neuro_input_queue: deque[dict] = deque()

def initialize_queues():
    """
    Initializes the chat queues with sizes from the loaded configuration.
    This must be called after the config is loaded.
    """
    global audience_chat_buffer, neuro_input_queue
    
    settings = config_manager.settings
    if not settings:
        logger.error("Queue initialization failed: Config not loaded.")
        return

    logger.info("Initializing queues with configured sizes.")
    
    # Re-initialize the deques with the correct maxlen
    audience_chat_buffer = deque(
        audience_chat_buffer, 
        maxlen=settings.performance.audience_chat_buffer_max_size
    )
    neuro_input_queue = deque(
        neuro_input_queue,
        maxlen=settings.performance.neuro_input_queue_max_size
    )

def clear_all_queues():
    """Clears all chat queues."""
    audience_chat_buffer.clear()
    neuro_input_queue.clear()
    app_state.superchat_queue.clear()
    logger.info("All chat queues (including superchats) have been cleared.")

def add_to_audience_buffer(chat_item: dict):
    """Adds a chat item to the audience buffer."""
    audience_chat_buffer.append(chat_item)

def add_to_neuro_input_queue(chat_item: dict):
    """Adds a chat item to the agent's input queue."""
    neuro_input_queue.append(chat_item)

def get_recent_audience_chats(limit: int) -> list[dict]:
    """Returns a list of recent chats from the audience buffer."""
    return list(audience_chat_buffer)[-limit:]

def get_all_neuro_input_chats() -> list[dict]:
    """Returns all chats from the agent's input queue and clears it."""
    chats = list(neuro_input_queue)
    neuro_input_queue.clear()
    return chats

def is_neuro_input_queue_empty() -> bool:
    """Checks if the agent's input queue is empty."""
    return not bool(neuro_input_queue)

def get_recent_audience_chats_for_chatbot(limit: int) -> list[dict]:
    """Returns a list of recent chats formatted for the chatbot agent."""
    recent_chats = list(audience_chat_buffer)[-limit:]
    formatted_chats = []
    for chat in recent_chats:
        role = "user" if chat.get("is_user_message") else "assistant"
        formatted_chats.append({
            "role": role,
            "content": f"{chat.get('username', 'unknown')}: {chat.get('text', '')}"
        })
    return formatted_chats