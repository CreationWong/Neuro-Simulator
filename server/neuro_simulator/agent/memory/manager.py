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
    """Manages three types of memory for the agent"""
    
    def __init__(self, working_dir: str = None):
        # Use provided working directory or default to current directory
        if working_dir is None:
            working_dir = os.getcwd()
            
        self.memory_dir = os.path.join(working_dir, "agent", "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # Memory file paths
        self.init_memory_file = os.path.join(self.memory_dir, "init_memory.json")
        self.core_memory_file = os.path.join(self.memory_dir, "core_memory.json")
        self.temp_memory_file = os.path.join(self.memory_dir, "temp_memory.json")
        
        # In-memory storage
        self.init_memory: Dict[str, Any] = {}
        self.core_memory: Dict[str, Any] = {}
        self.temp_memory: List[Dict[str, Any]] = {}
        
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
            
    async def _save_temp_memory(self):
        """Save temp memory to file"""
        with open(self.temp_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.temp_memory, f, ensure_ascii=False, indent=2)
            
    async def reset_all_memory(self):
        """Reset all memory to default values"""
        # Reset to defaults
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
        
        self.temp_memory = []
        
        # Save all memory types
        await self._save_init_memory()
        await self._save_core_memory()
        await self._save_temp_memory()
        
        print("All memory has been reset to default values")
        
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
                    
        # Add temp memory
        context_parts.append("\n=== TEMP MEMORY (Recent Context) ===")
        for i, item in enumerate(self.temp_memory[-20:]):  # Last 20 items
            context_parts.append(f"{i+1}. [{item.get('role', 'unknown')}] {item.get('content', '')}")
            
        return "\n".join(context_parts)
        
    async def add_temp_memory(self, content: str, role: str = "user"):
        """Add an item to temp memory"""
        self.temp_memory.append({
            "id": generate_id(),  # Generate a random ID
            "content": content,
            "role": role,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 100 items
        if len(self.temp_memory) > 100:
            self.temp_memory = self.temp_memory[-100:]
            
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