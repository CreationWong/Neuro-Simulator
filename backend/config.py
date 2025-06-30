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
AUDIENCE_MODEL_NAME = os.getenv("AUDIENCE_MODEL_NAME", "gemini-2.5-flash-lite-preview-06-17")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # 留作未来 OpenAI 支持

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# --- 用户可配置的 LLM Prompts 和初始消息 ---
# Neuro Agent 的核心系统提示词应在 Letta 平台或通过 Letta API 配置 Agent 时设定
# 这里我们只保留用于生成观众聊天的Prompt
# 以及 Neuro 首次开播时的初始消息 (作为用户消息，引导Neuro开始讲话)

# 用于生成随机聊天消息的用户名池
USERNAME_POOL = [
    "ChatterBox", "EmoteLord", "QuestionMark", "StreamFan", "PixelPundit",
    "CodeSage", "DataDiver", "ByteBard", "LogicLover", "AI_Enthusiast",
    "SynthWave", "CyberPunk", "NoSleepGang", "JustHere", "LurkMaster",
    "PogChamp", "KappaPride", "ModdedMind", "VirtualVoyager", "MatrixMind"
]

# 用于生成随机聊天消息的 Audience LLM Prompt
AUDIENCE_LLM_PROMPT = """You are a Twitch live stream viewer. Generate short, realistic chat messages as if you are watching a stream.
Your messages should be varied: questions, comments about the streamer (Neuro-Sama), emotes, general banter, or reactions to what Neuro might be saying.
Do NOT act as the streamer (Neuro-Sama). Do NOT generate full conversations or detailed replies.
Generate around 30 distinct chat messages. Each message should be prefixed with a fictional username, like 'username: message text'.
Examples:
KappaKing: LUL
ChatterBox: Is Neuro talking about the weather again?
EmoteSpammer: pog pog pog
QuestionMark: How are you doing today, Neuro?
StreamFan: Neuro-Sama you are so cool!
"""

# Neuro 首次开播时的初始消息 (作为 System / 引导性用户消息发送给 Neuro Agent)
INITIAL_NEURO_STARTUP_MESSAGE = {"username": "System", "text": "Welcome to the stream, Neuro-Sama! How are you doing today? Your audience is excited to chat with you."}

# --- 用户可配置的直播和聊天行为设置 ---
AUDIENCE_CHAT_GENERATION_INTERVAL = 10 # 秒 (每次生成聊天的间隔)
AUDIENCE_LLM_MAX_OUTPUT_TOKENS = 1500 # LLM 最大输出 Token 数 (用于观众聊天生成)
AUDIENCE_CHAT_BUFFER_MAX_SIZE = 500 # 观众聊天缓冲区最大消息数
NEURO_INPUT_QUEUE_MAX_SIZE = 200 # Neuro LLM 输入队列最大消息数
CHAT_SEND_INTERVAL = 0.5 # 秒 (前端聊天显示 WebSocket 发送消息的间隔)
NUM_CHATS_TO_SEND_PER_INTERVAL = 3 # 每次向前端发送的聊天数量
INITIAL_CHAT_BACKLOG_LIMIT = 50 # 新连接客户端发送的初始聊天历史数量

# Neuro TTS 的默认语音和音高 (可由用户调整)
AZURE_TTS_VOICE_NAME = "en-US-AshleyNeural"
AZURE_TTS_VOICE_PITCH = 1.25

# --- 应用及 WebSocket 配置 (通常由开发者设定，但也可作为配置) ---
BACKEND_BASE_URL = "http://127.0.0.1:8000" 
CLIENT_ORIGINS = [ # 允许的前端 CORS 来源
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# --- 验证配置 ---
def validate_config():
    """验证必要的环境变量是否已设置。"""
    if not LETTA_API_TOKEN:
        print("Warning: LETTA_API_TOKEN 环境变量未找到。使用一个虚拟 token 初始化 letta_client。")
    if not LETTA_BASE_URL:
        raise ValueError("LETTA_BASE_URL 环境变量未找到。请指定您的 Letta 服务器 URL (例如, http://localhost:8283)。")
    if not NEURO_AGENT_ID:
        raise ValueError("NEURO_AGENT_ID 环境变量未找到。请提供您预先创建的 Neuro Letta Agent 的 ID。")

    if AUDIENCE_LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY 环境变量未找到。Gemini Audience LLM 将无法正常运行。")
    elif AUDIENCE_LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY 环境变量未找到。OpenAI Audience LLM 将无法正常运行。")

    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        print("Warning: AZURE_SPEECH_KEY 或 AZURE_SPEECH_REGION 未找到。Azure TTS 功能将无法使用。")

# 在模块加载时执行验证
validate_config()
