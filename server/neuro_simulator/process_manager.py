# backend/process_manager.py
import asyncio

class ProcessManager:
    """管理后台核心直播任务的生命周期。"""

    def __init__(self):
        self._tasks: list[asyncio.Task] = []
        self._is_running = False
        print("ProcessManager initialized.")

    @property
    def is_running(self) -> bool:
        """返回直播核心进程是否正在运行。"""
        return self._is_running

    def start_live_processes(self):
        """
        启动所有与直播相关的后台任务。
        这个方法会动态地从 main.py 导入任务函数，以避免循环导入。
        """
        if self.is_running:
            print("警告: 直播进程已在运行，无法重复启动。")
            return

        print("正在启动直播核心进程...")
        from .main import generate_audience_chat_task, neuro_response_cycle, broadcast_events_task
        from .stream_manager import live_stream_manager
        from .stream_chat import clear_all_queues
        from .letta import reset_neuro_agent_memory
        
        # 清理状态和队列，开始新的直播周期
        clear_all_queues()
        asyncio.create_task(reset_neuro_agent_memory())
        live_stream_manager.reset_stream_state()

        # 创建并存储任务
        self._tasks.append(asyncio.create_task(live_stream_manager.start_new_stream_cycle()))
        self._tasks.append(asyncio.create_task(broadcast_events_task()))
        self._tasks.append(asyncio.create_task(generate_audience_chat_task()))
        self._tasks.append(asyncio.create_task(neuro_response_cycle()))
        
        self._is_running = True
        print(f"直播核心进程已启动，共 {len(self._tasks)} 个任务。")

    def stop_live_processes(self):
        """停止并清理所有后台任务。"""
        if not self.is_running:
            print("信息: 直播进程未运行，无需停止。")
            return
            
        print(f"正在停止 {len(self._tasks)} 个直播核心任务...")
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        self._tasks.clear()
        self._is_running = False
        
        # 停止后，也重置一下 stream manager 的状态
        from .stream_manager import live_stream_manager
        live_stream_manager.reset_stream_state()
        
        print("所有直播核心任务已停止。")

# 创建一个全局单例
process_manager = ProcessManager()