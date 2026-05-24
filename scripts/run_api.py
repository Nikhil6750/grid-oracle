"""
Launch script for PitWall AI API.
Usage: python scripts/run_api.py [--port 8000] [--host 0.0.0.0]
"""
import sys
import os
from pathlib import Path
import argparse
import uvicorn

# Ensure project root is on sys.path so uvicorn can resolve src.api.main
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

def main():
    parser = argparse.ArgumentParser(description="Run PitWall AI API")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=PROJECT_ROOT,
    )

if __name__ == "__main__":
    main()
