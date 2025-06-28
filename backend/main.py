import os
import base64
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from letta_client import Letta, MessageCreate, TextContent, LlmConfig, AssistantMessage
import asyncio
import re
import json
import traceback
from collections import deque
import random

from google import genai
from google.genai import types 
from starlette.websockets import WebSocketState 

# 1. 加载环境变量
load_dotenv()

LETTA_API_TOKEN = os.getenv("LETTA_API_TOKEN")
LETTA_BASE_URL = os.getenv("LETTA_BASE_URL")
NEURO_AGENT_ID = os.getenv("AGENT_ID") 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
AUDIENCE_MODEL_NAME = os.getenv("AUDIENCE_MODEL_NAME", "gemini-2.5-flash-lite-preview-06-17") 

# Audience LLM 提供商配置
AUDIENCE_LLM_PROVIDER = os.getenv("AUDIENCE_LLM_PROVIDER", "gemini").lower() # 'gemini' 或 'openai'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # 用于 OpenAI 的 API 密钥

# 检查 Letta API 配置
if not LETTA_API_TOKEN:
    print("Warning: LETTA_API_TOKEN 环境变量未找到。使用一个虚拟 token 初始化 letta_client。")
    LETTA_API_TOKEN = "dummy_token"

if not LETTA_BASE_URL:
    raise ValueError("LETTA_BASE_URL 环境变量未找到。请指定您的 Letta 服务器 URL (例如, http://localhost:8283)。")

if not NEURO_AGENT_ID:
    raise ValueError("NEURO_AGENT_ID 环境变量未找到。请提供您预先创建的 Neuro Letta Agent 的 ID。")

# 检查 Audience LLM API 密钥配置
if AUDIENCE_LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY 环境变量未找到。Gemini Audience LLM 需要此密钥。")
elif AUDIENCE_LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY 环境变量未找到。OpenAI Audience LLM 将无法正常运行。")

# 检查 Azure Speech 服务配置
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
    print("Warning: AZURE_SPEECH_KEY 或 AZURE_SPEECH_REGION 环境变量未找到。Azure TTS/STT 功能将无法使用。")


# 2. 初始化 FastAPI 应用
app = FastAPI()

# 配置 CORS 中间件，允许前端访问
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 初始化 Letta 客户端 (用于 Neuro)
letta_client = Letta(token=LETTA_API_TOKEN, base_url=LETTA_BASE_URL)

# --- Audience LLM 抽象接口 ---
class AudienceLLMClient:
    """Audience LLM 客户端的抽象类/接口。"""
    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        raise NotImplementedError

class GeminiAudienceLLM(AudienceLLMClient):
    """Gemini 作为 Audience LLM 的实现。"""
    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        print(f"已初始化 GeminiAudienceLLM，模型: {self.model_name}")

    async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=max_tokens)
        )
        raw_chat_text = ""
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    raw_chat_text += part.text
        return raw_chat_text

# class OpenAIAudienceLLM(AudienceLLMClient):
#     """OpenAI 作为 Audience LLM 的实现 (待启用)。"""
#     def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
#         # 需要先安装 openai 库：pip install openai
#         # import openai
#         self.client = openai.AsyncOpenAI(api_key=api_key) # 使用 AsyncOpenAI 进行异步操作
#         self.model_name = model_name
#         print(f"已初始化 OpenAIAudienceLLM，模型: {self.model_name}")

#     async def generate_chat_messages(self, prompt: str, max_tokens: int) -> str:
#         response = await self.client.chat.completions.create(
#             model=self.model_name,
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant."}, # OpenAI 通常需要系统 Prompt
#                 {"role": "user", "content": prompt}
#             ],
#             max_tokens=max_tokens,
#             temperature=0.7
#         )
#         return response.choices[0].message.content.strip() # 确保返回文本

# 根据配置获取 Audience LLM 客户端实例
def get_audience_llm_client() -> AudienceLLMClient:
    """根据配置选择并返回 Audience LLM 客户端实例。"""
    if AUDIENCE_LLM_PROVIDER == "gemini":
        return GeminiAudienceLLM(api_key=GEMINI_API_KEY, model_name=AUDIENCE_MODEL_NAME)
    # elif AUDIENCE_LLM_PROVIDER == "openai":
    #    return OpenAIAudienceLLM(api_key=OPENAI_API_KEY, model_name="gpt-3.5-turbo") 
    else:
        raise ValueError(f"不支持的 AUDIENCE_LLM_PROVIDER: {AUDIENCE_LLM_PROVIDER}")

