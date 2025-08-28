# neuro_simulator/services/builtin.py
"""Builtin agent module for Neuro Simulator"""

import logging
from typing import List, Dict, Any, Optional

from ..core.agent_interface import BaseAgent
from ..agent.core import Agent as LocalAgent
from ..utils.websocket import connection_manager

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

async def initialize_builtin_agent() -> Optional[LocalAgent]:
    """Initializes a new builtin agent instance and returns it."""
    try:
        agent_instance = LocalAgent()
        await agent_instance.initialize()
        logger.info("New builtin agent instance initialized successfully.")
        return agent_instance
    except Exception as e:
        logger.error(f"Failed to initialize local agent instance: {e}", exc_info=True)
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

    async def process_and_respond(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        return await self.agent_instance.process_and_respond(messages)

    # Memory Block Management
    async def get_memory_blocks(self) -> List[Dict[str, Any]]:
        blocks_dict = await self.agent_instance.memory_manager.get_core_memory_blocks()
        return list(blocks_dict.values())

    async def get_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        return await self.agent_instance.memory_manager.get_core_memory_block(block_id)

    async def create_memory_block(self, title: str, description: str, content: List[str]) -> Dict[str, str]:
        block_id = await self.agent_instance.memory_manager.create_core_memory_block(title, description, content)
        updated_blocks = await self.get_memory_blocks()
        await connection_manager.broadcast_to_admins({"type": "core_memory_updated", "payload": updated_blocks})
        return {"block_id": block_id}

    async def update_memory_block(self, block_id: str, title: Optional[str], description: Optional[str], content: Optional[List[str]]):
        await self.agent_instance.memory_manager.update_core_memory_block(block_id, title, description, content)
        updated_blocks = await self.get_memory_blocks()
        await connection_manager.broadcast_to_admins({"type": "core_memory_updated", "payload": updated_blocks})

    async def delete_memory_block(self, block_id: str):
        await self.agent_instance.memory_manager.delete_core_memory_block(block_id)
        updated_blocks = await self.get_memory_blocks()
        await connection_manager.broadcast_to_admins({"type": "core_memory_updated", "payload": updated_blocks})

    # Init Memory Management
    async def get_init_memory(self) -> Dict[str, Any]:
        return self.agent_instance.memory_manager.init_memory

    async def update_init_memory(self, memory: Dict[str, Any]):
        await self.agent_instance.memory_manager.replace_init_memory(memory)
        updated_init_mem = await self.get_init_memory()
        await connection_manager.broadcast_to_admins({"type": "init_memory_updated", "payload": updated_init_mem})

    async def update_init_memory_item(self, key: str, value: Any):
        await self.agent_instance.memory_manager.update_init_memory_item(key, value)
        updated_init_mem = await self.get_init_memory()
        await connection_manager.broadcast_to_admins({"type": "init_memory_updated", "payload": updated_init_mem})

    async def delete_init_memory_key(self, key: str):
        await self.agent_instance.memory_manager.delete_init_memory_key(key)
        updated_init_mem = await self.get_init_memory()
        await connection_manager.broadcast_to_admins({"type": "init_memory_updated", "payload": updated_init_mem})

    # Temp Memory Management
    async def get_temp_memory(self) -> List[Dict[str, Any]]:
        return self.agent_instance.memory_manager.temp_memory

    async def add_temp_memory(self, content: str, role: str):
        await self.agent_instance.memory_manager.add_temp_memory(content, role)
        updated_temp_mem = await self.get_temp_memory()
        await connection_manager.broadcast_to_admins({"type": "temp_memory_updated", "payload": updated_temp_mem})

    async def delete_temp_memory_item(self, item_id: str):
        await self.agent_instance.memory_manager.delete_temp_memory_item(item_id)
        updated_temp_mem = await self.get_temp_memory()
        await connection_manager.broadcast_to_admins({"type": "temp_memory_updated", "payload": updated_temp_mem})

    async def clear_temp_memory(self):
        await self.agent_instance.memory_manager.reset_temp_memory()
        updated_temp_mem = await self.get_temp_memory()
        await connection_manager.broadcast_to_admins({"type": "temp_memory_updated", "payload": updated_temp_mem})

    # Tool Management
    async def get_available_tools(self) -> str:
        # This method is now for internal use, the dashboard uses the new API
        schemas = self.agent_instance.tool_manager.get_tool_schemas_for_agent('neuro_agent')
        return self.agent_instance._format_tool_schemas_for_prompt(schemas)

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        result = await self.agent_instance.tool_manager.execute_tool(tool_name, **params)
        if tool_name == "add_temp_memory":
            updated_temp_mem = await self.get_temp_memory()
            await connection_manager.broadcast_to_admins({"type": "temp_memory_updated", "payload": updated_temp_mem})
        return result

    # Context/Message History
    async def get_message_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return await self.agent_instance.get_neuro_history(limit)