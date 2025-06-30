# backend/main.py
import asyncio
import json
import traceback
import random
import re

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from chatbot import audience_llm_client, AUDIENCE_LLM_PROMPT
from letta import reset_neuro_agent_memory, get_neuro_response
from audio_synthesis import synthesize_audio_segment
from stream_chat import (
    audience_chat_buffer, neuro_input_queue, clear_all_queues, 
    add_to_audience_buffer, add_to_neuro_input_queue, get_recent_audience_chats, 
    is_neuro_input_queue_empty, get_all_neuro_input_chats
)
from websocket_manager import neuro_tts_ws_manager, audience_chat_ws_manager
from stream_manager import live_stream_manager

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=config.CLIENT_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

async def broadcast_events_task():
    """后台任务，从事件队列中取出事件并广播给所有客户端。"""
    while True:
        try:
            event = await live_stream_manager.event_queue.get()
            print(f"广播事件: {event}")
            # 向两个 WebSocket 管理器广播相同的事件
            await neuro_tts_ws_manager.broadcast(event)
            await audience_chat_ws_manager.broadcast(event)
            live_stream_manager.event_queue.task_done()
        except Exception as e:
            print(f"广播事件时出错: {e}")

@app.on_event("startup")
async def startup_event():
    print("FastAPI 应用正在启动...")
    await reset_neuro_agent_memory() 
    asyncio.create_task(live_stream_manager.start_new_stream_cycle()) 
    asyncio.create_task(broadcast_events_task()) # 启动事件广播任务
    asyncio.create_task(generate_audience_chat_task()) 
    asyncio.create_task(neuro_processing_task()) 
    print("所有后台任务已启动。")

# --- HTTP 端点 (无变化) ---
# ... (synthesize_error_speech_endpoint, reset_agent_messages_endpoint, root) ...
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
@app.post("/reset_agent_messages", status_code=200)
async def reset_agent_messages_endpoint():
    print("收到重置请求。")
    live_stream_manager.set_neuro_speaking_status(False)
    live_stream_manager.reset_stream_state()
    clear_all_queues()
    await reset_neuro_agent_memory()
    asyncio.create_task(live_stream_manager.start_new_stream_cycle())
    return {"message": "重置成功，正在重启直播。"}
@app.get("/")
async def root(): return {"message": "AI 主播后端正在运行！"}

# --- 后台任务 (neuro_processing_task 有微调) ---
# ... (generate_audience_chat_task 保持不变) ...
async def generate_audience_chat_task():
    while True:
        # 使用 live_stream_manager 的内部状态 _current_phase 来检查
        if live_stream_manager._current_phase == live_stream_manager.StreamPhase.LIVE:
            try:
                raw_chat_text = await audience_llm_client.generate_chat_messages(prompt=AUDIENCE_LLM_PROMPT,max_tokens=config.AUDIENCE_LLM_MAX_OUTPUT_TOKENS)
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
                    await audience_chat_ws_manager.broadcast(broadcast_message)
                    await neuro_tts_ws_manager.broadcast(broadcast_message)
                print(f"已生成 {len(parsed_chats)} 条观众聊天。")
            except Exception as e:
                print(f"生成观众聊天时出错: {e}")
        else:
            print(f"当前直播阶段为 {live_stream_manager._current_phase}，暂不生成观众聊天。")
        
        await asyncio.sleep(config.AUDIENCE_CHAT_GENERATION_INTERVAL)

async def neuro_processing_task():
    while True:
        # 使用 live_stream_manager 内部状态，而不是 get_current_state()
        if live_stream_manager._current_phase != live_stream_manager.StreamPhase.LIVE or live_stream_manager._is_neuro_speaking:
            await asyncio.sleep(0.5)
            continue
            
        if is_neuro_input_queue_empty():
            await asyncio.sleep(0.5)
            continue
        
        current_queue_snapshot = get_all_neuro_input_chats()
        selected_chats_for_neuro = random.sample(current_queue_snapshot, min(50, len(current_queue_snapshot)))
        
        print(f"正在处理 Neuro 的输入，包含 {len(selected_chats_for_neuro)} 条队列消息。")
        try:
            ai_full_response_text = await get_neuro_response(selected_chats_for_neuro)
            print(f"Neuro 的完整响应已生成: '{ai_full_response_text}'")
            def split_text_into_sentences(text: str) -> list[str]:
                sentences = re.split(r'(?<=[.!?])(?<!Mr\.)(?<!Mrs\.)(?<!Dr\.)(?<!etc\.)\s+|$', text)
                return [s.strip() for s in sentences if s.strip()]
            sentences = split_text_into_sentences(ai_full_response_text)
            if not sentences: continue

            live_stream_manager.set_neuro_speaking_status(True) 
            total_speech_duration = 0.0
            for i, sentence in enumerate(sentences):
                if neuro_tts_ws_manager.active_connections:
                    try:
                        audio_base64, audio_duration = await synthesize_audio_segment(text=sentence)
                        total_speech_duration += audio_duration
                        await neuro_tts_ws_manager.broadcast({"type": "neuro_speech_segment", "segment_id": i, "text": sentence, "audio_base64": audio_base64, "is_end": False})
                    except Exception as e:
                        print(f"TTS 合成或发送片段 '{sentence}' 时出错: {e}")
                        break
            
            if total_speech_duration > 0:
                await asyncio.sleep(total_speech_duration)
            
            live_stream_manager.set_neuro_speaking_status(False)
            
            if neuro_tts_ws_manager.active_connections:
                await neuro_tts_ws_manager.broadcast({"type": "neuro_speech_segment", "is_end": True})
        except Exception as e:
            traceback.print_exc()
            live_stream_manager.set_neuro_speaking_status(False)
        await asyncio.sleep(0.5)

# --- WebSocket 端点 ---
@app.websocket("/ws/neuro_stream") 
async def websocket_neuro_stream(websocket: WebSocket):
    await neuro_tts_ws_manager.connect(websocket)
    try:
        # 发送一次性的初始状态事件
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
                    await audience_chat_ws_manager.broadcast(broadcast_message)
                    await neuro_tts_ws_manager.broadcast(broadcast_message)
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