# backend/chatbot.py
from google import genai
from google.genai import types
from openai import AsyncOpenAI
import random
import asyncio
from config import settings # <-- 核心变化
import shared_state

class AudienceLLMClient:
    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        raise NotImplementedError

class GeminiAudienceLLM(AudienceLLMClient):
    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("Gemini API Key is not provided for GeminiAudienceLLM.")
        self.client = genai.Client(api_key=api_key) 
        self.model_name = model_name
        print(f"已初始化 GeminiAudienceLLM，模型: {self.model_name}")

    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config=types.GenerateContentConfig(
                temperature=settings.audience_simulation.llm_temperature, # <-- 修改
                max_output_tokens=max_tokens
            )
        )
        # ... (解析逻辑保持不变)
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
        print(f"已初始化 OpenAIAudienceLLM，模型: {self.model_name}，API Base: {base_url}")

    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=settings.audience_simulation.llm_temperature, # <-- 修改
            max_tokens=max_tokens,
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        return ""

async def get_dynamic_audience_prompt() -> str:
    current_neuro_speech = ""
    async with shared_state.neuro_last_speech_lock:
        current_neuro_speech = shared_state.neuro_last_speech
    
    # 使用 settings 对象中的模板和变量
    prompt = settings.audience_simulation.prompt_template.format(
        neuro_speech=current_neuro_speech,
        num_chats_to_generate=settings.audience_simulation.chats_per_batch
    )
    return prompt

def get_audience_llm_client() -> AudienceLLMClient:
    provider = settings.audience_simulation.llm_provider
    if provider.lower() == "gemini":
        if not settings.api_keys.gemini_api_key:
            raise ValueError("GEMINI_API_KEY 未在配置中设置")
        return GeminiAudienceLLM(api_key=settings.api_keys.gemini_api_key, model_name=settings.audience_simulation.gemini_model)
    elif provider.lower() == "openai":
        if not settings.api_keys.openai_api_key:
            raise ValueError("OPENAI_API_KEY 未在配置中设置")
        return OpenAIAudienceLLM(api_key=settings.api_keys.openai_api_key, model_name=settings.audience_simulation.openai_model, base_url=settings.api_keys.openai_api_base_url)
    else:
        raise ValueError(f"不支持的 AUDIENCE_LLM_PROVIDER: {provider}")

audience_llm_client = get_audience_llm_client()