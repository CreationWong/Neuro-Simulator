# agent/base.py
"""Base classes for Neuro Simulator Agent"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    @abstractmethod
    async def initialize(self):
        """Initialize the agent"""
        pass
    
    @abstractmethod
    async def reset_memory(self):
        """Reset agent memory"""
        pass
    
    @abstractmethod
    async def get_response(self, chat_messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get response from the agent
        
        Args:
            chat_messages: List of message dictionaries with 'username' and 'text' keys
            
        Returns:
            Dictionary containing processing details including tool executions and final response
        """
        pass
    
    @abstractmethod
    async def process_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Process messages and generate a response
        
        Args:
            messages: List of message dictionaries with 'username' and 'text' keys
            
        Returns:
            Dictionary containing processing details including tool executions and final response
        """
        pass