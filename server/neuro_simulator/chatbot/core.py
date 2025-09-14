# neuro_simulator/chatbot/core.py
"""
Core module for the Neuro Simulator's Chatbot agent.
Implements a dual-LLM "Actor/Thinker" architecture.
"""

import asyncio
import json
import logging
import re
import shutil
import importlib.resources
import os
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

from ..core.path_manager import path_manager
from .llm import ChatbotLLMClient
from .memory.manager import ChatbotMemoryManager
from .tools.manager import ChatbotToolManager
from .nickname_gen.generator import NicknameGenerator

logger = logging.getLogger("neuro_chatbot")

class ChatbotAgent:
    """
    Chatbot Agent class implementing the Actor/Thinker model.
    """
    
    def __init__(self):
        if not path_manager:
            raise RuntimeError("PathManager must be initialized before the Chatbot Agent.")
        
        self.memory_manager = ChatbotMemoryManager(path_manager.chatbot_memories_dir)
        self.tool_manager = ChatbotToolManager(self.memory_manager)
        self.nickname_generator = NicknameGenerator()
        
        self.chatbot_llm = ChatbotLLMClient()
        self.memory_llm = ChatbotLLMClient()
        
        self._initialized = False
        self.turn_counter = 0
        self.reflection_threshold = 5 # Consolidate memory every 5 turns

    async def initialize(self):
        """Initialize the agent, copying default files and loading components."""
        if not self._initialized:
            logger.info("Initializing Chatbot Agent...")
            self._setup_working_directory()
            self.tool_manager.load_tools()
            await self.memory_manager.initialize()
            await self.nickname_generator.initialize()
            self._initialized = True
            logger.info("Chatbot Agent initialized successfully.")

    def _setup_working_directory(self):
        """Ensures the chatbot's working directory is populated with default files."""
        logger.info("Setting up chatbot working directory...")
        try:
            package_source_dir = Path(importlib.resources.files('neuro_simulator'))
        except (ModuleNotFoundError, AttributeError):
             package_source_dir = Path(__file__).parent.parent

        files_to_copy = {
            "chatbot/prompts/chatbot_prompt.txt": path_manager.chatbot_agent_prompt_path,
            "chatbot/prompts/memory_prompt.txt": path_manager.chatbot_memory_agent_prompt_path,
            "chatbot/memory/init_memory.json": path_manager.chatbot_init_memory_path,
            "chatbot/memory/core_memory.json": path_manager.chatbot_core_memory_path,
            "chatbot/memory/temp_memory.json": path_manager.chatbot_temp_memory_path,
            "chatbot/nickname_gen/data/adjectives.txt": path_manager.chatbot_nickname_data_dir / "adjectives.txt",
            "chatbot/nickname_gen/data/nouns.txt": path_manager.chatbot_nickname_data_dir / "nouns.txt",
            "chatbot/nickname_gen/data/special_users.txt": path_manager.chatbot_nickname_data_dir / "special_users.txt",
        }

        for src_rel_path, dest_path in files_to_copy.items():
            if not dest_path.exists():
                source_path = package_source_dir / src_rel_path
                if source_path.exists():
                    try:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(source_path, dest_path)
                        logger.info(f"Copied default file to {dest_path}")
                    except Exception as e:
                        logger.error(f"Could not copy default file from {source_path}: {e}")
        
        self._copy_builtin_tools(package_source_dir)

    def _copy_builtin_tools(self, package_source_dir: Path):
        """Copies the packaged built-in tools to the working directory."""
        source_dir = package_source_dir / "chatbot" / "tools"
        dest_dir = path_manager.chatbot_builtin_tools_dir

        if not source_dir.exists():
            logger.warning(f"Default chatbot tools source directory not found at {source_dir}")
            return

        dest_dir.mkdir(parents=True, exist_ok=True)

        for item in os.listdir(source_dir):
            source_item = source_dir / item
            if source_item.is_file() and source_item.name.endswith('.py') and not item.startswith(('__', 'base', 'manager')):
                dest_item = dest_dir / item
                if not dest_item.exists():
                    shutil.copy(source_item, dest_item)
                    logger.info(f"Copied default chatbot tool to {dest_item}")

    async def _append_to_history(self, file_path: Path, data: Dict[str, Any]):
        """Appends a new entry to a JSON Lines history file."""
        data['timestamp'] = datetime.now().isoformat()
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    async def _read_history(self, file_path: Path, limit: int) -> List[Dict[str, Any]]:
        """Reads the last N lines from a JSON Lines history file."""
        if not file_path.exists(): return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            return [json.loads(line) for line in lines[-limit:]]
        except (json.JSONDecodeError, IndexError): return []

    def _format_tool_schemas_for_prompt(self, agent_name: str) -> str:
        """Formats tool schemas for a specific agent (actor or thinker)."""
        schemas = self.tool_manager.get_tool_schemas_for_agent(agent_name)
        if not schemas: return "No tools available."
        lines = ["Available tools:"]
        for i, schema in enumerate(schemas):
            params = ", ".join([f"{p.get('name')}: {p.get('type')}" for p in schema.get("parameters", [])])
            lines.append(f"{i+1}. {schema.get('name')}({params}) - {schema.get('description')}")
        return "\n".join(lines)

    async def _build_chatbot_prompt(self, neuro_speech: str, recent_history: List[Dict[str, str]]) -> str:
        """Builds the prompt for the Chatbot (Actor) LLM."""
        with open(path_manager.chatbot_agent_prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        tool_descriptions = self._format_tool_schemas_for_prompt('chatbot_agent')
        init_memory_text = json.dumps(self.memory_manager.init_memory, indent=2)
        core_memory_text = json.dumps(self.memory_manager.core_memory, indent=2)
        temp_memory_text = json.dumps(self.memory_manager.temp_memory, indent=2)
        recent_history_text = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in recent_history])

        from ..core.config import config_manager
        chats_per_batch = config_manager.settings.chatbot_agent.chats_per_batch

        return prompt_template.format(
            tool_descriptions=tool_descriptions,
            init_memory=init_memory_text,
            core_memory=core_memory_text,
            temp_memory=temp_memory_text,
            recent_history=recent_history_text,
            neuro_speech=neuro_speech,
            chats_per_batch=chats_per_batch
        )

    async def _build_memory_prompt(self, conversation_history: List[Dict[str, str]]) -> str:
        """Builds the prompt for the Memory (Thinker) LLM."""
        with open(path_manager.chatbot_memory_agent_prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        tool_descriptions = self._format_tool_schemas_for_prompt('chatbot_memory_agent')
        history_text = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in conversation_history])
        return prompt_template.format(tool_descriptions=tool_descriptions, conversation_history=history_text)

    def _parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """Extracts and parses a JSON array from the LLM's response text."""
        try:
            # Find the start and end of the main JSON array
            start_index = response_text.find('[')
            end_index = response_text.rfind(']')

            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_str = response_text[start_index : end_index + 1]
                return json.loads(json_str)
            else:
                logger.warning(f"Could not find a valid JSON array in response: {response_text}")
                return []
        except Exception as e:
            logger.error(f"Failed to parse tool calls from LLM response: {e}\nRaw text: {response_text}")
            return []

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]], agent_name: str) -> List[Dict[str, str]]:
        generated_messages = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            params = tool_call.get("params", {})
            result = await self.tool_manager.execute_tool(tool_name, **params)
            
            if agent_name == 'chatbot_agent' and tool_name == "post_chat_message" and result.get("status") == "success":
                text_to_post = result.get("text_to_post", "")
                if text_to_post:
                    nickname = self.nickname_generator.generate_nickname()
                    message = {"username": nickname, "text": text_to_post}
                    generated_messages.append(message)
                    await self._append_to_history(path_manager.chatbot_agent_history_path, {'role': 'assistant', 'content': f"{nickname}: {text_to_post}"})
        logger.info(f"Returning generated messages: {generated_messages}")
        return generated_messages

    async def generate_chat_messages(self, neuro_speech: str, recent_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """The main actor loop to generate chat messages."""
        for entry in recent_history:
            await self._append_to_history(path_manager.chatbot_agent_history_path, entry)
        
        prompt = await self._build_chatbot_prompt(neuro_speech, recent_history)
        response_text = await self.chatbot_llm.generate(prompt)
        if not response_text: return []

        tool_calls = self._parse_tool_calls(response_text)
        if not tool_calls: return []

        messages = await self._execute_tool_calls(tool_calls, 'chatbot_agent')
        
        self.turn_counter += 1
        if self.turn_counter >= self.reflection_threshold:
            asyncio.create_task(self._reflect_and_consolidate())
        
        return messages

    async def _reflect_and_consolidate(self):
        """The main thinker loop to consolidate memories."""
        logger.info("Chatbot is reflecting on recent conversations...")
        self.turn_counter = 0
        history = await self._read_history(path_manager.chatbot_agent_history_path, limit=50)
        if len(history) < self.reflection_threshold:
            return

        prompt = await self._build_memory_prompt(history)
        response_text = await self.memory_llm.generate(prompt)
        if not response_text: return

        tool_calls = self._parse_tool_calls(response_text)
        if not tool_calls: return

        await self._execute_tool_calls(tool_calls, 'chatbot_memory_agent')
        logger.info("Chatbot memory consolidation complete.")
