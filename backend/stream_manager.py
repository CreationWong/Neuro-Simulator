# backend/stream_manager.py
import asyncio
import time
import os
import subprocess
import json
from config import settings
from shared_state import live_phase_started_event

class LiveStreamManager:
    class NeuroAvatarStage:
        HIDDEN = "hidden"
        STEP1 = "step1"
        STEP2 = "step2"

    class StreamPhase:
        OFFLINE = "offline"
        INITIALIZING = "initializing"
        AVATAR_INTRO = "avatar_intro"
        LIVE = "live"
    
    event_queue: asyncio.Queue = asyncio.Queue()

    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _WELCOME_VIDEO_PATH_BACKEND = os.path.join(_current_dir, "media", "neuro_start.mp4")
    _WELCOME_VIDEO_DURATION_SEC_DEFAULT = 10.0
    _WELCOME_VIDEO_DURATION_SEC = _WELCOME_VIDEO_DURATION_SEC_DEFAULT

    @staticmethod
    def _get_video_duration_ffprobe_static(video_path: str) -> float:
        if not os.path.exists(video_path):
            print(f"警告: 视频文件 '{video_path}' 不存在。将使用默认值。")
            return LiveStreamManager._WELCOME_VIDEO_DURATION_SEC_DEFAULT
        try:
            command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "format=duration", "-of", "json", video_path]
            # 尝试静默运行ffprobe -h检查是否存在
            subprocess.run(["ffprobe", "-h"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=10)
            duration = float(json.loads(result.stdout)["format"]["duration"])
            print(f"已成功读取视频 '{video_path}' 时长: {duration:.2f} 秒。")
            return duration
        except Exception as e:
            print(f"获取视频时长时出错: {e}. 将使用默认视频时长。")
            return LiveStreamManager._WELCOME_VIDEO_DURATION_SEC_DEFAULT

    # 初始化时获取一次时长
    _WELCOME_VIDEO_DURATION_SEC = _get_video_duration_ffprobe_static(_WELCOME_VIDEO_PATH_BACKEND)
    AVATAR_INTRO_TOTAL_DURATION_SEC = 3.0

    def __init__(self):
        self._current_phase: str = self.StreamPhase.OFFLINE
        self._stream_start_global_time: float = 0.0
        self._is_neuro_speaking: bool = False
        self.reset_stream_state()
        print("LiveStreamManager 初始化完成。")

    async def broadcast_stream_metadata(self):
        """将直播元数据放入事件队列进行广播。"""
        metadata_event = {
            "type": "update_stream_metadata",
            **settings.stream_metadata.model_dump()
        }
        await self.event_queue.put(metadata_event)
        print("直播元数据已放入广播队列。")

    def reset_stream_state(self):
        """重置直播状态到初始离线状态。"""
        self._current_phase = self.StreamPhase.OFFLINE
        self._stream_start_global_time = 0.0
        self._is_neuro_speaking = False
        # 清空事件队列中可能残留的事件
        while not self.event_queue.empty():
            self.event_queue.get_nowait()
        live_phase_started_event.clear()
        print("直播状态已重置为 OFFLINE。")
        # 重置后广播离线状态，让客户端UI同步
        asyncio.create_task(self.event_queue.put(self.get_initial_state_for_client()))


    async def start_new_stream_cycle(self):
        """开始一个全新的直播周期，从欢迎视频开始。"""
        if self._current_phase != self.StreamPhase.OFFLINE:
            print("警告: 直播已在进行中，无法开始新周期。")
            return

        print("正在启动新的直播周期...")
        self._stream_start_global_time = time.time()
        
        # --- 核心修复点 ---
        # 阶段1: 欢迎视频
        self._current_phase = self.StreamPhase.INITIALIZING
        print(f"进入阶段: {self.StreamPhase.INITIALIZING}. 广播 'play_welcome_video' 事件。")
        # 立即广播“播放视频”事件，而不是静默等待
        await self.event_queue.put({
            "type": "play_welcome_video",
            "progress": 0,  # 强制从头开始播放
            "elapsed_time_sec": self.get_elapsed_time()
        })
        
        # 等待视频播放完毕
        print(f"等待视频时长: {self._WELCOME_VIDEO_DURATION_SEC:.2f} 秒")
        await asyncio.sleep(self._WELCOME_VIDEO_DURATION_SEC)
        
        # 阶段2: 立绘入场
        self._current_phase = self.StreamPhase.AVATAR_INTRO
        print(f"进入阶段: {self.StreamPhase.AVATAR_INTRO}. 广播 'start_avatar_intro' 事件。")
        await self.event_queue.put({"type": "start_avatar_intro", "elapsed_time_sec": self.get_elapsed_time()})
        
        # 等待立绘入场动画完成
        print(f"等待立绘入场动画: {self.AVATAR_INTRO_TOTAL_DURATION_SEC} 秒")
        await asyncio.sleep(self.AVATAR_INTRO_TOTAL_DURATION_SEC)

        # 阶段3: 进入直播
        self._current_phase = self.StreamPhase.LIVE
        print(f"进入阶段: {self.StreamPhase.LIVE}. 广播 'enter_live_phase' 事件。")
        await self.event_queue.put({"type": "enter_live_phase", "elapsed_time_sec": self.get_elapsed_time()})
        
        # 设置事件，让 neuro_response_cycle 等待的任务可以开始运行
        live_phase_started_event.set()
        print("Live phase started event has been set.")
    
    def set_neuro_speaking_status(self, speaking: bool):
        """设置并广播Neuro是否正在说话。"""
        if self._is_neuro_speaking != speaking:
            self._is_neuro_speaking = speaking
            asyncio.create_task(self.event_queue.put({"type": "neuro_is_speaking", "speaking": speaking}))
    
    def get_elapsed_time(self) -> float:
        """获取从直播开始到现在的总时长（秒）。"""
        if self._stream_start_global_time > 0:
            return time.time() - self._stream_start_global_time
        return 0.0

    def get_initial_state_for_client(self) -> dict:
        """为新连接的客户端生成当前的初始状态事件。"""
        elapsed_time = self.get_elapsed_time()
        base_state = {"elapsed_time_sec": elapsed_time}
        if self._current_phase == self.StreamPhase.INITIALIZING:
            return {"type": "play_welcome_video", "progress": elapsed_time, **base_state}
        elif self._current_phase == self.StreamPhase.AVATAR_INTRO:
            return {"type": "start_avatar_intro", **base_state}
        elif self._current_phase == self.StreamPhase.LIVE:
            return {"type": "enter_live_phase", "is_speaking": self._is_neuro_speaking, **base_state}
        # 默认返回 OFFLINE 状态
        return {"type": "offline", **base_state}

# 全局单例
live_stream_manager = LiveStreamManager()