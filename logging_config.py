"""
Configuration for application-wide logging.
"""

import logging
import datetime
import sys
from logging.handlers import RotatingFileHandler

# A class to redirect stdout and stderr to the logging framework
class StreamToLogger:
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass

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
    console_handler = logging.StreamHandler(sys.__stdout__) 
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

    # Redirect stdout and stderr to the logger
    stdout_logger = logging.getLogger('STDOUT')
    sys.stdout = StreamToLogger(stdout_logger, logging.INFO)

    stderr_logger = logging.getLogger('STDERR')
    sys.stderr = StreamToLogger(stderr_logger, logging.ERROR)
