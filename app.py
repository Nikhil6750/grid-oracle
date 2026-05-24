"""
Root-level FastAPI entrypoint for Vercel deployment.
Vercel looks for an `app` object in app.py at the project root.
"""
import sys
from pathlib import Path

# Ensure src.* imports resolve when Vercel imports this file from the root
sys.path.insert(0, str(Path(__file__).parent))

from src.api.main import app  # noqa: E402


@app.get("/")
def root():
    return {"status": "Grid Oracle backend is running"}
