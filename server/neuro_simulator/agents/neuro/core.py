# server/neuro_simulator/agents/neuro/core.py
"""
Core module for the Neuro Simulator's built-in agent.
Implements a dual-LLM "Actor/Thinker" architecture for responsive interaction
and asynchronous memory consolidation.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.agent_interface import BaseAgent
from ...core.config import config_manager
from ...core.llm_manager import llm_manager
from ...core.path_manager import path_manager
from ...utils.banner import Colors, box_it_up
from ..memory.manager import MemoryManager
from ..tools.manager import ToolManager
from .filter.filter import NeuroFilter

logger = logging.getLogger("neuro_agent")


class Neuro(BaseAgent):
    """
    Main Neuro agent class, implementing the BaseAgent interface.
    This class handles the core logic for Neuro's responses and memory.
    """

    def __init__(self):
        if not path_manager:
            raise RuntimeError("PathManager must be initialized before the Neuro agent.")

        if not config_manager.settings:
            raise RuntimeError("ConfigManager must be initialized before the Neuro agent.")

        settings = config_manager.settings
        self.neuro_llm = llm_manager.get_client(settings.neuro.neuro_llm_provider_id)
        self.memory_llm = llm_manager.get_client(
            settings.neuro.neuro_memory_llm_provider_id
        )

        filter_llm_id = (
            settings.neuro.neuro_filter_llm_provider_id
            or settings.neuro.neuro_llm_provider_id
        )
        self.filter = NeuroFilter(filter_llm_id)

        self.memory_manager = MemoryManager(
            init_memory_path=path_manager.init_memory_path,
            core_memory_path=path_manager.core_memory_path,
            temp_memory_path=path_manager.temp_memory_path,
        )
        self._tool_manager = ToolManager(
            memory_manager=self.memory_manager,
            builtin_tools_path=Path(__file__).parent / "tools",
            user_tools_path=path_manager.user_tools_dir,
            tool_allocations_paths={
                "neuro_agent": path_manager.neuro_tools_path,
                "memory_manager": path_manager.memory_agent_tools_path,
            },
            default_allocations={
                "neuro_agent": [
                    "think",
                    "speak",
                    "add_temp_memory",
                    "get_core_memory_blocks",
                    "get_core_memory_block",
                    "model_spin",
                    "model_zoom",
                ],
                "memory_manager": [
                    "add_temp_memory",
                    "create_core_memory_block",
                    "update_core_memory_block",
                    "delete_core_memory_block",
                    "add_to_core_memory_block",
                    "remove_from_core_memory_block",
                    "get_core_memory_blocks",
                    "get_core_memory_block",
                ],
            }
        )

        self._initialized = False
        self.turn_counter = 0
        self.reflection_threshold = settings.neuro.reflection_threshold

        logger.info("Hello everyone, Neuro-sama here.")

    @property
    def tool_manager(self) -> ToolManager:
        return self._tool_manager

    async def initialize(self):
        """Initialize the agent, loading any persistent memory and tools."""
        if not self._initialized:
            logger.info("Initializing agent memory and tools...")
            await self.memory_manager.initialize()
            self.tool_manager.load_tools()
            self._initialized = True
            logger.info("Agent initialized successfully.")

    async def reset_memory(self):
        """Reset all agent memory types and clear history logs."""
        assert path_manager is not None
        await self.memory_manager.reset_temp_memory()
        # Clear history files by overwriting them
        open(path_manager.neuro_history_path, "w").close()
        open(path_manager.memory_agent_history_path, "w").close()
        logger.info("All agent memory and history logs have been reset.")

    async def get_message_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Reads the last N lines from the Neuro agent's history log."""
        assert path_manager is not None
        return await self._read_history_log(path_manager.neuro_history_path, limit)

    async def _append_to_history_log(self, file_path: Path, data: Dict[str, Any]):
        """Appends a new entry to a JSON Lines history file."""
        data["timestamp"] = datetime.now().isoformat()
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    async def _read_history_log(
        self,
        file_path: Path,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Reads the last N lines from a JSON Lines history file."""
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return [json.loads(line) for line in lines[-limit:]]
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Could not read or parse history from {file_path}: {e}")
            return []

    def _format_tool_schemas_for_prompt(self, schemas: List[Dict[str, Any]]) -> str:
        """Formats a list of tool schemas into a string for the LLM prompt."""
        if not schemas:
            return "No tools available."
        lines = ["Available tools:"]
        for i, schema in enumerate(schemas):
            params_str_parts = []
            for param in schema.get("parameters", []):
                p_name = param.get("name")
                p_type = param.get("type")
                p_req = "required" if param.get("required") else "optional"
                params_str_parts.append(f"{p_name}: {p_type} ({p_req})")
            params_str = ", ".join(params_str_parts)
            lines.append(
                f"{i + 1}. {schema.get('name')}({params_str}) - {schema.get('description')}"
            )
        return "\n".join(lines)



    async def build_neuro_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Builds the prompt for the Neuro (Actor) LLM."""
        assert path_manager is not None
        prompt_template = ""
        if path_manager.neuro_prompt_path.exists():
            with open(path_manager.neuro_prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        else:
            logger.warning(
                f"Neuro prompt template not found at {path_manager.neuro_prompt_path}"
            )

        tool_schemas = self.tool_manager.get_tool_schemas_for_agent("neuro_agent")
        tool_descriptions = self._format_tool_schemas_for_prompt(tool_schemas)

        init_memory_text = "\n".join(
            f"{key}: {value}" for key, value in self.memory_manager.init_memory.items()
        )

        core_memory_blocks = await self.memory_manager.get_core_memory_blocks()
        core_memory_parts = [
            f"\nBlock: {b.get('title', '')} ({b_id})\nDescription: {b.get('description', '')}\nContent:\n"
            + "\n".join([f"  - {item}" for item in b.get("content", [])])
            for b_id, b in core_memory_blocks.items()
        ]
        core_memory_text = (
            "\n".join(core_memory_parts) if core_memory_parts else "Not set."
        )

        temp_memory_text = (
            "\n".join(
                [
                    f"[{item.get('role', 'system')}] {item.get('content', '')}"
                    for item in self.memory_manager.temp_memory
                ]
            )
            if self.memory_manager.temp_memory
            else "Empty."
        )

        user_messages_text = "\n".join(
            [f"{msg['username']}: {msg['text']}" for msg in messages]
        )

        return prompt_template.format(
            tool_descriptions=tool_descriptions,
            init_memory=init_memory_text,
            core_memory=core_memory_text,
            temp_memory=temp_memory_text,
            user_messages=user_messages_text,
        )

    async def _build_memory_prompt(
        self,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        """Builds the prompt for the Memory (Thinker) LLM."""
        assert path_manager is not None
        prompt_template = ""
        if path_manager.memory_agent_prompt_path.exists():
            with open(
                path_manager.memory_agent_prompt_path, "r", encoding="utf-8"
            ) as f:
                prompt_template = f.read()
        else:
            logger.warning(
                f"Memory prompt template not found at {path_manager.memory_agent_prompt_path}"
            )

        tool_schemas = self.tool_manager.get_tool_schemas_for_agent("memory_manager")
        tool_descriptions = self._format_tool_schemas_for_prompt(tool_schemas)
        history_text = "\n".join(
            [
                f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                for msg in conversation_history
            ]
        )

        return prompt_template.format(
            tool_descriptions=tool_descriptions, conversation_history=history_text
        )

    def _parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        try:
            match = re.search(
                r"""```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\])""", response_text
            )
            if not match:
                logger.warning(
                    f"No valid JSON tool call block found in response: {response_text}"
                )
                return []
            json_str = match.group(1) or match.group(2)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse tool calls from LLM response: {e}")
            return []

    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        agent_name: str, # Added for signature consistency
    ) -> Dict[str, Any]:
        execution_results = []
        final_responses = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            # Handle both 'params' and 'parameters' for robustness.
            params = tool_call.get("params") or tool_call.get("parameters", {})
            if not tool_name:
                continue
            logger.info(f"Executing tool: {tool_name} with params: {params}")
            try:
                result = await self.tool_manager.execute_tool(tool_name, **params)
                execution_results.append(
                    {"name": tool_name, "params": params, "result": result}
                )
                if tool_name == "speak" and result.get("status") == "success":
                    spoken_text = result.get("spoken_text", "")
                    if spoken_text:
                        final_responses.append(spoken_text)
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                execution_results.append(
                    {"name": tool_name, "params": params, "error": str(e)}
                )
        return {"tool_executions": execution_results, "final_responses": final_responses}

    async def process_and_respond(
        self, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        assert path_manager is not None
        await self.initialize()
        logger.info(f"Processing {len(messages)} messages in Actor flow.")

        if not self.neuro_llm:
            logger.warning("Neuro's Actor LLM is not configured. Skipping response.")
            return {"tool_executions": [], "final_response": ""}

        for msg in messages:
            await self._append_to_history_log(
                path_manager.neuro_history_path,
                {"role": "user", "content": f"{msg['username']}: {msg['text']}"},
            )

        prompt = await self.build_neuro_prompt(messages)
        response_text = await self.neuro_llm.generate(prompt)

        tool_calls = self._parse_tool_calls(response_text)

        # Filter all speak tool calls
        if self.filter and config_manager.settings.neuro.filter_enabled:
            for i in range(len(tool_calls) - 1, -1, -1):
                tool_call = tool_calls[i]
                if tool_call.get("name") == "speak":
                    logger.info("Filter enabled. Reviewing a speak call.")
                    original_text = (tool_call.get("params") or tool_call.get("parameters", {})).get("text", "")

                    if original_text:
                        filtered_calls = await self.filter.process(original_output=original_text)
                        if filtered_calls:
                            # Replace the original speak call with the filtered one
                            tool_calls[i] = filtered_calls[0]
                        else:
                            # If filter fails, remove the speak call to be safe
                            tool_calls.pop(i)
                            logger.warning("Filter did not return a tool call. Suppressing this speech.")
                    else:
                        # If speak call has no text, remove it
                        tool_calls.pop(i)

        # Execute all tool calls (including 'think' and the filtered 'speak')
        processing_result = await self._execute_tool_calls(tool_calls, "neuro_agent")

        if final_responses := processing_result.get("final_responses", []):
            full_response = " ".join(final_responses)
            await self._append_to_history_log(
                path_manager.neuro_history_path,
                {"role": "assistant", "content": full_response},
            )

        self.turn_counter += 1
        if self.turn_counter >= self.reflection_threshold:
            asyncio.create_task(self._reflect_and_consolidate())

        return processing_result

    async def _reflect_and_consolidate(self):
        """The main thinker loop to consolidate memories for the Neuro agent."""
        if not self.reflection_threshold > 0:
            return

        if not self.memory_llm:
            logger.warning(
                "Neuro Memory LLM is not configured. Skipping memory consolidation."
            )
            return

        assert path_manager is not None
        logger.info("Neuro is reflecting on recent conversations...")
        box_it_up(
            ["The 'Thinker' agent is now active.", "Consolidating recent memories..."],
            title="Neuro Memory Consolidation Started",
            border_color=Colors.BLUE,
        )
        self.turn_counter = 0
        # Use neuro's history path
        history = await self._read_history_log(path_manager.neuro_history_path, limit=50)
        if len(history) < self.reflection_threshold:
            return

        prompt = await self._build_memory_prompt(history)
        response_text = await self.memory_llm.generate(prompt)
        box_it_up(
            response_text.split('\n'),
            title="Neuro (Thinker) Raw Response",
            border_color=Colors.GREEN,
        )
        if not response_text:
            return

        tool_calls = self._parse_tool_calls(response_text)
        box_it_up(
            json.dumps(tool_calls, indent=2).split('\n'),
            title="Neuro (Thinker) Parsed Tool Calls",
            border_color=Colors.YELLOW,
        )
        if not tool_calls:
            return

        # Execute with the 'memory_manager' agent name
        await self._execute_tool_calls(tool_calls, "memory_manager")
        box_it_up(
            ["The 'Thinker' agent has finished its task."],
            title="Neuro Memory Consolidation Complete",
            border_color=Colors.BLUE,
        )
        logger.info("Neuro memory consolidation complete.")

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
        return self.tool_manager.get_tool_schemas_for_agent("neuro_agent")

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        return await self.tool_manager.execute_tool(tool_name, **params)
