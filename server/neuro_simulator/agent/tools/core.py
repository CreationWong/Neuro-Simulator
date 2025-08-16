# neuro_simulator/agent/tools/core.py
"""
Core tools for the Neuro Simulator Agent
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Use a logger with a shortened, more readable name
logger = logging.getLogger(__name__.replace("neuro_simulator", "agent", 1))

class ToolManager:
    """Manages all tools available to the agent"""
    
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.tools = {}
        self._register_tools()
        
    def _register_tools(self):
        """Register all available tools"""
        self.tools["get_core_memory_blocks"] = self._get_core_memory_blocks
        self.tools["get_core_memory_block"] = self._get_core_memory_block
        self.tools["create_core_memory_block"] = self._create_core_memory_block
        self.tools["update_core_memory_block"] = self._update_core_memory_block
        self.tools["delete_core_memory_block"] = self._delete_core_memory_block
        self.tools["add_to_core_memory_block"] = self._add_to_core_memory_block
        self.tools["remove_from_core_memory_block"] = self._remove_from_core_memory_block
        self.tools["add_temp_memory"] = self._add_temp_memory
        self.tools["speak"] = self._speak
        
    def get_tool_descriptions(self) -> str:
        """Get descriptions of all available tools"""
        descriptions = [
            "Available tools:",
            "1. get_core_memory_blocks() - Get all core memory blocks",
            "2. get_core_memory_block(block_id: string) - Get a specific core memory block",
            "3. create_core_memory_block(title: string, description: string, content: list) - Create a new core memory block with a generated ID",
            "4. update_core_memory_block(block_id: string, title: string (optional), description: string (optional), content: list (optional)) - Update a core memory block",
            "5. delete_core_memory_block(block_id: string) - Delete a core memory block",
            "6. add_to_core_memory_block(block_id: string, item: string) - Add an item to a core memory block",
            "7. remove_from_core_memory_block(block_id: string, index: integer) - Remove an item from a core memory block by index",
            "8. add_temp_memory(content: string, role: string) - Add an item to temporary memory",
            "9. speak(text: string) - Output text to the user",
            "",
            "IMPORTANT INSTRUCTIONS:",
            "- When you want to speak to the user, ONLY use the speak tool with your response as the text parameter",
            "- DO NOT use print() or any other wrapper functions around the speak tool",
            "- Example of correct usage: speak(text='Hello, how can I help you today?')",
            "- Example of incorrect usage: print(speak(text='Hello, how can I help you today?'))",
            "- ONLY return ONE tool call per response",
            "- Format your response as plain text with the tool call, nothing else"
        ]
        return "\n".join(descriptions)
        
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found"}
            
        try:
            result = await self.tools[tool_name](**params)
            return result
        except Exception as e:
            return {"error": f"Error executing tool '{tool_name}': {str(e)}"}
            
    # Tool implementations
    async def _get_core_memory_blocks(self) -> Dict[str, Any]:
        return await self.memory_manager.get_core_memory_blocks()
        
    async def _get_core_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        return await self.memory_manager.get_core_memory_block(block_id)
        
    async def _create_core_memory_block(self, title: str, description: str, content: List[str]) -> str:
        block_id = await self.memory_manager.create_core_memory_block(title, description, content)
        return f"Created core memory block '{block_id}' with title '{title}'"
        
    async def _update_core_memory_block(self, block_id: str, title: str = None, description: str = None, content: List[str] = None) -> str:
        await self.memory_manager.update_core_memory_block(block_id, title, description, content)
        return f"Updated core memory block '{block_id}'"
        
    async def _delete_core_memory_block(self, block_id: str) -> str:
        await self.memory_manager.delete_core_memory_block(block_id)
        return f"Deleted core memory block '{block_id}'"
        
    async def _add_to_core_memory_block(self, block_id: str, item: str) -> str:
        await self.memory_manager.add_to_core_memory_block(block_id, item)
        return f"Added item to core memory block '{block_id}'"
        
    async def _remove_from_core_memory_block(self, block_id: str, index: int) -> str:
        await self.memory_manager.remove_from_core_memory_block(block_id, index)
        return f"Removed item from core memory block '{block_id}' at index {index}"
        
    async def _add_temp_memory(self, content: str, role: str = "user") -> str:
        await self.memory_manager.add_temp_memory(content, role)
        return f"Added item to temp memory with role '{role}'"
        
    async def _speak(self, text: str) -> str:
        """Output text - this is how the agent communicates with users"""
        logger.info(f"Agent says: {text}")
        return text
