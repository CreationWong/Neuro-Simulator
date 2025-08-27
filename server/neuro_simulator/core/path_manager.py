# neuro_simulator/core/path_manager.py
"""Manages all file and directory paths for the application's working directory."""

import os
from pathlib import Path

class PathManager:
    """A centralized manager for all dynamic paths within the working directory."""

    def __init__(self, working_dir: str):
        """Initializes the PathManager and defines the directory structure."""
        self.working_dir = Path(working_dir).resolve()

        # Top-level directories
        self.agents_dir = self.working_dir / "agents"
        self.assets_dir = self.working_dir / "assets"

        # Agents subdirectories
        self.neuro_agent_dir = self.agents_dir / "neuro"
        self.memory_agent_dir = self.agents_dir / "memory_manager"
        self.shared_memories_dir = self.agents_dir / "memories"
        self.user_tools_dir = self.agents_dir / "tools"
        self.builtin_tools_dir = self.user_tools_dir / "builtin_tools"

        # Agent-specific config files
        self.neuro_config_path = self.neuro_agent_dir / "config.yaml"
        self.neuro_tools_path = self.neuro_agent_dir / "tools.json"
        self.neuro_history_path = self.neuro_agent_dir / "history.jsonl"
        self.neuro_prompt_path = self.neuro_agent_dir / "neuro_prompt.txt"

        self.memory_agent_config_path = self.memory_agent_dir / "config.yaml"
        self.memory_agent_tools_path = self.memory_agent_dir / "tools.json"
        self.memory_agent_history_path = self.memory_agent_dir / "history.jsonl"
        self.memory_agent_prompt_path = self.memory_agent_dir / "memory_prompt.txt"

        # Shared memory files
        self.init_memory_path = self.shared_memories_dir / "init_memory.json"
        self.core_memory_path = self.shared_memories_dir / "core_memory.json"
        self.temp_memory_path = self.shared_memories_dir / "temp_memory.json"

    def initialize_directories(self):
        """Creates all necessary directories if they don't exist."""
        dirs_to_create = [
            self.agents_dir,
            self.assets_dir,
            self.neuro_agent_dir,
            self.memory_agent_dir,
            self.shared_memories_dir,
            self.user_tools_dir,
            self.builtin_tools_dir
        ]
        for dir_path in dirs_to_create:
            os.makedirs(dir_path, exist_ok=True)

        # Create the warning file in the builtin_tools directory
        warning_file_path = self.builtin_tools_dir / "!!!NO-CHANGE-WILL-BE-SAVED-AFTER-RESTART!!!"
        if not warning_file_path.exists():
            warning_file_path.touch()

# A global instance that can be imported and used by other modules.
# It will be initialized on application startup.
path_manager: PathManager = None

def initialize_path_manager(working_dir: str):
    """Initializes the global path_manager instance."""
    global path_manager
    if path_manager is None:
        path_manager = PathManager(working_dir)
        path_manager.initialize_directories()
