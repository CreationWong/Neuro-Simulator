# backend/main.py

import asyncio
import json
import traceback
import random
import re
import time
import os
import sys
from typing import Optional

from fastapi import (
    FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Form, Depends, status
)
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.websockets import WebSocketState
from starlette.status import HTTP_303_SEE_OTHER
from fastapi.security import APIKeyCookie

# --- 核心模块导入 ---
from .config import config_manager, AppSettings
from .process_manager import process_manager
from .log_handler import configure_server_logging, server_log_queue, agent_log_queue

# --- 功能模块导入 ---
from .chatbot import ChatbotManager, get_dynamic_audience_prompt
# from .letta import get_neuro_response, reset_neuro_agent_memory, initialize_agent # This will be imported dynamically
from .audio_synthesis import synthesize_audio_segment
from .stream_chat import (
    add_to_audience_buffer, add_to_neuro_input_queue, 
    get_recent_audience_chats, is_neuro_input_queue_empty, get_all_neuro_input_chats
)
from .websocket_manager import connection_manager
from .stream_manager import live_stream_manager
import neuro_simulator.shared_state as shared_state

# --- FastAPI 应用和模板设置 ---
from .agent.api import router as agent_router

app = FastAPI(title="vedal987 Simulator API", version="1.0.0")

# 注册API路由
app.include_router(agent_router)
app.include_router(agent_router)  # Include the agent management API router
app.add_middleware(
    CORSMiddleware,
    allow_origins=config_manager.settings.server.client_origins + ["http://localhost:8080", "https://dashboard.live.jiahui.cafe"],  # 添加dashboard_web的地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-API-Token"],  # 暴露API Token头
)

# --- 安全和认证 ---
API_TOKEN_HEADER = "X-API-Token"

async def get_api_token(request: Request):
    """检查API token是否有效"""
    password = config_manager.settings.server.panel_password
    if not password:
        # No password set, allow access
        return True

    # 检查header中的token
    header_token = request.headers.get(API_TOKEN_HEADER)
    if header_token and header_token == password:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API token",
        headers={"WWW-Authenticate": "Bearer"},
    )

# -------------------------------------------------------------
# --- 后台任务函数定义 ---
# -------------------------------------------------------------

async def broadcast_events_task():
    """从 live_stream_manager 的队列中获取事件并广播给所有客户端。"""
    while True:
        try:
            event = await live_stream_manager.event_queue.get()
            print(f"广播事件: {event}")
            await connection_manager.broadcast(event)
            live_stream_manager.event_queue.task_done()
        except asyncio.CancelledError:
            print("广播任务被取消。")
            break
        except Exception as e:
            print(f"广播事件时出错: {e}")

async def fetch_and_process_audience_chats():
    """单个聊天生成任务的执行体。"""
    if not chatbot_manager or not chatbot_manager.client:
        print("错误: Chatbot manager 未初始化，跳过聊天生成。")
        return
    try:
        dynamic_prompt = await get_dynamic_audience_prompt()
        raw_chat_text = await chatbot_manager.client.generate_chat_messages(
            prompt=dynamic_prompt, 
            max_tokens=config_manager.settings.audience_simulation.max_output_tokens
        )
        
        parsed_chats = []
        for line in raw_chat_text.split('\n'):
            line = line.strip()
            if ':' in line:
                username_raw, text = line.split(':', 1)
                username = username_raw.strip()
                if username in config_manager.settings.audience_simulation.username_blocklist:
                    username = random.choice(config_manager.settings.audience_simulation.username_pool)
                if username and text.strip(): 
                    parsed_chats.append({"username": username, "text": text.strip()})
            elif line: 
                parsed_chats.append({"username": random.choice(config_manager.settings.audience_simulation.username_pool), "text": line})
        
        chats_to_broadcast = parsed_chats[:config_manager.settings.audience_simulation.chats_per_batch]
        
        for chat in chats_to_broadcast: 
            add_to_audience_buffer(chat)
            add_to_neuro_input_queue(chat)
            broadcast_message = {"type": "chat_message", **chat, "is_user_message": False}
            await connection_manager.broadcast(broadcast_message)
            await asyncio.sleep(random.uniform(0.1, 0.4))
    except Exception:
        print("错误: 单个聊天生成任务失败。详情见 traceback。")
        traceback.print_exc()

