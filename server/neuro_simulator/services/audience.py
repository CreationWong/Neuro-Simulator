# neuro_simulator/services/audience.py
import asyncio
import logging
import random

from google import genai
from google.genai import types
from openai import AsyncOpenAI

from ..core.config import config_manager, AppSettings
from ..utils.state import app_state

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

class AudienceLLMClient:
    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        raise NotImplementedError

class GeminiAudienceLLM(AudienceLLMClient):
    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("Gemini API Key is not provided for GeminiAudienceLLM.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        logger.info(f"Initialized GeminiAudienceLLM (new SDK), model: {self.model_name}")

    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=config_manager.settings.audience_simulation.llm_temperature,
                max_output_tokens=max_tokens
            )
        )
        raw_chat_text = ""
        if hasattr(response, 'text') and response.text:
            raw_chat_text = response.text
        elif response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    raw_chat_text += part.text
        return raw_chat_text

class OpenAIAudienceLLM(AudienceLLMClient):
    def __init__(self, api_key: str, model_name: str, base_url: str | None):
        if not api_key:
            raise ValueError("OpenAI API Key is not provided for OpenAIAudienceLLM.")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        logger.info(f"Initialized OpenAIAudienceLLM, model: {self.model_name}, API Base: {base_url}")

    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=config_manager.settings.audience_simulation.llm_temperature,
            max_tokens=max_tokens,
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        return ""

async def get_dynamic_audience_prompt() -> str:
    current_neuro_speech = ""
    async with app_state.neuro_last_speech_lock:
        current_neuro_speech = app_state.neuro_last_speech

    prompt = config_manager.settings.audience_simulation.prompt_template.format(
        neuro_speech=current_neuro_speech,
        num_chats_to_generate=config_manager.settings.audience_simulation.chats_per_batch
    )
    return prompt

class AudienceChatbotManager:
    def __init__(self):
        self.client: AudienceLLMClient = self._create_client(config_manager.settings)
        self._last_checked_settings: dict = config_manager.settings.audience_simulation.model_dump()
        logger.info("AudienceChatbotManager initialized.")

    def _create_client(self, settings: AppSettings) -> AudienceLLMClient:
        provider = settings.audience_simulation.llm_provider
        logger.info(f"Creating new audience LLM client for provider: {provider}")
        if provider.lower() == "gemini":
            if not settings.api_keys.gemini_api_key:
                raise ValueError("GEMINI_API_KEY not set in config")
            return GeminiAudienceLLM(api_key=settings.api_keys.gemini_api_key, model_name=settings.audience_simulation.gemini_model)
        elif provider.lower() == "openai":
            if not settings.api_keys.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set in config")
            return OpenAIAudienceLLM(api_key=settings.api_keys.openai_api_key, model_name=settings.audience_simulation.openai_model, base_url=settings.api_keys.openai_api_base_url)
        else:
            raise ValueError(f"Unsupported AUDIENCE_LLM_PROVIDER: {provider}")

    def handle_config_update(self, new_settings: AppSettings):
        new_audience_settings = new_settings.audience_simulation.model_dump()
        if new_audience_settings != self._last_checked_settings:
            logger.info("Audience simulation settings changed, re-initializing LLM client...")
            try:
                self.client = self._create_client(new_settings)
                self._last_checked_settings = new_audience_settings
                logger.info("LLM client hot-reloaded successfully.")
            except Exception as e:
                logger.error(f"Error hot-reloading LLM client: {e}", exc_info=True)