audience_llm_client = get_audience_llm_client()


# --- 全局队列和事件 ---
# 观众聊天消息缓冲区 (用于前端显示)
audience_chat_buffer = deque(maxlen=500) 
# Neuro LLM 的输入队列 (观众聊天和用户消息都会进入此队列)
neuro_input_queue = deque(maxlen=200) 

# 用于 Neuro TTS 的 WebSocket 连接实例
neuro_tts_websocket: WebSocket | None = None

# 用于控制 neuro_processing_task 何时运行的异步事件
neuro_tts_ready_event = asyncio.Event() 


# --- LLM Prompts (英文，供 AI 阅读) ---
NEURO_AGENT_SYSTEM_PROMPT = """You are Neuro-Sama, an AI VTuber. You are intelligent, sometimes quirky, and observant.
Your primary role is to host a live stream, interact with your audience, and maintain an engaging personality.
You will receive messages from the stream chat. These messages can be direct questions to you, comments about your stream, or general banter among viewers.
Selectively respond to or acknowledge a few recent chat messages in your replies. You do not need to reply to every single message.
Maintain your VTuber persona. Do not explicitly mention 'AI' or 'LLM' unless specifically asked.
Keep your responses concise and natural for a live stream.
"""

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

# Neuro 首次开播时的初始消息
INITIAL_NEURO_STARTUP_MESSAGE = {"username": "System", "text": "Welcome to the stream, Neuro-Sama! How are you doing today? Your audience is excited to chat with you."}

@app.on_event("startup")
async def startup_event():
    """FastAPI 应用启动时的事件处理函数。"""
    global NEURO_AGENT_ID

    print(f"尝试获取 Neuro Letta Agent，ID: {NEURO_AGENT_ID}")
    try:
        agent_data = letta_client.agents.retrieve(agent_id=NEURO_AGENT_ID)
        print(f"成功获取 Agent 详情，ID: {agent_data.id}")
        llm_model_info = "N/A"
        if hasattr(agent_data, 'model') and agent_data.model:
            llm_model_info = agent_data.model
        elif agent_data.llm_config:
            if isinstance(agent_data.llm_config, LlmConfig):
                llm_config_dict = agent_data.llm_config.model_dump() if hasattr(agent_data.llm_config, 'model_dump') else agent_data.llm_config.__dict__
                llm_model_info = llm_config_dict.get('model_name') or llm_config_dict.get('name') or llm_config_dict.get('model')
            if not llm_model_info:
                llm_model_info = str(agent_data.llm_config)
        print(f"Neuro Agent 名称: {agent_data.name}, LLM 模型: {llm_model_info}")

    except Exception as e:
        print(f"错误: 无法获取 Neuro Letta Agent (ID: {NEURO_AGENT_ID})。请确保 ID 正确，且 Letta 服务器正在运行并可访问。")
        print(f"详情: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Neuro Agent {NEURO_AGENT_ID} 无法找到或访问: {e}")
    
    # 初始化 Neuro 会话状态，但不立即触发 Neuro LLM (等待前端信号)
    await _initialize_neuro_session_state_only() 
    
    # 启动后台任务
    asyncio.create_task(generate_audience_chat_task()) # 观众聊天立即开始生成
    asyncio.create_task(neuro_processing_task()) # 此任务将等待事件触发，不会立即运行
    print("后台任务 'generate_audience_chat_task' 和 'neuro_processing_task' 已启动。")


