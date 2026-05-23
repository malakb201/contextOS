"""
utils/logger.py
Sets up logging for the whole application.
Logs go to both the console and a rotating log file.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR  = os.path.join(BASE_DIR, "data", "user_data")
LOG_PATH = os.path.join(LOG_DIR, "contextos.log")

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
    datefmt="%H:%M:%S",
)


def setup_logger(level=logging.INFO) -> logging.Logger:
    """
    Configure root logger with console + rotating file handler.
    Call once at startup. Returns the root logger.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler — clean output
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(_FORMATTER)

    # File handler — keeps last 2 MB, 3 backup files
    fh = RotatingFileHandler(
        LOG_PATH,
        maxBytes  = 2 * 1024 * 1024,   # 2 MB
        backupCount = 3,
        encoding  = "utf-8",
    )
    fh.setLevel(logging.DEBUG)   # always log everything to file
    fh.setFormatter(_FORMATTER)

    # Avoid duplicate handlers if called twice
    if not root.handlers:
        root.addHandler(ch)
        root.addHandler(fh)

    return root
