# backend/main.py
import asyncio
import json
import traceback
import random
import re
import time 

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

import config
from chatbot import audience_llm_client, AUDIENCE_LLM_PROMPT
from letta import get_neuro_response
from audio_synthesis import synthesize_audio_segment
from stream_chat import (
    add_to_audience_buffer, add_to_neuro_input_queue, 
    get_recent_audience_chats, is_neuro_input_queue_empty, get_all_neuro_input_chats
)
from websocket_manager import connection_manager
from stream_manager import live_stream_manager
from shared_state import live_phase_started_event

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=config.CLIENT_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ... (broadcast_events_task, startup_event, HTTP endpoints, generate_audience_chat_task 不变) ...
async def broadcast_events_task():
    while True:
        try:
            event = await live_stream_manager.event_queue.get()
            print(f"广播事件: {event}")
            await connection_manager.broadcast(event) # <-- 使用单一管理器
            live_stream_manager.event_queue.task_done()
        except Exception as e:
            print(f"广播事件时出错: {e}")

@app.on_event("startup")
async def startup_event():
    print("FastAPI 应用正在启动...")
    try:
        from letta import reset_neuro_agent_memory
        await reset_neuro_agent_memory()
    except Exception as e:
        print(f"启动时重置 Letta Agent 记忆失败: {e}")
    asyncio.create_task(live_stream_manager.start_new_stream_cycle()) 
    asyncio.create_task(broadcast_events_task())
    asyncio.create_task(generate_audience_chat_task()) 
    asyncio.create_task(neuro_response_cycle())
    print("所有后台任务已启动。")
class ErrorSpeechRequest(BaseModel):
    text: str
    voice_name: str = config.AZURE_TTS_VOICE_NAME
    pitch: float = config.AZURE_TTS_VOICE_PITCH
class ErrorSpeechResponse(BaseModel):
    audio_base64: str
@app.post("/synthesize_error_speech", response_model=ErrorSpeechResponse)
async def synthesize_error_speech_endpoint(request: ErrorSpeechRequest):
    try:
        audio_base64, _ = await synthesize_audio_segment(text=request.text, voice_name=request.voice_name, pitch=request.pitch)
        return ErrorSpeechResponse(audio_base64=audio_base64)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/")
async def root(): return {"message": "AI 主播后端正在运行！"}
async def generate_audience_chat_task():
    while True:
        try:
            raw_chat_text = await audience_llm_client.generate_chat_messages(prompt=AUDIENCE_LLM_PROMPT, max_tokens=config.AUDIENCE_LLM_MAX_OUTPUT_TOKENS)
            parsed_chats = []
            for line in raw_chat_text.split('\n'):
                line = line.strip()
                if ':' in line:
                    username, text = line.split(':', 1)
                    if username.strip() and text.strip(): parsed_chats.append({"username": username.strip(), "text": text.strip()})
                elif line: parsed_chats.append({"username": random.choice(config.USERNAME_POOL), "text": line})
            
            for chat in parsed_chats[:30]: 
                add_to_audience_buffer(chat); add_to_neuro_input_queue(chat)
                broadcast_message = {"type": "chat_message", **chat, "is_user_message": False}
                await connection_manager.broadcast(broadcast_message) # <-- 使用单一管理器
            print(f"已生成 {len(parsed_chats)} 条观众聊天。")
        except Exception as e:
            print(f"生成观众聊天时出错: {e}")
        await asyncio.sleep(config.AUDIENCE_CHAT_GENERATION_INTERVAL)

# --- V5 核心逻辑 ---

