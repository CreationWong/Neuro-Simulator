# neuro_simulator/chatbot/core.py
"""
Core module for the Neuro Simulator's Chatbot agent.
Implements a dual-LLM "Actor/Thinker" architecture.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...core.agent_interface import BaseAgent
from ...core.config import config_manager
from ...core.llm_manager import llm_manager
from ...core.path_manager import path_manager
from ..memory.manager import MemoryManager
from ..tools.manager import ToolManager
from .nickname_gen.generator import NicknameGenerator

logger = logging.getLogger("neuro_chatbot")


class Chatbot(BaseAgent):
    """
    Chatbot Agent class implementing the Actor/Thinker model and BaseAgent interface.
    """

    def __init__(self):
        if not path_manager:
            raise RuntimeError(
                "PathManager must be initialized before the Chatbot agent."
            )
        if not config_manager.settings:
            raise RuntimeError("ConfigManager must be initialized before the Chatbot agent.")

        settings = config_manager.settings
        self.chatbot_llm = llm_manager.get_client(
            settings.chatbot.chatbot_llm_provider_id
        )
        self.memory_llm = llm_manager.get_client(
            settings.chatbot.chatbot_memory_llm_provider_id
        )

        self.memory_manager = MemoryManager(
            init_memory_path=path_manager.chatbot_init_memory_path,
            core_memory_path=path_manager.chatbot_core_memory_path,
            temp_memory_path=path_manager.chatbot_temp_memory_path,
        )
        self._tool_manager = ToolManager(
            memory_manager=self.memory_manager,
            builtin_tools_path=Path(__file__).parent / "tools",
            user_tools_path=path_manager.chatbot_tools_dir,
            tool_allocations_paths={
                "chatbot": path_manager.chatbot_tools_path,
                "chatbot_memory_manager": path_manager.chatbot_memory_agent_tools_path,
            },
            default_allocations={
                "chatbot": ["post_chat_message"],
                "chatbot_memory_manager": ["add_temp_memory"],
            }
        )
        self.nickname_generator = NicknameGenerator(llm_client=self.chatbot_llm)

        self._initialized = False
        self.turn_counter = 0
        self.reflection_threshold = settings.chatbot.reflection_threshold

    @property
    def tool_manager(self) -> ToolManager:
        return self._tool_manager

    async def initialize(self):
        """Initializes components that are safe to run on startup."""
        if not self._initialized:
            logger.info("Initializing Chatbot agent (startup-safe components)...")
            await self.memory_manager.initialize()
            self.tool_manager.load_tools()
            self._initialized = True
            logger.info("Chatbot agent startup components initialized successfully.")

    async def initialize_runtime_components(self):
        """Initializes components that require a live configuration, like the LLM."""
        logger.info("Initializing Chatbot agent (runtime components)...")
        await self.nickname_generator.initialize()
        logger.info("Chatbot agent runtime components initialized successfully.")

    async def reset_memory(self):
        """Reset all agent memory types and clear history logs."""
        assert path_manager is not None
        await self.memory_manager.reset_temp_memory()
        # Clear history files by overwriting them
        open(path_manager.chatbot_history_path, "w").close()
        logger.info("All chatbot memory and history logs have been reset.")

    async def get_message_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Reads the last N lines from the Chatbot agent's history log."""
        assert path_manager is not None
        return await self._read_history(path_manager.chatbot_history_path, limit)

    async def process_and_respond(
        self,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Main entry point for BaseAgent, not used by Chatbot's current design."""
        logger.warning("process_and_respond is not the primary entry point for Chatbot.")
        return {"status": "not_implemented"}

    async def _append_to_history(self, file_path: Path, data: Dict[str, Any]):
        """Appends a new entry to a JSON Lines history file."""
        data["timestamp"] = datetime.now().isoformat()
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    async def _read_history(self, file_path: Path, limit: int) -> List[Dict[str, Any]]:
        """Reads the last N lines from a JSON Lines history file."""
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return [json.loads(line) for line in lines[-limit:]]
        except (json.JSONDecodeError, IndexError):
            return []

    def _format_tool_schemas_for_prompt(self, agent_name: str) -> str:
        """Formats tool schemas for a specific agent (actor or thinker)."""
        schemas = self.tool_manager.get_tool_schemas_for_agent(agent_name)
        if not schemas:
            return "No tools available."
        lines = ["Available tools:"]
        for i, schema in enumerate(schemas):
            params = ", ".join(
                [
                    f"{p.get('name')}: {p.get('type')}"
                    for p in schema.get("parameters", [])
                ]
            )
            lines.append(
                f"{i + 1}. {schema.get('name')}({params}) - {schema.get('description')}"
            )
        return "\n".join(lines)

    async def build_chatbot_prompt(
        self,
        neuro_speech: str,
        recent_history: List[Dict[str, str]],
    ) -> str:
        """Builds the prompt for the Chatbot (Actor) LLM."""
        assert path_manager is not None
        with open(path_manager.chatbot_prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        tool_descriptions = self._format_tool_schemas_for_prompt("chatbot")
        init_memory_text = json.dumps(self.memory_manager.init_memory, indent=2)
        core_memory_text = json.dumps(self.memory_manager.core_memory, indent=2)
        temp_memory_text = json.dumps(self.memory_manager.temp_memory, indent=2)
        recent_history_text = "\n".join(
            [f"{msg.get('role')}: {msg.get('content')}" for msg in recent_history]
        )

        from ...core.config import config_manager

        assert config_manager.settings is not None

        chats_per_batch = config_manager.settings.chatbot.chats_per_batch

        return prompt_template.format(
            tool_descriptions=tool_descriptions,
            init_memory=init_memory_text,
            core_memory=core_memory_text,
            temp_memory=temp_memory_text,
            recent_history=recent_history_text,
            neuro_speech=neuro_speech,
            chats_per_batch=chats_per_batch,
        )

    async def build_neuro_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Implements the BaseAgent requirement, but delegates to build_chatbot_prompt."""
        # This is a slight mismatch in concepts, as chatbot has a different trigger.
        # We'll use the last message as the 'neuro_speech' context.
        neuro_speech = messages[-1]["text"] if messages else ""
        recent_history = await self.get_message_history(limit=10)
        return await self.build_chatbot_prompt(neuro_speech, recent_history)

    async def _build_memory_prompt(
        self,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        """Builds the prompt for the Memory (Thinker) LLM."""
        assert path_manager is not None
        with open(path_manager.chatbot_memory_agent_prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        tool_descriptions = self._format_tool_schemas_for_prompt('chatbot_memory_manager')
        history_text = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in conversation_history])
        return prompt_template.format(
            tool_descriptions=tool_descriptions, conversation_history=history_text
        )

    def _parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """Extracts and parses a JSON array from the LLM's response text."""
        try:
            start_index = response_text.find("[")
            end_index = response_text.rfind("]")

            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_str = response_text[start_index : end_index + 1]
                return json.loads(json_str)
            else:
                logger.warning(
                    f"Could not find a valid JSON array in response: {response_text}"
                )
                return []
        except Exception as e:
            logger.error(
                f"Failed to parse tool calls from LLM response: {e}\nRaw text: {response_text}"
            )
            return []

    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        agent_name: str,
    ) -> List[Dict[str, str]]:
        assert path_manager is not None
        generated_messages = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            if not tool_name:
                continue
            params = tool_call.get("params", {})
            result = await self.tool_manager.execute_tool(tool_name, **params)

            if (
                agent_name == "chatbot"
                and tool_name == "post_chat_message"
                and result.get("status") == "success"
            ):
                text_to_post = result.get("text_to_post", "")
                if text_to_post:
                    nickname = self.nickname_generator.generate_nickname()
                    message = {"username": nickname, "text": text_to_post}
                    generated_messages.append(message)
                    await self._append_to_history(
                        path_manager.chatbot_history_path,
                        {"role": "assistant", "content": f"{nickname}: {text_to_post}"},
                    )
        logger.info(f"Returning generated messages: {generated_messages}")
        return generated_messages

    async def generate_chat_messages(
        self,
        neuro_speech: str,
        recent_history: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """The main actor loop to generate chat messages."""
        if not self.chatbot_llm:
            logger.warning("Chatbot LLM is not configured. Skipping message generation.")
            return []

        assert path_manager is not None
        for entry in recent_history:
            await self._append_to_history(path_manager.chatbot_history_path, entry)

        prompt = await self.build_chatbot_prompt(neuro_speech, recent_history)
        response_text = await self.chatbot_llm.generate(prompt)
        if not response_text:
            return []

        tool_calls = self._parse_tool_calls(response_text)
        if not tool_calls:
            return []

        messages = await self._execute_tool_calls(tool_calls, "chatbot")

        self.turn_counter += 1
        if self.turn_counter >= self.reflection_threshold:
            asyncio.create_task(self._reflect_and_consolidate())

        return messages

    async def _reflect_and_consolidate(self):
        """The main thinker loop to consolidate memories."""
        if not self.reflection_threshold > 0:
            return

        if not self.memory_llm:
            logger.warning(
                "Chatbot Memory LLM is not configured. Skipping memory consolidation."
            )
            return

        assert path_manager is not None
        logger.info("Chatbot is reflecting on recent conversations...")
        self.turn_counter = 0
        history = await self._read_history(path_manager.chatbot_history_path, limit=50)
        if len(history) < self.reflection_threshold:
            return

        prompt = await self._build_memory_prompt(history)
        response_text = await self.memory_llm.generate(prompt)
        if not response_text:
            return

        tool_calls = self._parse_tool_calls(response_text)
        if not tool_calls:
            return

        await self._execute_tool_calls(tool_calls, 'chatbot_memory_manager')
        logger.info("Chatbot memory consolidation complete.")

    # --- Implementation of BaseAgent interface methods ---

    # Memory Block Management
    async def get_memory_blocks(self) -> List[Dict[str, Any]]:
        blocks_dict = await self.memory_manager.get_core_memory_blocks()
        return list(blocks_dict.values())

    async def get_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        return await self.memory_manager.get_core_memory_block(block_id)

    async def create_memory_block(
        self,
        title: str,
        description: str,
        content: List[str],
    ) -> Dict[str, str]:
        block_id = await self.memory_manager.create_core_memory_block(
            title, description, content
        )
        return {"block_id": block_id}

    async def update_memory_block(
        self,
        block_id: str,
        title: Optional[str],
        description: Optional[str],
        content: Optional[List[str]],
    ):
        await self.memory_manager.update_core_memory_block(
            block_id, title, description, content
        )

    async def delete_memory_block(self, block_id: str):
        await self.memory_manager.delete_core_memory_block(block_id)

    # Init Memory Management
    async def get_init_memory(self) -> Dict[str, Any]:
        return self.memory_manager.init_memory

    async def update_init_memory(self, memory: Dict[str, Any]):
        await self.memory_manager.replace_init_memory(memory)

    async def update_init_memory_item(self, key: str, value: Any):
        await self.memory_manager.update_init_memory_item(key, value)

    async def delete_init_memory_key(self, key: str):
        await self.memory_manager.delete_init_memory_key(key)

    # Temp Memory Management
    async def get_temp_memory(self) -> List[Dict[str, Any]]:
        return self.memory_manager.temp_memory

    async def add_temp_memory(self, content: str, role: str):
        await self.memory_manager.add_temp_memory(content, role)

    async def delete_temp_memory_item(self, item_id: str):
        await self.memory_manager.delete_temp_memory_item(item_id)

    async def clear_temp_memory(self):
        await self.memory_manager.reset_temp_memory()

    # Tool Management
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        return self.tool_manager.get_tool_schemas_for_agent("chatbot")

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        return await self.tool_manager.execute_tool(tool_name, **params)