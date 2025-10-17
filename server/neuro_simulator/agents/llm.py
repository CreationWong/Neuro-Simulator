# server/neuro_simulator/agents/llm.py
"""
Unified LLM client for all agents in the Neuro Simulator.
"""

import asyncio
import logging
from typing import Any, Optional

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

        # Store generation parameters from config
        self.temperature = provider_config.temperature
        self.top_p = provider_config.top_p
        self.top_k = provider_config.top_k
        self.frequency_penalty = provider_config.frequency_penalty
        self.presence_penalty = provider_config.presence_penalty
        self.max_output_tokens = provider_config.max_output_tokens
        self.stop_sequences = provider_config.stop_sequences
        self.seed = provider_config.seed
        self.force_json_output = provider_config.force_json_output

        logger.debug(f"LLMClient instance created for provider: '{self.provider_id}'")

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

        logger.debug(
            f"LLM client for '{self.provider_id}' initialized. Provider: {provider_type.upper()}, Model: {self.model_name}"
        )

    async def _generate_gemini(self, prompt: str, max_tokens: int) -> str:
        """Generates text using the Gemini model."""
        
        config_params = {
            "max_output_tokens": max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "stop_sequences": self.stop_sequences,
            "seed": self.seed,
        }
        if self.force_json_output:
            config_params["response_mime_type"] = "application/json"

        # Filter out None values
        filtered_params = {k: v for k, v in config_params.items() if v is not None}
        
        generation_config = types.GenerationConfig(**filtered_params)
        
        try:
            # Run the synchronous SDK call in a thread to avoid blocking asyncio
            response = await asyncio.to_thread(
                self.client.generate_content,
                model=self.model_name,
                contents=prompt,
                generation_config=generation_config,
            )
            return response.text if response and hasattr(response, "text") else ""
        except Exception as e:
            logger.error(f"Error in _generate_gemini for '{self.provider_id}': {e}", exc_info=True)
            return ""

    async def _generate_openai(self, prompt: str, max_tokens: int) -> str:
        """Generates text using the OpenAI model."""
        
        params = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stop": self.stop_sequences,
            "seed": self.seed,
        }
        if self.force_json_output:
            params["response_format"] = {"type": "json_object"}

        # Filter out None values from params
        filtered_params = {k: v for k, v in params.items() if v is not None}

        try:
            response = await self.client.chat.completions.create(**filtered_params)
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

    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate text using the configured LLM."""
        if not self._generate_func:
            # This should ideally not happen if __init__ is successful
            raise RuntimeError(f"LLM Client for '{self.provider_id}' could not be initialized.")
        
        # Use the per-call max_tokens if provided, otherwise fall back to the configured default.
        final_max_tokens = max_tokens if max_tokens is not None else self.max_output_tokens
        if final_max_tokens is None:
            # As a last resort, provide a sensible default if neither is set.
            final_max_tokens = 2048

        try:
            result = await self._generate_func(prompt, final_max_tokens)
            return result if result is not None else ""
        except Exception as e:
            logger.error(f"Error generating text with LLM for '{self.provider_id}': {e}", exc_info=True)
            return "Someone tell Vedal there is a problem with my AI."

