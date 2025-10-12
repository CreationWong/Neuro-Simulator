import yaml
import asyncio
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# --- Provider Models ---


class LLMProviderSettings(BaseModel):
    """Settings for a single LLM provider."""

    provider_id: str = Field(..., title="Provider ID")
    display_name: str = Field(..., title="Display Name")
    provider_type: Literal["openai", "gemini"] = Field(..., title="Provider Type")
    api_key: Optional[str] = Field(default=None, title="API Key")
    base_url: Optional[str] = Field(default=None, title="Base URL")
    model_name: str = Field(..., title="Model Name")


class TTSProviderSettings(BaseModel):
    """Settings for a single Text-to-Speech (TTS) provider."""

    provider_id: str = Field(..., title="Provider ID")
    display_name: str = Field(..., title="Display Name")
    provider_type: Literal["azure"] = Field(..., title="Provider Type")
    api_key: Optional[str] = Field(default=None, title="API Key")
    region: Optional[str] = Field(default=None, title="Region")


# --- Core Application Settings Models ---


class NeuroSettings(BaseModel):
    """Settings for the main agent (Neuro)."""

    neuro_llm_provider_id: Optional[str] = Field(default=None, title="Neuro LLM Provider ID")
    neuro_memory_llm_provider_id: Optional[str] = Field(default=None, title="Neuro Memory LLM Provider ID")
    tts_provider_id: Optional[str] = Field(default=None, title="TTS Provider ID")
    input_chat_sample_size: int = Field(..., title="Input Chat Sample Size")
    post_speech_cooldown_sec: float = Field(..., title="Post-Speech Cooldown (sec)")
    initial_greeting: str = Field(..., title="Initial Greeting", format="text-area")  # type: ignore[call-overload]
    neuro_input_queue_max_size: int = Field(..., title="Neuro Input Queue Max Size")


class NicknameGenerationSettings(BaseModel):
    enable_dynamic_pool: bool = Field(..., title="Enable Dynamic Pool")
    dynamic_pool_size: int = Field(..., title="Dynamic Pool Size")


class ChatbotSettings(BaseModel):
    """Settings for the audience chatbot."""

    chatbot_llm_provider_id: Optional[str] = Field(default=None, title="Chatbot LLM Provider ID")
    chatbot_memory_llm_provider_id: Optional[str] = Field(default=None, title="Chatbot Memory LLM Provider ID")
    generation_interval_sec: int = Field(..., title="Generation Interval (sec)")
    chats_per_batch: int = Field(..., title="Chats per Batch")
    nickname_generation: NicknameGenerationSettings


class StreamSettings(BaseModel):
    """Settings related to the stream's appearance."""

    streamer_nickname: str = Field(..., title="Streamer Nickname")
    stream_title: str = Field(..., title="Stream Title")
    stream_category: str = Field(..., title="Stream Category")
    stream_tags: List[str] = Field(..., title="Stream Tags")


class ServerSettings(BaseModel):
    """Settings for the web server and performance."""

    host: str = Field(..., title="Host")
    port: int = Field(..., title="Port")
    panel_password: Optional[str] = Field(default=None, title="Panel Password", format="password")  # type: ignore[call-overload]
    client_origins: List[str] = Field(..., title="Client Origins")
    audience_chat_buffer_max_size: int = Field(..., title="Audience Chat Buffer Max Size")
    initial_chat_backlog_limit: int = Field(..., title="Initial Chat Backlog Limit")


class AppSettings(BaseModel):
    """Root model for all application settings."""

    llm_providers: List[LLMProviderSettings] = Field(..., title="LLM Providers")
    tts_providers: List[TTSProviderSettings] = Field(..., title="TTS Providers")
    neuro: NeuroSettings = Field(..., title="Neuro")
    chatbot: ChatbotSettings = Field(..., title="Chatbot")
    stream: StreamSettings = Field(..., title="Stream")
    server: ServerSettings = Field(..., title="Server")


# --- Configuration Manager ---


class ConfigManager:
    """Manages loading, saving, and updating the application settings."""

    def __init__(self):
        self.file_path: Optional[str] = None
        self.settings: Optional[AppSettings] = None
        self.update_callbacks = []

    def load(self, file_path: str):
        self.file_path = file_path
        with open(self.file_path, "r") as f:
            data = yaml.safe_load(f)
        self.settings = AppSettings.model_validate(data)

    def save_settings(self):
        if self.settings and self.file_path:
            with open(self.file_path, "w") as f:
                yaml.dump(
                    self.settings.model_dump(exclude_none=True), f, sort_keys=False
                )

    def get_settings_schema(self):
        return AppSettings.model_json_schema()

    async def update_settings(self, updated_data: dict):
        if self.settings:
            updated_model_dict = self.settings.model_dump()
            updated_model_dict.update(updated_data)

            self.settings = AppSettings.model_validate(updated_model_dict)
            self.save_settings()
            for callback in self.update_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.settings)
                else:
                    callback(self.settings)

    def register_update_callback(self, callback):
        self.update_callbacks.append(callback)


config_manager = ConfigManager()
