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

# --- 核心变化：导入新的配置对象和更新函数 ---
from config import settings, update_and_broadcast_settings, AppSettings

# 保持其他导入不变
from chatbot import audience_llm_client, get_dynamic_audience_prompt
from letta import get_neuro_response, reset_neuro_agent_memory
from audio_synthesis import synthesize_audio_segment
from stream_chat import (
    add_to_audience_buffer, add_to_neuro_input_queue, 
    get_recent_audience_chats, is_neuro_input_queue_empty, get_all_neuro_input_chats
)
from websocket_manager import connection_manager
from stream_manager import live_stream_manager
import shared_state

# 使用配置中的origins初始化FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware, 
    allow_origins=settings.server.client_origins, # <-- 修改
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

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
        await reset_neuro_agent_memory()
    except Exception as e:
        print(f"启动时重置 Letta Agent 记忆失败: {e}")
    
    # 保持所有启动任务不变
    asyncio.create_task(live_stream_manager.broadcast_stream_metadata())
    asyncio.create_task(live_stream_manager.start_new_stream_cycle()) 
    asyncio.create_task(broadcast_events_task())
    asyncio.create_task(generate_audience_chat_task()) 
    asyncio.create_task(neuro_response_cycle())
    print("所有后台任务已启动。")

# Pydantic 模型定义，不再需要从 config 获取默认值，因为它们在函数签名中被处理
class ErrorSpeechRequest(BaseModel):
    text: str
    voice_name: str | None = None
    pitch: float | None = None

class ErrorSpeechResponse(BaseModel):
    audio_base64: str

@app.post("/synthesize_error_speech", response_model=ErrorSpeechResponse)
async def synthesize_error_speech_endpoint(request: ErrorSpeechRequest):
    try:
        # synthesize_audio_segment 现在能处理 None 值
        audio_base64, _ = await synthesize_audio_segment(
            text=request.text, 
            voice_name=request.voice_name, 
            pitch=request.pitch
        )
        return ErrorSpeechResponse(audio_base64=audio_base64)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root(): 
    return {"message": "AI 主播后端正在运行！"}

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
            max_tokens=settings.audience_simulation.max_output_tokens # <-- 修改
        )
        
        parsed_chats = []
        for line in raw_chat_text.split('\n'):
            line = line.strip()
            if ':' in line:
                username_raw, text = line.split(':', 1)
                username = username_raw.strip()
                if username in settings.audience_simulation.username_blocklist: # <-- 修改
                    username = random.choice(settings.audience_simulation.username_pool) # <-- 修改
                    print(f"  -> 强制替换用户名: LLM 生成 '{username_raw}'，替换为 '{username}'。")
                if username and text.strip(): 
                    parsed_chats.append({"username": username, "text": text.strip()})
            elif line: 
                parsed_chats.append({"username": random.choice(settings.audience_simulation.username_pool), "text": line}) # <-- 修改
        
        chats_to_broadcast = parsed_chats[:settings.audience_simulation.chats_per_batch] # <-- 修改
        
        for chat in chats_to_broadcast: 
            add_to_audience_buffer(chat)
            add_to_neuro_input_queue(chat)
            broadcast_message = {"type": "chat_message", **chat, "is_user_message": False}
            await connection_manager.broadcast(broadcast_message)
            await asyncio.sleep(random.uniform(0.1, 0.4)) 
        
        print(f"  <- 聊天生成任务完成，广播了 {len(chats_to_broadcast)} 条消息。")
    except Exception as e:
        traceback.print_exc()
        print(f"错误: 单个聊天生成任务失败: {e}")

async def generate_audience_chat_task():
    """
    这是一个“调度器”函数。它以固定的频率创建新的聊天生成任务。
    """
    print("观众聊天调度器: 任务启动。")
    while True:
        asyncio.create_task(fetch_and_process_audience_chats())
        await asyncio.sleep(settings.audience_simulation.chat_generation_interval_sec) # <-- 修改

