#!/usr/bin/env python3

import argparse
import os
import sys
import shutil
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Neuro-Simulator Server")
    parser.add_argument("-D", "--dir", help="Working directory containing settings.yaml")
    parser.add_argument("-H", "--host", help="Host to bind the server to")
    parser.add_argument("-P", "--port", type=int, help="Port to bind the server to")
    
    args = parser.parse_args()
    
    # Set working directory
    if args.dir:
        work_dir = Path(args.dir).resolve()
        # If the directory doesn't exist (and it's not the default), raise an error
        if not work_dir.exists():
            print(f"Error: Working directory '{work_dir}' does not exist. Please create it manually.")
            sys.exit(1)
    else:
        work_dir = Path.home() / ".config" / "neuro-simulator"
        work_dir.mkdir(parents=True, exist_ok=True)
    
    # Change to working directory
    os.chdir(work_dir)
    
    # Handle settings.yaml.example
    settings_example_path = work_dir / "settings.yaml.example"
    settings_path = work_dir / "settings.yaml"
    
    # Copy settings.yaml.example from package if it doesn't exist
    if not settings_example_path.exists():
        try:
            # Try pkg_resources first (for installed packages)
            try:
                import pkg_resources
                example_path = pkg_resources.resource_filename('neuro_simulator', 'settings.yaml.example')
                if os.path.exists(example_path):
                    shutil.copy(example_path, settings_example_path)
                    print(f"Created {settings_example_path} from package example")
                else:
                    # Fallback to relative path (for development mode)
                    dev_example_path = Path(__file__).parent / "settings.yaml.example"
                    if dev_example_path.exists():
                        shutil.copy(dev_example_path, settings_example_path)
                        print(f"Created {settings_example_path} from development example")
                    else:
                        print("Warning: settings.yaml.example not found in package or development folder")
            except Exception:
                # Fallback to relative path (for development mode)
                dev_example_path = Path(__file__).parent / "settings.yaml.example"
                if dev_example_path.exists():
                    shutil.copy(dev_example_path, settings_example_path)
                    print(f"Created {settings_example_path} from development example")
                else:
                    print("Warning: settings.yaml.example not found in package or development folder")
        except Exception as e:
            print(f"Warning: Could not copy settings.yaml.example from package: {e}")
    
    # Handle media folder
    media_dir = work_dir / "media"
    video_path = media_dir / "neuro_start.mp4"
    
    # Copy media folder from package if it doesn't exist or is invalid
    if not media_dir.exists() or not video_path.exists():
        # If media dir exists but video doesn't, remove the incomplete media dir
        if media_dir.exists():
            shutil.rmtree(media_dir)
            
        try:
            # Try pkg_resources first (for installed packages)
            try:
                import pkg_resources
                package_media_path = pkg_resources.resource_filename('neuro_simulator', 'media')
                if os.path.exists(package_media_path):
                    shutil.copytree(package_media_path, media_dir)
                    print(f"Created {media_dir} from package media")
                else:
                    # Fallback to relative path (for development mode)
                    dev_media_path = Path(__file__).parent / "media"
                    if dev_media_path.exists():
                        shutil.copytree(dev_media_path, media_dir)
                        print(f"Created {media_dir} from development media")
                    else:
                        print("Warning: media folder not found in package or development folder")
            except Exception:
                # Fallback to relative path (for development mode)
                dev_media_path = Path(__file__).parent / "media"
                if dev_media_path.exists():
                    shutil.copytree(dev_media_path, media_dir)
                    print(f"Created {media_dir} from development media")
                else:
                    print("Warning: media folder not found in package or development folder")
        except Exception as e:
            print(f"Warning: Could not copy media folder from package: {e}")
    
    # Now check for required files and handle errors appropriately
    errors = []
    
    # Check for settings.yaml (required for running)
    if not settings_path.exists():
        if settings_example_path.exists():
            errors.append(f"Error: {settings_path} not found. Please copy {settings_example_path} to {settings_path} and configure it.")
        else:
            errors.append(f"Error: Neither {settings_path} nor {settings_example_path} found. Please ensure proper configuration.")
    
    # Check for required media files (required for running)
    if not media_dir.exists() or not video_path.exists():
        errors.append(f"Error: Required media files not found in {media_dir}.")
    
    # If there are any errors, print them and exit
    if errors:
        for error in errors:
            print(error)
        sys.exit(1)
    
    # Import and run the main application
    try:
        from neuro_simulator.main import run_server
        run_server(args.host, args.port)
    except ImportError:
        # Fallback for development mode
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from neuro_simulator.main import run_server
        run_server(args.host, args.port)

if __name__ == "__main__":
    main()