async def generate_audience_chat_task():
    """周期性地调度聊天生成任务。"""
    print("观众聊天调度器: 任务启动。")
    while True:
        try:
            asyncio.create_task(fetch_and_process_audience_chats())
            await asyncio.sleep(config_manager.settings.audience_simulation.chat_generation_interval_sec)
        except asyncio.CancelledError:
            print("观众聊天调度器任务被取消。")
            break

async def neuro_response_cycle():
    """Neuro 的核心响应循环。"""
    await shared_state.live_phase_started_event.wait()
    print("Neuro响应周期: 任务启动。")
    is_first_response = True
    
    # Dynamically import get_neuro_response to respect agent_type
    agent_type = config_manager.settings.agent_type
    if agent_type == "builtin":
        from .builtin_agent import get_builtin_response as get_neuro_response
    else:
        from .letta import get_neuro_response

    while True:
        try:
            if is_first_response:
                print("首次响应: 注入开场白。")
                add_to_neuro_input_queue({"username": "System", "text": config_manager.settings.neuro_behavior.initial_greeting})
                is_first_response = False
            elif is_neuro_input_queue_empty():
                await asyncio.sleep(1)
                continue
            
            current_queue_snapshot = get_all_neuro_input_chats()
            sample_size = min(config_manager.settings.neuro_behavior.input_chat_sample_size, len(current_queue_snapshot))
            selected_chats = random.sample(current_queue_snapshot, sample_size)
            
            # 使用 asyncio.wait_for 添加超时机制，避免长时间阻塞
            try:
                ai_full_response_text = await asyncio.wait_for(
                    get_neuro_response(selected_chats),
                    timeout=10.0  # 默认10秒超时
                )
            except asyncio.TimeoutError:
                print(f"警告: {agent_type} 响应超时，跳过本轮。")
                await asyncio.sleep(5)
                continue
            
            async with shared_state.neuro_last_speech_lock:
                # Handle both string and dict responses
                response_text = ""
                if isinstance(ai_full_response_text, dict):
                    # Extract the final response from the dict
                    response_text = ai_full_response_text.get("final_response", "")
                else:
                    response_text = ai_full_response_text if ai_full_response_text else ""
                
                if response_text and response_text.strip():
                    shared_state.neuro_last_speech = response_text
                else:
                    shared_state.neuro_last_speech = "(Neuro-Sama is currently silent...)"
                    print(f"警告: 从 {agent_type} 获取的响应为空，跳过本轮。")
                    continue
            
            # Handle both string and dict responses for sentence splitting
            response_text = ""
            if isinstance(ai_full_response_text, dict):
                response_text = ai_full_response_text.get("final_response", "")
            else:
                response_text = ai_full_response_text if ai_full_response_text else ""
                
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', response_text.replace('\n', ' ').strip()) if s.strip()]
            if not sentences:
                continue

            synthesis_tasks = [synthesize_audio_segment(s) for s in sentences]
            synthesis_results = await asyncio.gather(*synthesis_tasks, return_exceptions=True)
            
            speech_packages = [
                {"segment_id": i, "text": sentences[i], "audio_base64": res[0], "duration": res[1]}
                for i, res in enumerate(synthesis_results) if not isinstance(res, Exception)
            ]

            if not speech_packages:
                print("错误: 所有句子的 TTS 合成都失败了。")
                await connection_manager.broadcast({"type": "neuro_error_signal"})
                await asyncio.sleep(15)
                continue

            live_stream_manager.set_neuro_speaking_status(True)
            for package in speech_packages:
                broadcast_package = {"type": "neuro_speech_segment", **package, "is_end": False}
                await connection_manager.broadcast(broadcast_package)
                await asyncio.sleep(package['duration'])
            
            await connection_manager.broadcast({"type": "neuro_speech_segment", "is_end": True})
            live_stream_manager.set_neuro_speaking_status(False)
            
            await asyncio.sleep(config_manager.settings.neuro_behavior.post_speech_cooldown_sec)
        except asyncio.CancelledError:
            print("Neuro 响应周期任务被取消。")
            live_stream_manager.set_neuro_speaking_status(False)
            break
        except Exception:
            print("Neuro响应周期发生严重错误，将在10秒后恢复。详情见 traceback。")
            traceback.print_exc()
            live_stream_manager.set_neuro_speaking_status(False)
            await asyncio.sleep(10)


