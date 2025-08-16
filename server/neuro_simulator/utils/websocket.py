# neuro_simulator/utils/websocket.py
import asyncio
import json
import logging
from collections import deque

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

class WebSocketManager:
    """Manages all active WebSocket connections and provides broadcasting capabilities."""
    def __init__(self):
        self.active_connections: deque[WebSocket] = deque()
        logger.info("WebSocketManager initialized.")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Could not send personal message, client likely disconnected: {e}")
                self.disconnect(websocket)

    async def broadcast(self, message: dict):
        disconnected_sockets = []
        for connection in list(self.active_connections):
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Could not broadcast message to client {connection}, it may have disconnected: {e}")
                    disconnected_sockets.append(connection)
            else:
                disconnected_sockets.append(connection)
        
        for disconnected_socket in disconnected_sockets:
            self.disconnect(disconnected_socket)

# Global singleton instance
connection_manager = WebSocketManager()
