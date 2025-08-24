# neuro_simulator/core/agent_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseAgent(ABC):
    """Abstract base class for all agents, defining a common interface for the server."""

    @abstractmethod
    async def initialize(self):
        """Initialize the agent."""
        pass

    @abstractmethod
    async def reset_memory(self):
        """Reset all types of agent memory."""
        pass

    @abstractmethod
    async def process_and_respond(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Process messages and generate a response."""
        pass

    # Memory Block Management
    @abstractmethod
    async def get_memory_blocks(self) -> List[Dict[str, Any]]:
        """Get all memory blocks."""
        pass

    @abstractmethod
    async def get_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory block by its ID."""
        pass

    @abstractmethod
    async def create_memory_block(self, title: str, description: str, content: List[str]) -> Dict[str, str]:
        """Create a new memory block."""
        pass

    @abstractmethod
    async def update_memory_block(self, block_id: str, title: Optional[str], description: Optional[str], content: Optional[List[str]]):
        """Update an existing memory block."""
        pass

    @abstractmethod
    async def delete_memory_block(self, block_id: str):
        """Delete a memory block."""
        pass

    # Init Memory Management
    @abstractmethod
    async def get_init_memory(self) -> Dict[str, Any]:
        """Get the agent's initialization memory."""
        pass

    @abstractmethod
    async def update_init_memory(self, memory: Dict[str, Any]):
        """Update the agent's initialization memory."""
        pass

    # Temp Memory Management
    @abstractmethod
    async def get_temp_memory(self) -> List[Dict[str, Any]]:
        """Get the agent's temporary memory."""
        pass

    @abstractmethod
    async def add_temp_memory(self, content: str, role: str):
        """Add an item to the agent's temporary memory."""
        pass

    @abstractmethod
    async def clear_temp_memory(self):
        """Clear the agent's temporary memory."""
        pass

    # Tool Management
    @abstractmethod
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get a list of available tools."""
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool with given parameters."""
        pass

    # Context/Message History
    @abstractmethod
    async def get_message_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the recent message history."""
        pass
