# server/neuro_simulator/core/llm_manager.py
"""
Centralized manager for LLMClient instances.
Ensures that only one client instance is created for each unique LLM provider configuration.
"""

import logging
from typing import Dict, Optional

from ..agents.llm import LLMClient
from .config import AppSettings, config_manager

logger = logging.getLogger(__name__)


class _LLMManager:
    """
    Manages the lifecycle of LLMClient instances.
    This class implements a singleton pattern for LLM clients based on provider_id.
    """

    def __init__(self):
        self._clients: Dict[str, LLMClient] = {}
        logger.info("LLMManager initialized.")

    def get_client(self, provider_id: Optional[str]) -> Optional[LLMClient]:
        """
        Retrieves a shared LLMClient instance for the given provider_id.
        If the client does not exist, it creates and caches one.
        If provider_id is None or empty, returns None.

        Args:
            provider_id: The unique identifier for the LLM provider configuration.

        Returns:
            A shared LLMClient instance, or None if provider_id is not set.
            
        Raises:
            ValueError: If the provider_id is specified but not found in the configuration.
            RuntimeError: If the configuration is not loaded.
        """
        if not provider_id:
            return None

        if provider_id in self._clients:
            return self._clients[provider_id]

        logger.info(f"Creating new LLMClient for provider_id: '{provider_id}'")

        if not config_manager.settings:
            raise RuntimeError("Configuration not loaded. Cannot create LLMClient.")

        provider_config = next(
            (p for p in config_manager.settings.llm_providers if p.provider_id == provider_id),
            None,
        )

        if not provider_config:
            raise ValueError(f"LLM Provider with ID '{provider_id}' not found in configuration.")

        client = LLMClient(provider_config=provider_config)
        self._clients[provider_id] = client
        return client


# Global instance of the manager
llm_manager = _LLMManager()


def _reset_llm_clients_on_config_update(new_settings: AppSettings):
    """Resets the cached LLM clients when configuration is updated."""
    global llm_manager
    logger.info("Configuration has been updated. Resetting cached LLMClient instances.")
    llm_manager._clients.clear()


# Register the callback to the config manager
config_manager.register_update_callback(_reset_llm_clients_on_config_update)
