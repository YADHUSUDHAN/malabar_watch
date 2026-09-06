"""Centralized production logging configuration for Malabar Watch."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from malabar_watch.config import settings

# Default directory for application log files
LOGS_DIR = Path("logs")
DEFAULT_LOG_FILE = LOGS_DIR / "malabar_watch.log"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_level: str | None = None,
    log_file: str | Path | None = None,
    enable_file_logging: bool = True,
) -> None:
    """Configures root logger with clean console output and rotating file storage.

    Args:
        log_level: String log level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
                   Defaults to settings.LOG_LEVEL.
        log_file: Optional path to log file. Defaults to logs/malabar_watch.log.
        enable_file_logging: Whether to write rotating log files to disk.
    """
    level_name = (log_level or settings.LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    root_logger.handlers.clear()

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # 1. Console Stream Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler (5 MB max size, 5 backups, UTF-8 encoded)
    if enable_file_logging:
        target_path = Path(log_file or DEFAULT_LOG_FILE)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=str(target_path),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 3. Suppress noisy third-party libraries
    noisy_loggers = [
        "httpx",
        "httpcore",
        "telegram",
        "urllib3",
        "asyncio",
        "backoff",
    ]
    for noisy in noisy_loggers:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Convenience helper to retrieve a named logger."""
    return logging.getLogger(name)
