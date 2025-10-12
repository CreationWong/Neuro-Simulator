# server/neuro_simulator/agents/llm.py
"""
Unified LLM client for all agents in the Neuro Simulator.
"""

import asyncio
import logging
from typing import Any

from google import genai
from google.genai import types
from openai import AsyncOpenAI


from ..core.config import LLMProviderSettings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    A unified, reusable LLM client.
    It is configured by passing a complete LLMProviderSettings object at creation.
    Initialization is now eager (happens in __init__).
    """

    def __init__(self, provider_config: LLMProviderSettings):
        """
        Initializes the client for a specific provider configuration.

        Args:
            provider_config: The configuration object for the LLM provider.
        """
        if not provider_config:
            raise ValueError("provider_config cannot be None.")

        self.provider_id = provider_config.provider_id
        self.client: Any = None
        self.model_name: str = provider_config.model_name
        self._generate_func = None

        logger.info(f"LLMClient instance created for provider: '{self.provider_id}'")

        provider_type = provider_config.provider_type.lower()

        if provider_type == "gemini":
            if not provider_config.api_key:
                raise ValueError(
                    f"API key for Gemini provider '{provider_config.display_name}' is not set."
                )
            self.client = genai.Client(api_key=provider_config.api_key)
            self._generate_func = self._generate_gemini

        elif provider_type == "openai":
            if not provider_config.api_key:
                raise ValueError(
                    f"API key for OpenAI provider '{provider_config.display_name}' is not set."
                )
            self.client = AsyncOpenAI(
                api_key=provider_config.api_key, base_url=provider_config.base_url
            )
            self._generate_func = self._generate_openai
        else:
            raise ValueError(
                f"Unsupported provider type in config for provider ID '{self.provider_id}': {provider_type}"
            )

        logger.info(
            f"LLM client for '{self.provider_id}' initialized. Provider: {provider_type.upper()}, Model: {self.model_name}"
        )

    async def _generate_gemini(self, prompt: str, max_tokens: int) -> str:
        """Generates text using the Gemini model."""
        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
        )
        try:
            # Run the synchronous SDK call in a thread to avoid blocking asyncio
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=generation_config,
            )
            return response.text if response and hasattr(response, "text") else ""
        except Exception as e:
            logger.error(f"Error in _generate_gemini for '{self.provider_id}': {e}", exc_info=True)
            return ""

    async def _generate_openai(self, prompt: str, max_tokens: int) -> str:
        """Generates text using the OpenAI model."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            if (
                response.choices
                and response.choices[0].message
                and response.choices[0].message.content
            ):
                return response.choices[0].message.content.strip()
            return ""
        except Exception as e:
            logger.error(f"Error in _generate_openai for '{self.provider_id}': {e}", exc_info=True)
            return ""

    async def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text using the configured LLM."""
        if not self._generate_func:
            # This should ideally not happen if __init__ is successful
            raise RuntimeError(f"LLM Client for '{self.provider_id}' could not be initialized.")
        try:
            result = await self._generate_func(prompt, max_tokens)
            return result if result is not None else ""
        except Exception as e:
            logger.error(f"Error generating text with LLM for '{self.provider_id}': {e}", exc_info=True)
            return "My brain is not working, tell Vedal to check the logs."

