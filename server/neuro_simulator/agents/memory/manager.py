# neuro_simulator/agents/memory/manager.py
"""
Manages an agent's shared memory state (init, core, temp).
This is a generic manager designed to be used by any agent.
"""

import json
import logging
import random
import string
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_id(length=6) -> str:
    """Generate a random ID string."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class MemoryManager:
    """Manages the three types of shared memory for any given agent."""

    def __init__(
        self,
        init_memory_path: Path,
        core_memory_path: Path,
        temp_memory_path: Path,
    ):
        """
        Initializes the MemoryManager with specific paths for its memory files.

        Args:
            init_memory_path: Path to the init_memory.json file.
            core_memory_path: Path to the core_memory.json file.
            temp_memory_path: Path to the temp_memory.json file.
        """
        if not all([init_memory_path, core_memory_path, temp_memory_path]):
            raise ValueError("All memory file paths must be provided.")

        self.init_memory_file = init_memory_path
        self.core_memory_file = core_memory_path
        self.temp_memory_file = temp_memory_path

        self.init_memory: Dict[str, Any] = {}
        self.core_memory: Dict[str, Any] = {}
        self.temp_memory: List[Dict[str, Any]] = []

    async def initialize(self):
        """Load all memory types from their respective files."""
        # Load init memory
        if self.init_memory_file.exists():
            with open(self.init_memory_file, "r", encoding="utf-8") as f:
                self.init_memory = json.load(f)
        else:
            logger.error(
                f"Init memory file not found at {self.init_memory_file}, proceeding with empty memory."
            )
            self.init_memory = {}

        # Load core memory
        if self.core_memory_file.exists():
            with open(self.core_memory_file, "r", encoding="utf-8") as f:
                self.core_memory = json.load(f)
        else:
            logger.error(
                f"Core memory file not found at {self.core_memory_file}, proceeding with empty memory."
            )
            self.core_memory = {"blocks": {}}

        # Load temp memory
        if self.temp_memory_file.exists():
            with open(self.temp_memory_file, "r", encoding="utf-8") as f:
                self.temp_memory = json.load(f)
        else:
            # This is less critical, can start empty
            self.temp_memory = []
            await self._save_temp_memory()

        logger.info(f"MemoryManager initialized from {self.init_memory_file.parent}.")

    # --- Private Save Methods ---

    async def _save_init_memory(self):
        with open(self.init_memory_file, "w", encoding="utf-8") as f:
            json.dump(self.init_memory, f, ensure_ascii=False, indent=2)

    async def _save_core_memory(self):
        with open(self.core_memory_file, "w", encoding="utf-8") as f:
            json.dump(self.core_memory, f, ensure_ascii=False, indent=2)

    async def _save_temp_memory(self):
        with open(self.temp_memory_file, "w", encoding="utf-8") as f:
            json.dump(self.temp_memory, f, ensure_ascii=False, indent=2)

    # --- Init Memory Management ---

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

    # --- Temp Memory Management ---

    async def reset_temp_memory(self):
        """Reset temp memory to an empty list."""
        self.temp_memory = []
        await self._save_temp_memory()
        logger.info(f"Temp memory at {self.temp_memory_file} has been reset.")

    async def add_temp_memory(self, content: str, role: str = "system"):
        """Adds an item to temp memory and ensures the list doesn't exceed 20 items."""
        self.temp_memory.append(
            {
                "id": generate_id(),
                "content": content,
                "role": role,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.temp_memory) > 20:
            self.temp_memory = self.temp_memory[-20:]
        await self._save_temp_memory()

    async def delete_temp_memory_item(self, item_id: str):
        """Deletes an item from temp memory by its ID."""
        initial_len = len(self.temp_memory)
        self.temp_memory = [
            item for item in self.temp_memory if item.get("id") != item_id
        ]
        if len(self.temp_memory) < initial_len:
            await self._save_temp_memory()

    # --- Core Memory Management ---

    async def get_core_memory_blocks(self) -> Dict[str, Any]:
        """Returns all blocks from core memory."""
        return self.core_memory.get("blocks", {})

    async def get_core_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single block from core memory by its ID."""
        return self.core_memory.get("blocks", {}).get(block_id)

    async def create_core_memory_block(
        self, title: str, description: str, content: List[str]
    ) -> str:
        """Creates a new block in core memory and returns its ID."""
        block_id = generate_id()
        if "blocks" not in self.core_memory:
            self.core_memory["blocks"] = {}
        self.core_memory["blocks"][block_id] = {
            "id": block_id,
            "title": title,
            "description": description,
            "content": content or [],
        }
        await self._save_core_memory()
        return block_id

    async def update_core_memory_block(
        self,
        block_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[List[str]] = None,
    ):
        """Updates the fields of an existing block in core memory."""
        block = self.core_memory.get("blocks", {}).get(block_id)
        if not block:
            raise ValueError(f"Block '{block_id}' not found")
        if title is not None:
            block["title"] = title
        if description is not None:
            block["description"] = description
        if content is not None:
            block["content"] = content
        await self._save_core_memory()

    async def delete_core_memory_block(self, block_id: str):
        """Deletes a block from core memory by its ID."""
        if "blocks" in self.core_memory and block_id in self.core_memory["blocks"]:
            del self.core_memory["blocks"][block_id]
            await self._save_core_memory()
