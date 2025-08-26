# neuro_simulator/utils/process.py
import asyncio
import logging

from ..services.stream import live_stream_manager
from .websocket import connection_manager

logger = logging.getLogger(__name__.replace("neuro_simulator", "server", 1))

class ProcessManager:
    """Manages the lifecycle of core background tasks for the stream."""

    def __init__(self):
        self._tasks: list[asyncio.Task] = []
        self._is_running = False
        logger.info("ProcessManager initialized.")

    @property
    def is_running(self) -> bool:
        """Returns True if the core stream processes are running."""
        return self._is_running

    def start_live_processes(self):
        """
        Starts all background tasks related to the live stream.
        Imports are done locally to prevent circular dependencies.
        """
        if self.is_running:
            logger.warning("Processes are already running.")
            return

        logger.info("Starting core stream processes...")
        from ..core.application import generate_audience_chat_task, neuro_response_cycle, broadcast_events_task
        from ..utils.queue import clear_all_queues
        from ..core.agent_factory import create_agent
        from ..utils.websocket import connection_manager
        
        asyncio.create_task(create_agent())
        
        clear_all_queues()
        live_stream_manager.reset_stream_state()

        self._tasks.append(asyncio.create_task(live_stream_manager.start_new_stream_cycle()))
        self._tasks.append(asyncio.create_task(broadcast_events_task()))
        self._tasks.append(asyncio.create_task(generate_audience_chat_task()))
        self._tasks.append(asyncio.create_task(neuro_response_cycle()))
        
        self._is_running = True
        # Broadcast stream status update
        status = {"is_running": self._is_running, "backend_status": "running" if self._is_running else "stopped"}
        asyncio.create_task(connection_manager.broadcast_to_admins({"type": "stream_status", "payload": status}))
        logger.info(f"Core processes started: {len(self._tasks)} tasks.")

    async def stop_live_processes(self):
        """Stops and cleans up all running background tasks."""
        if not self.is_running:
            return
        
        logger.info("Broadcasting offline message before stopping tasks...")
        await connection_manager.broadcast({"type": "offline"})
        await asyncio.sleep(0.1) # Give a brief moment for the message to be sent
            
        logger.info(f"Stopping {len(self._tasks)} core tasks...")
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        self._tasks.clear()
        self._is_running = False
        
        live_stream_manager.reset_stream_state()
        
        # Broadcast stream status update
        status = {"is_running": self._is_running, "backend_status": "running" if self._is_running else "stopped"}
        await connection_manager.broadcast_to_admins({"type": "stream_status", "payload": status})
        
        logger.info("All core tasks have been stopped.")

# Global singleton instance
process_manager = ProcessManager()