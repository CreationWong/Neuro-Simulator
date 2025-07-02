# backend/chatbot.py
from pydantic import BaseModel
from google import genai
from google.genai import types
from openai import AsyncOpenAI # <-- 导入 AsyncOpenAI
import random

# 从 config 模块导入所有需要的配置
from config import (
    GEMINI_API_KEY, GEMINI_AUDIENCE_MODEL,
    OPENAI_API_KEY, OPENAI_AUDIENCE_MODEL, OPENAI_API_BASE_URL,
    AUDIENCE_LLM_PROVIDER, AUDIENCE_LLM_PROMPT
)

# --- Audience LLM 抽象接口 ---
class AudienceLLMClient:
    """Audience LLM 客户端的抽象类/接口。"""
    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        raise NotImplementedError

class GeminiAudienceLLM(AudienceLLMClient):
    """Gemini 作为 Audience LLM 的实现。"""
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
            config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=max_tokens)
        )
        
        raw_chat_text = ""
        if hasattr(response, 'text') and response.text:
            raw_chat_text = response.text
        elif response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    raw_chat_text += part.text
                else:
                    print(f"警告: 遇到无法处理的 Gemini Part 类型或结构: {type(part)} - {part}")
        
        return raw_chat_text

class OpenAIAudienceLLM(AudienceLLMClient):
    """OpenAI 兼容 API 作为 Audience LLM 的实现。"""
    def __init__(self, api_key: str, model_name: str, base_url: str | None):
        if not api_key:
            raise ValueError("OpenAI API Key is not provided for OpenAIAudienceLLM.")
        
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        print(f"已初始化 OpenAIAudienceLLM，模型: {self.model_name}，API Base: {base_url}")

    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        """使用 OpenAI 兼容的 API 生成聊天消息。"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=max_tokens,
            )
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            else:
                print("警告: OpenAI API 响应中没有找到有效的聊天内容。")
                return ""
        except Exception as e:
            print(f"调用 OpenAI 兼容 API 时出错: {e}")
            # 抛出异常或返回空字符串，让上层处理
            raise

# 根据配置获取 Audience LLM 客户端实例
def get_audience_llm_client() -> AudienceLLMClient:
    """根据配置选择并返回 Audience LLM 客户端实例。"""
    if AUDIENCE_LLM_PROVIDER == "gemini":
        return GeminiAudienceLLM(
            api_key=GEMINI_API_KEY, 
            model_name=GEMINI_AUDIENCE_MODEL
        )
    elif AUDIENCE_LLM_PROVIDER == "openai":
       return OpenAIAudienceLLM(
           api_key=OPENAI_API_KEY,
           model_name=OPENAI_AUDIENCE_MODEL,
           base_url=OPENAI_API_BASE_URL
       )
    else:
        raise ValueError(f"不支持的 AUDIENCE_LLM_PROVIDER: {AUDIENCE_LLM_PROVIDER}")

# 全局实例
audience_llm_client = get_audience_llm_client()