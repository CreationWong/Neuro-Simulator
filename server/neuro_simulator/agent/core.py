# neuro_simulator/agent/core.py
"""
Core module for the Neuro Simulator's built-in agent.
"""

import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# Updated imports for the new structure
from ..utils.logging import QueueLogHandler, agent_log_queue
from ..utils.websocket import connection_manager

# --- Agent-specific imports ---
from .llm import LLMClient
from .memory.manager import MemoryManager
from .tools.core import ToolManager

# Create a logger for the agent
agent_logger = logging.getLogger("neuro_agent")
agent_logger.setLevel(logging.DEBUG)

# Configure agent logging to use the shared queue
def configure_agent_logging():
    """Configure agent logging to use the shared agent_log_queue."""
    if agent_logger.hasHandlers():
        agent_logger.handlers.clear()
    
    agent_queue_handler = QueueLogHandler(agent_log_queue)
    # Use the same format as the server for consistency
    formatter = logging.Formatter('%(asctime)s - [%(name)-24s] - %(levelname)-8s - %(message)s', datefmt='%H:%M:%S')
    agent_queue_handler.setFormatter(formatter)
    agent_logger.addHandler(agent_queue_handler)
    agent_logger.propagate = False
    agent_logger.info("Agent logging configured to use agent_log_queue.")

configure_agent_logging()

class Agent:
    """Main Agent class that integrates LLM, memory, and tools. This is the concrete implementation."""
    
    def __init__(self, working_dir: str = None):
        self.memory_manager = MemoryManager(working_dir)
        self.tool_manager = ToolManager(self.memory_manager)
        self.llm_client = LLMClient()
        self._initialized = False
        agent_logger.info("Agent instance created.")
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
        await self.memory_manager.reset_context()
        agent_logger.info("All agent memory has been reset.")
        
    async def process_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Process incoming messages and generate a response with tool usage."""
        await self.initialize()
        agent_logger.info(f"Processing {len(messages)} messages.")

        for msg in messages:
            content = f"{msg['username']}: {msg['text']}"
            await self.memory_manager.add_context_entry("user", content)
        
        context_messages = await self.memory_manager.get_recent_context()
        await connection_manager.broadcast({"type": "agent_context", "action": "update", "messages": context_messages})
        
        processing_entry_id = await self.memory_manager.add_detailed_context_entry(
            input_messages=messages, prompt="Processing started", llm_response="",
            tool_executions=[], final_response="Processing started"
        )
            
        context = await self.memory_manager.get_full_context()
        tool_descriptions = self.tool_manager.get_tool_descriptions()
        
        # --- CORRECTED HISTORY GATHERING ---
        recent_history = await self.memory_manager.get_detailed_context_history()
        assistant_responses = []
        for entry in reversed(recent_history):
            if entry.get("type") == "llm_interaction":
                for tool in entry.get("tool_executions", []):
                    if tool.get("name") == "speak" and tool.get("result"):
                        assistant_responses.append(tool["result"])

        # Create LLM prompt from template
        template_path = Path(self.memory_manager.memory_dir).parent / "prompt_template.txt"
        with open(template_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        recent_speak_history_text = "\n".join([f"- {response}" for response in assistant_responses[:5]]) if assistant_responses else "You haven't said anything yet."
        user_messages_text = "\n".join([f"{msg['username']}: {msg['text']}" for msg in messages])

        prompt = prompt_template.format(
            full_context=context,
            tool_descriptions=tool_descriptions,
            recent_speak_history=recent_speak_history_text,
            user_messages=user_messages_text
        )
        
        await self.memory_manager.add_detailed_context_entry(
            input_messages=messages, prompt=prompt, llm_response="", tool_executions=[],
            final_response="Prompt sent to LLM", entry_id=processing_entry_id
        )
        
        response_text = await self.llm_client.generate(prompt)
        agent_logger.debug(f"LLM raw response: {response_text[:100] if response_text else 'None'}...")
        
        await self.memory_manager.add_detailed_context_entry(
            input_messages=messages, prompt=prompt, llm_response=response_text, tool_executions=[],
            final_response="LLM response received", entry_id=processing_entry_id
        )
        
        processing_result = {
            "input_messages": messages, "llm_response": response_text,
            "tool_executions": [], "final_response": ""
        }
        
        if response_text:
            tool_calls = self._parse_tool_calls(response_text)
            for tool_call in tool_calls:
                agent_logger.info(f"Executing tool: {tool_call['name']}")
                await self._execute_parsed_tool(tool_call, processing_result)

        await self.memory_manager.add_detailed_context_entry(
            input_messages=messages, prompt=prompt, llm_response=response_text,
            tool_executions=processing_result["tool_executions"],
            final_response=processing_result["final_response"], entry_id=processing_entry_id
        )
            
        final_context = await self.memory_manager.get_recent_context()
        await connection_manager.broadcast({"type": "agent_context", "action": "update", "messages": final_context})
            
        agent_logger.info("Message processing completed.")
        return processing_result
        
    async def _execute_parsed_tool(self, tool_call: Dict[str, Any], processing_result: Dict[str, Any]):
        """Execute a parsed tool call and update processing result."""
        try:
            tool_result = await self.execute_tool(tool_call["name"], tool_call["params"])
            tool_call["result"] = tool_result
            if tool_call["name"] == "speak":
                processing_result["final_response"] = tool_call["params"].get("text", "")
            processing_result["tool_executions"].append(tool_call)
        except Exception as e:
            tool_call["error"] = str(e)
            processing_result["tool_executions"].append(tool_call)
            agent_logger.error(f"Error executing tool {tool_call['name']}: {e}")
            
    def _parse_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Parse tool calls using ast.literal_eval for robustness."""
        import ast
        calls = []
        text = text.strip()
        if text.startswith("speak(") and text.endswith(")"):
            try:
                # Extract the content inside speak(...)
                # e.g., "text='Hello, I'm here'"
                inner_content = text[len("speak("):-1].strip()

                # Ensure it's a text=... call
                if not inner_content.startswith("text="):
                    return []
                
                # Get the quoted string part
                quoted_string = inner_content[len("text="):
].strip()

                # Use ast.literal_eval to safely parse the Python string literal
                parsed_text = ast.literal_eval(quoted_string)
                
                if isinstance(parsed_text, str):
                    calls.append({
                        "name": "speak",
                        "params": {"text": parsed_text}
                    })

            except (ValueError, SyntaxError, TypeError) as e:
                agent_logger.warning(f"Could not parse tool call using ast.literal_eval: {text}. Error: {e}")

        return calls
        
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a registered tool."""
        await self.initialize()
        agent_logger.debug(f"Executing tool: {tool_name} with params: {params}")
        result = await self.tool_manager.execute_tool(tool_name, params)
        agent_logger.debug(f"Tool execution result: {result}")
        return result
