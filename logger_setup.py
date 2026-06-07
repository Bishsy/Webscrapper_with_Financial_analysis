# logger_setup.py

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# ── Path fix ──────────────────────────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from config import ScraperConfig


def get_logger(name: str, config: ScraperConfig) -> logging.Logger:
    """
    Returns a configured logger.
    Safe to call multiple times — avoids duplicate handlers.
    """
    logger = logging.getLogger(name)

    # Return early if already configured
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt     = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S",
    )

    # ── Console handler (INFO and above) ─────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    # ── File handler (DEBUG and above, rotating) ──────────────────────────────
    file_handler = RotatingFileHandler(
        filename    = config.log_path,
        maxBytes    = 5 * 1024 * 1024,   # 5 MB
        backupCount = 3,
        encoding    = "utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from config import ScraperConfig
    cfg = ScraperConfig()
    log = get_logger("test", cfg)
    log.info("Logger is working!")
    log.debug("Debug message (only in log file)")
    print("✅ Logger setup successful!")