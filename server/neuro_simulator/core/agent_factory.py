# neuro_simulator/core/agent_factory.py
import logging
from typing import Optional

from .agent_interface import BaseAgent
from .config import config_manager, AppSettings
from ..agents.neuro.core import Neuro

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

# A cache for the agent instance to avoid re-initialization
_agent_instance: Optional[BaseAgent] = None


def _reset_agent_on_config_update(new_settings: AppSettings):
    """Resets the cached agent instance when configuration is updated."""
    global _agent_instance
    logger.info("Configuration has been updated. Resetting cached agent instance.")
    _agent_instance = None


# Register the callback to the config manager
config_manager.register_update_callback(_reset_agent_on_config_update)


async def create_agent(force_recreate: bool = False) -> BaseAgent:
    """
    Factory function to create and initialize the Neuro agent instance.
    Returns a cached instance unless the configuration has changed.
    
    Args:
        force_recreate: If True, forces the recreation of the agent instance.
    """
    global _agent_instance

    if force_recreate:
        logger.info("Forcing recreation of agent instance.")
        _agent_instance = None

    if _agent_instance is not None:
        return _agent_instance

    logger.info("Creating new Neuro agent instance...")

    try:
        # Directly instantiate and initialize the Neuro agent
        agent = Neuro()
        await agent.initialize()
        _agent_instance = agent
        logger.info("New Neuro agent instance created and cached.")
        return _agent_instance
    except Exception as e:
        logger.critical(f"Failed to create and initialize Neuro agent: {e}", exc_info=True)
        # In case of failure, ensure we don't return a partially initialized object
        _agent_instance = None
        raise RuntimeError("Failed to initialize the Neuro agent.") from e