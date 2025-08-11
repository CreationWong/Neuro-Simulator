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
    streamer_nickname: str
    stream_title: str
    stream_category: str
    stream_tags: List[str] = Field(default_factory=list)

class AgentSettings(BaseModel):
    """Settings for the built-in agent"""
    agent_provider: str
    agent_model: str

class NeuroBehaviorSettings(BaseModel):
    input_chat_sample_size: int
    post_speech_cooldown_sec: float
    initial_greeting: str

class AudienceSimSettings(BaseModel):
    llm_provider: str
    gemini_model: str
    openai_model: str
    llm_temperature: float
    chat_generation_interval_sec: int
    chats_per_batch: int
    max_output_tokens: int
    prompt_template: str = Field(default="")
    username_blocklist: List[str] = Field(default_factory=list)
    username_pool: List[str] = Field(default_factory=list)

class TTSSettings(BaseModel):
    voice_name: str
    voice_pitch: float

class PerformanceSettings(BaseModel):
    neuro_input_queue_max_size: int
    audience_chat_buffer_max_size: int
    initial_chat_backlog_limit: int

class ServerSettings(BaseModel):
    host: str
    port: int
    client_origins: List[str] = Field(default_factory=list)
    panel_password: Optional[str] = None

class AppSettings(BaseModel):
    api_keys: ApiKeysSettings = Field(default_factory=ApiKeysSettings)
    stream_metadata: StreamMetadataSettings
    agent_type: str  # 可选 "letta" 或 "builtin"
    agent: AgentSettings
    neuro_behavior: NeuroBehaviorSettings
    audience_simulation: AudienceSimSettings
    tts: TTSSettings
    performance: PerformanceSettings
    server: ServerSettings

# --- 2. 加载和管理配置的逻辑 ---

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
        # 首先检查当前工作目录
        config_path = "config.yaml"
        if not os.path.exists(config_path):
            # 如果当前目录没有配置文件，检查默认配置目录
            default_config_path = os.path.join(os.path.expanduser("~"), ".config", "neuro-simulator", "config.yaml")
            if os.path.exists(default_config_path):
                config_path = default_config_path
            else:
                raise FileNotFoundError("config.yaml not found in current directory or default config directory. "
                                      "Please create it from config.yaml.example.")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                if content is None:
                    raise ValueError(f"Configuration file '{config_path}' is empty.")
                return content
        except Exception as e:
            logging.error(f"Error loading or parsing {config_path}: {e}")
            raise

    def _load_settings(self) -> AppSettings:
        yaml_config = self._load_config_from_yaml()
        
        base_settings = AppSettings.model_validate(yaml_config)

        # 检查关键配置项
        if base_settings.agent_type == "letta":
            missing_keys = []
            if not base_settings.api_keys.letta_token:
                missing_keys.append("api_keys.letta_token")
            if not base_settings.api_keys.neuro_agent_id:
                missing_keys.append("api_keys.neuro_agent_id")
            
            if missing_keys:
                raise ValueError(f"Critical config missing in config.yaml for letta agent: {', '.join(missing_keys)}. "
                               f"Please check your config.yaml file against config.yaml.example.")

        logging.info("Configuration loaded successfully.")
        return base_settings

    def save_settings(self):
        """Saves the current configuration to config.yaml while preserving comments and formatting."""
        try:
            # 1. Read the existing config file as text to preserve comments and formatting
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                config_lines = f.readlines()

            # 2. Get the current settings from memory
            config_to_save = self.settings.model_dump(mode='json', exclude={'api_keys'})

            # 3. Read the existing config on disk to get the api_keys that should be preserved.
            existing_config = self._load_config_from_yaml()
            if 'api_keys' in existing_config:
                # 4. Add the preserved api_keys block back to the data to be saved.
                config_to_save['api_keys'] = existing_config['api_keys']

            # 5. Update the config lines while preserving comments and formatting
            updated_lines = self._update_config_lines(config_lines, config_to_save)

            # 6. Write the updated lines back to the file
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
                
            logging.info(f"Configuration saved to {CONFIG_FILE_PATH}")
        except Exception as e:
            logging.error(f"Failed to save configuration to {CONFIG_FILE_PATH}: {e}")

    def _update_config_lines(self, lines, config_data):
        """Updates config lines with new values while preserving comments and formatting."""
        updated_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped_line = line.strip()
            
            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith('#'):
                updated_lines.append(line)
                i += 1
                continue
            
            # Check if this line is a top-level key
            if ':' in stripped_line and not stripped_line.startswith(' ') and not stripped_line.startswith('\t'):
                key = stripped_line.split(':')[0].strip()
                if key in config_data:
                    value = config_data[key]
                    if isinstance(value, dict):
                        # Handle nested dictionaries
                        updated_lines.append(line)
                        i += 1
                        # Process nested items
                        i = self._update_nested_config_lines(lines, updated_lines, i, value, 1)
                    else:
                        # Handle simple values
                        indent = len(line) - len(line.lstrip())
                        if isinstance(value, str) and '\n' in value:
                            # Handle multiline strings
                            updated_lines.append(' ' * indent + f"{key}: |\n")
                            for subline in value.split('\n'):
                                updated_lines.append(' ' * (indent + 2) + subline + '\n')
                        elif isinstance(value, list):
                            # Handle lists
                            updated_lines.append(' ' * indent + f"{key}:\n")
                            for item in value:
                                updated_lines.append(' ' * (indent + 2) + f"- {item}\n")
                        else:
                            # Handle simple values
                            updated_lines.append(' ' * indent + f"{key}: {value}\n")
                        i += 1
                else:
                    updated_lines.append(line)
                    i += 1
            else:
                updated_lines.append(line)
                i += 1
                
        return updated_lines

    def _update_nested_config_lines(self, lines, updated_lines, start_index, config_data, depth):
        """Recursively updates nested config lines."""
        i = start_index
        indent_size = depth * 2
        
        while i < len(lines):
            line = lines[i]
            stripped_line = line.strip()
            
            # Check indentation level
            current_indent = len(line) - len(line.lstrip())
            
            # If we've moved to a less indented section, we're done with this nested block
            if current_indent < indent_size:
                break
                
            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith('#'):
                updated_lines.append(line)
                i += 1
                continue
            
            # Check if this line is a key at the current nesting level
            if current_indent == indent_size and ':' in stripped_line:
                key = stripped_line.split(':')[0].strip()
                if key in config_data:
                    value = config_data[key]
                    if isinstance(value, dict):
                        # Handle nested dictionaries
                        updated_lines.append(line)
                        i += 1
                        i = self._update_nested_config_lines(lines, updated_lines, i, value, depth + 1)
                    else:
                        # Handle simple values
                        if isinstance(value, str) and '\n' in value:
                            # Handle multiline strings
                            updated_lines.append(' ' * indent_size + f"{key}: |\n")
                            for subline in value.split('\n'):
                                updated_lines.append(' ' * (indent_size + 2) + subline + '\n')
                            i += 1
                        elif isinstance(value, list):
                            # Handle lists
                            updated_lines.append(' ' * indent_size + f"{key}:\n")
                            for item in value:
                                updated_lines.append(' ' * (indent_size + 2) + f"- {item}\n")
                            i += 1
                        else:
                            # Handle simple values
                            updated_lines.append(' ' * indent_size + f"{key}: {value}\n")
                            i += 1
                else:
                    updated_lines.append(line)
                    i += 1
            else:
                updated_lines.append(line)
                i += 1
                
        return i

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
        from .stream_manager import live_stream_manager
        await live_stream_manager.broadcast_stream_metadata()
