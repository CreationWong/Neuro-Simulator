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
    
    # 1. Set working directory
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

    # 2. Initialize paths and load configuration
    from neuro_simulator.core import path_manager
    from neuro_simulator.core.config import config_manager
    import uvicorn

    path_manager.initialize_path_manager(os.getcwd())

    # Define example_path early for config loading
    example_path = Path(__file__).parent / "config.yaml.example"

    # 2.2. Copy default config.yaml.example if it doesn't exist
    try:
        source_config_example = example_path
        destination_config_example = path_manager.path_manager.working_dir / "config.yaml.example"
        if not destination_config_example.exists():
            shutil.copy(source_config_example, destination_config_example)
            logging.info(f"Copyed default config.yaml.example to {destination_config_example}")
    except Exception as e:
        logging.warning(f"Could not copy default config.yaml.example: {e}")

    main_config_path = path_manager.path_manager.working_dir / "config.yaml"
    config_manager.load_and_validate(str(main_config_path), str(example_path))

    # 2.5. Copy default prompt templates if they don't exist
    try:
        # Use Path(__file__).parent for robust path resolution
        base_path = Path(__file__).parent
        neuro_prompt_example = base_path / "agent" / "neuro_prompt.txt"
        memory_prompt_example = base_path / "agent" / "memory_prompt.txt"

        if not path_manager.path_manager.neuro_prompt_path.exists():
            shutil.copy(neuro_prompt_example, path_manager.path_manager.neuro_prompt_path)
            logging.info(f"Copied default neuro prompt to {path_manager.path_manager.neuro_prompt_path}")
        if not path_manager.path_manager.memory_agent_prompt_path.exists():
            shutil.copy(memory_prompt_example, path_manager.path_manager.memory_agent_prompt_path)
            logging.info(f"Copied default memory prompt to {path_manager.path_manager.memory_agent_prompt_path}")

        # Copy default memory JSON files if they don't exist
        memory_files = {
            "core_memory.json": path_manager.path_manager.core_memory_path,
            "init_memory.json": path_manager.path_manager.init_memory_path,
            "temp_memory.json": path_manager.path_manager.temp_memory_path,
        }
        for filename, dest_path in memory_files.items():
            src_path = base_path / "agent" / "memory" / filename
            if not dest_path.exists():
                shutil.copy(src_path, dest_path)
                logging.info(f"Copied default {filename} to {dest_path}")

        # Copy default assets directory if it doesn't exist
        source_assets_dir = base_path / "assets"
        destination_assets_dir = path_manager.path_manager.assets_dir
        
        # Ensure the destination assets directory exists
        destination_assets_dir.mkdir(parents=True, exist_ok=True)

        # Copy individual files from source assets to destination assets
        for item in source_assets_dir.iterdir():
            if item.is_file():
                dest_file = destination_assets_dir / item.name
                if not dest_file.exists():
                    shutil.copy(item, dest_file)
                    logging.info(f"Copied asset {item.name} to {dest_file}")
            elif item.is_dir():
                # Recursively copy subdirectories if they don't exist
                dest_subdir = destination_assets_dir / item.name
                if not dest_subdir.exists():
                    shutil.copytree(item, dest_subdir)
                    logging.info(f"Copied asset directory {item.name} to {dest_subdir}")
    except Exception as e:
        logging.warning(f"Could not copy default prompt templates, memory files, or assets: {e}")

    # 3. Determine server host and port
    server_host = args.host or config_manager.settings.server.host
    server_port = args.port or config_manager.settings.server.port

    # 4. Run the server
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