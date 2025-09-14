# neuro_simulator/core/application.py
"""Main application file: FastAPI app instance, events, and websockets."""

import asyncio
import json
import logging
import random
import re
import time
import os
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState

# --- Core Imports ---
from .config import config_manager, AppSettings
from ..core.agent_factory import create_agent
from ..agent.core import Agent as LocalAgent
from ..chatbot.core import ChatbotAgent
from ..services.letta import LettaAgent
from ..services.builtin import BuiltinAgentWrapper

# --- API Routers ---
from ..api.system import router as system_router

# --- Services and Utilities ---
from ..services.audio import synthesize_audio_segment
from ..services.stream import live_stream_manager
from ..utils.logging import configure_server_logging, server_log_queue, agent_log_queue
from ..utils.process import process_manager
from ..utils.queue import (
    add_to_audience_buffer,
    add_to_neuro_input_queue,
    get_recent_audience_chats,
    is_neuro_input_queue_empty,
    get_all_neuro_input_chats,
    initialize_queues,
    get_recent_audience_chats_for_chatbot,
)
from ..utils.state import app_state
from ..utils.websocket import connection_manager

# --- Logger Setup ---
logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Neuro-Sama Simulator API",
    version="2.0.0",
    description="Backend for the Neuro-Sama digital being simulator."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config_manager.settings.server.client_origins + ["http://localhost:8080", "https://dashboard.live.jiahui.cafe"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-API-Token"],
)

app.include_router(system_router)

# --- Background Task Definitions ---

chatbot_agent: ChatbotAgent = None

async def broadcast_events_task():
    """Broadcasts events from the live_stream_manager's queue to all clients."""
    while True:
        try:
            event = await live_stream_manager.event_queue.get()
            await connection_manager.broadcast(event)
            live_stream_manager.event_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in broadcast_events_task: {e}", exc_info=True)

async def fetch_and_process_audience_chats():
    """Generates a batch of audience chat messages using the new ChatbotAgent."""
    if not chatbot_agent:
        return
    try:
        # Get context for the chatbot
        current_neuro_speech = app_state.neuro_last_speech
        context_message = current_neuro_speech if current_neuro_speech else "The stream is starting! Let's say hello and get the hype going!"
        recent_history = get_recent_audience_chats_for_chatbot(limit=10)

        # Generate messages
        generated_messages = await chatbot_agent.generate_chat_messages(
            neuro_speech=context_message,
            recent_history=recent_history
        )
        
        if not generated_messages:
            return

        # Process and broadcast generated messages
        for chat in generated_messages: 
            add_to_audience_buffer(chat)
            add_to_neuro_input_queue(chat)
            broadcast_message = {"type": "chat_message", **chat, "is_user_message": False}
            await connection_manager.broadcast(broadcast_message)
            # Stagger the messages slightly to feel more natural
            await asyncio.sleep(random.uniform(0.2, 0.8))
            
    except Exception as e:
        logger.error(f"Error in new fetch_and_process_audience_chats: {e}", exc_info=True)

async def generate_audience_chat_task():
    """Periodically triggers the audience chat generation task."""
    while True:
        try:
            # Wait until the live phase starts
            # await app_state.live_phase_started_event.wait() 
            
            asyncio.create_task(fetch_and_process_audience_chats())
            
            # Use the interval from the new chatbot_agent config
            await asyncio.sleep(config_manager.settings.chatbot_agent.generation_interval_sec)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in generate_audience_chat_task: {e}", exc_info=True)
            await asyncio.sleep(10) # Avoid fast-looping on persistent errors

