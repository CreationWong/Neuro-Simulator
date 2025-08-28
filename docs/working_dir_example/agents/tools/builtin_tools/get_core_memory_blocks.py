# neuro_simulator/agent/tools/get_core_memory_blocks.py
"""The Get Core Memory Blocks tool for the agent."""

from typing import Dict, Any, List

from neuro_simulator.agent.tools.base import BaseTool
from neuro_simulator.agent.memory.manager import MemoryManager

class GetCoreMemoryBlocksTool(BaseTool):
    """Tool to retrieve all core memory blocks."""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "get_core_memory_blocks"

    @property
    def description(self) -> str:
        return "Retrieves a list of all available core memory blocks, including their IDs, titles, and descriptions."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return []

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        blocks = await self.memory_manager.get_core_memory_blocks()
        # The result should be JSON serializable, which a Dict of Dicts already is.
        return {"status": "success", "blocks": blocks}
