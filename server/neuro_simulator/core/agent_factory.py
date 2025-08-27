# neuro_simulator/core/agent_factory.py
import logging

from .agent_interface import BaseAgent
from .config import config_manager, AppSettings

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

# A cache for the agent instance to avoid re-initialization
_agent_instance: BaseAgent = None

def _reset_agent_on_config_update(new_settings: AppSettings):
    global _agent_instance
    logger.info("Configuration has been updated. Resetting cached agent instance.")
    _agent_instance = None

# Register the callback to the config manager
config_manager.register_update_callback(_reset_agent_on_config_update)

async def create_agent() -> BaseAgent:
    """
    Factory function to create and initialize an agent instance based on the configuration.
    Returns a cached instance unless the configuration has changed.
    """
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance

    agent_type = config_manager.settings.agent_type
    logger.info(f"Creating new agent instance of type: {agent_type}")
    
    if agent_type == "builtin":
        from ..services.builtin import BuiltinAgentWrapper, initialize_builtin_agent
        
        agent_impl = await initialize_builtin_agent()
        
        if agent_impl is None:
            raise RuntimeError("Failed to initialize the Builtin agent implementation.")
        
        _agent_instance = BuiltinAgentWrapper(agent_impl)

    elif agent_type == "letta":
        from ..services.letta import LettaAgent
        _agent_instance = LettaAgent()
    
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

    await _agent_instance.initialize()
    
    return _agent_instance