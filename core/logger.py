"""
core/logger.py
--------------
Centralized structured logging for the Enterprise Knowledge Assistant.

Features:
 - Console + rotating file output (logs/rag_system.log)
 - Logs retrieval hits, ingestion events, and errors
 - 10 MB max file size, 3 backup files

Usage:
    from core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Retrieval hit | source=%s | page=%s", src, page)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Ensure the logs directory exists
Path("logs").mkdir(exist_ok=True)

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger for the given module name.
    Idempotent — safe to call multiple times in the same module.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured — avoid duplicate handlers

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # ── Console handler ──────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ── Rotating file handler (10 MB, 3 backups) ─────────────────────
    file_handler = RotatingFileHandler(
        "logs/rag_system.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Prevent propagation to avoid duplicate root-logger output
    logger.propagate = False

    return logger
