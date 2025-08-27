# neuro_simulator/agent/tools/create_core_memory_block.py
"""The Create Core Memory Block tool for the agent."""

from typing import Dict, Any, List

from neuro_simulator.agent.tools.base import BaseTool
from neuro_simulator.agent.memory.manager import MemoryManager

class CreateCoreMemoryBlockTool(BaseTool):
    """Tool to create a new core memory block."""

    def __init__(self, memory_manager: MemoryManager):
        """Initializes the CreateCoreMemoryBlockTool."""
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "create_core_memory_block"

    @property
    def description(self) -> str:
        return "Creates a new core memory block with a specified title and description. Returns the new block's ID."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "title",
                "type": "string",
                "description": "The title for the new memory block.",
                "required": True,
            },
            {
                "name": "description",
                "type": "string",
                "description": "A short description of the purpose of this memory block.",
                "required": True,
            },
            {
                "name": "content",
                "type": "array",
                "description": "An optional list of initial string entries for the block's content.",
                "required": False,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Executes the action to create a new core memory block.

        Args:
            **kwargs: Must contain 'title' and 'description', and optionally 'content'.

        Returns:
            A dictionary with the result, including the new block's ID.
        """
        title = kwargs.get("title")
        description = kwargs.get("description")
        content = kwargs.get("content", [])

        if not isinstance(title, str) or not title:
            raise ValueError("The 'title' parameter must be a non-empty string.")
        if not isinstance(description, str) or not description:
            raise ValueError("The 'description' parameter must be a non-empty string.")
        if not isinstance(content, list):
            raise ValueError("The 'content' parameter must be a list of strings.")

        block_id = await self.memory_manager.create_core_memory_block(
            title=title,
            description=description,
            content=content
        )
        
        return {
            "status": "success",
            "message": f"Created core memory block '{block_id}' with title '{title}'.",
            "block_id": block_id
        }
