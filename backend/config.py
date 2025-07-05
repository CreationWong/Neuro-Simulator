# backend/config.py
import os
import yaml
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

# 配置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. 定义配置的结构 (Schema) ---

class ApiKeysSettings(BaseModel):
    letta_token: Optional[str] = None
    letta_base_url: Optional[str] = None
    neuro_agent_id: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_api_base_url: Optional[str] = None
    azure_speech_key: Optional[str] = None
    azure_speech_region: Optional[str] = None

class StreamMetadataSettings(BaseModel):
    streamer_nickname: str = "vedal987"
    stream_title: str = "neuro-sama is here for u all"
    stream_category: str = "谈天说地"
    stream_tags: List[str] = Field(default_factory=lambda: ["Vtuber", "AI", "Cute", "English", "Gremlin", "catgirl"])

class NeuroBehaviorSettings(BaseModel):
    input_chat_sample_size: int = 10
    post_speech_cooldown_sec: float = 1.0
    initial_greeting: str = "The stream has just started. Greet your audience and say hello!"

class AudienceSimSettings(BaseModel):
    llm_provider: str = "gemini"
    gemini_model: str = "gemini-1.5-flash-latest"
    openai_model: str = "gpt-3.5-turbo"
    llm_temperature: float = 1.0
    chat_generation_interval_sec: int = 2
    chats_per_batch: int = 3
    max_output_tokens: int = 300
    prompt_template: str = Field(default="""
You are a Twitch live stream viewer. Your goal is to generate short, realistic, and relevant chat messages.
The streamer, Neuro-Sama, just said the following:
---
{neuro_speech}
---
Based on what Neuro-Sama said, generate a variety of chat messages. Your messages should be:
- Directly reacting to her words.
- Asking follow-up questions.
- Using relevant Twitch emotes (like LUL, Pog, Kappa, etc.).
- General banter related to the topic.
- Short and punchy, like real chat messages.
Do NOT act as the streamer. Do NOT generate full conversations.
Generate exactly {num_chats_to_generate} distinct chat messages. Each message must be prefixed with a DIFFERENT fictional username, like 'ChatterBoy: message text', 'EmoteFan: message text'.
""")
    username_blocklist: List[str] = Field(default_factory=lambda: ["ChatterBoy", "EmoteFan", "Username", "User"])
    username_pool: List[str] = Field(default_factory=lambda: [
        "ChatterBox", "EmoteLord", "QuestionMark", "StreamFan", "PixelPundit",
        "CodeSage", "DataDiver", "ByteBard", "LogicLover", "AI_Enthusiast"
    ])

class TTSSettings(BaseModel):
    voice_name: str = "en-US-AshleyNeural"
    voice_pitch: float = 1.25

class PerformanceSettings(BaseModel):
    neuro_input_queue_max_size: int = 200
    audience_chat_buffer_max_size: int = 500
    initial_chat_backlog_limit: int = 50

class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    client_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

class AppSettings(BaseModel):
    api_keys: ApiKeysSettings = Field(default_factory=ApiKeysSettings)
    stream_metadata: StreamMetadataSettings = Field(default_factory=StreamMetadataSettings)
    neuro_behavior: NeuroBehaviorSettings = Field(default_factory=NeuroBehaviorSettings)
    audience_simulation: AudienceSimSettings = Field(default_factory=AudienceSimSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

# --- 2. 加载和管理配置的逻辑 ---

CONFIG_FILE_PATH = "settings.yaml"

def _load_config_from_yaml() -> dict:
    if not os.path.exists(CONFIG_FILE_PATH):
        logging.warning(f"{CONFIG_FILE_PATH} not found. Using default settings. You can create it from settings.yaml.example.")
        return {}
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logging.error(f"Error loading or parsing {CONFIG_FILE_PATH}: {e}")
        return {}

def _load_config_from_env(settings_model: AppSettings):
    api_keys = settings_model.api_keys
    api_keys.letta_token = os.getenv("LETTA_API_TOKEN", api_keys.letta_token)
    api_keys.letta_base_url = os.getenv("LETTA_BASE_URL", api_keys.letta_base_url)
    api_keys.neuro_agent_id = os.getenv("AGENT_ID", api_keys.neuro_agent_id)
    api_keys.gemini_api_key = os.getenv("GEMINI_API_KEY", api_keys.gemini_api_key)
    api_keys.openai_api_key = os.getenv("OPENAI_API_KEY", api_keys.openai_api_key)
    api_keys.openai_api_base_url = os.getenv("OPENAI_API_BASE_URL", api_keys.openai_api_base_url)
    api_keys.azure_speech_key = os.getenv("AZURE_SPEECH_KEY", api_keys.azure_speech_key)
    api_keys.azure_speech_region = os.getenv("AZURE_SPEECH_REGION", api_keys.azure_speech_region)

def load_settings() -> AppSettings:
    yaml_config = _load_config_from_yaml()
    # Pydantic v2: 创建一个模型实例，并用字典更新它
    base_settings = AppSettings.model_validate(yaml_config)
    
    _load_config_from_env(base_settings)

    if not base_settings.api_keys.letta_token or not base_settings.api_keys.neuro_agent_id:
        raise ValueError("Critical config missing: LETTA_API_TOKEN or AGENT_ID must be set in settings.yaml or environment variables.")
        
    logging.info("Configuration loaded successfully.")
    return base_settings

def save_settings(settings_to_save: AppSettings):
    try:
        config_dict = settings_to_save.model_dump(mode='json')
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, allow_unicode=True, sort_keys=False, indent=2)
        logging.info(f"Configuration saved to {CONFIG_FILE_PATH}")
    except Exception as e:
        logging.error(f"Failed to save configuration to {CONFIG_FILE_PATH}: {e}")

# --- 3. 创建全局可访问的配置实例 ---
settings = load_settings()

# --- 4. 运行时更新配置的函数 ---
async def update_and_broadcast_settings(new_settings_data: dict):
    global settings
    # 使用 model_copy 和 update 来创建新的、更新后的配置实例
    updated_settings = settings.model_copy(update=new_settings_data, deep=True)
    settings = updated_settings
    
    save_settings(settings)
    
    # 广播需要同步的更改
    if 'stream_metadata' in new_settings_data:
        from stream_manager import live_stream_manager
        await live_stream_manager.broadcast_stream_metadata()
    
    logging.info("Runtime configuration updated.")
