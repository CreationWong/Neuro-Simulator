# backend/stream_chat.py
from collections import deque
# 从 config 模块导入队列大小配置
from config import AUDIENCE_CHAT_BUFFER_MAX_SIZE, NEURO_INPUT_QUEUE_MAX_SIZE

# 观众聊天消息缓冲区 (用于前端显示)
audience_chat_buffer: deque[dict] = deque(maxlen=AUDIENCE_CHAT_BUFFER_MAX_SIZE)

# Neuro LLM 的输入队列 (观众聊天和用户消息都会进入此队列)
neuro_input_queue: deque[dict] = deque(maxlen=NEURO_INPUT_QUEUE_MAX_SIZE)

def clear_all_queues():
    """清空所有聊天队列。"""
    audience_chat_buffer.clear()
    neuro_input_queue.clear()
    print("所有聊天队列已清空。")

def add_to_audience_buffer(chat_item: dict):
    """将聊天消息添加到观众显示缓冲区。"""
    audience_chat_buffer.append(chat_item)

def add_to_neuro_input_queue(chat_item: dict):
    """将聊天消息添加到 Neuro LLM 的输入队列。"""
    neuro_input_queue.append(chat_item)

def get_recent_audience_chats(limit: int) -> list[dict]:
    """获取最近的观众聊天消息。"""
    return list(audience_chat_buffer)[-limit:]

def get_all_neuro_input_chats() -> list[dict]:
    """获取所有 Neuro LLM 输入队列中的消息并清空队列。"""
    chats = list(neuro_input_queue)
    neuro_input_queue.clear()
    return chats

def is_neuro_input_queue_empty() -> bool:
    """检查 Neuro 输入队列是否为空。"""
    return not bool(neuro_input_queue)
