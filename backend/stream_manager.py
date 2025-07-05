# backend/stream_manager.py
import asyncio
import time
import os
import subprocess
import json
from config import settings # <-- 核心变化
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
            subprocess.run(["ffprobe", "-h"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=10)
            duration = float(json.loads(result.stdout)["format"]["duration"])
            print(f"已成功读取视频 '{video_path}' 时长: {duration:.2f} 秒。")
            return duration
        except Exception as e:
            print(f"获取视频时长时出错: {e}. 将使用默认视频时长。")
            return LiveStreamManager._WELCOME_VIDEO_DURATION_SEC_DEFAULT

    _WELCOME_VIDEO_DURATION_SEC = _get_video_duration_ffprobe_static(_WELCOME_VIDEO_PATH_BACKEND)
    AVATAR_INTRO_TOTAL_DURATION_SEC = 3.0

    def __init__(self):
        self._current_phase: str = self.StreamPhase.OFFLINE
        self._stream_start_global_time: float = 0.0
        self._is_neuro_speaking: bool = False
        self.reset_stream_state()
        print("LiveStreamManager 初始化完成。")

    async def broadcast_stream_metadata(self):
        """
        将 settings 对象中的直播元数据打包并放入事件队列进行广播。
        """
        # 使用 settings 对象来获取元数据
        metadata_event = {
            "type": "update_stream_metadata",
            **settings.stream_metadata.model_dump() # <-- 核心变化
        }
        await self.event_queue.put(metadata_event)
        print("直播元数据已放入广播队列。")

    def reset_stream_state(self):
        self._current_phase = self.StreamPhase.OFFLINE
        self._stream_start_global_time = 0.0
        self._is_neuro_speaking = False
        while not self.event_queue.empty():
            self.event_queue.get_nowait()
        live_phase_started_event.clear()
        print("直播状态已重置为 OFFLINE。")

    async def start_new_stream_cycle(self):
        if self._current_phase != self.StreamPhase.OFFLINE:
            print("警告: 直播已在进行中，无法开始新周期。")
            return

        print("正在启动新的直播周期...")
        self._stream_start_global_time = time.time()
        
        self._current_phase = self.StreamPhase.INITIALIZING
        print(f"进入阶段: {self.StreamPhase.INITIALIZING}. 等待 {self._WELCOME_VIDEO_DURATION_SEC:.2f} 秒")
        await asyncio.sleep(self._WELCOME_VIDEO_DURATION_SEC)
        
        self._current_phase = self.StreamPhase.AVATAR_INTRO
        await self.event_queue.put({"type": "start_avatar_intro", "elapsed_time_sec": self.get_elapsed_time()})
        print(f"进入阶段: {self.StreamPhase.AVATAR_INTRO}. 等待 {self.AVATAR_INTRO_TOTAL_DURATION_SEC} 秒")
        await asyncio.sleep(self.AVATAR_INTRO_TOTAL_DURATION_SEC)

        self._current_phase = self.StreamPhase.LIVE
        await self.event_queue.put({"type": "enter_live_phase", "elapsed_time_sec": self.get_elapsed_time()})
        print(f"进入阶段: {self.StreamPhase.LIVE}")
        
        live_phase_started_event.set()
        print("Live phase started event has been set.")
    
    def set_neuro_speaking_status(self, speaking: bool):
        if self._is_neuro_speaking != speaking:
            self._is_neuro_speaking = speaking
            asyncio.create_task(self.event_queue.put({"type": "neuro_is_speaking", "speaking": speaking}))
    
    def get_elapsed_time(self) -> float:
        if self._stream_start_global_time > 0:
            return time.time() - self._stream_start_global_time
        return 0.0

    def get_initial_state_for_client(self) -> dict:
        elapsed_time = self.get_elapsed_time()
        base_state = {"elapsed_time_sec": elapsed_time}
        if self._current_phase == self.StreamPhase.INITIALIZING:
            return {"type": "play_welcome_video", "progress": elapsed_time, **base_state}
        elif self._current_phase == self.StreamPhase.AVATAR_INTRO:
            return {"type": "start_avatar_intro", **base_state}
        elif self._current_phase == self.StreamPhase.LIVE:
            return {"type": "enter_live_phase", "is_speaking": self._is_neuro_speaking, **base_state}
        return {"type": "offline", **base_state}

live_stream_manager = LiveStreamManager()