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
from chatbot import audience_llm_client, get_dynamic_audience_prompt
from letta import get_neuro_response
from audio_synthesis import synthesize_audio_segment
from stream_chat import (
    add_to_audience_buffer, add_to_neuro_input_queue, 
    get_recent_audience_chats, is_neuro_input_queue_empty, get_all_neuro_input_chats
)
from websocket_manager import connection_manager
from stream_manager import live_stream_manager
import shared_state

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=config.CLIENT_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- broadcast_events_task, startup_event, HTTP 端点保持不变 ---
async def broadcast_events_task():
    while True:
        try:
            event = await live_stream_manager.event_queue.get()
            print(f"广播事件: {event}")
            await connection_manager.broadcast(event)
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

# ... (ErrorSpeechRequest, ErrorSpeechResponse, root 端点保持不变) ...
class ErrorSpeechRequest(BaseModel):
    text: str; voice_name: str = config.AZURE_TTS_VOICE_NAME; pitch: float = config.AZURE_TTS_VOICE_PITCH
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

# --- 聊天生成逻辑重构 ---

async def fetch_and_process_audience_chats():
    """
    这是一个“工人”函数。它执行一次完整的聊天生成和广播流程。
    这个函数会被并发地调用。
    """
    try:
        print("  -> 新的聊天生成任务启动...")
        dynamic_prompt = await get_dynamic_audience_prompt()
        raw_chat_text = await audience_llm_client.generate_chat_messages(
            prompt=dynamic_prompt, 
            max_tokens=config.AUDIENCE_LLM_MAX_OUTPUT_TOKENS
        )
        
        parsed_chats = []
        for line in raw_chat_text.split('\n'):
            line = line.strip()
            if ':' in line:
                username, text = line.split(':', 1)
                if username.strip() and text.strip(): parsed_chats.append({"username": username.strip(), "text": text.strip()})
            elif line: parsed_chats.append({"username": random.choice(config.USERNAME_POOL), "text": line})
        
        # 为了避免消息风暴，即使API返回很多，我们也只取配置的数量
        chats_to_broadcast = parsed_chats[:config.NUM_CHATS_TO_GENERATE_PER_BATCH]
        
        # 将消息的广播分散开，模拟真实聊天的感觉
        for chat in chats_to_broadcast: 
            add_to_audience_buffer(chat); add_to_neuro_input_queue(chat)
            broadcast_message = {"type": "chat_message", **chat, "is_user_message": False}
            await connection_manager.broadcast(broadcast_message)
            # 在每条消息之间加入一个非常小的、随机的延迟
            await asyncio.sleep(random.uniform(0.1, 0.4)) 
        
        print(f"  <- 聊天生成任务完成，广播了 {len(chats_to_broadcast)} 条消息。")
    except Exception as e:
        # 在独立的任务中捕获异常，防止一个失败的任务影响整个应用
        print(f"错误: 单个聊天生成任务失败: {e}")


async def generate_audience_chat_task():
    """
    这是一个“调度器”函数。它以固定的频率创建新的聊天生成任务。
    """
    print("观众聊天调度器: 任务启动。")
    await shared_state.live_phase_started_event.wait()
    
    while True:
        # 创建一个新的并发任务，但不等待它完成 (fire-and-forget)
        # 这使得我们可以立即继续循环，并在2秒后创建下一个任务
        asyncio.create_task(fetch_and_process_audience_chats())
        
        # 严格按照设定的间隔调度，不受API延迟影响
        await asyncio.sleep(config.AUDIENCE_CHAT_GENERATION_INTERVAL)


# --- Neuro 响应周期和辅助函数保持不变 ---

