# backend/stream_chat.py
from collections import deque
from config import settings # <-- 核心变化

# 使用 settings 对象来初始化 deque 的 maxlen
audience_chat_buffer: deque[dict] = deque(maxlen=settings.performance.audience_chat_buffer_max_size)
neuro_input_queue: deque[dict] = deque(maxlen=settings.performance.neuro_input_queue_max_size)

def clear_all_queues():
    audience_chat_buffer.clear()
    neuro_input_queue.clear()
    print("所有聊天队列已清空。")

def add_to_audience_buffer(chat_item: dict):
    audience_chat_buffer.append(chat_item)

def add_to_neuro_input_queue(chat_item: dict):
    neuro_input_queue.append(chat_item)

def get_recent_audience_chats(limit: int) -> list[dict]:
    return list(audience_chat_buffer)[-limit:]

def get_all_neuro_input_chats() -> list[dict]:
    chats = list(neuro_input_queue)
    neuro_input_queue.clear()
    return chats

def is_neuro_input_queue_empty() -> bool:
    return not bool(neuro_input_queue)