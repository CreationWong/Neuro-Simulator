# backend/main.py

import os
import base64
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from letta_client import Letta, MessageCreate, TextContent, LlmConfig, AssistantMessage # Letta 客户端的导入
import asyncio # 用于异步操作,特别是 asyncio.to_thread
import re # 用于文本分割
import json # 用于处理 WebSocket 接收到的 JSON 消息

# 1. 加载环境变量
load_dotenv()

LETTA_API_TOKEN = os.getenv("LETTA_API_TOKEN")
LETTA_BASE_URL = os.getenv("LETTA_BASE_URL")
AGENT_ID_CONFIG = os.getenv("AGENT_ID")

if not LETTA_API_TOKEN:
    print("Warning: LETTA_API_TOKEN not found in .env file. Using a dummy token for letta_client initialization.")
    LETTA_API_TOKEN = "dummy_token"

if not LETTA_BASE_URL:
    raise ValueError("LETTA_BASE_URL not found in .env file. Please specify your self-hosted Letta server URL (e.g., http://localhost:8283).")

if not AGENT_ID_CONFIG:
    raise ValueError("AGENT_ID not found in .env file. Please provide the ID of your pre-existing Letta Agent.")

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
    print("Warning: AZURE_SPEECH_KEY or AZURE_SPEECH_REGION not found in .env. Azure TTS/STT will not be functional.")


# 2. 初始化 FastAPI 应用
app = FastAPI()

