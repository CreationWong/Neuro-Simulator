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
    else:
        work_dir = Path.home() / ".config" / "neuro-simulator"
        work_dir.mkdir(parents=True, exist_ok=True)
    
    # Change to working directory
    os.chdir(work_dir)
    
    # Copy settings.yaml.example to settings.yaml if it doesn't exist
    if not (work_dir / "settings.yaml").exists():
        # Try to find settings.yaml.example in the package
        try:
            import pkg_resources
            example_path = pkg_resources.resource_filename('neuro_simulator', 'settings.yaml.example')
            if os.path.exists(example_path):
                shutil.copy(example_path, work_dir / "settings.yaml")
                print(f"Created {work_dir / 'settings.yaml'} from example")
            else:
                print("Warning: settings.yaml.example not found in package")
        except Exception:
            print("Warning: Could not copy settings.yaml.example")
    
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