# neuro_simulator/agent/tools/get_core_memory_block.py
"""The Get Core Memory Block tool for the agent."""

from typing import Dict, Any, List

from neuro_simulator.agent.tools.base import BaseTool
from neuro_simulator.agent.memory.manager import MemoryManager

class GetCoreMemoryBlockTool(BaseTool):
    """Tool to retrieve a single core memory block by its ID."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "get_core_memory_block"

    @property
    def description(self) -> str:
        return "Retrieves the full details of a single core memory block using its ID."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "block_id",
                "type": "string",
                "description": "The ID of the memory block to retrieve.",
                "required": True,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        block_id = kwargs.get("block_id")
        if not block_id:
            raise ValueError("The 'block_id' parameter is required.")

        block = await self.memory_manager.get_core_memory_block(block_id)
        
        if block is None:
            return {"status": "error", "message": f"Block '{block_id}' not found."}

        return {"status": "success", "block": block}
