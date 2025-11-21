"""
Main entry point for the Advanced Image Tagger application.
"""

import logging
import sys
from gui import ImageTaggerGUI
from logging_config import setup_logging

if __name__ == "__main__":
    try:
        setup_logging()
        logging.info("Application starting.")
        app = ImageTaggerGUI()
        app.mainloop()
        logging.info("Application closed.")
    except Exception as e:
        logging.exception("Fatal error in application")
        sys.exit(1)
