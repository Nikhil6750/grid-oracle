import logging
import sys
from logging.handlers import RotatingFileHandler
from src.config.settings import settings
from src.utils.paths import LOGS_DIR

def get_logger(name: str) -> logging.Logger:
    """Configures and returns a logger with console and file handlers."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(settings.log_level.upper())
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOGS_DIR / "pitwall_ingestion.log"
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
