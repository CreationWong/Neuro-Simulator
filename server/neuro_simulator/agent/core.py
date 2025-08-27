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
from pathlib import Path
from typing import Any, Dict, List

from ..utils.logging import QueueLogHandler, agent_log_queue
from ..utils.websocket import connection_manager
from .llm import LLMClient
from .memory.manager import MemoryManager
from .tools.manager import ToolManager


# Create a logger for the agent
agent_logger = logging.getLogger("neuro_agent")
agent_logger.setLevel(logging.DEBUG)

# Configure agent logging to use the shared queue
def configure_agent_logging():
    """Configure agent logging to use the shared agent_log_queue."""
    if agent_logger.hasHandlers():
        agent_logger.handlers.clear()
    
    agent_queue_handler = QueueLogHandler(agent_log_queue)
    formatter = logging.Formatter('%(asctime)s - [%(name)-32s] - %(levelname)-8s - %(message)s', datefmt='%H:%M:%S')
    agent_queue_handler.setFormatter(formatter)
    agent_logger.addHandler(agent_queue_handler)
    agent_logger.propagate = False
    agent_logger.info("Agent logging configured to use agent_log_queue.")

configure_agent_logging()

class Agent:
    """
    Main Agent class implementing the Actor/Thinker model.
    - The "Neuro" part (Actor) handles real-time interaction.
    - The "Memory" part (Thinker) handles background memory consolidation.
    """
    
    def __init__(self, working_dir: str = None):
        self.memory_manager = MemoryManager(working_dir)
        self.tool_manager = ToolManager(self.memory_manager)
        
        # Dual LLM clients
        self.neuro_llm = LLMClient()
        self.memory_llm = LLMClient()
        
        self._initialized = False
        self.turn_counter = 0
        self.reflection_threshold = 3  # Trigger reflection every 3 turns
        
        agent_logger.info("Agent instance created with dual-LLM architecture.")
        agent_logger.debug(f"Agent working directory: {working_dir}")
        
    async def initialize(self):
        """Initialize the agent, loading any persistent memory."""
        if not self._initialized:
            agent_logger.info("Initializing agent memory manager...")
            await self.memory_manager.initialize()
            self._initialized = True
            agent_logger.info("Agent initialized successfully.")
        
    async def reset_all_memory(self):
        """Reset all agent memory types."""
        await self.memory_manager.reset_temp_memory()
        await self.memory_manager.reset_chat_history()
        agent_logger.info("All agent memory has been reset.")

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
        template_path = Path(self.memory_manager.memory_dir).parent / "neuro_prompt.txt"
        with open(template_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Gather context for Neuro Agent
        tool_schemas = self.tool_manager.get_tool_schemas_for_agent('neuro_agent')
        tool_descriptions = self._format_tool_schemas_for_prompt(tool_schemas)
        
        # Format Init Memory
        init_memory_items = self.memory_manager.init_memory or {}
        init_memory_text = "\n".join(f"{key}: {value}" for key, value in init_memory_items.items())

        # Format Core Memory from blocks
        core_memory_blocks = await self.memory_manager.get_core_memory_blocks()
        core_memory_parts = []
        if core_memory_blocks:
            for block_id, block in core_memory_blocks.items():
                core_memory_parts.append(f"\nBlock: {block.get('title', '')} ({block_id})")
                core_memory_parts.append(f"Description: {block.get('description', '')}")
                content_items = block.get("content", [])
                if content_items:
                    core_memory_parts.append("Content:")
                    for item in content_items:
                        core_memory_parts.append(f"  - {item}")
        core_memory_text = "\n".join(core_memory_parts) if core_memory_parts else "Not set."

        # Format Temp Memory
        temp_memory_items = self.memory_manager.temp_memory
        temp_memory_text = "\n".join(
            [f"[{item.get('role', 'system')}] {item.get('content', '')}" for item in temp_memory_items]
        ) if temp_memory_items else "Empty."

        recent_history = await self.memory_manager.get_recent_chat(entries=10)
        
        user_messages_text = "\n".join([f"{msg['username']}: {msg['text']}" for msg in messages])
        recent_history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_history])

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
        template_path = Path(self.memory_manager.memory_dir).parent / "memory_prompt.txt"
        with open(template_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # Gather context for Memory Agent
        tool_schemas = self.tool_manager.get_tool_schemas_for_agent('memory_agent')
        tool_descriptions = self._format_tool_schemas_for_prompt(tool_schemas)

        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        
        return prompt_template.format(
            tool_descriptions=tool_descriptions,
            conversation_history=history_text
        )

    def _parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """Parses LLM response for JSON tool calls."""
        try:
            # The LLM is prompted to return a JSON array of tool calls.
            # Find the JSON block, which might be wrapped in markdown.
            match = re.search(r'''```json\s*([\s\S]*?)\s*```|([[\][\s\S]*]])''', response_text)
            if not match:
                agent_logger.warning(f"No valid JSON tool call block found in response: {response_text}")
                return []

            json_str = match.group(1) or match.group(2)
            tool_calls = json.loads(json_str)
            
            if isinstance(tool_calls, list):
                return tool_calls
            return []
        except json.JSONDecodeError as e:
            agent_logger.error(f"Failed to decode JSON from LLM response: {e}\nResponse text: {response_text}")
            return []
        except Exception as e:
            agent_logger.error(f"An unexpected error occurred while parsing tool calls: {e}")
            return []

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Executes a list of parsed tool calls."""
        execution_results = []
        final_response = ""
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            params = tool_call.get("params", {})
            if not tool_name:
                continue

            agent_logger.info(f"Executing tool: {tool_name} with params: {params}")
            try:
                result = await self.tool_manager.execute_tool(tool_name, **params)
                execution_results.append({"name": tool_name, "params": params, "result": result})
                if tool_name == "speak" and result.get("status") == "success":
                    final_response = result.get("spoken_text", "")
            except Exception as e:
                agent_logger.error(f"Error executing tool {tool_name}: {e}")
                execution_results.append({"name": tool_name, "params": params, "error": str(e)})
        
        return {"tool_executions": execution_results, "final_response": final_response}

    async def process_and_respond(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        The main entry point for the "Neuro" (Actor) flow.
        Handles real-time interaction and triggers background reflection.
        """
        await self.initialize()
        agent_logger.info(f"Processing {len(messages)} messages in Actor flow.")

        # Add user messages to context
        for msg in messages:
            await self.memory_manager.add_chat_entry("user", f"{msg['username']}: {msg['text']}")

        # Build prompt and get response from Neuro LLM
        prompt = await self._build_neuro_prompt(messages)
        response_text = await self.neuro_llm.generate(prompt)
        agent_logger.debug(f"Neuro LLM raw response: {response_text[:150] if response_text else 'None'}...")

        # Parse and execute tools
        tool_calls = self._parse_tool_calls(response_text)
        processing_result = await self._execute_tool_calls(tool_calls)

        # Add agent's response to context
        if processing_result["final_response"]:
            await self.memory_manager.add_chat_entry("assistant", processing_result["final_response"])

        # Update dashboard/UI
        final_context = await self.memory_manager.get_recent_chat()
        # Broadcast to stream clients
        await connection_manager.broadcast({"type": "agent_context", "action": "update", "messages": final_context})
        # Broadcast to admin clients (Dashboard)
        await connection_manager.broadcast_to_admins({"type": "agent_context", "action": "update", "messages": final_context})

        # Handle reflection trigger
        self.turn_counter += 1
        if self.turn_counter >= self.reflection_threshold:
            agent_logger.info(f"Reflection threshold reached ({self.turn_counter}/{self.reflection_threshold}). Scheduling background reflection.")
            history_for_reflection = await self.memory_manager.get_recent_chat(entries=self.reflection_threshold * 2) # Get a bit more context
            asyncio.create_task(self.reflect_on_context(history_for_reflection))
            self.turn_counter = 0

        agent_logger.info("Actor flow completed.")
        return processing_result

    async def reflect_on_context(self, conversation_history: List[Dict[str, str]]):
        """
        The main entry point for the "Memory" (Thinker) flow.
        Runs in the background to consolidate memories.
        """
        agent_logger.info("Thinker flow started: Reflecting on recent context.")
        
        prompt = await self._build_memory_prompt(conversation_history)
        response_text = await self.memory_llm.generate(prompt)
        agent_logger.debug(f"Memory LLM raw response: {response_text[:150] if response_text else 'None'}...")

        tool_calls = self._parse_tool_calls(response_text)
        if not tool_calls:
            agent_logger.info("Thinker flow: No memory operations were suggested by the LLM.")
            return

        agent_logger.info(f"Thinker flow: Executing {len(tool_calls)} memory operations.")
        await self._execute_tool_calls(tool_calls)
        agent_logger.info("Thinker flow completed, memory has been updated.")
