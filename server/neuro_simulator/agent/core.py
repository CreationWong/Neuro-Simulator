# neuro_simulator/agent/core.py
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
from typing import Any, Dict, List

from ..core.path_manager import path_manager
from .llm import LLMClient
from .memory.manager import MemoryManager
from .tools.manager import ToolManager

logger = logging.getLogger("neuro_agent")

class Agent:
    """
    Main Agent class implementing the Actor/Thinker model.
    - The "Neuro" part (Actor) handles real-time interaction.
    - The "Memory" part (Thinker) handles background memory consolidation.
    """
    
    def __init__(self):
        if not path_manager:
            raise RuntimeError("PathManager must be initialized before the Agent.")
        
        self.memory_manager = MemoryManager()
        self.tool_manager = ToolManager(self.memory_manager)
        
        self.neuro_llm = LLMClient()
        self.memory_llm = LLMClient()
        
        self._initialized = False
        self.turn_counter = 0
        self.reflection_threshold = 3
        
        logger.info("Agent instance created with dual-LLM architecture.")

    async def initialize(self):
        """Initialize the agent, loading any persistent memory."""
        if not self._initialized:
            logger.info("Initializing agent memory manager...")
            await self.memory_manager.initialize()
            self._initialized = True
            logger.info("Agent initialized successfully.")
        
    async def reset_all_memory(self):
        """Reset all agent memory types and clear history logs."""
        await self.memory_manager.reset_temp_memory()
        # Clear history files by overwriting them
        open(path_manager.neuro_history_path, 'w').close()
        open(path_manager.memory_agent_history_path, 'w').close()
        logger.info("All agent memory and history logs have been reset.")

    async def get_neuro_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Reads the last N lines from the Neuro agent's history log."""
        return await self._read_history_log(path_manager.neuro_history_path, limit)

    async def _append_to_history_log(self, file_path: Path, data: Dict[str, Any]):
        """Appends a new entry to a JSON Lines history file."""
        data['timestamp'] = datetime.now().isoformat()
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    async def _read_history_log(self, file_path: Path, limit: int) -> List[Dict[str, Any]]:
        """Reads the last N lines from a JSON Lines history file."""
        if not file_path.exists():
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Get the last N lines and parse them
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
                p_name = param.get('name')
                p_type = param.get('type')
                p_req = 'required' if param.get('required') else 'optional'
                params_str_parts.append(f"{p_name}: {p_type} ({p_req})")
            params_str = ", ".join(params_str_parts)
            lines.append(f"{i+1}. {schema.get('name')}({params_str}) - {schema.get('description')}")
        return "\n".join(lines)

    async def _build_neuro_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Builds the prompt for the Neuro (Actor) LLM."""
        prompt_template = "" # Define a default empty prompt
        if path_manager.neuro_prompt_path.exists():
            with open(path_manager.neuro_prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        else:
            logger.warning(f"Neuro prompt template not found at {path_manager.neuro_prompt_path}")

        tool_schemas = self.tool_manager.get_tool_schemas_for_agent('neuro_agent')
        tool_descriptions = self._format_tool_schemas_for_prompt(tool_schemas)
        
        init_memory_text = "\n".join(f"{key}: {value}" for key, value in self.memory_manager.init_memory.items())
        
        core_memory_blocks = await self.memory_manager.get_core_memory_blocks()
        core_memory_parts = [f"\nBlock: {b.get('title', '')} ({b_id})\nDescription: {b.get('description', '')}\nContent:\n" + "\n".join([f"  - {item}" for item in b.get("content", [])]) for b_id, b in core_memory_blocks.items()]
        core_memory_text = "\n".join(core_memory_parts) if core_memory_parts else "Not set."

        temp_memory_text = "\n".join([f"[{item.get('role', 'system')}] {item.get('content', '')}" for item in self.memory_manager.temp_memory]) if self.memory_manager.temp_memory else "Empty."

        recent_history = await self._read_history_log(path_manager.neuro_history_path, limit=10)
        recent_history_text = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in recent_history])
        user_messages_text = "\n".join([f"{msg['username']}: {msg['text']}" for msg in messages])

        return prompt_template.format(
            tool_descriptions=tool_descriptions,
            init_memory=init_memory_text,
            core_memory=core_memory_text,
            temp_memory=temp_memory_text,
            recent_history=recent_history_text,
            user_messages=user_messages_text
        )

    async def _build_memory_prompt(self, conversation_history: List[Dict[str, str]]) -> str:
        """Builds the prompt for the Memory (Thinker) LLM."""
        prompt_template = "" # Define a default empty prompt
        if path_manager.memory_agent_prompt_path.exists():
            with open(path_manager.memory_agent_prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        else:
            logger.warning(f"Memory prompt template not found at {path_manager.memory_agent_prompt_path}")

        tool_schemas = self.tool_manager.get_tool_schemas_for_agent('memory_agent')
        tool_descriptions = self._format_tool_schemas_for_prompt(tool_schemas)
        history_text = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in conversation_history])
        
        return prompt_template.format(
            tool_descriptions=tool_descriptions,
            conversation_history=history_text
        )

    def _parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        try:
            match = re.search(r'''```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\])''', response_text)
            if not match:
                logger.warning(f"No valid JSON tool call block found in response: {response_text}")
                return []
            json_str = match.group(1) or match.group(2)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse tool calls from LLM response: {e}")
            return []

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        execution_results = []
        final_response = ""
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            params = tool_call.get("params", {})
            if not tool_name:
                continue
            logger.info(f"Executing tool: {tool_name} with params: {params}")
            try:
                result = await self.tool_manager.execute_tool(tool_name, **params)
                execution_results.append({"name": tool_name, "params": params, "result": result})
                if tool_name == "speak" and result.get("status") == "success":
                    final_response = result.get("spoken_text", "")
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                execution_results.append({"name": tool_name, "params": params, "error": str(e)})
        return {"tool_executions": execution_results, "final_response": final_response}

    async def process_and_respond(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        await self.initialize()
        logger.info(f"Processing {len(messages)} messages in Actor flow.")

        for msg in messages:
            await self._append_to_history_log(path_manager.neuro_history_path, {'role': 'user', 'content': f"{msg['username']}: {msg['text']}"})

        prompt = await self._build_neuro_prompt(messages)
        response_text = await self.neuro_llm.generate(prompt)
        
        tool_calls = self._parse_tool_calls(response_text)
        processing_result = await self._execute_tool_calls(tool_calls)

        if final_response := processing_result.get("final_response", ""):
            await self._append_to_history_log(path_manager.neuro_history_path, {'role': 'assistant', 'content': final_response})

        return processing_result

    