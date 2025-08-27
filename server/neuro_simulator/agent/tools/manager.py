# neuro_simulator/agent/tools/manager.py
"""The central tool manager for the agent, responsible for loading, managing, and executing tools."""

import os
import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseTool
from ..memory.manager import MemoryManager

logger = logging.getLogger(__name__.replace("neuro_simulator", "agent", 1))

class ToolManager:
    """
    Acts as a central registry and executor for all available tools.
    This manager dynamically loads tools from the 'tools' directory, making the system extensible.
    """

    def __init__(self, memory_manager: MemoryManager):
        """
        Initializes the ToolManager.
        Args:
            memory_manager: An instance of MemoryManager, passed to tools that need it.
        """
        self.memory_manager = memory_manager
        self.tools: Dict[str, BaseTool] = {}
        self._load_and_register_tools()

        # Hardcoded initial allocation of tool tags to agent types
        self.agent_tool_allocations = {
            "neuro_agent": ["communication", "memory_read"],
            "memory_agent": ["memory_write", "memory_read"]
        }
        logger.info(f"Initial tool allocations set: {self.agent_tool_allocations}")

    def _load_and_register_tools(self):
        """Dynamically scans the 'tools' directory, imports modules, and registers tool instances."""
        self.tools = {}
        tools_dir = Path(__file__).parent
        package_name = self.__module__.rsplit('.', 1)[0]

        for filename in os.listdir(tools_dir):
            if filename.endswith('.py') and not filename.startswith(('__', 'base', 'manager')):
                module_name = f".{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name, package=package_name)
                    for _, cls in inspect.getmembers(module, inspect.isclass):
                        if issubclass(cls, BaseTool) and cls is not BaseTool:
                            tool_instance = cls(memory_manager=self.memory_manager)
                            if tool_instance.name in self.tools:
                                logger.warning(f"Duplicate tool name '{tool_instance.name}' found. Overwriting.")
                            self.tools[tool_instance.name] = tool_instance
                            logger.info(f"Successfully loaded and registered tool: {tool_instance.name}")
                except Exception as e:
                    logger.error(f"Failed to load tool from {filename}: {e}", exc_info=True)

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Returns a list of serializable schemas for all registered tools.
        This is the 'API documentation' for the agent.
        """
        return [tool.get_schema() for tool in self.tools.values()]

    def get_tool_schemas_for_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Returns a list of tool schemas available to a specific agent
        based on the configured name allocations.
        """
        allowed_names = set(self.agent_tool_allocations.get(agent_name, []))
        if not allowed_names:
            return []

        return [tool.get_schema() for tool in self.tools.values() if tool.name in allowed_names]

    def reload_tools(self):
        """Forces a re-scan and registration of tools from the tools directory."""
        logger.info("Reloading tools...")
        self._load_and_register_tools()
        logger.info(f"Tools reloaded. {len(self.tools)} tools available.")

    def get_allocations(self) -> Dict[str, List[str]]:
        """Returns the current agent-to-tool-tag allocation mapping."""
        return self.agent_tool_allocations

    def set_allocations(self, allocations: Dict[str, List[str]]):
        """
        Sets a new agent-to-tool allocation mapping.

        Args:
            allocations: A dictionary mapping agent names to lists of tool names.
        """
        # Basic validation can be added here if needed
        self.agent_tool_allocations = allocations
        logger.info(f"Tool allocations updated: {self.agent_tool_allocations}")

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Executes a tool by its name with the given parameters.

        Args:
            tool_name: The name of the tool to execute.
            **kwargs: The parameters to pass to the tool's execute method.

        Returns:
            A JSON-serializable dictionary with the execution result.
        """
        if tool_name not in self.tools:
            logger.error(f"Attempted to execute non-existent tool: {tool_name}")
            return {"error": f"Tool '{tool_name}' not found."}

        tool = self.tools[tool_name]
        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}' with params {kwargs}: {e}", exc_info=True)
            return {"error": f"An unexpected error occurred while executing the tool: {str(e)}"}
