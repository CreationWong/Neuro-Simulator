# neuro_simulator/chatbot/memory/manager.py
"""
Manages the chatbot agent's shared memory state (init, core, temp).
"""

import json
import logging
import random
import string
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__.replace("neuro_simulator", "chatbot", 1))

def generate_id(length=6) -> str:
    """Generate a random ID string."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class ChatbotMemoryManager:
    """Manages the three types of shared memory for the chatbot agent."""
    
    def __init__(self, memory_root_path: Path):
        """Initializes the MemoryManager with a specific root path for its memory files."""
        if not memory_root_path:
            raise ValueError("memory_root_path must be provided.")

        self.init_memory_file = memory_root_path / "init_memory.json"
        self.core_memory_file = memory_root_path / "core_memory.json"
        self.temp_memory_file = memory_root_path / "temp_memory.json"
        
        self.init_memory: Dict[str, Any] = {}
        self.core_memory: Dict[str, Any] = {}
        self.temp_memory: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Load all memory types from files. Assumes files have been created by the setup mechanism."""
        # Load init memory
        if self.init_memory_file.exists():
            with open(self.init_memory_file, 'r', encoding='utf-8') as f:
                self.init_memory = json.load(f)
        else:
            logger.error(f"Init memory file not found at {self.init_memory_file}, proceeding with empty memory.")
            self.init_memory = {}
            
        # Load core memory
        if self.core_memory_file.exists():
            with open(self.core_memory_file, 'r', encoding='utf-8') as f:
                self.core_memory = json.load(f)
        else:
            logger.error(f"Core memory file not found at {self.core_memory_file}, proceeding with empty memory.")
            self.core_memory = {"blocks": {}}
            
        # Load temp memory
        if self.temp_memory_file.exists():
            with open(self.temp_memory_file, 'r', encoding='utf-8') as f:
                self.temp_memory = json.load(f)
        else:
            # This is less critical, can start empty
            self.temp_memory = []
            await self._save_temp_memory()
                
        logger.info(f"Chatbot MemoryManager initialized from {self.init_memory_file.parent}.")
        
    async def _save_init_memory(self):
        with open(self.init_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.init_memory, f, ensure_ascii=False, indent=2)

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
        logger.info("Chatbot temp memory has been reset.")
        
    async def add_temp_memory(self, content: str, role: str = "system"):
        self.temp_memory.append({"id": generate_id(), "content": content, "role": role, "timestamp": datetime.now().isoformat()})
        if len(self.temp_memory) > 20:
            self.temp_memory = self.temp_memory[-20:]
        await self._save_temp_memory()

    async def get_core_memory_blocks(self) -> Dict[str, Any]:
        return self.core_memory.get("blocks", {})
