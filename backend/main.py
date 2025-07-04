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
    asyncio.create_task(live_stream_manager.broadcast_stream_metadata())
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
                username_raw, text = line.split(':', 1)
                username = username_raw.strip()

                # --- 核心修改：如果用户名在黑名单中，就替换掉它 ---
                if username in config.USERNAME_BLOCKLIST:
                    username = random.choice(config.USERNAME_POOL)
                    print(f"  -> 强制替换用户名: LLM 生成 '{username_raw}'，替换为 '{username}'。")

                if username and text.strip(): 
                    parsed_chats.append({"username": username, "text": text.strip()})
            elif line: 
                # 如果没有冒号，即 LLM 直接输出文本，也为其分配一个随机用户名
                parsed_chats.append({"username": random.choice(config.USERNAME_POOL), "text": line})
        
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
        traceback.print_exc() # 打印详细的错误堆栈
        print(f"错误: 单个聊天生成任务失败: {e}")


async def generate_audience_chat_task():
    """
    这是一个“调度器”函数。它以固定的频率创建新的聊天生成任务。
    """
    print("观众聊天调度器: 任务启动。")
    
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
    """
    Neuro 的核心响应循环。
    采用“预合成，后分发”的半流式模式：
    1. 一次性获取完整文本。
    2. 并行合成所有句子的 TTS。
    3. 逐句、带停顿地广播已合成的音频片段。
    """
    await shared_state.live_phase_started_event.wait()
    print("Neuro响应周期: 任务启动。")
    is_first_response = True
    
    while True:
        try:
            if is_first_response:
                print("首次响应: 注入开场白。")
                add_to_neuro_input_queue({"username": "System", "text": config.NEURO_INITIAL_GREETING})
                is_first_response = False
            elif is_neuro_input_queue_empty():
                await asyncio.sleep(1)
                continue
            
            # --- 1. 获取聊天上下文并从 LLM 获取完整响应 ---
            current_queue_snapshot = get_all_neuro_input_chats()
            sample_size = min(config.NEURO_INPUT_CHAT_SAMPLE_SIZE, len(current_queue_snapshot))
            selected_chats = random.sample(current_queue_snapshot, sample_size)
            ai_full_response_text = await get_neuro_response(selected_chats)
            
            # 更新共享状态
            async with shared_state.neuro_last_speech_lock:
                if ai_full_response_text and ai_full_response_text.strip():
                    shared_state.neuro_last_speech = ai_full_response_text
                    print(f"共享状态已更新: '{shared_state.neuro_last_speech[:50]}...'")
                else:
                    shared_state.neuro_last_speech = "(Neuro-Sama is currently silent...)"
                    print("警告: 从 Letta 获取的响应为空，跳过本轮。")
                    continue

            # --- 2. 将响应分割成句子 ---
            sentences = re.split(r'(?<=[.!?])\s+', ai_full_response_text.replace('\n', ' ').strip())
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                print("警告: 无法从文本中分割出有效句子，跳过本轮。")
                continue

            # --- 3. 并行进行所有句子的 TTS 合成 ---
            print(f"开始并行合成 {len(sentences)} 个句子...")
            synthesis_tasks = [synthesize_audio_segment(s) for s in sentences]
            synthesis_results = await asyncio.gather(*synthesis_tasks, return_exceptions=True)
            print("所有句子合成完毕。")

            # --- 4. 准备好所有待广播的语音包 ---
            speech_packages = []
            for i, result in enumerate(synthesis_results):
                if isinstance(result, Exception):
                    print(f"警告: 跳过一个合成失败的句子。文本: '{sentences[i][:30]}...', 错误: {result}")
                    continue
                
                audio_base64, audio_duration = result
                speech_packages.append({
                    "type": "neuro_speech_segment",
                    "segment_id": i,
                    "text": sentences[i],
                    "audio_base64": audio_base64,
                    "duration": audio_duration,
                    "is_end": False
                })

            if not speech_packages:
                print("错误: 所有句子的 TTS 合成都失败了。跳过本轮。")
                await connection_manager.broadcast({"type": "neuro_error_signal"})
                await asyncio.sleep(15) # 等待较长时间再重试
                continue

            # --- 5. 逐个分发（广播）已合成的语音包 ---
            live_stream_manager.set_neuro_speaking_status(True)
            
            for i, package in enumerate(speech_packages):
                print(f"  -> 广播句子 {i+1}/{len(speech_packages)}: '{package['text'][:30]}...'")
                await connection_manager.broadcast(package)
                # 等待当前句子的音频播放时间，模拟说话的停顿
                await asyncio.sleep(package['duration'])
            
            # --- 6. 所有句子处理完毕后，发送结束信号 ---
            print("  -> 所有句子广播完毕，发送结束信号。")
            await connection_manager.broadcast({"type": "neuro_speech_segment", "is_end": True})
            live_stream_manager.set_neuro_speaking_status(False)

            # --- 7. 进入冷却期 ---
            print(f"发言结束，进入 {config.NEURO_POST_SPEECH_COOLDOWN_SEC} 秒冷却期。")
            await asyncio.sleep(config.NEURO_POST_SPEECH_COOLDOWN_SEC)

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
        metadata_event = {
            "type": "update_stream_metadata",
            **config.STREAM_METADATA
        }
        await connection_manager.send_personal_message(metadata_event, websocket)
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