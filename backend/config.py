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

# ==============================================================================
# --- Neuro-Sama 行为与节奏配置 ---
# ==============================================================================

# Neuro 从聊天队列中一次读取多少条消息作为回应的上下文
# 值越小，反应越快，但可能忽略早期信息。值越大，看得越广，但可能被旧信息干扰。
NEURO_INPUT_CHAT_SAMPLE_SIZE = 10

# Neuro 说完一整段话后，强制等待多少秒再开始下一次回应。
# 这给了观众反应的时间，调整直播节奏。
NEURO_POST_SPEECH_COOLDOWN_SEC = 1.0

# 直播开始时，Neuro 的第一句开场白。
NEURO_INITIAL_GREETING = "The stream has just started. Greet your audience and say hello!"

# ==============================================================================
# --- 观众聊天模拟配置 ---
# ==============================================================================

# 控制观众聊天生成的多样性 (LLM temperature)。
# 值越高，聊天内容越有创意/越混乱。值越低，内容越可预测/越保守。
AUDIENCE_LLM_TEMPERATURE = 1.0

# 观众聊天生成的频率（秒）
AUDIENCE_CHAT_GENERATION_INTERVAL = 2

# 每次请求生成的聊天数量。这个值会自动注入到下面的 Prompt 中。
NUM_CHATS_TO_GENERATE_PER_BATCH = 3

# 观众聊天LLM的最大输出Token
AUDIENCE_LLM_MAX_OUTPUT_TOKENS = 300

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
Generate exactly {num_chats_to_generate} distinct chat messages. Each message must be prefixed with a DIFFERENT fictional username, like 'ChatterBoy: message text', 'EmoteFan: message text'.
"""
# --- 添加一个不希望出现的用户名列表，这些将被强制替换 ---
USERNAME_BLOCKLIST = ["ChatterBoy", "EmoteFan", "Username", "User"] # 可以在这里添加 LLM 倾向于复用的用户名


# 用于生成随机聊天消息的用户名池 (当 LLM 未提供用户名时的后备)
USERNAME_POOL = [
    "ChatterBox", "EmoteLord", "QuestionMark", "StreamFan", "PixelPundit",
    "CodeSage", "DataDiver", "ByteBard", "LogicLover", "AI_Enthusiast",
    "SynthWave", "CyberPunk", "NoSleepGang", "JustHere", "LurkMaster",
    "PogChamp", "KappaPride", "ModdedMind", "VirtualVoyager", "MatrixMind"
]

# ==============================================================================
# --- 直播元数据配置 ---
# ==============================================================================
STREAM_METADATA = {
    "streamer_nickname": "vedal987",
    "stream_title": "neuro-sama is here for u all",
    "stream_category": "谈天说地",
    "stream_tags": ["Vtuber", "AI", "Cute", "English", "Gremlin", "catgirl"]
}

# ==============================================================================
# --- 数据流与性能配置 ---
# ==============================================================================

# 聊天队列和缓冲区的最大大小
AUDIENCE_CHAT_BUFFER_MAX_SIZE = 500
NEURO_INPUT_QUEUE_MAX_SIZE = 200
INITIAL_CHAT_BACKLOG_LIMIT = 50

# ==============================================================================
# --- 其他固定配置 ---
# ==============================================================================

# Neuro TTS 的默认语音和音高
AZURE_TTS_VOICE_NAME = "en-US-AshleyNeural"
AZURE_TTS_VOICE_PITCH = 1.25

# 应用及 WebSocket 配置
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