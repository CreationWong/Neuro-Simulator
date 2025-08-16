#!/usr/bin/env python3
"""Command-line interface for the Neuro-Simulator Server."""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

def copy_resource(package_name: str, resource_path: str, destination_path: Path, is_dir: bool = False):
    """A helper function to copy a resource from the package to the working directory."""
    if destination_path.exists():
        return

    try:
        import pkg_resources
        source_path_str = pkg_resources.resource_filename(package_name, resource_path)
        source_path = Path(source_path_str)
    except (ModuleNotFoundError, KeyError):
        source_path = Path(__file__).parent / resource_path

    if source_path.exists():
        try:
            if is_dir:
                shutil.copytree(source_path, destination_path)
            else:
                shutil.copy(source_path, destination_path)
            logging.info(f"Created '{destination_path}' from package resource.")
        except Exception as e:
            logging.warning(f"Could not copy resource '{resource_path}'. Error: {e}")
    else:
        logging.warning(f"Resource '{resource_path}' not found in package or development folder.")

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

    # 2. Ensure required assets and configs exist
    copy_resource('neuro_simulator', 'core/config.yaml.example', work_dir / 'config.yaml.example')
    copy_resource('neuro_simulator', 'assets', work_dir / 'assets', is_dir=True)
    agent_memory_dir = work_dir / "agent" / "memory"
    agent_memory_dir.mkdir(parents=True, exist_ok=True)
    for filename in ["context.json", "core_memory.json", "dialog_history.json", "init_memory.json"]:
        copy_resource('neuro_simulator', f'agent/memory/{filename}', agent_memory_dir / filename)

    # 3. Validate essential files
    errors = []
    if not (work_dir / "config.yaml").exists():
        errors.append(f"'config.yaml' not found in '{work_dir}'. Please copy 'config.yaml.example' to 'config.yaml' and configure it.")
    if not (work_dir / "assets" / "neuro_start.mp4").exists():
        errors.append(f"Required file 'neuro_start.mp4' not found in '{work_dir / 'assets'}'.")

    if errors:
        for error in errors:
            logging.error(error)
        sys.exit(1)

    # 4. Import and run the server
    try:
        from neuro_simulator.core.application import run_server
        logging.info("Starting Neuro-Simulator server...")
        # The full application logger will take over from here
        run_server(args.host, args.port)
    except ImportError as e:
        logging.error(f"Could not import the application. Make sure the package is installed correctly. Details: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()