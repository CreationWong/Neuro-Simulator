# neuro_simulator/agent/tools/base.py
"""Base classes and definitions for the tool system."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Coroutine

class BaseTool(ABC):
    """
    Abstract base class for all tools.
    It defines the standard interface that all tools must implement to be discoverable and executable.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool (e.g., 'speak', 'create_core_memory_block')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A concise description of what the tool does, intended for use by an LLM."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[Dict[str, Any]]:
        """
        A list of dictionaries describing the tool's parameters.
        This follows a JSON Schema-like format.
        Example:
        return [
            {"name": "param1", "type": "string", "description": "The first parameter.", "required": True},
            {"name": "param2", "type": "integer", "description": "The second parameter.", "required": False}
        ]
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        The method that executes the tool's logic.
        It must return a JSON-serializable dictionary.
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """
        Returns a serializable dictionary representing the tool's public schema.
        This is used by the ToolManager to expose tools to agents or future external services.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