# --- 辅助函数 ---
def split_text_into_sentences(text: str) -> list[str]:
    """将文本分割成句子。"""
    sentences = re.split(r'(?<=[.!?])(?<!Mr\.)(?<!Mrs\.)(?<!Dr\.)(?<!etc\.)\s+|$', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

async def synthesize_audio_segment(text: str, voice_name: str, pitch: float) -> str:
    """使用 Azure TTS 合成音频。"""
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise ValueError("Azure Speech Key 或 Region 未配置。")

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

    # 在单独的线程中执行同步的 TTS 操作，避免阻塞事件循环
    def _perform_synthesis_sync():
        return synthesizer.speak_ssml_async(ssml_string).get()

    result = await asyncio.to_thread(_perform_synthesis_sync)

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_data = result.audio_data
        encoded_audio = base64.b64encode(audio_data).decode('utf-8')
        return encoded_audio
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        error_message = f"语音合成取消: {cancellation_details.reason}。"
        if cancellation_details.error_details:
            error_message += f" 详情: {cancellation_details.error_details}"
        raise Exception(error_message)
    else:
        error_details = result.error_details if hasattr(result, 'error_details') else 'N/A'
        raise Exception(f"语音合成失败: {result.reason}。错误详情: {error_details}")


# --- HTTP 端点 ---
class ErrorSpeechRequest(BaseModel):
    text: str
    voice_name: str = "en-US-AshleyNeural"
    pitch: float = 1.25

class ErrorSpeechResponse(BaseModel):
    audio_base64: str

@app.post("/synthesize_error_speech", response_model=ErrorSpeechResponse)
async def synthesize_error_speech_endpoint(request: ErrorSpeechRequest):
    """通过 HTTP POST 合成特定错误消息的语音。"""
    try:
        audio_base64 = await synthesize_audio_segment(
            text=request.text,
            voice_name=request.voice_name,
            pitch=request.pitch
        )
        return ErrorSpeechResponse(audio_base64=audio_base64)
    except Exception as e:
        print(f"合成错误语音时出错: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"无法合成错误语音: {e}")

@app.post("/reset_agent_messages", status_code=status.HTTP_200_OK)
async def reset_agent_messages():
    """重置 Neuro 的会话 (记忆、队列) 并为新的直播开始做准备。"""
    print(f"尝试重置 Neuro Agent 的消息，ID: {NEURO_AGENT_ID}")
    try:
        # 仅重置状态，前端将处理视频播放并触发首次启动
        await _initialize_neuro_session_state_only() 
        return {"message": f"Neuro Agent {NEURO_AGENT_ID} 的消息已成功重置，所有聊天队列已清空。"}
    except Exception as e:
        print(f"重置 Neuro Agent 消息时出错 (ID: {NEURO_AGENT_ID}): {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"无法重置 Neuro Agent 消息: {e}")

@app.get("/")
async def root():
    """根路径，返回后端状态消息。"""
    return {"message": "AI 主播后端正在运行并已就绪！"}

# --- 观众聊天生成后台任务 ---
async def generate_audience_chat_task():
    """
    后台任务，持续生成观众聊天消息，并将其添加到 audience_chat_buffer 和 neuro_input_queue。
    """
    username_pool = [
        "ChatterBox", "EmoteLord", "QuestionMark", "StreamFan", "PixelPundit",
        "CodeSage", "DataDiver", "ByteBard", "LogicLover", "AI_Enthusiast",
        "SynthWave", "CyberPunk", "NoSleepGang", "JustHere", "LurkMaster",
        "PogChamp", "KappaPride", "ModdedMind", "VirtualVoyager", "MatrixMind"
    ]
    
    chat_generation_interval = 10 # 秒 (每次生成聊天的间隔)
    llm_max_output_tokens = 1500 # LLM 最大输出 Token 数 (约 30 条消息 * 50 tokens/消息)

    while True:
        try:
            # 使用选定的 Audience LLM 客户端生成聊天消息
            raw_chat_text = await audience_llm_client.generate_chat_messages(
                prompt=AUDIENCE_LLM_PROMPT,
                max_tokens=llm_max_output_tokens
            )
            
            parsed_chats = []
            for line in raw_chat_text.split('\n'):
                line = line.strip()
                if ':' in line:
                    username_part, text_part = line.split(':', 1)
                    username = username_part.strip()
                    text = text_part.strip()
                    if username and text:
                        parsed_chats.append({"username": username, "text": text})
                elif line: # 处理没有冒号分隔的行，分配随机用户名
                    random_username = username_pool[random.randrange(len(username_pool))] # 更随机地选择用户名
                    parsed_chats.append({"username": random_username, "text": line})

            actual_generated_count = 0
            # 限制最多添加 30 条聊天消息
            for chat in parsed_chats[:30]: 
                audience_chat_buffer.append(chat)
                neuro_input_queue.append(chat)
                actual_generated_count += 1
            
            print(f"已生成 {actual_generated_count} 条观众聊天。观众缓冲区大小: {len(audience_chat_buffer)}。Neuro 输入队列大小: {len(neuro_input_queue)}")

        except Exception as e:
            print(f"生成观众聊天时出错: {e}")
            traceback.print_exc()
        
        await asyncio.sleep(chat_generation_interval)

# --- Neuro 处理后台任务及初始化函数 ---

def _trigger_neuro_response_flow():
    """设置事件，允许 neuro_processing_task 继续执行。"""
    if not neuro_tts_ready_event.is_set():
        neuro_tts_ready_event.set()
        print("已触发 Neuro 响应流程 (neuro_tts_ready_event 已设置)。")

async def _initialize_neuro_session_state_only():
    """
    初始化 Neuro 的会话状态：重置记忆并清空队列。
    不触发 Neuro LLM 处理。
    在应用启动时和重置端点调用。
    """
    print("正在初始化 Neuro 会话状态 (无即时触发)...")
    audience_chat_buffer.clear()
    neuro_input_queue.clear()
    neuro_tts_ready_event.clear() # 确保事件被清除，以便 neuro_processing_task 等待
    try:
        letta_client.agents.messages.reset(agent_id=NEURO_AGENT_ID)
        print(f"Neuro Agent {NEURO_AGENT_ID} 记忆已重置。")
    except Exception as e:
        print(f"警告: 重置 Neuro Agent 记忆失败: {e}。它可能保留了之前的上下文。")
    


async def _trigger_neuro_initial_response():
    """
    将初始消息添加到 Neuro 的队列并触发其首次响应。
    由前端在视频播放后调用。
    """
    print("正在触发 Neuro 的首次响应 (视频播放后)...")
    # 将初始提示添加到 Neuro 的输入队列
    neuro_input_queue.append(INITIAL_NEURO_STARTUP_MESSAGE)
    print("已将初始提示添加到 Neuro 输入队列，用于首次响应。")
    
    _trigger_neuro_response_flow()


async def neuro_processing_task():
    """
    后台任务，持续检查 neuro_input_queue，
    在 TTS 就绪时使用 Neuro LLM 处理消息，并将响应发送到前端。
    """
    neuro_processing_interval = 0.5 # 每 0.5 秒检查队列
    chats_to_process_per_turn = 50 # 每次处理从队列中随机抽取的聊天数量

    while True:
        # 等待 Neuro 的 TTS 完成 (由前端确认) 或来自前端的首次触发
        await neuro_tts_ready_event.wait() 
        
        # 立即清除事件，以防止在新的 TTS 完成之前再次触发
        neuro_tts_ready_event.clear() 

        # 给 Neuro 一个短暂的休息/思考时间
        await asyncio.sleep(1) 

        # 如果队列为空，则等待一段时间，让消息积累，然后进入下一个处理周期
        if not neuro_input_queue:
            print(f"Neuro 输入队列为空。等待 {neuro_processing_interval} 秒以获取更多聊天。")
            await asyncio.sleep(neuro_processing_interval)
            _trigger_neuro_response_flow() # 重新设置事件以允许再次检查
            continue
        
        # --- 为 Neuro LLM 准备输入 ---
        current_queue_snapshot = list(neuro_input_queue)
        num_to_sample = min(chats_to_process_per_turn, len(current_queue_snapshot))
        
        if num_to_sample == 0:
            print("尽管队列有消息，但没有足够的消息可供 Neuro 采样 (可能是最小/最大问题？)。正在等待。")
            await asyncio.sleep(neuro_processing_interval)
            _trigger_neuro_response_flow() # 允许重试
            continue

        selected_chats_for_neuro = random.sample(current_queue_snapshot, num_to_sample)
        
        # 清空队列，为下一批消息做准备
        neuro_input_queue.clear() 

        injected_chat_text = ""
        if selected_chats_for_neuro:
            injected_chat_lines = [f"{chat['username']}: {chat['text']}" for chat in selected_chats_for_neuro]
            injected_chat_text = (
                "Recent stream chat messages:\n" + 
                "\n".join(injected_chat_lines) + 
                "\n\nPlease respond naturally, considering these messages and your role as a streamer."
            )

        neuro_llm_input_content = [TextContent(text=injected_chat_text)]
        
        print(f"正在处理 Neuro 的输入，包含 {len(selected_chats_for_neuro)} 条队列消息。")

        try:
            response = letta_client.agents.messages.create(
                agent_id=NEURO_AGENT_ID,
                messages=[
                    MessageCreate(
                        role="user", 
                        content=neuro_llm_input_content
                    )
                ]
            )

            ai_full_response_text = "I couldn't process that. Please try again."
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
                        if ai_full_response_text != "I couldn't process that. Please try again.":
                            break
            
            print(f"Neuro 的完整响应已生成: '{ai_full_response_text}'")

            sentences = split_text_into_sentences(ai_full_response_text)
            if not sentences:
                if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                    await neuro_tts_websocket.send_json({"type": "end"})
                print("Neuro 的响应为空。")
                _trigger_neuro_response_flow() # 如果响应为空，Neuro 立即准备好接受下一个输入
                continue

            for i, sentence in enumerate(sentences):
                if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        audio_base64 = await synthesize_audio_segment(
                            text=sentence,
                            voice_name="en-US-AshleyNeural",
                            pitch=1.25
                        )
                        await neuro_tts_websocket.send_json({
                            "type": "segment",
                            "segment_id": i,
                            "text": sentence,
                            "audio_base64": audio_base64
                        })
                    except Exception as e:
                        print(f"TTS 合成或发送片段 '{sentence}' 时出错: {e}")
                        if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                            await neuro_tts_websocket.send_json({
                                "type": "error",
                                "code": "TTS_SEGMENT_ERROR",
                                "message": f"TTS synthesis failed for segment: {e}",
                                "text_segment": sentence
                            })
                        break 
            
            if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                await neuro_tts_websocket.send_json({"type": "end"})
            print("已完成发送 Neuro 响应的所有片段。")
            # 前端将在所有音频实际播放完毕后发送 'tts_finished' 信号。
            # 因此，这里不设置 neuro_tts_ready_event。

        except Exception as e:
            traceback.print_exc()
            print(f"在 neuro_processing_task 中发生错误: {e}")
            if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await neuro_tts_websocket.send_json({"type": "error", "code": "NEURO_PROCESSING_ERROR", "message": f"Neuro processing error: {e}"})
                except RuntimeError as se:
                    print(f"在关闭前向 Neuro 客户端发送错误消息失败: {se}")
            # 确保在错误时设置事件，以防止处理卡住
            _trigger_neuro_response_flow() 
        
        await asyncio.sleep(neuro_processing_interval)


# --- WebSocket 端点 ---

@app.websocket("/ws/chat_stream")
async def websocket_neuro_chat(websocket: WebSocket):
    """
    处理 Neuro TTS 流 (音频和字幕) 的连接，并接收用户消息和 TTS 完成信号。
    """
    global neuro_tts_websocket
    
    # 确保只允许一个 Neuro TTS 客户端连接
    if neuro_tts_websocket and neuro_tts_websocket.client_state == WebSocketState.CONNECTED:
        print("另一个 Neuro TTS 客户端尝试连接。只允许一个。关闭新连接。")
        await websocket.close(code=status.WS_1013_UNEXPECTED_CONDITION, reason="只允许一个 Neuro TTS 客户端。")
        return

    neuro_tts_websocket = websocket
    await websocket.accept()
    print("Neuro TTS WebSocket 客户端已连接。")
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                parsed_data = json.loads(raw_data)
                message_type = parsed_data.get("type")

                if message_type == "user_message":
                    user_message_text = parsed_data.get("message", "").strip()
                    username = parsed_data.get("username", "User") 
                    if not user_message_text:
                        print("收到空的用户消息，忽略。")
                        continue
                    user_chat_item = {"username": username, "text": user_message_text}
                    audience_chat_buffer.append(user_chat_item)
                    neuro_input_queue.append(user_chat_item)
                    print(f"用户消息 '{user_message_text}' 已添加到队列。Neuro 输入队列大小: {len(neuro_input_queue)}。观众缓冲区大小: {len(audience_chat_buffer)}")
                
                elif message_type == "tts_finished":
                    # 此信号表示前端已播放完所有 TTS 音频
                    print("收到前端的 'tts_finished' 信号。Neuro 已准备好接受下一个输入。")
                    _trigger_neuro_response_flow() # 设置事件以触发 neuro_processing_task
                
                elif message_type == "start_live_stream":
                    # 收到前端的信号，用于启动 Neuro 的首次响应
                    print("收到前端的 'start_live_stream' 信号。正在触发 Neuro 首次响应。")
                    await _trigger_neuro_initial_response() # 这将添加初始消息并触发 LLM

            except json.JSONDecodeError:
                print(f"收到非 JSON 消息: {raw_data}。忽略。")
            except Exception as e:
                print(f"在 neuro_chat_ws 中处理接收到的消息时出错: {e}")
                traceback.print_exc()

    except WebSocketDisconnect:
        print("Neuro TTS WebSocket 客户端已断开连接。")
    except Exception as e:
        traceback.print_exc()
        print(f"发生意外的 Neuro TTS WebSocket 错误: {e}")
    finally:
        # 确保 neuro_tts_websocket 设置为 None 并在断开连接时触发事件
        neuro_tts_websocket = None
        _trigger_neuro_response_flow() # 即使断开连接，也确保事件被设置，以防后台任务卡住
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED: 
                await websocket.close()
                print("Neuro TTS WebSocket 连接已关闭。")
        except RuntimeError:
            pass


@app.websocket("/ws/audience_chat_display")
async def websocket_audience_chat_display(websocket: WebSocket):
    """
    处理将所有聊天消息 (AI 生成的 + 用户) 流式传输到前端显示。
    """
    await websocket.accept()
    # 全局列表 audience_display_websockets 不再用于直接发送，因为它有并发问题。
    # 每个连接的此协程都负责将其自身的聊天消息发送出去。
    print("Audience Chat Display WebSocket 客户端已连接。")

    chat_send_interval = 0.5 # 秒
    num_chats_to_send_per_interval = 3 

    try:
        # 发送初始积压的聊天消息
        initial_backlog_limit = 50 
        initial_chats_to_send = list(audience_chat_buffer)[-initial_backlog_limit:]
        
        # 跟踪此特定客户端连接已发送的最后一条消息的索引
        current_read_index = 0

        # 发送初始积压
        for chat in initial_chats_to_send:
            try:
                # 在发送前检查 WebSocket 状态
                if websocket.client_state == WebSocketState.CONNECTED: 
                    await websocket.send_json({
                        "type": "audience_chat",
                        "username": chat["username"],
                        "text": chat["text"]
                    })
                    current_read_index += 1 # 每发送一条聊天，索引就增加
                    await asyncio.sleep(0.01) # 短暂延迟以防止发送过快
                else:
                    print(f"跳过初始积压发送，WebSocket 未连接: {websocket.client_state}")
                    break # 如果未连接，则中断
            except Exception as e:
                print(f"发送初始积压聊天时出错: {e}")
                break 

        # 现在，随着新聊天消息出现在缓冲区中，持续发送
        while True:
            # 关键检查: 在进一步处理之前，确保 WebSocket 仍处于连接状态
            if websocket.client_state != WebSocketState.CONNECTED:
                print("Audience Display WebSocket 未连接，中断此客户端的循环。")
                break 
            
            # 检查缓冲区中是否有此客户端尚未接收到的新消息
            if len(audience_chat_buffer) > current_read_index:
                # 只获取缓冲区中 *新* 的消息
                new_chats_available = list(audience_chat_buffer)[current_read_index:]
                chats_chunk = new_chats_available[:num_chats_to_send_per_interval] # 限制块大小

                for chat in chats_chunk:
                    try:
                        if websocket.client_state == WebSocketState.CONNECTED: 
                            await websocket.send_json({
                                "type": "audience_chat",
                                "username": chat["username"],
                                "text": chat["text"]
                            })
                            current_read_index += 1 # 每发送一条聊天，索引就增加
                        else:
                            print(f"在发送块期间 WebSocket 断开连接。中断内部循环。")
                            break 
                    except Exception as e:
                        print(f"发送观众聊天时出错: {e}")
                        break 
            
            await asyncio.sleep(chat_send_interval)

    except WebSocketDisconnect:
        print("Audience Chat Display WebSocket 客户端已断开连接。")
    except Exception as e:
        traceback.print_exc()
        print(f"发生意外的 Audience Chat Display WebSocket 错误: {e}")
    finally:
        # 在断开连接时，此特定协程结束，不再发送数据
        try:
            # 确保 WebSocket 实际已关闭
            if websocket.client_state != WebSocketState.DISCONNECTED: 
                await websocket.close()
                print("Audience Chat Display WebSocket 连接已显式关闭。")
        except RuntimeError:
            pass
