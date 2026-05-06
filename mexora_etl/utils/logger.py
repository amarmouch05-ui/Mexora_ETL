import logging
import os
from datetime import datetime
from config.settings import LOGS_DIR

def setup_logger() -> logging.Logger:
    """Configure le logger ETL avec sortie fichier + console."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file   = os.path.join(LOGS_DIR, f"etl_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(levelname)s — %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("mexora_etl")

logger = setup_logger()
