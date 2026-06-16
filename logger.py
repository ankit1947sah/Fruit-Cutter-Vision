import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import config

def setup_logger():
    """Initializes and returns the root logger for the application."""
    # Ensure save/log directory exists
    os.makedirs(config.SAVE_DIR, exist_ok=True)
    
    logger = logging.getLogger("FruitNinjaVision")
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    # Format for logs
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(threadName)s] %(filename)s:%(lineno)d: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File Handler (Rotate logs at 1MB, keep 3 backup files)
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info("Logging initialized. Writing to %s", config.LOG_FILE)
    return logger

# Singleton instance of the logger
log = setup_logger()
