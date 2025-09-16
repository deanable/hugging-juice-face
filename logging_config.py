"""
Configuration for application-wide logging.
"""

import logging
import datetime

def setup_logging():
    """Configures the root logger to output to a file and the console."""
    log_filename = f"image_tagger_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
