# backend/log_handler.py
import logging
from collections import deque
from typing import Deque

# 创建两个独立的、有界限的队列，用于不同来源的日志
server_log_queue: Deque[str] = deque(maxlen=1000)
agent_log_queue: Deque[str] = deque(maxlen=1000)

class QueueLogHandler(logging.Handler):
    """一个将日志记录发送到指定队列的处理器。"""
    def __init__(self, queue: Deque[str]):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        self.queue.append(log_entry)

def configure_server_logging():
    """配置服务器（根）日志记录器，将其日志发送到 server_log_queue。"""
    # 为服务器日志创建一个处理器实例
    server_queue_handler = QueueLogHandler(server_log_queue)
    formatter = logging.Formatter('%(asctime)s - [SERVER] - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    server_queue_handler.setFormatter(formatter)
    
    # 获取根 logger 并添加 handler
    # 这将捕获所有未被专门处理的日志（来自fastapi, uvicorn等）
    root_logger = logging.getLogger()
    # 清除可能存在的旧handler，以防万一
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(server_queue_handler)
    root_logger.setLevel(logging.INFO)

    # 将 uvicorn 的日志也引导到我们的 handler
    logging.getLogger("uvicorn.access").handlers = [server_queue_handler]
    logging.getLogger("uvicorn.error").handlers = [server_queue_handler]

    print("服务器日志系统已配置，将日志输出到 server_log_queue。")

# Agent 的日志配置将会在 agent 模块内部完成，以保持解耦
