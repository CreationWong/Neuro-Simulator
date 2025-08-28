# neuro_simulator/agent/memory/manager.py
"""
Manages the agent's shared memory state (init, core, temp).
"""

import json
import logging
import random
import string
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...core.path_manager import path_manager

logger = logging.getLogger(__name__.replace("neuro_simulator", "agent", 1))

def generate_id(length=6) -> str:
    """Generate a random ID string."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class MemoryManager:
    """Manages the three types of shared memory for the agent."""
    
    def __init__(self):
        """Initializes the MemoryManager using paths from the global path_manager."""
        if not path_manager:
            raise RuntimeError("PathManager not initialized before MemoryManager.")

        self.init_memory_file = path_manager.init_memory_path
        self.core_memory_file = path_manager.core_memory_path
        self.temp_memory_file = path_manager.temp_memory_path
        
        self.init_memory: Dict[str, Any] = {}
        self.core_memory: Dict[str, Any] = {}
        self.temp_memory: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Load all memory types from files, creating defaults if they don't exist."""
        # Load or create init memory
        if self.init_memory_file.exists():
            with open(self.init_memory_file, 'r', encoding='utf-8') as f:
                self.init_memory = json.load(f)
        else:
            self.init_memory = {
                "name": "Neuro-Sama", "role": "AI VTuber",
                "personality": "Friendly, curious, and entertaining",
                "capabilities": ["Chat with viewers", "Answer questions"]
            }
            await self._save_init_memory()
            
        # Load or create core memory
        if self.core_memory_file.exists():
            with open(self.core_memory_file, 'r', encoding='utf-8') as f:
                self.core_memory = json.load(f)
        else:
            self.core_memory = {"blocks": {}}
            await self._save_core_memory()
            
        # Load or create temp memory
        if self.temp_memory_file.exists():
            with open(self.temp_memory_file, 'r', encoding='utf-8') as f:
                self.temp_memory = json.load(f)
        else:
            self.temp_memory = []
            await self._save_temp_memory()
                
        logger.info("MemoryManager initialized and memory files loaded/created.")
        
    async def _save_init_memory(self):
        with open(self.init_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.init_memory, f, ensure_ascii=False, indent=2)

    async def replace_init_memory(self, new_memory: Dict[str, Any]):
        """Replaces the entire init memory with a new object."""
        self.init_memory = new_memory
        await self._save_init_memory()

    async def update_init_memory_item(self, key: str, value: Any):
        """Updates or adds a single key-value pair in init memory."""
        self.init_memory[key] = value
        await self._save_init_memory()

    async def delete_init_memory_key(self, key: str):
        """Deletes a key from init memory."""
        if key in self.init_memory:
            del self.init_memory[key]
            await self._save_init_memory()
            
    async def _save_core_memory(self):
        with open(self.core_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.core_memory, f, ensure_ascii=False, indent=2)
            
    async def _save_temp_memory(self):
        with open(self.temp_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.temp_memory, f, ensure_ascii=False, indent=2)
            
    async def reset_temp_memory(self):
        """Reset temp memory to a default empty state."""
        self.temp_memory = []
        await self._save_temp_memory()
        logger.info("Agent temp memory has been reset.")
        
    async def add_temp_memory(self, content: str, role: str = "system"):
        self.temp_memory.append({"id": generate_id(), "content": content, "role": role, "timestamp": datetime.now().isoformat()})
        if len(self.temp_memory) > 20:
            self.temp_memory = self.temp_memory[-20:]
        await self._save_temp_memory()

    async def delete_temp_memory_item(self, item_id: str):
        """Deletes an item from temp memory by its ID."""
        initial_len = len(self.temp_memory)
        self.temp_memory = [item for item in self.temp_memory if item.get("id") != item_id]
        if len(self.temp_memory) < initial_len:
            await self._save_temp_memory()
        
    async def get_core_memory_blocks(self) -> Dict[str, Any]:
        return self.core_memory.get("blocks", {})
        
    async def get_core_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        return self.core_memory.get("blocks", {}).get(block_id)
        
    async def create_core_memory_block(self, title: str, description: str, content: List[str]) -> str:
        block_id = generate_id()
        if "blocks" not in self.core_memory:
            self.core_memory["blocks"] = {}
        self.core_memory["blocks"][block_id] = {
            "id": block_id, "title": title, "description": description, "content": content or []
        }
        await self._save_core_memory()
        return block_id
        
    async def update_core_memory_block(self, block_id: str, title: Optional[str] = None, description: Optional[str] = None, content: Optional[List[str]] = None):
        block = self.core_memory.get("blocks", {}).get(block_id)
        if not block:
            raise ValueError(f"Block '{block_id}' not found")
        if title is not None: block["title"] = title
        if description is not None: block["description"] = description
        if content is not None: block["content"] = content
        await self._save_core_memory()
        
    async def delete_core_memory_block(self, block_id: str):
        if "blocks" in self.core_memory and block_id in self.core_memory["blocks"]:
            del self.core_memory["blocks"][block_id]
            await self._save_core_memory()
