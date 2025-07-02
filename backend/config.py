# backend/config.py
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# --- 用户可配置的 API 密钥和模型 ---
LETTA_API_TOKEN = os.getenv("LETTA_API_TOKEN")
LETTA_BASE_URL = os.getenv("LETTA_BASE_URL")
NEURO_AGENT_ID = os.getenv("AGENT_ID")

AUDIENCE_LLM_PROVIDER = os.getenv("AUDIENCE_LLM_PROVIDER", "gemini").lower()

# Gemini 配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_AUDIENCE_MODEL = os.getenv("GEMINI_AUDIENCE_MODEL", "gemini-1.5-flash-latest")

# OpenAI & 兼容 API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_AUDIENCE_MODEL = os.getenv("OPENAI_AUDIENCE_MODEL", "gpt-3.5-turbo")
OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL")

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# --- 用户可配置的 LLM Prompts 和初始消息 ---

# 用于生成随机聊天消息的用户名池
USERNAME_POOL = [
    "ChatterBox", "EmoteLord", "QuestionMark", "StreamFan", "PixelPundit",
    "CodeSage", "DataDiver", "ByteBard", "LogicLover", "AI_Enthusiast",
    "SynthWave", "CyberPunk", "NoSleepGang", "JustHere", "LurkMaster",
    "PogChamp", "KappaPride", "ModdedMind", "VirtualVoyager", "MatrixMind"
]

# 用于生成与 Neuro 发言相关的观众聊天的 Prompt 模板
AUDIENCE_PROMPT_TEMPLATE = """
You are a Twitch live stream viewer. Your goal is to generate short, realistic, and relevant chat messages.

The streamer, Neuro-Sama, just said the following:
---
"{neuro_speech}"
---

Based on what Neuro-Sama said, generate a variety of chat messages. Your messages should be:
- Directly reacting to her words.
- Asking follow-up questions.
- Using relevant Twitch emotes (like LUL, Pog, Kappa, etc.).
- General banter related to the topic.
- Short and punchy, like real chat messages.

Do NOT act as the streamer. Do NOT generate full conversations.
Generate around 4-5 distinct chat messages. Each message must be prefixed with a fictional username, like 'ChatterBoy: message text'.
"""

# --- 用户可配置的直播和聊天行为设置 ---
# 修改：调整为每2秒生成4-5条
AUDIENCE_CHAT_GENERATION_INTERVAL = 2  # 秒
NUM_CHATS_TO_GENERATE_PER_BATCH = 5    # 每次请求生成的聊天数量
AUDIENCE_LLM_MAX_OUTPUT_TOKENS = 300   # 减少 Token 数以匹配少量消息的需求
AUDIENCE_CHAT_BUFFER_MAX_SIZE = 500
NEURO_INPUT_QUEUE_MAX_SIZE = 200
INITIAL_CHAT_BACKLOG_LIMIT = 50

# Neuro TTS 的默认语音和音高 (可由用户调整)
AZURE_TTS_VOICE_NAME = "en-US-AshleyNeural"
AZURE_TTS_VOICE_PITCH = 1.25

# --- 应用及 WebSocket 配置 ---
BACKEND_BASE_URL = "http://127.0.0.1:8000" 
CLIENT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# --- 验证配置 ---
def validate_config():
    """验证必要的环境变量是否已设置。"""
    if not LETTA_API_TOKEN:
        raise ValueError("LETTA_API_TOKEN 环境变量未找到。")
    if not NEURO_AGENT_ID:
        raise ValueError("NEURO_AGENT_ID 环境变量未找到。")

    if AUDIENCE_LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY 未设置，观众聊天生成器可能无法工作。")
    elif AUDIENCE_LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY 未设置，观众聊天生成器可能无法工作。")

    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        print("Warning: AZURE_SPEECH_KEY 或 AZURE_SPEECH_REGION 未设置，TTS功能将无法使用。")

# 在模块加载时执行验证
validate_config()