# agent/core.py
"""
Core module for the Neuro Simulator Agent
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys

class Agent:
    """Main Agent class that integrates LLM, memory, and tools"""
    
    def __init__(self, working_dir: str = None):
        # Lazy imports to avoid circular dependencies
        from .memory.manager import MemoryManager
        from .tools.core import ToolManager
        from .llm import LLMClient
        
        self.memory_manager = MemoryManager(working_dir)
        self.tool_manager = ToolManager(self.memory_manager)
        self.llm_client = LLMClient()
        self._initialized = False
        
    async def initialize(self):
        """Initialize the agent, loading any persistent memory"""
        if not self._initialized:
            await self.memory_manager.initialize()
            self._initialized = True
            print("Agent initialized successfully")
        
    async def reset_memory(self):
        """Reset all agent memory"""
        await self.memory_manager.reset_all_memory()
        print("Agent memory reset successfully")
        
    async def process_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Process incoming messages and generate a response
        
        Args:
            messages: List of message dictionaries with 'username' and 'text' keys
            
        Returns:
            Generated response text
        """
        # Ensure agent is initialized
        await self.initialize()
        
        # Add messages to temp memory
        for msg in messages:
            content = f"{msg['username']}: {msg['text']}"
            await self.memory_manager.add_temp_memory(content, "user")
            
        # Get full context for LLM
        context = await self.memory_manager.get_full_context()
        tool_descriptions = self.tool_manager.get_tool_descriptions()
        
        # Create LLM prompt with context and tools
        prompt = f"""
You are {self.memory_manager.init_memory.get('name', 'Neuro-Sama')}, an AI VTuber.
Your personality: {self.memory_manager.init_memory.get('personality', 'Friendly and curious')}

=== CONTEXT ===
{context}

=== AVAILABLE TOOLS ===
{tool_descriptions}

=== INSTRUCTIONS ===
Process the user messages and respond appropriately. You can use tools to manage memory or output responses.
When you want to speak to the user, use the 'speak' tool with your response as the text parameter.
When you want to update memory, use the appropriate memory management tools.
Always think about whether you need to use tools before responding.

User messages:
"""
        
        for msg in messages:
            prompt += f"{msg['username']}: {msg['text']}\n"
            
        prompt += "\nYour response (use tools as needed):"
        
        # Print the full context being sent to LLM for debugging
        print("=" * 50)
        print("CONTEXT SENT TO LLM:")
        print(prompt)
        print("=" * 50)
        
        # Generate response using LLM
        response = await self.llm_client.generate(prompt)
        
        # For now, we'll just return the response directly
        # A full implementation would parse for tool calls and handle them
        return response
        
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a registered tool"""
        # Ensure agent is initialized
        await self.initialize()
        return await self.tool_manager.execute_tool(tool_name, params)