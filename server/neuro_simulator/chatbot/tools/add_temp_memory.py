# neuro_simulator/chatbot/tools/add_temp_memory.py
"""The Add Temp Memory tool for the chatbot agent."""

from typing import Any, Dict, List

from neuro_simulator.chatbot.tools.base import BaseChatbotTool
from neuro_simulator.chatbot.memory.manager import ChatbotMemoryManager

class AddTempMemoryTool(BaseChatbotTool):
    """Tool to add an entry to the chatbot's temporary memory."""

    def __init__(self, memory_manager: ChatbotMemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "add_temp_memory"

    @property
    def description(self) -> str:
        return "Adds an entry to the temporary memory. Use for short-term observations, recent facts, or topics to bring up soon."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "content",
                "type": "string",
                "description": "The content of the memory entry.",
                "required": True,
            },
            {
                "name": "role",
                "type": "string",
                "description": "The role associated with the memory (e.g., 'system', 'user'). Defaults to 'system'.",
                "required": False,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        content = kwargs.get("content")
        if not isinstance(content, str) or not content:
            raise ValueError("The 'content' parameter must be a non-empty string.")
        
        role = kwargs.get("role", "system")
        if not isinstance(role, str):
            raise ValueError("The 'role' parameter must be a string.")

        await self.memory_manager.add_temp_memory(content=content, role=role)
        
        return {"status": "success", "message": f"Added entry to temporary memory with role '{role}'."}
