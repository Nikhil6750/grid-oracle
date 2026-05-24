import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.data_ingestion.base_ingestor import BaseIngestor
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    ingestor = BaseIngestor()
    
    # 2023 Bahrain Qualifying
    try:
        logger.info("Loading 2023 Bahrain Qualifying...")
        q_session = ingestor.load_session(2023, 'Bahrain', 'Q')
        assert not q_session.laps.empty, "Qualifying laps are empty"
        logger.info(f"Loaded Qualifying: {q_session.event.EventName} - Laps: {len(q_session.laps)}")
    except Exception as e:
        logger.error(f"Qualifying test failed: {e}")
        
    # 2023 Bahrain Race
    try:
        logger.info("Loading 2023 Bahrain Race...")
        r_session = ingestor.load_session(2023, 'Bahrain', 'R')
        assert not r_session.laps.empty, "Race laps are empty"
        logger.info(f"Loaded Race: {r_session.event.EventName} - Laps: {len(r_session.laps)}")
    except Exception as e:
        logger.error(f"Race test failed: {e}")

if __name__ == "__main__":
    main()
