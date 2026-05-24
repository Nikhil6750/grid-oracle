import os
from pathlib import Path

# Base directories
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Data directories
DATA_DIR = ROOT_DIR / os.getenv("DATA_DIR", "data")
RAW_DATA_DIR = ROOT_DIR / os.getenv("RAW_DATA_DIR", "data/raw")
PROCESSED_DATA_DIR = ROOT_DIR / os.getenv("PROCESSED_DATA_DIR", "data/processed")
FEATURES_DATA_DIR = ROOT_DIR / os.getenv("FEATURES_DATA_DIR", "data/features")
EXTERNAL_DATA_DIR = ROOT_DIR / os.getenv("EXTERNAL_DATA_DIR", "data/external")

# FastF1 Cache
FASTF1_CACHE_DIR = ROOT_DIR / os.getenv("FASTF1_CACHE_DIR", "data/raw/fastf1_cache")

# Logs
LOGS_DIR = ROOT_DIR / "logs"

def create_directories():
    """Ensure all critical directories exist."""
    directories = [
        DATA_DIR,
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        FEATURES_DATA_DIR,
        EXTERNAL_DATA_DIR,
        FASTF1_CACHE_DIR,
        LOGS_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    create_directories()
    print("Created base project directories.")
