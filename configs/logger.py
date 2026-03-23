import logging
import logging.handlers
import os
import sys
from datetime import datetime

# ----------------------------------------------------
# Log file setup
# ----------------------------------------------------

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "interview_engine.log")


# ----------------------------------------------------
# Formatter — structured JSON-style for production
# ----------------------------------------------------

class StructuredFormatter(logging.Formatter):
    """
    Outputs logs in a clean structured format:
    2024-01-15 10:23:45 | INFO     | interview_manager | Current difficulty: medium
    """

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(8)
        name = record.name.ljust(25)
        return f"{timestamp} | {level} | {name} | {record.getMessage()}"


# ----------------------------------------------------
# Setup function — call once at app startup
# ----------------------------------------------------

def setup_logging(level: str = "INFO"):
    """
    Call this once in server.py at startup.
    Logs go to both console and a rotating file.
    """

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    formatter = StructuredFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)

    # Rotating file handler — max 5MB per file, keep last 5 files
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)

    # Apply to root logger so all modules inherit it
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if called multiple times
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)

    logging.getLogger("app").info(f"Logging initialised — level: {level}, file: {LOG_FILE}")