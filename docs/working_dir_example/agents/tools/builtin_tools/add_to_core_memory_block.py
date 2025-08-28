# neuro_simulator/agent/tools/add_to_core_memory_block.py
"""The Add to Core Memory Block tool for the agent."""

from typing import Dict, Any, List

from neuro_simulator.agent.tools.base import BaseTool
from neuro_simulator.agent.memory.manager import MemoryManager

class AddToCoreMemoryBlockTool(BaseTool):
    """Tool to add an item to an existing core memory block's content list."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "add_to_core_memory_block"

    @property
    def description(self) -> str:
        return "Adds a new string item to the content list of a specific core memory block."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "block_id",
                "type": "string",
                "description": "The ID of the memory block to add to.",
                "required": True,
            },
            {
                "name": "item",
                "type": "string",
                "description": "The new string item to add to the block's content list.",
                "required": True,
            }
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        block_id = kwargs.get("block_id")
        item = kwargs.get("item")
        if not block_id or not item:
            raise ValueError("The 'block_id' and 'item' parameters are required.")

        # This functionality doesn't exist in MemoryManager, so we need to implement it here.
        # It's a common pattern: get, modify, save.
        block = await self.memory_manager.get_core_memory_block(block_id)
        if block is None:
            raise ValueError(f"Block '{block_id}' not found.")
        
        content = block.get("content", [])
        if not isinstance(content, list):
            # Handle case where content might not be a list
            raise TypeError(f"Content of block '{block_id}' is not a list.")

        content.append(item)
        
        await self.memory_manager.update_core_memory_block(block_id=block_id, content=content)
        
        return {
            "status": "success",
            "message": f"Added item to core memory block '{block_id}'."
        }
