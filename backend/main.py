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
from websocket_manager import neuro_tts_ws_manager, audience_chat_ws_manager
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
            await neuro_tts_ws_manager.broadcast(event)
            await audience_chat_ws_manager.broadcast(event)
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
                await audience_chat_ws_manager.broadcast(broadcast_message); await neuro_tts_ws_manager.broadcast(broadcast_message)
            print(f"已生成 {len(parsed_chats)} 条观众聊天。")
        except Exception as e:
            print(f"生成观众聊天时出错: {e}")
        await asyncio.sleep(config.AUDIENCE_CHAT_GENERATION_INTERVAL)

# --- V5 核心逻辑 ---

async def prepare_speech_package(is_recovery: bool = False) -> dict | None:
    """
    思考和准备流程。is_recovery 标志用于在出错后准备一个简单的恢复性发言。
    """
    if is_neuro_input_queue_empty():
        if is_recovery:
            add_to_neuro_input_queue({"username": "System", "text": "What should I talk about now? My mind is blank."})
        else:
            return None

    current_queue_snapshot = get_all_neuro_input_chats()
    selected_chats = random.sample(current_queue_snapshot, min(50, len(current_queue_snapshot)))
    
    print(f"准备语音包: 正在处理 {len(selected_chats)} 条消息...")
    ai_full_response_text = await get_neuro_response(selected_chats)
    
    if not ai_full_response_text or not ai_full_response_text.strip():
        print("准备语音包: Letta 返回空响应。")
        return None

    sentences = re.split(r'(?<=[.!?])\s+', ai_full_response_text.replace('\n', ' ').strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return None

    synthesis_tasks = [synthesize_audio_segment(s) for s in sentences]
    synthesis_results = await asyncio.gather(*synthesis_tasks, return_exceptions=True)
    
    synthesized_segments = []
    for i, result in enumerate(synthesis_results):
        if isinstance(result, Exception): continue
        audio_base64, audio_duration = result
        synthesized_segments.append({
            "segment_id": i, "text": sentences[i], 
            "audio_base64": audio_base64, "duration": audio_duration
        })
    
    if not synthesized_segments: return None

    total_duration = sum(seg['duration'] for seg in synthesized_segments)
    print(f"准备语音包: 成功。共 {len(synthesized_segments)} 句, 总时长 {total_duration:.2f}s。")
    return {"segments": synthesized_segments, "total_duration": total_duration}


async def delayed_thinking_and_preparing(delay: float) -> dict | None:
    """
    先等待指定时间，然后开始思考和准备语音包。
    """
    if delay > 0:
        print(f"下一次思考将在 {delay:.2f} 秒后开始。")
        await asyncio.sleep(delay)
    else:
        print(f"播放时间过短，立即开始下一次思考。")
    
    return await prepare_speech_package()


async def neuro_response_cycle():
    """
    AI响应的主循环，使用 V5 定时器调度方案。
    """
    await live_phase_started_event.wait()
    print("Neuro响应周期: 直播阶段开始，主循环启动。")

    # 准备第一段语音
    speech_package = await prepare_speech_package(is_recovery=True)

    while True:
        try:
            if not speech_package:
                print("主循环: 没有可播放的语音包，将等待并重试。")
                await asyncio.sleep(5)
                speech_package = await prepare_speech_package(is_recovery=True)
                continue

            # --- 阶段 1: 播放当前的语音 ---
            live_stream_manager.set_neuro_speaking_status(True)
            for segment in speech_package["segments"]:
                await neuro_tts_ws_manager.broadcast({"type": "neuro_speech_segment", **segment, "is_end": False})
            await neuro_tts_ws_manager.broadcast({"type": "neuro_speech_segment", "is_end": True})
            
            playback_duration = speech_package['total_duration']
            print(f"主循环: 开始播放语音 (时长: {playback_duration:.2f}s)。")

            # --- 阶段 2: 调度下一次思考 ---
            PREFETCH_SECONDS = 5.0  # 预留5秒给Letta和TTS，可以根据实际情况微调
            thinking_delay = playback_duration - PREFETCH_SECONDS
            
            thinking_task = asyncio.create_task(
                delayed_thinking_and_preparing(thinking_delay)
            )

            # --- 阶段 3: 等待当前播放结束 ---
            await asyncio.sleep(playback_duration)
            live_stream_manager.set_neuro_speaking_status(False)
            
            # --- 阶段 4: 等待下一次思考完成并进行话间停顿 ---
            print("主循环: 播放完毕，等待思考任务完成...")
            next_speech_package = await thinking_task
            
            # 思考完成后，执行固定的停顿
            PAUSE_BETWEEN_SPEECH_SECONDS = 3.0
            print(f"主循环: 思考完成，停顿 {PAUSE_BETWEEN_SPEECH_SECONDS} 秒。")
            await asyncio.sleep(PAUSE_BETWEEN_SPEECH_SECONDS)
            
            speech_package = next_speech_package

        except Exception as e:
            traceback.print_exc()
            print(f"Neuro响应周期发生严重错误: {e}，将尝试恢复。")
            live_stream_manager.set_neuro_speaking_status(False)
            await asyncio.sleep(5)
            speech_package = await prepare_speech_package(is_recovery=True)


# --- WebSocket 端点 (无变化) ---
@app.websocket("/ws/neuro_stream") 
async def websocket_neuro_stream(websocket: WebSocket):
    await neuro_tts_ws_manager.connect(websocket)
    try:
        initial_event = live_stream_manager.get_initial_state_for_client()
        await neuro_tts_ws_manager.send_personal_message(initial_event, websocket)
        initial_chats = get_recent_audience_chats(config.INITIAL_CHAT_BACKLOG_LIMIT)
        for chat in initial_chats:
            await neuro_tts_ws_manager.send_personal_message({"type": "chat_message", **chat, "is_user_message": False}, websocket)
            await asyncio.sleep(0.01)
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            if data.get("type") == "user_message":
                user_message = {"username": data.get("username", "User"), "text": data.get("message", "").strip()}
                if user_message["text"]:
                    add_to_audience_buffer(user_message); add_to_neuro_input_queue(user_message)
                    broadcast_message = {"type": "chat_message", **user_message, "is_user_message": True}
                    await audience_chat_ws_manager.broadcast(broadcast_message); await neuro_tts_ws_manager.broadcast(broadcast_message)
    except WebSocketDisconnect: print("Neuro TTS WebSocket 客户端已断开连接。")
    finally: neuro_tts_ws_manager.disconnect(websocket)

@app.websocket("/ws/audience_chat_display")
async def websocket_audience_chat_display(websocket: WebSocket):
    await audience_chat_ws_manager.connect(websocket)
    try:
        initial_event = live_stream_manager.get_initial_state_for_client()
        await audience_chat_ws_manager.send_personal_message(initial_event, websocket)
        initial_chats = get_recent_audience_chats(config.INITIAL_CHAT_BACKLOG_LIMIT)
        for chat in initial_chats:
            await audience_chat_ws_manager.send_personal_message({"type": "chat_message", **chat, "is_user_message": False}, websocket)
            await asyncio.sleep(0.01)
        while True: await asyncio.sleep(3600)
    except WebSocketDisconnect: print("Audience Chat Display WebSocket 客户端已断开连接。")
    finally: audience_chat_ws_manager.disconnect(websocket)