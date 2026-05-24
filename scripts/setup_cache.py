import sys
from pathlib import Path

# Add project root to path so we can import src
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.utils.paths import create_directories
from src.data_ingestion.base_ingestor import BaseIngestor
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    logger.info("Initializing PitWall AI backend setup...")
    
    # Create all paths
    create_directories()
    
    # Test base ingestor cache setup
    try:
        ingestor = BaseIngestor()
        logger.info("Cache setup completed successfully.")
    except Exception as e:
        logger.error(f"Cache setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