# -------------------------------------------------------------
# --- 应用生命周期事件 ---
# -------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """应用启动时执行。"""
    global chatbot_manager
    configure_server_logging()
    
    # 实例化管理器
    chatbot_manager = ChatbotManager()

    # 定义并注册回调
    async def metadata_callback(updated_settings: AppSettings):
        await live_stream_manager.broadcast_stream_metadata()
    
    config_manager.register_update_callback(metadata_callback)
    config_manager.register_update_callback(chatbot_manager.handle_config_update)
    
    # Initialize the appropriate agent
    from .letta import initialize_agent
    from .builtin_agent import initialize_builtin_agent
    
    agent_type = config_manager.settings.agent_type
    if agent_type == "builtin":
        await initialize_builtin_agent()
    else:
        await initialize_agent()
    
    print("FastAPI 应用已启动。请通过外部控制面板控制直播进程。")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行。"""
    if process_manager.is_running:
        process_manager.stop_live_processes()
    print("FastAPI 应用已关闭。")


# -------------------------------------------------------------
# --- 直播控制 API 端点 ---
# -------------------------------------------------------------

@app.post("/api/stream/start", tags=["Stream Control"], dependencies=[Depends(get_api_token)])
async def api_start_stream():
    """启动直播"""
    # If using builtin agent, clear temp memory and context when starting stream
    agent_type = config_manager.settings.agent_type
    if agent_type == "builtin":
        from .builtin_agent import clear_builtin_agent_temp_memory, clear_builtin_agent_context
        await clear_builtin_agent_temp_memory()
        await clear_builtin_agent_context()
    
    if not process_manager.is_running:
        process_manager.start_live_processes()
        return {"status": "success", "message": "直播已启动"}
    else:
        return {"status": "info", "message": "直播已在运行"}

@app.post("/api/stream/stop", tags=["Stream Control"], dependencies=[Depends(get_api_token)])
async def api_stop_stream():
    """停止直播"""
    if process_manager.is_running:
        process_manager.stop_live_processes()
        return {"status": "success", "message": "直播已停止"}
    else:
        return {"status": "info", "message": "直播未在运行"}

@app.post("/api/stream/restart", tags=["Stream Control"], dependencies=[Depends(get_api_token)])
async def api_restart_stream():
    """重启直播"""
    process_manager.stop_live_processes()
    await asyncio.sleep(1)
    process_manager.start_live_processes()
    return {"status": "success", "message": "直播已重启"}

@app.post("/api/agent/reset_memory", tags=["Agent"], dependencies=[Depends(get_api_token)])
async def api_reset_agent_memory():
    """重置Agent记忆"""
    agent_type = config_manager.settings.agent_type
    
    if agent_type == "builtin":
        from .builtin_agent import reset_builtin_agent_memory
        await reset_builtin_agent_memory()
        return {"status": "success", "message": "内置Agent记忆已重置"}
    else:
        from .letta import reset_neuro_agent_memory
        await reset_neuro_agent_memory()
        return {"status": "success", "message": "Letta Agent记忆已重置"}

@app.get("/api/stream/status", tags=["Stream Control"], dependencies=[Depends(get_api_token)])
async def api_get_stream_status():
    """获取直播状态"""
    return {
        "is_running": process_manager.is_running,
        "backend_status": "running" if process_manager.is_running else "stopped"
    }

# -------------------------------------------------------------
# --- WebSocket 端点 ---
# -------------------------------------------------------------

@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        initial_event = live_stream_manager.get_initial_state_for_client()
        await connection_manager.send_personal_message(initial_event, websocket)
        
        metadata_event = {"type": "update_stream_metadata", **config_manager.settings.stream_metadata.model_dump()}
        await connection_manager.send_personal_message(metadata_event, websocket)
        
        initial_chats = get_recent_audience_chats(config_manager.settings.performance.initial_chat_backlog_limit)
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
        print(f"客户端 {websocket.client} 已断开连接。")
    finally:
        connection_manager.disconnect(websocket)

@app.websocket("/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Send initial server logs
        for log_entry in list(server_log_queue):
            await websocket.send_json({"type": "server_log", "data": log_entry})
        
        # Send initial agent logs
        for log_entry in list(agent_log_queue):
            await websocket.send_json({"type": "agent_log", "data": log_entry})
        
        while websocket.client_state == WebSocketState.CONNECTED:
            # Check for new server logs
            if server_log_queue:
                log_entry = server_log_queue.popleft()
                await websocket.send_json({"type": "server_log", "data": log_entry})
            
            # Check for new agent logs
            if agent_log_queue:
                log_entry = agent_log_queue.popleft()
                await websocket.send_json({"type": "agent_log", "data": log_entry})
            
            # Small delay to prevent busy waiting
            if not server_log_queue and not agent_log_queue:
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("管理面板WebSocket客户端已断开连接。")
    finally:
        print("管理面板WebSocket连接关闭。")


# -------------------------------------------------------------
# --- 其他 API 端点 ---
# -------------------------------------------------------------

class ErrorSpeechRequest(BaseModel):
    text: str
    voice_name: str | None = None
    pitch: float | None = None

@app.post("/api/tts/synthesize", tags=["TTS"], dependencies=[Depends(get_api_token)])
async def synthesize_speech_endpoint(request: ErrorSpeechRequest):
    """TTS语音合成端点"""
    try:
        audio_base64, _ = await synthesize_audio_segment(
            text=request.text, voice_name=request.voice_name, pitch=request.pitch
        )
        return {"audio_base64": audio_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# --- 配置管理 API 端点 ---
# -------------------------------------------------------------

def filter_config_for_frontend(settings):
    """过滤配置，只返回前端需要的配置项"""
    # 创建一个新的字典，只包含前端需要的配置项
    filtered_settings = {}
    
    # Stream metadata (除了streamer_nickname)
    if hasattr(settings, 'stream_metadata'):
        filtered_settings['stream_metadata'] = {
            'stream_title': settings.stream_metadata.stream_title,
            'stream_category': settings.stream_metadata.stream_category,
            'stream_tags': settings.stream_metadata.stream_tags
        }
    
    # Agent settings (不包含 agent_type)
    if hasattr(settings, 'agent'):
        filtered_settings['agent'] = {
            'agent_provider': settings.agent.agent_provider,
            'agent_model': settings.agent.agent_model
        }
    
    # Neuro behavior settings
    if hasattr(settings, 'neuro_behavior'):
        filtered_settings['neuro_behavior'] = {
            'input_chat_sample_size': settings.neuro_behavior.input_chat_sample_size,
            'post_speech_cooldown_sec': settings.neuro_behavior.post_speech_cooldown_sec,
            'initial_greeting': settings.neuro_behavior.initial_greeting
        }
    
    # Audience simulation settings
    if hasattr(settings, 'audience_simulation'):
        filtered_settings['audience_simulation'] = {
            'llm_provider': settings.audience_simulation.llm_provider,
            'gemini_model': settings.audience_simulation.gemini_model,
            'openai_model': settings.audience_simulation.openai_model,
            'llm_temperature': settings.audience_simulation.llm_temperature,
            'chat_generation_interval_sec': settings.audience_simulation.chat_generation_interval_sec,
            'chats_per_batch': settings.audience_simulation.chats_per_batch,
            'max_output_tokens': settings.audience_simulation.max_output_tokens,
            'username_blocklist': settings.audience_simulation.username_blocklist,
            'username_pool': settings.audience_simulation.username_pool
        }
    
    # Performance settings
    if hasattr(settings, 'performance'):
        filtered_settings['performance'] = {
            'neuro_input_queue_max_size': settings.performance.neuro_input_queue_max_size,
            'audience_chat_buffer_max_size': settings.performance.audience_chat_buffer_max_size,
            'initial_chat_backlog_limit': settings.performance.initial_chat_backlog_limit
        }
    
    return filtered_settings

@app.get("/api/configs", tags=["Config Management"], dependencies=[Depends(get_api_token)])
async def get_configs():
    """获取当前配置（已过滤，不包含敏感信息）"""
    return filter_config_for_frontend(config_manager.settings)

@app.patch("/api/configs", tags=["Config Management"], dependencies=[Depends(get_api_token)])
async def update_configs(new_settings: dict):
    """更新配置（已过滤，不包含敏感信息）"""
    try:
        # 过滤掉不应该被修改的配置项
        filtered_settings = {}
        
        # 定义允许修改的配置路径
        allowed_paths = {
            'stream_metadata.stream_title',
            'stream_metadata.stream_category',
            'stream_metadata.stream_tags',
            'agent.agent_provider',  # 添加 agent 配置项（不包含 agent_type）
            'agent.agent_model',
            'neuro_behavior.input_chat_sample_size',
            'neuro_behavior.post_speech_cooldown_sec',
            'neuro_behavior.initial_greeting',
            'audience_simulation.llm_provider',
            'audience_simulation.gemini_model',
            'audience_simulation.openai_model',
            'audience_simulation.llm_temperature',
            'audience_simulation.chat_generation_interval_sec',
            'audience_simulation.chats_per_batch',
            'audience_simulation.max_output_tokens',
            'audience_simulation.username_blocklist',
            'audience_simulation.username_pool',
            'performance.neuro_input_queue_max_size',
            'performance.audience_chat_buffer_max_size',
            'performance.initial_chat_backlog_limit'
        }
        
        # 递归函数来检查和过滤配置项
        def filter_nested_dict(obj, prefix=''):
            filtered = {}
            for key, value in obj.items():
                full_path = f"{prefix}.{key}" if prefix else key
                if full_path in allowed_paths:
                    filtered[key] = value
                elif isinstance(value, dict):
                    nested_filtered = filter_nested_dict(value, full_path)
                    if nested_filtered:  # 只有当过滤后还有内容时才添加
                        filtered[key] = nested_filtered
            return filtered
        
        # 应用过滤
        filtered_settings = filter_nested_dict(new_settings)
        
        # 更新配置
        await config_manager.update_settings(filtered_settings)
        return filter_config_for_frontend(config_manager.settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

@app.post("/api/configs/reload", tags=["Config Management"], dependencies=[Depends(get_api_token)])
async def reload_configs():
    """重载配置文件"""
    try:
        await config_manager.update_settings({}) # 传入空字典，强制重载并触发回调
        return {"status": "success", "message": "配置已重载"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重载配置失败: {str(e)}")

@app.get("/api/system/health", tags=["System"])
async def health_check():
    """健康检查端点，用于监控系统状态"""
    return {
        "status": "healthy",
        "backend_running": True,
        "process_manager_running": process_manager.is_running,
        "timestamp": time.time()
    }

@app.get("/", tags=["Root"])
async def root(): 
    return {
        "message": "Neuro-Sama Simulator Backend",
        "version": "2.0",
        "api_docs": "/docs",
        "api_structure": {
            "stream": "/api/stream",
            "configs": "/api/configs", 
            "logs": "/api/logs",
            "tts": "/api/tts",
            "system": "/api/system",
            "websocket": "/ws/stream"
        }
    }

# -------------------------------------------------------------
# --- Uvicorn 启动 ---
# -------------------------------------------------------------

def run_server(host: str = None, port: int = None):
    """Run the server with optional host and port overrides"""
    import uvicorn
    
    # Use provided host/port or fall back to config values
    server_host = host or config_manager.settings.server.host
    server_port = port or config_manager.settings.server.port
    
    # When running as a package, we need to specify the full module path
    uvicorn.run(
        "neuro_simulator.main:app",
        host=server_host,
        port=server_port,
        reload=False  # 生产环境中建议关闭reload
    )

if __name__ == "__main__":
    import uvicorn
    # 从配置文件中读取host和port设置
    uvicorn.run(
        "neuro_simulator.main:app",
        host=config_manager.settings.server.host,
        port=config_manager.settings.server.port,
        reload=False  # 生产环境中建议关闭reload
    )
