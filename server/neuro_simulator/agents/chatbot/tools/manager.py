# neuro_simulator/chatbot/tools/manager.py
"""
The central tool manager for the chatbot agent.
"""

import importlib
import inspect
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from ....core.path_manager import path_manager
from .base import BaseChatbotTool
from ..memory.manager import ChatbotMemoryManager

logger = logging.getLogger(__name__.replace("neuro_simulator", "chatbot", 1))


class ChatbotToolManager:
    """
    Acts as a central registry and executor for all available chatbot tools.
    """

    def __init__(self, memory_manager: ChatbotMemoryManager):
        self.memory_manager = memory_manager
        self.tools: Dict[str, BaseChatbotTool] = {}
        self.agent_tool_allocations: Dict[str, List[str]] = {}

    def load_tools(self):
        """Dynamically scans tool directories, imports modules, and registers tool instances."""
        logger.info("Loading chatbot tools...")
        self.tools = {}

        # Define paths for built-in and user-defined tools
        try:
            import pkg_resources

            builtin_tools_path_str = pkg_resources.resource_filename(
                "neuro_simulator", "agents/chatbot/tools"
            )
            builtin_tools_path = Path(builtin_tools_path_str)
        except (ModuleNotFoundError, KeyError):
            builtin_tools_path = Path(__file__).parent

        user_tools_path = path_manager.chatbot_tools_dir
        tool_paths = [builtin_tools_path, user_tools_path]

        for tools_dir in tool_paths:
            if not tools_dir.exists():
                continue

            logger.info(f"Scanning for chatbot tools in: {tools_dir}")
            for filename in os.listdir(tools_dir):
                if filename.endswith(".py") and not filename.startswith(
                    ("__", "base", "manager")
                ):
                    module_path = tools_dir / filename
                    spec = importlib.util.spec_from_file_location(
                        module_path.stem, module_path
                    )
                    if spec and spec.loader:
                        try:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            for _, cls in inspect.getmembers(module, inspect.isclass):
                                if (
                                    issubclass(cls, BaseChatbotTool)
                                    and cls is not BaseChatbotTool
                                ):
                                    tool_instance = cls(
                                        memory_manager=self.memory_manager
                                    )
                                    if tool_instance.name in self.tools:
                                        logger.warning(
                                            f"Duplicate chatbot tool name '{tool_instance.name}' found. Overwriting with version from {module_path}."
                                        )
                                    self.tools[tool_instance.name] = tool_instance
                                    logger.info(
                                        f"Successfully loaded chatbot tool: {tool_instance.name}"
                                    )
                        except Exception as e:
                            logger.error(
                                f"Failed to load chatbot tool from {module_path}: {e}",
                                exc_info=True,
                            )
        self._load_allocations()

    def _load_allocations(self):
        """Loads tool allocations from JSON files, creating defaults if they don't exist."""
        default_allocations = {
            "chatbot": ["post_chat_message"],
            "chatbot_memory_manager": [
                "add_temp_memory"
            ],  # Add more memory tools later
        }
        # Load actor agent allocations
        if path_manager.chatbot_tools_path.exists():
            with open(path_manager.chatbot_tools_path, "r", encoding="utf-8") as f:
                self.agent_tool_allocations["chatbot"] = json.load(f)
        else:
            self.agent_tool_allocations["chatbot"] = default_allocations["chatbot"]
            with open(path_manager.chatbot_tools_path, "w", encoding="utf-8") as f:
                json.dump(default_allocations["chatbot"], f, indent=2)

        # Load thinker agent allocations
        if path_manager.chatbot_memory_agent_tools_path.exists():
            with open(
                path_manager.chatbot_memory_agent_tools_path, "r", encoding="utf-8"
            ) as f:
                self.agent_tool_allocations["chatbot_memory_manager"] = json.load(f)
        else:
            self.agent_tool_allocations["chatbot_memory_manager"] = default_allocations[
                "chatbot_memory_manager"
            ]
            with open(
                path_manager.chatbot_memory_agent_tools_path, "w", encoding="utf-8"
            ) as f:
                json.dump(default_allocations["chatbot_memory_manager"], f, indent=2)

        logger.info(f"Chatbot tool allocations loaded: {self.agent_tool_allocations}")

    def get_tool_schemas_for_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """Gets the tool schemas for a specific agent based on its allocation."""
        allowed_names = set(self.agent_tool_allocations.get(agent_name, []))
        if not allowed_names:
            return []
        return [
            tool.get_schema()
            for tool in self.tools.values()
            if tool.name in allowed_names
        ]

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        if tool_name not in self.tools:
            logger.error(f"Attempted to execute non-existent chatbot tool: {tool_name}")
            return {"error": f"Tool '{tool_name}' not found."}
        tool = self.tools[tool_name]
        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.error(
                f"Error executing chatbot tool '{tool_name}' with params {kwargs}: {e}",
                exc_info=True,
            )
            return {"error": f"An unexpected error occurred: {str(e)}"}