async def neuro_response_cycle():
    """
    Neuro 的核心响应循环。
    采用“预合成，后分发”的半流式模式。
    """
    await shared_state.live_phase_started_event.wait()
    print("Neuro响应周期: 任务启动。")
    is_first_response = True
    
    while True:
        try:
            if is_first_response:
                print("首次响应: 注入开场白。")
                add_to_neuro_input_queue({"username": "System", "text": settings.neuro_behavior.initial_greeting}) # <-- 修改
                is_first_response = False
            elif is_neuro_input_queue_empty():
                await asyncio.sleep(1)
                continue
            
            current_queue_snapshot = get_all_neuro_input_chats()
            sample_size = min(settings.neuro_behavior.input_chat_sample_size, len(current_queue_snapshot)) # <-- 修改
            selected_chats = random.sample(current_queue_snapshot, sample_size)
            ai_full_response_text = await get_neuro_response(selected_chats)
            
            async with shared_state.neuro_last_speech_lock:
                if ai_full_response_text and ai_full_response_text.strip():
                    shared_state.neuro_last_speech = ai_full_response_text
                    print(f"共享状态已更新: '{shared_state.neuro_last_speech[:50]}...'")
                else:
                    shared_state.neuro_last_speech = "(Neuro-Sama is currently silent...)"
                    print("警告: 从 Letta 获取的响应为空，跳过本轮。")
                    continue
            
            sentences = re.split(r'(?<=[.!?])\s+', ai_full_response_text.replace('\n', ' ').strip())
            sentences = [s.strip() for s in sentences if s.strip()]
            if not sentences:
                print("警告: 无法从文本中分割出有效句子，跳过本轮。")
                continue

            print(f"开始并行合成 {len(sentences)} 个句子...")
            synthesis_tasks = [synthesize_audio_segment(s) for s in sentences]
            synthesis_results = await asyncio.gather(*synthesis_tasks, return_exceptions=True)
            print("所有句子合成完毕。")

            speech_packages = []
            for i, result in enumerate(synthesis_results):
                if isinstance(result, Exception):
                    print(f"警告: 跳过一个合成失败的句子。文本: '{sentences[i][:30]}...', 错误: {result}")
                    continue
                audio_base64, audio_duration = result
                speech_packages.append({
                    "segment_id": i,
                    "text": sentences[i],
                    "audio_base64": audio_base64,
                    "duration": audio_duration
                })

            if not speech_packages:
                print("错误: 所有句子的 TTS 合成都失败了。跳过本轮。")
                await connection_manager.broadcast({"type": "neuro_error_signal"})
                await asyncio.sleep(15)
                continue

            live_stream_manager.set_neuro_speaking_status(True)
            for i, package in enumerate(speech_packages):
                # 注意：这里我们重新构造了要广播的包，以避免修改原始的 speech_packages 列表
                broadcast_package = {"type": "neuro_speech_segment", **package, "is_end": False}
                print(f"  -> 广播句子 {i+1}/{len(speech_packages)}: '{package['text'][:30]}...'")
                await connection_manager.broadcast(broadcast_package)
                await asyncio.sleep(package['duration'])
            
            await connection_manager.broadcast({"type": "neuro_speech_segment", "is_end": True})
            live_stream_manager.set_neuro_speaking_status(False)

            print(f"发言结束，进入 {settings.neuro_behavior.post_speech_cooldown_sec} 秒冷却期。") # <-- 修改
            await asyncio.sleep(settings.neuro_behavior.post_speech_cooldown_sec) # <-- 修改
        except Exception as e:
            traceback.print_exc()
            print(f"Neuro响应周期发生严重错误: {e}，将在10秒后恢复。")
            live_stream_manager.set_neuro_speaking_status(False)
            await asyncio.sleep(10)

@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        initial_event = live_stream_manager.get_initial_state_for_client()
        await connection_manager.send_personal_message(initial_event, websocket)
        
        metadata_event = {"type": "update_stream_metadata", **settings.stream_metadata.model_dump()} # <-- 修改
        await connection_manager.send_personal_message(metadata_event, websocket)
        
        initial_chats = get_recent_audience_chats(settings.performance.initial_chat_backlog_limit) # <-- 修改
        for chat in initial_chats:
            await connection_manager.send_personal_message({"type": "chat_message", **chat, "is_user_message": False}, websocket)
            await asyncio.sleep(0.01)
        
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            if data.get("type") == "user_message":
                user_message = {"username": data.get("username", "User"), "text": data.get("message", "").strip()}
                if user_message["text"]:
                    add_to_audience_buffer(user_message)
                    add_to_neuro_input_queue(user_message)
                    broadcast_message = {"type": "chat_message", **user_message, "is_user_message": True}
                    await connection_manager.broadcast(broadcast_message)
    except WebSocketDisconnect:
        print("WebSocket 客户端已断开连接。")
    finally:
        connection_manager.disconnect(websocket)

# --- API 端点用于控制面板 ---
@app.get("/api/settings", response_model=AppSettings)
async def get_current_settings():
    """获取当前所有运行时配置"""
    return settings

@app.patch("/api/settings", response_model=AppSettings)
async def update_partial_settings(new_settings: dict):
    """
    更新部分配置项。
    请求体示例: {"neuro_behavior": {"post_speech_cooldown_sec": 5.0}}
    """
    await update_and_broadcast_settings(new_settings)
    return settings

# --- Uvicorn 启动 ---
if __name__ == "__main__":
    import uvicorn
    # 使用配置中的服务器设置
    uvicorn.run(
        "main:app", 
        host=settings.server.host, 
        port=settings.server.port, 
        reload=True # 在开发时开启热重载
    )