# neuro_simulator/chatbot/tools/base.py
"""Base classes and definitions for the chatbot tool system."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseChatbotTool(ABC):
    """
    Abstract base class for all chatbot tools.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool."""
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
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        The method that executes the tool's logic.
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """
        Returns a serializable dictionary representing the tool's public schema.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
