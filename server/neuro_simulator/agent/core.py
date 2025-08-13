# agent/core.py
"""
Core module for the Neuro Simulator Agent
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import logging

# Import the shared log queue from the main log_handler
from ..log_handler import agent_log_queue, QueueLogHandler

# Create a logger for the agent
agent_logger = logging.getLogger("neuro_agent")
agent_logger.setLevel(logging.DEBUG)

# Configure agent logging to use the shared queue
def configure_agent_logging():
    """Configure agent logging to use the shared agent_log_queue"""
    # Create a handler for the agent queue
    agent_queue_handler = QueueLogHandler(agent_log_queue)
    formatter = logging.Formatter('%(asctime)s - [AGENT] - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    agent_queue_handler.setFormatter(formatter)
    
    # Clear any existing handlers
    if agent_logger.hasHandlers():
        agent_logger.handlers.clear()
    
    # Add the queue handler
    agent_logger.addHandler(agent_queue_handler)
    agent_logger.propagate = False  # Prevent logs from propagating to root logger
    
    print("Agent日志系统已配置，将日志输出到 agent_log_queue。")

# Configure agent logging when module is imported
configure_agent_logging()

class Agent:
    """Main Agent class that integrates LLM, memory, and tools"""
    
    def __init__(self, working_dir: str = None):
        # Lazy imports to avoid circular dependencies
        from .memory.manager import MemoryManager
        from .tools.core import ToolManager
        from .llm import LLMClient
        
        self.memory_manager = MemoryManager(working_dir)
        self.tool_manager = ToolManager(self.memory_manager)
        self.llm_client = LLMClient()
        self._initialized = False
        
        # Log agent initialization
        agent_logger.info("Agent initialized")
        agent_logger.debug(f"Agent working directory: {working_dir}")
        
    async def initialize(self):
        """Initialize the agent, loading any persistent memory"""
        if not self._initialized:
            agent_logger.info("Initializing agent memory manager")
            await self.memory_manager.initialize()
            self._initialized = True
            agent_logger.info("Agent initialized successfully")
        
    async def reset_all_memory(self):
        """Reset all agent memory types"""
        # Reset temp memory
        await self.memory_manager.reset_temp_memory()
        
        # Reset context (dialog history)
        await self.memory_manager.reset_context()
        
        agent_logger.info("All agent memory reset successfully")
        print("All agent memory reset successfully")
        
    async def reset_memory(self):
        """Reset agent temp memory (alias for backward compatibility)"""
        await self.reset_all_memory()
        
    async def process_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Process incoming messages and generate a response
        
        Args:
            messages: List of message dictionaries with 'username' and 'text' keys
            
        Returns:
            Dictionary containing processing details including tool executions and final response
        """
        # Ensure agent is initialized
        await self.initialize()
        
        agent_logger.info(f"Processing {len(messages)} messages")
        
        # Add messages to context
        for msg in messages:
            content = f"{msg['username']}: {msg['text']}"
            await self.memory_manager.add_context_entry("user", content)
            agent_logger.debug(f"Added message to context: {content}")
            
        # Send context update via WebSocket after adding user messages
        from ..websocket_manager import connection_manager
        context_messages = await self.memory_manager.get_recent_context()
        await connection_manager.broadcast({
            "type": "agent_context",
            "action": "update",
            "messages": context_messages
        })
        
        # Add detailed context entry for the start of processing
        processing_entry_id = await self.memory_manager.add_detailed_context_entry(
            input_messages=messages,
            prompt="Processing started",
            llm_response="",
            tool_executions=[],
            final_response="Processing started"
        )
            
        # Get full context for LLM
        context = await self.memory_manager.get_full_context()
        tool_descriptions = self.tool_manager.get_tool_descriptions()
        
        # Get last agent response to avoid repetition
        last_response = await self.memory_manager.get_last_agent_response()
        
        # Create LLM prompt with context and tools
        prompt = f"""You are {self.memory_manager.init_memory.get('name', 'Neuro-Sama')}, an AI VTuber.
Your personality: {self.memory_manager.init_memory.get('personality', 'Friendly and curious')}

=== CONTEXT ===
{context}

=== AVAILABLE TOOLS ===
{tool_descriptions}

=== INSTRUCTIONS ===
Process the user messages and respond appropriately. You can use tools to manage memory or output responses.
When you want to speak to the user, use the 'speak' tool with your response as the text parameter.
When you want to update memory, use the appropriate memory management tools.
You are fully responsible for managing your own memory. Use the memory tools proactively when you need to:
- Remember important information from the conversation
- Update your knowledge or personality
- Store observations about users or events
- Retrieve relevant information to inform your responses
Always think about whether you need to use tools before responding.

IMPORTANT GUIDELINES:
- Be creative and engaging in your responses
- Avoid repeating the same phrases or ideas from your last response: "{last_response}" (if available)
- Keep responses concise and conversational
- Maintain your character's personality

User messages:
"""
        
        for msg in messages:
            prompt += f"{msg['username']}: {msg['text']}\n"
            
        prompt += "\nYour response (use tools as needed):"
        
        agent_logger.debug("Sending prompt to LLM")
        
        # Add detailed context entry for the prompt
        await self.memory_manager.add_detailed_context_entry(
            input_messages=messages,
            prompt=prompt,
            llm_response="",
            tool_executions=[],
            final_response="Prompt sent to LLM",
            entry_id=processing_entry_id
        )
        
        # Generate response using LLM
        response = await self.llm_client.generate(prompt)
        agent_logger.debug(f"LLM response received: {response[:100] if response else 'None'}...")
        
        # Add detailed context entry for the LLM response
        await self.memory_manager.add_detailed_context_entry(
            input_messages=messages,
            prompt=prompt,
            llm_response=response,
            tool_executions=[],
            final_response="LLM response received",
            entry_id=processing_entry_id
        )
        
        # Parse the response to handle tool calls
        # This is a simplified parser - in a full implementation, you would use a more robust method
        processing_result = {
            "input_messages": messages,
            "llm_response": response,
            "tool_executions": [],
            "final_response": ""
        }
        
        # Extract tool calls from the response
        # Look for tool calls in the response
        lines = response.split('\n') if response else []
        i = 0
        json_buffer = ""  # Buffer to accumulate multi-line JSON
        in_json_block = False  # Flag to track if we're inside a JSON block
        
        while i < len(lines):
            line = lines[i].strip()
            agent_logger.debug(f"Parsing line: {line}")
            
            # Handle JSON blocks
            if line.startswith('```json'):
                in_json_block = True
                json_buffer = line + '\n'
            elif line == '```' and in_json_block:
                # End of JSON block
                json_buffer += line
                in_json_block = False
                # Process the complete JSON block
                tool_call = self._parse_tool_call(json_buffer)
                if tool_call:
                    agent_logger.info(f"Executing tool: {tool_call['name']}")
                    await self._execute_parsed_tool(tool_call, processing_result)
                    # Update detailed context entry for tool execution
                    await self.memory_manager.add_detailed_context_entry(
                        input_messages=messages,
                        prompt=prompt,
                        llm_response=response,
                        tool_executions=processing_result["tool_executions"].copy(),  # Pass a copy of current tool executions
                        final_response=f"Executed tool: {tool_call['name']}",
                        entry_id=processing_entry_id
                    )
                else:
                    agent_logger.warning(f"Failed to parse tool call from JSON block: {json_buffer}")
            elif in_json_block:
                # Accumulate lines for JSON block
                json_buffer += line + '\n'
            else:
                # Check if line contains a tool call
                if any(line.startswith(prefix) for prefix in ["get_", "create_", "update_", "delete_", "add_", "remove_", "speak("]):
                    # Parse tool call
                    tool_call = self._parse_tool_call(line)
                    if tool_call:
                        agent_logger.info(f"Executing tool: {tool_call['name']}")
                        await self._execute_parsed_tool(tool_call, processing_result)
                        # Update detailed context entry for tool execution
                        await self.memory_manager.add_detailed_context_entry(
                            input_messages=messages,
                            prompt=prompt,
                            llm_response=response,
                            tool_executions=processing_result["tool_executions"].copy(),  # Pass a copy of current tool executions
                            final_response=f"Executed tool: {tool_call['name']}",
                            entry_id=processing_entry_id
                        )
                    else:
                        agent_logger.warning(f"Failed to parse tool call from line: {line}")
            i += 1
            
        # If we're still in a JSON block at the end, process it
        if in_json_block and json_buffer:
            tool_call = self._parse_tool_call(json_buffer)
            if tool_call:
                agent_logger.info(f"Executing tool: {tool_call['name']}")
                await self._execute_parsed_tool(tool_call, processing_result)
                # Update detailed context entry for tool execution
                await self.memory_manager.add_detailed_context_entry(
                    input_messages=messages,
                    prompt=prompt,
                    llm_response=response,
                    tool_executions=processing_result["tool_executions"].copy(),  # Pass a copy of current tool executions
                    final_response=f"Executed tool: {tool_call['name']}",
                    entry_id=processing_entry_id
                )
            else:
                agent_logger.warning(f"Failed to parse tool call from incomplete JSON block: {json_buffer}")
        
        # If we have a final response, add it to context
        if processing_result["final_response"]:
            await self.memory_manager.add_context_entry("assistant", processing_result["final_response"])
            
        # Update the detailed context entry with final LLM interaction details
        await self.memory_manager.add_detailed_context_entry(
            input_messages=messages,
            prompt=prompt,
            llm_response=response,
            tool_executions=processing_result["tool_executions"],
            final_response=processing_result["final_response"],
            entry_id=processing_entry_id
        )
            
        # Send context update via WebSocket
        from ..websocket_manager import connection_manager
        context_messages = await self.memory_manager.get_recent_context()
        await connection_manager.broadcast({
            "type": "agent_context",
            "action": "update",
            "messages": context_messages
        })
            
        agent_logger.info("Message processing completed")
        return processing_result
        
    async def _execute_parsed_tool(self, tool_call: Dict[str, Any], processing_result: Dict[str, Any]):
        """Execute a parsed tool call and update processing result"""
        # Only prevent duplicate speak tool executions to avoid repeated responses
        if tool_call["name"] == "speak":
            for executed_tool in processing_result["tool_executions"]:
                if (executed_tool["name"] == "speak" and 
                    executed_tool["params"].get("text") == tool_call["params"].get("text")):
                    agent_logger.debug(f"Skipping duplicate speak tool execution: {tool_call['params'].get('text')}")
                    return
        
        # Execute the tool
        try:
            tool_result = await self.execute_tool(tool_call["name"], tool_call["params"])
            tool_call["result"] = tool_result
            
            # If this is the speak tool, capture the final response
            if tool_call["name"] == "speak":
                processing_result["final_response"] = tool_call["params"].get("text", "")
                agent_logger.info(f"Speak tool executed with text: {processing_result['final_response']}")
            else:
                agent_logger.debug(f"Tool execution result: {tool_result}")
                
            processing_result["tool_executions"].append(tool_call)
        except Exception as e:
            tool_call["error"] = str(e)
            processing_result["tool_executions"].append(tool_call)
            agent_logger.error(f"Error executing tool {tool_call['name']}: {e}")
            
    def _parse_tool_call(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a tool call from a line of text"""
        import re
        import json
        
        # First try to parse as JSON if it looks like JSON
        line = line.strip()
        if line.startswith('```json'):
            try:
                # Extract JSON content
                json_content = line[7:]  # Remove ```json
                if json_content.endswith('```'):
                    json_content = json_content[:-3]  # Remove trailing ```
                json_content = json_content.strip()
                
                # Parse the JSON
                tool_call_data = json.loads(json_content)
                
                # Handle different JSON formats
                if isinstance(tool_call_data, dict):
                    # Check if it's a tool_code format
                    if 'tool_code' in tool_call_data:
                        # Extract the tool call from tool_code
                        tool_code = tool_call_data['tool_code']
                        # Remove any wrapper functions like print()
                        tool_code = re.sub(r'^\w+\((.*)\)$', r'\1', tool_code)
                        # Now parse the tool call normally
                        pattern = r'(\w+)\((.*)\)'
                        match = re.match(pattern, tool_code)
                        if match:
                            tool_name = match.group(1)
                            params_str = match.group(2)
                            
                            # Parse parameters
                            params = {}
                            param_pattern = r'(\w+)\s*=\s*(".*?"|\'.*?\'|[^,]+?)(?:,|$)'
                            for param_match in re.finditer(param_pattern, params_str):
                                key, value = param_match.groups()
                                # Remove quotes if present
                                if (value.startswith('"') and value.endswith('"')) or \
                                   (value.startswith("'") and value.endswith("'")):
                                    value = value[1:-1]
                                params[key] = value
                                
                            return {
                                "name": tool_name,
                                "params": params
                            }
                    # Check if it's a name/arguments format
                    elif 'name' in tool_call_data and 'arguments' in tool_call_data:
                        return {
                            "name": tool_call_data['name'],
                            "params": tool_call_data['arguments']
                        }
                elif isinstance(tool_call_data, list) and len(tool_call_data) > 0:
                    # Handle array format - take the first item
                    first_item = tool_call_data[0]
                    if isinstance(first_item, dict):
                        if 'tool_code' in first_item:
                            # Extract the tool call from tool_code
                            tool_code = first_item['tool_code']
                            # Remove any wrapper functions like print()
                            tool_code = re.sub(r'^\w+\((.*)\)$', r'\1', tool_code)
                            # Now parse the tool call normally
                            pattern = r'(\w+)\((.*)\)'
                            match = re.match(pattern, tool_code)
                            if match:
                                tool_name = match.group(1)
                                params_str = match.group(2)
                                
                                # Parse parameters
                                params = {}
                                param_pattern = r'(\w+)\s*=\s*(".*?"|\'.*?\'|[^,]+?)(?:,|$)'
                                for param_match in re.finditer(param_pattern, params_str):
                                    key, value = param_match.groups()
                                    # Remove quotes if present
                                    if (value.startswith('"') and value.endswith('"')) or \
                                       (value.startswith("'") and value.endswith("'")):
                                        value = value[1:-1]
                                    params[key] = value
                                    
                                return {
                                    "name": tool_name,
                                    "params": params
                                }
                        elif 'name' in first_item and 'arguments' in first_item:
                            return {
                                "name": first_item['name'],
                                "params": first_item['arguments']
                            }
                    
            except (json.JSONDecodeError, KeyError, IndexError):
                pass  # Fall back to regex parsing
        
        # Handle multi-line JSON that might be split across several lines
        if line == '```json' or line == '{' or line == '}':
            # Skip these lines as they're part of JSON structure
            return None
            
        # Pattern to match tool_name(param1=value1, param2=value2, ...)
        pattern = r'(\w+)\((.*)\)'
        match = re.match(pattern, line)
        
        if match:
            tool_name = match.group(1)
            params_str = match.group(2)
            
            # Parse parameters more robustly
            params = {}
            
            # Handle parameters one by one
            # This handles quoted strings correctly, including special characters
            param_pattern = r'(\w+)\s*=\s*(".*?"|\'.*?\'|[^,]+?)(?:,|$)'
            for param_match in re.finditer(param_pattern, params_str):
                key, value = param_match.groups()
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                params[key] = value
                
            return {
                "name": tool_name,
                "params": params
            }
        
        return None
        
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a registered tool"""
        # Ensure agent is initialized
        await self.initialize()
        agent_logger.debug(f"Executing tool: {tool_name} with params: {params}")
        result = await self.tool_manager.execute_tool(tool_name, params)
        agent_logger.debug(f"Tool execution result: {result}")
        return result

# Function to get agent logs (now uses the shared queue)
def get_agent_logs(lines: int = 50) -> List[str]:
    """Get recent agent logs from the shared queue"""
    logs_list = list(agent_log_queue)
    return logs_list[-lines:] if len(logs_list) > lines else logs_list