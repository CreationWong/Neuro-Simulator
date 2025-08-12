# agent/memory/manager.py
"""
Advanced memory management for the Neuro Simulator Agent
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import random
import string
import sys


def generate_id(length=6) -> str:
    """Generate a random ID string"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


class MemoryManager:
    """Manages different types of memory for the agent"""
    
    def __init__(self, working_dir: str = None):
        # Use provided working directory or default to current directory
        if working_dir is None:
            working_dir = os.getcwd()
            
        self.memory_dir = os.path.join(working_dir, "agent", "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # Memory file paths
        self.init_memory_file = os.path.join(self.memory_dir, "init_memory.json")
        self.core_memory_file = os.path.join(self.memory_dir, "core_memory.json")
        self.context_file = os.path.join(self.memory_dir, "context.json")  # 新的上下文文件
        self.temp_memory_file = os.path.join(self.memory_dir, "temp_memory.json")
        
        # In-memory storage
        self.init_memory: Dict[str, Any] = {}
        self.core_memory: Dict[str, Any] = {}
        self.context_history: List[Dict[str, Any]] = []  # 新的上下文历史
        self.temp_memory: List[Dict[str, Any]] = []     # 真正的临时内存
        
    async def initialize(self):
        """Load all memory types from files"""
        # Load init memory (immutable by agent)
        if os.path.exists(self.init_memory_file):
            with open(self.init_memory_file, 'r', encoding='utf-8') as f:
                self.init_memory = json.load(f)
        else:
            # Default init memory - this is just an example, users can customize
            self.init_memory = {
                "name": "Neuro-Sama",
                "role": "AI VTuber",
                "personality": "Friendly, curious, and entertaining",
                "capabilities": [
                    "Chat with viewers",
                    "Answer questions",
                    "Entertain audience",
                    "Express opinions"
                ]
            }
            await self._save_init_memory()
            
        # Load core memory (mutable by both agent and user)
        if os.path.exists(self.core_memory_file):
            with open(self.core_memory_file, 'r', encoding='utf-8') as f:
                self.core_memory = json.load(f)
        else:
            # Default core memory with blocks
            self.core_memory = {
                "blocks": {
                    "general_knowledge": {
                        "id": "general_knowledge",
                        "title": "General Knowledge",
                        "description": "Basic facts and knowledge about the world",
                        "content": [
                            "The earth is round",
                            "Water boils at 100°C at sea level",
                            "Humans need oxygen to survive"
                        ]
                    },
                    "stream_info": {
                        "id": "stream_info",
                        "title": "Stream Information",
                        "description": "Information about this stream and Neuro-Sama",
                        "content": [
                            "This is a simulation of Neuro-Sama, an AI VTuber",
                            "The stream is meant for entertainment and experimentation",
                            "Viewers can interact with Neuro-Sama through chat"
                        ]
                    }
                }
            }
            await self._save_core_memory()
            
        # Load context history
        if os.path.exists(self.context_file):
            with open(self.context_file, 'r', encoding='utf-8') as f:
                self.context_history = json.load(f)
        else:
            self.context_history = []
            
        # Load temp memory (frequently changed by agent)
        if os.path.exists(self.temp_memory_file):
            with open(self.temp_memory_file, 'r', encoding='utf-8') as f:
                self.temp_memory = json.load(f)
                
        print("Memory manager initialized with all memory types")
        
    async def _save_init_memory(self):
        """Save init memory to file"""
        with open(self.init_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.init_memory, f, ensure_ascii=False, indent=2)
            
    async def _save_core_memory(self):
        """Save core memory to file"""
        with open(self.core_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.core_memory, f, ensure_ascii=False, indent=2)
            
    async def _save_context(self):
        """Save context to file"""
        with open(self.context_file, 'w', encoding='utf-8') as f:
            json.dump(self.context_history, f, ensure_ascii=False, indent=2)
            
    async def _save_temp_memory(self):
        """Save temp memory to file"""
        with open(self.temp_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.temp_memory, f, ensure_ascii=False, indent=2)
            
    async def add_context_entry(self, role: str, content: str):
        """Add an entry to context"""
        entry = {
            "id": generate_id(),
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.context_history.append(entry)
        
        # Keep only last 20 context entries (10 rounds)
        if len(self.context_history) > 20:
            self.context_history = self.context_history[-20:]
            
        await self._save_context()
        
    async def add_detailed_context_entry(self, input_messages: List[Dict[str, str]], 
                                         prompt: str, llm_response: str, 
                                         tool_executions: List[Dict[str, Any]], 
                                         final_response: str):
        """Add a detailed context entry with full LLM interaction details"""
        entry = {
            "id": generate_id(),
            "type": "llm_interaction",
            "input_messages": input_messages,
            "prompt": prompt,
            "llm_response": llm_response,
            "tool_executions": tool_executions,
            "final_response": final_response,
            "timestamp": datetime.now().isoformat()
        }
        self.context_history.append(entry)
        
        # Keep only last 20 context entries
        if len(self.context_history) > 20:
            self.context_history = self.context_history[-20:]
            
        await self._save_context()
        
    async def get_recent_context(self, rounds: int = 5) -> List[Dict[str, Any]]:
        """Get recent context (default: last 5 rounds, 10 entries)"""
        # Each round consists of user message and assistant response
        entries_needed = rounds * 2
        return self.context_history[-entries_needed:] if self.context_history else []
        
    async def get_detailed_context_history(self) -> List[Dict[str, Any]]:
        """Get the full detailed context history"""
        return self.context_history
        
    async def get_last_agent_response(self) -> Optional[str]:
        """Get the last response from the agent"""
        for entry in reversed(self.context_history):
            if entry.get("role") == "assistant":
                return entry["content"]
            elif entry.get("type") == "llm_interaction":
                return entry["final_response"]
        return None
        
    async def reset_context(self):
        """Reset context"""
        self.context_history = []
        await self._save_context()
        
    async def reset_temp_memory(self):
        """Reset only temp memory to default values from example files"""
        # Load default temp memory from example
        example_temp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                         "..", "docs", "working_dir_example", "agent", "memory", "temp_memory.json")
        if os.path.exists(example_temp_path):
            with open(example_temp_path, 'r', encoding='utf-8') as f:
                self.temp_memory = json.load(f)
        else:
            # Fallback to empty list with one test entry if example file not found
            self.temp_memory = [
                {
                    "id": "0test0",
                    "content": "This is a test temp_memory.",
                    "role": "Vedal987",
                    "timestamp": "2024-12-24T00:00:00.000000"
                }
            ]
        
        # Save only temp memory
        await self._save_temp_memory()
        
        print("Temp memory has been reset to default values from example files")
        
    async def get_full_context(self) -> str:
        """Get all memory as context for LLM"""
        context_parts = []
        
        # Add init memory
        context_parts.append("=== INIT MEMORY (Immutable) ===")
        for key, value in self.init_memory.items():
            context_parts.append(f"{key}: {value}")
            
        # Add core memory
        context_parts.append("\n=== CORE MEMORY (Long-term, Mutable) ===")
        if "blocks" in self.core_memory:
            for block_id, block in self.core_memory["blocks"].items():
                context_parts.append(f"\nBlock: {block['title']} ({block_id})")
                context_parts.append(f"Description: {block['description']}")
                context_parts.append("Content:")
                for item in block["content"]:
                    context_parts.append(f"  - {item}")
                    
        # Add context (recent conversation history)
        context_parts.append("\n=== CONTEXT (Recent Conversation) ===")
        recent_context = await self.get_recent_context(5)
        for i, entry in enumerate(recent_context):
            role_display = "User" if entry["role"] == "user" else "Assistant"
            context_parts.append(f"{i+1}. [{role_display}] {entry['content']}")
            
        # Add temp memory (only for temporary state, not dialog history)
        if self.temp_memory:
            context_parts.append("\n=== TEMP MEMORY (Processing State) ===")
            for item in self.temp_memory:
                context_parts.append(f"[{item.get('role', 'system')}] {item.get('content', '')}")
                
        return "\n".join(context_parts)
        
    async def add_temp_memory(self, content: str, role: str = "system"):
        """Add an item to temp memory (for temporary processing state)"""
        self.temp_memory.append({
            "id": generate_id(),
            "content": content,
            "role": role,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 temp items
        if len(self.temp_memory) > 20:
            self.temp_memory = self.temp_memory[-20:]
            
        await self._save_temp_memory()
        
    # Core memory management methods
    async def get_core_memory_blocks(self) -> Dict[str, Any]:
        """Get all core memory blocks"""
        return self.core_memory.get("blocks", {})
        
    async def get_core_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific core memory block"""
        blocks = self.core_memory.get("blocks", {})
        return blocks.get(block_id)
        
    async def create_core_memory_block(self, title: str, description: str, content: List[str]):
        """Create a new core memory block with a generated ID"""
        block_id = generate_id()
        
        if "blocks" not in self.core_memory:
            self.core_memory["blocks"] = {}
            
        self.core_memory["blocks"][block_id] = {
            "id": block_id,
            "title": title,
            "description": description,
            "content": content if content else []
        }
        
        await self._save_core_memory()
        return block_id  # Return the generated ID
        
    async def update_core_memory_block(self, block_id: str, title: str = None, description: str = None, content: List[str] = None):
        """Update a core memory block"""
        if "blocks" not in self.core_memory or block_id not in self.core_memory["blocks"]:
            raise ValueError(f"Block '{block_id}' not found")
            
        block = self.core_memory["blocks"][block_id]
        if title is not None:
            block["title"] = title
        if description is not None:
            block["description"] = description
        if content is not None:
            block["content"] = content
            
        await self._save_core_memory()
        
    async def delete_core_memory_block(self, block_id: str):
        """Delete a core memory block"""
        if "blocks" in self.core_memory and block_id in self.core_memory["blocks"]:
            del self.core_memory["blocks"][block_id]
            await self._save_core_memory()
            
    async def add_to_core_memory_block(self, block_id: str, item: str):
        """Add an item to a core memory block"""
        if "blocks" not in self.core_memory or block_id not in self.core_memory["blocks"]:
            raise ValueError(f"Block '{block_id}' not found")
            
        self.core_memory["blocks"][block_id]["content"].append(item)
        await self._save_core_memory()
        
    async def remove_from_core_memory_block(self, block_id: str, index: int):
        """Remove an item from a core memory block by index"""
        if "blocks" not in self.core_memory or block_id not in self.core_memory["blocks"]:
            raise ValueError(f"Block '{block_id}' not found")
            
        if 0 <= index < len(self.core_memory["blocks"][block_id]["content"]):
            self.core_memory["blocks"][block_id]["content"].pop(index)
            await self._save_core_memory()
        else:
            raise IndexError(f"Index {index} out of range for block '{block_id}'")