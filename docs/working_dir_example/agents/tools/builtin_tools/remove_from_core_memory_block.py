# neuro_simulator/agent/tools/remove_from_core_memory_block.py
"""The Remove from Core Memory Block tool for the agent."""

from typing import Dict, Any, List

from neuro_simulator.agent.tools.base import BaseTool
from neuro_simulator.agent.memory.manager import MemoryManager

class RemoveFromCoreMemoryBlockTool(BaseTool):
    """Tool to remove an item from an existing core memory block's content list by its index."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "remove_from_core_memory_block"

    @property
    def description(self) -> str:
        return "Removes an item from the content list of a specific core memory block by its zero-based index."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "block_id",
                "type": "string",
                "description": "The ID of the memory block to modify.",
                "required": True,
            },
            {
                "name": "index",
                "type": "integer",
                "description": "The zero-based index of the item to remove from the content list.",
                "required": True,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        block_id = kwargs.get("block_id")
        index = kwargs.get("index")

        if not block_id or index is None:
            raise ValueError("The 'block_id' and 'index' parameters are required.")

        block = await self.memory_manager.get_core_memory_block(block_id)
        if block is None:
            raise ValueError(f"Block '{block_id}' not found.")
        
        content = block.get("content", [])
        if not isinstance(content, list):
            raise TypeError(f"Content of block '{block_id}' is not a list.")

        try:
            removed_item = content.pop(index)
        except IndexError:
            raise IndexError(f"Index {index} is out of bounds for content in block '{block_id}'.")
        
        await self.memory_manager.update_core_memory_block(block_id=block_id, content=content)
        
        return {
            "status": "success",
            "message": f"Removed item '{removed_item}' from core memory block '{block_id}' at index {index}."
        }
