import fastf1
import pandas as pd
from typing import Optional
from src.utils.logger import get_logger
from src.utils.paths import FASTF1_CACHE_DIR

logger = get_logger(__name__)

class BaseIngestor:
    """Base class for FastF1 data ingestion."""
    
    def __init__(self):
        self.enable_cache()

    def enable_cache(self) -> None:
        """Enables the FastF1 cache."""
        try:
            FASTF1_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            fastf1.Cache.enable_cache(str(FASTF1_CACHE_DIR))
            logger.info(f"FastF1 cache enabled at {FASTF1_CACHE_DIR}")
        except Exception as e:
            logger.error(f"Failed to enable FastF1 cache: {e}")
            raise

    def get_event_schedule(self, year: int) -> pd.DataFrame:
        """Fetches the event schedule for a given year."""
        try:
            logger.info(f"Fetching event schedule for {year}")
            schedule = fastf1.get_event_schedule(year)
            return schedule
        except Exception as e:
            logger.error(f"Failed to fetch schedule for {year}: {e}")
            raise

    def get_session(self, year: int, grand_prix: str | int, session_type: str) -> fastf1.core.Session:
        """Gets a session without loading telemetry/lap data yet."""
        try:
            logger.info(f"Getting session: {year} {grand_prix} {session_type}")
            if session_type == 'SQ':
                try:
                    return fastf1.get_session(year, grand_prix, 'SQ')
                except ValueError as ve:
                    if "not known" in str(ve).lower():
                        logger.info(f"SQ not known, trying SS for {year} {grand_prix}")
                        return fastf1.get_session(year, grand_prix, 'SS')
                    raise
            return fastf1.get_session(year, grand_prix, session_type)
        except Exception as e:
            logger.error(f"Failed to get session {year} {grand_prix} {session_type}: {e}")
            raise

    def load_session(self, year: int, grand_prix: str | int, session_type: str) -> fastf1.core.Session:
        """Loads a session with all lap and telemetry data."""
        try:
            session = self.get_session(year, grand_prix, session_type)
            logger.info(f"Loading data for session: {year} {grand_prix} {session_type}")
            session.load()
            return session
        except Exception as e:
            logger.error(f"Failed to load session data {year} {grand_prix} {session_type}: {e}")
            raise

    def session_available(self, year: int, grand_prix: str | int, session_type: str) -> bool:
        """Checks if a session is available by attempting to get it (does not download telemetry)."""
        try:
            self.get_session(year, grand_prix, session_type)
            return True
        except Exception as e:
            logger.warning(f"Session not available: {year} {grand_prix} {session_type} - {e}")
            return False
