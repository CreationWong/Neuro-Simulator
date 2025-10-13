import yaml
import asyncio
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# --- Provider Models ---


class LLMProviderSettings(BaseModel):
    """Settings for a single LLM provider."""

    provider_id: str = Field(..., title="Provider ID", description="Automatic generated unique identifier for this provider instance.")
    display_name: str = Field(..., title="Display Name", description="User-friendly name for this provider.")
    provider_type: Literal["openai", "gemini"] = Field(..., title="Provider Type", description="The type of the provider service.")
    api_key: Optional[str] = Field(default=None, title="API Key", description="API key for authentication.")
    base_url: Optional[str] = Field(default=None, title="Base URL", description="Optional custom base URL for the API endpoint.")
    model_name: str = Field(..., title="Model Name", description="The specific model to be used (e.g., gpt-4, gemini-pro).")


class TTSProviderSettings(BaseModel):
    """Settings for a single Text-to-Speech (TTS) provider."""

    provider_id: str = Field(..., title="Provider ID", description="Automatic generated unique identifier for this provider instance.")
    display_name: str = Field(..., title="Display Name", description="User-friendly name for this provider.")
    provider_type: Literal["azure"] = Field(..., title="Provider Type", description="The type of the provider service.")
    api_key: Optional[str] = Field(default=None, title="API Key", description="API key for authentication.")
    region: Optional[str] = Field(default=None, title="Region", description="The service region for the provider (e.g., eastus).")


# --- Core Application Settings Models ---


class NeuroSettings(BaseModel):
    """Settings for the main agent (Neuro)."""

    neuro_llm_provider_id: Optional[str] = Field(default=None, title="Neuro LLM Provider ID", description="The ID of the LLM provider for Neuro's main responses.")
    neuro_memory_llm_provider_id: Optional[str] = Field(default=None, title="Neuro Memory LLM Provider ID", description="The ID of the LLM provider for Neuro's memory operations.")
    tts_provider_id: Optional[str] = Field(default=None, title="TTS Provider ID", description="The ID of the TTS provider for speech synthesis.")
    input_chat_sample_size: int = Field(10, title="Input Chat Sample Size", description="Number of recent chat messages to use as context in one turn.")
    post_speech_cooldown_sec: float = Field(1.0, title="Post-Speech Cooldown (sec)", description="Time to wait after Neuro speaks before she can speak again.")
    initial_greeting: str = Field("The stream has just started. Greet your audience and say hello!", title="Initial Greeting", format="text-area", description="The message Neuro will see when the stream first starts.")  # type: ignore[call-overload]
    neuro_input_queue_max_size: int = Field(200, title="Neuro Input Queue Max Size", description="Max number of incoming events (chats, etc.) to hold in the queue.")
    reflection_threshold: int = Field(
        5, title="Reflection Threshold", description="Number of turns before triggering memory consolidation. Set to 0 to disable."
    )


class NicknameGenerationSettings(BaseModel):
    enable_dynamic_pool: bool = Field(True, title="Enable Dynamic Pool", description="Whether to dynamically generate nicknames for viewers.")
    dynamic_pool_size: int = Field(50, title="Dynamic Pool Size", description="The number of dynamically generated nicknames to maintain.")


class ChatbotSettings(BaseModel):
    """Settings for the audience chatbot."""

    chatbot_llm_provider_id: Optional[str] = Field(default=None, title="Chatbot LLM Provider ID", description="The ID of the LLM provider for the audience-facing chatbot.")
    chatbot_memory_llm_provider_id: Optional[str] = Field(default=None, title="Chatbot Memory LLM Provider ID", description="The ID of the LLM provider for the chatbot's memory operations.")
    generation_interval_sec: int = Field(3, title="Generation Interval (sec)", description="How often (in seconds) the chatbot should try to generate a message.")
    chats_per_batch: int = Field(2, title="Chats per Batch", description="How many chat messages the chatbot should generate at once.")
    reflection_threshold: int = Field(
        50, title="Reflection Threshold", description="Number of turns before triggering memory consolidation. Set to 0 to disable."
    )
    nickname_generation: NicknameGenerationSettings = Field(default_factory=NicknameGenerationSettings, description="Settings for generating viewer nicknames.")


class StreamSettings(BaseModel):
    """Settings related to the stream's appearance."""

    streamer_nickname: str = Field("vedal987", title="Streamer Nickname", description="The nickname of the streamer.")
    stream_title: str = Field("neuro-sama is here for u all", title="Stream Title", description="The title of the stream.")
    stream_category: str = Field("谈天说地", title="Stream Category", description="The category or game being streamed.")
    stream_tags: List[str] = Field(default_factory=lambda: ["Vtuber", "AI", "Cute", "English", "Gremlin", "catgirl"], title="Stream Tags", description="Tags to associate with the stream.")


class ServerSettings(BaseModel):
    """Settings for the web server and performance."""

    host: str = Field("127.0.0.1", title="Host", description="The IP address the server will bind to.")
    port: int = Field(8000, title="Port", description="The port the server will listen on.")
    panel_password: Optional[str] = Field("your-secret-api-token-here", title="Panel Password", format="password", description="Password to protect access to the admin dashboard.")  # type: ignore[call-overload]
    client_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"], title="Client Origins", description="Allowed origins for CORS (whitelist for remote dashboard).")
    audience_chat_buffer_max_size: int = Field(1000, title="Audience Chat Buffer Max Size", description="How many recent chat messages to keep in buffer for new clients.")
    initial_chat_backlog_limit: int = Field(50, title="Initial Chat Backlog Limit", description="How many messages from buffer to send to a new client.")


class AppSettings(BaseModel):
    """Root model for all application settings."""

    llm_providers: List[LLMProviderSettings] = Field(default_factory=list, title="LLM Providers", description="Configuration for Large Language Model providers.")
    tts_providers: List[TTSProviderSettings] = Field(default_factory=list, title="TTS Providers", description="Configuration for Text-to-Speech providers.")
    neuro: NeuroSettings = Field(default_factory=NeuroSettings, title="Neuro", description="Settings for Neuro Agent.")
    chatbot: ChatbotSettings = Field(default_factory=ChatbotSettings, title="Chatbot", description="Settings for Chatbot Agent.")
    stream: StreamSettings = Field(default_factory=StreamSettings, title="Stream", description="Settings related to the stream's appearance.")
    server: ServerSettings = Field(default_factory=ServerSettings, title="Server", description="Settings for the server and performance.")


# --- Configuration Manager ---


class ConfigManager:
    """Manages loading, saving, and updating the application settings."""

    def __init__(self):
        self.file_path: Optional[str] = None
        self.settings: Optional[AppSettings] = None
        self.update_callbacks = []

    def load(self, file_path: str):
        self.file_path = file_path
        try:
            with open(self.file_path, "r") as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            data = {}
        
        self.settings = AppSettings.model_validate(data)
        # Save the settings back immediately. This auto-migrates old configs
        # and populates new ones with all default values.
        self.save_settings()

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
