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
from config import config_manager, AppSettings
from process_manager import process_manager
from log_handler import configure_logging, log_queue

# --- 功能模块导入 ---
from chatbot import ChatbotManager, get_dynamic_audience_prompt
from letta import get_neuro_response, reset_neuro_agent_memory
from audio_synthesis import synthesize_audio_segment
from stream_chat import (
    add_to_audience_buffer, add_to_neuro_input_queue, 
    get_recent_audience_chats, is_neuro_input_queue_empty, get_all_neuro_input_chats
)
from websocket_manager import connection_manager
from stream_manager import live_stream_manager
import shared_state

# --- FastAPI 应用和模板设置 ---
app = FastAPI(title="Neuro-Sama Simulator Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config_manager.settings.server.client_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="panels")

# --- 全局管理器实例 ---
chatbot_manager: ChatbotManager | None = None

# --- 核心修复点 ---
# 将 Python 内置的函数和类型添加到 Jinja2 的全局环境中，以便模板可以使用它们
templates.env.globals['isinstance'] = isinstance
templates.env.globals['list'] = list
templates.env.globals['str'] = str
templates.env.globals['int'] = int
templates.env.globals['float'] = float
templates.env.globals['bool'] = bool

# --- 安全和认证 ---
COOKIE_NAME = "panel_session"
cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)

async def get_panel_access(request: Request, session_token: Optional[str] = Depends(cookie_scheme)):
    password = config_manager.settings.server.panel_password
    if not password:
        # No password set, allow access
        yield
        return

    if session_token and session_token == password:
        # Valid token, allow access
        yield
        return
    
    # Redirect to login page
    raise HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": "/login"}
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
            ai_full_response_text = await get_neuro_response(selected_chats)
            
            async with shared_state.neuro_last_speech_lock:
                if ai_full_response_text and ai_full_response_text.strip():
                    shared_state.neuro_last_speech = ai_full_response_text
                else:
                    shared_state.neuro_last_speech = "(Neuro-Sama is currently silent...)"
                    print("警告: 从 Letta 获取的响应为空，跳过本轮。")
                    continue
            
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', ai_full_response_text.replace('\n', ' ').strip()) if s.strip()]
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
    configure_logging()
    
    # 实例化管理器
    chatbot_manager = ChatbotManager()

    # 定义并注册回调
    async def metadata_callback(updated_settings: AppSettings):
        await live_stream_manager.broadcast_stream_metadata()
    
    config_manager.register_update_callback(metadata_callback)
    config_manager.register_update_callback(chatbot_manager.handle_config_update)
    
    print("FastAPI 应用已启动。请通过 /panel 控制直播进程。")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行。"""
    if process_manager.is_running:
        process_manager.stop_live_processes()
    print("FastAPI 应用已关闭。")


# -------------------------------------------------------------
# --- 认证和高级控制面板端点 ---
# -------------------------------------------------------------

@app.get("/login", tags=["Authentication"], response_class=HTMLResponse)
async def get_login_form(request: Request):
    """显示登录页面。"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", tags=["Authentication"])
async def login_for_panel_access(request: Request, password: str = Form(...)):
    """处理登录请求并设置 cookie。"""
    if password == config_manager.settings.server.panel_password:
        response = RedirectResponse(url="/panel", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key=COOKIE_NAME, value=password, httponly=True, samesite="strict")
        return response
    # Return to login form with an error message
    return templates.TemplateResponse("login.html", {"request": request, "error": "密码错误"})

@app.post("/logout", tags=["Authentication"])
async def logout(response: RedirectResponse = RedirectResponse(url="/login")):
    """处理登出请求并删除 cookie。"""
    response.delete_cookie(COOKIE_NAME)
    return response

@app.get("/panel", tags=["Control Panel"], dependencies=[Depends(get_panel_access)])
async def get_advanced_panel(request: Request, message: str | None = None):
    """显示高级控制面板页面。"""
    return templates.TemplateResponse("control_panel.html", {
        "request": request,
        "settings": config_manager.settings.model_dump(),
        "is_running": process_manager.is_running,
        "message": message,
    })

