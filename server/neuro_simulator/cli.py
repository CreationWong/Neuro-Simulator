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
            logging.error(f"Working directory '{work_dir}' does not exist. Please create it first.")
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
        package_source_path = Path(__file__).parent
        
        # Helper to copy files if they don't exist
        def copy_if_not_exists(src: Path, dest: Path):
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dest)
                logging.info(f"Copied default file to {dest}")

        # Copy config.yaml.example
        copy_if_not_exists(package_source_path / "config.yaml.example", work_dir / "config.yaml.example")

        # Copy prompts
        copy_if_not_exists(package_source_path / "agent" / "neuro_prompt.txt", path_manager.path_manager.neuro_prompt_path)
        copy_if_not_exists(package_source_path / "agent" / "memory_prompt.txt", path_manager.path_manager.memory_agent_prompt_path)

        # Copy default memory JSON files
        copy_if_not_exists(package_source_path / "agent" / "memory" / "core_memory.json", path_manager.path_manager.core_memory_path)
        copy_if_not_exists(package_source_path / "agent" / "memory" / "init_memory.json", path_manager.path_manager.init_memory_path)
        copy_if_not_exists(package_source_path / "agent" / "memory" / "temp_memory.json", path_manager.path_manager.temp_memory_path)

        # Copy default assets directory
        source_assets_dir = package_source_path / "assets"
        destination_assets_dir = path_manager.path_manager.assets_dir
        if not destination_assets_dir.exists():
            shutil.copytree(source_assets_dir, destination_assets_dir)
            logging.info(f"Copied default asset directory to {destination_assets_dir}")

    except Exception as e:
        logging.warning(f"Could not copy all default files: {e}")

    # --- 4. Load Configuration ---
    from neuro_simulator.core.config import config_manager
    from pydantic import ValidationError
    import uvicorn

    main_config_path = path_manager.path_manager.working_dir / "config.yaml"
    try:
        config_manager.load(str(main_config_path))
    except FileNotFoundError:
        logging.error(f"FATAL: Configuration file '{main_config_path.name}' not found.")
        logging.error(f"If this is your first time, please rename 'config.yaml.example' to 'config.yaml' after filling it out.")
        sys.exit(1)
    except ValidationError as e:
        logging.error(f"FATAL: Configuration error in '{main_config_path.name}':")
        logging.error(e)
        sys.exit(1)
    except Exception as e:
        logging.error(f"FATAL: An unexpected error occurred while loading the configuration: {e}")
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
            reload=False
        )
    except ImportError as e:
        logging.error(f"Could not import the application. Make sure the package is installed correctly. Details: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()