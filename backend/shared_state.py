# backend/shared_state.py
import asyncio

# 用来同步直播进入 LIVE 阶段的信号
live_phase_started_event = asyncio.Event()

# --- 用于在任务间共享 Neuro 的最新发言 ---
# 使用一个锁来确保在读写时不会发生冲突
neuro_last_speech_lock = asyncio.Lock()
# 存储 Neuro 最新一次完整发言的文本，并提供一个初始值
neuro_last_speech: str = "Neuro-Sama has just started the stream and hasn't said anything yet."