async def neuro_response_cycle():
    """The core response loop for the agent."""
    await app_state.live_phase_started_event.wait()
    agent = await create_agent()
    is_first_response = True

    while True:
        try:
            selected_chats = []
            # Superchat logic
            if app_state.superchat_queue and (time.time() - app_state.last_superchat_time > 10):
                sc = app_state.superchat_queue.popleft()
                app_state.last_superchat_time = time.time()
                await connection_manager.broadcast({"type": "processing_superchat", "data": sc})

                # Agent-specific payload generation for superchats
                if isinstance(agent, LettaAgent):
                    selected_chats = [
                        {"role": "system", "content": "=== RANDOM 10 MSG IN CHATROOM ===\nNO MSG FETCH DUE TO UNPROCESSED HIGHLIGHTED MESSAGE"},
                        {"role": "system", "content": f"=== HIGHLIGHTED MESSAGE ===\n{sc['username']}: {sc['text']}"}
                    ]
                else: # For BuiltinAgent and any other future agents
                    selected_chats = [{'username': sc['username'], 'text': sc['text']}]

                # Clear the regular input queue to prevent immediate follow-up with normal chats
                get_all_neuro_input_chats()
            else:
                if is_first_response:
                    add_to_neuro_input_queue({"username": "System", "text": config_manager.settings.neuro_behavior.initial_greeting})
                    is_first_response = False
                elif is_neuro_input_queue_empty():
                    await asyncio.sleep(1)
                    continue
                
                current_queue_snapshot = get_all_neuro_input_chats()
                if not current_queue_snapshot:
                    continue
                sample_size = min(config_manager.settings.neuro_behavior.input_chat_sample_size, len(current_queue_snapshot))
                selected_chats = random.sample(current_queue_snapshot, sample_size)
            
            if not selected_chats:
                continue
            
            response_result = await asyncio.wait_for(agent.process_and_respond(selected_chats), timeout=20.0)
            
            response_text = response_result.get("final_response", "").strip()
            if not response_text:
                continue

            # Push updated agent context to admin clients immediately after processing
            updated_context = await agent.get_message_history()
            await connection_manager.broadcast_to_admins({"type": "agent_context", "action": "update", "messages": updated_context})

            async with app_state.neuro_last_speech_lock:
                app_state.neuro_last_speech = response_text

            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', response_text.replace('\n', ' ')) if s.strip()]
            if not sentences: continue

            synthesis_tasks = [synthesize_audio_segment(s) for s in sentences]
            synthesis_results = await asyncio.gather(*synthesis_tasks, return_exceptions=True)
            
            speech_packages = [
                {"segment_id": i, "text": sentences[i], "audio_base64": res[0], "duration": res[1]}
                for i, res in enumerate(synthesis_results) if not isinstance(res, Exception)
            ]

            if not speech_packages: continue

            live_stream_manager.set_neuro_speaking_status(True)
            for package in speech_packages:
                await connection_manager.broadcast({"type": "neuro_speech_segment", **package, "is_end": False})
                await asyncio.sleep(package['duration'])
            
            await connection_manager.broadcast({"type": "neuro_speech_segment", "is_end": True})
            live_stream_manager.set_neuro_speaking_status(False)
            
            await asyncio.sleep(config_manager.settings.neuro_behavior.post_speech_cooldown_sec)

        except asyncio.TimeoutError:
            logger.warning("Agent response timed out, skipping this cycle.")
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            live_stream_manager.set_neuro_speaking_status(False)
            break
        except Exception as e:
            logger.error(f"Critical error in neuro_response_cycle: {e}", exc_info=True)
            live_stream_manager.set_neuro_speaking_status(False)
            await asyncio.sleep(10)

# --- Application Lifecycle Events ---

@app.on_event("startup")
async def startup_event():
    """Actions to perform on application startup."""
    # 1. Configure logging first
    configure_server_logging()

    # 2. Initialize queues now that config is loaded
    initialize_queues()

    # 3. Initialize the new Chatbot Agent
    global chatbot_agent
    chatbot_agent = ChatbotAgent()
    await chatbot_agent.initialize()

    # 4. Register callbacks
    async def metadata_callback(settings: AppSettings):
        await live_stream_manager.broadcast_stream_metadata()
    
    config_manager.register_update_callback(metadata_callback)
    
    # 5. Initialize main agent (which will load its own configs)
    try:
        await create_agent()
        logger.info(f"Successfully initialized agent type: {config_manager.settings.agent_type}")
    except Exception as e:
        logger.critical(f"Agent initialization failed on startup: {e}", exc_info=True)
    
    logger.info("FastAPI application has started.")

@app.on_event("shutdown")
def shutdown_event():
    """Actions to perform on application shutdown."""
    if process_manager.is_running:
        process_manager.stop_live_processes()
    logger.info("FastAPI application has shut down.")

# --- WebSocket Endpoints ---

