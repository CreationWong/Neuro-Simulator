# backend/builtin_agent.py
"""Builtin agent module for Neuro Simulator"""

import asyncio
from typing import List, Dict, Union
from .config import config_manager
import time
from datetime import datetime

# Global variables
local_agent = None

async def initialize_builtin_agent():
    """Initialize the builtin agent"""
    global local_agent
    
    try:
        from .agent.core import Agent as LocalAgentImport
        from .stream_manager import live_stream_manager
        
        local_agent = LocalAgentImport(working_dir=live_stream_manager._working_dir)
        await local_agent.initialize()
    except Exception as e:
        print(f"初始化本地 Agent 失败: {e}")
        import traceback
        traceback.print_exc()
        local_agent = None

async def reset_builtin_agent_memory():
    """Reset the builtin agent's memory"""
    global local_agent
    
    if local_agent is not None:
        await local_agent.reset_all_memory()
    else:
        print("错误: 本地 Agent 未初始化，无法重置记忆。")

async def clear_builtin_agent_temp_memory():
    """Clear the builtin agent's temp memory"""
    global local_agent
    
    if local_agent is not None:
        # Reset only temp memory
        await local_agent.memory_manager.reset_temp_memory()
    else:
        print("错误: 本地 Agent 未初始化，无法清空临时记忆。")

async def clear_builtin_agent_context():
    """Clear the builtin agent's context (dialog history)"""
    global local_agent
    
    if local_agent is not None:
        # Reset only context
        await local_agent.memory_manager.reset_context()
        
        # Send context update via WebSocket to notify frontend
        from .websocket_manager import connection_manager
        await connection_manager.broadcast({
            "type": "agent_context",
            "action": "update",
            "messages": []
        })
    else:
        print("错误: 本地 Agent 未初始化，无法清空上下文。")

async def get_builtin_response(chat_messages: list[dict]) -> dict:
    """Get response from the builtin agent with detailed processing information"""
    global local_agent
    
    if local_agent is not None:
        response = await local_agent.process_messages(chat_messages)
        
        # Store processing details in temp memory
        processing_entry = {
            "id": f"proc_{int(time.time() * 1000)}",
            "content": f"Processed {len(chat_messages)} messages",
            "role": "system",
            "timestamp": datetime.now().isoformat(),
            "processing_details": response
        }
        # Convert to string for storage in temp memory
        await local_agent.memory_manager.add_temp_memory(str(processing_entry), "system")
        
        return response
    else:
        print("错误: 本地 Agent 未初始化，无法获取响应。")
        return {
            "input_messages": chat_messages,
            "llm_response": "",
            "tool_executions": [],
            "final_response": "Someone tell Vedal there is a problem with my AI.",
            "error": "Agent not initialized"
        }
