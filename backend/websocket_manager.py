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
        """处理新的 WebSocket 连接。"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket 客户端已连接。当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """处理 WebSocket 断开连接。"""
        try:
            # 检查连接是否在列表中，避免 ValueError
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                print(f"WebSocket 客户端已断开连接。当前连接数: {len(self.active_connections)}")
            else:
                print("尝试移除一个不在列表中的 WebSocket 连接 (可能已通过其他方式断开)。")
        except Exception as e:
            print(f"断开 WebSocket 连接时出错: {e}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """向单个 WebSocket 客户端发送 JSON 消息。"""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(message)
            except RuntimeError as e: # 捕获运行时错误，如 WebSocket disconnected
                print(f"发送个人消息失败，客户端可能已断开: {e}")
                self.disconnect(websocket)
            except Exception as e:
                print(f"发送个人消息时发生未知错误: {e}")
                self.disconnect(websocket)
        else:
            print(f"尝试向未连接的 WebSocket 发送消息: {websocket.client_state}")
            self.disconnect(websocket)


    async def broadcast(self, message: dict):
        """向所有连接的 WebSocket 客户端广播 JSON 消息。"""
        disconnected_sockets = []
        # 遍历副本以安全地从原始列表中移除
        for connection in list(self.active_connections): 
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_json(message)
                except RuntimeError as e: # 捕获运行时错误，如 WebSocket disconnected
                    print(f"广播消息失败，客户端 {connection} 可能已断开: {e}")
                    disconnected_sockets.append(connection)
                except Exception as e:
                    print(f"向客户端 {connection} 广播消息时发生未知错误: {e}")
                    disconnected_sockets.append(connection)
            else:
                print(f"广播时发现未连接的 WebSocket {connection.client_state}。")
                disconnected_sockets.append(connection)
        
        for disconnected_socket in disconnected_sockets:
            self.disconnect(disconnected_socket)
        
        if disconnected_sockets:
            print(f"广播后移除了 {len(disconnected_sockets)} 个断开的连接。")


# 为每种 WebSocket 类型创建单独的管理器实例
# 这样可以隔离不同类型的 WebSocket 客户端（例如 Neuro 语音流 vs 观众聊天显示）
# 理论上 Neuro TTS 应该只有一个客户端连接，而观众聊天显示可以有多个
neuro_tts_ws_manager = WebSocketManager()
audience_chat_ws_manager = WebSocketManager()