@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        await connection_manager.send_personal_message(live_stream_manager.get_initial_state_for_client(), websocket)
        await connection_manager.send_personal_message({"type": "update_stream_metadata", **config_manager.settings.stream_metadata.model_dump()}, websocket)
        
        initial_chats = get_recent_audience_chats(config_manager.settings.performance.initial_chat_backlog_limit)
        for chat in initial_chats:
            await connection_manager.send_personal_message({"type": "chat_message", **chat, "is_user_message": False}, websocket)
            await asyncio.sleep(0.01)
        
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            if data.get("type") == "user_message":
                user_message = {"username": data.get("username", "User"), "text": data.get("text", "").strip()}
                if user_message["text"]:
                    add_to_audience_buffer(user_message)
                    add_to_neuro_input_queue(user_message)
                    await connection_manager.broadcast({"type": "chat_message", **user_message, "is_user_message": True})
            elif data.get("type") == "superchat":
                sc_message = {
                    "username": data.get("username", "User"),
                    "text": data.get("text", "").strip(),
                    "sc_type": data.get("sc_type", "bits")
                }
                if sc_message["text"]:
                    app_state.superchat_queue.append(sc_message)

    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket)

@app.websocket("/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Add the new admin client to a dedicated list
    connection_manager.admin_connections.append(websocket)
    try:
        # Send initial state
        for log_entry in list(server_log_queue): await websocket.send_json({"type": "server_log", "data": log_entry})
        for log_entry in list(agent_log_queue): await websocket.send_json({"type": "agent_log", "data": log_entry})
        
        agent = await create_agent()
        initial_context = await agent.get_message_history()
        await websocket.send_json({"type": "agent_context", "action": "update", "messages": initial_context})
        
        # Send initial stream status
        status = {"is_running": process_manager.is_running, "backend_status": "running" if process_manager.is_running else "stopped"}
        await websocket.send_json({"type": "stream_status", "payload": status})
        
        # Main loop for receiving messages from the client and pushing log updates
        while websocket.client_state == WebSocketState.CONNECTED:
            # Check for incoming messages
            try:
                raw_data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                data = json.loads(raw_data)
                await handle_admin_ws_message(websocket, data)
            except asyncio.TimeoutError:
                pass # No message received, continue to push logs

            # Push log updates
            if server_log_queue: await websocket.send_json({"type": "server_log", "data": server_log_queue.popleft()})
            if agent_log_queue: await websocket.send_json({"type": "agent_log", "data": agent_log_queue.popleft()})
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.admin_connections.remove(websocket)
        logger.info("Admin WebSocket client disconnected.")

async def handle_admin_ws_message(websocket: WebSocket, data: dict):
    """Handles incoming messages from the admin WebSocket."""
    action = data.get("action")
    payload = data.get("payload", {})
    request_id = data.get("request_id")
    
    agent = await create_agent()
    response = {"type": "response", "request_id": request_id, "payload": {}}

    try:
        # Core Memory Actions
        if action == "get_core_memory_blocks":
            blocks = await agent.get_memory_blocks()
            response["payload"] = blocks
        
        elif action == "get_core_memory_block":
            block = await agent.get_memory_block(**payload)
            response["payload"] = block

        elif action == "create_core_memory_block":
            block_id = await agent.create_memory_block(**payload)
            response["payload"] = {"status": "success", "block_id": block_id}
            # Broadcast the update to all admins
            updated_blocks = await agent.get_memory_blocks()
            await connection_manager.broadcast_to_admins({"type": "core_memory_updated", "payload": updated_blocks})

        elif action == "update_core_memory_block":
            await agent.update_memory_block(**payload)
            response["payload"] = {"status": "success"}
            # Broadcast the update to all admins
            updated_blocks = await agent.get_memory_blocks()
            await connection_manager.broadcast_to_admins({"type": "core_memory_updated", "payload": updated_blocks})

        elif action == "delete_core_memory_block":
            await agent.delete_memory_block(**payload)
            response["payload"] = {"status": "success"}
            # Broadcast the update to all admins
            updated_blocks = await agent.get_memory_blocks()
            await connection_manager.broadcast_to_admins({"type": "core_memory_updated", "payload": updated_blocks})

        # Temp Memory Actions
        elif action == "get_temp_memory":
            temp_mem = await agent.get_temp_memory()
            response["payload"] = temp_mem

        elif action == "add_temp_memory":
            await agent.add_temp_memory(**payload)
            response["payload"] = {"status": "success"}
            updated_temp_mem = await agent.get_temp_memory()
            await connection_manager.broadcast_to_admins({"type": "temp_memory_updated", "payload": updated_temp_mem})

        elif action == "delete_temp_memory_item":
            await agent.delete_temp_memory_item(**payload)
            response["payload"] = {"status": "success"}
            updated_temp_mem = await agent.get_temp_memory()
            await connection_manager.broadcast_to_admins({"type": "temp_memory_updated", "payload": updated_temp_mem})

        elif action == "clear_temp_memory":
            await agent.clear_temp_memory()
            response["payload"] = {"status": "success"}
            updated_temp_mem = await agent.get_temp_memory()
            await connection_manager.broadcast_to_admins({"type": "temp_memory_updated", "payload": updated_temp_mem})

        # Init Memory Actions
        elif action == "get_init_memory":
            init_mem = await agent.get_init_memory()
            response["payload"] = init_mem

        elif action == "update_init_memory":
            await agent.update_init_memory(**payload)
            response["payload"] = {"status": "success"}
            updated_init_mem = await agent.get_init_memory()
            await connection_manager.broadcast_to_admins({"type": "init_memory_updated", "payload": updated_init_mem})

        elif action == "update_init_memory_item":
            await agent.update_init_memory_item(**payload)
            response["payload"] = {"status": "success"}
            updated_init_mem = await agent.get_init_memory()
            await connection_manager.broadcast_to_admins({"type": "init_memory_updated", "payload": updated_init_mem})

        elif action == "delete_init_memory_key":
            await agent.delete_init_memory_key(**payload)
            response["payload"] = {"status": "success"}
            updated_init_mem = await agent.get_init_memory()
            await connection_manager.broadcast_to_admins({"type": "init_memory_updated", "payload": updated_init_mem})

        # Tool Actions
        elif action == "get_all_tools":
            agent_instance = getattr(agent, 'agent_instance', agent)
            all_tools = agent_instance.tool_manager.get_all_tool_schemas()
            response["payload"] = {"tools": all_tools}

        elif action == "get_agent_tool_allocations":
            agent_instance = getattr(agent, 'agent_instance', agent)
            allocations = agent_instance.tool_manager.get_allocations()
            response["payload"] = {"allocations": allocations}

        elif action == "set_agent_tool_allocations":
            agent_instance = getattr(agent, 'agent_instance', agent)
            allocations_payload = payload.get("allocations", {})
            agent_instance.tool_manager.set_allocations(allocations_payload)
            response["payload"] = {"status": "success"}
            # Broadcast the update to all admins
            updated_allocations = agent_instance.tool_manager.get_allocations()
            await connection_manager.broadcast_to_admins({"type": "agent_tool_allocations_updated", "payload": {"allocations": updated_allocations}})

        elif action == "reload_tools":
            agent_instance = getattr(agent, 'agent_instance', agent)
            agent_instance.tool_manager.reload_tools()
            response["payload"] = {"status": "success"}
            # Broadcast an event to notify UI to refresh tool lists
            all_tools = agent_instance.tool_manager.get_all_tool_schemas()
            await connection_manager.broadcast_to_admins({"type": "available_tools_updated", "payload": {"tools": all_tools}})

        elif action == "execute_tool":
            result = await agent.execute_tool(**payload)
            response["payload"] = {"result": result}

        # Stream Control Actions
        elif action == "start_stream":
            logger.info("Start stream action received. Resetting agent memory before starting processes...")
            await agent.reset_memory()
            if not process_manager.is_running:
                process_manager.start_live_processes()
            response["payload"] = {"status": "success", "message": "Stream started"}
            # Broadcast stream status update
            status = {"is_running": process_manager.is_running, "backend_status": "running" if process_manager.is_running else "stopped"}
            await connection_manager.broadcast_to_admins({"type": "stream_status", "payload": status})

        elif action == "stop_stream":
            if process_manager.is_running:
                await process_manager.stop_live_processes()
            response["payload"] = {"status": "success", "message": "Stream stopped"}
            # Broadcast stream status update
            status = {"is_running": process_manager.is_running, "backend_status": "running" if process_manager.is_running else "stopped"}
            await connection_manager.broadcast_to_admins({"type": "stream_status", "payload": status})

        elif action == "restart_stream":
            await process_manager.stop_live_processes()
            await asyncio.sleep(1)
            process_manager.start_live_processes()
            response["payload"] = {"status": "success", "message": "Stream restarted"}
            # Broadcast stream status update
            status = {"is_running": process_manager.is_running, "backend_status": "running" if process_manager.is_running else "stopped"}
            await connection_manager.broadcast_to_admins({"type": "stream_status", "payload": status})

        elif action == "get_stream_status":
            status = {"is_running": process_manager.is_running, "backend_status": "running" if process_manager.is_running else "stopped"}
            response["payload"] = status

        # Config Management Actions
        elif action == "get_configs":
            from ..api.system import filter_config_for_frontend
            configs = filter_config_for_frontend(config_manager.settings)
            response["payload"] = configs

        elif action == "update_configs":
            from ..api.system import filter_config_for_frontend
            await config_manager.update_settings(payload)
            updated_configs = filter_config_for_frontend(config_manager.settings)
            response["payload"] = updated_configs
            await connection_manager.broadcast_to_admins({"type": "config_updated", "payload": updated_configs})

        elif action == "reload_configs":
            await config_manager.update_settings({})
            response["payload"] = {"status": "success", "message": "Configuration reloaded"}
            from ..api.system import filter_config_for_frontend
            updated_configs = filter_config_for_frontend(config_manager.settings)
            await connection_manager.broadcast_to_admins({"type": "config_updated", "payload": updated_configs})

        # Other Agent Actions
        elif action == "get_agent_context":
            context = await agent.get_message_history()
            response["payload"] = context

        elif action == "get_last_prompt":
            # This is specific to the builtin agent, as Letta doesn't expose its prompt.
            agent_instance = getattr(agent, 'agent_instance', agent)
            if not isinstance(agent_instance, LocalAgent):
                 response["payload"] = {"prompt": "The active agent does not support prompt generation introspection."}
            else:
                try:
                    # 1. Get the recent history from the agent itself
                    history = await agent_instance.get_neuro_history(limit=10)
                    
                    # 2. Reconstruct the 'messages' list that _build_neuro_prompt expects
                    messages_for_prompt = []
                    for entry in history:
                        if entry.get('role') == 'user':
                            # Content is in the format "username: text"
                            content = entry.get('content', '')
                            parts = content.split(':', 1)
                            if len(parts) == 2:
                                messages_for_prompt.append({'username': parts[0].strip(), 'text': parts[1].strip()})
                            elif content: # Handle cases where there's no colon
                                messages_for_prompt.append({'username': 'user', 'text': content})

                    # 3. Build the prompt using the agent's own internal logic
                    prompt = await agent_instance._build_neuro_prompt(messages_for_prompt)
                    response["payload"] = {"prompt": prompt}
                except Exception as e:
                    logger.error(f"Error generating last prompt: {e}", exc_info=True)
                    response["payload"] = {"prompt": f"Failed to generate prompt: {e}"}

        elif action == "reset_agent_memory":
            await agent.reset_memory()
            response["payload"] = {"status": "success"}
            # Broadcast updates for all memory types
            await connection_manager.broadcast_to_admins({"type": "core_memory_updated", "payload": await agent.get_memory_blocks()})
            await connection_manager.broadcast_to_admins({"type": "temp_memory_updated", "payload": await agent.get_temp_memory()})
            await connection_manager.broadcast_to_admins({"type": "init_memory_updated", "payload": await agent.get_init_memory()})
            await connection_manager.broadcast_to_admins({"type": "agent_context", "action": "update", "messages": await agent.get_message_history()})

        else:
            response["payload"] = {"status": "error", "message": f"Unknown action: {action}"}

        # Send the direct response to the requesting client
        if request_id:
            await websocket.send_json(response)

    except Exception as e:
        logger.error(f"Error handling admin WS message (action: {action}): {e}", exc_info=True)
        if request_id:
            response["payload"] = {"status": "error", "message": str(e)}
            await websocket.send_json(response)