async def prepare_speech_package(ai_full_response_text: str) -> dict | None:
    if not ai_full_response_text or not ai_full_response_text.strip():
        print("警告: 传入的文本为空，无法准备语音包。")
        return None
    sentences = re.split(r'(?<=[.!?])\s+', ai_full_response_text.replace('\n', ' ').strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        print(f"警告: 无法从文本中分割出有效句子。")
        return None
    synthesis_tasks = [synthesize_audio_segment(s) for s in sentences]
    synthesis_results = await asyncio.gather(*synthesis_tasks, return_exceptions=True)
    synthesized_segments = []
    for i, result in enumerate(synthesis_results):
        if isinstance(result, Exception):
            print(f"警告: 跳过一个合成失败的句子。错误: {result}")
            continue
        audio_base64, audio_duration = result
        synthesized_segments.append({"segment_id": i, "text": sentences[i], "audio_base64": audio_base64, "duration": audio_duration})
    if not synthesized_segments:
        print("错误: 所有句子的 TTS 合成都失败了。")
        return None
    total_duration = sum(seg['duration'] for seg in synthesized_segments)
    print(f"准备语音包成功: 共 {len(synthesized_segments)} 句, 总时长 {total_duration:.2f}s。")
    return {"segments": synthesized_segments, "total_duration": total_duration}

async def neuro_response_cycle():
    await shared_state.live_phase_started_event.wait()
    print("Neuro响应周期: 任务启动。")
    is_first_response = True
    while True:
        try:
            if is_first_response:
                print("首次响应: 注入开场白。")
                add_to_neuro_input_queue({"username": "System", "text": "The stream has just started. Greet your audience and say hello!"})
                is_first_response = False
            elif is_neuro_input_queue_empty():
                await asyncio.sleep(1)
                continue
            
            current_queue_snapshot = get_all_neuro_input_chats()
            selected_chats = random.sample(current_queue_snapshot, min(50, len(current_queue_snapshot)))
            ai_full_response_text = await get_neuro_response(selected_chats)
            
            async with shared_state.neuro_last_speech_lock:
                if ai_full_response_text and ai_full_response_text.strip():
                    shared_state.neuro_last_speech = ai_full_response_text
                    print(f"共享状态已更新: '{shared_state.neuro_last_speech[:50]}...'")
                else:
                    shared_state.neuro_last_speech = "(Neuro-Sama is currently silent...)"

            speech_package = await prepare_speech_package(ai_full_response_text)

            if not speech_package:
                print("错误: 语音包准备失败。将在15秒后重试。")
                await connection_manager.broadcast({"type": "neuro_error_signal"})
                await asyncio.sleep(15)
                continue

            live_stream_manager.set_neuro_speaking_status(True)
            for segment in speech_package["segments"]:
                await connection_manager.broadcast({"type": "neuro_speech_segment", **segment, "is_end": False})
            await connection_manager.broadcast({"type": "neuro_speech_segment", "is_end": True})
            
            await asyncio.sleep(speech_package['total_duration'])
            live_stream_manager.set_neuro_speaking_status(False)
            await asyncio.sleep(3.0)

        except Exception as e:
            traceback.print_exc()
            print(f"Neuro响应周期发生严重错误: {e}，将在10秒后恢复。")
            live_stream_manager.set_neuro_speaking_status(False)
            await asyncio.sleep(10)

# --- WebSocket 端点保持不变 ---
@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        initial_event = live_stream_manager.get_initial_state_for_client()
        await connection_manager.send_personal_message(initial_event, websocket)
        initial_chats = get_recent_audience_chats(config.INITIAL_CHAT_BACKLOG_LIMIT)
        for chat in initial_chats:
            await connection_manager.send_personal_message({"type": "chat_message", **chat, "is_user_message": False}, websocket)
            await asyncio.sleep(0.01)
        
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            if data.get("type") == "user_message":
                user_message = {"username": data.get("username", "User"), "text": data.get("message", "").strip()}
                if user_message["text"]:
                    add_to_audience_buffer(user_message); add_to_neuro_input_queue(user_message)
                    broadcast_message = {"type": "chat_message", **user_message, "is_user_message": True}
                    await connection_manager.broadcast(broadcast_message)
    except WebSocketDisconnect:
        print("WebSocket 客户端已断开连接。")
    finally:
        connection_manager.disconnect(websocket)