async def prepare_speech_package() -> dict | None:
    """
    思考和准备流程。这个函数现在不再需要 is_recovery 参数。
    """
    # 这个函数现在只负责一件事：根据当前队列内容，准备一个语音包。
    current_queue_snapshot = get_all_neuro_input_chats()
    # 如果队列是空的，调用者（主循环）应该负责决定是否注入提示。
    if not current_queue_snapshot:
        print("准备语音包: 输入队列为空，无需响应。")
        return None

    selected_chats = random.sample(current_queue_snapshot, min(50, len(current_queue_snapshot)))
    
    print(f"准备语音包 (输入包含 {len(selected_chats)} 条消息)...")
    ai_full_response_text = await get_neuro_response(selected_chats)
    
    if not ai_full_response_text or not ai_full_response_text.strip():
        print("警告: Letta 返回了空响应，无法准备语音包。")
        return None

    sentences = re.split(r'(?<=[.!?])\s+', ai_full_response_text.replace('\n', ' ').strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        print(f"警告: 无法从文本中分割出有效句子。原始文本: '{ai_full_response_text}'")
        return None

    synthesis_tasks = [synthesize_audio_segment(s) for s in sentences]
    synthesis_results = await asyncio.gather(*synthesis_tasks, return_exceptions=True)
    
    synthesized_segments = []
    for i, result in enumerate(synthesis_results):
        if isinstance(result, Exception):
            print(f"警告: 跳过一个合成失败的句子。错误: {result}")
            continue
        audio_base64, audio_duration = result
        synthesized_segments.append({
            "segment_id": i, "text": sentences[i], 
            "audio_base64": audio_base64, "duration": audio_duration
        })
    
    if not synthesized_segments:
        # 这是当所有句子的TTS都失败时的情况
        print("错误: 所有句子的 TTS 合成都失败了，无法生成语音包。")
        return None

    total_duration = sum(seg['duration'] for seg in synthesized_segments)
    print(f"准备语音包成功: 共 {len(synthesized_segments)} 句, 总时长 {total_duration:.2f}s。")
    return {"segments": synthesized_segments, "total_duration": total_duration}


async def neuro_response_cycle():
    """
    AI响应的主循环，采用更健壮的线性“思考->说话->暂停”逻辑。
    """
    await live_phase_started_event.wait()
    print("Neuro响应周期: 直播阶段开始，主循环启动。")

    while True:
        try:
            if is_neuro_input_queue_empty():
                print("输入队列为空，为 Neuro 添加一个启动提示。")
                add_to_neuro_input_queue({
                    "username": "System", 
                    "text": "What should I talk about now? The stream is live and my audience is waiting."
                })
            
            speech_package = await prepare_speech_package()

            # --- 核心修改点在这里 ---
            if not speech_package:
                print("错误: 语音包准备失败。向前端发送错误信号。")
                await connection_manager.broadcast({"type": "neuro_error_signal"}) # <-- 使用单一管理器
                print("将在15秒后进行下一次尝试。")
                await asyncio.sleep(15)
                continue
            
            live_stream_manager.set_neuro_speaking_status(True)
            for segment in speech_package["segments"]:
                await connection_manager.broadcast({"type": "neuro_speech_segment", **segment, "is_end": False}) # <-- 使用单一管理器
            await connection_manager.broadcast({"type": "neuro_speech_segment", "is_end": True}) # <-- 使用单一管理器
            
            playback_duration = speech_package['total_duration']
            print(f"主循环: 开始播放语音 (时长: {playback_duration:.2f}s)。")
            
            await asyncio.sleep(playback_duration)
            live_stream_manager.set_neuro_speaking_status(False)

            PAUSE_BETWEEN_SPEECH_SECONDS = 3.0
            print(f"主循环: 播放完毕，停顿 {PAUSE_BETWEEN_SPEECH_SECONDS} 秒。")
            await asyncio.sleep(PAUSE_BETWEEN_SPEECH_SECONDS)

        except Exception as e:
            traceback.print_exc()
            print(f"Neuro响应周期发生严重错误: {e}，将在10秒后恢复。")
            live_stream_manager.set_neuro_speaking_status(False)
            await asyncio.sleep(10)

# --- WebSocket 端点 (无变化) ---
@app.websocket("/ws/stream") # <-- 重命名为更通用的名称
async def websocket_stream_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket) # <-- 使用单一管理器
    try:
        # 发送初始状态和聊天历史
        initial_event = live_stream_manager.get_initial_state_for_client()
        await connection_manager.send_personal_message(initial_event, websocket)
        initial_chats = get_recent_audience_chats(config.INITIAL_CHAT_BACKLOG_LIMIT)
        for chat in initial_chats:
            await connection_manager.send_personal_message({"type": "chat_message", **chat, "is_user_message": False}, websocket)
            await asyncio.sleep(0.01)
        
        # 保持连接并接收用户消息
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            # 处理用户输入
            if data.get("type") == "user_message":
                user_message = {"username": data.get("username", "User"), "text": data.get("message", "").strip()}
                if user_message["text"]:
                    add_to_audience_buffer(user_message)
                    add_to_neuro_input_queue(user_message)
                    broadcast_message = {"type": "chat_message", **user_message, "is_user_message": True}
                    await connection_manager.broadcast(broadcast_message) # <-- 使用单一管理器
    except WebSocketDisconnect:
        print("WebSocket 客户端已断开连接。")
    finally:
        connection_manager.disconnect(websocket) # <-- 使用单一管理器