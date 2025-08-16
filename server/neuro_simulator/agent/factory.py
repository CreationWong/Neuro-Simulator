# agent/factory.py
"""Factory for creating agent instances"""

from .base import BaseAgent
from ..config import config_manager


async def create_agent() -> BaseAgent:
    """Create an agent instance based on the configuration"""
    agent_type = config_manager.settings.agent_type
    
    if agent_type == "builtin":
        from ..builtin_agent import local_agent, BuiltinAgentWrapper, initialize_builtin_agent
        if local_agent is None:
            # Try to initialize the builtin agent
            await initialize_builtin_agent()
            # Re-import local_agent after initialization
            from ..builtin_agent import local_agent
            if local_agent is None:
                raise RuntimeError("Failed to initialize Builtin agent")
        return BuiltinAgentWrapper(local_agent)
    elif agent_type == "letta":
        from ..letta import get_letta_agent, initialize_letta_client
        # Try to initialize the letta client
        initialize_letta_client()
        agent = get_letta_agent()
        await agent.initialize()
        return agent
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")