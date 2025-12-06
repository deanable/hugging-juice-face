"""
Configuration for application-wide logging.
"""

import logging
import datetime
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configures the root logger to output to a file and the console with rotation."""
    log_filename = f"image_tagger_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'  # Explicitly set encoding to UTF-8
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # Explicitly set encoding for console handler to prevent UnicodeEncodeError on Windows
    console_handler = logging.StreamHandler() 
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )
