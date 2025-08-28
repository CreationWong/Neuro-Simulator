# neuro_simulator/agent/tools/delete_core_memory_block.py
"""The Delete Core Memory Block tool for the agent."""

from typing import Dict, Any, List

from neuro_simulator.agent.tools.base import BaseTool
from neuro_simulator.agent.memory.manager import MemoryManager

class DeleteCoreMemoryBlockTool(BaseTool):
    """Tool to delete an existing core memory block."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "delete_core_memory_block"

    @property
    def description(self) -> str:
        return "Deletes a core memory block using its ID."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "block_id",
                "type": "string",
                "description": "The ID of the memory block to delete.",
                "required": True,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        block_id = kwargs.get("block_id")
        if not block_id:
            raise ValueError("The 'block_id' parameter is required.")

        await self.memory_manager.delete_core_memory_block(block_id=block_id)
        
        return {
            "status": "success",
            "message": f"Core memory block '{block_id}' has been deleted."
        }
