# backend/stream_manager.py
import asyncio
import time
import os
import subprocess
import json

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
    
    # 新增：事件队列，用于向广播任务发送一次性事件
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
    AVATAR_INTRO_TOTAL_DURATION_SEC = 3.0 # 前端负责这个总时长内的动画

    def __init__(self):
        self._current_phase: str = self.StreamPhase.OFFLINE
        self._stream_start_global_time: float = 0.0
        self._is_neuro_speaking: bool = False
        self.reset_stream_state()
        print("LiveStreamManager 初始化完成。")

    def reset_stream_state(self):
        self._current_phase = self.StreamPhase.OFFLINE
        self._stream_start_global_time = 0.0
        self._is_neuro_speaking = False
        while not self.event_queue.empty(): # 清空事件队列
            self.event_queue.get_nowait()
        print("直播状态已重置为 OFFLINE。")

    async def start_new_stream_cycle(self):
        if self._current_phase != self.StreamPhase.OFFLINE:
            print("警告: 直播已在进行中，无法开始新周期。")
            return

        print("正在启动新的直播周期...")
        self._stream_start_global_time = time.time()
        
        # 阶段 1: 欢迎视频
        self._current_phase = self.StreamPhase.INITIALIZING
        print(f"进入阶段: {self.StreamPhase.INITIALIZING}. 等待 {self._WELCOME_VIDEO_DURATION_SEC:.2f} 秒")
        await asyncio.sleep(self._WELCOME_VIDEO_DURATION_SEC)
        
        # 阶段 2: 立绘入场
        self._current_phase = self.StreamPhase.AVATAR_INTRO
        await self.event_queue.put({"type": "start_avatar_intro"})
        print(f"进入阶段: {self.StreamPhase.AVATAR_INTRO}. 等待 {self.AVATAR_INTRO_TOTAL_DURATION_SEC} 秒 (前端动画时间)")
        await asyncio.sleep(self.AVATAR_INTRO_TOTAL_DURATION_SEC)

        # 阶段 3: 进入正常直播
        self._current_phase = self.StreamPhase.LIVE
        await self.event_queue.put({"type": "enter_live_phase"})
        print(f"进入阶段: {self.StreamPhase.LIVE}")
        
        from stream_chat import add_to_neuro_input_queue
        from config import INITIAL_NEURO_STARTUP_MESSAGE
        add_to_neuro_input_queue(INITIAL_NEURO_STARTUP_MESSAGE)
        print("已将 Neuro 首次响应消息添加到队列。")
    
    def set_neuro_speaking_status(self, speaking: bool):
        if self._is_neuro_speaking != speaking:
            self._is_neuro_speaking = speaking
            # 将说话状态的变化也作为事件放入队列
            asyncio.create_task(self.event_queue.put({"type": "neuro_is_speaking", "speaking": speaking}))

    def get_initial_state_for_client(self) -> dict:
        """为新连接的客户端获取一次性的初始状态。"""
        elapsed_time = 0.0
        if self._stream_start_global_time > 0:
            elapsed_time = time.time() - self._stream_start_global_time

        if self._current_phase == self.StreamPhase.INITIALIZING:
            return {"type": "play_welcome_video", "progress": elapsed_time}
        elif self._current_phase == self.StreamPhase.AVATAR_INTRO:
            return {"type": "start_avatar_intro"}
        elif self.StreamPhase.LIVE:
            return {"type": "enter_live_phase", "is_speaking": self._is_neuro_speaking}
        
        return {"type": "offline"} # 默认或错误状态

live_stream_manager = LiveStreamManager()