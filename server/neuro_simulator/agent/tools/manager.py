# neuro_simulator/agent/tools/manager.py
"""The central tool manager for the agent, responsible for loading, managing, and executing tools."""

import os
import json
import importlib
import inspect
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseTool
from ..memory.manager import MemoryManager
from ...core.path_manager import path_manager

logger = logging.getLogger(__name__.replace("neuro_simulator", "agent", 1))

class ToolManager:
    """
    Acts as a central registry and executor for all available tools.
    This manager dynamically loads tools from the user's working directory.
    """

    def __init__(self, memory_manager: MemoryManager):
        if not path_manager:
            raise RuntimeError("PathManager not initialized before ToolManager.")
        self.memory_manager = memory_manager
        self.tools: Dict[str, BaseTool] = {}
        self.agent_tool_allocations: Dict[str, List[str]] = {}

        self._copy_builtin_tools()
        self.reload_tools()  # Initial load
        self._load_allocations()

    def _copy_builtin_tools(self):
        """Copies the packaged built-in tools to the working directory, overwriting existing ones."""
        try:
            import pkg_resources
            source_dir_str = pkg_resources.resource_filename('neuro_simulator', 'agent/tools')
            source_dir = Path(source_dir_str)
        except (ModuleNotFoundError, KeyError):
            source_dir = Path(__file__).parent

        dest_dir = path_manager.builtin_tools_dir
        if not dest_dir.exists():
            os.makedirs(dest_dir)

        for item in os.listdir(source_dir):
            source_item = source_dir / item
            if source_item.is_file() and source_item.name.endswith('.py') and not source_item.name.startswith(('__', 'manager')):
                shutil.copy(source_item, dest_dir / item)
        logger.info(f"Built-in tools copied to {dest_dir}")

    def _load_and_register_tools(self):
        """Dynamically scans the user tools directory, imports modules, and registers tool instances."""
        self.tools = {}
        tools_dir = path_manager.user_tools_dir
        
        for root, _, files in os.walk(tools_dir):
            for filename in files:
                if filename.endswith('.py') and not filename.startswith('__'):
                    module_path = Path(root) / filename
                    # Create a module spec from the file path
                    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
                    if spec:
                        try:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            for _, cls in inspect.getmembers(module, inspect.isclass):
                                if issubclass(cls, BaseTool) and cls is not BaseTool:
                                    tool_instance = cls(memory_manager=self.memory_manager)
                                    if tool_instance.name in self.tools:
                                        logger.warning(f"Duplicate tool name '{tool_instance.name}' found. Overwriting.")
                                    self.tools[tool_instance.name] = tool_instance
                                    logger.info(f"Successfully loaded and registered tool: {tool_instance.name}")
                        except Exception as e:
                            logger.error(f"Failed to load tool from {module_path}: {e}", exc_info=True)

    def _load_allocations(self):
        """Loads tool allocations from JSON files, creating defaults if they don't exist."""
        default_allocations = {
            "neuro_agent": ["speak", "get_core_memory_blocks", "get_core_memory_block", "model_spin", "model_zoom"],
            "memory_agent": ["add_temp_memory", "create_core_memory_block", "update_core_memory_block", "delete_core_memory_block", "add_to_core_memory_block", "remove_from_core_memory_block", "get_core_memory_blocks", "get_core_memory_block"]
        }

        # Load neuro agent allocations
        if path_manager.neuro_tools_path.exists():
            with open(path_manager.neuro_tools_path, 'r', encoding='utf-8') as f:
                self.agent_tool_allocations['neuro_agent'] = json.load(f)
        else:
            self.agent_tool_allocations['neuro_agent'] = default_allocations['neuro_agent']
            with open(path_manager.neuro_tools_path, 'w', encoding='utf-8') as f:
                json.dump(default_allocations['neuro_agent'], f, indent=2)

        # Load memory agent allocations
        if path_manager.memory_agent_tools_path.exists():
            with open(path_manager.memory_agent_tools_path, 'r', encoding='utf-8') as f:
                self.agent_tool_allocations['memory_agent'] = json.load(f)
        else:
            self.agent_tool_allocations['memory_agent'] = default_allocations['memory_agent']
            with open(path_manager.memory_agent_tools_path, 'w', encoding='utf-8') as f:
                json.dump(default_allocations['memory_agent'], f, indent=2)
        
        logger.info(f"Tool allocations loaded: {self.agent_tool_allocations}")

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        return [tool.get_schema() for tool in self.tools.values()]

    def get_tool_schemas_for_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        allowed_names = set(self.agent_tool_allocations.get(agent_name, []))
        if not allowed_names:
            return []
        return [tool.get_schema() for tool in self.tools.values() if tool.name in allowed_names]

    def reload_tools(self):
        logger.info("Reloading tools...")
        self._load_and_register_tools()
        logger.info(f"Tools reloaded. {len(self.tools)} tools available.")

    def get_allocations(self) -> Dict[str, List[str]]:
        return self.agent_tool_allocations

    def set_allocations(self, allocations: Dict[str, List[str]]):
        self.agent_tool_allocations = allocations
        # Persist the changes to the JSON files
        with open(path_manager.neuro_tools_path, 'w', encoding='utf-8') as f:
            json.dump(allocations.get('neuro_agent', []), f, indent=2)
        with open(path_manager.memory_agent_tools_path, 'w', encoding='utf-8') as f:
            json.dump(allocations.get('memory_agent', []), f, indent=2)
        logger.info(f"Tool allocations updated and saved: {self.agent_tool_allocations}")

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
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