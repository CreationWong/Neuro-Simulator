# neuro_simulator/agent/tools/update_core_memory_block.py
"""The Update Core Memory Block tool for the agent."""

from typing import Dict, Any, List, Optional

from neuro_simulator.agent.tools.base import BaseTool
from neuro_simulator.agent.memory.manager import MemoryManager

class UpdateCoreMemoryBlockTool(BaseTool):
    """Tool to update an existing core memory block."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "update_core_memory_block"

    @property
    def description(self) -> str:
        return "Updates an existing core memory block. All parameters are optional, only provided fields will be updated."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "block_id",
                "type": "string",
                "description": "The ID of the memory block to update.",
                "required": True,
            },
            {
                "name": "title",
                "type": "string",
                "description": "The new title for the memory block.",
                "required": False,
            },
            {
                "name": "description",
                "type": "string",
                "description": "The new description for the memory block.",
                "required": False,
            },
            {
                "name": "content",
                "type": "array",
                "description": "The new list of string entries, which will overwrite the existing content.",
                "required": False,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        block_id = kwargs.get("block_id")
        if not block_id:
            raise ValueError("The 'block_id' parameter is required.")

        # Only include parameters that are not None to avoid overwriting with nulls
        update_payload = {k: v for k, v in kwargs.items() if v is not None}

        await self.memory_manager.update_core_memory_block(**update_payload)
        
        return {
            "status": "success",
            "message": f"Successfully updated core memory block '{block_id}'."
        }
