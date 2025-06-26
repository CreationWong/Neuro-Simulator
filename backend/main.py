import os
import base64 # 用于处理音频的base64编码
import azure.cognitiveservices.speech as speechsdk # [1]
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from letta_client import Letta, MessageCreate, TextContent, LlmConfig, AssistantMessage # [1]


# 1. 加载环境变量
load_dotenv()

LETTA_API_TOKEN = os.getenv("LETTA_API_TOKEN")
LETTA_BASE_URL = os.getenv("LETTA_BASE_URL")
AGENT_ID_CONFIG = os.getenv("AGENT_ID")
# GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY") # 暂时不需要直接使用，Letta内部处理

if not LETTA_API_TOKEN:
    print("Warning: LETTA_API_TOKEN not found in .env file. Using a dummy token for letta_client initialization.")
    LETTA_API_TOKEN = "dummy_token"

if not LETTA_BASE_URL:
    raise ValueError("LETTA_BASE_URL not found in .env file. Please specify your self-hosted Letta server URL (e.g., http://localhost:8283).")

if not AGENT_ID_CONFIG:
    raise ValueError("AGENT_ID not found in .env file. Please provide the ID of your pre-existing Agent.")

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
    print("Warning: AZURE_SPEECH_KEY or AZURE_SPEECH_REGION not found in .env. Azure TTS/STT will not be functional.")


# 2. 初始化 FastAPI 应用
app = FastAPI()

# 3. 初始化 Letta 客户端，指定你的自托管服务器URL
letta_client = Letta(token=LETTA_API_TOKEN, base_url=LETTA_BASE_URL)

@app.on_event("startup")
async def startup_event():
    """在应用启动时，确认 Agent 的存在。"""
    global AGENT_ID_CONFIG

    print(f"Using pre-existing Agent with ID: {AGENT_ID_CONFIG}")
    try:
        agent_data = letta_client.agents.retrieve(agent_id=AGENT_ID_CONFIG) # [1]
        print(f"Successfully retrieved Agent details for ID: {agent_data.id}")

        llm_model_info = "N/A"
        if hasattr(agent_data, 'model') and agent_data.model:
            llm_model_info = agent_data.model
        elif agent_data.llm_config:
            if isinstance(agent_data.llm_config, LlmConfig):
                llm_config_dict = agent_data.llm_config.model_dump() if hasattr(agent_data.llm_config, 'model_dump') else agent_data.llm_config.__dict__
                llm_model_info = llm_config_dict.get('model_name') or \
                                 llm_config_dict.get('name') or \
                                 llm_config_dict.get('model')
            if not llm_model_info:
                llm_model_info = str(agent_data.llm_config)

        print(f"Agent Name: {agent_data.name}, LLM Model: {llm_model_info}")

    except Exception as e:
        print(f"Error: Could not retrieve Agent with ID {AGENT_ID_CONFIG}. Please ensure the ID is correct and your Letta server is running and accessible.")
        print(f"Details: {e}")
        raise HTTPException(status_code=500, detail=f"Agent {AGENT_ID_CONFIG} cannot be found or accessed: {e}")

class UserMessage(BaseModel):
    text: str # 用户输入的文本消息

class AgentResponse(BaseModel):
    ai_response_text: str # AI 回复的文本
    # 后续可以添加音频或其他信息

class AudioSynthesisRequest(BaseModel):
    text: str # 需要合成的文本
    voice_name: str = Field("en-US-AshleyNeural", description="Azure TTS voice name, e.g., 'en-US-AshleyNeural'")
    pitch: float = Field(1.0, description="Pitch adjustment factor, 1.0 for normal, 1.25 for 25% higher")


@app.post("/chat")
async def chat(message: UserMessage):
    """
    接收用户文本消息，通过 Letta Agent 处理，并返回 AI 的文本回复。
    """
    try:
        response = letta_client.agents.messages.create(
            agent_id=AGENT_ID_CONFIG,
            messages=[
                MessageCreate(
                    role="user",
                    content=[
                        TextContent(text=message.text)
                    ]
                )
            ]
        )

        ai_response_text = "没有收到回复。"
        if response and response.messages:
            for msg in response.messages:
                if isinstance(msg, AssistantMessage): # 使用导入的 AssistantMessage 类型
                    if hasattr(msg, 'content') and msg.content:
                        content_items = msg.content if isinstance(msg.content, list) else [msg.content]

                        for item in content_items:
                            # 假设 content 可能是 TextContent 对象或直接的字符串
                            if isinstance(item, TextContent) and item.text:
                                ai_response_text = item.text
                                break
                            elif isinstance(item, str): # 兼容直接返回字符串的情况
                                ai_response_text = item
                                break
                    if ai_response_text != "没有收到回复。":
                        break

        return AgentResponse(ai_response_text=ai_response_text)

    except Exception as e:
        print(f"Error communicating with Agent (ID: {AGENT_ID_CONFIG}): {e}")
        raise HTTPException(status_code=500, detail=f"通信时发生错误：'{e}'")


@app.post("/synthesize_speech")
async def synthesize_speech(request: AudioSynthesisRequest):
    """
    使用 Azure TTS 将文本合成语音，支持指定语音和音调。
    返回 Base64 编码的 MP3 音频数据。
    """
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Azure Speech Key or Region not configured in .env.")

    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
        # 设置输出格式为 MP3，这里使用 16kHz 32kbps 单声道
        speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

        # 构建 SSML
        # pitch 参数是相对调整，例如 1.25 意味着 +25%
        # Calculate pitch percentage: (pitch - 1.0) * 100
        pitch_percent = int((request.pitch - 1.0) * 100)
        pitch_ssml_value = f"+{pitch_percent}%" if pitch_percent >= 0 else f"{pitch_percent}%"

        # 设置默认语音为您希望的 en-US-AshleyNeural，并应用音调
        ssml_string = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{request.voice_name}">
                <prosody pitch="{pitch_ssml_value}">
                    {request.text}
                </prosody>
            </voice>
        </speak>
        """
        
        # 使用 None 作为 audio_config 表示不直接播放，而是获取字节流
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

        result = synthesizer.speak_ssml_async(ssml_string).get() # 使用 speak_ssml_async

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio_data = result.audio_data
            encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            return {"audio_base64": encoded_audio}
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            error_message = f"Speech synthesis canceled: {cancellation_details.reason}."
            if cancellation_details.error_details:
                error_message += f" Details: {cancellation_details.error_details}"
            raise HTTPException(status_code=500, detail=error_message)
        else:
            raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {result.reason}")

    except Exception as e:
        print(f"Error during speech synthesis: {e}")
        raise HTTPException(status_code=500, detail=f"语音合成失败：'{e}'")


@app.get("/")
async def root():
    return {"message": "AI Streamer Backend is running and ready!"}
