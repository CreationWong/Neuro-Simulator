# neuro_simulator/chatbot/llm.py
"""
LLM client for the Neuro Simulator's Chatbot agent.
"""

import asyncio
import logging
from typing import Any

from google import genai
from google.genai import types
from openai import AsyncOpenAI

from ..core.config import config_manager

logger = logging.getLogger(__name__.replace("neuro_simulator", "chatbot", 1))


class ChatbotLLMClient:
    """A completely independent LLM client for the chatbot agent, with lazy initialization."""

    def __init__(self):
        self.client: Any = None
        self.model_name: str | None = None
        self._generate_func = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Initializes the client on first use."""
        if self._initialized:
            return

        logger.info("First use of Chatbot's LLMClient, performing initialization...")
        settings = config_manager.settings

        provider_id = settings.chatbot.llm_provider_id
        if not provider_id:
            raise ValueError("LLM Provider ID is not set for the chatbot.")

        provider_config = next(
            (p for p in settings.llm_providers if p.provider_id == provider_id), None
        )
        if not provider_config:
            raise ValueError(
                f"LLM Provider with ID '{provider_id}' not found in configuration."
            )

        provider_type = provider_config.provider_type.lower()
        self.model_name = provider_config.model_name

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
                f"Unsupported provider type in chatbot config: {provider_type}"
            )

        self._initialized = True
        logger.info(
            f"Chatbot LLM client initialized. Provider: {provider_type.upper()}, Model: {self.model_name}"
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
            return response.text
        except Exception as e:
            logger.error(f"Error in chatbot _generate_gemini: {e}", exc_info=True)
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
            logger.error(f"Error in chatbot _generate_openai: {e}", exc_info=True)
            return ""

    async def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text using the configured LLM, ensuring client is initialized."""
        await self._ensure_initialized()

        if not self._generate_func:
            raise RuntimeError("Chatbot LLM Client could not be initialized.")
        try:
            result = await self._generate_func(prompt, max_tokens)
            return result if result is not None else ""
        except Exception as e:
            logger.error(f"Error generating text with Chatbot LLM: {e}", exc_info=True)
            return "My brain is not working, tell Vedal to check the logs."
