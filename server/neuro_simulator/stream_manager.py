# backend/stream_manager.py
import asyncio
import time
import os
from .config import config_manager
import neuro_simulator.shared_state as shared_state
from mutagen.mp4 import MP4, MP4StreamInfoError

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

    # Get the working directory where media files are located
    _working_dir = os.getcwd()  # This will be set by cli.py to the --dir path
    _WELCOME_VIDEO_PATH_BACKEND = os.path.join(_working_dir, "media", "neuro_start.mp4")
    _WELCOME_VIDEO_DURATION_SEC_DEFAULT = 10.0
    
    # --- NEW: 使用 mutagen 获取时长的静态方法 ---
    @staticmethod
    def _get_video_duration_mutagen_static(video_path: str) -> float:
        """使用 mutagen 库可靠地获取 MP4 视频时长。"""
        if not os.path.exists(video_path):
            print(f"警告: 视频文件 '{video_path}' 不存在。将使用默认值。")
            return LiveStreamManager._WELCOME_VIDEO_DURATION_SEC_DEFAULT
        try:
            video = MP4(video_path)
            duration = video.info.length
            print(f"已通过 mutagen 成功读取视频 '{video_path}' 时长: {duration:.2f} 秒。")
            return duration
        except MP4StreamInfoError:
            print(f"警告: mutagen 无法解析 '{video_path}' 的流信息。它可能不是一个标准的MP4文件。将使用默认值。")
            return LiveStreamManager._WELCOME_VIDEO_DURATION_SEC_DEFAULT
        except Exception as e:
            print(f"使用 mutagen 获取视频时长时出错: {e}. 将使用默认视频时长。")
            return LiveStreamManager._WELCOME_VIDEO_DURATION_SEC_DEFAULT

    # --- 核心修改点: 调用新的 mutagen 方法 ---
    _WELCOME_VIDEO_DURATION_SEC = _get_video_duration_mutagen_static(_WELCOME_VIDEO_PATH_BACKEND)
    AVATAR_INTRO_TOTAL_DURATION_SEC = 3.0

    def __init__(self):
        self._current_phase: str = self.StreamPhase.OFFLINE
        self._stream_start_global_time: float = 0.0
        self._is_neuro_speaking: bool = False
        # Note: We don't call reset_stream_state here to avoid asyncio issues during initialization
        print("LiveStreamManager 初始化完成。")

    async def broadcast_stream_metadata(self):
        """将直播元数据放入事件队列进行广播。"""
        metadata_event = {
            "type": "update_stream_metadata",
            **config_manager.settings.stream_metadata.model_dump()
        }
        await self.event_queue.put(metadata_event)
        print("直播元数据已放入广播队列。")

    def reset_stream_state(self):
        """重置直播状态到初始离线状态。"""
        self._current_phase = self.StreamPhase.OFFLINE
        self._stream_start_global_time = 0.0
        self._is_neuro_speaking = False
        while not self.event_queue.empty():
            self.event_queue.get_nowait()
        shared_state.live_phase_started_event.clear()
        print("直播状态已重置为 OFFLINE。")
        # Don't create task during initialization, will be called properly in main.py startup

    async def start_new_stream_cycle(self):
        """开始一个全新的直播周期，从欢迎视频开始。"""
        if self._current_phase != self.StreamPhase.OFFLINE:
            print("警告: 直播已在进行中，无法开始新周期。")
            return

        print("正在启动新的直播周期...")
        self._stream_start_global_time = time.time()
        
        self._current_phase = self.StreamPhase.INITIALIZING
        print(f"进入阶段: {self.StreamPhase.INITIALIZING}. 广播 'play_welcome_video' 事件。")
        await self.event_queue.put({
            "type": "play_welcome_video",
            "progress": 0,
            "elapsed_time_sec": self.get_elapsed_time()
        })
        
        print(f"等待视频时长: {self._WELCOME_VIDEO_DURATION_SEC:.2f} 秒")
        await asyncio.sleep(self._WELCOME_VIDEO_DURATION_SEC)
        
        self._current_phase = self.StreamPhase.AVATAR_INTRO
        print(f"进入阶段: {self.StreamPhase.AVATAR_INTRO}. 广播 'start_avatar_intro' 事件。")
        await self.event_queue.put({"type": "start_avatar_intro", "elapsed_time_sec": self.get_elapsed_time()})
        
        print(f"等待立绘入场动画: {self.AVATAR_INTRO_TOTAL_DURATION_SEC} 秒")
        await asyncio.sleep(self.AVATAR_INTRO_TOTAL_DURATION_SEC)

        self._current_phase = self.StreamPhase.LIVE
        print(f"进入阶段: {self.StreamPhase.LIVE}. 广播 'enter_live_phase' 事件。")
        await self.event_queue.put({"type": "enter_live_phase", "elapsed_time_sec": self.get_elapsed_time()})
        
        shared_state.live_phase_started_event.set()
        print("Live phase started event has been set.")
    
    def set_neuro_speaking_status(self, speaking: bool):
        """设置并广播Neuro是否正在说话。"""
        if self._is_neuro_speaking != speaking:
            self._is_neuro_speaking = speaking
            # Only create task if we're in an event loop
            try:
                asyncio.get_running_loop()
                asyncio.create_task(self.event_queue.put({"type": "neuro_is_speaking", "speaking": speaking}))
            except RuntimeError:
                # No running loop, just put directly (this might block)
                self.event_queue.put_nowait({"type": "neuro_is_speaking", "speaking": speaking})
    
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
        return {"type": "offline", **base_state}

# 全局单例
live_stream_manager = LiveStreamManager()