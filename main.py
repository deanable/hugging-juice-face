"""
Main entry point for the Advanced Image Tagger application.
"""

import logging
from gui import ImageTaggerGUI
from logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    logging.info("Application starting.")
    app = ImageTaggerGUI()
    app.mainloop()
    logging.info("Application closed.")
