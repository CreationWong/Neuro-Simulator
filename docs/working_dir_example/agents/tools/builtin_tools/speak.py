# neuro_simulator/agent/tools/speak.py
"""The Speak tool for the agent."""

import logging
from typing import Dict, Any, List

from neuro_simulator.agent.tools.base import BaseTool
from neuro_simulator.agent.memory.manager import MemoryManager

logger = logging.getLogger(__name__.replace("neuro_simulator", "agent", 1))

class SpeakTool(BaseTool):
    """Tool for the agent to speak to the audience."""

    def __init__(self, memory_manager: MemoryManager):
        """Initializes the SpeakTool."""
        # This tool doesn't directly use the memory manager, but accepts it for consistency.
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "speak"

    @property
    def description(self) -> str:
        return "Outputs text to the user. This is the primary way to communicate with the audience."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "text",
                "type": "string",
                "description": "The text to be spoken to the audience.",
                "required": True,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Executes the speak action.
        
        Args:
            **kwargs: Must contain a 'text' key with the string to be spoken.

        Returns:
            A dictionary confirming the action and the text that was spoken.
        """
        text = kwargs.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError("The 'text' parameter must be a non-empty string.")
        
        logger.info(f"Agent says: {text}")
        # The result of the speak tool is the text that was spoken.
        # This can be used for logging or further processing.
        return {"status": "success", "spoken_text": text}
