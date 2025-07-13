# backend/config.py
import os
import yaml
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import asyncio
from collections.abc import Mapping

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
    stream_tags: List[str] = Field(default_factory=lambda: ["Vtuber"])

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
    panel_password: Optional[str] = None

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

def _deep_update(source: dict, overrides: dict) -> dict:
    """
    Recursively update a dictionary.
    """
    for key, value in overrides.items():
        if isinstance(value, Mapping) and value:
            returned = _deep_update(source.get(key, {}), value)
            source[key] = returned
        else:
            source[key] = overrides[key]
    return source

class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.settings: AppSettings = self._load_settings()
        self._update_callbacks = []
        self._initialized = True

    def _load_config_from_yaml(self) -> dict:
        if not os.path.exists(CONFIG_FILE_PATH):
            logging.warning(f"{CONFIG_FILE_PATH} not found. Using default settings. You can create it from settings.yaml.example.")
            return {}
        try:
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logging.error(f"Error loading or parsing {CONFIG_FILE_PATH}: {e}")
            return {}

    def _load_config_from_env(self, settings_model: AppSettings):
        api_keys = settings_model.api_keys
        api_keys.letta_token = os.getenv("LETTA_API_TOKEN", api_keys.letta_token)
        api_keys.letta_base_url = os.getenv("LETTA_BASE_URL", api_keys.letta_base_url)
        api_keys.neuro_agent_id = os.getenv("AGENT_ID", api_keys.neuro_agent_id)
        api_keys.gemini_api_key = os.getenv("GEMINI_API_KEY", api_keys.gemini_api_key)
        api_keys.openai_api_key = os.getenv("OPENAI_API_KEY", api_keys.openai_api_key)
        api_keys.openai_api_base_url = os.getenv("OPENAI_API_BASE_URL", api_keys.openai_api_base_url)
        api_keys.azure_speech_key = os.getenv("AZURE_SPEECH_KEY", api_keys.azure_speech_key)
        api_keys.azure_speech_region = os.getenv("AZURE_SPEECH_REGION", api_keys.azure_speech_region)

    def _load_settings(self) -> AppSettings:
        yaml_config = self._load_config_from_yaml()
        base_settings = AppSettings.model_validate(yaml_config)
        self._load_config_from_env(base_settings)

        if not base_settings.api_keys.letta_token or not base_settings.api_keys.neuro_agent_id:
            raise ValueError("Critical config missing: LETTA_API_TOKEN or AGENT_ID must be set in settings.yaml or environment variables.")

        logging.info("Configuration loaded successfully.")
        return base_settings

    def save_settings(self):
        """Saves the current configuration to settings.yaml, preserving the api_keys section."""
        try:
            # 1. Get the current settings from memory, EXCLUDING api_keys
            #    to avoid saving keys loaded from environment variables.
            config_to_save = self.settings.model_dump(mode='json', exclude={'api_keys'})

            # 2. Read the existing config on disk to get the api_keys that should be preserved.
            existing_config = self._load_config_from_yaml()
            if 'api_keys' in existing_config:
                # 3. Add the preserved api_keys block back to the data to be saved.
                config_to_save['api_keys'] = existing_config['api_keys']

            # 4. Rebuild the dictionary to maintain the original order from the Pydantic model.
            final_config = {}
            for field_name in AppSettings.model_fields:
                if field_name in config_to_save:
                    final_config[field_name] = config_to_save[field_name]

            # 5. Write the final, correctly ordered configuration to the file.
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(final_config, f, allow_unicode=True, sort_keys=False, indent=2)
            logging.info(f"Configuration saved to {CONFIG_FILE_PATH}")
        except Exception as e:
            logging.error(f"Failed to save configuration to {CONFIG_FILE_PATH}: {e}")

    def register_update_callback(self, callback):
        """Registers a callback function to be called on settings update."""
        self._update_callbacks.append(callback)

    async def update_settings(self, new_settings_data: dict):
        """
        Updates the settings by merging new data, re-validating the entire
        model to ensure sub-models are correctly instantiated, and then
        notifying callbacks.
        """
        # Prevent API keys from being updated from the panel
        new_settings_data.pop('api_keys', None)

        try:
            # 1. Dump the current settings model to a dictionary.
            current_settings_dict = self.settings.model_dump()

            # 2. Recursively update the dictionary with the new data.
            updated_settings_dict = _deep_update(current_settings_dict, new_settings_data)

            # 3. Re-validate the entire dictionary back into a Pydantic model.
            #    This is the crucial step that reconstructs the sub-models.
            self.settings = AppSettings.model_validate(updated_settings_dict)
            
            # 4. Save the updated configuration to the YAML file.
            self.save_settings()
            
            # 5. Call registered callbacks with the new, valid settings model.
            for callback in self._update_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self.settings)
                    else:
                        callback(self.settings)
                except Exception as e:
                    logging.error(f"Error executing settings update callback: {e}", exc_info=True)

            logging.info("Runtime configuration updated and callbacks executed.")
        except Exception as e:
            logging.error(f"Failed to update settings: {e}", exc_info=True)


# --- 3. 创建全局可访问的配置实例 ---
config_manager = ConfigManager()

# --- 4. 运行时更新配置的函数 (legacy wrapper for compatibility) ---
async def update_and_broadcast_settings(new_settings_data: dict):
    await config_manager.update_settings(new_settings_data)
    # Broadcast stream_metadata changes specifically for now
    if 'stream_metadata' in new_settings_data:
        from stream_manager import live_stream_manager
        await live_stream_manager.broadcast_stream_metadata()
