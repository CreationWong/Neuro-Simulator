# agent/tools.py
"""
Tools that the Neuro Simulator Agent can use
"""

import json
import asyncio
from typing import Dict, Any
from .memory import MemoryManager

class ToolManager:
    """Manages tools that the agent can use to interact with its memory"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.tools = {}
        self._register_default_tools()
        
    def _register_default_tools(self):
        """Register default tools for memory management"""
        self.tools["update_mood"] = self._update_mood
        self.tools["update_topic"] = self._update_topic
        self.tools["update_viewer_count"] = self._update_viewer_count
        self.tools["get_memory_state"] = self._get_memory_state
        
    async def _update_mood(self, mood: str) -> str:
        """Update the agent's mood"""
        await self.memory_manager.update_mutable_memory({"mood": mood})
        return f"Mood updated to: {mood}"
        
    async def _update_topic(self, topic: str) -> str:
        """Update the current topic"""
        await self.memory_manager.update_mutable_memory({"current_topic": topic})
        return f"Topic updated to: {topic}"
        
    async def _update_viewer_count(self, count: int) -> str:
        """Update the viewer count"""
        await self.memory_manager.update_mutable_memory({"viewer_count": count})
        return f"Viewer count updated to: {count}"
        
    async def _get_memory_state(self) -> Dict[str, Any]:
        """Get the current state of all memory"""
        return {
            "immutable": self.memory_manager.immutable_memory,
            "mutable": self.memory_manager.mutable_memory,
            "conversation_history_length": len(self.memory_manager.conversation_history)
        }
        
    def get_tool_descriptions(self) -> str:
        """Get descriptions of all available tools"""
        descriptions = [
            "Available tools:",
            "1. update_mood(mood: string) - Update the agent's mood",
            "2. update_topic(topic: string) - Update the current topic of conversation",
            "3. update_viewer_count(count: integer) - Update the viewer count",
            "4. get_memory_state() - Get the current state of all memory"
        ]
        return "\n".join(descriptions)
        
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool by name with given parameters"""
        if tool_name in self.tools:
            try:
                result = await self.tools[tool_name](**params)
                return result
            except Exception as e:
                return f"Error executing tool '{tool_name}': {str(e)}"
        else:
            return f"Tool '{tool_name}' not found"