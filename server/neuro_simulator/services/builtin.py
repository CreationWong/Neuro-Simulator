# neuro_simulator/services/builtin.py
"""Builtin agent module for Neuro Simulator"""

import asyncio
import re
import logging
from typing import List, Dict, Any, Optional

from ..core.agent_interface import BaseAgent
from ..agent.core import Agent as LocalAgent
from ..services.stream import live_stream_manager

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

async def initialize_builtin_agent() -> Optional[LocalAgent]:
    """Initializes the builtin agent instance and returns it."""
    try:
        working_dir = live_stream_manager._working_dir
        agent_instance = LocalAgent(working_dir=working_dir)
        await agent_instance.initialize()
        logger.info("Builtin agent implementation initialized successfully.")
        return agent_instance
    except Exception as e:
        logger.error(f"Failed to initialize local agent implementation: {e}", exc_info=True)
        return None

class BuiltinAgentWrapper(BaseAgent):
    """Wrapper for the builtin agent to implement the BaseAgent interface."""    
    def __init__(self, agent_instance: LocalAgent):
        self.agent_instance = agent_instance
        
    async def initialize(self):
        if self.agent_instance is None:
            raise RuntimeError("Builtin agent not initialized")
        await self.agent_instance.initialize()

    async def reset_memory(self):
        await self.agent_instance.reset_all_memory()

    async def process_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        return await self.agent_instance.process_messages(messages)

    # Memory Block Management
    async def get_memory_blocks(self) -> List[Dict[str, Any]]:
        blocks_dict = await self.agent_instance.memory_manager.get_core_memory_blocks()
        return list(blocks_dict.values())

    async def get_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        return await self.agent_instance.memory_manager.get_core_memory_block(block_id)

    async def create_memory_block(self, title: str, description: str, content: List[str]) -> Dict[str, str]:
        block_id = await self.agent_instance.memory_manager.create_core_memory_block(title, description, content)
        return {"block_id": block_id}

    async def update_memory_block(self, block_id: str, title: Optional[str], description: Optional[str], content: Optional[List[str]]):
        await self.agent_instance.memory_manager.update_core_memory_block(block_id, title, description, content)

    async def delete_memory_block(self, block_id: str):
        await self.agent_instance.memory_manager.delete_core_memory_block(block_id)

    # Init Memory Management
    async def get_init_memory(self) -> Dict[str, Any]:
        return self.agent_instance.memory_manager.init_memory

    async def update_init_memory(self, memory: Dict[str, Any]):
        await self.agent_instance.memory_manager.update_init_memory(memory)

    # Temp Memory Management
    async def get_temp_memory(self) -> List[Dict[str, Any]]:
        return self.agent_instance.memory_manager.temp_memory

    async def add_temp_memory(self, content: str, role: str):
        await self.agent_instance.memory_manager.add_temp_memory(content, role)

    async def clear_temp_memory(self):
        await self.agent_instance.memory_manager.reset_temp_memory()

    # Tool Management
    async def get_available_tools(self) -> str:
        return self.agent_instance.tool_manager.get_tool_descriptions()

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        return await self.agent_instance.execute_tool(tool_name, params)

    # Context/Message History
    async def get_message_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return await self.agent_instance.memory_manager.get_recent_context(limit)
