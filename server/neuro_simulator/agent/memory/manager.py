# neuro_simulator/agent/memory/manager.py
"""
Advanced memory management for the Neuro Simulator Agent.
"""

import asyncio
import json
import logging
import os
import random
import string
from datetime import datetime
from typing import Any, Dict, List, Optional

# Use the existing agent logger for consistent logging
logger = logging.getLogger("neuro_agent")

def generate_id(length=6) -> str:
    """Generate a random ID string."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class MemoryManager:
    """Manages different types of memory for the agent."""
    
    def __init__(self, working_dir: str = None):
        if working_dir is None:
            working_dir = os.getcwd()
            
        self.memory_dir = os.path.join(working_dir, "agent", "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        self.init_memory_file = os.path.join(self.memory_dir, "init_memory.json")
        self.core_memory_file = os.path.join(self.memory_dir, "core_memory.json")
        self.chat_history_file = os.path.join(self.memory_dir, "chat_history.json")
        self.temp_memory_file = os.path.join(self.memory_dir, "temp_memory.json")
        
        self.init_memory: Dict[str, Any] = {}
        self.core_memory: Dict[str, Any] = {}
        self.chat_history: List[Dict[str, Any]] = []
        self.temp_memory: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Load all memory types from files."""
        # Load init memory
        if os.path.exists(self.init_memory_file):
            with open(self.init_memory_file, 'r', encoding='utf-8') as f:
                self.init_memory = json.load(f)
        else:
            self.init_memory = {
                "name": "Neuro-Sama", "role": "AI VTuber",
                "personality": "Friendly, curious, and entertaining",
                "capabilities": ["Chat with viewers", "Answer questions"]
            }
            await self._save_init_memory()
            
        # Load core memory
        if os.path.exists(self.core_memory_file):
            with open(self.core_memory_file, 'r', encoding='utf-8') as f:
                self.core_memory = json.load(f)
        else:
            self.core_memory = {"blocks": {}}
            await self._save_core_memory()
            
        # Load chat history
        if os.path.exists(self.chat_history_file):
            with open(self.chat_history_file, 'r', encoding='utf-8') as f:
                self.chat_history = json.load(f)
        else:
            self.chat_history = []
            
        # Load temp memory
        if os.path.exists(self.temp_memory_file):
            with open(self.temp_memory_file, 'r', encoding='utf-8') as f:
                self.temp_memory = json.load(f)
        else:
            self.temp_memory = []
                
        logger.info("Agent memory manager initialized.")
        
    async def _save_init_memory(self):
        with open(self.init_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.init_memory, f, ensure_ascii=False, indent=2)
            
    async def update_init_memory(self, new_memory: Dict[str, Any]):
        self.init_memory.update(new_memory)
        await self._save_init_memory()
            
    async def _save_core_memory(self):
        with open(self.core_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.core_memory, f, ensure_ascii=False, indent=2)
            
    async def _save_chat_history(self):
        with open(self.chat_history_file, 'w', encoding='utf-8') as f:
            json.dump(self.chat_history, f, ensure_ascii=False, indent=2)
            
    async def _save_temp_memory(self):
        with open(self.temp_memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.temp_memory, f, ensure_ascii=False, indent=2)
            
    async def add_chat_entry(self, role: str, content: str):
        entry = {"id": generate_id(), "role": role, "content": content, "timestamp": datetime.now().isoformat()}
        self.chat_history.append(entry)
        await self._save_chat_history()
        
    async def add_detailed_chat_entry(self, input_messages: List[Dict[str, str]], 
                                         prompt: str, llm_response: str, 
                                         tool_executions: List[Dict[str, Any]], 
                                         final_response: str, entry_id: str = None):
        update_data = {
            "input_messages": input_messages, "prompt": prompt, "llm_response": llm_response,
            "tool_executions": tool_executions, "final_response": final_response,
            "timestamp": datetime.now().isoformat()
        }
        if entry_id:
            for entry in self.chat_history:
                if entry.get("id") == entry_id:
                    entry.update(update_data)
                    await self._save_chat_history()
                    return entry_id
        
        new_entry = {"id": entry_id or generate_id(), "type": "llm_interaction", "role": "assistant", **update_data}
        self.chat_history.append(new_entry)
        await self._save_chat_history()
        return new_entry["id"]
        
    async def get_recent_chat(self, entries: int = 10) -> List[Dict[str, Any]]:
        return self.chat_history[-entries:]
        
    async def get_detailed_chat_history(self) -> List[Dict[str, Any]]:
        return self.chat_history
        
    async def get_last_agent_response(self) -> Optional[str]:
        for entry in reversed(self.chat_history):
            if entry.get("type") == "llm_interaction":
                final_response = entry.get("final_response", "")
                if final_response and final_response not in ["Processing started", "Prompt sent to LLM", "LLM response received"]:
                    return final_response
            elif entry.get("role") == "assistant":
                content = entry.get("content", "")
                if content and content != "Processing started":
                    return content
        return None
        
    async def reset_chat_history(self):
        self.chat_history = []
        await self._save_chat_history()
        
    async def reset_temp_memory(self):
        """Reset temp memory to a default empty state."""
        self.temp_memory = []
        await self._save_temp_memory()
        logger.info("Agent temp memory has been reset.")
        
    async def get_full_context(self) -> str:
        context_parts = ["=== INIT MEMORY (Immutable) ===", json.dumps(self.init_memory, indent=2)]
        context_parts.append("\n=== CORE MEMORY (Long-term, Mutable) ===")
        if "blocks" in self.core_memory:
            for block_id, block in self.core_memory["blocks"].items():
                context_parts.append(f"\nBlock: {block.get('title', '')} ({block_id})")
                context_parts.append(f"Description: {block.get('description', '')}")
                context_parts.append("Content:")
                for item in block.get("content", []):
                    context_parts.append(f"  - {item}")
        if self.temp_memory:
            context_parts.append("\n=== TEMP MEMORY (Processing State) ===")
            for item in self.temp_memory:
                context_parts.append(f"[{item.get('role', 'system')}] {item.get('content', '')}")
        return "\n".join(context_parts)
        
    async def add_temp_memory(self, content: str, role: str = "system"):
        self.temp_memory.append({"id": generate_id(), "content": content, "role": role, "timestamp": datetime.now().isoformat()})
        if len(self.temp_memory) > 20:
            self.temp_memory = self.temp_memory[-20:]
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