# 配置 CORS 中间件,允许前端跨域请求
origins = [
    "http://localhost:5173",  # Vite 开发服务器默认地址
    "http://127.0.0.1:5173",  # 另一个可能的 Vite 地址
    # 根据你的 Electron 配置,你可能还需要添加 Electron 的特殊协议，例如 "app://.", "electron://."
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 3. 初始化 Letta 客户端
letta_client = Letta(token=LETTA_API_TOKEN, base_url=LETTA_BASE_URL)

@app.on_event("startup")
async def startup_event():
    """在应用启动时,确认 Letta Agent 的存在和配置。"""
    global AGENT_ID_CONFIG

    print(f"Attempting to retrieve Letta Agent with ID: {AGENT_ID_CONFIG}")
    try:
        agent_data = letta_client.agents.retrieve(agent_id=AGENT_ID_CONFIG)
        print(f"Successfully retrieved Agent details for ID: {agent_data.id}")

        llm_model_info = "N/A"
        if hasattr(agent_data, 'model') and agent_data.model:
            llm_model_info = agent_data.model
        elif agent_data.llm_config:
            # 尝试从 llm_config 对象中获取模型名称
            if isinstance(agent_data.llm_config, LlmConfig):
                llm_config_dict = agent_data.llm_config.model_dump() if hasattr(agent_data.llm_config, 'model_dump') else agent_data.llm_config.__dict__
                llm_model_info = llm_config_dict.get('model_name') or \
                                 llm_config_dict.get('name') or \
                                 llm_config_dict.get('model')
            if not llm_model_info:
                llm_model_info = str(agent_data.llm_config) # 兜底方案

        print(f"Agent Name: {agent_data.name}, LLM Model: {llm_model_info}")

    except Exception as e:
        print(f"Error: Could not retrieve Letta Agent with ID {AGENT_ID_CONFIG}. Please ensure the ID is correct and your Letta server is running and accessible.")
        print(f"Details: {e}")
        raise HTTPException(status_code=500, detail=f"Agent {AGENT_ID_CONFIG} cannot be found or accessed: {e}")


# 辅助函数,用于将长文本分割成适合 TTS 的短句
def split_text_into_sentences(text: str) -> list[str]:
    # 尽可能保留完整的句子,避免一个句子被劈开
    # 使用正则表达式匹配句号、问号、感叹号、省略号等,并在它们后面加上空格或换行符
    # 同时处理常见的缩写,避免在缩写后分割
    sentences = re.split(r'(?<=[.!?…])\s+|\n', text)
    # 过滤空字符串,并去除每个句子的首尾空白
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

# TTS 合成辅助函数 (封装现有逻辑)
async def synthesize_audio_segment(text: str, voice_name: str, pitch: float) -> str:
    """
    将单个文本段合成音频并返回 Base64 编码的字符串。
    此函数在单独的线程中执行 Azure TTS 的同步阻塞操作。
    """
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise ValueError("Azure Speech Key or Region not configured.")

    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

    pitch_percent = int((pitch - 1.0) * 100)
    pitch_ssml_value = f"+{pitch_percent}%" if pitch_percent >= 0 else f"{pitch_percent}%"

    ssml_string = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="{voice_name}">
            <prosody pitch="{pitch_ssml_value}">
                {text}
            </prosody>
        </voice>
    </speak>
    """

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    def _perform_synthesis_sync():
        return synthesizer.speak_ssml_async(ssml_string).get()

    result = await asyncio.to_thread(_perform_synthesis_sync)

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_data = result.audio_data
        encoded_audio = base64.b64encode(audio_data).decode('utf-8')
        return encoded_audio
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        error_message = f"Speech synthesis canceled: {cancellation_details.reason}."
        if cancellation_details.error_details:
            error_message += f" Details: {cancellation_details.error_details}"
        raise Exception(error_message)
    else:
        error_details = result.error_details if hasattr(result, 'error_details') else 'N/A'
        raise Exception(f"Speech synthesis failed: {result.reason}. Error details: {error_details}")


# 新增 HTTP POST 接口，用于合成错误提示语音
class ErrorSpeechRequest(BaseModel):
    text: str # 需要合成的错误文本
    voice_name: str = "en-US-AshleyNeural"
    pitch: float = 1.25

class ErrorSpeechResponse(BaseModel):
    audio_base64: str

@app.post("/synthesize_error_speech", response_model=ErrorSpeechResponse)
async def synthesize_error_speech_endpoint(request: ErrorSpeechRequest):
    """
    通过 HTTP POST 请求合成指定错误文本的语音。
    """
    try:
        audio_base64 = await synthesize_audio_segment(
            text=request.text,
            voice_name=request.voice_name,
            pitch=request.pitch
        )
        return ErrorSpeechResponse(audio_base64=audio_base64)
    except Exception as e:
        print(f"Error synthesizing error speech: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to synthesize error speech: {e}")


@app.websocket("/ws/chat_stream") # 将路径命名为 chat_stream 更明确
async def websocket_endpoint(websocket: WebSocket):
    """
    处理前端的 WebSocket 连接,接收用户消息,与 Letta Agent 交互,
    并将 AI 回复的文本和分段音频流式发送回前端。
    """
    await websocket.accept()
    print("WebSocket client connected.")
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                parsed_data = json.loads(raw_data)
                user_message = parsed_data.get("message", "").strip()
            except json.JSONDecodeError:
                user_message = raw_data.strip() # 如果不是JSON,当作纯文本处理

            if not user_message:
                print("Received empty message, ignoring.")
                continue

            print(f"Received user message: {user_message}")

            response = letta_client.agents.messages.create(
                agent_id=AGENT_ID_CONFIG,
                messages=[
                    MessageCreate(
                        role="user",
                        content=[
                            TextContent(text=user_message)
                        ]
                    )
                ]
            )

            ai_full_response_text = "没有收到回复。"
            if response and response.messages:
                for msg in response.messages:
                    if isinstance(msg, AssistantMessage):
                        if hasattr(msg, 'content') and msg.content:
                            content_items = msg.content if isinstance(msg.content, list) else [msg.content]
                            for item in content_items:
                                if isinstance(item, TextContent) and item.text:
                                    ai_full_response_text = item.text
                                    break
                                elif isinstance(item, str):
                                    ai_full_response_text = item
                                    break
                        if ai_full_response_text != "没有收到回复。":
                            break
            
            print(f"AI full response: {ai_full_response_text}")

            sentences = split_text_into_sentences(ai_full_response_text)
            if not sentences: # 如果AI回复为空，也发送结束信号
                await websocket.send_json({"type": "end"})
                print("AI response was empty, sent end signal.")
                continue

            for i, sentence in enumerate(sentences):
                try:
                    audio_base64 = await synthesize_audio_segment(
                        text=sentence,
                        voice_name="en-US-AshleyNeural", # 指定音色
                        pitch=1.25 # 指定音调
                    )
                    await websocket.send_json({
                        "type": "segment", # 统一为 segment 类型
                        "segment_id": i,
                        "text": sentence,
                        "audio_base64": audio_base64
                    })
                    
                except Exception as e:
                    print(f"Error during TTS synthesis for segment '{sentence}': {e}")
                    await websocket.send_json({
                        "type": "error", # 使用 'error' 类型
                        "code": "TTS_SEGMENT_ERROR",
                        "message": f"TTS synthesis failed for segment: {e}",
                        "text_segment": sentence # 返回原文，方便前端显示或调试
                    })
            
            await websocket.send_json({"type": "end"})
            print("Finished sending all segments for the current response.")

    except WebSocketDisconnect:
        print("WebSocket client disconnected.")
    except Exception as e:
        import traceback
        traceback.print_exc() # 打印详细栈追踪
        print(f"An unexpected WebSocket error occurred: {e}")
        try:
            # 向前端发送一个通用错误，前端会显示 Vedal 错误并播放对应音频
            await websocket.send_json({"type": "error", "code": "GENERAL_BACKEND_ERROR", "message": f"An internal server error occurred: {e}"})
        except RuntimeError as se:
            print(f"Failed to send error message to client before closing: {se}")
    finally:
        try:
            if websocket.client_state != 3: # WebSocketState.CLOSED = 3 (from websockets library)
                await websocket.close()
                print("WebSocket connection closed.")
        except RuntimeError:
            pass # Socket already closed


@app.get("/")
async def root():
    return {"message": "AI Streamer Backend is running and ready!"}
