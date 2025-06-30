# backend/chatbot.py
from pydantic import BaseModel
from google import genai
from google.genai import types
import random # 用于选择随机用户名

# 从 config 模块导入 Audience LLM 相关配置和 Prompt
from config import GEMINI_API_KEY, OPENAI_API_KEY, AUDIENCE_MODEL_NAME, AUDIENCE_LLM_PROVIDER, AUDIENCE_LLM_PROMPT

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
        # 优先尝试从 response.text 获取，这是纯文本响应最直接的方式
        if hasattr(response, 'text') and response.text:
            raw_chat_text = response.text
        elif response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            # 如果 response.text 不存在或为空，则遍历 parts
            for part in response.candidates[0].content.parts:
                # 确保 part 是 types.TextPart 或有 .text 属性
                if isinstance(part, types.TextPart) and part.text:
                    raw_chat_text += part.text
                elif hasattr(part, 'text') and part.text: # 兼容其他有 .text 属性的 Part 类型
                    raw_chat_text += part.text
                elif isinstance(part, tuple) and len(part) > 0 and isinstance(part[0], str):
                    # 如果 part 是一个元组，并且第一个元素是字符串，假定它是文本
                    raw_chat_text += part[0]
                else:
                    print(f"警告: 遇到无法处理的 Part 类型或结构: {type(part)} - {part}")
        
        return raw_chat_text

# class OpenAIAudienceLLM(AudienceLLMClient):
#     """OpenAI 作为 Audience LLM 的实现 (待启用)。"""
#     def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
#         if not api_key:
#             raise ValueError("OpenAI API Key is not provided for OpenAIAudienceLLM.")
#         # self.client = openai.AsyncOpenAI(api_key=api_key)
#         self.model_name = model_name
#         print(f"已初始化 OpenAIAudienceLLM，模型: {self.model_name}")

#     async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
#         # ... (占位符，待实现) ...
#         pass

# 根据配置获取 Audience LLM 客户端实例
def get_audience_llm_client() -> AudienceLLMClient:
    """根据配置选择并返回 Audience LLM 客户端实例。"""
    if AUDIENCE_LLM_PROVIDER == "gemini":
        return GeminiAudienceLLM(api_key=GEMINI_API_KEY, model_name=AUDIENCE_MODEL_NAME)
    # elif AUDIENCE_LLM_PROVIDER == "openai":
    #    return OpenAIAudienceLLM(api_key=OPENAI_API_KEY, model_name="gpt-3.5-turbo") 
    else:
        raise ValueError(f"不支持的 AUDIENCE_LLM_PROVIDER: {AUDIENCE_LLM_PROVIDER}")

# 全局实例
audience_llm_client = get_audience_llm_client()