"""
utils/logger.py
Shared logger for all agents.
Each module calls get_logger(__name__) to get a named logger.
"""

import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        ))
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger