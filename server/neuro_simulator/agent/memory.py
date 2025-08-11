# agent/memory.py
"""
Memory management for the Neuro Simulator Agent
"""

import os
import json
import asyncio
from typing import Dict, List, Any
from datetime import datetime, timedelta

class MemoryManager:
    """Manages both immutable and mutable memory for the agent"""
    
    def __init__(self, memory_dir: str = "agent_memory"):
        self.memory_dir = memory_dir
        self.immutable_memory_file = os.path.join(memory_dir, "immutable_memory.json")
        self.mutable_memory_file = os.path.join(memory_dir, "mutable_memory.json")
        self.conversation_history_file = os.path.join(memory_dir, "conversation_history.json")
        
        # In-memory storage for faster access
        self.immutable_memory: Dict[str, Any] = {}
        self.mutable_memory: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Create memory directory if it doesn't exist
        os.makedirs(self.memory_dir, exist_ok=True)
        
    async def initialize(self):
        """Load memory from files"""
        # Load immutable memory
        if os.path.exists(self.immutable_memory_file):
            with open(self.immutable_memory_file, 'r') as f:
                self.immutable_memory = json.load(f)
        else:
            # Initialize with default immutable data
            self.immutable_memory = {
                "name": "Neuro-Sama",
                "personality": "Friendly, curious, and entertaining AI VTuber",
                "capabilities": ["chat", "answer questions", "entertain viewers"]
            }
            await self._save_immutable_memory()
            
        # Load mutable memory
        if os.path.exists(self.mutable_memory_file):
            with open(self.mutable_memory_file, 'r') as f:
                self.mutable_memory = json.load(f)
        else:
            # Initialize with default mutable data
            self.mutable_memory = {
                "mood": "happy",
                "current_topic": "streaming",
                "viewer_count": 0
            }
            await self._save_mutable_memory()
            
        # Load conversation history
        if os.path.exists(self.conversation_history_file):
            with open(self.conversation_history_file, 'r') as f:
                self.conversation_history = json.load(f)
                
        print("Memory manager initialized")
        
    async def _save_immutable_memory(self):
        """Save immutable memory to file"""
        with open(self.immutable_memory_file, 'w') as f:
            json.dump(self.immutable_memory, f, indent=2)
            
    async def _save_mutable_memory(self):
        """Save mutable memory to file"""
        with open(self.mutable_memory_file, 'w') as f:
            json.dump(self.mutable_memory, f, indent=2)
            
    async def _save_conversation_history(self):
        """Save conversation history to file"""
        with open(self.conversation_history_file, 'w') as f:
            json.dump(self.conversation_history, f, indent=2)
            
    async def reset(self):
        """Reset all memory"""
        self.immutable_memory = {
            "name": "Neuro-Sama",
            "personality": "Friendly, curious, and entertaining AI VTuber",
            "capabilities": ["chat", "answer questions", "entertain viewers"]
        }
        self.mutable_memory = {
            "mood": "happy",
            "current_topic": "streaming",
            "viewer_count": 0
        }
        self.conversation_history = []
        
        await self._save_immutable_memory()
        await self._save_mutable_memory()
        await self._save_conversation_history()
        
        print("Memory reset completed")
        
    async def add_message(self, message: Dict[str, Any]):
        """Add a message to conversation history"""
        self.conversation_history.append(message)
        # Keep only the last 50 messages
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
        await self._save_conversation_history()
        
    async def get_context(self, max_messages: int = 10) -> str:
        """Get context from conversation history"""
        # Get recent messages
        recent_messages = self.conversation_history[-max_messages:] if self.conversation_history else []
        
        # Format context
        context_parts = []
        
        # Add immutable memory as context
        context_parts.append("Character Information:")
        for key, value in self.immutable_memory.items():
            context_parts.append(f"- {key}: {value}")
            
        # Add mutable memory as context
        context_parts.append("\nCurrent State:")
        for key, value in self.mutable_memory.items():
            context_parts.append(f"- {key}: {value}")
            
        # Add conversation history
        if recent_messages:
            context_parts.append("\nRecent Conversation:")
            for msg in recent_messages:
                context_parts.append(f"{msg['role']}: {msg['content']}")
                
        return "\n".join(context_parts)
        
    async def update_mutable_memory(self, updates: Dict[str, Any]):
        """Update mutable memory with new values"""
        self.mutable_memory.update(updates)
        await self._save_mutable_memory()
        print(f"Mutable memory updated: {updates}")