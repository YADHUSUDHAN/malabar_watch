"""Unit tests for centralized logging setup."""

import logging
from pathlib import Path

from malabar_watch.logging import get_logger, setup_logging


def test_setup_logging(tmp_path: Path):
    test_log_file = tmp_path / "test.log"
    setup_logging(log_level="DEBUG", log_file=test_log_file, enable_file_logging=True)

    logger = get_logger("malabar_watch.test")
    logger.info("Test log message for verification")

    # Verify log level was set
    assert logging.getLogger().level == logging.DEBUG

    # Verify file was written
    assert test_log_file.exists()
    content = test_log_file.read_text(encoding="utf-8")
    assert "Test log message for verification" in content
    assert "malabar_watch.test" in content
