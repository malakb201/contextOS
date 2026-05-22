"""
utils/logger.py  -  Sets up logging for the whole application.
Logs go to both the console and a rotating log file.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR  = os.path.join(BASE_DIR, "data", "user_data")
LOG_PATH = os.path.join(LOG_DIR, "contextos.log")

_FMT = logging.Formatter(
    fmt="%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
    datefmt="%H:%M:%S",
)

def setup_logger(level=logging.INFO):
    os.makedirs(LOG_DIR, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(_FMT)
    fh = RotatingFileHandler(LOG_PATH, maxBytes=2*1024*1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_FMT)
    if not root.handlers:
        root.addHandler(ch)
        root.addHandler(fh)
    return root
