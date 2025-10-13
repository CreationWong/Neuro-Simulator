#!/usr/bin/env python3
"""Command-line interface for the Neuro-Simulator Server."""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Neuro-Simulator Server")
    parser.add_argument("-D", "--dir", help="Working directory for config and data")
    parser.add_argument("-H", "--host", help="Host to bind the server to")
    parser.add_argument("-P", "--port", type=int, help="Port to bind the server to")

    args = parser.parse_args()

    # --- 1. Setup Working Directory ---
    if args.dir:
        work_dir = Path(args.dir).resolve()
        if not work_dir.exists():
            logging.error(
                f"Working directory '{work_dir}' does not exist. Please create it first."
            )
            sys.exit(1)
    else:
        work_dir = Path.home() / ".config" / "neuro-simulator"
        work_dir.mkdir(parents=True, exist_ok=True)

    os.chdir(work_dir)
    logging.info(f"Using working directory: {work_dir}")

    # --- 2. Initialize Path Manager ---
    from neuro_simulator.core import path_manager

    path_manager.initialize_path_manager(os.getcwd())

    # --- 3. First-Run Environment Initialization ---
    # This block ensures that a new user has all the necessary default files.
    try:
        # Define the default configuration data, mirroring the old config.yaml
        DEFAULT_CONFIG_DATA = {
            "llm_providers": [],
            "tts_providers": [],
            "neuro": {
                "neuro_llm_provider_id": None,
                "neuro_memory_llm_provider_id": None,
                "tts_provider_id": None,
                "input_chat_sample_size": 10,
                "post_speech_cooldown_sec": 1.0,
                "initial_greeting": "The stream has just started. Greet your audience and say hello!",
                "neuro_input_queue_max_size": 200,
                "reflection_threshold": 5,
            },
            "chatbot": {
                "chatbot_llm_provider_id": None,
                "chatbot_memory_llm_provider_id": None,
                "generation_interval_sec": 3,
                "chats_per_batch": 2,
                "reflection_threshold": 50,
                "nickname_generation": {
                    "enable_dynamic_pool": True,
                    "dynamic_pool_size": 50,
                },
            },
            "stream": {
                "streamer_nickname": "vedal987",
                "stream_title": "neuro-sama is here for u all",
                "stream_category": "谈天说地",
                "stream_tags": [
                    "Vtuber",
                    "AI",
                    "Cute",
                    "English",
                    "Gremlin",
                    "catgirl",
                ],
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8000,
                "panel_password": "your-secret-api-token-here",
                "client_origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
                "audience_chat_buffer_max_size": 1000,
                "initial_chat_backlog_limit": 50,
            },
        }

        main_config_path = path_manager.path_manager.working_dir / "config.yaml"

        # Generate config.yaml if it doesn't exist
        if not main_config_path.exists():
            logging.info(f"Config file not found. Generating default config at {main_config_path}")
            import yaml
            from neuro_simulator.core.config import AppSettings

            validated_settings = AppSettings.model_validate(DEFAULT_CONFIG_DATA)
            config_to_write = validated_settings.model_dump(exclude_none=True)
            
            with open(main_config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_to_write, f, sort_keys=False, allow_unicode=True)
            logging.info("Successfully generated default config file.")

        # --- Copy other asset and prompt files ---
        package_source_path = Path(__file__).parent

        def copy_if_not_exists(src: Path, dest: Path):
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dest)
                logging.info(f"Copied default file to {dest}")

        # --- Copy Neuro Agent Files ---
        neuro_source_path = package_source_path / "agents" / "neuro"
        copy_if_not_exists(
            neuro_source_path / "prompts" / "neuro_prompt.txt",
            path_manager.path_manager.neuro_prompt_path,
        )
        copy_if_not_exists(
            neuro_source_path / "prompts" / "memory_prompt.txt",
            path_manager.path_manager.memory_agent_prompt_path,
        )
        copy_if_not_exists(
            neuro_source_path / "memory" / "core_memory.json",
            path_manager.path_manager.core_memory_path,
        )
        copy_if_not_exists(
            neuro_source_path / "memory" / "init_memory.json",
            path_manager.path_manager.init_memory_path,
        )
        copy_if_not_exists(
            neuro_source_path / "memory" / "temp_memory.json",
            path_manager.path_manager.temp_memory_path,
        )

        # --- Copy Chatbot Agent Files ---
        chatbot_source_path = package_source_path / "agents" / "chatbot"
        copy_if_not_exists(
            chatbot_source_path / "prompts" / "chatbot_prompt.txt",
            path_manager.path_manager.chatbot_prompt_path,
        )
        copy_if_not_exists(
            chatbot_source_path / "prompts" / "memory_prompt.txt",
            path_manager.path_manager.chatbot_memory_agent_prompt_path,
        )
        copy_if_not_exists(
            chatbot_source_path / "memory" / "init_memory.json",
            path_manager.path_manager.chatbot_init_memory_path,
        )
        copy_if_not_exists(
            chatbot_source_path / "memory" / "core_memory.json",
            path_manager.path_manager.chatbot_core_memory_path,
        )
        copy_if_not_exists(
            chatbot_source_path / "memory" / "temp_memory.json",
            path_manager.path_manager.chatbot_temp_memory_path,
        )
        copy_if_not_exists(
            chatbot_source_path / "nickname_gen" / "data" / "adjectives.txt",
            path_manager.path_manager.chatbot_nickname_data_dir / "adjectives.txt",
        )
        copy_if_not_exists(
            chatbot_source_path / "nickname_gen" / "data" / "nouns.txt",
            path_manager.path_manager.chatbot_nickname_data_dir / "nouns.txt",
        )
        copy_if_not_exists(
            chatbot_source_path / "nickname_gen" / "data" / "special_users.txt",
            path_manager.path_manager.chatbot_nickname_data_dir / "special_users.txt",
        )

        # --- Copy Shared Assets ---
        copy_if_not_exists(
            package_source_path / "assets" / "neuro_start.mp4",
            path_manager.path_manager.assets_dir / "neuro_start.mp4",
        )

    except Exception as e:
        logging.warning(f"Could not copy all default files: {e}")

    # --- 4. Load Configuration ---
    from neuro_simulator.core.config import config_manager
    from pydantic import ValidationError
    import uvicorn

    main_config_path = path_manager.path_manager.working_dir / "config.yaml"
    try:
        config_manager.load(str(main_config_path))
    except ValidationError as e:
        logging.error(f"FATAL: Configuration error in '{main_config_path.name}':")
        logging.error(e)
        sys.exit(1)
    except Exception as e:
        logging.error(
            f"FATAL: An unexpected error occurred while loading the configuration: {e}"
        )
        sys.exit(1)

    # --- 5. Determine Server Host and Port ---
    # Command-line arguments override config file settings
    server_host = args.host or config_manager.settings.server.host
    server_port = args.port or config_manager.settings.server.port

    # --- 6. Run the Server ---
    logging.info(f"Starting Neuro-Simulator server on {server_host}:{server_port}...")
    try:
        uvicorn.run(
            "neuro_simulator.core.application:app",
            host=server_host,
            port=server_port,
            reload=False,
        )
    except ImportError as e:
        logging.error(
            f"Could not import the application. Make sure the package is installed correctly. Details: {e}",
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
