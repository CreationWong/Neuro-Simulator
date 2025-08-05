# backend/websocket_manager.py
from fastapi import WebSocket
from collections import deque
import asyncio
import json
from starlette.websockets import WebSocketState # 确保导入 WebSocketState

class WebSocketManager:
    """管理所有活动的 WebSocket 连接，并提供消息广播功能。"""
    def __init__(self):
        self.active_connections: deque[WebSocket] = deque()
        print("WebSocketManager 初始化完成。")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket 客户端已连接。当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                print(f"WebSocket 客户端已断开连接。当前连接数: {len(self.active_connections)}")
        except Exception as e:
            print(f"断开 WebSocket 连接时出错: {e}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"发送个人消息时出错，客户端可能已断开: {e}")
                self.disconnect(websocket)

    async def broadcast(self, message: dict):
        disconnected_sockets = []
        for connection in list(self.active_connections): 
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"广播消息时出错，客户端 {connection} 可能已断开: {e}")
                    disconnected_sockets.append(connection)
            else:
                disconnected_sockets.append(connection)
        
        for disconnected_socket in disconnected_sockets:
            self.disconnect(disconnected_socket)

# --- 核心修改点：只创建一个实例 ---
connection_manager = WebSocketManager()