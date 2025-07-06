# backend/log_handler.py
import logging
import asyncio
from collections import deque

# 使用 deque 作为有界队列，避免内存无限增长
log_queue: deque = deque(maxlen=1000)

class QueueLogHandler(logging.Handler):
    """一个将日志记录发送到队列的处理器。"""
    def emit(self, record: logging.LogRecord):
        # 格式化日志消息
        log_entry = self.format(record)
        log_queue.append(log_entry)

def configure_logging():
    """配置全局日志，添加我们的队列处理器。"""
    queue_handler = QueueLogHandler()
    # 设置一个你喜欢的日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    queue_handler.setFormatter(formatter)
    
    # 获取根 logger 并添加我们的 handler
    # 这将捕获来自所有模块（fastapi, uvicorn, letta等）的日志
    root_logger = logging.getLogger()
    root_logger.addHandler(queue_handler)
    root_logger.setLevel(logging.INFO)

    print("日志系统已配置，将日志输出到内部队列。")