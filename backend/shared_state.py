# backend/shared_state.py
import asyncio

# 这个 asyncio.Event 将被 main.py 和 stream_manager.py 共享
# 用来同步直播进入 LIVE 阶段的信号
live_phase_started_event = asyncio.Event()