@app.post("/panel/settings", tags=["Control Panel"], dependencies=[Depends(get_panel_access)])
async def update_settings_from_panel(request: Request):
    """从面板热重载设置。"""
    form_data = await request.form()
    new_settings_data = {}
    for key, value in form_data.items():
        parts = key.split('.')
        d = new_settings_data
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        
        try:
            # 尝试从原始配置模型中获取类型
            original_type = type(config_manager.settings.model_dump(by_alias=True)[parts[0]][parts[-1]])
            if original_type is list:
                d[parts[-1]] = [item.strip() for item in value.split(',') if item.strip()]
            elif original_type is bool:
                 d[parts[-1]] = value.lower() in ['true', '1', 'yes', 'on']
            else:
                 d[parts[-1]] = original_type(value)
        except (ValueError, TypeError, KeyError):
            # 如果转换失败或找不到原始类型，则作为字符串处理
            d[parts[-1]] = value

    await config_manager.update_settings(new_settings_data)
    return RedirectResponse(url="/panel?message=设置已保存并热重载！", status_code=HTTP_303_SEE_OTHER)

@app.post("/panel/start", tags=["Control Panel"], dependencies=[Depends(get_panel_access)])
async def start_processes_from_panel():
    process_manager.start_live_processes()
    return RedirectResponse(url="/panel?message=直播已启动", status_code=HTTP_303_SEE_OTHER)

@app.post("/panel/stop", tags=["Control Panel"], dependencies=[Depends(get_panel_access)])
async def stop_processes_from_panel():
    process_manager.stop_live_processes()
    return RedirectResponse(url="/panel?message=直播已停止", status_code=HTTP_303_SEE_OTHER)

@app.post("/panel/restart", tags=["Control Panel"], dependencies=[Depends(get_panel_access)])
async def restart_processes_from_panel():
    process_manager.stop_live_processes()
    await asyncio.sleep(1)
    process_manager.start_live_processes()
    return RedirectResponse(url="/panel?message=直播已重启", status_code=HTTP_303_SEE_OTHER)

@app.post("/panel/restart-server", tags=["Control Panel"], dependencies=[Depends(get_panel_access)])
async def restart_server_hard():
    print("控制面板请求硬重启服务器... 服务器正在关闭。")
    async def shutdown():
        await asyncio.sleep(1)
        sys.exit(0)
    asyncio.create_task(shutdown())
    return {"message": "服务器正在关闭..."}


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

@app.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        for log_entry in list(log_queue):
            await websocket.send_text(log_entry)
        
        while websocket.client_state == WebSocketState.CONNECTED:
            if log_queue:
                log_entry = log_queue.popleft()
                await websocket.send_text(log_entry)
            else:
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("日志流客户端已断开连接。")
    finally:
        print("日志流WebSocket连接关闭。")


# -------------------------------------------------------------
# --- 其他 API 端点 ---
# -------------------------------------------------------------

class ErrorSpeechRequest(BaseModel):
    text: str
    voice_name: str | None = None
    pitch: float | None = None

@app.post("/synthesize_error_speech", tags=["Utilities"])
async def synthesize_error_speech_endpoint(request: ErrorSpeechRequest):
    try:
        audio_base64, _ = await synthesize_audio_segment(
            text=request.text, voice_name=request.voice_name, pitch=request.pitch
        )
        return {"audio_base64": audio_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings", response_model=AppSettings, tags=["API"], deprecated=True)
async def get_current_settings():
    return config_manager.settings

@app.patch("/api/settings", response_model=AppSettings, tags=["API"], deprecated=True)
async def update_partial_settings(new_settings: dict):
    await config_manager.update_settings(new_settings)
    return config_manager.settings

@app.get("/", tags=["Root"])
async def root(): 
    return {"message": "AI 主播后端正在运行！访问 /docs 查看API文档，或访问 /panel 查看控制面板。"}

# -------------------------------------------------------------
# --- Uvicorn 启动 ---
# -------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config_manager.settings.server.host,
        port=config_manager.settings.server.port,
        reload=True
    )